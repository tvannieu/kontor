# Conventions

Two layers: rules every branch follows, and rules each branch invented for itself.

Eleven branches were asked independently what conventions they had and which mistake produced each. They work on entirely unrelated things — a manuscript, a recipe collection, a benchmark suite, a set of running administrative matters — and they had **independently arrived at the same class of rule.**

> **Every one of them had built a mechanism to stop a record from quietly drifting away from
> reality.**

Nobody coordinated that. It emerged because the same failure kept happening in eleven different shapes.

---

## Shared style

Inherited across all branches:

- **No emojis** in markdown or code unless asked for
- Minimal, technical, but aesthetic
- **Prefer editing an existing file to creating a new one**
- **No duplicate content** — cross-reference instead of copying
- Every directory has an index; landing anywhere should orient the reader
- Answer the question asked; no unnecessary elaboration

---

## The rules that stop a record from drifting

Collected from eleven branches. Each is quoted close to how its branch stated it, and each survives being moved to a repository about something else entirely — that was the test applied before it was written down.

### Against silence

> **An open-items register in which an item leaves the list by being decided, not by going quiet.**

> **Incoming notes are closed with their resolution, not just archived.**

> **A warning that is legitimate is triaged once and recorded as known-good, with the date and the
> reason. A warning list everyone has learned to ignore is worse than no warning list.**

### Against the record and the world parting company

> **Every inventory line carries the date it was last confirmed.** An inventory describes the past,
> not the present.

> **A full re-survey from direct observation supersedes accumulated incremental edits.**

> **Status lives in the filename, not inside the document.** A directory listing is an index; line
> 40 is not.

> **Sent means: has a receipt.**

> **A signed file is copied back into its folder immediately**, and whether the signature is
> actually there is checked mechanically, not by eye.

### Against corrections that hide

> **Corrections are appended, never applied silently.** A superseded passage is struck through and
> a guard comment says why.

> **Expected value and text change in the same commit, never one without the other.**

> **Results are committed, including the bad ones.** A discarded run is a dishonest record.

### Against inferring what could be looked up

> **Nothing is computed here, only cited.** Every number belongs to a branch that produced it.

> **Identifiers come from a source or not at all.** If the search finds nothing, the answer is
> "not found", not "does not exist".

> **Verify at source before adopting.** Nothing relayed by another session is acted on from the
> relay alone.

> **A distinction is enforced between what the branch decided and what it merely relayed.**

### Against checks that flatter themselves

> **Every check has a population it silently excludes. Write down which one.**

A duplicate check keyed on document references and invoice numbers found several duplicates. The rows with neither — typed in from a statement rather than from a document — were invisible to it, and there were more of them.

It travels further than anything else here, and it names the shape that [`lessons.md`](lessons.md) records over and over: a check that reports success over a population it defined itself.

### Against automating the part that is the work

One branch admits nothing except through an intake folder, where a session reads each item and turns it into something new before filing it.

> **Placing is the work.** An automated placer would file correctly and produce nothing: the rule
> protects the interval between arrival and filing, the only place judgement happens. **It would
> measure as an improvement and leave the tree intact and empty.**

Its own limit, which is also the test for the distribution exception in [`architecture.md`](architecture.md): *a generated file with exactly one correct location is not content. Content is whatever requires a judgement about where it goes.*

---

## Instruction files

Three files at the root of every branch. Agent harnesses resolve them **by name, relative to the repository root**, before the first prompt. Moving them into a subfolder breaks nothing visibly — a session simply runs without the repository's rules, and nobody is told.

| File | Role |
|---|---|
| `CLAUDE.md` | **Canonical.** The branch's full working guidelines. Model-agnostic despite the name. |
| `AGENTS.md` | A short pointer to `CLAUDE.md` plus a few rules that prevent irreversible damage. |
| `REPO_MANIFEST.md` | The map. Distributed, not linked — an identical copy in each branch. |

**Why `AGENTS.md` is a pointer and not a copy.** It began as a full duplicate of `CLAUDE.md`. Neither file mentioned the other existed, so the first edit to either would have diverged them silently. What settled it was a measurement rather than taste: some agent tools load **both** by name, so a branch was spending roughly 7,000 tokens saying the same thing twice before a question was asked — a fifth of a local model's context window. The pointer keeps a damage-prevention block rather than being bare, because some harnesses inject one file without reliably opening a second.

---
← [README](../README.md) · [Architecture](architecture.md) · [Lessons](lessons.md)
