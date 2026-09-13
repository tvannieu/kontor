# Lessons

The failures. This is the most useful file here, and it is the one most systems omit.

One shape recurs. It is worth stating before the instances, because the instances are otherwise
just a list of small mistakes:

> **A mechanism reports success over a population it defined itself, and nobody checks the
> definition.**

Every item below is that, wearing different clothes.

---

## The distribution script that covered three branches of sixteen

A script copied a generated file from its canonical location into every other branch, and had a
`--check` mode that reported drift. `--check` said *all copies match the canonical file*, truthfully,
for months.

Its list of target branches held **three names. Sixteen repositories carried the file.** Thirteen
were never written to and sat three versions behind while the canonical one moved on. No copy
anywhere carried the generated-file header the script emits, which means it had in fact never
written a single one.

**The drift it existed to prevent was accumulating underneath it, invisibly, because the check only
ever looked at the three it knew about.**

---

## The claim with a file-and-line citation that was still wrong

A design document stated that a tool read three specific instruction files "by those exact names,
at the repository root", cited to `tool.py:77`.

It read them from the **current working directory**, not the repository root — so running it from a
subfolder gave it no context at all, silently. And the second half of the claim was never true in
any form: the scan was `sorted(glob("*.md"))[:5]`, non-recursive and alphabetical, so as the folder
grew it saw only the *oldest* five and never a new arrival. Every file was truncated at 4,000
characters, so the model never reached the rules the document was arguing about.

The conclusion drawn from the claim was correct. The reason was not.

> **The conclusion was right and the reason was wrong, which is the more dangerous combination —
> the claim carried a file-and-line reference, and the reference is what made it look checked.**

---

## The archive that was five files and was one hundred and eleven

A folder of finished material was to be deleted. The estimate carried into that afternoon, from
the same session's memory of its own earlier cleanup, was **five leftover files**. It held **111**,
and **27 existed in no repository at all** — including both receipts proving that a submission had
arrived, for a matter that was blocked on exactly that question.

The rest of that package *was* filed. Only the receipts were not.

Four rules came out of it:

1. **A receipt is part of the sending.** Marking something sent is not complete until the
   acknowledgement sits beside it.
2. **Folder names are not evidence.** One folder was named *done*; it held the only copy of a
   document that was very much not. Judge a file by reading it.
3. **A living document needs a snapshot, not a home.** A file being added to daily should be
   copied, not moved — moving it breaks the habit that produces it.
4. **Distrust a session's memory of its own cleanup.** Five versus 111 was not a miscount. It was a
   recollection, and it erred in the comfortable direction.

*368 files were checked by hash. 262 were byte-identical duplicates and were deleted without loss.
The nine that mattered were found by reading, not by sorting.*

---

## The runbook that described a capability nobody had used

A fallback was configured so that a local model could take over when the hosted subscription ran
out. The model list populated, the wrapper printed its banner, the hosted path answered a test
question. A runbook was written describing a working fallback.

The operator then opened the tool and typed `test`. It returned **`404 page not found`**, twice.

Four faults were stacked behind that, each hidden by the one in front: a missing path segment in
the endpoint URL; a context window pinned so large the model could not load at all on the available
memory and thrashed instead; instruction files large enough to consume a fifth of the window before
a question was asked; and a token budget so small that the model's reasoning consumed it entirely
and returned empty content — a successful call that looks like a broken one.

Three green lights had been read as four.

> **A capability is not verified until it has produced its output once.**

---

## The gate that printed "clean" and an error in the same breath

A script was written to refuse publication if anything private was present. Its first run printed
`clean`, and above it, a `grep` error: a pattern had been assembled by stripping whitespace, which
also stripped the spaces *inside* a character class and left it malformed. That check never ran. The
script reported success anyway.

This happened **one hour** after the rule about checks and their populations was written down, in
the code written to enforce it.

> A scan that cannot run must fail, not pass.

It is now verified with a planted canary: the gate must block a file containing the things it
claims to catch, and pass once that file is removed. **A boundary you have never seen open is an
outage, not a boundary.**

---

## A retirement, and why the record of it is kept

An early tool was deleted rather than fixed. Its documentation was kept as a tombstone: what it
was, the six defects an audit found, why fixing them was still the wrong call, and what survived it.

The reasoning for not fixing it generalises: *the bugs were never the problem. Fix all six and it is
still a single-turn chat that cannot open a file.*

> **Deleting the record is how the reasoning gets lost and the thing gets rebuilt.**

A retirement note is a convention worth having. See
[`../templates/TOMBSTONE.md`](../templates/TOMBSTONE.md).

---
← [README](../README.md) · [Conventions](conventions.md)
