#!/usr/bin/env python3
"""Stage Q, Q4 (DESIGN §4). Parse stageQ-private/judge/q4-<pass>/part-N.md and validate them BEFORE reading the key:
every code of the part's folder exactly 3 rows (rules 1, 2, 3), verdict in kept / broken / n/a. Then join with
stageQ-private/keys/q4-key-<pass>.jsonl -> stageQ-private/judge/scores-q4-<pass>.jsonl
{code, request, job, tag, k, task, skill, cond, rules_source, rule, verdict, quote}.
usage: unblind_q4.py <pass>"""
import json
import re
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
PRIV = SQ.parent / "stageQ-private"
pas = sys.argv[1]
pkg = SQ / "judge-package" / f"q4-{pas}"
rows, problems = [], []
for part in sorted(p for p in pkg.iterdir() if p.is_dir()):
    codes = {p.name for p in part.iterdir() if p.is_dir()}
    f = PRIV / "judge" / f"q4-{pas}" / f"{part.name}.md"
    if not f.exists():
        problems.append(f"{part.name}: no judgment file")
        continue
    seen = {}
    for line in f.read_text().splitlines():
        m = re.match(r"\|\s*([0-9a-f]{8})\s*\|\s*(\d)\s*\|\s*([^|]+?)\s*\|(.*)\|\s*$", line)
        if not m:
            continue
        code, rule, verdict, quote = m.group(1), int(m.group(2)), m.group(3).strip().lower(), m.group(4).strip()
        if verdict not in ("kept", "broken", "n/a"):
            problems.append(f"{part.name}: {code} rule {rule}: bad verdict {verdict!r}")
        if (code, rule) in seen:
            problems.append(f"{part.name}: {code} rule {rule} twice")
        seen[(code, rule)] = (verdict, quote)
    want = {(c, r) for c in codes for r in (1, 2, 3)}
    if set(seen) != want:
        problems.append(f"{part.name}: rows mismatch (missing {len(want - set(seen))}, extra {len(set(seen) - want)})")
    rows += [{"code": c, "rule": r, "verdict": v, "quote": q} for (c, r), (v, q) in seen.items()]
if problems:
    sys.exit("format problems (key not read):\n" + "\n".join(problems))
key = {k["code"]: k for k in map(json.loads, (PRIV / "keys" / f"q4-key-{pas}.jsonl").open())}
out = [{**{x: key[r["code"]][x] for x in ("request", "job", "tag", "k", "task", "skill", "cond", "rules_source")}, **r}
       for r in rows]
(PRIV / "judge" / f"scores-q4-{pas}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print(f"q4-{pas}: {len(out)} rule verdicts for {len({r['code'] for r in out})} items")
