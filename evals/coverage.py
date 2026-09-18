#!/usr/bin/env python3
"""Which profile-to-model assignment in profiles.conf is evidenced, and which is a guess?

choosing-a-model.md states openly that the model choice per profile is
currently an estimate. This script turns that into a checkable claim: for
each profile, the assigned (large) model, the tasks that carry that profile,
and whether there is a run in results/ for exactly that model on exactly
those tasks — and how it went.

Second part, the confidentiality axis: a local-first branch may not have a
hosted model as its default (tools/kontor refuses it). For profiles that
point at a hosted model, this reports whether any local model is evidenced
on their tasks at all — that is, whether a local-first branch could do that
kind of work with measured capability, or would simply have to guess.

Reads only results/*.json (the durable, versioned evidence) and the instance
configuration. No model call, no cost.
"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS, RESULTS = ROOT / "tasks", ROOT / "results"
PROFILES = Path(os.environ.get("KONTOR_PROFILES", os.path.expanduser("~/.config/kontor/profiles.conf")))


def norm(model):
    """'ollama/kontor-4b:latest' and 'kontor-4b:latest' mean the same model;
    older runs wrote the name without a provider prefix. 'crush/' is not a
    provider but the harness (run.py, ask_crush) — underneath it the model is
    named as profiles.conf names it."""
    return re.sub(r"^(ollama|crush)/", "", model)


def load_profiles():
    if not PROFILES.is_file():
        sys.exit(f"no profiles.conf at {PROFILES} (see tools/profiles.conf.example)")
    out = {}
    for line in PROFILES.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "profile":
            out[parts[1]] = {"large": parts[2], "small": parts[3]}
    return out


def load_tasks():
    out = {}
    for f in sorted(TASKS.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        out[t["id"]] = t.get("profile", [])
    return out


def verdict(t):
    if "error" in t:
        return "error"
    if "auto" in t:
        return "+" if t["auto"]["passed"] else "-"
    r = t.get("manual", {}).get("rating")
    return {1: "+", 0.5: "o", 0: "-"}.get(r, "?")


def load_results():
    """(normalised model, task) -> list of (date, verdict)."""
    out = {}
    for f in sorted(RESULTS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue  # an interrupted run; it sits in results/ but is not evidence
        m = norm(d["model"])
        for t in d["tasks"]:
            out.setdefault((m, t["id"]), []).append((d["time_utc"][:10], verdict(t)))
    return out


def evidence(results, model, task):
    """Only real verdicts count. An HTTP error is not evidence, and neither
    is an unrated manual run."""
    return [(dt, v) for dt, v in results.get((norm(model), task), []) if v in "+o-"]


def main():
    profiles, tasks, results = load_profiles(), load_tasks(), load_results()
    by_profile = {}
    for tid, profs in tasks.items():
        for p in profs:
            by_profile.setdefault(p, []).append(tid)

    print("Evidenced or estimated?  Per profile: the assigned large model against\n"
          "the tasks that carry that profile, according to results/.\n")
    for p, spec in profiles.items():
        model = spec["large"]
        tids = sorted(by_profile.get(p, []))
        print(f"== {p}  ->  {model} ==")
        tested, passed, failed, errored = 0, 0, 0, 0
        for tid in tids:
            ev = evidence(results, model, tid)
            if not ev:
                # "never attempted" and "attempted, only errors" are two
                # different results; the second usually means the model is
                # not reachable through the harness that reaches it.
                runs = results.get((norm(model), tid), [])
                if runs:
                    errored += 1
                    print(f"  {tid:<32} error, no evidence  ({len(runs)} run(s), last {runs[-1][0]})")
                else:
                    print(f"  {tid:<32} untested")
                continue
            tested += 1
            dt, v = ev[-1]
            if v == "+": passed += 1
            elif v == "-": failed += 1
            print(f"  {tid:<32} {v}  ({dt}" + (f", {len(ev)} runs" if len(ev) > 1 else "") + ")")
        if not tids:
            print("  (no task carries this profile)")
        elif tested == 0 and errored:
            print(f"  => ESTIMATE -- {errored} of {len(tids)} attempted, only errors, not one verdict\n")
            continue
        elif tested == 0:
            print("  => ESTIMATE -- not a single run with this model on these tasks\n")
            continue
        elif failed:
            print(f"  => evidenced, with failures: {tested} of {len(tids)} tested, {passed} passed, {failed} failed\n")
            continue
        else:
            rest = "" if tested == len(tids) else f" -- {len(tids) - tested} still untested"
            print(f"  => evidenced: {tested} of {len(tids)} tested, all passed{rest}\n")
            continue

    print("Confidentiality axis: profiles with a hosted model, and whether any local\n"
          "model is evidenced on their tasks. A local-first branch may not have the\n"
          "hosted model as its default; this says whether it could fall back on\n"
          "measured local capability instead.\n")
    # After norm() a local model carries no provider prefix; anything with a
    # slash is hosted.
    local_models = sorted({m for (m, _) in results if "/" not in m})
    for p, spec in profiles.items():
        model = spec["large"]
        if model.startswith("ollama/"):
            continue
        tids = sorted(by_profile.get(p, []))
        print(f"== {p}  ({model}, hosted) ==")
        any_local = False
        for lm in local_models:
            hits = [(tid, evidence(results, lm, tid)) for tid in tids]
            hits = [(tid, ev[-1][1]) for tid, ev in hits if ev]
            if hits:
                any_local = True
                print(f"  local evidence: {lm}  " + "  ".join(f"{tid} {v}" for tid, v in hits))
        if not any_local:
            print("  no local model evidenced on any of these tasks -- a local-first branch\n"
                  "  would have to guess here, not measure")
        print()


if __name__ == "__main__":
    main()
