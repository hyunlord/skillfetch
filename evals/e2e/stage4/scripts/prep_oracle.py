#!/usr/bin/env python3
"""Steps T2-T6 for the candidates (gen/candidates.jsonl), stage-3 pipeline with the repo's profile:
  2a  oracle picks over the catalog (gen/sys-oracle.txt, 10 per call)            -> gen/oracle-2a.json
  pool 2a ∪ search_skills top-10 of the request (k=50 compact, the repo's profile_repo result) ∪ 2 seeded random,
       shuffled                                                                   -> gen/pools.json
  2b  grade each pool 0-3 + process flag (gen/sys-grade.txt, one call per task)   -> gen/grades-2b.json
  q   Q2 (stage-3 one-sentence rule, gen/sys-q2.txt) and Q3 (router a1cbcd5 step 1, gen/sys-q3r.txt), 20 per call
                                                                                  -> queries.jsonl
  3-0 add the top-10 of Q2 and Q3 (Q3 as `queries`, RRF) with the profile; grade only new candidates with the same
      2b prompt                                                                    -> oracle.jsonl, pool-expansion.json
Run with skillfetch a1cbcd5: uv run --project ~/github/skillfetch python scripts/prep_oracle.py"""
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S4, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index  # noqa: E402
from skillfetch.mcp.session import Session  # noqa: E402

G = S4 / "gen"
ROUND = os.environ.get("S4_ROUND", "1")
SUF, PRE = ("", "") if ROUND == "1" else (f"-r{ROUND}", f"r{ROUND}-")
tasks = [json.loads(l) for l in (G / f"candidates{SUF}.jsonl").open()]
profiles = json.loads((G / "profiles.json").read_text())
s = Session(Index.load(DEFAULT_INDEX_DIR))
cat = [l.split(" | ")[0] for l in (G / "catalog.md").read_text().splitlines()]
valid = set(cat)


def top(t, **q):
    return [r["id"] for r in s.search_skills(profile=profiles[t["repo"]], **q)["results"]]


def grade(name, t, order):
    return (name, G / "sys-grade.txt", f"TASK\n{t['text']}\n\nCANDIDATES ({len(order)})\n" + "\n".join(card(x) for x in order))


def parse_grades(r, order):
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(order))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    return g


cost = Counter()
# 2a
res = run_all([(f"{PRE}oracle2a-{b // 10 + 1:02d}", G / "sys-oracle.txt",
                "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['text']}" for t in tasks[b: b + 10]))
               for b in range(0, len(tasks), 10)], workers=6)
o2a = {}
for r in res:
    assert not r["is_error"], r["name"]
    cost["2a"] += r.get("cost_usd") or 0
    for x in parse_json_last(r["text"]):
        o2a[x["id"]] = {"skills": resolve_ids(x["skills"], valid)[0], "reason": x.get("reason", "")}
assert set(o2a) == {t["id"] for t in tasks}, set(t["id"] for t in tasks) - set(o2a)
(G / f"oracle-2a{SUF}.json").write_text(json.dumps(o2a, indent=1, ensure_ascii=False))
# pools
pools = {}
for t in tasks:
    rng = random.Random(f"pool-{t['id']}")
    q1 = top(t, query=t["text"])
    src = {}
    for sid in o2a[t["id"]]["skills"]:
        src.setdefault(sid, []).append("2a")
    for sid in q1[:10]:
        src.setdefault(sid, []).append("bm25")
    for sid in rng.sample([c for c in cat if c not in src], 2):
        src.setdefault(sid, []).append("random")
    order = list(src)
    rng.shuffle(order)
    pools[t["id"]] = {"order": order, "sources": src, "q1_top50": q1}
(G / f"pools{SUF}.json").write_text(json.dumps(pools, indent=1))
# 2b
res = run_all([grade(f"{PRE}grade2b-{t['id']}", t, pools[t["id"]]["order"]) for t in tasks], workers=8)
g2b = {}
for t, r in zip(tasks, res):
    assert not r["is_error"], r["name"]
    cost["2b"] += r.get("cost_usd") or 0
    g2b[t["id"]] = parse_grades(r, pools[t["id"]]["order"])
