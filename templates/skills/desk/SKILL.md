---
name: desk
description: Use whenever drafting correspondence for the operator to send (an email, letter, form, message) or preparing material for an upcoming appointment. Covers where it goes, what the draft must contain, the register, and what happens once it is sent or the appointment has happened.
---

# The desk

The convention is `$KONTOR_ROOT/kontor/docs/outbox.md`. **Read it before placing anything**;
this file is only the trigger and the checklist, and where the two disagree the document wins.

Before:
- Read the register, `00_README.txt` at the root of the desk.
- Put the work in the counterpart's folder. If no folder exists for them yet, ask before
  creating one.

The draft:
- Recipient address and subject as header lines at the top, even if the body repeats them.
- Attachments copied into the same folder, not referenced by path. Keep the folder flat.

In the same step:
- Write or update the counterpart's register entry.

Afterwards:
- Sent correspondence: `$KONTOR_ROOT/kontor/tools/archive-sent.sh <desk>/<counterpart>
  <branch>/<where-sent-post-lives>`, then remove the register entry.
- Preparation: copy what is worth keeping into the owning branch by hand, then delete the
  folder and its entry.

Never leave a folder marked done. The folder disappearing is the record that it is done.
