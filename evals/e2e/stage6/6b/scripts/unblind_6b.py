#!/usr/bin/env python3
"""Parse judge outputs judge/p<N>/<task>.md (rubric format), validate them BEFORE reading the key (every code of the set
exactly once in the table, score in 1-5, rank lines present), then join with keys/blind-key-p<N>.jsonl.
Score column: bundle (1) "(b) 쓸만함 1-5" (and "(a) AI느낌 수"), bundles (2)/(3) "총점 1-5".
Writes judge/scores-p<N>.jsonl {code, task, bundle, cond, rep, score, ai_look}. usage: unblind_6b.py <N>"""
import json
import re
import sys
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
n = int(sys.argv[1])
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6B / "tasks.jsonl").open()}
blind = S6B / f"blind-p{n}"
rows, problems = [], []
for tid, t in tasks.items():
    codes = {p.name for p in (blind / tid).iterdir() if p.is_dir() and p.name != "_context"}
    f = S6B / "judge" / f"p{n}" / f"{tid}.md"
    if not f.exists():
        problems.append(f"{tid}: no judgment file")
        continue
    lines = f.read_text().splitlines()
    head = next((l for l in lines if l.startswith("| code |")), None)
    if not head:
        problems.append(f"{tid}: no table header")
        continue
    cols = [c.strip() for c in head.strip("|").split("|")]
    sc = cols.index("(b) 쓸만함 1-5") if t["bundle"] == 1 else cols.index("총점 1-5")
    ai = cols.index("(a) AI느낌 수") if t["bundle"] == 1 else None
    seen = {}
    for l in lines:
        m = re.match(r"\|\s*([0-9a-f]{8})\s*\|", l)
        if m:
            cells = [c.strip() for c in l.strip("|").split("|")]
            if m.group(1) in seen:
                problems.append(f"{tid}: code {m.group(1)} twice")
            seen[m.group(1)] = (int(cells[sc]), int(cells[ai]) if ai is not None else None)
    if set(seen) != codes:
        problems.append(f"{tid}: codes mismatch (missing {sorted(codes - set(seen))}, extra {sorted(set(seen) - codes)})")
    if any(not 1 <= s <= 5 for s, _ in seen.values()):
        problems.append(f"{tid}: score out of range")
    if not any(re.match(r"^\d+\.\s", l) for l in lines):
        problems.append(f"{tid}: no rank lines")
    for code, (s, a) in seen.items():
        rows.append({"code": code, "task": tid, "score": s, "ai_look": a})
if problems:
    sys.exit("format problems (key not read):\n" + "\n".join(problems))
key = {json.loads(l)["code"]: json.loads(l) for l in (S6B / "keys" / f"blind-key-p{n}.jsonl").open()}
out = [{**r, **{k: key[r["code"]][k] for k in ("bundle", "cond", "rep")}} for r in rows]
assert all(key[r["code"]]["task"] == r["task"] for r in rows)
(S6B / "judge" / f"scores-p{n}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print(f"p{n}: {len(out)} scores")
