# Desktop drafts — the third channel

Two channels are already documented: the pouch (`inbox/`, branch-to-branch, see [`pouch.md`](pouch.md)) and direct session messaging, which exists and is useful but is explicitly *not* the pouch — see ["a message is a conversation, a file is a delivery"](pouch.md#a-message-is-a-conversation-a-file-is-a-delivery). A third channel has existed for weeks without being named anywhere: a folder on the operator's own desktop, outside every repository, where sessions leave drafts of outbound correspondence.

## What it is

`~/Desktop/_Offen_Entwuerfe/` — one subfolder per recipient. Each holds drafts of things addressed to people outside the system entirely: letters, emails, applications, forms. State: *finished enough to review, not yet sent.* Each recipient folder carries its own register, `00_LIESMICH.txt`, with sections for what was finished today, what's still open, what's parked, what's waiting on a reply, and any dates that matter.

Nothing about *which* recipients exist belongs in this repository — same reasoning as the absence of a branch roster in [the README](../README.md#branch-names): a list of plausible recipients says almost exactly what the real ones would.

## Why this is Kontor's business even though it is not a repository

1. **It is an outbox with the direction reversed.** The pouch carries branch-to-branch. This carries operator-to-world, and a session writing into it is drafting *for* the operator, not addressing another branch. That role had no name anywhere a session could find it.
2. **Sessions find it by accident, not by knowing.** A session without this context, needing somewhere to put a finished draft, has no way to know the folder exists — it either invents a location inside its own branch or drops the file loose on the Desktop.
3. **It overlaps with existing responsibilities on purpose.** Once a draft is sent, the record of having sent it belongs in whichever branch owns that relationship, and is kept there. The draft itself stays on the Desktop only until it goes out.

   > **Draft here, record of sending there.** The separation is deliberate, not an oversight, and it should read like a rule rather than be rediscovered each time.

## Before adding anything

Read `00_LIESMICH.txt` in the recipient's folder first. If the folder doesn't exist yet, that is itself informative — check with the operator before creating one, rather than guessing at a recipient name.

## Once something is actually sent

Two branches arrived at the same rule independently before either of them wrote it down: once a draft has gone out, its text is copied into whichever branch owns that relationship, named `YYYY-MM-DD_GESENDET_<what it was>.<ext>` (an optional matching `_QUELLE.txt` may hold the rationale), and the recipient's Desktop folder is **deleted**, not left marked done. A folder still sitting there is a claim that something is still open.

[`tools/archive-sent.sh`](../tools/archive-sent.sh) does the mechanical half of that — copy with the date prefix, skip rather than overwrite if a copy already exists there, delete the drafts folder. It does not decide which repository or which category a piece of correspondence belongs to, and it does not touch the register; both stay judgement calls for the session:

```
tools/archive-sent.sh <draft-dir> <archive-dir>
```

---
← [README](../README.md) · [The pouch](pouch.md)
