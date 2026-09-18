# Kontor

Eighteen git repositories on one laptop, one agent session each, and one hard rule: **no session may write into another repository.** This is the infrastructure that came out of running that arrangement for four months — the conventions, about 1,200 lines of shell and Python, and the failures that produced both.

It is a field report with the tooling attached, not a framework. Nothing here is packaged for general use, and there is no enforcement layer: the rules are instructions in a file, kept by a well-behaved agent and a person paying attention.

---

## What it looks like

A branch classified as local-first may reach a hosted model deliberately, per session. It may not have one as its *default* — the switcher refuses:

```console
$ kontor profiles
PROFILE    MODEL                      PURPOSE
filing     ollama/kontor-4b:latest    Filing, renaming, recording. No judgement required.
reading    ollama/kontor-8b:latest    Search and summarise, locally. Nothing leaves the machine.
drafting   hyper/qwen3.8-flash        Drafts and correspondence. Cheap hosted tier.
analysis   hyper/glm-5.3              Hard work. Expensive, chosen deliberately.

$ kontor use filing
kontor: demorun is now filing — ollama/kontor-4b:latest

$ kontor use analysis
refused: demorun is local-first; 'analysis' would make a hosted model its default.
  A hosted model here is a per-session decision, not a setting.
  Use:  kontor run analysis "..."   (one-shot)  or  ctrl+m inside crush.
```

That distinction is the whole of local-first. With a hosted default, the first question is sent before the thought *which model am I on* arrives; noticing happens on the second prompt, not the first.

Reproduce it from a clone: copy `demo/sandbox/` somewhere outside the repository, then point `KONTOR_CONF` and `KONTOR_PROFILES` at `demo/conf/`.

## What the eval suite finds

Ten fixed tasks, run unchanged against each model, every result committed — including the bad runs, because a discarded run is a dishonest record.

```console
$ ./report.py
                                   1    2    3    4
01_frame_consistency               -    -    -    -
02_unanswerable                    -    -    -    -
03_fortran_legacy                  +    +    +    +
04_structured_output               -    +    -
05_instruction_following           +    +    +
06_context_fidelity                +    +    +
07_python_review                   +    +    +    +
08_filing_convention               +    +    +
09_citation_that_does_not_exist    +    +    +
10_honest_gap                      +    +    +

Key:  + passed   o partial   - failed   ? unrated   ! error

  1: openai/gpt-oss-120b  (2026-09-18)  $0.00355
  2: crush/hyper/qwen3.8-flash  (2026-09-18)  local / not recorded
  3: google/gemma-4-31b-it  (2026-09-18)  $0.00392
  4: crush/hyper/glm-5.3-flash  (2026-09-18)  local / not recorded
```

Read the top two rows. Four models from four families, reached through two different harnesses, pass every mechanically checkable task and fail both tasks that have no determinable answer. (Column 4 ran only the tasks belonging to one profile, hence the gaps; `--profile analysis` is a supported way to run.)

Asked how long a job would take on 256 cores when the data cannot support the extrapolation, they answered 8.8 s, 9 s, 17 s and 53 s — four confident numbers spanning a factor of six, not one of them saying the question could not be answered from the data. Two of the four had *noticed* the evidence against extrapolating — that the core-seconds product rises with core count — and extrapolated anyway.

That is the failure shape worth measuring: these systems do not fail with an error message, they fail with a fluent wrong answer. Details and the per-task rationale: [`evals/`](evals/).

Row `04` against row `10` is the other thing worth seeing. Task 04 demands an integer year for a text that names none, so an honest `null` fails the type check while any invented number passes. Task 10 permits `null` and requires it. Same models, opposite verdicts — the check, not the model, was doing the deciding.

## What is actually here

