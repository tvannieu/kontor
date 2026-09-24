# model-evals

A fixed set of tasks, run unchanged against every new model.

## Why

Anyone can say "I test new models". What almost nobody does, because it is work: **the same tasks every time, rated the same way every time, results kept.** Only that turns an impression into a statement.

It is the same idea as the scattering-code comparison this came out of: one task, several independent implementations, systematic comparison. There it was six scattering codes; here it is language models.

## What is unusual about it

Most collections measure whether a model finds the right answer. **This one measures above all whether it admits when there is none.** Five of the ten tasks have no determinable answer or contain a trap — `ls tasks/` is the authority on the total, not this line:

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
./run.py openai/gpt-5 --epochs 3                  # three runs per task; the verdict is the majority
./run.py --dry-run                                # shows what would be sent, no key needed
./report.py                                       # every run side by side
./coverage.py                                     # which profile-model assignment is evidenced, which is a guess
./oracle.py                                       # does every check accept an answer known to be right?
```

A second, smaller task set lives in [`classifier/`](classifier/) and answers a different question — whether a model knows when it *cannot* decide which profile a piece of work belongs to. Same runner, same checks, same format:

```bash
KONTOR_TASKS_DIR=$PWD/classifier/tasks KONTOR_RESULTS_DIR=$PWD/classifier/results ./run.py openai/gpt-5-nano
./report.py classifier/results
./oracle.py classifier/tasks
```

All four tools resolve their directories the same way — command-line argument
first, then `KONTOR_TASKS_DIR` / `KONTOR_RESULTS_DIR`, then the default. They
did not always: `oracle.py` read only the argument, so an environment variable
set for a classifier run checked the main task set and reported a pass for it.

**The key is in no file.** `run.py` takes it from the operating system's keychain and only then falls back to an environment variable:

```bash
security add-generic-password -a "$USER" -s kontor-openrouter -w   # prompts; not in shell history
```

That keeps the key out of the repository and out of shell configuration, and an accidental `git add` cannot catch it. `OPENROUTER_API_KEY` still works, but it is the fallback, not the way.

Via **OpenRouter**, new models are usually available within hours of release, billed per token rather than per subscription. A full run costs a few cents, depending on the model.

`temperature=0`, so that runs stay comparable. It does not make them identical: three runs of `deepseek-v4-flash` at temperature 0 answered task 02 with 37 s, 17.2 s and 106 s. That is why `--epochs` exists, and why a single run is not a measurement. A task whose epochs disagree is reported as `~` rather than as its majority.

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
oracle.py   submits each task's own known-good answer to its own check
classifier/ a second task set: can a model tell when it cannot route a job?
inspect_port/  the same tasks ported to Inspect AI, with an opinion in NOTES.md
run.py, report.py, coverage.py and oracle.py each have tests beside them
            where the behaviour is worth guaranteeing: test_run.py covers the
            retry-and-backoff path
```

[`kontor-eval-contract.md`](kontor-eval-contract.md) is the depth: how a manual
rating has to be written so `report.py` can read it, what the HTTP error codes
mean and why collapsing them all into `!` loses information, and one
instruction that turned out to be wrong and is kept as a correction.

Every task carries an `oracle` block holding an answer known to be right, and `oracle.py` puts it through that task's own verifier. Task `04` declares `"expect": "reject"` — the text names no year, so the honest `null` fails its type check by design, which is the documented defect that `10` exists to correct. Everything else must accept its own correct answer, and `03` was retired the day this was introduced because it did not: its premise turned out to be false, after thirteen models had been scored as passing it.

## The one place that is not in English

Everything written here is in English. Three kinds of file are not, and the
distinction is deliberate rather than an oversight:

- [`retired/german-suite-2026-09/`](retired/german-suite-2026-09/) — the
  original tasks and every run made against them. **Translating a prompt
  changes the artefact being measured**, so under this collection's own rule
  they were not edited: they were retired whole and replaced by new English
  tasks starting from zero runs.
- stored answers and stored human ratings, in `results/` and in the port's
  calibration artefacts. A record of what a model actually said is not a
  document to be improved.
- [`inspect_port/regression_two_pass.py`](inspect_port/regression_two_pass.py)
  and its `regression_case.json`, which replay one retired task's rubric
  against one stored answer. Translating the input would destroy the point of
  a regression test.

Everywhere those are quoted in prose, the quotation is given in English and
marked as a translation.

## Rules that keep it worth something

1. **Do not patch a prompt when a model fails it.** Otherwise the collection only measures itself.
2. **Commit results**, including the bad runs.
3. **New tasks come out of real work**, not from puzzle books.
4. **One run per model per round**; variance belongs in the note, not in a second attempt. One exception on record: `crush/openrouter/thinkingmachines/inkling:free` was run again on 2026-09-22, three days after its first run and outside `--epochs`. Kept, because it failed `01` and `02` the same way both times — the same shape of wrong answer, not just the same verdict — which is evidence the finding is stable, not an excuse to discard the rule when a second run happens to agree.
5. **A verifier that fails a correct answer is a broken task, not a failing model.** Task 10 of the retired suite is the worked example.
