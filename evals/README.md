# model-evals

Eine feste Aufgabensammlung, die bei jedem neuen Modell unverändert durchläuft.

## Warum

Zu sagen „ich teste neue Modelle" kann jeder. Was kaum jemand tut, weil es Arbeit ist: **immer dieselben Aufgaben, immer gleich bewertet, Ergebnisse aufgehoben.** Erst dadurch wird aus einem Eindruck eine Aussage.

Es ist derselbe Gedanke wie im Streucode-Vergleich: dieselbe Aufgabe, mehrere unabhängige Implementierungen, systematischer Vergleich. Dort waren es sechs Streucodes, hier sind es Sprachmodelle.

## Was hier besonders ist

Die meisten Sammlungen messen, ob ein Modell die richtige Antwort findet. **Diese misst vor allem, ob es zugibt, wenn es keine gibt.** Drei der Aufgaben haben keine ermittelbare Lösung oder enthalten eine Falle — wie viele es insgesamt sind, sagt `ls tasks/`, nicht diese Zeile:

- `02_unanswerable` fragt nach einem Wert, den die Daten nicht hergeben. Nennt das Modell eine Zahl, ist es durchgefallen, egal wie plausibel sie ist.
- `01_frame_consistency` zeigt zwei Ergebnisse, die sich nur im Vorzeichen einer Größe unterscheiden. Erfindet das Modell einen Umrechnungsfaktor, ist es durchgefallen.
- `06_kontext_treue` enthält eine Jahreszahl, die vom Weltwissen abweicht. Das Modell soll beim Text bleiben.

Das ist die Fehlerform, auf die es ankommt: diese Systeme scheitern nicht mit einer Fehlermeldung, sondern mit einer plausiblen falschen Antwort.

## Benutzung

```bash
./run.py anthropic/claude-sonnet-4.5     # alle Aufgaben
./run.py openai/gpt-5 --tasks 02 05      # nur einzelne
./run.py --dry-run                       # zeigt nur, was gesendet würde, ohne Schlüssel
./report.py                              # alle Läufe nebeneinander
```

**Der Schlüssel steht in keiner Datei.** `run.py` holt ihn aus dem Schlüsselbund des Betriebssystems und fällt erst danach auf eine Umgebungsvariable zurück:

```bash
security add-generic-password -a "$USER" -s kontor-openrouter -w   # fragt nach, nicht in der History
```

Damit liegt der Schlüssel weder im Repository noch in einer Shell-Konfiguration, und ein versehentliches `git add` kann ihn nicht erfassen. Die Umgebungsvariable `OPENROUTER_API_KEY` funktioniert weiterhin, ist aber der Notnagel und nicht der Weg.

Über **OpenRouter** liegen neue Modelle meist binnen Stunden nach der Veröffentlichung an, gegen Abrechnung pro Token statt pro Abonnement. Ein Durchlauf kostet je nach Modell wenige Cent.

`temperature=0`, damit Läufe vergleichbar bleiben.

## Bewertung

Vier Aufgaben prüfen sich selbst (`contains_any`, `regex_absent`, `json_schema`). Drei brauchen ein Urteil; dafür steht in jeder Aufgabe eine **Rubrik**, und im Ergebnis ein Feld `manuell.bewertung`, das mit `1`, `0.5` oder `0` zu füllen ist.

Dass ein Teil von Hand bewertet wird, ist kein Mangel. Genau dort liegt die Frage, die sich nicht automatisieren lässt.

## Aufbau

```
tasks/      eine Datei je Aufgabe, versioniert. Prompts werden nicht still geändert;
            wer etwas ändert, legt eine neue Aufgabe an
results/    ein Ergebnis je Lauf, Dateiname aus Zeitstempel und Modell
run.py      Läufer
report.py   Gegenüberstellung
```

## Regeln, damit es etwas wert bleibt

1. **Prompts nicht nachbessern, wenn ein Modell durchfällt.** Sonst misst die Sammlung nur noch sich selbst.
2. **Ergebnisse committen**, auch die schlechten Läufe.
3. **Neue Aufgaben kommen aus echter Arbeit**, nicht aus Rätselsammlungen.
4. Bei jedem Lauf **dasselbe Modell nur einmal**; Schwankungen gehören in die Notiz, nicht in einen zweiten Versuch.
