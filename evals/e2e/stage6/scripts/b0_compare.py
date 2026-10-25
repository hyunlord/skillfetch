#!/usr/bin/env python3
"""6b B-0: S-b' (select-cands/S-bp: S-b without the `kind` sentence; search results without kind) vs S-b's 3 generations.
Picks of S-b' outside the oracle v4r pool are graded with the unchanged 2b prompt -> oracle-v4r2.jsonl (v4r + those).
On v4r2: none accuracy (no-relevant tasks), hit (coverage tasks), unnecessary loads (grade < 2) for S-b x3 and S-b' x1;
rule: S-b' passes when each of the three is inside S-b's min-max or better. Writes b0-compare.json."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S6, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "tasks.jsonl").open()}
v4r = {json.loads(l)["id"]: json.loads(l) for l in (S6 / "oracle-v4r.jsonl").open()}
load = lambda f: {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f).open()}  # noqa: E731
sb = [load(f) for f in ("select-S-b.jsonl", "select-S-b-rep2.jsonl", "select-S-b-rep3.jsonl")]
sbp = load("select-S-bp.jsonl")
new = {}
for tid, o in v4r.items():
    have = {x["skill"] for x in o["pool"]}
    add = sorted(s for s in sbp[tid] if s not in have)
    if add:
        random.Random(f"v4r2-{tid}").shuffle(add)
        new[tid] = add
res = run_all([(f"grade-v4r2-{tid}", S6 / "gen" / "sys-grade.txt",
                f"TASK\n{tasks[tid]['text']}\n\nCANDIDATES ({len(a)})\n" + "\n".join(card(s) for s in a)) for tid, a in new.items()], workers=8)
orc, added, rel_added = {}, 0, 0
for tid, o in v4r.items():
    pool = list(o["pool"])
    if tid in new:
        r = res[list(new).index(tid)]
        assert not r["is_error"], r["name"]
        for x in parse_json_last(r["text"]):
            ids, _ = resolve_ids([x["skill"]], set(new[tid]))
            if ids:
                pool.append({"skill": ids[0], "grade": int(x["grade"]), "process": bool(x.get("process")), "sources": ["sel-S-bp"], "added_in": "6b-B0"})
                added += 1
                rel_added += int(x["grade"]) >= 2
    orc[tid] = {"id": tid, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2]}
(S6 / "oracle-v4r2.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in orc.values()))
grade = {t: {x["skill"]: x["grade"] for x in orc[t]["pool"]} for t in orc}
cov = [t for t in orc if orc[t]["relevant"] and not tasks[t]["expect_none"]]
nor = [t for t in orc if not orc[t]["relevant"]]


def m(g):
    return {"none_acc_no_relevant": round(sum(not g[t] for t in nor) / len(nor), 3),
            "hit": round(sum(any(grade[t].get(s, 0) >= 2 for s in g[t]) for t in cov) / len(cov), 3),
            "unnecessary_loads": sum(grade[t].get(s, 0) < 2 for t in orc for s in g[t]),
            "none_acc_expect_none": round(sum(not g[t] for t in orc if tasks[t]["expect_none"]) / 40, 3),
            "mean_picks": round(sum(len(g[t]) for t in orc) / len(orc), 3)}


ms, mp = [m(g) for g in sb], m(sbp)
better_high = {"none_acc_no_relevant": True, "hit": True, "unnecessary_loads": False}
check = {}
for k, hi in better_high.items():
    lo_, hi_ = min(x[k] for x in ms), max(x[k] for x in ms)
    ok = (lo_ <= mp[k] <= hi_) or (mp[k] > hi_ if hi else mp[k] < lo_)
    check[k] = {"S-b_range": [lo_, hi_], "S-bp": mp[k], "inside_or_better": ok}
out = {"graded_tasks": len(new), "added": added, "added_relevant": rel_added, "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2),
       "n_no_relevant": len(nor), "n_cov": len(cov), "S-b": ms, "S-bp": mp, "check": check,
       "verdict": "Cb = S-b' (no server branch)" if all(c["inside_or_better"] for c in check.values()) else "Cb = S-b + kind branch (as designed)"}
(S6 / "b0-compare.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
