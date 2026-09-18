#!/usr/bin/env python3
"""
Läuft die feste Aufgabensammlung gegen ein Modell und legt das Ergebnis ab.

    ./run.py anthropic/claude-sonnet-4.5
    ./run.py openai/gpt-5 --tasks 02 05
    ./run.py ollama/kontor-4b --profile filing   nur die Aufgaben, die Ablage-Arbeit betreffen
    ./run.py crush/hyper/glm-5.3 --profile analysis   durch den Agenten-Runner, für Anbieter, die nur er erreicht

Ohne Schlüssel:  ./run.py --dry-run   zeigt, was gesendet würde.
"""
import argparse, atexit, json, os, shutil, subprocess, sys, tempfile, time, re, urllib.request, urllib.error
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


_CRUSH_CWD = None


def ask_crush(name, prompt, timeout):
    """Ein 'crush/'-Präfix bedeutet: durch den Agenten-Runner, nicht direkt.

    Nötig für Anbieter, die nur crush selbst erreicht -- die Hyper-Modelle
    sprechen Charms eigenes Protokoll, nicht das OpenAI-Format, und crush
    hält das Login dazu. Zwei Einschränkungen, die im Ergebnis stehen müssen:
    die Temperatur ist nicht steuerbar (Anbieter-Standard, nicht 0), und
    crush legt seinen Agenten-Systemprompt vor die Aufgabe. Läufe hierüber
    sind deshalb ein anderes Geschirr als die direkten Aufrufe und werden
    im Ergebnis als solches markiert.

    crush liest seine Anbieter aus der crush.json des Arbeitsverzeichnisses,
    darum bekommt ein Wegwerf-Verzeichnis eine Kopie der von Kontor
    verteilten -- so landet auch die Sitzungsdatenbank dort und nicht im
    Repository."""
    global _CRUSH_CWD
    if _CRUSH_CWD is None:
        _CRUSH_CWD = tempfile.mkdtemp(prefix="kontor-evals-crush-")
        shutil.copy(ROOT.parent / "crush.json", _CRUSH_CWD)
        atexit.register(shutil.rmtree, _CRUSH_CWD, ignore_errors=True)
    crush = os.environ.get("KONTOR_CRUSH", "crush")
    t0 = time.time()
    r = subprocess.run([crush, "run", "-q", "-c", _CRUSH_CWD, "-m", name, prompt],
                       capture_output=True, text=True, timeout=timeout, cwd=_CRUSH_CWD)
    if r.returncode != 0:
        raise RuntimeError(f"crush run: {r.stderr.strip()[:300]}")
    return r.stdout.strip(), round(time.time() - t0, 1), {}


def ask(model, prompt, key, temperature=0.0, timeout=600):
    """Ein 'ollama/'-Präfix bedeutet: lokal, und zwar ausschliesslich.

    Früher wurde erst OpenRouter versucht und bei HTTP 400 lokal nachgefasst,
    mit unverändertem Modellnamen -- den Ollama nicht kennt. Der zweite Fehler
    wurde dann von einem nackten `except Exception: pass` verschluckt und der
    erste gemeldet. Die Fehlermeldung zeigte damit auf den falschen Dienst.
    Jetzt wird geroutet statt geraten, und ein lokaler Fehler wird als lokaler
    Fehler gemeldet."""
    if model.startswith("crush/"):
        return ask_crush(model.split("/", 1)[1], prompt, timeout)
    local = model.startswith("ollama/")
    name = model.split("/", 1)[1] if local else model
    payload = {
        "model": name,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if not local:
        # OpenRouter only returns usage.cost when explicitly asked; Ollama
        # has no such concept and ignores an unknown field harmlessly, but
        # local calls are free anyway so there is nothing to request.
        payload["usage"] = {"include": True}
    body = json.dumps(payload).encode()

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
    # Zwei optionale Zusaetze (18.09.2026, fuer Aufgabe 10): Schluessel, die
    # null sein MUESSEN -- weil der Text den Wert nicht hergibt und jede Zahl
    # dort erfunden waere -- und Listen, die bestimmte Eintraege enthalten
    # muessen. Aufgabe 04 kann eine ehrlich markierte Luecke nicht von einem
    # plausiblen Ratewert unterscheiden; hiermit kann es eine Aufgabe.
    for k in expect.get("null", []):
        if k not in o:
            return (False, f"{k} fehlt")
        if o[k] is not None:
            return (False, f"{k} ist {o[k]!r}, aber der Text gibt keinen Wert her: erfunden")
    for k, items in expect.get("list_contains", {}).items():
        have = o.get(k) if isinstance(o.get(k), list) else []
        missing = [i for i in items if i not in have]
        if missing:
            return (False, f"{k} nennt nicht: {missing}")
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
    if not key and not a.model.startswith(("ollama/", "crush/")):
        sys.exit("Kein OpenRouter-Schlüssel gefunden.\n"
                 "Kontor legt ihn im Schlüsselbund unter 'kontor-openrouter' ab:\n"
                 "  security find-generic-password -s kontor-openrouter -w\n"
                 "Alternativ:  export OPENROUTER_API_KEY=sk-or-...")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    run = {"modell": a.model, "zeit_utc": stamp, "aufgaben": []}
    if a.model.startswith("crush/"):
        run["geschirr"] = ("crush run: Temperatur nicht steuerbar (Anbieter-Standard, nicht 0), "
                           "Agenten-Systemprompt vor der Aufgabe, keine Token- oder Kostenzahlen. "
                           "Nicht direkt vergleichbar mit Läufen über die API.")
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
               "tokens": usage.get("total_tokens"), "kosten_usd": usage.get("cost"),
               "antwort": ans}
        kost = f"  ${rec['kosten_usd']:.5f}" if rec["kosten_usd"] is not None else ""
        fn = CHECKS.get(t["check"])
        if fn:
            ok, note = fn(ans, t["expect"])
            rec["automatisch"] = {"bestanden": ok, "notiz": note}
            print(("BESTANDEN" if ok else "DURCHGEFALLEN") + f"  ({note})  {dur}s{kost}")
        else:
            rec["manuell"] = {"bewertung": None, "rubrik": t.get("rubric", []), "notiz": ""}
            offen += 1
            print(f"zu bewerten  {dur}s{kost}")
        run["aufgaben"].append(rec)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{stamp}_{a.model.replace('/', '_')}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out.relative_to(ROOT)}")
    kosten = [r["kosten_usd"] for r in run["aufgaben"] if r.get("kosten_usd") is not None]
    if kosten:
        print(f"Kosten (OpenRouter, gemeldet): ${sum(kosten):.5f}")
    if offen:
        print(f"{offen} Aufgaben warten auf deine Bewertung. Feld 'manuell.bewertung' "
              f"auf 1, 0.5 oder 0 setzen und 'notiz' ausfüllen.")


if __name__ == "__main__":
    main()
