# tools

One file each, configuration from outside the repository, no shared runtime. Most
need nothing but git and a shell; the exceptions are noted.

| | |
|---|---|
| [`check-public.sh`](check-public.sh) | the publication gate. Refuses to push if anything private is in a file or a commit message, and refuses to run at all against an empty wordlist. Wire it as `.git/hooks/pre-push` |
| [`check-public-selftest.sh`](check-public-selftest.sh) | proves the gate can still say no, by planting a term it must catch |
| [`census.sh`](census.sh) | the numbers quoted in the documentation, each with the definition used |
| [`kontor`](kontor) | the profile switcher and the local-first guard. Needs `crush` and Ollama |
| [`distribute_manifest.sh`](distribute_manifest.sh), [`distribute_crush_config.sh`](distribute_crush_config.sh) | push generated files into every branch. The second needs `crush` |
| [`mail-reader.py`](mail-reader.py) | read, search and archive mail. macOS: Mail.app and the Keychain |
| [`archive-sent.sh`](archive-sent.sh) | file a sent draft into the record, dated, without overwriting |
| [`letter_pdf.py`](letter_pdf.py) | a DIN 5008 letter as a PDF. Standard library only |
| [`ocr_vision.swift`](ocr_vision.swift) | OCR a PDF locally. macOS: Apple's Vision framework |
| `*.example` | the shape of each file in `~/.config/kontor/`; copy and fill in |
| `test_*.py` | run them directly, no framework and no network |

`deny.txt` and `vocab.txt` are **not** here and never should be: a list of the names
you are protecting publishes the names. See [`../docs/adopting.md`](../docs/adopting.md).

---
← [README](../README.md)
