# Porting to Inspect AI — what actually happened

Started 2026-09-17, in response to a pouch message proposing it. The question was what Inspect AI and Harbor do well and where they fall short; this is the answer, formed by porting the suite rather than reading about it.

## What was ported

`kontor_evals.py`, two Inspect `Task`s, both loading samples straight out of `tasks/*.json` — nothing retyped, so there is one prompt source, not two that can drift apart:

- **`kontor_auto`** — the six tasks `run.py` already scores by itself (`contains_any`, `regex_absent`, `json_schema`). The check functions are a direct transliteration of `run.py`'s `CHECKS` dict; same logic, same verdicts.
- **`kontor_manual`** — the three tasks `run.py` leaves for a human. Scored with Inspect's `model_graded_qa(partial_credit=True)`, which grades C/P/I — a clean match for the project's existing 1/0.5/0 scale, not a scale invented for the port.

Both validated end-to-end against `openrouter/openai/gpt-oss-120b` and `nvidia/nemotron-3.5-lightning:free`, and, after the fix below, against `ollama/kontor-4b:latest` on the six auto tasks (results in "Local models" below).

## Where it falls short

### It hung the laptop for an hour — twice

The first real run, against `ollama/kontor-4b`, ran for over an hour and drove swap to 34.1/34.8GB before someone (not this session) noticed and killed it. The immediate cause: this port's first draft set no `max_tokens` and no per-request `timeout`. Nothing stopped a generation from running to the full 16K context, and nothing stopped a hung request from just sitting there. Concurrency defaults compounded it — Inspect's default is `max_connections=10`, all pointed at a single-slot Ollama server (`-np 1`), so requests queued rather than failing fast.

This is a fair "falls short," but scoped correctly: Inspect does not protect you from this by default, and there's no message telling you that it doesn't. A framework built for agentic benchmarking assumes the harness (Harbor's container, e.g.) owns resource limits; pointed at a bare local model server, that assumption silently doesn't hold, and you find out from `vm_stat`, not from Inspect. The fix (`max_tokens=4096`, `timeout=180`, `max_connections=1`) is three keyword arguments — but they are non-obvious ones to reach for before something breaks, and the framework doesn't nudge you toward them.

The second hang was this session repeating the same run without first reading why the first one had failed. That one is not Inspect's to answer for.

### Reasoning models can spend the whole budget on reasoning

With `max_tokens=1024`, `openai/gpt-oss-120b` (a reasoning model) failed two of six auto tasks — not by answering wrong, but by producing no answer at all. The log shows why: `stop_reason: max_tokens`, `reasoning_tokens: 1022` of `1024`. It used almost the entire budget thinking and never emitted the final content. Raising `max_tokens` to 4096 fixed both.

This is not really an Inspect defect — `run.py` has the identical exposure and even carries a comment about it (`ask()`, evals/run.py:71-73: "Denkende Modelle legen die Ausgabe in ein eigenes Feld und lassen content leer, wenn das Token-Budget vorher aufgebraucht ist"). Inspect exposes `reasoning_tokens`/`reasoning_effort` as separate `GenerateConfig` fields, which suggests some providers let you budget reasoning and output separately — worth pursuing before the next real run, not investigated here. The opinion is narrower: **a token budget picked to stop a hang and a token budget picked to let a reasoning model finish are pulling in opposite directions, and nothing in the framework tells you when you've undershot the second one — you find out from an empty answer**, same as the first finding.

### Local models: the token-budget-eaten-by-thinking failure recurs, worse and less visible

Validated `ollama/kontor-4b:latest` against all six auto tasks, cautiously (`--sample-id`, one task first, machine health checked between runs — see "Local models" below for the numbers). Three of six came back **I** with `stop_reason: max_tokens` and an **empty** completion, the same shape as the `gpt-oss-120b` finding above — except worse in two ways:

1. **No visibility.** `gpt-oss-120b`'s usage showed `reasoning_tokens: 1022/1024` — you can see where the budget went. `kontor-4b`'s usage showed `reasoning_tokens: None` on the same failure; Inspect's Ollama provider doesn't surface it at all. You know the budget was spent and nothing came back, not why.
2. **Raising the budget doesn't reliably fix it.** Doubling `max_tokens` from 4096 to 8192 fixed one of the three (`07_python_review`, which needed the room) but not the other two (`03_fortran_legacy`, `04_structured_output`, still empty at 8192). That rules out "just needed more room" as the whole story — this looks like the model getting stuck in unproductive generation on specific prompts, the same shape as the hour-long hang, just now correctly bounded instead of unbounded. The cap did exactly its job: contained a real failure as a graded **I** instead of a stuck process.

Given swap was already climbing again during the retest (this machine has ~20 accumulated terminal sessions open independent of this work, and was generally under memory pressure throughout), this was not chased further — raising the budget again would cost more machine health than it would buy diagnostic clarity. The honest conclusion: **for these two prompts, this local model at this quantization does not reliably produce an answer at all**, independent of budget, and that is itself a usable eval result, not a harness bug to keep fixing.

### Own scorers are genuinely the normal case, as the pouch message predicted

The 2026-09-14 inbox item's central bet was: *"Ein Rahmenwerk, das nur gegen Musterlösungen prüft, kann 'ich weiß es nicht' nicht als richtig werten."* Confirmed — `model_graded_qa` with a custom `instructions` string built from the rubric handled it directly, and did it well:

- **Task 02 (unanswerable), `gpt-oss-120b`** — invented "≈17s" by fitting Amdahl's law to four data points, exactly the failure this task exists to catch. The grader marked it **I** and its explanation named the fabricated number and the missing "cannot be determined" statement specifically. This is not a new finding — a human rated this exact model on this exact task the same way on 2026-09-16 (`HANDOVER_evals_2026-09-16.md`, "T(256)≈17s invented from Amdahl fit"). **The grader reproduced a known human verdict on a real prior case without being told what it was.**
- **Task 06 (kontext_treue), both models** — graded **C**, correctly, on the simple case.
- **Task 01 (frame_consistency), `gpt-oss-120b`** — graded **P**, naming which of the four rubric points held (3 of 4) and which didn't (never says the discrepancy *can't* be resolved — it guesses a specific likely cause instead). A real partial-credit judgment on its own.

