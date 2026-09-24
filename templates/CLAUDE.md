# CLAUDE.md — <Branch>

The full working guidelines for this repository. Model-agnostic despite the filename — every agent harness in use here reads it the same way. `AGENTS.md` beside this file is a short pointer to it, not a second copy.

This repository is one branch in the kontor system: <one sentence — what this branch is for>. The rules that hold across every branch are not restated here; restating them is exactly the kind of duplication that drifts. They live in kontor itself, in the sibling directory `kontor/` — `$KONTOR_ROOT` below is the directory holding every branch, defined in `~/.config/kontor/branches.conf`; if you cannot read that, the paths still resolve from one level above this repository:

- `$KONTOR_ROOT/kontor/docs/architecture.md` — the two rules, and the one sanctioned exception to the first
- `$KONTOR_ROOT/kontor/docs/pouch.md` — the cross-branch message protocol
- `$KONTOR_ROOT/kontor/docs/conventions.md` — shared style, and what other branches independently arrived at

This file only adds what is specific to *this* branch.

## If you read nothing else

- **No session writes into another branch's repository.** To reach one, put a file in its `inbox/`.
- **This branch is <local-first / not local-first>.** <One line on what that means for the default model — see `$KONTOR_ROOT/kontor/docs/fallback.md` if unsure what the distinction does.>
- <Three to five rules specific to this branch — the ones that would cause irreversible damage if skipped. This is the part a generic template cannot write for you.>

## What this branch is

<A paragraph or two: the domain, what "done" looks like here, anything a session needs to know before doing its first piece of real work.>

## Conventions specific to this branch

<Whatever this branch has learned about itself. `conventions.md`'s collected rules are a starting point to check against, not a checklist to copy — several branches arrived at the same class of rule independently, which is worth knowing before reinventing it, but the point was that each one stated it in its own words, close to the failure that produced it.>

---
← [AGENTS.md](AGENTS.md) · `REPO_MANIFEST.md` (distributed, not in git)
