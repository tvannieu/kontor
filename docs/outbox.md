# The outbox — a third channel

Two channels carry traffic inside the system: the pouch (`inbox/`, branch to branch,
see [`pouch.md`](pouch.md)) and direct session messaging, which is useful for
conversation and is explicitly not the pouch. Neither carries anything *out*.

The outbox is the third: one place, outside every repository, where sessions leave
drafts of correspondence addressed to people who are not part of the system at all —
letters, emails, applications, forms. State: finished enough to review, not yet sent.

## Why it belongs to kontor rather than to a branch

**It is an outbox with the direction reversed.** The pouch carries branch to branch.
This carries operator to world, and a session writing into it is drafting *for* the
operator rather than addressing another branch. That role has no other name anywhere a
session can find it.

**A session cannot guess the location.** Without somewhere agreed, a session that has
just finished a draft either invents a path inside its own branch — where the recipient
has nothing to do with the branch's subject — or drops the file loose and it is lost.

**One folder, not one per branch.** Correspondence with a given person often touches
several branches. Filing the draft by branch means deciding which one owns a letter
before it has been sent, which is a decision nobody can make correctly and everybody has
to make again next time.

## The shape

- **One subfolder per recipient**, not per branch or per topic.
- **A register in each**, `00_README.txt`, holding what is open, what is parked, what is
  waiting on a reply, and any dates that matter. Read it before adding anything: if a
  recipient folder does not exist yet, that is itself informative — ask before creating
  one rather than guessing at a name.
- **Draft here, record of sending there.** Once something has actually gone out, its text
  is copied into whichever branch owns that relationship and the recipient's outbox folder
  is deleted, not marked done. A folder still sitting there is a claim that something is
  still open.

That last rule was arrived at independently by two branches before either wrote it down.

## Where it lives

Anywhere outside every repository. It holds unsent post addressed to named people, so it
is the last thing that should sit in something publishable.

A visible location works better than a tidy one — an outbox you do not walk past is an
outbox you forget to empty. `~/Desktop/_Open_Drafts/` is the default suggestion for that
reason, and is where this instance keeps it. Nothing in the tooling depends on the choice:
[`archive-sent.sh`](../tools/archive-sent.sh) takes both directories as arguments.

Which recipients exist is instance data and appears nowhere in this repository — a list of
plausible names says nearly as much as the real ones.

## Once something is sent

```
tools/archive-sent.sh <outbox-dir>/<recipient> <branch>/<where-sent-post-lives>
```

It copies each file with a `YYYY-MM-DD_SENT_` prefix, skips rather than overwrites
anything already there, and removes the drafts folder. It does not decide which repository
or which category the correspondence belongs to, and it does not touch the register; both
stay judgement calls for the session.

---
← [README](../README.md) · [The pouch](pouch.md) · [docs](README.md)