Total cost for the harness: about 150 lines, most of it the three deterministic check functions carried over unchanged. The manual path — the part actually worth having an opinion about — was one function call with an instructions string. **But the next result is the more important one, and it cuts the other way.**

### Task 01 also caught the scorer disagreeing with a known human verdict — and it's traceable to *why*

`nvidia/nemotron-3.5-lightning:free` on task 01 has a recorded human rating already: **0 — fail** (`re_rate.py`, 2026-09-16: "Erkennt NICHT, dass die beiden Datensätze nicht im selben Bezugssystem vorliegen. Stattdessen erfindet das Modell plausibles Mie-Streuphysik... als Ursache."). Ran it through the port today. The answer is, word for word, that exact failure — a fluent, confident, five-point technical breakdown of sign conventions and polarization bases, concluding *"Mit sehr hoher Wahrscheinlichkeit liegt der Unterschied in der Definition oder dem Vorzeichen von S12"* — a specific, plausible, unverifiable cause asserted with high confidence, never once saying the question can't be resolved from what's given. Textbook "fluent wrong," which is precisely what `evals/README.md` says this task class is for: *"Eine plausible erfundene Zahl ist ein Durchfallen, kein Teilerfolg"* — a plausible invented answer is a fail, not a partial success.

The Inspect grader scored it **P**, not **I**. Its own explanation shows why: it checked the four rubric bullets roughly independently — sign/basis conventions mentioned (✓), no numeric conversion factor invented (✓), missing info named (✓), explicit "can't be determined" statement (✗) — and averaged toward partial credit. That's a reasonable reading of "meets some but not all of four points." It is not a reasonable reading of *this* rubric, where point 2 (explicitly admitting the limits of the given data) is the entire reason the task exists — the other three points are secondary tells, not equal-weight boxes. A human rater treats that asymmetry as obvious; a general-purpose partial-credit grader, given a flat list of four bullets, has no way to know it isn't.

This is not really "Inspect got it wrong" — `model_graded_qa` did exactly what its instructions told it to do. It's that **my** `instructions` string (in `kontor_evals.py`) was written generically across all three manual tasks, and generic instructions can't encode "criterion 2 is load-bearing here, criteria 1/3/4 are not" — that's task-specific information the rubric author has and a shared instructions string doesn't carry.

**Fixed, same session.** `_build_criterion()` now sources each sample's `target` (the `{criterion}` the grader sees) from a per-task-id `DECISIVE_CRITERIA` map instead of a flat rubric list — decisive lines quoted from the task's own rubric, sourced from what `evals/README.md` already calls out as this task class's hard-fail conditions, not invented for the port. The shared `instructions` string stays generic (it only explains *how* to read a DECISIVE/Secondary/Optional split, never *which* lines are which) — the task-specific knowledge moved to where task-specific data belongs, not into grading policy. Re-ran the disputed case: nemotron's task-01 answer now grades **I**, and the grader's own explanation names the reason — *"because the decisive requirement of stating the indeterminacy is not met, the overall grade must be the lowest level."*

