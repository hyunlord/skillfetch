#!/usr/bin/env python3
"""Validate and unblind stage-2 judgments.
  unblind_s2.py --validate <pass>   format check only (every code once in the table and the ranks); never reads keys
  unblind_s2.py <pass>              stage2/judge-p<pass>.md + blind-key-p<pass>.jsonl -> stage2/judged-p<pass>.json
  unblind_s2.py --consistency       judged-p1.json vs judged-p2.json -> stage2/judge-consistency.json
Judgment file: one `## <task>` section per domain (s2-tests, s2-api, s2-docs, s2-data) as in rubrics.md."""
import json
import re
import statistics as st
import sys
from pathlib import Path

S2 = Path(__file__).resolve().parents[1]
TASKS = ("s2-tests", "s2-api", "s2-docs", "s2-data")


def parse(path):
    text = path.read_text()
    sets = {}
    for sec in re.split(r"^## ", text, flags=re.M)[1:]:
        name = sec.split("\n", 1)[0].strip()
        if name not in TASKS:
            continue
        rows, header = {}, None
        for line in sec.splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] == "code":
                header = cells
                continue
            if re.fullmatch(r"[0-9a-f]{8}", cells[0]) and header:
                rows[cells[0]] = {h: (int(c) if re.fullmatch(r"\d", c) else c) for h, c in zip(header[1:], cells[1:])}
        ranks = {}
        for m in re.finditer(r"^(\d+)\.\s+(.+)$", sec, re.M):
            for code in re.findall(r"[0-9a-f]{8}", m.group(2)):
                ranks.setdefault(code, []).append(int(m.group(1)))
        sets[name] = {"rows": rows, "ranks": ranks}
    return sets


def validate(n):
    sets = parse(S2 / f"judge-p{n}.md")
    errs = []
    for task in TASKS:
        codes = sorted(p.name for p in (S2 / f"blind-p{n}" / task).iterdir() if p.is_dir() and not p.name.startswith("_"))
        s = sets.get(task)
        if not s:
            errs.append(f"{task}: section missing")
            continue
        if sorted(s["rows"]) != codes:
            errs.append(f"{task}: table codes differ from the set ({len(s['rows'])} vs {len(codes)})")
        if sorted(s["ranks"]) != codes or any(len(v) != 1 for v in s["ranks"].values()):
            errs.append(f"{task}: rank lines must list every code exactly once")
        for code, r in s["rows"].items():
            for h, v in r.items():
                if h.endswith("1-5") and not (isinstance(v, int) and 1 <= v <= 5):
                    errs.append(f"{task} {code}: {h}={v!r}")
    return sets, errs


def main():
    if sys.argv[1] == "--consistency":
        a = {x["name"] + x["cond"]: x for x in json.loads((S2 / "judged-p1.json").read_text())}
        b = {x["name"] + x["cond"]: x for x in json.loads((S2 / "judged-p2.json").read_text())}
        out = {}
        for task in TASKS:
            names = [k for k in a if a[k]["task"] == task]
            d = [abs(a[k]["총점 1-5"] - b[k]["총점 1-5"]) for k in names]
            same = sum(1 for x in d if x == 0)
            order = {}
            for p, src in (("p1", a), ("p2", b)):
                means = {c: st.mean(src[k]["총점 1-5"] for k in names if src[k]["cond"] == c) for c in ("A", "B", "C2")}
                order[p] = means
            out[task] = {"n": len(names), "total_exact_agree": same, "total_mean_abs_diff": round(st.mean(d), 2),
                         "total_max_abs_diff": max(d), "means": order,
                         "c2_ge_b_same_in_both": (order["p1"]["C2"] >= order["p1"]["B"]) == (order["p2"]["C2"] >= order["p2"]["B"]),
                         "c2_ge_a_same_in_both": (order["p1"]["C2"] >= order["p1"]["A"]) == (order["p2"]["C2"] >= order["p2"]["A"])}
        (S2 / "judge-consistency.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    if sys.argv[1] == "--validate":
        _, errs = validate(int(sys.argv[2]))
        print("OK" if not errs else "\n".join(errs))
        sys.exit(1 if errs else 0)
    n = int(sys.argv[1])
    sets, errs = validate(n)
    if errs:
        sys.exit("\n".join(errs))
    keys = {k["code"]: k for k in map(json.loads, (S2 / f"blind-key-p{n}.jsonl").read_text().splitlines())}
    rows = []
    for task, s in sets.items():
        for code, r in s["rows"].items():
            k = keys[code]
            assert k["task"] == task
            rows.append({**k, **r, "rank": s["ranks"][code][0], "set_size": len(s["rows"])})
    (S2 / f"judged-p{n}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for task in TASKS:
        means = {c: round(st.mean(x["총점 1-5"] for x in rows if x["task"] == task and x["cond"] == c), 2) for c in ("A", "B", "C2")}
        print(task, means)


if __name__ == "__main__":
    main()
