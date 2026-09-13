# Kontor

*A system for running many agent branches on one machine without letting them into each other.*

---

Twenty repositories on one laptop, 3,580 commits, one agent session each — and not one of them
can write into another. It was built while running legal, medical, financial and research threads
in parallel, where the cost of one contaminating another was high, and the whole architecture
follows from that single constraint: **a branch that can be written to from outside has no
reliable state.** Everything crossing a boundary goes through a file in the receiving repository's
`inbox/`; 669 such messages have been delivered so far. What is here is the infrastructure — the
conventions, the scripts that distribute generated configuration to every branch, the runbook for
when the subscription runs out and a local model takes over, and a fixed evaluation suite for
deciding which model is safe to open a given repository with. None of the contents of those
repositories are here, and none of them ever will be.

*Numbers as of 13 September 2026. Reproduce them with [`tools/census.sh`](tools/census.sh) —
it prints the definition it used for each.*

---

## The name

A **Kontor** was a trading house's foreign branch — Bergen, Bruges, Novgorod, the London
Steelyard. Each one did its own work, kept its own books, and corresponded with the others by
letter, because it could not simply walk into their offices.

That is the arrangement. The branches are not folders in one project. They are separate
establishments that write to each other.

---

## The two rules

Everything else is convenience. These two are constitutional.

### 1. No session writes into another branch's repository

This holds even when the other session asks, even when the writing session knows the target
structure well, and even when it would obviously be faster.

### 2. Everything that crosses branches goes through the pouch

**The pouch** is the `inbox/` folder in each repository. A session with something for another
branch writes a file there. The receiving session reads it, acts, and moves it to
`inbox/processed/`.

Direct session-to-session messaging exists and is useful for conversation. **It is not the pouch.**
On two occasions, four sessions sent work by message to a session that was not the one in use. All
four went to a session nobody was reading. When the same material was resent as a file, it arrived.

> **A message is a conversation, a file is a delivery.**

If losing it would cost something, write the file.

Details: [`docs/architecture.md`](docs/architecture.md) · [`docs/pouch.md`](docs/pouch.md)

---

## Branch names

Branch names in this repository are **role names** — `counsel`, `ledger`, `journal`,
`applications`, `devotional`, `framework`, `benchmarks`, `thesis`, `kitchen`. The real ones are
domain-specific and stay private.

This is not decoration. The classification below is a list of which branches may not reach a
hosted model, and a list like that, published under a real name, says a great deal about a life
without a single sentence of content. The architecture does not depend on the names.

---

## What is here

| | |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | branches, the two rules, and the one sanctioned exception to the first |
| [`docs/pouch.md`](docs/pouch.md) | the cross-branch message protocol |
| [`docs/conventions.md`](docs/conventions.md) | shared style rules, and what each kind of branch does differently |
| [`docs/fallback.md`](docs/fallback.md) | what happens when the subscription runs out: local-first defaults, providers, and how to prove the boundary holds |
| [`docs/lessons.md`](docs/lessons.md) | the failures. The most useful file here |
| [`tools/`](tools/) | the distribution scripts, the census, and the gate that refuses to publish |
| [`templates/`](templates/) | skeletons for a new branch |
| [`evals/`](evals/) | a fixed task set for deciding which model to trust with which branch |

---

## Configuration lives outside the repository

The scripts here are generic. The lists they act on — which branches exist, which are local-first,
which are read-only — live in `~/.config/kontor/branches.conf`, outside every repository.
[`tools/kontor.conf.example`](tools/kontor.conf.example) shows the shape.

🔑 The same applies, more strictly, to the wordlist used by
[`tools/check-public.sh`](tools/check-public.sh), which refuses to publish if anything private is
present. **That list is not in this repository and must never be.** A public file enumerating the
names you are protecting publishes the names, permanently, in git history, in the one place you
are inviting people to read. The script ships the mechanism and fails closed when the list is
absent.

---

## Status

Early. The conventions and the fallback are in daily use and have been for months; the evaluation
suite is days old and has more tasks than results. [`docs/choosing-a-model.md`](docs/choosing-a-model.md)
says which parts of it are measured and which are still guesswork, rather than pretending the
question is settled.

This repository was assembled using the protocol it documents, including the request that produced
its own contents.
