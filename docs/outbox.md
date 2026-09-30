# The desk — a third channel

Two channels carry traffic inside the system: the pouch (`inbox/`, branch to branch,
see [`pouch.md`](pouch.md)) and direct session messaging, which is useful for
conversation and is explicitly not the pouch. Neither carries anything *out*, and
neither holds what the operator has to act on next.

The desk is the third: one place, outside every repository, that holds what the operator
has to act on or walk into next — drafts of correspondence to people outside the system
(letters, emails, applications, forms), things to sign, and preparation for an upcoming
appointment. State: finished enough to use, not yet done.

It began as an outbox for drafts only. Preparation started landing on it because it has
the same lifecycle — made by a session for the operator, used once, then gone — and the
rules carry over unchanged.

## Why it belongs to kontor rather than to a branch

**It is the pouch with the direction reversed.** The pouch carries branch to branch.
This carries session to operator, and on to the world: a session writing into it is
working *for* the operator rather than addressing another branch. That role has no other
name anywhere a session can find it.

**A session cannot guess the location.** Without somewhere agreed, a session that has
just finished a draft either invents a path inside its own branch — where the recipient
has nothing to do with the branch's subject — or drops the file loose and it is lost.

**One place, not one per branch.** Correspondence with a given person often touches
several branches. Filing the draft by branch means deciding which one owns a letter
before it has been sent, which is a decision nobody can make correctly and everybody has
to make again next time.

## The shape

- **One subfolder per counterpart** — the person a letter goes to, or the appointment a
  preparation is for — not per branch or per topic.
- **One register at the root**, `00_README.txt`, with one entry per folder: what is open,
  what is parked, what is waiting on a reply, and any dates that matter. It shows the
  current state only, never a history — an entry leaves when its folder does. Something
  deliberately held back is marked "locked until <date>", not left looking open.
- **The session that places something on the desk writes its register entry**, in the
  same step. The register belongs to the operator, not to kontor or to any branch; a
  folder with no entry is a folder nobody will find. Read the register before adding
  anything: if a counterpart's folder does not exist yet, that is itself informative —
  ask before creating one rather than guessing at a name.
- **A draft carries its own header and its attachments.** Recipient address and subject
  stand as header lines at the top, even when the body names them too. Anything to be
  attached is copied into the same folder, not referenced by path: a copy can be dragged
  straight into the mail, a path has to be found first. If a file is too large to copy,
  say so beside the path. Keep the folder flat — see below.
- **Draft here, record there.** Once a letter has gone out, or an appointment has
  happened, whatever is worth keeping — the sent text, a reply, notes from the meeting —
  is copied into whichever branch owns that relationship, and the folder is deleted, not
  marked done. A folder still sitting there is a claim that something is still open.

That last rule was arrived at independently by two branches before either wrote it down.

A branch whose desk work is high-volume and short-lived — several items a day, each gone
within hours — may keep its own folder on the desk under its own written rules instead
of filling the register. The register is for what the operator has to find; a queue that
empties itself before anyone looks does not need an index.

No tool creates a folder or writes an entry. Each is one step, and the part that matters —
which counterpart, what the entry says — is a judgement. The one step that repeats
identically every time has a script, below. What sessions actually miss is not the steps
but the convention itself, so [`templates/skills/desk/`](../templates/skills/desk/SKILL.md)
holds a skill that makes a session read this document whenever it starts drafting.

## Where it lives

Anywhere outside every repository. It holds unsent post and preparation about named
people, so it is the last thing that should sit in something publishable.

A visible location works better than a tidy one — a desk you do not walk past is one you
forget to clear. `~/Desktop/_Open_Drafts/` is the default suggestion for that reason, and
is where this instance keeps it. Nothing in the tooling depends on the choice:
[`archive-sent.sh`](../tools/archive-sent.sh) takes both directories as arguments.

Which counterparts exist is instance data and appears nowhere in this repository — a list
of plausible names says nearly as much as the real ones.

## Once something is sent

```
tools/archive-sent.sh <desk-dir>/<counterpart> <branch>/<where-sent-post-lives>
```

It copies each file with a `YYYY-MM-DD_SENT_` prefix and removes the folder. It never
overwrites: an identical archived copy is skipped, and a different one keeps the whole
folder in place for a person to compare. It refuses a folder that contains a subfolder,
because it archives only top-level files and would otherwise delete the rest unread. It
does not decide which repository or which category the correspondence belongs to, and it
does not touch the register — removing the entry is a separate step, and both stay
judgement calls for the session.

Preparation is never "sent", so the script's prefix would be wrong for it: after the
appointment, copy what is worth keeping by hand, then delete the folder and its entry.

---
← [README](../README.md) · [The pouch](pouch.md) · [docs](README.md)
