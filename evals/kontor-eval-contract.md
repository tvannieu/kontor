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
non-numeric value — falls through to `"?"` (unbewertet) and does not appear as
a pass/fail/partial in the table. The rubric fields in `tasks/*.json` are German
descriptions for the human rater; they are NOT the rating value.

When rating an existing result:
1. Read the task's `rubric` to know what each level means.
2. Write `manual.rating` as `1`, `0.5`, or `0`.
3. Write `manual.note` as the rationale, mirroring the rubric's own language —
   the note should read like the rubric, not like a loose paraphrase of it.
4. Run `python3 evals/report.py` and confirm the cell changed from `?` to `+`/`o`/`-`.

## Error codes mean different things — don't lump them as `!`

The current report collapses every `fehler` into `!`. The actual codes carry
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

## The gate must not scan inbox/

`tools/check-public.sh` scans tracked and untracked files for private content
before every push. `inbox/` holds inter-branch mail (the pouch), not
publishable repository content. If the gate scans inbox items, ordinary German
prose in them can share word stems with the private domain-vocabulary list —
confirmed in practice, not hypothetical — and the gate refuses to publish on
noise that was never a leak.

The `files()` function in `check-public.sh` must exclude `inbox/`:

```
files() { git ls-files -co --exclude-standard | grep -vE 'check-public\.sh$' | grep -vE '^inbox/'; }
```

After changing `files()`, run `bash tools/check-public.sh` and confirm it says
`clean`. An inbox item landing in the working tree is normal and must not block
publishing.

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
