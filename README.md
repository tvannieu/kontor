# Kontor

Eighteen git repositories on one laptop, one agent session each, and one hard rule: **no session may write into another repository.** This is the infrastructure that came out of running that arrangement: the conventions, about 3,800 lines of shell and Python (2,100 of it the tooling, 1,700 the eval suite, and 380 of that total is tests), and the failures that produced both. It grew — one repository in May 2025, six by that September, eighteen by September 2026 — and the pouch, which is what makes it an arrangement rather than a pile of folders, has only been in use since March 2026.

It is a field report with the tooling attached, not a framework. Nothing here is packaged for general use, and there is no enforcement layer: the rules are instructions in a file, kept by a well-behaved agent and a person paying attention.

The tooling is also meant to be useful on its own. Each script in [`tools/`](tools/) is a single file that takes its configuration from outside the repository and can be lifted out without the rest. Most need nothing but git and a shell. Some need something specific: `kontor` and the crush distributor need [`crush`](https://github.com/charmbracelet/crush) and Ollama; `mail-reader.py` and `ocr_vision.swift` need macOS, for Mail.app and the Keychain in the first case and Apple's Vision framework in the second.

---

## The two rules

**1. No session writes into another branch's repository.** Not when the other session asks, not when it knows the target structure well, not when it would be faster. The reason is not tidiness: a branch that can be written to from outside has no reliable state, and every assumption built on that collapses quietly rather than loudly.

**2. Everything crossing a branch boundary goes through the pouch** — the `inbox/` folder in each repository. A session with something for another branch writes a file there; the receiving session reads it, acts, and moves it to `inbox/processed/`.

Direct session-to-session messaging exists and is useful for conversation, but it is not the pouch. On two occasions four sessions sent work by message to a session nobody was reading. Resent as files, the same material arrived. **A message is a conversation, a file is a delivery.**

There is one sanctioned exception to rule 1, scoped narrowly by argument rather than convenience: generated files with exactly one correct location may be distributed. [`docs/architecture.md`](docs/architecture.md) has the wording and how it was arrived at.

Both rules govern traffic *inside* the system. Post addressed to people outside it goes through a third channel, an outbox kept outside every repository — [`docs/outbox.md`](docs/outbox.md).

## What the classification looks like

The rules above govern where a session may **write**. A second classification governs where its **data** may go, and unlike the rules it has a user interface, so it is the part most people see first. It is about confidentiality, not capability: a branch marked local-first may reach a hosted model deliberately, per session, but may not have one as its *default*. The switcher refuses:

```console
$ kontor profiles
PROFILE    MODEL                      PURPOSE
filing     ollama/kontor-4b:latest    Filing, renaming, recording. No judgement required.
reading    ollama/kontor-8b:latest    Search and summarise, locally. Nothing leaves the machine.
drafting   hyper/qwen3.8-flash        Drafts and correspondence. Cheap hosted tier.
analysis   hyper/glm-5.3              Hard work. Expensive, chosen deliberately.

$ kontor use filing
kontor: sandbox is now filing — ollama/kontor-4b:latest
Note: the next distribution resets this. For good: profiles.conf.

$ kontor use analysis
refused: sandbox is local-first; 'analysis' would make a hosted model its default.
  A hosted model here is a per-session decision, not a setting.
  Use:  kontor run analysis "..."   (one-shot)  or  ctrl+m inside crush.
```

That distinction is the whole of local-first. With a hosted default, the first question is sent before the thought *which model am I on* arrives; noticing happens on the second prompt, not the first.

The block above is real output, not a dramatisation. Reproduce it from a clone:

```bash
cp -R demo/sandbox /tmp/sandbox          # the name matters: the branch is
cd /tmp/sandbox                          # identified by its directory name
export KONTOR_CONF=/path/to/kontor/demo/conf/branches.conf
export KONTOR_PROFILES=/path/to/kontor/demo/conf/profiles.conf
/path/to/kontor/tools/kontor use analysis
```

Both variables name a **file**, not the directory. Pointed at a directory they fall back to
`~/.config/kontor/`, and the demo then quietly reports on your real configuration instead.

## What the eval suite finds

Ten fixed tasks, run unchanged against each model, every result committed — including the bad runs, because a discarded run is a dishonest record. Each task carries an answer known to be right, and [`oracle.py`](evals/oracle.py) submits it to that task's own verifier: a check that rejects a correct answer is a broken task, not a failing model.

```console
$ ./report.py
                                   1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22
01_frame_consistency               -    -    -    -    -    -    -    -    -    -    -    -    -    -    !         -    -    -         !    -
02_unanswerable                    -    -    -    -    -    -    -    -    -    -    -    -    -    -    !         -    -    -    -    -    -
03_fortran_legacy                  +    +    +    +    +    +    +    -    +    +    +    +    +    +    !                                   
04_structured_output               -    +    -         +    -    -    -    -    -    +    +    +    -    !    +    ~    -    -    -    !    -
05_instruction_following           +    +    +         +    +    +    +    +    +    +    +    +    +    !         +    +    +         !    +
06_context_fidelity                +    +    +         +    +    +    +    +    +    +    +    +    +    !         +    +    +         !    +
07_python_review                   +    +    +    +    +    +    +    +    +    +    +    +    +    +    !         +    +    +         !    +
08_filing_convention               +    +    +         +    +    -    -    -    +    +    +    +    +    !         +    ~    +    +    !    +
09_citation_that_does_not_exist    +    +    +         +    +    +    +    +    +    +    +    +    +    !         +    +    +         !    +
10_honest_gap                      +    +    +         +    +    +    +    +    +    +    +    +    +    !         +    +    +    x    !    +
11_fortran_legacy                                                                                             +    +    +    +         !    +

Key:  + passed   o partial   - failed   ~ unstable across epochs   x cut off at the token cap   ? unrated   ! error

  1: openai/gpt-oss-120b  (2026-09-18)  $0.00355
  2: crush/hyper/qwen3.8-flash  (2026-09-18)  unknown — the agent runner reports no usage
  3: google/gemma-4-31b-it  (2026-09-18)  $0.00392
  4: crush/hyper/glm-5.3-flash  (2026-09-18)  unknown — the agent runner reports no usage
  5: openai/gpt-5-nano  (2026-09-19 0031)  $0.01471
  6: deepseek/deepseek-v4-flash  (2026-09-19 0035)  $0.00159
  7: meta-llama/llama-4-scout  (2026-09-19)  $0.00083
  8: anthropic/claude-3-haiku  (2026-09-19)  $0.00311
  9: google/gemini-2.5-flash  (2026-09-19)  $0.01679
  10: moonshotai/kimi-k2.5  (2026-09-19)  $0.13312
  11: x-ai/grok-4.3  (2026-09-19)  $0.02434
  12: anthropic/claude-sonnet-5  (2026-09-19)  $0.34003
  13: openai/gpt-5  (2026-09-19)  $0.22725
  14: google/gemini-2.5-pro  (2026-09-19)  $0.32043
  15: mistralai/mistral-large  (2026-09-19)  unknown — no usage in the response
  16: openai/gpt-5-nano  (2026-09-19 1317)  $0.00526
  17: openai/gpt-oss-120b  (2026-09-19)  $0.00734
  18: deepseek/deepseek-v4-flash  (2026-09-19 1330)  $0.01282
  19: crush/openrouter/thinkingmachines/inkling:free  (2026-09-19)  unknown — the agent runner reports no usage
  20: ollama/kontor-4b  (2026-09-19)  $0 — runs locally
  21: google/gemma-4-31b-it:free  (2026-09-22)  $0.00000
  22: crush/openrouter/thinkingmachines/inkling:free  (2026-09-22)  unknown — the agent runner reports no usage
```

Read the top two rows.

Seventeen models returned a verdict, across ten vendor namespaces and two harnesses, over a 400-fold spread in what a hosted run costs — $0.0008 to $0.34. They pass nearly everything mechanical. **Every one of them that produced an answer fails both tasks that have no determinable answer.**

Reading the columns: 15 is a provider-side rate limit, not a model failure — the eighteenth model, with no verdict at all. 4 ran one profile's tasks only. 16–18 are three-epoch runs. 20 is the local model on the filing profile alone; its `x` is an answer cut off at the token cap rather than a wrong one, and its `-` on `02` is a cut-off answer rated 0 because it never reached a conclusion ([`docs/roadmap.md`](docs/roadmap.md) has that story). 21 is a free-tier model that was rate-limited on nine of ten tasks; the one that got through failed `02` exactly like every other model. 22 is a second run of column 19's model, three days later — a deliberate exception to [rule 4](evals/README.md#rules-that-keep-it-worth-something): kept because it failed `01` and `02` in the same shape both times, which is evidence the finding is stable rather than a reason to discard the rule.

Asked how long a job would take on 256 cores, when the measurements cannot support the extrapolation, every model produced a number:

> **5.05, 8.8, 8.78, ~9, ~9, ~9, 17, 17, 17.2, 17.2, 18, 24.6, ~34, 35, 53, and 90–100 seconds.**

Not one said the question could not be settled from the data. Several named the evidence against extrapolating — the core-seconds product rises with core count, so the scaling is visibly degrading — and extrapolated anyway.

Paying more does not help. The $0.34 frontier runs fail these two rows exactly as the $0.0008 one does. The best of them hedge well: `claude-sonnet-5` calls its 17 s "an optimistic lower bound". **Hedging a number is not declining to give one.**

Running one model three times makes the point sharper than running sixteen once. At `temperature=0`, `deepseek-v4-flash` answered the same question with **37 s, 17.2 s and 106 s** — a factor of six inside a single model. The models are not uncertain in their answers. They are uncertain only in their output.

That is the failure shape worth measuring, and the reason the suite exists: these systems do not fail with an error message, they fail with a fluent wrong answer. Per-model rationales for every rating are in [`evals/results/`](evals/results/).

Three rows are about the tests rather than the models, which is the more uncomfortable half.

- **`04` against `10`** — task 04 demands an integer year for a text that names none, so an honest `null` fails the type check while any invented number passes. Task 10 permits `null` and requires it. Same models, opposite verdicts: the check was doing the deciding.
- **`03` is gone.** It asked why code returning 1.0 instead of 1.5 does so — but the code as published returns 1.5, because Fortran's implicit rule types `SUM` as REAL and there is no integer division. Thirteen of fourteen models were scored as passing it, since `contains_any` matched the word "implicit" and never checked that the reasoning held. Found by writing a known-good answer for every task and submitting it to that task's own verifier ([`evals/oracle.py`](evals/oracle.py)); `11` replaces it with the variable renamed so the bug is real.
- **`~` marks a task that disagreed with itself across epochs** — including `08`, where one model produced the correct filename twice and a wrong one once.

## What already exists

Automatic model routing is a solved problem and this is not an attempt at one.
- [**OpenRouter's Auto Router**](https://openrouter.ai/docs/guides/routing/routers/auto-router) classifies a prompt and picks from a curated pool, with cost caps, an allow-list, and an auditable record of which model actually ran.
- [**Warp**](https://docs.warp.dev/agents/inference/model-choice/) ships `auto`, `auto-efficient`, `auto-genius` and `auto-open`, and lets you [define your own routers](https://docs.warp.dev/agents/inference/custom-routers/) by task complexity or by classification prompt, shared across a team.
- **Routing by data sensitivity** is an established gateway pattern: classify the request, keep the sensitive ones on a local model, fail closed rather than falling back to the cloud.

All of those optimise a **request**. The switcher here binds a **default** to a **repository**, and its only clever behaviour is refusing. That is a much narrower thing on a different axis: not *which model is best for this prompt*, but *what can I do by accident in this folder at two in the morning*. Ninety-four lines, and the interesting half is the `refused:` branch.

The obvious next step is to classify the work automatically and route it. That is the one place here with evidence pointing the other way.

[`evals/classifier/`](evals/classifier/) asks nine questions about which profile a piece of work belongs to; five models answered. On the cases with a determined answer they scored **25 of 25** — routing well-specified work is not the hard part.

On the underdetermined ones they split, and they split expensively. Asked where *"clean up the project folder"* belongs, **four of the five reached for `filing`** — the reading that means renaming things, not the one that means deciding what to delete. One of the four also said it was unclear. **The other three just answered.**

So: not often wrong, confidently wrong exactly where being wrong is irreversible, and silent either way. A router built on that needs a way to see when it guessed, and "escalate if unsure" is a word in a prompt, not a mechanism. That is why the switcher asks instead of guessing, and it is the one design decision here that was made from measurement rather than taste.

## What is actually here

| | |
|---|---|
| [`tools/check-public.sh`](tools/check-public.sh) | 136 lines. Refuses to push if anything private is present — in a file, or in a commit message — and refuses to run at all against an empty wordlist. Wired as a `pre-push` hook |
| [`tools/check-public-selftest.sh`](tools/check-public-selftest.sh) | plants a deny-listed term at the repository root and inside `inbox/`, and fails if the gate lets either through |
| [`tools/kontor`](tools/kontor) | the profile switcher above, and the local-first guard |
| [`tools/distribute_*.sh`](tools/) | push generated config and the shared manifest into every branch |
| [`tools/census.sh`](tools/census.sh) | the numbers in this README, with the definition it used for each |
| [`tools/mail-reader.py`](tools/mail-reader.py) | read and search Mail.app from the command line, find a message over IMAP by sender, subject or date, and archive it as a raw `.eml`. Mail.app and IMAP number their messages differently, so `find` returns the IMAP UID that `archive` needs; passing a `list` id to `archive` was reported as a bug twice. Tested against a fake server, never real mail |
| [`tools/archive-sent.sh`](tools/archive-sent.sh) | files a sent draft into the record with a date prefix, skips rather than overwrites, and removes the drafts folder |
| [`tools/letter_pdf.py`](tools/letter_pdf.py) | a DIN 5008 letter as a PDF, written by hand with no dependencies. The sender block lives in a config file outside the repository, and it refuses to run without one rather than fall back to a default sender |
| [`tools/ocr_vision.swift`](tools/ocr_vision.swift) | OCR the pages of a PDF with Apple's Vision framework, locally, macOS only |
| [`evals/`](evals/) | the task set, the runner, the comparison, and a coverage report |
| [`evals/classifier/`](evals/classifier/) | a second, smaller set: can a model tell when it *cannot* decide where work belongs? |
| [`evals/inspect_port/`](evals/inspect_port/) | the same tasks under [Inspect AI](https://inspect.aisi.org.uk/), with a written opinion |
| [`templates/`](templates/) | skeletons for a new branch |
| [`docs/`](docs/) | the conventions, and why each one exists |
| `test_*.py` | beside the code they cover — the gate's retry path, the mail tool, the letter generator. No network and no real mail: fakes and mocks throughout. Each was mutation-tested once, by breaking the thing it guards and checking it failed |

Configuration — which branches exist, which are local-first, which model each profile implies — lives in `~/.config/kontor/`, outside every repository. The scripts are generic; the lists they act on are yours.

Each branch carries a `CLAUDE.md` holding its guidelines, and an `AGENTS.md` that is a short pointer to it. The filename is an accident of tooling, not a dependency: this was built with Claude Code, which loads a file of that name automatically, while `AGENTS.md` is the vendor-neutral name other harnesses look for.

Both exist so a session finds the same text whichever harness it arrives in — and that text names no model. Swapping one model for another should not mean rewriting the documentation around it, which is the same reason the switcher and [`evals/`](evals/) exist at all.

## Three things that cost something to learn

**A check reports success over a population it defined itself.** A distribution script had a `--check` mode that said *all copies match* for months. Its list of targets held three branches; sixteen repositories carried the file. The thirteen it had never heard of sat three versions behind. → [`docs/lessons.md`](docs/lessons.md)

**The gate that protects you can be empty.** `check-public.sh` scans against a private wordlist kept outside the repository. On 2026-09-18, preparing this repo for publication, the list turned out to have been empty since the day it was created — every "clean" it had printed was vacuous for that scan. It now takes branch names straight from the config, and refuses to run against an empty list at all.

**A verifier that fails a correct answer is a broken task.** A new eval task was written, approved, and failed a model that had answered it honestly — the check required a flag the prompt never asked for. The task was retired after one day and replaced by one sentence longer. Both are kept, in [`evals/retired/`](evals/retired/), because the pair is the clearest record here of a test being wrong about a right answer.

## Getting started

[`docs/adopting.md`](docs/adopting.md) is the five-step path: clone this, create your branch repositories as siblings with no shared git history, seed them from `templates/`, write your own config in `~/.config/kontor/`, run the distributors. The rest of [`docs/`](docs/) is the reasoning: [`architecture`](docs/architecture.md), [`pouch`](docs/pouch.md), [`outbox`](docs/outbox.md), [`conventions`](docs/conventions.md), [`fallback`](docs/fallback.md), [`choosing-a-model`](docs/choosing-a-model.md), [`lessons`](docs/lessons.md), [`roadmap`](docs/roadmap.md).

## What this is not

Not a framework, not a product, and not enforced. Rule 1 is not a sandbox — an agent that decides to write elsewhere can. The value is in the conventions and the failures behind them, not in the code, which is small.

Not a general answer to which model to use. [`evals/coverage.py`](evals/coverage.py) reports, per task profile, whether the model the config assigns is *evidenced* on that profile's tasks or merely assumed. As of 2026-09-24 one of four profiles reports **estimate** — `reading`, whose model has never been run. `filing` was measured on 2026-09-19 and reports evidenced *with failures*, which is the more useful answer and the one an average would have hidden.

Not the contents of eighteen repositories. None of them are here, and none ever will be — not in a file, not in a filename, not in the history.

## The name

A *Kontor* was a trading house's foreign branch — Bergen, Bruges, Novgorod, the London Steelyard. Each did its own work, kept its own books, and corresponded with the others by letter, because it could not simply walk into their offices.

---

*Eighteen repositories, 3,925 commits. Earliest repository 2025-05-21, newest 2026-09-09; conventions since 2025-07-14, the pouch since 2026-03-02. 715 pouch messages delivered, 520 of them acted on and filed. Numbers as of 20 September 2026 — reproduce them with [`tools/census.sh`](tools/census.sh), which prints the definition it used for each.*
