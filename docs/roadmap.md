# Roadmap

What's next, in the order it should happen and why — not a wishlist, a dependency order. Written 2026-09-17.

## 1. Close the evals gap

Everything below depends on this being solid, not the other way around. `choosing-a-model.md` is already honest that model choice per branch is currently **an estimate, marked as one**: not enough runs to say anything about a tier, no task sets for branch classes beyond the scientific and code ones, and no mapping from task class to confidentiality class.

What's open, concretely:

- **The Inspect AI port** (`evals/inspect_port/`) is validated against one hosted model (`openai/gpt-oss-120b`) and unvalidated against the local Ollama models — the local run that should have validated it hung for an hour and had to be killed twice before the harness got a `max_tokens`/`timeout`/`max_connections` cap. Needs a careful, single-sample-first re-validation.
- **No multi-model comparison run yet.** The original point of the port — same tasks, several models, write up the differences — has one model's worth of data.
- **No cost tracking.** `report.py` shows pass/fail only. `run.py` already captures token counts per task and the Inspect port captures full usage; neither is surfaced anywhere a model choice could be based on it. "Capable enough" and "cheap enough" are currently two separate judgement calls a person makes from memory, not one comparison a report shows.
- **No task-class-to-confidentiality mapping.** The cheap model adequate for one branch's tasks may be unusable for another's, and nothing here measures that second axis yet.

## 2. An eval'd classifier, not an assumed one — later, not now

`choosing-a-model.md`'s argument against automatic model routing is that classifying a task costs more (in a paid model call) than the cheap task saves. A **free, local** classifier breaks that specific argument — but trades it for a different, more dangerous cost: **misclassification**, not compute. A classifier that confidently routes the wrong task to the wrong model fails silently, one layer before the task itself is ever seen — exactly the failure shape the whole eval suite exists to catch, just moved earlier.

So: worth building, but as a natural extension of the measurement discipline already here, not a bet placed ahead of it —

- A small task set: "here's a task, which profile is this," with known-correct answers.
- Scored the same honesty-over-confidence way as the rest of the suite: does it escalate on an ambiguous case instead of guessing.
- Only attempted once (1) has given the tier system enough runs to trust in the first place. Building a classifier on top of an unvalidated tier system just moves the estimate one level up.

## 3. Documentation — real gap, but narrow and lower-stakes

The one concrete hole found so far: there is no single walkthrough of how someone else would actually adopt kontor — clone the system repo (not yet public; no remote configured as of this writing), create sibling branch repos with no shared git history, seed them from `templates/`, populate `~/.config/kontor/` themselves, run the distribution scripts. Reconstructable today from `README.md` + `architecture.md` + `pouch.md` + `fallback.md` together, but nowhere as one path. A contained addition, not a rewrite — the existing docs are already disciplined. Ranked below the evals gap because nothing here blocks anything else; it's a reader's convenience, not a dependency.

---
← [README](../README.md) · [Choosing a model](choosing-a-model.md)
