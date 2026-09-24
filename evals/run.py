#!/usr/bin/env python3
"""
Run the fixed task set against one model and record the result.

    ./run.py anthropic/claude-sonnet-4.5
    ./run.py openai/gpt-5 --tasks 02 05
    ./run.py ollama/kontor-4b --profile filing      only the tasks that concern filing work
    ./run.py crush/hyper/glm-5.3 --profile analysis through the agent runner, for providers only it reaches

Without a key:  ./run.py --dry-run   shows what would be sent.
"""
import argparse, atexit, json, os, shutil, subprocess, sys, tempfile, time, re, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Overridable so the same runner, the same checks and the same result format
# serve a second task set (classifier/) without a second copy of any of it.
TASKS = Path(os.environ.get("KONTOR_TASKS_DIR", ROOT / "tasks"))
RESULTS = Path(os.environ.get("KONTOR_RESULTS_DIR", ROOT / "results"))
API = "https://openrouter.ai/api/v1/chat/completions"


def load_tasks(only=None, profile=None):
    """only: task-id prefixes. profile: only tasks that concern this profile.

    A profile is a kind of work, not a branch. Tasks without a profile field
    apply to all of them — anything unassigned is not silently excluded.
    Every check has a population it leaves out; here that population is
    empty, deliberately."""
    out = []
    for f in sorted(TASKS.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        if only and not any(t["id"].startswith(p) for p in only):
            continue
        if profile and profile not in t.get("profile", [profile]):
            continue
        out.append(t)
    return out


_CRUSH_CWD = None


def ask_crush(name, prompt, timeout):
    """A 'crush/' prefix means: through the agent runner, not directly.

    Needed for providers only crush itself reaches — the Hyper models speak
    Charm's own protocol rather than the OpenAI format, and crush holds the
    login for it. Two limitations belong in the result: the temperature is
    not controllable (the provider's default, not 0), and crush puts its
    agent system prompt in front of the task. Runs made this way are a
    different harness from the direct calls and are marked as one.

    crush reads its providers from the crush.json of the working directory,
    so a throwaway directory gets a copy of the one Kontor distributes —
    which also keeps its session database out of the repository."""
    global _CRUSH_CWD
    if _CRUSH_CWD is None:
        _CRUSH_CWD = tempfile.mkdtemp(prefix="kontor-evals-crush-")
        shutil.copy(ROOT.parent / "crush.json", _CRUSH_CWD)
        atexit.register(shutil.rmtree, _CRUSH_CWD, ignore_errors=True)
    crush = os.environ.get("KONTOR_CRUSH", "crush")
    t0 = time.time()
    r = subprocess.run([crush, "run", "-q", "-c", _CRUSH_CWD, "-m", name, prompt],
                       capture_output=True, text=True, timeout=timeout, cwd=_CRUSH_CWD)
    if r.returncode != 0:
        raise RuntimeError(f"crush run: {r.stderr.strip()[:300]}")
    return r.stdout.strip(), round(time.time() - t0, 1), {}


# --- local runs: the machine is a resource like any other -------------------
#
# This laptop has 16 GB. Two runs of a 4B model drove it into swap deep enough
# that it stopped responding and had to be restarted, both times because the
# runner asked for a local model without first asking whether there was room
# for one, and then waited ten minutes for an answer that was never coming.
#
# Three separate mistakes, so three separate guards:
#   free_ram()      refuse to load a model that does not fit
#   LOCAL_MAX_TOKENS  cap the answer, so one prompt cannot eat a whole context
#   LOCAL_TIMEOUT   give up in minutes rather than in ten
#
# The check is macOS-specific and returns None elsewhere; None means "cannot
# tell", and cannot-tell is reported rather than treated as a pass. That is
# the same rule tools/check-public.sh follows.

LOCAL_MAX_TOKENS = int(os.environ.get("KONTOR_LOCAL_MAX_TOKENS", 4096))
LOCAL_TIMEOUT = int(os.environ.get("KONTOR_LOCAL_TIMEOUT", 180))
OLLAMA = os.environ.get("KONTOR_OLLAMA", "http://127.0.0.1:11434")


def free_ram():
    """(free_bytes, swap_used_bytes, pressure) on macOS, or None if unknown.

    `pressure` is kern.memorystatus_vm_pressure_level: 1 normal, 2 warning,
    4 critical. It is the live signal. vm.swapusage is *cumulative* and does
    not fall when the pressure passes, so gating on it refuses runs the
    machine has ample room for — which this did, for one commit, at 4.6 GB
    free and pressure level 1. Swap is still reported, as history."""
    if sys.platform != "darwin":
        return None
    try:
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10).stdout
        page = int(re.search(r"page size of (\d+) bytes", vm).group(1))

        def pages(label):
            m = re.search(rf"{label}:\s+(\d+)", vm)
            return int(m.group(1)) * page if m else 0

        # Free plus inactive: inactive pages are reclaimable without paging
        # out. Speculative and compressed pages are not counted as available,
        # because they are the pressure, not the relief.
        free = pages("Pages free") + pages("Pages inactive")
        sw = subprocess.run(["sysctl", "-n", "vm.swapusage"],
                            capture_output=True, text=True, timeout=10).stdout
        used = float(re.search(r"used\s*=\s*([\d.,]+)M", sw).group(1).replace(",", "."))
        lvl = subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
                             capture_output=True, text=True, timeout=10).stdout
        return free, int(used * 1024 * 1024), int(lvl.strip() or 1)
    except Exception:
        return None


