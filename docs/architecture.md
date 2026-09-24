# Architecture

A **branch** is one git repository with one agent session and one domain. Eighteen of them on one laptop, as of the last [`census.sh`](../tools/census.sh) — that script is the authority on the number, not this sentence. They are not folders in a project; they are separate establishments that write to each other.

## The two rules

### 1. No session writes into another branch's repository

Not when the other session asks. Not when it knows the target structure well. Not when it would obviously be faster.

The reason is not tidiness. **A branch that can be written to from outside has no reliable state** — its session can no longer assume that what it last wrote is what is there, and every assumption built on that collapses quietly rather than loudly.

### 2. Everything that crosses branches goes through the pouch

The `inbox/` folder in each repository. See [`pouch.md`](pouch.md).

## The one sanctioned exception, and how it was scoped

Some files are generated centrally and must exist identically in every branch — the manifest that maps the system, and the per-branch tool configuration. Distributing them means writing into other repositories, which rule 1 forbids.

The exception is narrow and was made narrower by argument rather than convenience:

> The operator directs the distribution; a session may execute it. The exception covers **generated
> files with exactly one correct location** and nothing else.

**The wording was rewritten once, under pressure.** The original rule said the *act* of distribution belonged to the operator and a session must never run it. In practice the operator asked and a session ran it, three times in one day, and the rule became a small negotiation each time instead of protecting anything. **A rule set aside by agreement whenever it comes up is not a boundary; it is friction.** So the boundary was moved to where it actually was.

The test for whether something qualifies came from the branch with the strictest local rule:

> **A generated file with exactly one correct location is not content. Content is whatever requires
> a judgement about where it goes.**

## Hierarchy and chronology

One branch had carried an absolute clause — *no exceptions* — since long before the general rule existed for an exception to attach to. It was read for months as evidence that this branch was stricter than the others. It was not: it was simply written first. An absolute clause has to say whether it means *stricter* or merely *older*.

There is one rule, it applies to every branch equally, and the branch where it was first written down has no special status.

## Instance and system

This repository is the system. The lists it operates on — which branches exist, which are local-first, which are read-only — are **instance data** and live in `~/.config/kontor/`, outside every repository. See [`../tools/kontor.conf.example`](../tools/kontor.conf.example).

A public repository that is a *sanitised copy* of a private one holds two copies of every decision and drifts forever. A public repository that **is** the system, configured by a private file, has nothing to sync.

The same system has been bitten three times by exactly the copy-and-drift failure it now avoids — see [`lessons.md`](lessons.md).

---
← [README](../README.md) · [The pouch](pouch.md) · [Conventions](conventions.md)
