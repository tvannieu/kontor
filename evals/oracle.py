#!/usr/bin/env python3
"""Check the checks: does each task's verifier accept an answer known to be right?

A verifier that rejects a correct answer is a broken task, not a failing model.
Both times that happened here it was found by accident — once when a task's
check demanded a flag its prompt never asked for, and once when a task's stated
symptom turned out not to follow from its own code, after thirteen models had
been marked as passing it. Harbor's `oracle` agent does this deliberately, by
submitting a task's reference solution to its own verifier; this is the same
idea at the scale of this collection.

Every task carries an `oracle` block:

    "oracle": {
      "expect":   "pass" | "reject" | "grader",
      "solution": "an answer that is correct",
      "why":      "only for expect=reject: why the rejection is the known defect"
    }

`pass`    the check must accept the solution. A failure here is a broken task.
`reject`  the check is known to reject the honest answer; that defect is the
          point of the task's existence and is documented in `why`. A *pass*
          here is the surprise, and is reported.
`grader`  a manual task: no mechanical check exists, so the solution is the
          reference answer for the model grader in inspect_port/.

Takes no model call and costs nothing. Run it whenever a check changes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from run import CHECKS  # noqa: E402 -- the runner's own checks, not a copy

#     ./oracle.py                   the task set in tasks/
#     ./oracle.py classifier/tasks  any other set in the same format
TASKS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tasks"


def main():
    problems, graded = 0, []
    print("Does each check accept an answer known to be right?\n")
    for f in sorted(TASKS.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        tid = t["id"]
        o = t.get("oracle")
        if not o:
            print(f"  {tid:<34} NO REFERENCE ANSWER — nothing checks this check")
            problems += 1
            continue
        if o["expect"] == "grader":
            graded.append(tid)
            print(f"  {tid:<34} manual task; reference answer kept for the model grader")
            continue

        fn = CHECKS.get(t["check"])
        ok, note = fn(o["solution"], t["expect"])
        want_pass = o["expect"] == "pass"
        if ok == want_pass:
            if want_pass:
                print(f"  {tid:<34} accepts its own correct answer  ({note})")
            else:
                print(f"  {tid:<34} rejects the honest answer, as documented  ({note})")
        else:
            problems += 1
            if want_pass:
                print(f"  {tid:<34} BROKEN TASK: rejects a correct answer  ({note})")
            else:
                print(f"  {tid:<34} CHANGED: now accepts the honest answer it used to reject —")
                print(f"  {'':<34} the documented defect may be fixed; re-read the task")

    if graded:
        print(f"\n{len(graded)} manual tasks carry a reference answer for the grader: "
              + ", ".join(graded))
    print()
    if problems:
        print(f"{problems} task(s) need attention.")
        return 1
    print("Every check accepts an answer known to be right, or fails one for a "
          "reason written down in the task.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
