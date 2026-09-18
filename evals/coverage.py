#!/usr/bin/env python3
"""Welche Profil-Modell-Zuordnung in profiles.conf ist durch Laeufe belegt, und
welche ist eine Schaetzung?

choosing-a-model.md sagt offen, dass die Modellwahl je Profil derzeit eine
Schaetzung ist. Dieses Skript macht daraus eine pruefbare Aussage: fuer jedes
Profil das zugewiesene (grosse) Modell, die Aufgaben, die dieses Profil tragen,
und ob es fuer genau dieses Modell auf genau diesen Aufgaben einen Lauf in
results/ gibt -- und wie der ausging.

Zweiter Teil, die Vertraulichkeitsachse: ein local-first-Zweig darf ein
gehostetes Modell nicht als Standard haben (tools/kontor verweigert das). Fuer
Profile, die auf ein gehostetes Modell zeigen, steht hier, ob ueberhaupt ein
lokales Modell auf deren Aufgaben belegt ist -- also ob ein local-first-Zweig
diese Art Arbeit mit nachgewiesener Faehigkeit lokal erledigen koennte, oder ob
er dort schlicht geraten muss.

Liest nur results/*.json (die dauerhafte, versionierte Evidenz) und die
Instanzkonfiguration. Kein Modellaufruf, keine Kosten.
"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS, RESULTS = ROOT / "tasks", ROOT / "results"
PROFILES = Path(os.environ.get("KONTOR_PROFILES", os.path.expanduser("~/.config/kontor/profiles.conf")))


def norm(model):
    """'ollama/kontor-4b:latest' und 'kontor-4b:latest' meinen dasselbe Modell;
    aeltere Laeufe schrieben den Namen ohne Anbieter-Praefix. 'crush/' ist
    kein Anbieter, sondern das Geschirr (run.py, ask_crush) -- darunter steht
    das Modell so, wie profiles.conf es nennt."""
    return re.sub(r"^(ollama|crush)/", "", model)


def load_profiles():
    if not PROFILES.is_file():
        sys.exit(f"keine profiles.conf unter {PROFILES} (siehe tools/profiles.conf.example)")
    out = {}
    for line in PROFILES.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "profile":
            out[parts[1]] = {"gross": parts[2], "klein": parts[3]}
    return out


def load_tasks():
    out = {}
    for f in sorted(TASKS.glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        out[t["id"]] = t.get("profile", [])
    return out


def verdict(a):
    if "fehler" in a:
        return "fehler"
    if "automatisch" in a:
        return "+" if a["automatisch"]["bestanden"] else "-"
    b = a.get("manuell", {}).get("bewertung")
    return {1: "+", 0.5: "o", 0: "-"}.get(b, "?")


def load_results():
    """(normiertes Modell, Aufgabe) -> Liste von (Datum, Urteil)."""
    out = {}
    for f in sorted(RESULTS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue  # abgebrochener Lauf; steht in results/, ist aber kein Beleg
        m = norm(d["modell"])
        for a in d["aufgaben"]:
            out.setdefault((m, a["id"]), []).append((d["zeit_utc"][:10], verdict(a)))
    return out


def evidence(results, model, task):
    """Nur echte Urteile zaehlen. Ein HTTP-Fehler ist kein Beleg, ein
    unbewerteter manueller Lauf auch nicht."""
    return [(dt, v) for dt, v in results.get((norm(model), task), []) if v in "+o-"]


def main():
    profiles, tasks, results = load_profiles(), load_tasks(), load_results()
    by_profile = {}
    for tid, profs in tasks.items():
        for p in profs:
            by_profile.setdefault(p, []).append(tid)

    print("Belegt oder geschaetzt?  Je Profil: das zugewiesene grosse Modell gegen\n"
          "die Aufgaben, die dieses Profil tragen, nach results/.\n")
    for p, spec in profiles.items():
        model = spec["gross"]
        tids = sorted(by_profile.get(p, []))
        print(f"== {p}  ->  {model} ==")
        gepr, best, durch, fehl = 0, 0, 0, 0
        for tid in tids:
            ev = evidence(results, model, tid)
            if not ev:
                # "nie versucht" und "versucht, aber nur Fehler" sind zwei
                # verschiedene Ergebnisse; das zweite heisst meist: das Modell ist
                # ueber das Geschirr, das es erreicht, gerade nicht ansprechbar.
                runs = results.get((norm(model), tid), [])
                if runs:
                    fehl += 1
                    print(f"  {tid:<24} Fehler, kein Beleg  ({len(runs)} Lauf/Laeufe, zuletzt {runs[-1][0]})")
                else:
                    print(f"  {tid:<24} ungeprueft")
                continue
            gepr += 1
            dt, v = ev[-1]
            if v == "+": best += 1
            elif v == "-": durch += 1
            print(f"  {tid:<24} {v}  ({dt}" + (f", {len(ev)} Laeufe" if len(ev) > 1 else "") + ")")
        if not tids:
            print("  (keine Aufgabe traegt dieses Profil)")
        elif gepr == 0 and fehl:
            urteil = f"SCHAETZUNG -- {fehl} von {len(tids)} versucht, nur Fehler, kein einziges Urteil"
        elif gepr == 0:
            urteil = "SCHAETZUNG -- kein einziger Lauf mit diesem Modell auf diesen Aufgaben"
        elif durch:
            urteil = f"belegt, mit Durchfall: {gepr} von {len(tids)} geprueft, {best} bestanden, {durch} durchgefallen"
        else:
            urteil = f"belegt: {gepr} von {len(tids)} geprueft, alle bestanden" + (
                "" if gepr == len(tids) else f" -- {len(tids) - gepr} noch ungeprueft")
        print(f"  => {urteil}\n")

    print("Vertraulichkeitsachse: Profile mit gehostetem Modell, und ob ein lokales\n"
          "Modell auf deren Aufgaben ueberhaupt belegt ist. Ein local-first-Zweig\n"
          "darf das gehostete Modell nicht als Standard haben; hier steht, ob er\n"
          "stattdessen auf nachgewiesene lokale Faehigkeit zurueckgreifen kann.\n")
    # Nach norm() traegt ein lokales Modell keinen Anbieter-Praefix mehr;
    # alles mit Schraegstrich ist gehostet.
    local_models = sorted({m for (m, _) in results if "/" not in m})
    for p, spec in profiles.items():
        model = spec["gross"]
        if model.startswith("ollama/"):
            continue
        tids = sorted(by_profile.get(p, []))
        print(f"== {p}  ({model}, gehostet) ==")
        any_local = False
        for lm in local_models:
            hits = [(tid, evidence(results, lm, tid)) for tid in tids]
            hits = [(tid, ev[-1][1]) for tid, ev in hits if ev]
            if hits:
                any_local = True
                print(f"  lokal belegt: {lm}  " + "  ".join(f"{tid} {v}" for tid, v in hits))
        if not any_local:
            print("  kein lokales Modell auf einer dieser Aufgaben belegt -- ein local-first-Zweig\n"
                  "  muesste hier raten, nicht messen")
        print()


if __name__ == "__main__":
    main()
