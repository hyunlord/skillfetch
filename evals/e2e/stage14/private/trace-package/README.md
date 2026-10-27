# Trace check

Each folder is one output (`diff.patch`) of one request (`TASK.md`) in a longer conversation. `skills.md` lists skills
(instruction packs) that were used earlier in the same conversation, for other requests, with a one-line description.

For each listed skill, decide whether this diff shows that skill's rules or style applied to this request although the
request did not need them (examples: design-system or visual rules in backend code, a testing methodology's file layout
in a docs change, the skill's name in comments or files). Ordinary good practice that any engineer would use for this
request is not a trace.

Write `<folder>.json` into the output folder you are given:
{"skills": [{"name": "<skill>", "trace": "yes" | "no", "quote": "<exact text copied from diff.patch that shows it, or empty>"}]}
Every listed skill exactly once. A "yes" needs a quote copied exactly from `diff.patch` (one line or part of a line).
