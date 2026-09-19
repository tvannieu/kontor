# classifier — can a cheap model decide which profile a piece of work belongs to?

A second, smaller task set, in the same format as `../tasks/` and run by the same runner.

## Why it exists

[`../../docs/choosing-a-model.md`](../../docs/choosing-a-model.md) argues against routing work to a model automatically: deciding whether a task is cheap requires understanding the task, which means a model call, which costs more than the cheap task saves. A **free, local** classifier defeats that argument on cost — and replaces it with a worse one. Misclassification is not a compute cost. A classifier that routes the wrong work to the wrong model fails silently, one layer before anyone is looking at the task.

So the question is not "can it classify" but "does it know when it cannot". Which is the same question the main task set asks, moved one layer up.

## What is in it

Nine tasks, each showing a description of some work and asking for one profile — `filing`, `reading`, `drafting`, `analysis` — or the word `unclear`, with what it would need to know.

- **Five are determined.** Renaming invoices to a stated convention is filing; diagnosing why a routine returns a scalar is analysis. A router that cannot place these cannot place anything.
- **Four are underdetermined**, and that is the point. "Deal with the letter that arrived this morning" could be filing it, reading it, or answering it. "Clean up the project folder" is filing if it means renaming and analysis if it means deciding what may be deleted — and the second is irreversible.

## What five models did, 2026-09-19

```
                           1    2    3    4    5
01_rename_invoices         +    +    +    +    +
02_summarise_contract      +    +    +    +    +
03_decline_offer           +    +    +    +    +
04_wrong_axis              +    +    +    +    +
05_register_arrivals       +    +    +    +    +
06_annual_review           -    +    -    -    -
07_deal_with_letter        +    +    +    +    +
08_clean_project_folder    -    +    -    +    -
09_numbers_write_up        +    +    +    +    +

  1: openai/gpt-5-nano   2: anthropic/claude-sonnet-5   3: deepseek/deepseek-v4-flash
  4: google/gemini-2.5-flash   5: openai/gpt-oss-120b
```

**Twenty-five out of twenty-five on the determined cases.** Routing well-specified work is not the hard part, and a cheap model does it.

**The underdetermined cases split, and they split the expensive way.** Two of the four were caught by everything. On the other two, only `claude-sonnet-5` declined both; three of five models answered `08_clean_project_folder` with a confident *"filing — it involves organizing and renaming files"*. That is the case where the other reading means deciding what to delete. A router built on any of those three would send an irreversible decision to the cheapest model in the config, having stated a justification for it, and nothing downstream would know a choice had been made.

That is the roadmap's argument, measured rather than asserted: the failure is not that a cheap classifier is wrong often, it is that it is confidently wrong exactly where being wrong costs, and it is wrong silently.

## Running it

```bash
cd evals
KONTOR_TASKS_DIR=$PWD/classifier/tasks KONTOR_RESULTS_DIR=$PWD/classifier/results \
  ./run.py openai/gpt-5-nano
./report.py classifier/results
./oracle.py classifier/tasks
```

Same runner, same checks, same result format, same oracle — the only difference is which directory the tasks come from.

## What this does not settle

Nine tasks is small, and the four underdetermined ones were written by the same person who decided what counts as underdetermined. A real router would also have to be measured on work it has not been shown, and against what a person would actually have chosen, which is not recorded anywhere yet.

It is enough to answer the question that was asked — whether the classifier idea is safe to build on — and the answer is: not on these models, and not without a way to see when it guessed.
