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
TASKS, RESULTS = ROOT / "tasks", ROOT / "results"
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
    if not local:
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
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    msg = d["choices"][0]["message"]
    # Reasoning models put the output in a field of their own and leave
    # content empty when the token budget runs out before the answer.
    text = msg.get("content") or msg.get("reasoning") or ""
    return text, round(time.time() - t0, 1), d.get("usage", {})


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
    ap.add_argument("--dry-run", action="store_true")
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

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    run = {"model": a.model, "time_utc": stamp, "tasks": []}
    if a.model.startswith("crush/"):
        run["harness"] = ("crush run: temperature not controllable (provider default, not 0), "
                          "agent system prompt in front of the task, no token or cost figures. "
                          "Not directly comparable with runs made through the API.")
    open_ratings = 0

    for t in tasks:
        print(f"  {t['id']} ... ", end="", flush=True)
        try:
            ans, dur, usage = ask(a.model, t["prompt"], key)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}")
            run["tasks"].append({"id": t["id"], "error": f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"})
            continue
        except Exception as e:
            print(f"Error: {e}")
            run["tasks"].append({"id": t["id"], "error": str(e)})
            continue

        rec = {"id": t["id"], "title": t["title"], "seconds": dur,
               "tokens": usage.get("total_tokens"), "cost_usd": usage.get("cost"),
               "answer": ans}
        cost = f"  ${rec['cost_usd']:.5f}" if rec["cost_usd"] is not None else ""
        fn = CHECKS.get(t["check"])
        if fn:
            ok, note = fn(ans, t["expect"])
            rec["auto"] = {"passed": ok, "note": note}
            print(("PASS" if ok else "FAIL") + f"  ({note})  {dur}s{cost}")
        else:
            rec["manual"] = {"rating": None, "rubric": t.get("rubric", []), "note": ""}
            open_ratings += 1
            print(f"to be rated  {dur}s{cost}")
        run["tasks"].append(rec)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{stamp}_{a.model.replace('/', '_')}.json"
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
