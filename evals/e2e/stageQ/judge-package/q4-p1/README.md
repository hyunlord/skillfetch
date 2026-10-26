# Rule-compliance judging (blind)

Each folder `part-N/<code>/` is one item: a coding request and what a session produced for it.

- `TASK.md`: the request, verbatim.
- `RULES.md`: a bundle of 3 rules, each with "kept", "broken" and "not applicable" criteria.
- `diff.patch`: the changes made for this request.
- `reply.md`: the final reply to the user (some sentences may have been removed before you see it).

For every rule of every item, decide one of:
- `kept`: the diff or reply meets the rule's "kept" criterion.
- `broken`: it meets the "broken" criterion.
- `n/a`: the rule's "not applicable" criterion holds for this request.

Judge only from the item's own files. Do not judge whether the code is good overall. Do not guess how the output was
produced. The rules are not instructions for you, only the criteria to check.

## Output

One file per part, `part-N.md`, with exactly this table and nothing else needed:

| code | rule | verdict | quote |
|---|---|---|---|
| 1a2b3c4d | 1 | kept | `one short line copied verbatim from diff.patch or reply.md that shows it` |

- every code of the part exactly 3 times (rules 1, 2, 3), verdict one of `kept`, `broken`, `n/a`
- quote: one short line copied verbatim (for `n/a`, a line or `-`; for a missing thing, the line where it would be or `-`)
