#!/usr/bin/env python3
"""Puts every run side by side.

    ./report.py                       the runs in results/
    ./report.py classifier/results    any other set of runs in the same format
    KONTOR_RESULTS_DIR=... ./report.py    the same, for a whole shell

Argument first, environment second, default third, as in run.py and oracle.py.
"""
import json, os, sys
from pathlib import Path

R = Path(sys.argv[1] if len(sys.argv) > 1
         else os.environ.get("KONTOR_RESULTS_DIR",
                             Path(__file__).resolve().parent / "results"))
runs = sorted(R.glob("*.json"))
if not runs:
    sys.exit(f"No runs in {R}/ yet.")

def cost_label(model, run_costs):
    """What a run cost has three honest answers: a number, zero because the
    model is local, or unknown. Naming the provider adds nothing — hosted is
    the ordinary case — and 'local / not recorded' used to be printed for all
    three, which said a metered model was free. Unknown is not zero."""
    if run_costs:
        return f"${sum(run_costs):.5f}"
    if model.startswith("ollama/") or "/" not in model:
        return "$0 — runs locally"
    if model.startswith("crush/"):
        return "unknown — the agent runner reports no usage"
    return "unknown — no usage in the response"


loaded = [json.loads(f.read_text(encoding="utf-8")) for f in runs]
# Two runs of one model on one day are two columns; the legend has to tell
# them apart, so the clock time is added only where the date is not enough.
seen = {}
for d in loaded:
    seen[(d["model"], d["time_utc"][:10])] = seen.get((d["model"], d["time_utc"][:10]), 0) + 1

rows, models, costs = {}, [], {}
for d in loaded:
    stamp = d["time_utc"][:10]
    if seen[(d["model"], stamp)] > 1:
        stamp += " " + d["time_utc"][11:]
    name = f"{d['model']}  ({stamp})"
    models.append(name)
    run_costs = [t["cost_usd"] for t in d["tasks"] if t.get("cost_usd") is not None]
    costs[name] = cost_label(d["model"], run_costs)
    for t in d["tasks"]:
        if "error" in t:
            mark = "!"
        elif "auto" in t:
            mark = "+" if t["auto"]["passed"] else "-"
            # A task that does not agree with itself across epochs is reported
            # as such rather than as its majority: task 04 answered null twice
            # and an integer once from one model at temperature 0.
            if t["auto"].get("stable") is False:
                mark = "~"
        else:
            r = t.get("manual", {}).get("rating")
            mark = {1: "+", 0.5: "o", 0: "-"}.get(r, "?")
        rows.setdefault(t["id"], {})[name] = mark

w = max(len(i) for i in rows) + 2
print(" " * w + "  ".join(f"{i+1:>3}" for i in range(len(models))))
for tid in sorted(rows):
    print(f"{tid:<{w}}" + "  ".join(f"{rows[tid].get(m,' '):>3}" for m in models))
print("\nKey:  + passed   o partial   - failed   ~ unstable across epochs   ? unrated   ! error\n")
for i, m in enumerate(models, 1):
    print(f"  {i}: {m}  {costs[m]}")
