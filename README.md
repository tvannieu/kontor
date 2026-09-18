# Kontor

*A system for running many agent branches on one machine without letting them into each other.*

---

Eighteen repositories on one laptop, 3,868 commits, one agent session each — and not one of them can write into another. It was built while running legal, medical, financial and research threads in parallel, where the cost of one contaminating another was high, and the whole architecture follows from that single constraint: **a branch that can be written to from outside has no reliable state.** Everything crossing a boundary goes through a file in the receiving repository's `inbox/`; 713 such messages have been delivered so far, 518 of them acted on and filed. What is here is the infrastructure — the conventions, the scripts that distribute generated configuration to every branch, the runbook for when the subscription runs out and a local model takes over, the gate that refuses to publish anything private, and a fixed evaluation suite for deciding which model to trust with which kind of work. None of the contents of those repositories are here, and none of them ever will be — not in a file, not in a filename, and not in the history.

*Numbers as of 18 September 2026. Reproduce them with [`tools/census.sh`](tools/census.sh) — it prints the definition it used for each.*

---

## The name

A **Kontor** was a trading house's foreign branch — Bergen, Bruges, Novgorod, the London Steelyard. Each one did its own work, kept its own books, and corresponded with the others by letter, because it could not simply walk into their offices.

That is the arrangement. The branches are not folders in one project. They are separate establishments that write to each other.

---

## The two rules

Everything else is convenience. These two are constitutional.

### 1. No session writes into another branch's repository

This holds even when the other session asks, even when the writing session knows the target structure well, and even when it would obviously be faster.

### 2. Everything that crosses branches goes through the pouch

**The pouch** is the `inbox/` folder in each repository. A session with something for another branch writes a file there. The receiving session reads it, acts, and moves it to `inbox/processed/`.

Direct session-to-session messaging exists and is useful for conversation. **It is not the pouch.** On two occasions, four sessions sent work by message to a session that was not the one in use. All four went to a session nobody was reading. When the same material was resent as a file, it arrived.

> **A message is a conversation, a file is a delivery.**

If losing it would cost something, write the file.

There is no enforcement behind either rule — no sandbox, no permission boundary. They are instructions in a file, trusted to a well-behaved agent and a person who is paying attention. Adopting Kontor means adopting that discipline; [`docs/adopting.md`](docs/adopting.md) says so plainly and walks the five steps.

Details: [`docs/architecture.md`](docs/architecture.md) · [`docs/pouch.md`](docs/pouch.md)

---

## Branch names

Branch names in this repository are placeholders. The real ones are domain-specific and stay private, and so is the list of which branches fall into which class.

This is not decoration, and role names are not enough on their own. A roster of plausible roles says almost exactly what the real names would: a reader infers the domains from the shape of the list, whether the label is the real directory name or a tactful synonym for it.

So there is no roster. What matters architecturally is the **criterion**, not the membership: a branch whose contents must not leave the machine defaults to a local model. Which branches those are is instance data, and instance data lives in the config.

---

## What is here

| | |
|---|---|
| [`docs/adopting.md`](docs/adopting.md) | the path from nothing to a working set of branches, in five steps |
| [`docs/architecture.md`](docs/architecture.md) | branches, the two rules, and the one sanctioned exception to the first |
| [`docs/pouch.md`](docs/pouch.md) | the cross-branch message protocol |
| [`docs/desktop-drafts.md`](docs/desktop-drafts.md) | the third channel: correspondence drafted for a person, not a branch |
| [`docs/conventions.md`](docs/conventions.md) | shared style rules, and the rules eleven branches arrived at independently |
| [`docs/fallback.md`](docs/fallback.md) | when the subscription runs out: local-first defaults, providers, and how to prove the boundary holds |
| [`docs/choosing-a-model.md`](docs/choosing-a-model.md) | which model to open a branch with — what is measured, what is still an estimate |
| [`docs/roadmap.md`](docs/roadmap.md) | what is next, in dependency order, and what got done on the way |
| [`docs/lessons.md`](docs/lessons.md) | the failures. The most useful file here |
| [`tools/`](tools/) | the distribution scripts, the census, the profile switcher, and the gate that refuses to publish |
| [`templates/`](templates/) | skeletons for a new branch: its two instruction files, a pouch message, a retirement note |
| [`evals/`](evals/) | a fixed task set, in German, for deciding which model to trust with which kind of work — see below |

### The evaluation suite

[`evals/`](evals/) holds ten live tasks (and one retired with its reasons), re-run unchanged against each new model at temperature zero, with every result committed — including the bad runs, because a discarded run is a dishonest record. Most of the tasks are ordinary; three deliberately have no determinable answer and measure whether a model says so or invents something plausible. That is the failure shape that matters: these systems do not fail with an error, they fail with a fluent wrong answer.

Around the tasks: [`run.py`](evals/run.py) runs them (hosted, local, or through an agent runner for the providers only it reaches) and records cost per call; [`report.py`](evals/report.py) puts the runs side by side; [`coverage.py`](evals/coverage.py) says, per task profile, whether the model your config assigns is *evidenced* on that profile's tasks or merely *assumed* — the mapping between what a branch may use and what has been shown to work. [`evals/inspect_port/`](evals/inspect_port/) is the same suite ported to Inspect AI, with [`NOTES.md`](evals/inspect_port/NOTES.md), an opinion formed by running it rather than reading about it: what the framework does well, where it hung a laptop, where its grader lost a correct verdict to markdown bold, and a judge calibration with the reasoning kept — because a calibration that stores only the percentage has thrown away the part you would act on.

---

## Configuration lives outside the repository

The scripts here are generic. The lists they act on — which branches exist, which are local-first, which are read-only, which model each task profile implies — live in `~/.config/kontor/`, outside every repository. [`tools/kontor.conf.example`](tools/kontor.conf.example) and [`tools/profiles.conf.example`](tools/profiles.conf.example) show the shape.

🔑 The same applies, more strictly, to what [`tools/check-public.sh`](tools/check-public.sh) scans for. **Neither the wordlist of private names nor the vocabulary of private matters is in this repository, and neither must ever be.** A public file enumerating the names you are protecting publishes the names, permanently, in git history, in the one place you are inviting people to read — and a list of the *kinds* of matter does the same. The script ships the mechanism and fails closed when either list is absent. It also takes every branch name straight from the config, so a name can never be missing from the list because nobody typed it twice; that was learned the hard way, and [`docs/lessons.md`](docs/lessons.md) is where such things go.

---

## Languages

The documentation is in English, written for a stranger. The evaluation suite — its tasks, its README, its result notes — is in German, and deliberately so: the private corpus these branches work on is German, and the failure the suite measures (a plausible wrong answer) is not language-neutral. Translating the tasks would measure a different thing.

---

## Status

The conventions, the distribution scripts and the fallback have been in daily use for months. The evaluation suite is younger and now has more to say: runs against local and hosted models, a port to a second framework with the differences written up, a calibration of the grader against human ratings, and a per-profile account of what is evidenced. The honest part is unchanged in kind — the model choice per branch is still an estimate for some profiles, and [`docs/choosing-a-model.md`](docs/choosing-a-model.md) says which, rather than pretending the question is settled. [`docs/roadmap.md`](docs/roadmap.md) says what comes next and why in that order.

This repository was assembled using the protocol it documents, including the request that produced its own contents.
