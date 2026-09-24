# The German suite, retired 2026-09-19

The first version of this task set, and every run made against it. Nothing here runs any more: `run.py` and the Inspect port glob `tasks/*.json` one level up, not this directory.

## Why it is retired

The tasks were written in German because the person who wrote them works in German. When the repository was prepared for publication it became clear that this made the suite unreadable to most of its potential audience, for no benefit the tasks themselves required — none of them measures anything language-specific. They were translated, and the translations are the live suite.

Translating a prompt changes the artefact being measured, so under this collection's own rule the German tasks were not edited. They were retired whole, together with their results, and the English versions are new tasks starting from zero runs.

## What is here

`tasks/` — eleven task files, `01` through `11`. Task `10` was itself already retired on 2026-09-18, one day into its life: its check required a key to be listed as uncertain on top of being null, and its prompt never said so, so a model that answered honestly failed. Task `11` is that task with the missing clause added. Both are kept, because the pair is the clearest record in this repository of a verifier being wrong about a correct answer.

`results/` — fifteen result files, 2026-09-12 to 2026-09-18, across nine models: two local (Ollama), four through OpenRouter, three through the agent runner. Manual ratings and their German rationales are intact.

## Reading them against the English suite

The English tasks carry the same numbers where the content corresponds, with two renumberings: German `11_ehrliche_luecke` is English `10_honest_gap`, and the German `10` has no English counterpart. Names were anglicised where the German name was descriptive (`05_instruktionstreue` → `05_instruction_following`, `08_ablage_entscheidung` → `08_filing_convention`, `09_stelle_nicht_im_text` → `09_citation_that_does_not_exist`).

The task IDs inside these files are the ones the results reference. They repeat the IDs used by the live English suite, which is why the two trees are kept apart: a result file belongs to whichever suite it sits beside. `report.py` and `coverage.py` read only the live `results/`, so nothing here can quietly merge into a current comparison.

## What the runs showed, in one paragraph

Every hosted model tried was competent on the mechanically checkable tasks and failed the epistemic ones: asked for a runtime the data did not support, five different models each produced a confident number from an Amdahl fit, between 5 and 17 seconds, none of them saying the question could not be answered. The local 4B model could not produce an answer at all on two tasks, regardless of token budget. That is the finding the suite was built to produce, and it reproduced across families, price tiers, and both harnesses.
