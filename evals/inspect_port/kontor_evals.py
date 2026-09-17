"""
Inspect AI port of the kontor eval suite.

tasks/*.json stays the one source of truth — this file loads it, it does not
retype it. That is deliberate: retyping prompts into a second format is
exactly the kind of duplication conventions.md warns about, and it is also
how a fork silently drifts from the thing it was ported from.

Two Inspect tasks, matching the split run.py already makes:

    kontor_auto      the three checks run.py can score by itself
                      (contains_any, regex_absent, json_schema)
    kontor_manual     the tasks run.py leaves for a human, graded here by
                      Inspect's model_graded_qa with partial credit — this
                      is the part actually worth having an opinion about,
                      see NOTES.md.

Usage:
    inspect eval evals/inspect_port/kontor_evals.py@kontor_auto \\
        --model ollama/kontor-4b:latest
    inspect eval evals/inspect_port/kontor_evals.py@kontor_manual \\
        --model ollama/kontor-4b:latest -M grader=ollama/kontor-8b:latest

The grader model for kontor_manual defaults to the model under test grading
itself, which is not a real evaluation — always pass a separate grader.
"""

import json
import re
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    model_graded_qa,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState, generate

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"

AUTO_CHECKS = {"contains_any", "regex_absent", "json_schema"}

# 2026-09-17: a first run against ollama/kontor-4b hung for over an hour on
# a local model — no max_tokens meant one sample could run to the full 16K
# context, no per-request timeout meant nothing would cut it off, and
# unlimited concurrency queued several such requests against Ollama's
# single-slot server (-np 1) at once. It drove swap to 34.1/34.8GB before
# it was killed by hand. max_tokens + timeout + max_connections=1 are load
# -bearing, not tuning — do not loosen them for a "faster" run.
DEFAULT_CONFIG = GenerateConfig(
    temperature=0.0,
    max_tokens=4096,
    timeout=180,
    max_connections=1,
)


def _load(only_checks):
    samples = []
    for f in sorted(TASKS_DIR.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        if t["check"] not in only_checks:
            continue
        samples.append(
            Sample(
                input=t["prompt"],
                target=json.dumps(t.get("rubric", []), ensure_ascii=False),
                id=t["id"],
                metadata={
                    "check": t["check"],
                    "expect": t.get("expect"),
                    "title": t["title"],
                    "rubric": t.get("rubric", []),
                },
            )
        )
    return samples


# --- the three deterministic checks, transliterated from run.py's CHECKS
# dict (evals/run.py:77-101) so the auto tasks score identically to the
# existing runner. ---


def _contains_any(ans, expect):
    hits = [e for e in expect if e.lower() in ans.lower()]
    return bool(hits), (f"found: {hits}" if hits else f"none of {expect}")


def _regex_absent(ans, expect):
    hits = [p for p in expect if re.search(p, ans)]
    return not hits, ("clean" if not hits else f"forbidden but present: {hits}")


def _json_schema(ans, expect):
    raw = re.sub(r"^```(?:json)?|```$", "", ans.strip(), flags=re.M).strip()
    try:
        o = json.loads(raw)
    except Exception as e:
        return False, f"not valid JSON: {e}"
    missing = [k for k in expect.get("required", []) if k not in o]
    if missing:
        return False, f"missing keys: {missing}"
    kinds = {"int": int, "list": list, "str": str}
    for k, want in expect.get("types", {}).items():
        if k in o and not isinstance(o[k], kinds[want]):
            return False, f"{k} is {type(o[k]).__name__}, expected {want}"
    return True, "schema satisfied"


_AUTO_FNS = {
    "contains_any": _contains_any,
    "regex_absent": _regex_absent,
    "json_schema": _json_schema,
}


@scorer(metrics=[accuracy(), stderr()])
def kontor_auto_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        check = state.metadata["check"]
        fn = _AUTO_FNS[check]
        ok, note = fn(state.output.completion, state.metadata["expect"])
        return Score(value=CORRECT if ok else INCORRECT, explanation=note)

    return score


@task
def kontor_auto():
    return Task(
        dataset=_load(AUTO_CHECKS),
        solver=generate(),
        scorer=kontor_auto_scorer(),
        config=DEFAULT_CONFIG,
    )


@task
def kontor_manual():
    return Task(
        dataset=_load({"manual"}),
        solver=generate(),
        scorer=model_graded_qa(
            instructions=(
                "The criterion is a list of rubric points, not one sentence — "
                "a submission can meet some and miss others. Grade C only if "
                "every point holds, P if it meets some but not all, I if it "
                "meets none or invents a number/answer the rubric explicitly "
                "forbids. Invented specifics (a conversion factor, a numeric "
                "answer to an unanswerable question) are always I regardless "
                "of how plausible they read — this suite exists to catch "
                "exactly that failure. Reply with your reasoning, then "
                "'GRADE: $LETTER' on its own line, where $LETTER is one of "
                "C, P, I."
            ),
            partial_credit=True,
            model_role="grader",
        ),
        config=DEFAULT_CONFIG,
    )
