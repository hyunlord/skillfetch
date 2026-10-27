#!/usr/bin/env python3
"""Stage 12/12b rulebook judging results (stage12b/DESIGN.md §4; report only). First every file
stage12-private/judgments-rules/<pass>/<set>.md is checked against rubric-s12-rules.md (section header, column names,
every code of the set once with integer scores 1-5 and 예/아니오 in `기존 동작 변경`, rank lines naming every code once)
WITHOUT reading any key; only when all pass are the keys (keys/blind-key-rules-<pass>.jsonl) joined.
Output: stage12-private/judging-rules.json and a printed summary: mean 총점 and criteria per condition (T1–T8, T1–T7,
C1–C2), 기존 동작 변경 예 counts per condition, agreement; plus the Stage 12 judging without the rulebook
(stage12-private/judging.json) for A, R, O side by side.
usage: unblind_rules.py p1 p2"""
import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
PRIV = S12.parent / "stage12-private"
COLS = ["code", "요청 충족 1-5", "정확성 1-5", "구조·가독성 1-5", "검증 1-5", "총점 1-5", "기존 동작 변경", "근거"]
CONDS = ("A", "R", "O", "Rp", "N", "F")


def parse(path, codes):
    text = path.read_text()
    probs, rows, header = [], {}, None
    if not re.search(rf"^## {re.escape(path.stem)}\s*$", text, re.M):
        probs.append("no section header")
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "code":
            header = cells
        elif header and re.fullmatch(r"[0-9a-f]{8}", cells[0] or ""):
            rows[cells[0]] = cells
    if header != COLS:
        probs.append(f"header {header}")
    if set(rows) != codes:
        probs.append(f"codes table {sorted(set(rows) ^ codes)}")
    scores = {}
    for c, cells in rows.items():
        try:
            v = [int(x) for x in cells[1:6]]
            assert all(1 <= x <= 5 for x in v) and cells[6] in ("예", "아니오")
            scores[c] = {**dict(zip(COLS[1:6], v)), "기존 동작 변경": cells[6] == "예", "근거": cells[7]}
        except (ValueError, AssertionError, IndexError):
            probs.append(f"bad row {c}")
    ranked = re.findall(r"[0-9a-f]{8}", "\n".join(l for l in text.splitlines() if re.match(r"^\d+\.\s", l)))
    if sorted(ranked) != sorted(codes):
        probs.append("rank lines")
    return scores, probs


def main():
    passes = sys.argv[1:] or ["p1", "p2"]
    probs, got = [], {}
    for p in passes:
        for sdir in sorted(x for x in (PRIV / "judge-package-rules" / p).iterdir() if x.is_dir()):
            codes = {c.name for c in sdir.iterdir() if c.is_dir() and re.fullmatch(r"[0-9a-f]{8}", c.name)}
            f = PRIV / "judgments-rules" / p / f"{sdir.name}.md"
            if not f.exists():
                probs.append(f"{p}/{sdir.name}: missing")
                continue
            s, pr = parse(f, codes)
            probs += [f"{p}/{sdir.name}: {x}" for x in pr]
            got[(p, sdir.name)] = s
    if probs:
        sys.exit("format problems (keys not read):\n" + "\n".join(probs))
    rows = []
    for p in passes:
        key = {k["code"]: k for k in map(json.loads, (PRIV / "keys" / f"blind-key-rules-{p}.jsonl").open())}
        for (pp, tset), s in got.items():
            if pp == p:
                for code, sc in s.items():
                    assert key[code]["task"] == tset
                    rows.append({"pass": p, "task": tset, "cond": key[code]["cond"], "tag": key[code]["tag"], **sc})

    def grp(task):
        return "C" if task.startswith("C") else "T"

    def mean(xs):
        return round(st.mean(xs), 3) if xs else None
    out = {"rows": rows, "total": {}, "criteria_T": {}, "changed_existing": {}, "per_task": {}}
    for c in CONDS:
        r = [x for x in rows if x["cond"] == c]
        out["total"][c] = {"T1-T8": mean([x["총점 1-5"] for x in r if grp(x["task"]) == "T"]),
                           "T1-T7": mean([x["총점 1-5"] for x in r if grp(x["task"]) == "T" and x["task"] != "T8"]),
                           "C1-C2": mean([x["총점 1-5"] for x in r if grp(x["task"]) == "C"]),
                           "p1 T1-T8": mean([x["총점 1-5"] for x in r if grp(x["task"]) == "T" and x["pass"] == passes[0]]),
                           "p2 T1-T8": mean([x["총점 1-5"] for x in r if grp(x["task"]) == "T" and x["pass"] == passes[-1]])}
        out["criteria_T"][c] = {k: mean([x[k] for x in r if grp(x["task"]) == "T"]) for k in COLS[1:5]}
        out["changed_existing"][c] = {"yes": sum(x["기존 동작 변경"] for x in r), "of": len(r)}
        for t in sorted({x["task"] for x in r}):
            out["per_task"][f"{t} {c}"] = mean([x["총점 1-5"] for x in r if x["task"] == t])
    pair = defaultdict(dict)
    for x in rows:
        pair[(x["task"], x["cond"], x["tag"])][x["pass"]] = x["총점 1-5"]
    both = [v for v in pair.values() if len(v) == 2]
    out["agreement"] = {"pairs": len(both), "same": sum(len(set(v.values())) == 1 for v in both),
                        "within_1": sum(abs(max(v.values()) - min(v.values())) <= 1 for v in both)}
    old = json.loads((PRIV / "judging.json").read_text())["rows"]
    out["without_rulebook"] = {c: {"T1-T8": mean([x["총점 1-5"] for x in old if x["cond"] == c and grp(x["task"]) == "T"]),
                                   "T1-T7": mean([x["총점 1-5"] for x in old if x["cond"] == c and grp(x["task"]) == "T"
                                                  and x["task"] != "T8"]),
                                   "C1-C2": mean([x["총점 1-5"] for x in old if x["cond"] == c and grp(x["task"]) == "C"])}
                               for c in ("A", "R", "O")}
    (PRIV / "judging-rules.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "per_task")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