def model_bytes(name):
    """Size of a local model as ollama reports it, or None if unknown."""
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=10) as r:
            for m in json.loads(r.read()).get("models", []):
                if m["name"] == name or m["name"].split(":")[0] == name.split(":")[0]:
                    return m.get("size")
    except Exception:
        return None
    return None


def preflight_local(name, force=False):
    """Refuse a local run the machine has no room for. Returns a note to record."""
    need = model_bytes(name)
    mem = free_ram()
    gb = lambda n: f"{n / 1024**3:.1f} GB"
    if mem is None or need is None:
        msg = ("Cannot measure free memory or model size, so cannot tell whether "
               f"{name} fits.")
        if not force:
            sys.exit(f"{msg}\nRe-run with --force-local if you are sure. "
                     "A check that cannot run is not a pass.")
        return msg
    free, swap, pressure = mem
    # 1.3x: weights are not the whole footprint — the KV cache and the runner
    # itself also want room, and a model that fits exactly does not fit.
    headroom = need * 1.3
    state = {1: "normal", 2: "warning", 4: "critical"}.get(pressure, str(pressure))
    report = (f"{name} needs ~{gb(need)} (~{gb(headroom)} with its cache); "
              f"{gb(free)} available, pressure {state}, {gb(swap)} swap used so far")
    if free < headroom or pressure >= 2:
        if not force:
            sys.exit(
                f"Not enough room: {report}.\n\n"
                "This is the condition that hung the machine twice. Free memory "
                "first — quitting the browser and the chat apps is usually "
                "enough — then run this again. --force-local overrides, at your "
                "own risk.")
        report += " -- OVERRIDDEN with --force-local"
    return report


