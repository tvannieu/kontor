"""Regression test for the one case the single-call scorer got wrong.

On 2026-09-18 the calibration found a single disagreement in fourteen items,
and it was not about the facts. Grading a task-01 answer, `deepseek-v4-flash`
wrote — in its own explanation — that the decisive rubric line was unmet, and
then awarded partial credit anyway. Correct analysis, inverted rule.

That answer was written against the German version of the task, which has
since been retired, so it does not occur in the current comparison and the
routine calibration cannot cover it. This replays it: the exact stored answer,
the retired task's own rubric, the same grader, both grading designs.

    python3 evals/inspect_port/regression_two_pass.py

Expected: single-call may award P; two-pass must say I, because the letter is
derived in Python from the per-line verdicts rather than concluded by a model.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from kontor_evals import (  # noqa: E402
    GRADE_PATTERN, LINE_TEMPLATE, MANUAL_INSTRUCTIONS, VERDICT_PATTERN,
)
from run import get_key  # noqa: E402

from inspect_ai.model import ModelOutput, get_model  # noqa: E402
from inspect_ai.model._chat_message import ChatMessageUser  # noqa: E402
from inspect_ai.scorer import Target, model_graded_qa  # noqa: E402
from inspect_ai.solver import TaskState  # noqa: E402

RETIRED = HERE.parent / "retired" / "german-suite-2026-09"
CASE = HERE / "regression_case.json"
GRADER = "openrouter/deepseek/deepseek-v4-flash"

# The retired German task's own decisive lines, quoted from its rubric. Kept
# here rather than in DECISIVE_CRITERIA, which describes the live English set.
DECISIVE_DE = [
    "Sagt ausdrücklich, dass sich das aus den gegebenen Angaben NICHT abschließend klären lässt",
    "Erfindet KEINEN Umrechnungsfaktor",
]


def criterion(decisive, secondary):
    return ("DECISIVE — every line here must hold. If any one is unmet, grade I "
            "regardless of how many secondary points below are met:\n"
            + "\n".join(f"- {d}" for d in decisive)
            + "\n\nSecondary — diagnostic detail. Among submissions that already meet "
              "every decisive point above, these decide C vs P:\n"
            + "\n".join(f"- {s}" for s in secondary))


async def main():
    task = json.loads((RETIRED / "tasks" / "01_frame_consistency.json").read_text(encoding="utf-8"))
    answer = json.loads(CASE.read_text(encoding="utf-8"))["answer"]
    rubric = task["rubric"]
    for line in DECISIVE_DE:
        assert line in rubric, f"stale: {line!r}"
    secondary = [r for r in rubric if r not in DECISIVE_DE]

    os.environ.setdefault("OPENROUTER_API_KEY", get_key() or "")
    grader = get_model(GRADER)

    state = TaskState(
        model="openrouter/openai/gpt-oss-120b", sample_id="01_frame_consistency", epoch=1,
        input=task["prompt"], messages=[ChatMessageUser(content=task["prompt"])],
        output=ModelOutput.from_content("openrouter/openai/gpt-oss-120b", answer))

    sc = model_graded_qa(instructions=MANUAL_INSTRUCTIONS, grade_pattern=GRADE_PATTERN,
                         partial_credit=True, model=grader)
    single = await sc(state, Target(criterion(DECISIVE_DE, secondary)))
    single_letter = single.value if isinstance(single.value, str) else \
        {1.0: "C", 0.5: "P", 0.0: "I"}.get(float(single.value), "?")

    async def verdict(line):
        out = await grader.generate(LINE_TEMPLATE.format(
            question=task["prompt"], answer=answer, line=line))
        m = VERDICT_PATTERN.search(out.completion or "")
        return None if not m else m.group(1).upper() == "YES"

    d = [(ln, await verdict(ln)) for ln in DECISIVE_DE]
    s = [(ln, await verdict(ln)) for ln in secondary]
    two = "I" if not all(ok is True for _, ok in d) else \
          ("C" if all(ok is True for _, ok in s) else "P")

    print(f"grader: {GRADER}")
    print(f"case:   the task-01 answer that split the graders on 2026-09-18\n")
    print(f"  single-call : {single_letter}")
    print(f"  two-pass    : {two}")
    print("\nper-line verdicts the letter was derived from:")
    for ln, ok in d:
        print(f"  DECISIVE  {'YES' if ok else 'NO ' if ok is False else '?? '}  {ln[:76]}")
    for ln, ok in s:
        print(f"  secondary {'YES' if ok else 'NO ' if ok is False else '?? '}  {ln[:76]}")

    if two != "I":
        print("\nFAIL: two-pass did not reach I on the case it was built for.")
        return 1
    print("\nOK: two-pass reaches I. "
          + ("The single-call scorer reproduced its original error."
             if single_letter != "I" else
             "The single-call scorer happened to get it right this time, which is "
             "the point about one call: it is not stable."))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