| | |
|---|---|
| [`tools/check-public.sh`](tools/check-public.sh) | 57 lines. Refuses to push if anything private is present. Wired as a `pre-push` hook |
| [`tools/kontor`](tools/kontor) | the profile switcher above, and the local-first guard |
| [`tools/distribute_*.sh`](tools/) | push generated config and the shared manifest into every branch |
| [`tools/census.sh`](tools/census.sh) | the numbers in this README, with the definition it used for each |
| [`evals/`](evals/) | the task set, the runner, the comparison, and a coverage report |
| [`evals/inspect_port/`](evals/inspect_port/) | the same tasks under [Inspect AI](https://inspect.aisi.org.uk/), with a written opinion |
| [`templates/`](templates/) | skeletons for a new branch |
| [`docs/`](docs/) | the conventions, and why each one exists |

Configuration — which branches exist, which are local-first, which model each profile implies — lives in `~/.config/kontor/`, outside every repository. The scripts are generic; the lists they act on are yours.

## Three things that cost something to learn

**A check reports success over a population it defined itself.** A distribution script had a `--check` mode that said *all copies match* for months. Its list of targets held three branches; sixteen repositories carried the file. The thirteen it had never heard of sat three versions behind. → [`docs/lessons.md`](docs/lessons.md)

**The gate that protects you can be empty.** `check-public.sh` scans against a private wordlist kept outside the repository. On 2026-09-18, preparing this repo for publication, the list turned out to have been empty since the day it was created — every "clean" it had printed was vacuous for that scan. It now takes branch names straight from the config, and refuses to run against an empty list at all.

**A verifier that fails a correct answer is a broken task.** A new eval task was written, approved, and failed a model that had answered it honestly — the check required a flag the prompt never asked for. The task was retired after one day and replaced by one sentence longer. Both are kept, in [`evals/retired/`](evals/retired/), because the pair is the clearest record here of a test being wrong about a right answer.

## The two rules

**1. No session writes into another branch's repository.** Not when the other session asks, not when it knows the target structure well, not when it would be faster. The reason is not tidiness: a branch that can be written to from outside has no reliable state, and every assumption built on that collapses quietly rather than loudly.

**2. Everything crossing a branch boundary goes through the pouch** — the `inbox/` folder in each repository. A session with something for another branch writes a file there; the receiving session reads it, acts, and moves it to `inbox/processed/`.

Direct session-to-session messaging exists and is useful for conversation, but it is not the pouch. On two occasions four sessions sent work by message to a session nobody was reading. Resent as files, the same material arrived. **A message is a conversation, a file is a delivery.**

There is one sanctioned exception to rule 1, scoped narrowly by argument rather than convenience: generated files with exactly one correct location may be distributed. [`docs/architecture.md`](docs/architecture.md) has the wording and how it was arrived at.

## Getting started

[`docs/adopting.md`](docs/adopting.md) is the five-step path: clone this, create your branch repositories as siblings with no shared git history, seed them from `templates/`, write your own config in `~/.config/kontor/`, run the distributors. The rest of [`docs/`](docs/) is the reasoning: [`architecture`](docs/architecture.md), [`pouch`](docs/pouch.md), [`conventions`](docs/conventions.md), [`fallback`](docs/fallback.md), [`choosing-a-model`](docs/choosing-a-model.md), [`lessons`](docs/lessons.md), [`roadmap`](docs/roadmap.md).

## What this is not

Not a framework, not a product, and not enforced. Rule 1 is not a sandbox — an agent that decides to write elsewhere can. The value is in the conventions and the failures behind them, not in the code, which is small.

Not a general answer to which model to use. [`evals/coverage.py`](evals/coverage.py) reports, per task profile, whether the model the config assigns is *evidenced* on that profile's tasks or merely assumed. As of today two of four profiles report **estimate** — which is the honest state, and the reason the tool prints it that way rather than averaging over it.

Not the contents of eighteen repositories. None of them are here, and none ever will be — not in a file, not in a filename, not in the history.

## The name

A *Kontor* was a trading house's foreign branch — Bergen, Bruges, Novgorod, the London Steelyard. Each did its own work, kept its own books, and corresponded with the others by letter, because it could not simply walk into their offices.

---

*Eighteen repositories, 3,868 commits, earliest 2025-05-21; 713 pouch messages delivered, 518 of them acted on and filed. Numbers as of 18 September 2026 — reproduce them with [`tools/census.sh`](tools/census.sh), which prints the definition it used for each.*
