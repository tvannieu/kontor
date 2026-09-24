# processed

Where a pouch message goes once this branch has **acted** on it — not once it
has been read. The folder exists to hold that distinction: a message
read and not acted on is still outstanding, and leaving it in `inbox/` is what
keeps it visible.

This folder is empty in the published repository.

Real pouch messages arrive **from the other branches**. They are written by a
session that knows its own repository, its own correspondents and its own
subject matter, and they name all three — which is what makes them useful to
the branch receiving them, and unpublishable here.

Eight of them were committed to this repository and removed again on
2026-09-20, history included. They had been carrying organisation names, private
surnames and paths naming private matters through every
`clean` the publication gate printed, because `tools/check-public.sh` excluded
`inbox/` from its scan — the one directory whose contents come from somewhere
else. The exclusion is gone. See [`docs/lessons.md`](../../docs/lessons.md).

If you adopt Kontor, expect the same of your own instance: `inbox/` will be the
most private directory in any branch that has a public repository. Scan it
first, not last.

---
← [inbox](../README.md) · [The pouch](../../docs/pouch.md)
