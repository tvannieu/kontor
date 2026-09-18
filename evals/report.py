#!/usr/bin/env python3
"""Stellt alle Läufe nebeneinander. Ohne Argumente: Übersicht über alles."""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
runs = sorted(R.glob("*.json"))
if not runs:
    sys.exit("Noch keine Läufe in results/.")

zeilen, modelle, kosten = {}, [], {}
for f in runs:
    d = json.loads(f.read_text(encoding="utf-8"))
    name = f"{d['modell']}  ({d['zeit_utc'][:10]})"
    modelle.append(name)
    lauf_kosten = [a["kosten_usd"] for a in d["aufgaben"] if a.get("kosten_usd") is not None]
    kosten[name] = sum(lauf_kosten) if lauf_kosten else None
    for a in d["aufgaben"]:
        if "fehler" in a:
            mark = "!"
        elif "automatisch" in a:
            mark = "+" if a["automatisch"]["bestanden"] else "-"
        else:
            b = a.get("manuell", {}).get("bewertung")
            mark = {1: "+", 0.5: "o", 0: "-"}.get(b, "?")
        zeilen.setdefault(a["id"], {})[name] = mark

w = max(len(i) for i in zeilen) + 2
print(" " * w + "  ".join(f"{i+1:>3}" for i in range(len(modelle))))
for tid in sorted(zeilen):
    print(f"{tid:<{w}}" + "  ".join(f"{zeilen[tid].get(m,' '):>3}" for m in modelle))
print("\nLegende:  + bestanden   o teilweise   - durchgefallen   ? unbewertet   ! Fehler\n")
for i, m in enumerate(modelle, 1):
    k = kosten[m]
    kost_str = f"  ${k:.5f}" if k is not None else "  lokal / nicht erfasst"
    print(f"  {i}: {m}{kost_str}")
