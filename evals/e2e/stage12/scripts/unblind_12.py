#!/usr/bin/env python3
"""Stage 12 judging results (DESIGN §7; scores are reported only, not a gate). First every judgment file
stage12-private/judgments/<pass>/<set>.md is checked against the rubric format (section header, column names, every
code of the set exactly once with integer scores 1-5, rank lines naming every code once) WITHOUT reading any key; only
when all files pass are the keys (stage12-private/keys/blind-key-<pass>.jsonl) joined.
Output: stage12-private/judging.json and a printed summary: mean 총점 per condition and judge, per task, criteria
means, judge agreement (same score / within 1).
usage: unblind_12.py p1 p2"""
import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
PRIV = S12.parent / "stage12-private"
COLS = ["code", "요청 충족 1-5", "정확성 1-5", "구조·가독성 1-5", "검증 1-5", "총점 1-5", "근거"]


def parse(path, codes):
    text = path.read_text()
    probs = []
    if not re.search(rf"^## {re.escape(path.stem)}\s*$", text, re.M):
        probs.append("no section header")
    rows, header = {}, None
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "code":
            header = cells
            continue
        if header and re.fullmatch(r"[0-9a-f]{8}", cells[0] or ""):
            rows[cells[0]] = cells
    if header != COLS:
        probs.append(f"header {header}")
    if set(rows) != codes:
        probs.append(f"codes table {sorted(set(rows) ^ codes)}")
    scores = {}
    for c, cells in rows.items():
        try:
            v = [int(x) for x in cells[1:6]]
            assert all(1 <= x <= 5 for x in v)
            scores[c] = dict(zip(COLS[1:6], v))
        except (ValueError, AssertionError):
            probs.append(f"bad scores {c}")
    ranked = re.findall(r"[0-9a-f]{8}", "\n".join(l for l in text.splitlines() if re.match(r"^\d+\.\s", l)))
    if sorted(ranked) != sorted(codes):
        probs.append("rank lines")
    return scores, probs


def main():
    passes = sys.argv[1:] or ["p1", "p2"]
    allp, got = [], {}
    for p in passes:
        root = PRIV / "judge-package" / p
        for sdir in sorted(x for x in root.iterdir() if x.is_dir()):
            codes = {c.name for c in sdir.iterdir() if c.is_dir() and re.fullmatch(r"[0-9a-f]{8}", c.name)}
            f = PRIV / "judgments" / p / f"{sdir.name}.md"
            if not f.exists():
                allp.append(f"{p}/{sdir.name}: missing")
                continue
            s, probs = parse(f, codes)
            allp += [f"{p}/{sdir.name}: {x}" for x in probs]
            got[(p, sdir.name)] = s
    if allp:
        sys.exit("format problems (keys not read):\n" + "\n".join(allp))
    rows = []
    for p in passes:
        key = {k["code"]: k for k in map(json.loads, (PRIV / "keys" / f"blind-key-{p}.jsonl").open())}
        for (pp, tset), s in got.items():
            if pp != p:
                continue
            for code, sc in s.items():
                k = key[code]
                assert k["task"] == tset
                rows.append({"pass": p, "task": tset, "cond": k["cond"], "tag": k["tag"], **sc})
    summ = defaultdict(list)
    for r in rows:
        g = "T" if r["task"].startswith("T") else "C"
        summ[(r["pass"], g, r["cond"])].append(r["총점 1-5"])
        summ[("both", g, r["cond"])].append(r["총점 1-5"])
    by_task = defaultdict(list)
    for r in rows:
        by_task[(r["task"], r["cond"])].append(r["총점 1-5"])
    crit = defaultdict(list)
    for r in rows:
        if r["task"].startswith("T"):
            for c in COLS[1:5]:
                crit[(r["cond"], c)].append(r[c])
    pair = defaultdict(dict)
    for r in rows:
        pair[(r["task"], r["cond"], r["tag"])][r["pass"]] = r["총점 1-5"]
    both = [v for v in pair.values() if len(v) == 2]
    same = sum(len(set(v.values())) == 1 for v in both)
    within1 = sum(abs(v[passes[0]] - v[passes[1]]) <= 1 for v in both) if len(passes) == 2 else None
    out = {"rows": rows,
           "mean_total": {f"{a} {g} {c}": round(st.mean(v), 3) for (a, g, c), v in sorted(summ.items())},
           "by_task": {f"{t} {c}": round(st.mean(v), 2) for (t, c), v in sorted(by_task.items())},
           "criteria_T": {f"{c} {k}": round(st.mean(v), 2) for (c, k), v in sorted(crit.items())},
           "agreement": {"pairs": len(both), "same": same, "within_1": within1}}
    (PRIV / "judging.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
