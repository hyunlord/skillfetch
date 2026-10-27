#!/usr/bin/env python3
"""Stage 14 judging (DESIGN §4 item 1), same parsing and pre-key validation as stage13/scripts/unblind_13.py: judge outputs
stage14-private/judge/<pass>/<set>.md are validated BEFORE the key is read (every code of the set once, score 1-5, rank
lines present), then joined with stage14-private/keys/blind-key-<pass>.jsonl. Score column: s14-landing "(b) 쓸만함 1-5"
(and "(a) AI느낌 수"), others "총점 1-5"; the 근거 column is kept.
Writes stage14-private/judge/scores-<pass>.jsonl {code, set, task, cond, order, tag, k, score, ai_look, reason}.
usage: unblind_14.py <pass>"""
import json
import re
import sys
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
PRIV = S14.parent / "stage14-private"

pas = sys.argv[1]
blind = PRIV / "judge-package" / pas
rows, problems = [], []
for sdir in sorted(p for p in blind.iterdir() if p.is_dir()):
    sname = sdir.name
    codes = {p.name for p in sdir.iterdir() if p.is_dir() and p.name != "_context"}
    f = PRIV / "judge" / pas / f"{sname}.md"
    if not f.exists():
        problems.append(f"{sname}: no judgment file")
        continue
    lines = f.read_text().splitlines()
    head = next((l for l in lines if l.startswith("| code |")), None)
    if not head:
        problems.append(f"{sname}: no table header")
        continue
    cols = [c.strip() for c in head.strip("|").split("|")]
    try:
        sc = cols.index("(b) 쓸만함 1-5") if sname == "s14-landing" else cols.index("총점 1-5")
        ai = cols.index("(a) AI느낌 수") if sname == "s14-landing" else None
        rz = cols.index("근거") if "근거" in cols else None
    except ValueError:
        problems.append(f"{sname}: score column missing in {cols}")
        continue
    seen = {}
    for l in lines:
        m = re.match(r"\|\s*([0-9a-f]{8})\s*\|", l)
        if m:
            cells = [c.strip() for c in l.strip("|").split("|")]
            if m.group(1) in seen:
                problems.append(f"{sname}: code {m.group(1)} twice")
            try:
                seen[m.group(1)] = (int(cells[sc]), int(cells[ai]) if ai is not None else None, cells[rz] if rz is not None and rz < len(cells) else "")
            except (ValueError, IndexError):
                problems.append(f"{sname}: non-integer score for {m.group(1)}")
    if set(seen) != codes:
        problems.append(f"{sname}: codes mismatch (missing {sorted(codes - set(seen))}, extra {sorted(set(seen) - codes)})")
    if any(not 1 <= s <= 5 for s, _, _ in seen.values()):
        problems.append(f"{sname}: score out of range")
    if not any(re.match(r"^\d+\.\s", l) for l in lines):
        problems.append(f"{sname}: no rank lines")
    rows += [{"code": c, "set": sname, "score": s, "ai_look": a, "reason": r} for c, (s, a, r) in seen.items()]
if problems:
    sys.exit("format problems (key not read):\n" + "\n".join(problems))
key = {json.loads(l)["code"]: json.loads(l) for l in (PRIV / "keys" / f"blind-key-{pas}.jsonl").open()}
assert all(key[r["code"]]["set"] == r["set"] for r in rows)
out = [{**r, **{k: key[r["code"]][k] for k in ("task", "cond", "order", "tag", "k")}} for r in rows]
(PRIV / "judge" / f"scores-{pas}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print(f"{pas}: {len(out)} scores from {len({r['set'] for r in out})} sets")