(G / f"grades-2b{SUF}.json").write_text(json.dumps(g2b, indent=1))
# queries
chunks = [tasks[i: i + 20] for i in range(0, len(tasks), 20)]
body = lambda c: "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['text']}" for t in c)  # noqa: E731
r2 = run_all([(f"{PRE}q2-{n + 1:02d}", G / "sys-q2.txt", body(c)) for n, c in enumerate(chunks)], workers=6)
r3 = run_all([(f"{PRE}q3r-{n + 1:02d}", G / "sys-q3r.txt", body(c)) for n, c in enumerate(chunks)], workers=6)
cost["queries"] += sum((r.get("cost_usd") or 0) for r in r2 + r3)
q2 = {x["id"]: x["q"] for r in r2 for x in parse_json_last(r["text"])}
q3 = {x["id"]: [q for q in x["queries"] if q.strip()][:4] for r in r3 for x in parse_json_last(r["text"])}
assert set(q2) == set(q3) == {t["id"] for t in tasks}
(S4 / f"queries{SUF}.jsonl").write_text("".join(json.dumps({"id": t["id"], "repo": t["repo"], "q1": t["text"], "q2": q2[t["id"]],
                                                      "q3": q3[t["id"]]}, ensure_ascii=False) + "\n" for t in tasks))
rank = {t["id"]: {"q1": pools[t["id"]]["q1_top50"], "q2": top(t, query=q2[t["id"]]), "q3": top(t, queries=q3[t["id"]])}
        for t in tasks}
(S4 / f"rankings{SUF}.json").write_text(json.dumps(rank))
# 3-0
new = {}
for t in tasks:
    have = set(pools[t["id"]]["order"])
    add = {}
    for m in ("q2", "q3"):
        for sid in rank[t["id"]][m][:10]:
            if sid not in have:
                add.setdefault(sid, []).append(f"bm25_{m}")
    if add:
        order = list(add)
        random.Random(f"expand-{t['id']}").shuffle(order)
        new[t["id"]] = {"order": order, "sources": add}
by = {t["id"]: t for t in tasks}
res = run_all([grade(f"{PRE}grade3x-{tid}", by[tid], n["order"]) for tid, n in new.items()], workers=8)
g3 = {}
for (tid, n), r in zip(new.items(), res):
    assert not r["is_error"], r["name"]
    cost["3-0"] += r.get("cost_usd") or 0
    g3[tid] = parse_grades(r, n["order"])
rows, stats = [], Counter()
for t in tasks:
    p, tid = pools[t["id"]], t["id"]
    pool = [{"skill": x, "sources": p["sources"][x], **g2b[tid][x]} for x in p["order"] if x in g2b[tid]]
    v1_rel = [x["skill"] for x in pool if x["grade"] >= 2]
    for x in new.get(tid, {}).get("order", []):
        if x in g3.get(tid, {}):
            pool.append({"skill": x, "sources": new[tid]["sources"][x], **g3[tid][x], "added_in": "3-0"})
            stats["added"] += 1
            stats["added_relevant"] += g3[tid][x]["grade"] >= 2
    rel = sorted((x for x in pool if x["grade"] >= 2), key=lambda x: -x["grade"])
    rows.append({"id": tid, "repo": t["repo"], "expect_none": t["expect_none"], "relevant": [x["skill"] for x in rel],
                 "relevant_grades": {x["skill"]: x["grade"] for x in rel},
                 "relevant_process": [x["skill"] for x in rel if x["process"]],
                 "relevant_2a": [x["skill"] for x in rel if "2a" in x["sources"]], "relevant_v1": v1_rel,
                 "oracle_2a": o2a[tid]["skills"], "pool": pool})
(S4 / f"oracle{SUF}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
summary = {"tasks": len(rows), "added": stats["added"], "added_relevant": stats["added_relevant"],
           "relevant_v1": sum(len(r["relevant_v1"]) for r in rows), "relevant_v2": sum(len(r["relevant"]) for r in rows),
           "no_relevant": sum(1 for r in rows if not r["relevant"]), "cost_usd": {k: round(v, 2) for k, v in cost.items()}}
(S4 / f"pool-expansion{SUF}.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary))