def unload_local(name):
    """Release the weights. Without this the model sits in RAM for five
    minutes after the run, which matters on a machine this size."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA}/api/generate",
            data=json.dumps({"model": name, "keep_alive": 0}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass


RETRY_STATUSES = {429, 503}


def _urlopen_with_retry(req, timeout, max_retries=3):
    """Retry a hosted call that failed with 429 (rate limited) or 503
    (provider overloaded), honouring Retry-After when the server sends one.

    Added 2026-09-24, replacing a blanket `time.sleep(60)` after every task
    regardless of model or provider — which slowed every run, including
    ones that never hit a limit, and still was not enough: a free-tier
    model kept returning 429 three separate times with the delay in place.
    A fixed sleep guesses at the wait; reading the response is not a guess.
    Only 429/503 are retried — anything else is the caller's problem, same
    as before. Local (Ollama) calls never go through this at all."""
    delay = 5
    for attempt in range(max_retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_STATUSES or attempt == max_retries:
                raise
            wait = delay
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after and retry_after.isdigit():
                wait = int(retry_after)
            time.sleep(wait)
            delay *= 3


def ask(model, prompt, key, temperature=0.0, timeout=600):
    """An 'ollama/' prefix means: local, and local only.

    An earlier version tried OpenRouter first and fell back to local on
    HTTP 400, with the model name unchanged — a name Ollama does not know.
    The second error was then swallowed by a bare `except Exception: pass`
    and the first one reported, so the message pointed at the wrong service.
    It routes now instead of guessing, and a local failure is reported as a
    local failure."""
    if model.startswith("crush/"):
        return ask_crush(model.split("/", 1)[1], prompt, timeout)
    local = model.startswith("ollama/")
    name = model.split("/", 1)[1] if local else model
    payload = {
        "model": name,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if local:
        # Without a cap the 4B model has been observed to spend an entire
        # context on one prompt and return nothing, holding its weights in
        # RAM the whole time. A truncated answer is a result; a wedged
        # machine is not.
        payload["max_tokens"] = LOCAL_MAX_TOKENS
    else:
        # OpenRouter only returns usage.cost when explicitly asked; Ollama
        # has no such concept and ignores an unknown field harmlessly, but
        # local calls are free anyway so there is nothing to request.
        payload["usage"] = {"include": True}
    body = json.dumps(payload).encode()

    if local:
        url, headers = "http://127.0.0.1:11434/v1/chat/completions", {
            "Content-Type": "application/json"}
    else:
        url, headers = API, {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tvannieu/kontor",
            "X-Title": "kontor-evals",
        }

    req = urllib.request.Request(url, data=body, headers=headers)
    t0 = time.time()
    opener = urllib.request.urlopen if local else _urlopen_with_retry
    with opener(req, timeout=LOCAL_TIMEOUT if local else timeout) as r:
        d = json.loads(r.read())
    choice = d["choices"][0]
    msg = choice["message"]
    # Reasoning models put the output in a field of their own and leave
    # content empty when the token budget runs out before the answer.
    text = msg.get("content") or msg.get("reasoning") or ""
    usage = dict(d.get("usage", {}))
    # A cap that stops an answer mid-word has not measured the model, it has
    # measured the cap. The first version of this guard scored two truncated
    # answers as invalid JSON, which is true and beside the point. Carry the
    # reason out so the caller can tell the two apart.
    usage["finish_reason"] = choice.get("finish_reason")
    return text, round(time.time() - t0, 1), usage


def check_contains_any(ans, expect):
    hits = [e for e in expect if e.lower() in ans.lower()]
    return (bool(hits), f"found: {hits}" if hits else f"none of {expect}")


def check_regex_absent(ans, expect):
    hits = [p for p in expect if re.search(p, ans)]
    return (not hits, "clean" if not hits else f"forbidden but present: {hits}")


def check_json_schema(ans, expect):
    raw = ans.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    try:
        o = json.loads(raw)
    except Exception as e:
        return (False, f"not valid JSON: {e}")
    missing = [k for k in expect.get("required", []) if k not in o]
    if missing:
        return (False, f"missing keys: {missing}")
    kinds = {"int": int, "list": list, "str": str}
    for k, want in expect.get("types", {}).items():
        if k in o and not isinstance(o[k], kinds[want]):
            return (False, f"{k} is {type(o[k]).__name__}, expected {want}")
    # Two optional additions (2026-09-18, for task 10): keys that MUST be
    # null — because the text does not supply the value and any number there
    # would be invented — and lists that must contain particular entries.
    # Task 04 cannot tell an honestly marked gap from a plausible guess;
    # with these, a task can.
    for k in expect.get("null", []):
        if k not in o:
            return (False, f"{k} missing")
        if o[k] is not None:
            return (False, f"{k} is {o[k]!r}, but the text supplies no value: invented")
    for k, items in expect.get("list_contains", {}).items():
        have = o.get(k) if isinstance(o.get(k), list) else []
        missing = [i for i in items if i not in have]
        if missing:
            return (False, f"{k} does not list: {missing}")
    return (True, "schema satisfied")


CHECKS = {"contains_any": check_contains_any,
          "regex_absent": check_regex_absent,
          "json_schema": check_json_schema}


def get_key():
    """The OS keychain first, the way Kontor uses it, then the environment."""
    import subprocess
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "kontor-openrouter", "-w"],
            capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get("OPENROUTER_API_KEY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", help="e.g. anthropic/claude-sonnet-4.5")
    ap.add_argument("--tasks", nargs="*", help="only these prefixes, e.g. 02 05")
    ap.add_argument("--profile", help="only tasks of this profile, e.g. filing")
    ap.add_argument("--epochs", type=int, default=1, metavar="N",
                    help="run each task N times; the verdict is the majority, and a task "
                         "that does not agree with itself is marked unstable")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-local", action="store_true",
                    help="run a local model even when the machine has no room for it")
    a = ap.parse_args()

    tasks = load_tasks(a.tasks, a.profile)
    if not tasks:
        sys.exit("No tasks found.")

    if a.dry_run:
        for t in tasks:
            print(f"\n=== {t['id']}  ({t['check']})\n{t['prompt'][:300]}")
        print(f"\n{len(tasks)} tasks.")
        return

    if not a.model:
        sys.exit("Name a model, e.g.:  ./run.py anthropic/claude-sonnet-4.5")
    key = get_key()
    if not key and not a.model.startswith(("ollama/", "crush/")):
        sys.exit("No OpenRouter key found.\n"
                 "Kontor keeps it in the OS keychain under 'kontor-openrouter':\n"
                 "  security find-generic-password -s kontor-openrouter -w\n"
                 "Alternatively:  export OPENROUTER_API_KEY=sk-or-...")

    local_name = a.model.split("/", 1)[1] if a.model.startswith("ollama/") else None
    headroom = None
    if local_name:
        headroom = preflight_local(local_name, a.force_local)
        print(f"Local run: {headroom}\n")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    run = {"model": a.model, "time_utc": stamp, "tasks": []}
    if a.model.startswith("crush/"):
        run["harness"] = ("crush run: temperature not controllable (provider default, not 0), "
                          "agent system prompt in front of the task, no token or cost figures. "
                          "Not directly comparable with runs made through the API.")
    open_ratings = 0

    if a.epochs > 1:
        run["epochs"] = a.epochs

    for t in tasks:
        print(f"  {t['id']} ... ", end="", flush=True)
        fn = CHECKS.get(t["check"])
        attempts, failed = [], None
        for _ in range(a.epochs):
            try:
                ans, dur, usage = ask(a.model, t["prompt"], key)
            except urllib.error.HTTPError as e:
                failed = f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"
                break
            except Exception as e:
                failed = str(e)
                break
            att = {"seconds": dur, "tokens": usage.get("total_tokens"),
                   "cost_usd": usage.get("cost"), "answer": ans,
                   "truncated": usage.get("finish_reason") == "length"}
            if fn:
                ok, note = fn(ans, t["expect"])
                att["passed"], att["note"] = ok, note
            attempts.append(att)

        if failed is not None:
            print(f"Error: {failed[:90]}")
            run["tasks"].append({"id": t["id"], "error": failed})
            continue

        costs_here = [x["cost_usd"] for x in attempts if x["cost_usd"] is not None]
        rec = {"id": t["id"], "title": t["title"],
               "seconds": round(sum(x["seconds"] for x in attempts), 1),
               "tokens": sum(x["tokens"] or 0 for x in attempts) or None,
               "cost_usd": sum(costs_here) if costs_here else None,
               "answer": attempts[0]["answer"]}
        cost = f"  ${rec['cost_usd']:.5f}" if rec["cost_usd"] is not None else ""
        if a.epochs > 1:
            # Keep every attempt: the point of epochs is the disagreement, and
            # a reduced verdict that hides which runs disagreed is worth less
            # than no reduction at all.
            rec["attempts"] = attempts

        if fn:
            verdicts = [x["passed"] for x in attempts]
            ok = sum(verdicts) * 2 > len(verdicts)          # majority
            stable = len(set(verdicts)) == 1
            # The note has to come from an attempt that agrees with the
            # reported verdict, or an unstable task prints "PASS" beside the
            # reason one attempt failed.
            note = next(x["note"] for x in attempts if x["passed"] == ok)
            cut = any(x["truncated"] for x in attempts)
            rec["auto"] = {"passed": ok, "note": note, "stable": stable}
            if cut and not ok:
                # Not a verdict on the answer: the answer never finished.
                rec["auto"]["truncated"] = True
                note = f"{note} -- but the answer was cut off at the token cap"
                rec["auto"]["note"] = note
            mark = "PASS" if ok else ("TRUNC" if cut else "FAIL")
            extra = "" if stable else f"  UNSTABLE {sum(verdicts)}/{len(verdicts)}"
            print(f"{mark}  ({note}){extra}  {rec['seconds']}s{cost}")
        else:
            rec["manual"] = {"rating": None, "rubric": t.get("rubric", []), "note": ""}
            if any(x["truncated"] for x in attempts):
                rec["manual"]["note"] = ("cut off at the token cap -- rate the "
                                         "answer that exists, or raise the cap and re-run")
            open_ratings += 1
            cut = "  CUT OFF at the token cap" if any(x["truncated"] for x in attempts) else ""
            print(f"to be rated  {rec['seconds']}s{cost}{cut}")
        run["tasks"].append(rec)

    if local_name:
        # What the machine had at the time is part of the result: a local run
        # made under pressure is not comparable with one made with room, and
        # an answer cut off at the token cap is not the model's best.
        run["local"] = {"headroom": headroom, "max_tokens": LOCAL_MAX_TOKENS,
                        "timeout_s": LOCAL_TIMEOUT}
        unload_local(local_name)

    RESULTS.mkdir(exist_ok=True)
    # ':' is legal on this filesystem and not on Windows; model ids carry it
    # (":free"), and a repository meant to be cloned should not hand out files
    # that cannot be checked out.
    out = RESULTS / f"{stamp}_{a.model.replace('/', '_').replace(':', '-')}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWritten: {out.relative_to(ROOT)}")
    costs = [r["cost_usd"] for r in run["tasks"] if r.get("cost_usd") is not None]
    if costs:
        print(f"Cost (as reported by OpenRouter): ${sum(costs):.5f}")
    if open_ratings:
        print(f"{open_ratings} tasks await your rating. Set the field 'manual.rating' "
              f"to 1, 0.5 or 0 and fill in 'note'.")


if __name__ == "__main__":
    main()
