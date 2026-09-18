# Choosing a model

The question this is meant to answer: *which model should I open a branch of type X with?*

**It is not answered yet.** This file says what is measured, what is not, and what the method is, rather than presenting a recommendation the evidence does not support.

That is not modesty. The evaluation suite's central test is whether a model admits there is no answer instead of producing a plausible one; writing a confident selection guide on eight runs would fail the suite's own criterion.

## What exists

[`../evals/`](../evals) holds a fixed set of tasks, re-run unchanged against each new model, at temperature zero, with results versioned — including the bad runs, because a discarded run is a dishonest record.

How many tasks there are, and how many are machine-checkable, is `tasks/`'s own count — not a number to keep in sync here by hand. A fixed count in this sentence already drifted once: the collection grew from seven tasks to nine and this file, like `evals/README.md`, still said seven. **Three deliberately have no determinable answer** and measure whether the model says so or invents something plausible.

## The bridge

🔑 **The three unanswerable tasks are branch-independent.** Every branch needs a model that says *I don't know*. The branches that need it most are the ones where a plausible wrong answer costs more than an obvious failure — fluent prose that is wrong in the details is worse than a refusal, because nothing about it invites checking.

Each branch class then adds tasks of its own: administrative prose for one, tabular integrity for another, legacy numerics for a third. The task set is JSON files with a fixed schema, so a new class is new files and not new code.

## Profiles: the part that is built

The selection is by **task profile**, not by branch and not automatically. `tools/kontor` takes a profile name and launches the runner with the models that profile implies:

```
kontor profiles              list them
kontor which                 what this branch is set to
kontor run filing "..."      one-shot; nothing persists
kontor use reading           set this branch's default
```

🔑 **Why it is not automatic.** To decide whether a task is cheap, a system has to understand the task — which means a model call, which costs more than the cheap task saves. Every automatic router of this kind spends more deciding than it spends doing. The judgement stays with the person, at the moment they start, which is the only place it is free.

⚠️ **A local-first branch refuses `use` with a hosted profile.** It may reach a hosted model deliberately, per session, with `run` or by switching inside the runner — but it may not have one as its *default*. That distinction is the whole of local-first: a hosted default sends the first question before the thought *which model am I on* arrives.

The first version of this tool did not enforce that and cheerfully made a hosted model the permanent default of a local-first branch. It is enforced now, and verified in both directions: refused where it must be, allowed where it must be.

**Profiles are also the missing input to the question above.** With a task set per profile, "which tier suffices for filing-shaped work" becomes a measurement rather than the estimate currently written into the generated configuration.

## What is missing

- Enough runs to say anything about a tier. A handful of models is an impression, not a measurement.
- Task sets for branch classes other than the scientific and code ones.
- ~~A mapping from task class to confidentiality class~~ Now measurable rather than asserted: [`../evals/coverage.py`](../evals/coverage.py) checks each profile's assigned model against the tasks carrying that profile, using only committed runs in `results/`, and says per profile whether the assignment is *belegt* or a *Schätzung*. Its second section is the confidentiality axis proper — for every profile pointing at a hosted model, whether any **local** model is evidenced on that profile's tasks at all, i.e. whether a local-first branch could do that class of work with measured capability or would have to guess. As of 2026-09-18, after `run.py` learned to go through `crush run` for the one provider only it reaches: drafting's model is evidenced on all three of its tasks (one failure — it hedged the unanswerable question well, then named a number anyway); reading on one of three; filing on one of three, with a failure on record. Analysis's assigned model (`hyper/glm-5.3`) rejects every request through crush with `bad request: Invalid input` — a one-word probe included, while its `-flash` sibling answers — so four attempts produced no verdict at all. That is a finding about the instance configuration, not about capability, and it is the kind the report exists to surface: the profile has been pointing at a model that does not currently answer, and nothing else would have said so. Runs through crush are marked as such in the result (`geschirr`): the temperature is the provider's default, not 0, and crush's agent system prompt precedes the task — comparable among themselves, not with the direct API runs.

Until those runs exist, the model choice per branch in the distributed configuration is an **estimate**, and is marked as one — `coverage.py` says which ones.

---
← [README](../README.md) · [The fallback](fallback.md)
