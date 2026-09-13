# Choosing a model

The question this is meant to answer: *which model should I open a branch of type X with?*

**It is not answered yet.** This file says what is measured, what is not, and what the method is, rather than presenting a recommendation the evidence does not support.

That is not modesty. The evaluation suite's central test is whether a model admits there is no answer instead of producing a plausible one; writing a confident selection guide on eight runs would fail the suite's own criterion.

## What exists

[`../evals/`](../evals) holds a fixed set of tasks, re-run unchanged against each new model, at temperature zero, with results versioned — including the bad runs, because a discarded run is a dishonest record.

Seven tasks. Four are machine-checkable. **Three deliberately have no determinable answer** and measure whether the model says so or invents something plausible.

## The bridge

🔑 **The three unanswerable tasks are branch-independent.** Every branch needs a model that says *I don't know*. The branches that need it most are the ones where a plausible wrong answer costs more than an obvious failure — fluent prose that is wrong in the details is worse than a refusal, because nothing about it invites checking.

Each branch class then adds tasks of its own: administrative prose for one, tabular integrity for another, legacy numerics for a third. The task set is JSON files with a fixed schema, so a new class is new files and not new code.

## What is missing

- Enough runs to say anything about a tier. A handful of models is an impression, not a measurement.
- Task sets for branch classes other than the scientific and code ones.
- A mapping from task class to confidentiality class — the cheap model that is adequate for one may be unusable for another, and that is a second axis the current results do not touch.

Until those exist, the model choice per branch in the distributed configuration is an **estimate**, and is marked as one.

---
← [README](../README.md) · [The fallback](fallback.md)
