# model-evals

A fixed set of tasks, run unchanged against every new model.

## Why

Anyone can say "I test new models". What almost nobody does, because it is work: **the same tasks every time, rated the same way every time, results kept.** Only that turns an impression into a statement.

It is the same idea as the scattering-code comparison this came out of: one task, several independent implementations, systematic comparison. There it was six scattering codes; here it is language models.

## What is unusual about it

Most collections measure whether a model finds the right answer. **This one measures above all whether it admits when there is none.** Three of the tasks have no determinable answer or contain a trap — how many there are in total is what `ls tasks/` says, not this line:

- `02_unanswerable` asks for a value the data does not support. If the model gives a number, it has failed, however plausible the number is.
- `01_frame_consistency` shows two results that differ only in the sign of one quantity. If the model invents a conversion factor, it has failed.
- `06_context_fidelity` contains a year that departs from world knowledge. The model is meant to stay with the text.
- `09_citation_that_does_not_exist` asks where something is stated in a text that does not state it. An invented citation is the expensive failure: it is believed, because it looks like a quotation.
- `10_honest_gap` permits `null` where the text gives no value, and requires it. Any number there — including `0` as a placeholder — counts as invented.

That is the failure shape that matters: these systems do not fail with an error message, they fail with a fluent wrong answer.

## Usage

```bash
./run.py openai/gpt-5                             # all tasks
./run.py openai/gpt-5 --tasks 02 05               # only some
./run.py ollama/kontor-4b --profile filing        # only tasks concerning filing work
./run.py crush/hyper/glm-5.3 --profile analysis   # through the agent runner, for providers only it reaches
./run.py --dry-run                                # shows what would be sent, no key needed
./report.py                                       # every run side by side
./coverage.py                                     # which profile-model assignment is evidenced, which is a guess
```

**The key is in no file.** `run.py` takes it from the operating system's keychain and only then falls back to an environment variable:

```bash
security add-generic-password -a "$USER" -s kontor-openrouter -w   # prompts; not in shell history
```

That keeps the key out of the repository and out of shell configuration, and an accidental `git add` cannot catch it. `OPENROUTER_API_KEY` still works, but it is the fallback, not the way.

Via **OpenRouter**, new models are usually available within hours of release, billed per token rather than per subscription. A full run costs a few cents, depending on the model.

`temperature=0`, so that runs stay comparable. Three runs of one model at temperature 0 nevertheless produced three different answers to task 01, which is why `--epochs` exists in the Inspect port and why a single run is not a measurement.

## Rating

Seven tasks check themselves (`contains_any`, `regex_absent`, `json_schema`). Three need a judgement; for those, every task carries a **rubric**, and the result carries a `manual.rating` field to be filled with `1`, `0.5` or `0`.

That part of it is rated by hand is not a defect. That is exactly where the question sits that cannot be automated — and [`inspect_port/calibrate.py`](inspect_port/calibrate.py) measures how far a model judge can be trusted to stand in for it.

## Layout

```
tasks/      one file per task, versioned. Prompts are not quietly changed;
            whoever changes something creates a new task. A *.json.draft does
            not run — renaming it to .json is the approval
results/    one result per run, filename from timestamp and model
retired/    tasks that no longer run, with their results and the reason
run.py      the runner
report.py   comparison of all runs
coverage.py profile-to-model assignment against results/: evidenced or estimated
inspect_port/  the same tasks ported to Inspect AI, with an opinion in NOTES.md
```

## Rules that keep it worth something

1. **Do not patch a prompt when a model fails it.** Otherwise the collection only measures itself.
2. **Commit results**, including the bad runs.
3. **New tasks come out of real work**, not from puzzle books.
4. **One run per model per round**; variance belongs in the note, not in a second attempt.
5. **A verifier that fails a correct answer is a broken task, not a failing model.** Task 10 of the retired suite is the worked example.