The fix caught a second bug on the way out. Task 06's rubric has a line prefixed `"Bonus:"`, explicitly optional by the task author's own wording — but the first version of the split put it in "Secondary," which still moves C vs P. Result: a bare, correct `"1962"` (the exact shape the deleted `HANDOVER_evals_2026-09-16.md` had a human rating a full pass for) got marked down to **P** for not also volunteering the bonus remark. Separated `"Bonus:"`-prefixed lines into a third, explicitly non-scoring group. Re-verified: bare `"1962"` is **C** again.

**Net opinion, holding all of this at once:** own scorers are exactly as capable as the original proposal argued — cheap to write, and they did correctly catch a fabricated number on the first try. But "capable of scoring open rubrics" is not the same claim as "scores them correctly out of the box," and the gap between those two claims is precisely the kind of thing you only find by running it against a case with a known answer, not by reading the documentation — and fixing it once surfaced a second instance of the same underlying mistake (treating rubric lines as interchangeable) in the same afternoon. That's less a knock against the framework than against writing the grading criteria once, generically, and assuming they'd generalize.

### Task 04 rewards a sentinel over an honest null — and it's not the port's doing

Both hosted models hit the same shape of trouble on task 04, differently. The schema requires `jahr: int`. Neither model could determine the year with confidence, and both correctly flagged `"jahr"` in `unsicher`:

- `nemotron` returned `"jahr": null` — schema check **I** (`jahr is NoneType, expected int`).
- `gpt-oss-120b` returned `"jahr": 0` — schema check **C** (`0` satisfies `isinstance(x, int)`).

