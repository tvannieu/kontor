"""
Judge calibration: how much to trust the model grader on the manual tasks.

Every manual-task grade in this port so far came from one grader, sometimes
grading its own answers. This re-scores every stored manual-task completion
under the *current* criteria with two or more graders and reports agreement —
grader vs. the human ratings already on record in results/ (the real
calibration), and grader vs. grader (the cheap proxy for it).

Items come from two places and are deduplicated on (task, text):
  - evals/results/*.json — manual tasks with a numeric human rating
    (1 / 0.5 / 0 → C / P / I). These carry ground truth.
  - inspect_port/logs/*kontor-manual*.eval — completions the port produced.
    No human label; they add grader-vs-grader coverage.

No new candidate generations: only grading calls, one per item per grader.

    python3 evals/inspect_port/calibrate.py \\
        openrouter/openai/gpt-oss-120b openrouter/deepseek/deepseek-v4-flash
"""

import asyncio
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from kontor_evals import MANUAL_INSTRUCTIONS, TASKS_DIR, _build_criterion  # noqa: E402
from run import get_key  # noqa: E402

from inspect_ai.log import read_eval_log  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402
from inspect_ai.model._chat_message import ChatMessageUser  # noqa: E402
from inspect_ai.scorer import Target, model_graded_qa  # noqa: E402
from inspect_ai.solver import TaskState  # noqa: E402

RESULTS = HERE.parent / "results"
LOGS = HERE / "logs"
HUMAN = {1: "C", 0.5: "P", 0: "I"}


def load_tasks():
    out = {}
    for f in sorted(TASKS_DIR.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        if t["check"] == "manual":
            out[t["id"]] = t
    return out


def gather(tasks):
    items, seen = [], set()

    def add(task, candidate, text, human, source):
        key = (task, text.strip())
        if key in seen or not text.strip():
            return
        seen.add(key)
        items.append({"task": task, "candidate": candidate, "text": text,
                      "human": human, "source": source})

    for f in sorted(RESULTS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for a in d["aufgaben"]:
            if a["id"] in tasks and a.get("manuell", {}).get("bewertung") is not None:
                add(a["id"], d["modell"], a["antwort"], HUMAN.get(a["manuell"]["bewertung"]), f.name)
    for f in sorted(glob.glob(str(LOGS / "*kontor-manual*.eval"))):
        log = read_eval_log(f)
        if log.status != "success":
            continue
        for s in log.samples:
            add(s.id, log.eval.model, s.output.completion or "", None, Path(f).name)
    return items


async def grade(grader_name, item, tasks, sem):
    t = tasks[item["task"]]
    scorer = model_graded_qa(instructions=MANUAL_INSTRUCTIONS, partial_credit=True,
                             model=get_model(grader_name))
    state = TaskState(model=item["candidate"], sample_id=item["task"], epoch=1,
                      input=t["prompt"], messages=[ChatMessageUser(content=t["prompt"])],
                      output=ModelOutput.from_content(item["candidate"], item["text"]))
    async with sem:
        score = await scorer(state, Target(_build_criterion(item["task"], t["rubric"])))
    return score.value, (score.explanation or "")


def agreement(pairs):
    """pairs: list of (a, b). Exact and lenient (C/P together vs I)."""
    pairs = [(a, b) for a, b in pairs if a and b]
    if not pairs:
        return None
    exact = sum(a == b for a, b in pairs) / len(pairs)
    lenient = sum((a == "I") == (b == "I") for a, b in pairs) / len(pairs)
    return len(pairs), exact, lenient


async def main(graders):
    tasks = load_tasks()
    items = gather(tasks)
    os.environ.setdefault("OPENROUTER_API_KEY", get_key() or "")
    sem = asyncio.Semaphore(3)
    for g in graders:
        grades = await asyncio.gather(*(grade(g, it, tasks, sem) for it in items))
        for it, (v, why) in zip(items, grades):
            it.setdefault("grades", {})[g] = v
            it.setdefault("explanations", {})[g] = why

    short = {g: g.split("/")[-1][:22] for g in graders}
    w = max(len(it["candidate"]) for it in items)
    print(f"{'task':<22} {'candidate':<{w}} {'human':>5}  " + "  ".join(f"{short[g]:>22}" for g in graders))
    for it in items:
        print(f"{it['task']:<22} {it['candidate']:<{w}} {it['human'] or '-':>5}  "
              + "  ".join(f"{it['grades'][g]:>22}" for g in graders))

    print("\nAgreement (n, exact, lenient = C/P vs I):")
    for g in graders:
        r = agreement([(it["human"], it["grades"][g]) for it in items])
        if r:
            print(f"  {short[g]:>22} vs human   n={r[0]:<3} exact={r[1]:.0%}  lenient={r[2]:.0%}")
    for i, g1 in enumerate(graders):
        for g2 in graders[i + 1:]:
            r = agreement([(it["grades"][g1], it["grades"][g2]) for it in items])
            print(f"  {short[g1]:>22} vs {short[g2]:<22} n={r[0]:<3} exact={r[1]:.0%}  lenient={r[2]:.0%}")

    # The agreement rate is the headline; the disagreements are the content.
    # A calibration that only reports a percentage has thrown away the part
    # you would act on.
    print("\nDisagreements (a grader differs from the human label or from another grader):")
    for it in items:
        votes = ([it["human"]] if it["human"] else []) + [it["grades"][g] for g in graders]
        if len(set(votes)) > 1:
            print(f"\n  {it['task']}  {it['candidate']}  human={it['human'] or '-'}")
            for g in graders:
                print(f"    {short[g]} -> {it['grades'][g]}: {it['explanations'][g].strip()[:700]}")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    out = HERE / f"calibration_{stamp}.json"
    out.write_text(json.dumps({"graders": graders, "items": items}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"\nGeschrieben: {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1:]))
