#!/usr/bin/env python3
"""6b-A2: run-to-run spread of S-0 and S-b (3 independent generations each: select-<C>.jsonl, -rep2, -rep3).
Picks from the repeats that are outside the oracle v4 pool are graded with the unchanged 2b prompt (one call per task)
-> oracle-v4r.jsonl. On v4r, per generation: none accuracy (no-relevant tasks; expect_none 40), hit (coverage tasks),
unnecessary loads (picks graded < 2, all 380 tasks), mean picks; range = min-max of the 3; compares the S-0 vs S-b gap
with the ranges. Writes variability.json."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S6, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

GENS = {c: [f"select-{c}.jsonl", f"select-{c}-rep2.jsonl", f"select-{c}-rep3.jsonl"] for c in ("S-0", "S-b")}
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "tasks.jsonl").open()}
v4 = {json.loads(l)["id"]: json.loads(l) for l in (S6 / "oracle-v4.jsonl").open()}
sel = {c: [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f).open()} for f in fs] for c, fs in GENS.items()}
new = {}
for tid, o in v4.items():
    have = {x["skill"] for x in o["pool"]}
    add = sorted({s for c in sel for g in sel[c] for s in g[tid] if s not in have})
    if add:
        random.Random(f"v4r-{tid}").shuffle(add)
        new[tid] = add
res = run_all([(f"grade-v4r-{tid}", S6 / "gen" / "sys-grade.txt",
                f"TASK\n{tasks[tid]['text']}\n\nCANDIDATES ({len(order)})\n" + "\n".join(card(s) for s in order)) for tid, order in new.items()], workers=8)
orc = {}
added = rel_added = 0
for tid, o in v4.items():
    pool = list(o["pool"])
    if tid in new:
        r = res[list(new).index(tid)]
        assert not r["is_error"], r["name"]
        for x in parse_json_last(r["text"]):
            ids, _ = resolve_ids([x["skill"]], set(new[tid]))
            if ids:
                pool.append({"skill": ids[0], "grade": int(x["grade"]), "process": bool(x.get("process")), "sources": ["sel-rep"], "added_in": "6b"})
                added += 1
                rel_added += int(x["grade"]) >= 2
    orc[tid] = {"id": tid, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2]}
(S6 / "oracle-v4r.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in orc.values()))


def metrics(g):
    grade = {t: {x["skill"]: x["grade"] for x in orc[t]["pool"]} for t in orc}
    cov = [t for t in orc if orc[t]["relevant"] and not tasks[t]["expect_none"]]
    nor = [t for t in orc if not orc[t]["relevant"]]
    en = [t for t in orc if tasks[t]["expect_none"]]
    return {"none_acc_no_relevant": round(sum(not g[t] for t in nor) / len(nor), 3),
            "none_acc_expect_none": round(sum(not g[t] for t in en) / len(en), 3),
            "hit": round(sum(any(grade[t].get(s, 0) >= 2 for s in g[t]) for t in cov) / len(cov), 3),
            "unnecessary_loads": sum(grade[t].get(s, 0) < 2 for t in orc for s in g[t]),
            "mean_picks": round(sum(len(g[t]) for t in orc) / len(orc), 3), "n_no_relevant": len(nor), "n_cov": len(cov)}


out = {"graded_tasks": len(new), "added": added, "added_relevant": rel_added,
       "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2), "per_generation": {}, "range": {}, "gap_vs_range": {}}
for c in sel:
    out["per_generation"][c] = [metrics(g) for g in sel[c]]
    out["range"][c] = {k: [min(m[k] for m in out["per_generation"][c]), max(m[k] for m in out["per_generation"][c])]
                       for k in ("none_acc_no_relevant", "none_acc_expect_none", "hit", "unnecessary_loads", "mean_picks")}
for k in ("none_acc_no_relevant", "none_acc_expect_none", "hit", "unnecessary_loads", "mean_picks"):
    r0, rb = out["range"]["S-0"][k], out["range"]["S-b"][k]
    mean = lambda c: sum(m[k] for m in out["per_generation"][c]) / 3  # noqa: E731
    gap = mean("S-b") - mean("S-0")
    out["gap_vs_range"][k] = {"mean_gap": round(gap, 3), "S-0_range_width": round(r0[1] - r0[0], 3), "S-b_range_width": round(rb[1] - rb[0], 3),
                              "ranges_overlap": not (r0[1] < rb[0] or rb[1] < r0[0]),
                              "gap_larger_than_both_widths": abs(gap) > max(r0[1] - r0[0], rb[1] - rb[0])}
(S6 / "variability.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("graded_tasks", "added", "added_relevant", "cost_usd", "range", "gap_vs_range")}, indent=1))
