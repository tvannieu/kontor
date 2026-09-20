# AGENTS.md — Kontor

The full working guidelines for this repository live in **[`CLAUDE.md`](CLAUDE.md)**
in this same directory. Despite the filename it is model-agnostic — read it
first and follow it. It explains why both files exist.

`CLAUDE.md` is the single source of truth. This file is only a pointer, kept
short so the two cannot drift apart — and because some agent tools load both by
name, so a full copy here would send the same instructions twice before a
question is asked. It was such a copy until 2026-09-20: it called itself a
pointer and then restated every rule, which made it longer than the file it
pointed at.

## If you read nothing else

- **Write only in this repository.** To reach another branch, put a file in its `inbox/`.
- **Never `git clone` from a private branch, never add a private remote.**
- **Run `tools/check-public.sh` before every push**, never with `--no-verify`.
- **Nothing here is published until Thomas has read the finished text.**

---
← [CLAUDE.md](CLAUDE.md) · [README](README.md)
