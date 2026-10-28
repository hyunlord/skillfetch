# Scan accuracy

How often `skillfetch scan` catches what it should (recall) and how often its warnings are worth
a reviewer's look (precision). Results and method: numbers.md §30. No model call is needed to
rerun the recall numbers; the precision verdicts came from two isolated `claude -p` judges per
item.

- `recall/dev.yaml`, `recall/eval.yaml`: 80 hand-written skills (40 risky, 40 harmless
  lookalikes), each with `expect` (catch or pass) and the reason. Every URL is on
  example.invalid; nothing runs. `recall/FROZEN-eval.sha256` fixed the evaluation half before
  any rule changed; `scripts/scan_accuracy.py recall --split eval` refuses a changed file and
  prints its cases only with `--final`.
- `precision/sample.py`: the stratified sample of the released index's warnings (scan rules
  v6), split into development and evaluation halves. `sample.jsonl` holds ids, rules and
  file:line locations only, no skill text.
- `precision/judge.py`: the two judges, with their prompt. `verdicts.jsonl`, `verdicts-new.jsonl`:
  verdict and kind per item and judge (the judges' reasons quote skill text and are not
  published).
- `precision/rescore.py`: which sampled warnings the current rules still raise
  (`flagged-now.jsonl`) and the warnings they add (`new.jsonl`, judged into
  `verdicts-new.jsonl`).
- `precision/results.json`: `scripts/scan_accuracy.py precision`.
- `independent/set/`: the independent set, 80 skills (40 risky, 40 harmless lookalikes, two with
  a `references/policy.md`) written by GPT without seeing the scan rules, with its `cases.jsonl`
  (label, path, reason) and `SHA256SUMS`, as delivered. Every URL is on example.invalid; there
  are no scripts. `independent/FROZEN.sha256` fixed it before rules v8 were final; v8 was
  committed before the set was opened, each rules version ran once, and no rule was changed
  from it. `scripts/scan_accuracy_versions.sh independent/set` runs v6, v7 and v8 each under its
  own code into `independent/results-vN.json` (by warning) and `independent/advice-vN.json` (by
  advice); `scripts/scan_accuracy.py independent-summary` prints the §30 tables, with the
  categories of `independent/categories.yaml` (assigned after the runs).

These folders hold SKILL.md files that ask for risky things on purpose. Do not install them.
