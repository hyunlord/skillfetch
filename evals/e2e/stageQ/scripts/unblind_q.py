#!/usr/bin/env python3
"""Stage Q, Q1 (same as stage11/scripts/unblind_s11.py). Parse judge outputs stageQ-private/judge/<pass>/<task>.md (rubric format), validate them BEFORE reading the key
(every code of the set exactly once in the table, score in 1-5, rank lines present), then join with
stageQ-private/keys/blind-key-<pass>.jsonl. Only the sets present in stageQ/judge-package/<pass>/ are read.
Score column: bundle (1) "(b) 쓸만함 1-5" (and "(a) AI느낌 수"), bundles (2)-(4) "총점 1-5" (as 6b).
Writes stageQ-private/judge/scores-<pass>.jsonl {code, task, bundle, cond (on/off), tag, score, ai_look}.
usage: unblind_q.py <pass>"""
import json
import re
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
S11 = SQ.parent / "stage11"
PRIV = SQ.parent / "stageQ-private"
sys.path.insert(0, str(S11 / "scripts"))
from run_s11 import load_tasks  # noqa: E402
pas = sys.argv[1]
tasks = load_tasks()
blind = SQ / "judge-package" / pas
rows, problems = [], []
for tdir in sorted(p for p in blind.iterdir() if p.is_dir() and p.name in tasks):
    tid, t = tdir.name, tasks[tdir.name]
    codes = {p.name for p in tdir.iterdir() if p.is_dir() and p.name != "_context"}
    f = PRIV / "judge" / pas / f"{tid}.md"
    if not f.exists():
        problems.append(f"{tid}: no judgment file")
        continue
    lines = f.read_text().splitlines()
    head = next((l for l in lines if l.startswith("| code |")), None)
    if not head:
        problems.append(f"{tid}: no table header")
        continue
    cols = [c.strip() for c in head.strip("|").split("|")]
    try:
        sc = cols.index("(b) 쓸만함 1-5") if t["bundle"] == 1 else cols.index("총점 1-5")
        ai = cols.index("(a) AI느낌 수") if t["bundle"] == 1 else None
    except ValueError:
        problems.append(f"{tid}: score column missing in {cols}")
        continue
    seen = {}
    for l in lines:
        m = re.match(r"\|\s*([0-9a-f]{8})\s*\|", l)
        if m:
            cells = [c.strip() for c in l.strip("|").split("|")]
            if m.group(1) in seen:
                problems.append(f"{tid}: code {m.group(1)} twice")
            try:
                seen[m.group(1)] = (int(cells[sc]), int(cells[ai]) if ai is not None else None)
            except ValueError:
                problems.append(f"{tid}: non-integer score for {m.group(1)}")
    if set(seen) != codes:
        problems.append(f"{tid}: codes mismatch (missing {sorted(codes - set(seen))}, extra {sorted(set(seen) - codes)})")
    if any(not 1 <= s <= 5 for s, _ in seen.values()):
        problems.append(f"{tid}: score out of range")
    if not any(re.match(r"^\d+\.\s", l) for l in lines):
        problems.append(f"{tid}: no rank lines")
    rows += [{"code": c, "task": tid, "score": s, "ai_look": a} for c, (s, a) in seen.items()]
if problems:
    sys.exit("format problems (key not read):\n" + "\n".join(problems))
key = {json.loads(l)["code"]: json.loads(l) for l in (PRIV / "keys" / f"blind-key-{pas}.jsonl").open()}
assert all(key[r["code"]]["task"] == r["task"] for r in rows)
out = [{**r, **{k: key[r["code"]][k] for k in ("bundle", "cond", "tag")}} for r in rows]
(PRIV / "judge" / f"scores-{pas}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print(f"{pas}: {len(out)} scores from {len({r['task'] for r in out})} sets")
