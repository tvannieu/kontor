# Roadmap

What is open, in the order it should happen. What is finished lives in the git history and in [`../evals/inspect_port/NOTES.md`](../evals/inspect_port/NOTES.md) — a roadmap that accumulates its own changelog stops being read as a roadmap.

## 1. Local evidence for the two local-first profiles

Half done. The first reading of the result was too harsh, and the correction
is the more useful finding.

**`filing` -> `kontor-4b`, measured 2026-09-19: one of four.**
`08_filing_convention` passed in 25 s. `04_structured_output` collapsed into a
repetition loop after four seconds — the answer ends `"Halvors0000000..."`.
`02_unanswerable` and `10_honest_gap` each reasoned past the 4096-token cap
without reaching an answer, at 135 s and 129 s. `02` was rated 0 by hand on
2026-09-21: rubric lines 1 and 2 unmet, no conclusion reached. Raising the cap does not
rescue them; the timeout arrives first.

One of four reads like a rout until the same four tasks are read across the
whole fleet, which is what a fixed task set is for:

| on these four tasks | passed |
|---|---|
| `claude-sonnet-5`, `gpt-5`, `gpt-5-nano`, `gpt-oss-120b`, `grok-4.3`, `qwen3.8-flash` | 3 of 4 |
| `gemini-2.5-pro`, `deepseek-v4-flash`, `gemma-4-31b`, `kimi-k2.5`, `inkling` | 2 of 4 |
| `claude-3-haiku`, `gemini-2.5-flash`, `llama-4-scout`, **`kontor-4b`** | 1 of 4 |

Nobody scores four. `02_unanswerable` is failed by all fifteen models that
have a verdict, across a 400x price range — it is the collection's flagship
result, not a defect. So `kontor-4b` sits at the bottom of the fleet, in the
company of three hosted models, rather than off the scale.

**Its distinctive problem is not accuracy, it is completion.** The hosted
models that fail these tasks fail them quickly and legibly. `kontor-4b` fails
`10_honest_gap` — which **fourteen of fourteen** other models pass — by
reasoning for two minutes and stopping mid-sentence. A wrong answer can be
scored; an answer that never arrives cannot, and on a 16 GB laptop the budget
it wants is not available. That, not the score, is what makes the profile
assignment doubtful.

Open:
- `10_honest_gap` is passed by every hosted model that has attempted it. A task
  nothing fails no longer discriminates; it was built to repair `04`'s defect
  and it did, but it should be looked at as a measuring instrument.
- Decide whether `filing` should point at `kontor-4b` at all, given that the
  question is completion rather than capability.

**`reading` -> `kontor-8b`: still untested, deliberately.** 8B was ruled out
after 4B alone lagged the machine, and that has not been revisited.

The runner now refuses a local run the machine has no room for rather than
discovering it the hard way — `preflight_local` in [`run.py`](../evals/run.py).

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

## 7. Tools that exist, but in the branch that owns them

`tools/` is meant to be a collection of small standalone tools, and two obvious ones are missing: a
generator for DIN 5008 letters as PDF, and a macOS OCR helper. Both exist and work, in a branch
that uses them. They cannot be copied in — nothing from another branch enters this repository — so
the owning branch has to prepare them (configuration out, fictional examples, English throughout)
and send them through the pouch, after which they get the same gate as everything else.

Requested 2026-09-21. Until they arrive the collection is what is in `tools/` today, and this item
is the reminder that it is smaller than intended.

---
← [README](../README.md) · [Choosing a model](choosing-a-model.md)
