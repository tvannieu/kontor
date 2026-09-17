# evals — the task set

Teil des Kontor-Repositories. Übersicht: [`../README.md`](../README.md), Einordnung: [`../docs/choosing-a-model.md`](../docs/choosing-a-model.md).

## Was das hier ist

Eine **feste Aufgabensammlung**, die bei jedem neuen Sprachmodell unverändert durchläuft. Angelegt im September 2026, weil „ich teste neue Modelle" ohne feste Aufgaben und aufgehobene Ergebnisse ein Eindruck bleibt und keine Aussage wird.

Der Gedanke ist derselbe wie in dem Framework-Zweig, aus dem die Methode stammt: dieselbe Aufgabe, mehrere unabhängige Implementierungen, systematischer Vergleich. Dort sechs Streucodes, hier Modelle.

## Die eine Regel, die alles trägt

🔴 **Prompts werden nicht nachgebessert, wenn ein Modell durchfällt.**

Wer eine Aufgabe ändert, legt eine **neue** an und lässt die alte stehen. Sonst misst die Sammlung irgendwann nur noch sich selbst, und alle früheren Läufe werden wertlos.

Das gilt auch für dich als Agent: **`tasks/*.json` nie stillschweigend anfassen.**

## Was hier gemessen wird

Nicht in erster Linie, ob ein Modell die richtige Antwort findet, sondern **ob es zugibt, wenn es keine gibt.** Drei der Aufgaben (`01`, `02`, `06`) haben keine ermittelbare Lösung oder enthalten eine Falle — wie viele es insgesamt sind, sagt `ls tasks/`, nicht diese Zeile. Eine plausible erfundene Zahl ist ein Durchfallen, kein Teilerfolg.

Das ist die Fehlerform, um die es geht: diese Systeme scheitern nicht mit einer Fehlermeldung, sondern mit einer plausiblen falschen Antwort.

## Arbeitsregeln

- **Ergebnisse werden committet**, auch die schlechten Läufe. Ein weggeworfener Lauf ist ein verfälschter Vergleich.
- **Ein Modell pro Lauf nur einmal.** Schwankungen gehören in die Notiz, nicht in einen zweiten Versuch.
- **Neue Aufgaben kommen aus echter Arbeit**, nicht aus Rätselsammlungen. Wenn etwas im Streucode-Vergleich, im Forschungszweig oder im Agentensystem tatsächlich schiefgegangen ist, ist es ein Kandidat.
- `temperature=0`, damit Läufe vergleichbar bleiben. Nicht ändern.

## Schlüssel

Der OpenRouter-Schlüssel liegt im macOS-Schlüsselbund unter **`kontor-openrouter`**, derselbe, den `kontor/distribute_crush_config.sh` in die crush.json schreibt. `run.py` holt ihn von dort; ersatzweise `OPENROUTER_API_KEY`. **Der Schlüssel gehört nicht in eine Datei.**

## Struktur

| Pfad | Inhalt |
|---|---|
| `tasks/` | eine Datei je Aufgabe, versioniert, unveränderlich |
| `results/` | ein Ergebnis je Lauf, benannt nach Zeitstempel und Modell |
| `run.py` | Läufer über OpenRouter |
| `report.py` | Gegenüberstellung aller Läufe |

## Wozu es dient

Zwei Zwecke, und der zweite ist der wichtigere.

1. **Auswahl:** welches Modell für welche Aufgabe im Kontor taugt. Die crush.json führt mehrere Anbieter und Preisstufen; welche Stufe wo reicht, ist bisher Gefühl.
2. **Belegbarkeit:** Erfahrung mit Evaluation zu behaupten ist leicht. Nach ein paar Läufen ist das hier keine Behauptung mehr.

---
## Document Information
*Last Updated: September 12, 2026* *Document Type: Guide* *Scope: Arbeitsanweisung für Agenten in model-evals* *Status: Active Documentation*
