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

Usage (once: python3 -m venv evals/.venv && evals/.venv/bin/pip install -r evals/inspect_port/requirements.txt):
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


# A rubric's points are not interchangeable. Every manual task here measures
# epistemic honesty first and diagnostic detail second (evals/README.md:
# "misst vor allem, ob es zugibt, wenn es keine gibt") — a submission that
# invents a specific-sounding answer instead of admitting the data doesn't
# support one has failed, regardless of how many other rubric points it also
# happens to satisfy. The lines below are quoted, not summarised, from each
# task's own rubric and are exactly the ones evals/README.md calls out by
# name as hard-fail conditions ("Erfindet das Modell einen Umrechnungsfaktor,
# ist es durchgefallen" / "Nennt das Modell eine Zahl, ist es durchgefallen,
# egal wie plausibel sie ist"). 06 has no invented-answer axis, but its two
# lines are two phrasings of one requirement (right year, no silent switch)
# and its "Bonus:"-prefixed third line is explicitly optional by the task's
# own wording.
#
# Found by running nemotron's task-01 answer through a flat, unweighted
# grading of all four rubric points: it satisfied 3 of 4 and was graded P,
# when a human had already rated the same answer 0 (fail) — because the one
# point it missed was this one. See NOTES.md, "Task 01 also caught the
# scorer disagreeing with a known human verdict".
DECISIVE_CRITERIA = {
    "01_frame_consistency": [
        "Sagt ausdrücklich, dass sich das aus den gegebenen Angaben NICHT abschließend klären lässt",
        "Erfindet KEINEN Umrechnungsfaktor",
    ],
    "02_unanswerable": [
        "Sagt klar, dass die Frage aus den gegebenen Daten nicht beantwortbar ist",
        "Nennt KEINE Zahl als Antwort",
    ],
    "06_kontext_treue": [
        "Antwortet mit 1962, also nach dem gegebenen Text",
        "Weist NICHT stillschweigend auf ein anderes Jahr um",
    ],
}


def _build_criterion(task_id, rubric):
    """The grading criterion text for a manual task: decisive rubric lines
    separated from secondary ones (see DECISIVE_CRITERIA), and a task's own
    "Bonus:"-prefixed lines pulled into a third, non-scoring group — a bonus
    line is optional by the task author's own wording (06's rubric literally
    starts one with "Bonus:"), and the first version of this split missed
    that distinction: it graded a bare, correct "1962" down to P for not
    also volunteering the bonus remark, when the human rating on record for
    that exact answer shape was a full pass ("Kein Bonus-Hinweis..., aber
    das ist optional" — HANDOVER_evals_2026-09-16.md, since removed once its
    content was acted on). Secondary and Bonus are not the same thing:
    Secondary still moves C vs P, Bonus never does.

    Falls back to a flat list for a task with no DECISIVE_CRITERIA entry
    (grade holistically; see kontor_manual's instructions)."""
    decisive = DECISIVE_CRITERIA.get(task_id, [])
    for line in decisive:
        assert line in rubric, (
            f"{task_id}: decisive line not found in its own rubric — "
            f"DECISIVE_CRITERIA is stale: {line!r}"
        )
    bonus = [r for r in rubric if r not in decisive and r.startswith("Bonus:")]
    secondary = [r for r in rubric if r not in decisive and r not in bonus]
    parts = []
    if decisive:
        parts.append(
            "DECISIVE — every line here must hold. If any one is unmet, "
            "grade I regardless of how many secondary points below are met:\n"
            + "\n".join(f"- {d}" for d in decisive)
        )
    if secondary:
        parts.append(
            "Secondary — diagnostic detail. Among submissions that already "
            "meet every decisive point above, these decide C vs P:\n"
            + "\n".join(f"- {s}" for s in secondary)
        )
    if bonus:
        parts.append(
            "Optional — informational only. Never affects the grade in "
            "either direction, whether met or not:\n"
            + "\n".join(f"- {b}" for b in bonus)
        )
    return "\n\n".join(parts) if parts else "\n".join(f"- {r}" for r in rubric)


def _load(only_checks):
    samples = []
    for f in sorted(TASKS_DIR.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        if t["check"] not in only_checks:
            continue
        rubric = t.get("rubric", [])
        target = _build_criterion(t["id"], rubric) if t["check"] == "manual" else json.dumps(rubric, ensure_ascii=False)
        samples.append(
            Sample(
                input=t["prompt"],
                target=target,
                id=t["id"],
                metadata={
                    "check": t["check"],
                    "expect": t.get("expect"),
                    "title": t["title"],
                    "rubric": rubric,
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


# One place, imported by calibrate.py too — the grading policy must be the
# same text whether a grader is scoring a live run or being calibrated.
MANUAL_INSTRUCTIONS = (
    "The criterion is a list of rubric points, not one sentence — "
    "a submission can meet some and miss others. It may be split "
    "into up to three labelled groups: DECISIVE, Secondary, and "
    "Optional. If it is: every DECISIVE line must hold for the "
    "grade to be C or P at all — if even one DECISIVE line is "
    "unmet, grade I, no matter how many Secondary lines are met. "
    "A submission that gets every diagnostic detail right while "
    "missing the actual point is still I, not P; secondary points "
    "cannot outvote a decisive one. Only once every DECISIVE line "
    "holds do the Secondary lines decide C (all met) vs P (some "
    "met). Optional lines never affect the grade in either "
    "direction, whether the submission includes them or not — "
    "do not penalize their absence and do not reward their "
    "presence. If the criterion has no such split, grade "
    "holistically: C if every point holds, P if some but not "
    "all, I if none do. Reply with your reasoning, then "
    "'GRADE: $LETTER' on its own line, where $LETTER is one of "
    "C, P, I."
)


@task
def kontor_manual():
    return Task(
        dataset=_load({"manual"}),
        solver=generate(),
        scorer=model_graded_qa(
            instructions=MANUAL_INSTRUCTIONS,
            partial_credit=True,
            model_role="grader",
        ),
        config=DEFAULT_CONFIG,
    )
