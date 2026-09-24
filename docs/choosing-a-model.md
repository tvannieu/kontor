# Choosing a model

The question this is meant to answer: *which model should I open a branch of type X with?*

**It is not answered yet.** This file says what is measured, what is not, and what the method is, rather than presenting a recommendation the evidence does not support.

That is not modesty. The evaluation suite's central test is whether a model admits there is no answer instead of producing a plausible one; writing a confident selection guide on twenty runs would fail the suite's own criterion.

## What exists

[`../evals/`](../evals) holds a fixed set of tasks, re-run unchanged against each new model, at temperature zero, with results versioned — including the bad runs, because a discarded run is a dishonest record.

How many tasks there are, and how many are machine-checkable, is `tasks/`'s own count — not a number to keep in sync here by hand. A fixed count in this sentence has already drifted twice: the collection grew from seven tasks to nine while this file still said seven, and the count of trap tasks stood at three here and in `evals/README.md` while five were listed beneath it. **Five have no determinable answer or contain a trap** — `../evals/tasks/*.json` is the authority on the total — and they measure whether the model says so or invents something plausible.

## The bridge

**The tasks with no determinable answer are branch-independent.** Every branch needs a model that says *I don't know*. The branches that need it most are the ones where a plausible wrong answer costs more than an obvious failure — fluent prose that is wrong in the details is worse than a refusal, because nothing about it invites checking.

Each branch class then adds tasks of its own: administrative prose for one, tabular integrity for another, legacy numerics for a third. The task set is JSON files with a fixed schema, so a new class is new files and not new code.

## Profiles: the part that is built

The selection is by **task profile**, not by branch and not automatically. `tools/kontor` takes a profile name and launches the runner with the models that profile implies:

```
kontor profiles              list them
kontor which                 what this branch is set to
kontor run filing "..."      one-shot; nothing persists
kontor use reading           set this branch's default
```

**Why it is not automatic.** To decide whether a task is cheap, a system has to understand the task — which means a model call, which costs more than the cheap task saves. Every automatic router of this kind spends more deciding than it spends doing. The judgement stays with the person, at the moment they start, which is the only place it is free.

**A local-first branch refuses `use` with a hosted profile.** It may reach a hosted model deliberately, per session, with `run` or by switching inside the runner — but it may not have one as its *default*. That distinction is the whole of local-first: a hosted default sends the first question before the thought *which model am I on* arrives.

The first version of this tool did not enforce that and cheerfully made a hosted model the permanent default of a local-first branch. It is enforced now, and verified in both directions: refused where it must be, allowed where it must be.

**Profiles are also the missing input to the question above.** With a task set per profile, "which tier suffices for filing-shaped work" becomes a measurement rather than the estimate currently written into the generated configuration.

## What is missing

- Enough runs to say anything about a tier. A handful of models is an impression, not a measurement.
- Task sets for branch classes other than the scientific and code ones.

### The mapping from task class to confidentiality class

No longer missing, and no longer asserted. [`../evals/coverage.py`](../evals/coverage.py)
checks each profile's assigned model against the tasks carrying that profile,
using only committed runs in `results/`, and reports per profile whether the
assignment is **evidenced** or an **estimate**. Its second section is the
confidentiality axis proper: for every profile pointing at a hosted model,
whether any *local* model is evidenced on those tasks at all — that is, whether
a local-first branch could do that class of work with measured capability or
would simply have to guess.

**The instance finding that came out of it.** `analysis` pointed at
`hyper/glm-5.3`, which rejected every request through crush with `bad request:
Invalid input` — a one-word probe included, while its `-flash` sibling answered.
Four attempts, no verdict. Chased as far as it can be from here: the model ID
matches crush's cached catalog and `crush models` lists it for this account;
lowering `max_tokens` and clearing the reasoning flag change nothing; crush's
log shows a generic upstream provider error with no request detail. Every
config-side lever is ruled out, so the rejection is on the provider's side.

That is a finding about the instance rather than about capability, and it is
exactly what the report exists to surface: **the profile had been pointing at a
model that does not answer, and nothing else would have said so.** Repointed to
`glm-5.3-flash` on 2026-09-18, the reason recorded beside the line in
`profiles.conf`, with a note to return once it answers.

Run on the same four tasks as a stand-in, `glm-5.3-flash` passes both
machine-checked ones and fails both epistemic ones — it asserts a cause on `01`
as good as certain, and names a figure on `02` with no caveat at all. Two of
four: competent on the checkable work, wrong in precisely the way this suite
exists to catch.

Runs made through crush carry a `harness` field in the result, because the
temperature is the provider's default rather than 0 and crush's agent system
prompt precedes the task. They are comparable among themselves, not with the
direct API runs.

Until those runs exist, the model choice per branch in the distributed configuration is an **estimate**, and is marked as one — `coverage.py` says which ones.

---
← [README](../README.md) · [The fallback](fallback.md)
