# The pouch

Every branch has an `inbox/`. A session with something for another branch writes a file there. The receiving session reads it, acts, and moves it to `inbox/processed/`.

That is the whole protocol. What follows is why it is a file and not a message.

## A message is a conversation, a file is a delivery

Direct session-to-session messaging exists and is useful. It is not the pouch.

On two occasions, four sessions sent work by message to a session that was not the one in use: a deadline warning, a status report, a note for an appointment, and a question about a contact. All four went to a session nobody was reading. When the same material was resent as a file in the receiving branch's `inbox/`, it arrived.

> **If losing it would cost something, write the file.**

The distinction is not about reliability of transport. A message addresses *a session*, which may end, be replaced, or never be read. A file addresses *a branch*, which persists.

## Format

```markdown
**Von:** <sending branch>
**An:** <receiving branch>
**Datum:** <YYYY-MM-DD>
**Betreff:** <one line>
**Erledigt:** [ ]

---

<body>
```

Four conventions make it work:

- **The subject line is a claim, not a topic.** "Config distributed, three branches missing" rather than "config".
- **`Erledigt` is checked by the receiver**, never the sender.
- **Processed means processed.** A file moves to `processed/` when it has been acted on, not when it has been read.
- **Filenames are dated and descriptive**, because a directory listing is the index.

## What the pouch is not for

- **Not for content that belongs in the other branch.** Send the note; let the receiving session place the file. In at least one branch, placing *is* the work — see [`conventions.md`](conventions.md).
- **Not for work you could do yourself in your own branch.**
- **Not as a way around rule 1.** Writing a file into another branch's `inbox/` is the permitted act. Writing anywhere else in it is not.

## A failure worth knowing about

An intake folder collecting replies from eleven branches was populated by moving files into it. Two files had the same name; the second silently replaced the first, and the reply that was lost was the newer and better one. It was noticed only because the sending branch had left a separate note saying which version to use.

> **A move into a collection folder is not a copy, it is a replacement.** Check what is already
> there, or refuse to overwrite.

---
← [README](../README.md) · [Architecture](architecture.md)