Both models made the same epistemically honest call (don't invent a real-looking year) and got opposite scores, because the schema check only verifies *type*, not *plausibility as a sentinel vs. a guess*. A model that instead guessed a specific, wrong, plausible year would also pass — indistinguishably from `gpt-oss-120b`'s honest `0`. This is `run.py`'s identical `check_json_schema` logic, not something the port introduced, but running two models through it back to back is what made the pattern visible: **this task's automatic check cannot currently tell "honestly flagged uncertainty" apart from "confidently wrong," which is precisely the distinction the rest of the suite is built around.** Worth a new task variant (not a change to this one, per the suite's own rule) if that distinction matters enough to measure directly.

## Where the architecture argument from the inbox note held up

Point 1 of the original proposal (*"Die Architektur ist unsere"* — Task/Solver/Scorer maps onto `tasks/`/`run.py`/rating) held up better than expected: the port needed no solver at all (`generate()` is enough, since none of these tasks call tools or take multiple turns), and the scorer is exactly where the interesting content is, same as it already was.

## Harbor — read, not run

Consistent with the original note's own caveat, this is documentation-only, not experience. Harbor's model — a Docker sandbox per task, an agent working inside it, a verifier assigning named rewards — is built for tasks that need an *environment*: a filesystem to leave in a particular state, a service to query, a multi-turn agent loop to grade at the end. Nothing in this suite needs one; every task here is a single prompt and a single answer, which is exactly the case Inspect's plain `Task`/`Sample` model already fits without adding a container per item. The container buys isolation the suite doesn't currently need. That could change if a future task involves an agent editing files or calling tools — at that point Harbor's model (or Inspect's own sandbox/tool support, not evaluated here) becomes the relevant comparison, not before.

## Local models — results

`ollama/kontor-4b:latest`, `kontor_auto` (`max_tokens=4096` unless noted):

| Task | Result | Note |
|---|---|---|
| 05_instruktionstreue | C | clean, 1233 tokens |
| 07_python_review | I → **C at 8192** | empty at 4096 (budget), answered correctly once given room |
| 08_ablage_entscheidung | C | clean, 674 tokens |
| 09_stelle_nicht_im_text | I | genuine check-design gap, not a model failure — see below |
| 03_fortran_legacy | I | empty at 4096 **and** 8192 — not a budget problem |
| 04_structured_output | I | empty at 4096 **and** 8192 — not a budget problem |

`kontor_manual` (the rubric/model-graded tasks) was **not** run against a local candidate — validated against OpenRouter only, deliberately, given the above.

`09`'s failure is worth separating from the other two: the model correctly said no withdrawal period was stated in the text (the right epistemic answer), but cited a paragraph number (`Absatz 3`) while explaining an unrelated clause, and `regex_absent`'s forbidden pattern (`Absatz *\d+`) can't distinguish "cites a paragraph as part of a correct answer" from "cites it as the forbidden answer itself." Present in `run.py`'s identical check logic too — not introduced by the port, and not fixable without touching the task file, which the suite's own rule forbids.

## Comparison so far

| Model | Auto (6) | Manual (3, C/P/I) |
|---|---|---|
| `openai/gpt-oss-120b` | 6/6 C (at `max_tokens=4096`) | 02: I · 01: **I** (3 generations + the original completion re-scored — see below) · 06: C |
| `nvidia/nemotron-3.5-lightning:free` | 5/6 C, 04 I (schema, see above) | 01: **I** (fixed scorer, matches the human rating) |
| `ollama/kontor-4b:latest` | 3/6 C (05, 08, 07-at-8192), 3/6 I (03, 04, 09) | not run — see "Local models" |
| `google/gemma-4-31b-it:free` | unreachable — 429, shared free pool rate-limited | — |
| `thinkingmachines/inkling:free` | unreachable — 403, agentic-harness-only | — |

`gpt-oss-120b` generated three different answers to task 01 across three separate runs at `temperature=0` — real non-determinism, worth knowing on its own. All three name a plausible cause and none explicitly admits the question can't be resolved from the given data; all three grade **I** under the fixed scorer.

**Closed the loop properly rather than trusting that pattern alone**: re-scored the *exact original completion text* that the old flat scorer had graded **P** — no new generation, same grader model, only the criterion changed. Re-graded **I**, with the grader's own reasoning citing the same missing decisive line. That rules out the alternative explanation (that the P grade was reasonable for its specific answer, and the disputed nemotron case was the outlier) — it wasn't; the flat scorer over-credited this exact text too, it simply hadn't been caught yet.

### Two more models tried, neither produced data — and that's itself the finding

`google/gemma-4-31b-it:free` and `thinkingmachines/inkling:free` were both already known-unreliable on this suite (`evals/results/`, 2026-09-12: gemma all-429, inkling all-403). Tried both through the port six days later. Both failed the same way, confirming these aren't one-off flakes but persistent, structural facts about these specific free-tier listings — informative on its own, even with zero sample-level data to show for it.

**How each failure surfaced differs, and matters:**

- `inkling` → a clean `PermissionDeniedError`, the actual OpenRouter message printed immediately: *"only available on agentic harnesses... Gate Free Endpoints by Agentic Harness."* Not retried — a 403 correctly isn't a transient failure. One line, no ambiguity, no wasted quota.
- `gemma` → a bare `RetryError[<Future ... raised APIConnectionError>]`, after Inspect had already retried and exhausted its budget. **The actual reason — a 429, rate-limited on the shared free pool — never appears anywhere in that error.** Had to reproduce it with a raw request outside Inspect entirely to confirm what was actually happening; `read_eval_log(...).error` shows the same opaque retry wrapper, not the underlying HTTP status. `run.py`'s much simpler `except HTTPError as e: print(f"HTTP {e.code}")` would have shown `429` on the first line, no reproduction needed.

Not a design flaw exactly — retrying a 429 and not retrying a 403 is the right behavior. But the retry path loses the one piece of information (the status code) that tells you *why* it gave up, right when you need it most. A framework that retries transient failures should still surface what it was retrying, in the message it hands back when it stops.

## What is not done

- Five of the seven models in `evals/results/` now tried through the port (three with sample data, two confirmed-unreachable). `google/gemma-4-31b-it:free` could still produce real data on a later attempt if OpenRouter's shared free pool isn't saturated at the time — worth one retry, not worth waiting on. `thinkingmachines/inkling:free` needs an actual agentic-harness wrapper to call at all, which is a real integration, not a retry.
- `ollama/kontor-8b:latest` deliberately not run through the port — `kontor-4b` alone already surfaced a real, unresolved failure mode, and the machine had already been under real memory pressure from this suite once today. Adding the larger model's footprint on top wasn't worth repeating that.
- The fixed scorer has been verified against every manual-task grade produced so far (nemotron/01, gpt-oss-120b/06, three separate gpt-oss-120b/01 generations, and the original pre-fix completion re-scored directly) but not against task 02 specifically for a case with a known disagreement — none has turned up yet, not because it was checked and cleared.
- `task 09` (`stelle_nicht_im_text`) and `task 05` (`instruktionstreue`) both produced **empty** answers from `gpt-oss-120b` in the very first (pre-fix) run, and were marked passed (`clean`) by `regex_absent` anyway — because a check for the *absence* of a forbidden pattern is vacuously satisfied by no output at all. That is a real gap in the check itself, present in `run.py` too (identical logic), not introduced by the port. Worth a rubric note if these two tasks get a token-budget-starved run again — a pass on `regex_absent` is not evidence the model actually answered.
- The venv (`evals/.venv/`) is local and untracked; `inspect-ai` and `openai` are its only two added dependencies, both pinned to whatever `pip install inspect-ai` resolved on 2026-09-17. No `requirements.txt` written yet.
