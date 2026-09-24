# kontor-eval — rating and reporting contract

> Depth for the eval pipeline. The runner and task files are described in
> `../README.md` and the task set in `tasks/`; this file is only the parts a
> future session needs to rate results or extend the pipeline without
> re-learning them from scratch.

## Manual ratings must be numeric

`report.py` classifies a manual task's mark from `manual.rating` alone:

```
{1: "+", 0.5: "o", 0: "-"}
```

Anything else — a word like `"passed"` or `"failed"`, or any
non-numeric value — falls through to `"?"` (unrated) and does not appear as
a pass/fail/partial in the table. The `rubric` fields in `tasks/*.json` are
descriptions for the human rater; they are NOT the rating value.

When rating an existing result:
1. Read the task's `rubric` to know what each level means.
2. Write `manual.rating` as `1`, `0.5`, or `0`.
3. Write `manual.note` as the rationale, mirroring the rubric's own language —
   the note should read like the rubric, not like a loose paraphrase of it.
4. Run `python3 evals/report.py` and confirm the cell changed from `?` to `+`/`o`/`-`.

## Error codes mean different things — don't lump them as `!`

The current report collapses every error into `!`. The actual codes carry
information:

| Code | Meaning | Action |
|------|---------|--------|
| 400  | Model ID not valid on the provider (e.g. a local Ollama model sent to OpenRouter) | Invalid run; do not score. Annotate or drop. |
| 429  | Rate-limited on a valid model | Re-runnable later; the model is real. |
| 403  | Policy/harness restriction (e.g. model only callable through an agentic harness) | Cannot be rated in a plain request; annotate. |
| truncated / parse error | Run interrupted or writer failed mid-output | Re-runnable; the model is real. |

A future `report.py` should at minimum separate 400 (invalid) from the others,
because lumping them all as `!` makes the table say "every model failed every
task" when what actually happened is "two models had invalid IDs and one was
rate-limited."

## The gate must scan `inbox/` — this section used to say the opposite

**Superseded 2026-09-20. The instruction that stood here was wrong, and acting
on it caused a leak.** It is kept rather than deleted because the reasoning that
produced it is worth seeing.

It argued that `inbox/` holds inter-branch mail rather than publishable content,
that ordinary prose in a message can share word stems with the private
domain-vocabulary list, and that the gate therefore refuses to publish over
noise that was never a leak. The last part is true and was observed. The
conclusion drawn from it was not:

```
# WRONG — do not restore this
files() { git ls-files -co --exclude-standard | grep -vE 'check-public\.sh$' | grep -vE '^inbox/'; }
```

`inbox/` is where the **other branches** write. Their messages name their own
repository, their own correspondents and their own subject matter, because that
is what makes them useful to the branch receiving them. Of everything in a
kontor repository it is the likeliest place for another branch's private
material to appear — and that exclusion made it the one place never scanned.
Eight committed and pushed messages carried between one and seventeen
deny-listed terms each before it was found. See [`../docs/lessons.md`](../docs/lessons.md).

The real problem — that ordinary mail should not block an unrelated push — is
solved where it belongs, in `.gitignore`:

```
inbox/*.md
inbox/processed/*.md
!inbox/README.md
!inbox/processed/README.md
```

An ignored file is not listed by `git ls-files -co --exclude-standard`, so
everyday pouch traffic never blocks a push. A message that is force-added
becomes tracked, and a tracked file is scanned like any other. Both properties
hold at once, which is what the exclusion was reaching for and missed.

`tools/check-public-selftest.sh` plants a canary inside `inbox/` specifically so
that restoring the exclusion fails the self-test instead of passing silently.

## Credentials: do not bake the account identifier into tool source

A tool that retrieves a credential from the keychain must not also hardcode the
account identifier (email, username) in its source. Hardcoding leaks the
identifier into the repository and trips the identifier-pattern scan in
`check-public.sh`.

Pattern that works: read the account from an environment variable or a CLI flag,
and error out clearly when neither is set.

```
# Bad — leaks the account into source
account_email = "<real-address-here>"

# Good — account comes from outside the source
account_email = os.environ.get("KONTOR_MAIL_ACCOUNT")
# or from a CLI flag --account=<email>
if not account_email:
    print("Error: account email required. Pass --account=<email> or set KONTOR_MAIL_ACCOUNT.", file=sys.stderr)
    sys.exit(1)
```

The credential itself stays in the keychain (`security find-generic-password
-a <account> -s <service> -w`). Only the account identifier travels through the
tool's interface — and that interface must be configurable, not hardcoded.
