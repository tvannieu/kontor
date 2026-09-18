#!/usr/bin/env python3
"""Re-run the eval tasks against both Ollama models.

kontor-8b:latest needs num_ctx=4096 (16K doesn't fit in the machine's current
memory state — it's loaded at 6.5GB, only ~148MB free, load avg 24/29/18).
kontor-4b:latest works fine with defaults.

Saves to evals/results/<timestamp>_<model>.json, same format as run.py.

Usage:
    python3 re_run_ollama.py          # runs both models, all tasks
    python3 re_run_ollama.py 4b      # only 4b
    python3 re_run_ollama.py 8b      # only 8b
    python3 re_run_ollama.py 4b 02 05  # only 4b, tasks 02 and 05
"""
import json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"
RESULTS_DIR = ROOT / "results"
OLLAMA = "http://127.0.0.1:11434/v1/chat/completions"

sys.path.insert(0, str(ROOT))
from run import CHECKS  # noqa: E402 -- same checks run.py uses, not a second copy

TASK_IDS = sorted(t.stem for t in TASKS_DIR.glob("*.json"))
TASK_PROMPTS = {tid: json.loads((TASKS_DIR / f"{tid}.json").read_text(encoding="utf-8"))
                for tid in TASK_IDS}

def call_ollama(model, prompt, num_ctx=None, timeout=600):
    body = {
        "model": model,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if num_ctx:
        body["options"] = {"num_ctx": num_ctx}
    data = json.dumps(body).encode()
    req = urllib.request.Request(OLLAMA, data=data,
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        elapsed = round(time.time() - t0, 1)
        msg = d["choices"][0]["message"]
        text = msg.get("content") or msg.get("reasoning") or ""
        usage = d.get("usage", {})
        return text, elapsed, usage, None
    except urllib.error.HTTPError as e:
        return None, None, None, f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}"
    except TimeoutError:
        return None, round(time.time()-t0, 1), None, f"timeout after {round(time.time()-t0,1)}s"
    except Exception as e:
        return None, round(time.time()-t0, 1), None, str(e)

def run_model(model, task_ids, num_ctx=None):
    print(f"\n{'='*60}")
    print(f"Model: {model}  tasks: {task_ids}  num_ctx: {num_ctx}")
    print(f"{'='*60}")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    run = {"model": f"ollama/{model}", "time_utc": stamp, "tasks": []}

    for tid in task_ids:
        t = TASK_PROMPTS[tid]
        print(f"\n  {tid} ... ", end="", flush=True)
        text, dur, usage, err = call_ollama(model, t["prompt"], num_ctx, timeout=600)

        if err:
            print(f"ERROR: {err[:120]}")
            run["tasks"].append({"id": tid, "error": err[:200]})
            continue

        rec = {"id": tid, "title": t["title"], "seconds": dur,
               "tokens": usage.get("total_tokens"), "answer": text}

        check_fn = CHECKS.get(t.get("check", "manual"))
        if check_fn and t.get("expect") is not None:
            ok, note = check_fn(text, t["expect"])
            rec["auto"] = {"passed": ok, "note": note}
            print(f"{'PASS' if ok else 'FAIL'}  ({note})  {dur}s")
        else:
            rec["manual"] = {"rating": None, "rubric": t.get("rubric", []), "note": ""}
            print(f"to be rated  {dur}s")

        run["tasks"].append(rec)

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{stamp}_ollama_{model.replace(':', '_')}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWritten: {out.name}")
    return out

def main():
    only_model = sys.argv[1] if len(sys.argv) > 1 else None
    task_filter = sys.argv[2:] if len(sys.argv) > 2 else None

    if only_model and only_model not in ("4b", "8b"):
        print("Usage: python3 re_run_ollama.py [4b|8b] [task_ids...]")
        sys.exit(1)

    models = []
    if only_model == "4b" or only_model is None:
        models.append(("kontor-4b:latest", None))
    if only_model == "8b" or only_model is None:
        models.append(("kontor-8b:latest", 4096))

    for model, num_ctx in models:
        ids = TASK_IDS if task_filter is None else [t for t in TASK_IDS if any(t.startswith(f) for f in task_filter)]
        if not ids:
            print(f"No tasks matching filter {task_filter}")
            continue
        run_model(model, ids, num_ctx)

if __name__ == "__main__":
    main()
