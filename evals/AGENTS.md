# evals — the task set

Part of the Kontor repository. Overview: [`../README.md`](../README.md), context: [`../docs/choosing-a-model.md`](../docs/choosing-a-model.md).

## What this is

A **fixed set of tasks**, run unchanged against every new language model. Created in September 2026, because "I test new models" without fixed tasks and kept results stays an impression and never becomes a statement.

## The one rule everything rests on

**Prompts are not patched when a model fails them.**

Whoever changes a task creates a **new** one and leaves the old one standing. Otherwise the collection eventually measures only itself, and every earlier run becomes worthless.

That applies to you as an agent too: **never touch `tasks/*.json` quietly.**

## What is measured here

Not in the first instance whether a model finds the right answer, but **whether it admits when there is none.** Five of the tasks (`01`, `02`, `06`, `09`, `10`) have no determinable answer or contain a trap. `ls tasks/` is the authority on both counts, not this line — it has been wrong about this one twice. A plausible invented number is a failure, not partial credit.

That is the failure shape at issue: these systems do not fail with an error message, they fail with a fluent wrong answer.

## Working rules

- **Results are committed**, including the bad runs. A discarded run is a falsified comparison.
- **One model per run, once.** Variance belongs in the note, not in a second attempt.
- **New tasks come out of real work**, not from puzzle books. If something actually went wrong in the scattering-code comparison, in a research branch or in the agent system, it is a candidate.
- `temperature=0`, so that runs stay comparable. Do not change it.
- **A verifier that fails a correct answer is a broken task.** Check a new check against an answer you know to be right before trusting it. The retired task 10 is what happens when you do not.

## Key

The OpenRouter key is in the macOS keychain under **`kontor-openrouter`**, the same one `tools/distribute_crush_config.sh` writes into the crush.json. `run.py` takes it from there; failing that, `OPENROUTER_API_KEY`. **The key does not belong in a file.**

## Structure

| Path | Contents |
|---|---|
| `tasks/` | one file per task, versioned, immutable |
| `results/` | one result per run, named after timestamp and model |
| `retired/` | tasks that no longer run, with their results and the reason |
| `run.py` | runner, via OpenRouter, Ollama, or the agent runner |
| `report.py` | comparison of all runs |
| `coverage.py` | which profile-model assignment is evidenced, which is estimated |
| `inspect_port/` | the same tasks under Inspect AI, with an opinion in `NOTES.md` |

## What it is for

Two purposes, and the second is the more important one.

1. **Selection:** which model is fit for which kind of work in the Kontor. The crush.json carries several providers and price tiers; which tier suffices where used to be a feeling. `coverage.py` is where it stops being one.
2. **Evidence:** claiming experience with evaluation is easy. After a few runs this is no longer a claim.

---
## Document Information
*Last Updated: September 19, 2026* *Document Type: Guide* *Scope: Working instructions for agents in model-evals* *Status: Active Documentation*
