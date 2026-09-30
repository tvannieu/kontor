# templates

Skeletons for a new branch. Copy into the new repository and fill in the angle brackets;
nothing here is meant to survive unedited.

| | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | the branch's working guidelines, and the single source of truth for them |
| [`AGENTS.md`](AGENTS.md) | a short pointer to `CLAUDE.md`, deliberately not a second copy |
| [`pouch-message.md`](pouch-message.md) | the shape of a message to another branch |
| [`TOMBSTONE.md`](TOMBSTONE.md) | the shape of a retirement note, for when something stops being used |
| [`skills/desk/SKILL.md`](skills/desk/SKILL.md) | a Claude Code skill that loads the desk convention whenever a session drafts post or prepares an appointment. Install it once at user level (`~/.claude/skills/desk/`), not per branch: it points at `docs/outbox.md` rather than restating it |

The rules that hold across every branch are linked from these files, not copied into
them. Copying is how the two drift apart — see [`../docs/lessons.md`](../docs/lessons.md).

---
← [README](../README.md) · [Adopting](../docs/adopting.md)
