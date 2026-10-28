# Index review

The semantic review (`scan --review`, docs/design/review.md) over the released index, in two
stages: SKILL.md only for every canonical skill, then all text files for the skills flagged or
warned about remote instructions. Results and method: numbers.md §32.

- `run.py`: the stages (`stage1`, `stage2`), their targets and the export.
- `results-stage1.jsonl`, `results-stage2.jsonl`: one derived row per skill (flagged,
  categories, file:line, incomplete, partly reviewed, requests, cost). The reviewer's quoted
  lines and reasons stay out of the repo.
- `judgements.yaml`: the user's judgement of each flagged skill; §32 quotes one public line of
  each.
