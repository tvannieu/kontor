# CLAUDE.md — Kontor

The full working guidelines for this repository, and the single source of
truth. [`AGENTS.md`](AGENTS.md) beside it is a short pointer here, never a
second copy.

**Why both.** The filename is an accident of tooling, not a claim about the
content: the work was done with Claude Code, which loads a file of this name
automatically, while `AGENTS.md` is the vendor-neutral name other harnesses
look for. Nothing in the conventions below depends on which model reads them —
that is the same principle as the profile switcher and the eval suite, which
exist so that one model can be swapped for another without rewriting the
documentation around it. Whichever harness a session arrives in, it should
reach the same text, and that text names no model.

This repository is the **system**: the conventions, scripts and documentation that the branches around it follow. It is **destined to be public** and currently private while it is written.

`REPO_MANIFEST.md`, when it is beside this file, is the map of the whole arrangement — generated and distributed, never committed, so a fresh clone does not have it. [`docs/adopting.md`](docs/adopting.md) says where it comes from.

## What makes this branch different from every other

Everything here is written for a stranger. No instance data, no real branch names, no content from any other branch — not as an example, not in a filename, not in a quotation.

## If you read nothing else

- **Configuration is not system.** Real branch names, classifications and the deny-list live in `~/.config/kontor/`, outside every repository. Never move them in here to make something easier.
- **Never `git clone` from a private branch, never add a private remote.** This repository must share no commit with any other. `tools/check-public.sh` checks for it; do not make it necessary.
- **Run `tools/check-public.sh` before every push**, and never with `--no-verify`. It fails closed when the deny-list is missing, and a scan that cannot run counts as a failure, not a pass.
- **Numbers in the documentation come from `tools/census.sh`**, quoted with the date. Never from memory, and never rounded up.
- **Write only in this branch.** To reach another, put a file in its `inbox/`.
- **Nothing here is published until Thomas has read the finished text.** Two sessions made that a condition of contributing, independently. It applies to all of it.

---
← [README](README.md) · [Adopting](docs/adopting.md)
