#!/usr/bin/env python3
"""
Läuft die feste Aufgabensammlung gegen ein Modell und legt das Ergebnis ab.

    ./run.py anthropic/claude-sonnet-4.5
    ./run.py openai/gpt-5 --tasks 02 05
    ./run.py ollama/kontor-4b --profile filing   nur die Aufgaben, die Ablage-Arbeit betreffen

Ohne Schlüssel:  ./run.py --dry-run   zeigt, was gesendet würde.
"""
import argparse, json, os, sys, time, re, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS, RESULTS = ROOT / "tasks", ROOT / "results"
API = "https://openrouter.ai/api/v1/chat/completions"


def load_tasks(only=None, profile=None):
    """only: Aufgaben-Präfixe. profile: nur Aufgaben, die dieses Profil betreffen.

    Ein Profil ist eine Art von Arbeit, kein Zweig. Aufgaben ohne profile-Feld
    gelten für alle — wer keine Zuordnung hat, wird nicht stillschweigend
    ausgeschlossen. Jede Prüfung hat eine Population, die sie ausschliesst;
    hier ist sie leer und das ist Absicht."""
    out = []
    for f in sorted(TASKS.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        if only and not any(t["id"].startswith(p) for p in only):
            continue
        if profile and profile not in t.get("profile", [profile]):
            continue
        out.append(t)
    return out


def ask(model, prompt, key, temperature=0.0, timeout=600):
    """Ein 'ollama/'-Präfix bedeutet: lokal, und zwar ausschliesslich.

    Früher wurde erst OpenRouter versucht und bei HTTP 400 lokal nachgefasst,
    mit unverändertem Modellnamen -- den Ollama nicht kennt. Der zweite Fehler
    wurde dann von einem nackten `except Exception: pass` verschluckt und der
    erste gemeldet. Die Fehlermeldung zeigte damit auf den falschen Dienst.
    Jetzt wird geroutet statt geraten, und ein lokaler Fehler wird als lokaler
    Fehler gemeldet."""
    local = model.startswith("ollama/")
    name = model.split("/", 1)[1] if local else model
    body = json.dumps({
        "model": name,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    if local:
        url, headers = "http://127.0.0.1:11434/v1/chat/completions", {
            "Content-Type": "application/json"}
    else:
        url, headers = API, {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kontor-evals",
            "X-Title": "model-evals",
        }

    req = urllib.request.Request(url, data=body, headers=headers)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    msg = d["choices"][0]["message"]
    # Denkende Modelle legen die Ausgabe in ein eigenes Feld und lassen
    # content leer, wenn das Token-Budget vorher aufgebraucht ist.
    text = msg.get("content") or msg.get("reasoning") or ""
    return text, round(time.time() - t0, 1), d.get("usage", {})


def check_contains_any(ans, expect):
    hits = [e for e in expect if e.lower() in ans.lower()]
    return (bool(hits), f"gefunden: {hits}" if hits else f"keiner von {expect}")


def check_regex_absent(ans, expect):
    hits = [p for p in expect if re.search(p, ans)]
    return (not hits, "sauber" if not hits else f"verboten, aber vorhanden: {hits}")


def check_json_schema(ans, expect):
    raw = ans.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    try:
        o = json.loads(raw)
    except Exception as e:
        return (False, f"kein gültiges JSON: {e}")
    missing = [k for k in expect.get("required", []) if k not in o]
    if missing:
        return (False, f"Schlüssel fehlen: {missing}")
    kinds = {"int": int, "list": list, "str": str}
    for k, want in expect.get("types", {}).items():
        if k in o and not isinstance(o[k], kinds[want]):
            return (False, f"{k} ist {type(o[k]).__name__}, erwartet {want}")
    return (True, "Schema erfüllt")


CHECKS = {"contains_any": check_contains_any,
          "regex_absent": check_regex_absent,
          "json_schema": check_json_schema}


def get_key():
    """Erst der Schlüsselbund, wie Kontor ihn benutzt, dann die Umgebungsvariable."""
    import subprocess
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "kontor-openrouter", "-w"],
            capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get("OPENROUTER_API_KEY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", help="z.B. anthropic/claude-sonnet-4.5")
    ap.add_argument("--tasks", nargs="*", help="nur diese Präfixe, z.B. 02 05")
    ap.add_argument("--profile", help="nur Aufgaben dieses Profils, z.B. filing")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tasks = load_tasks(a.tasks, a.profile)
    if not tasks:
        sys.exit("Keine Aufgaben gefunden.")

    if a.dry_run:
        for t in tasks:
            print(f"\n=== {t['id']}  ({t['check']})\n{t['prompt'][:300]}")
        print(f"\n{len(tasks)} Aufgaben.")
        return

    if not a.model:
        sys.exit("Modell angeben, z.B.:  ./run.py anthropic/claude-sonnet-4.5")
    key = get_key()
    if not key:
        sys.exit("Kein OpenRouter-Schlüssel gefunden.\n"
                 "Kontor legt ihn im Schlüsselbund unter 'kontor-openrouter' ab:\n"
                 "  security find-generic-password -s kontor-openrouter -w\n"
                 "Alternativ:  export OPENROUTER_API_KEY=sk-or-...")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    run = {"modell": a.model, "zeit_utc": stamp, "aufgaben": []}
    offen = 0

    for t in tasks:
        print(f"  {t['id']} ... ", end="", flush=True)
        try:
            ans, dur, usage = ask(a.model, t["prompt"], key)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}")
            run["aufgaben"].append({"id": t["id"], "fehler": f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"})
            continue
        except Exception as e:
            print(f"Fehler: {e}")
            run["aufgaben"].append({"id": t["id"], "fehler": str(e)})
            continue

        rec = {"id": t["id"], "titel": t["title"], "sekunden": dur,
               "tokens": usage.get("total_tokens"), "antwort": ans}
        fn = CHECKS.get(t["check"])
        if fn:
            ok, note = fn(ans, t["expect"])
            rec["automatisch"] = {"bestanden": ok, "notiz": note}
            print(("BESTANDEN" if ok else "DURCHGEFALLEN") + f"  ({note})  {dur}s")
        else:
            rec["manuell"] = {"bewertung": None, "rubrik": t.get("rubric", []), "notiz": ""}
            offen += 1
            print(f"zu bewerten  {dur}s")
        run["aufgaben"].append(rec)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{stamp}_{a.model.replace('/', '_')}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out.relative_to(ROOT)}")
    if offen:
        print(f"{offen} Aufgaben warten auf deine Bewertung. Feld 'manuell.bewertung' "
              f"auf 1, 0.5 oder 0 setzen und 'notiz' ausfüllen.")


if __name__ == "__main__":
    main()
