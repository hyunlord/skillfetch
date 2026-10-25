#!/usr/bin/env python3
"""7a baseline: S-b' 3 generations (stage6/select-S-bp.jsonl, -rep2, -rep3). Picks outside the v4r2 pool are graded with
the unchanged 2b prompt -> oracle-v5.jsonl. Per generation on v5: none accuracy (no-relevant tasks), hit (coverage
tasks), unnecessary loads, pairs moved with the direction among the 16 (DESIGN.md §0). Writes baseline.json."""
import json
import random
import sys
from pathlib import Path

S7 = Path(__file__).resolve().parents[1]
S6 = S7.parent / "stage6"
sys.path.insert(0, str(S6 / "scripts"))
from batch import parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S7.parent / "stage3" / "tasks.jsonl").open()}
v = {json.loads(l)["id"]: json.loads(l) for l in (S6 / "oracle-v4r2.jsonl").open()}
gens = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f).open()} for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
new = {}
for t, o in v.items():
    have = {x["skill"] for x in o["pool"]}
    add = sorted({s for g in gens for s in g[t] if s not in have})
    if add:
        random.Random(f"v5-{t}").shuffle(add)
        new[t] = add
res = run_all([(f"s7-grade-v5-{t}", S6 / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(a)})\n" + "\n".join(card(s) for s in a))
               for t, a in new.items()], workers=8)
orc, added, rel_added = {}, 0, 0
for t, o in v.items():
    pool = list(o["pool"])
    if t in new:
        r = res[list(new).index(t)]
        assert not r["is_error"]
        for x in parse_json_last(r["text"]):
            ids, _ = resolve_ids([x["skill"]], set(new[t]))
            if ids:
                pool.append({"skill": ids[0], "grade": int(x["grade"]), "process": bool(x.get("process")), "sources": ["s7-baseline"], "added_in": "7a"})
                added += 1
                rel_added += int(x["grade"]) >= 2
    orc[t] = {"id": t, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2]}
(S7 / "oracle-v5.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in orc.values()))
grade = {t: {x["skill"]: x["grade"] for x in orc[t]["pool"]} for t in orc}
rel = {t: set(orc[t]["relevant"]) for t in orc}
cov = [t for t in orc if rel[t] and not tasks[t]["expect_none"]]
nor = [t for t in orc if not rel[t]]
P16 = json.loads((S7 / "pairs-16.json").read_text())
pairs = {}
for t in tasks.values():
    if t["pair_id"] in P16:
        pairs.setdefault(t["pair_id"], {})[t["pair_side"]] = t["id"]


def moved(Sa, Sb, Ra, Rb):
    if Sa == Sb:
        return False
    ea, eb = Sa - Sb, Sb - Sa
    return bool(ea | eb) and all(x in Ra for x in ea) and all(x in Rb for x in eb) \
        and not any(x in Rb and x not in Ra for x in ea) and not any(x in Ra and x not in Rb for x in eb)


def metrics(g):
    return {"none_acc": round(sum(not g[t] for t in nor) / len(nor), 3), "hit": round(sum(any(grade[t].get(s, 0) >= 2 for s in g[t]) for t in cov) / len(cov), 3),
            "unnecessary_loads": sum(grade[t].get(s, 0) < 2 for t in orc for s in g[t]),
            "pairs_moved_16": sum(moved(set(g[a["a"]]), set(g[a["b"]]), rel[a["a"]], rel[a["b"]]) for a in pairs.values()),
            "moved_pairs": sorted(p for p, a in pairs.items() if moved(set(g[a["a"]]), set(g[a["b"]]), rel[a["a"]], rel[a["b"]]))}


per = [metrics(g) for g in gens]
mean = {k: round(sum(m[k] for m in per) / 3, 3) for k in ("none_acc", "hit", "unnecessary_loads", "pairs_moved_16")}
out = {"graded_tasks": len(new), "added": added, "added_relevant": rel_added, "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2),
       "n_no_relevant": len(nor), "n_cov": len(cov), "per_generation": per, "mean": mean}
(S7 / "baseline.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("graded_tasks", "added", "added_relevant", "cost_usd", "n_no_relevant", "n_cov", "mean")}, indent=1))
for m in per:
    print(m)
