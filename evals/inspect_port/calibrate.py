"""
Judge calibration: how far can a model grader stand in for the human rating?

Every manual grade in this collection is a judgement someone made by hand, and
the rubric is what makes it repeatable. This re-scores those same stored
answers with a model grader and reports how often it agrees.

Two grading designs are compared on identical inputs:

  single    one call per answer: the whole rubric goes in, the model replies
            with a letter. This is Inspect's model_graded_qa.
  two-pass  one call per rubric line, each a plain yes/no about the answer,
            and the letter derived in Python afterwards.

The second exists because the first was caught, on 2026-09-18, writing that a
decisive rubric line was unmet and then awarding partial credit anyway.
Correct analysis, inverted rule. Asking a model to hold a conditional and also
apply it is two separate demands; this measures whether splitting them helps.

Agreement is reported against the human ratings and broken down by rating,
because the set is skewed — most manual answers fail — and a grader that
always said "fail" would score well on the total alone.

    python3 evals/inspect_port/calibrate.py --grader openrouter/deepseek/deepseek-v4-flash
    python3 evals/inspect_port/calibrate.py --grader ... --mode two-pass --limit 12
"""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from kontor_evals import (  # noqa: E402
    GRADE_PATTERN, LINE_TEMPLATE, MANUAL_INSTRUCTIONS, TASKS_DIR,
    VERDICT_PATTERN, _build_criterion, _split_rubric,
)
from run import get_key  # noqa: E402

from inspect_ai.model import ModelOutput, get_model  # noqa: E402
from inspect_ai.model._chat_message import ChatMessageUser  # noqa: E402
from inspect_ai.scorer import Target, model_graded_qa  # noqa: E402
from inspect_ai.solver import TaskState  # noqa: E402

RESULTS = HERE.parent / "results"
HUMAN = {1: "C", 0.5: "P", 0: "I"}
LETTER = {1.0: "C", 0.5: "P", 0.0: "I"}


def load_tasks():
    out = {}
    for f in sorted(TASKS_DIR.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        if t["check"] == "manual":
            out[t["id"]] = t
    return out


def gather(tasks):
    """Every human-rated manual answer in results/, deduplicated on its text."""
    items, seen = [], set()
    for f in sorted(RESULTS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for a in d["tasks"]:
            if a["id"] not in tasks or "answer" not in a:
                continue
            if a.get("manual", {}).get("rating") is None:
                continue
            key = (a["id"], a["answer"].strip())
            if key in seen or not a["answer"].strip():
                continue
            seen.add(key)
            items.append({"task": a["id"], "candidate": d["model"],
                          "answer": a["answer"], "human": HUMAN[a["manual"]["rating"]]})
    return items


def _state(task, item):
    return TaskState(
        model=item["candidate"], sample_id=item["task"], epoch=1,
        input=task["prompt"], messages=[ChatMessageUser(content=task["prompt"])],
        output=ModelOutput.from_content(item["candidate"], item["answer"]))


async def grade_single(grader, task, item):
    sc = model_graded_qa(instructions=MANUAL_INSTRUCTIONS, grade_pattern=GRADE_PATTERN,
                         partial_credit=True, model=grader)
    score = await sc(_state(task, item), Target(_build_criterion(task["id"], task["rubric"])))
    v = score.value
    return (v if isinstance(v, str) else LETTER.get(float(v), "?")), (score.explanation or "")


async def grade_two_pass(grader, task, item):
    decisive, secondary, _ = _split_rubric(task["id"], task["rubric"])

    async def verdict(line):
        out = await grader.generate(LINE_TEMPLATE.format(
            question=task["prompt"], answer=item["answer"], line=line))
        m = VERDICT_PATTERN.search(out.completion or "")
        return None if not m else m.group(1).upper() == "YES"

    d = [await verdict(ln) for ln in decisive]
    s = [await verdict(ln) for ln in secondary]
    if not all(x is True for x in d):
        letter = "I"
    elif all(x is True for x in s):
        letter = "C"
    else:
        letter = "P"
    return letter, f"decisive={d} secondary={s}"


def agreement(pairs):
    pairs = [(a, b) for a, b in pairs if a and b and b != "?"]
    if not pairs:
        return None
    exact = sum(a == b for a, b in pairs) / len(pairs)
    lenient = sum((a == "I") == (b == "I") for a, b in pairs) / len(pairs)
    return len(pairs), exact, lenient


async def main(args):
    tasks = load_tasks()
    items = gather(tasks)
    if args.limit:
        items = items[: args.limit]
    if not items:
        sys.exit("No human-rated manual answers in results/ yet.")
    os.environ.setdefault("OPENROUTER_API_KEY", get_key() or "")
    grader = get_model(args.grader)

    modes = ["single", "two-pass"] if args.mode == "both" else [args.mode]
    for mode in modes:
        fn = grade_single if mode == "single" else grade_two_pass
        sem = asyncio.Semaphore(args.concurrency)

        async def one(it):
            async with sem:
                return await fn(grader, tasks[it["task"]], it)

        out = await asyncio.gather(*(one(it) for it in items))
        for it, (letter, why) in zip(items, out):
            it.setdefault("grades", {})[mode] = letter
            it.setdefault("why", {})[mode] = why

    print(f"{len(items)} human-rated answers, grader {args.grader}\n")
    w = max(len(i["candidate"]) for i in items)
    print(f"{'task':<26} {'candidate':<{w}} {'human':>5}  " + "  ".join(f"{m:>9}" for m in modes))
    for it in items:
        flags = "".join(" <-" if it["grades"][m] != it["human"] else "" for m in modes)
        print(f"{it['task']:<26} {it['candidate']:<{w}} {it['human']:>5}  "
              + "  ".join(f"{it['grades'][m]:>9}" for m in modes) + flags)

    print("\nAgreement with the human rating (exact; lenient treats C and P alike):")
    for m in modes:
        r = agreement([(it["human"], it["grades"][m]) for it in items])
        print(f"  {m:<9} n={r[0]:<3} exact={r[1]:.0%}  lenient={r[2]:.0%}")

    print("\nBy human rating, since the set is skewed:")
    for human in ("C", "P", "I"):
        subset = [it for it in items if it["human"] == human]
        if not subset:
            continue
        line = f"  human={human} n={len(subset):<3}"
        for m in modes:
            hit = sum(it["grades"][m] == human for it in subset)
            line += f"  {m}: {hit}/{len(subset)}"
        print(line)
        for m in modes:
            wrong = Counter(it["grades"][m] for it in subset if it["grades"][m] != human)
            if wrong:
                print(f"      {m} said instead: {dict(wrong)}")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    out_path = HERE / f"calibration_{stamp}.json"
    out_path.write_text(json.dumps(
        {"grader": args.grader, "modes": modes, "items": items},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWritten: {out_path.relative_to(HERE.parent)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--grader", required=True, help="e.g. openrouter/deepseek/deepseek-v4-flash")
    ap.add_argument("--mode", choices=["single", "two-pass", "both"], default="both")
    ap.add_argument("--limit", type=int, default=0, help="only the first N answers")
    ap.add_argument("--concurrency", type=int, default=4)
    asyncio.run(main(ap.parse_args()))
