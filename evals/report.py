#!/usr/bin/env python3
"""Puts every run side by side. Without arguments: an overview of all of them."""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
runs = sorted(R.glob("*.json"))
if not runs:
    sys.exit("No runs in results/ yet.")

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


rows, models, costs = {}, [], {}
for f in runs:
    d = json.loads(f.read_text(encoding="utf-8"))
    name = f"{d['model']}  ({d['time_utc'][:10]})"
    models.append(name)
    run_costs = [t["cost_usd"] for t in d["tasks"] if t.get("cost_usd") is not None]
    costs[name] = cost_label(d["model"], run_costs)
    for t in d["tasks"]:
        if "error" in t:
            mark = "!"
        elif "auto" in t:
            mark = "+" if t["auto"]["passed"] else "-"
        else:
            r = t.get("manual", {}).get("rating")
            mark = {1: "+", 0.5: "o", 0: "-"}.get(r, "?")
        rows.setdefault(t["id"], {})[name] = mark

w = max(len(i) for i in rows) + 2
print(" " * w + "  ".join(f"{i+1:>3}" for i in range(len(models))))
for tid in sorted(rows):
    print(f"{tid:<{w}}" + "  ".join(f"{rows[tid].get(m,' '):>3}" for m in models))
print("\nKey:  + passed   o partial   - failed   ? unrated   ! error\n")
for i, m in enumerate(models, 1):
    print(f"  {i}: {m}  {costs[m]}")
