# Roadmap

What is open, in the order it should happen. What is finished lives in the git history and in [`../evals/inspect_port/NOTES.md`](../evals/inspect_port/NOTES.md) — a roadmap that accumulates its own changelog stops being read as a roadmap.

## 1. Local evidence for the two local-first profiles

[`coverage.py`](../evals/coverage.py) reports `filing` and `reading` as **estimate**: neither `kontor-4b` nor `kontor-8b` has run the current task set. This is the half of the argument that matters most. Local-first exists so that a branch whose contents must not leave the machine still has somewhere to send work — and nothing at present shows those two models can do it. Fourteen hosted models have data; the two the confidentiality rule actually depends on have none.

Blocked on machine headroom rather than on effort. This laptop has 16 GB and has twice been driven deep into swap by a local run. `run.py` sets no token cap, and the 4B model has been observed to spend an entire context on a single prompt without producing an answer. Run one task at a time and watch the memory.

## 2. Check the checks against answers known to be right

Task 10 exists because task 04's verifier rejects an honest `null`. Task 10's own first verifier then rejected a correct answer too, and was retired a day later. Both were found by accident, which is the problem.

Harbor does this on purpose: its `oracle` agent submits a task's own reference solution to that task's verifier, so a verifier that fails a correct answer is caught as a broken *task* rather than misread as a failing model. Nothing here does that. Two checks are already suspect — `08` tests a string where it means a file, and `09`'s forbidden-pattern regex has fired on an answer that was right but happened to cite an unrelated clause.

The cheap version: one known-good answer stored beside each task, re-checked whenever a check changes.

## 3. More than one run per model

The same model at `temperature=0` answered task 04 with `null` twice and an integer once. A single run is therefore not a measurement, at least for that task — and every column in the comparison table is a single run.

The Inspect port has `--epochs` with a `mode` reducer; `run.py` has nothing. Either lift it across, or mark in the table which columns are one sample. The second is honest and costs nothing.

## 4. A grader that cannot invert its own rule

[`calibrate.py`](../evals/inspect_port/calibrate.py) found one disagreement in fourteen items: a grader identified the decisive rubric line as unmet and then awarded partial credit anyway. Correct analysis, inverted rule. The structure is sound — both graders found the same fact — and the aggregation is what leaked.

The fix is a two-pass scorer: decide each decisive line yes or no, then derive the letter mechanically instead of asking the model to conclude. Harbor's rewardkit offers exactly this as `mode = "individual"`. Not built here.

## 5. An eval'd classifier — still not yet

[`choosing-a-model.md`](choosing-a-model.md) argues against automatic model routing on cost: classifying a task requires understanding it, which means a model call, which costs more than the cheap task saves. A **free, local** classifier defeats that particular argument — but trades it for a worse one. Misclassification is not a compute cost. A classifier that confidently routes the wrong task to the wrong model fails silently, one layer before the task is ever seen: the exact failure shape this suite exists to catch, moved somewhere nothing is watching.

Worth building, as an extension of the measurement discipline rather than a bet placed ahead of it: a small task set of "here is a task, which profile is this" with known-correct answers, scored the same honesty-over-confidence way — does it escalate on an ambiguous case, or guess?

Gated on (1). Building a classifier on top of profiles that are half estimate moves the guess up a level instead of removing it.

## 6. Waiting on infrastructure

**Harbor, run rather than read.** `colima` and the docker CLI are installed; the VM has never been started, because the machine sat at 20 GB of swap when they went in. One `hello-alpine` trial would turn that section of `NOTES.md` from a careful code reading into experience.

**`thinkingmachines/inkling`** answers a plain API call with 403: available only through an agentic harness. That is an integration, not a retry, and it remains the one model in this repository's history with no data at all.

---
← [README](../README.md) · [Choosing a model](choosing-a-model.md)
