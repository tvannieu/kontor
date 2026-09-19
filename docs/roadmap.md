# Roadmap

What is open, in the order it should happen. What is finished lives in the git history and in [`../evals/inspect_port/NOTES.md`](../evals/inspect_port/NOTES.md) — a roadmap that accumulates its own changelog stops being read as a roadmap.

## 1. Local evidence for the two local-first profiles

[`coverage.py`](../evals/coverage.py) reports `filing` and `reading` as **estimate**: neither `kontor-4b` nor `kontor-8b` has run the current task set. This is the half of the argument that matters most. Local-first exists so that a branch whose contents must not leave the machine still has somewhere to send work — and nothing at present shows those two models can do it. Fifteen hosted models have data; the two the confidentiality rule actually depends on have none.

Blocked on machine headroom rather than on effort. This laptop has 16 GB and has twice been driven deep into swap by a local run; at the time of writing it sits at 21 GB of swap with about 60 MB of RAM free. `run.py` sets no token cap, and the 4B model has been observed to spend an entire context on one prompt without producing an answer. Run one task at a time and watch the memory.

## 2. Weigh a rubric line without hand-maintaining a list

`DECISIVE_CRITERIA` in [`kontor_evals.py`](../evals/inspect_port/kontor_evals.py) names, per task, which rubric lines are decisive — and it is a hand-kept mapping of quoted strings, guarded only by an assertion that fires when a line stops matching. That is the shape of every drift this repository has recorded: the manifest's inbox table, the README's task count, the empty deny-list.

The lines could live in the task files, where the rubric already is. That is a change to `tasks/*.json`, so under the collection's own rule it means new task files rather than edits, and it is worth doing only if the mapping grows.

## 3. Grade the manual tasks across epochs

`--epochs` reduces automatic checks by majority and marks disagreement as `~`. For manual tasks it records every attempt and still asks for one rating, which leaves the rater to judge a set of answers as though it were one. `deepseek-v4-flash` answering 37 s, 17.2 s and 106 s to the same question got a single 0, and the three numbers only survive in the note because someone wrote them there.

Either rate each attempt, or record a per-task variance the report can show.

## 4. A case that sits on the C/P boundary

The two-pass scorer was built because a grader identified a decisive line as unmet and awarded partial credit anyway. It cannot be shown to help: on all 36 human-rated answers both designs agree with the human rating exactly, because every rating in the set is a clear 0 or 1 and nothing sits on the boundary where the error occurred. Replaying the original case shows the single-call design is *unstable* there rather than wrong — P one day, I the next, same input.

What would settle it is a manual answer that genuinely deserves P, rated by hand, and then graded both ways several times. There is not one in the collection yet.

## 5. The classifier, now that it has been measured

[`evals/classifier/`](../evals/classifier/) exists and has been run against five models. The determined cases are trivial — 25 of 25. The underdetermined ones split, and they split the expensive way: three of five models answered "clean up the project folder" with a confident *filing*, which is the reading that means renaming rather than the one that means deciding what to delete.

So the original argument holds, with numbers behind it now: a cheap classifier is not often wrong, it is confidently wrong exactly where being wrong is irreversible, and it is wrong silently. Building a router on that needs a way to see when it guessed — the escalation path has to be real, not a word in a prompt. Still gated on (1) for the tier evidence.

## 6. Harbor, run rather than read

`colima` and the docker CLI are installed; the VM has never been started, because the machine has not had the memory since they went in. One `hello-alpine` trial would turn that section of `NOTES.md` from a careful code reading into experience. Same blocker as (1), and it should wait for the same clearance.

---
← [README](../README.md) · [Choosing a model](choosing-a-model.md)
