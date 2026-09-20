# AGENTS.md — <Branch>

The full working guidelines for this repository live in **`CLAUDE.md`** in this same directory. Despite the filename it is model-agnostic — read it first and follow it. `REPO_MANIFEST.md`, when it is beside it, is the map of the whole system — generated and distributed into each branch, never committed, so a fresh clone does not have one.

`CLAUDE.md` is the single source of truth. This file is only a pointer, kept short so the two cannot drift apart — and because some agent tools load both by name, so a full copy here would send the same instructions twice before a question is asked.

## If you read nothing else

- **Write only in this repository.** To reach another branch, put a file in its `inbox/`.
- **Ask before anything destructive or ambiguous.** Look at what you are about to remove first.
- <three to five rules specific to this branch that prevent irreversible damage>
- **Never commit a credential**, and never commit the agent runner's session database.

---
← [CLAUDE.md](CLAUDE.md) · `REPO_MANIFEST.md` (distributed, not in git)
