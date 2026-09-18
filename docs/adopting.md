# Adopting kontor

The path from nothing to a working set of branches, assembled once instead of left as five separate things a reader has to reconstruct from `architecture.md`, `pouch.md`, `conventions.md` and `fallback.md`. Nothing below is a new rule — every piece is already documented elsewhere and linked from here rather than restated.

## 1. Clone the system repo

`git clone https://github.com/tvannieu/kontor` — this step is the only one that involves kontor's own git history at all. Everything that follows is your own repositories and your own config.

## 2. Create the branch repos — as siblings, never as clones of kontor

Each domain (a project, a running matter, anything with its own state) gets its own ordinary, unrelated git repository, next to kontor, not inside it and not cloned from it.

> **Kontor must share no commit history with any branch.** `tools/check-public.sh` checks for exactly this, in one direction — see [`architecture.md`](architecture.md).

`KONTOR_ROOT` (from your own `~/.config/kontor/branches.conf`, see step 4) is the directory that holds them all as siblings — kontor included.

## 3. Seed each new branch from `templates/`

What's there and what it gives you:

| Template | Becomes |
|---|---|
| `templates/CLAUDE.md` | The branch's `CLAUDE.md` — placeholders for what's specific to this branch; the rules that hold everywhere are linked, not copied |
| `templates/AGENTS.md` | The branch's `AGENTS.md` — a pointer to `CLAUDE.md`, kept short on purpose, see `conventions.md`'s "why `AGENTS.md` is a pointer and not a copy" |
| `templates/pouch-message.md` | The shape of a pouch message, when this branch has something to send |
| `templates/TOMBSTONE.md` | The shape of a retirement note, for when something in this branch stops being used |

**`REPO_MANIFEST.md` is not templated, deliberately.** It's the one generated file every branch carries identically — written once, canonically, in whichever branch your config designates (`MANIFEST_SOURCE` in `tools/kontor.conf.example`), then distributed by script, never hand-seeded per branch. See `architecture.md`'s "one sanctioned exception."

## 4. Write your own instance config — outside every repository

None of this lives in git, anywhere:

- `~/.config/kontor/branches.conf` — which branches exist, which are local-first, which are read-only. `tools/kontor.conf.example` shows the shape.
- `~/.config/kontor/deny.txt` — the private wordlist `check-public.sh` refuses to run without. Never in a repository, for the reason the README gives: a public file enumerating the names you're protecting publishes the names.
- `~/.config/kontor/profiles.conf` — task-profile-to-model mapping, if you're using `tools/kontor` (see `choosing-a-model.md`).

## 5. Distribute, then work independently

`tools/distribute_manifest.sh` and `tools/distribute_crush_config.sh` push the generated files (the manifest, per-branch model config) out to every branch listed in your config. Run once after any change to the branch list; the operator directs it, a session may execute it — see `architecture.md`'s "how that wording was arrived at."

From here, each branch runs its own session, in its own directory, and never writes into another's.

## What this doesn't give you

No technical enforcement. Rule 1 — no session writes into another branch's repository — is an instruction in a file, not a sandbox boundary (`fallback.md`'s sandbox profile is the one place a real OS-level seal existed, and it was for the network boundary, not this one, and was removed deliberately). Adopting kontor means adopting the discipline these docs describe, not installing something that enforces it for you.

---
← [README](../README.md) · [Architecture](architecture.md) · [Roadmap](roadmap.md)
