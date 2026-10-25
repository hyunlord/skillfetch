#!/usr/bin/env python3
"""Steps T7-T8: offline selection and the 40 tasks.
  select  the router's search (Q3 as `queries`, the repo's profile, k=50 compact, skillfetch a1cbcd5) + router a1cbcd5
          "When" and step 4 (gen/sys-select.txt), 20 tasks per call; tasks whose answer names an id outside their own
          50 are redone alone                                                     -> offline.jsonl
  classify against oracle.jsonl (relevant = grade >= 2), relative to the router's query Q3:
          R empty -> over_load if S else ok · S∩R -> ok · some r in Q3 top-50 -> select_fail
          · else some r in Q1 or Q2 top-50 -> restate_fail · else search_fail
  pick    10 per failure class (select_fail, restate_fail, search_fail, over_load), seeded, round-robin over task
          types so each class spreads across them; shortfalls recorded         -> tasks.jsonl, picks.json
Run with skillfetch a1cbcd5: uv run --project ~/github/skillfetch python scripts/prep_select.py"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S4, parse_json_last, resolve_ids, run_all  # noqa: E402
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index  # noqa: E402
from skillfetch.mcp.session import Session  # noqa: E402

G = S4 / "gen"
CLASSES = ("select_fail", "restate_fail", "search_fail", "over_load")
ROUNDS = [("1", ""), *((f.stem.split("-r")[-1], "-r" + f.stem.split("-r")[-1])
                         for f in sorted(G.glob("candidates-r*.jsonl")))]  # round 2+: more candidates
tasks, round_of = [], {}
queries, rank, oracle = {}, {}, {}
for rnd, suf in ROUNDS:
    for line in (G / f"candidates{suf}.jsonl").open():
        x = json.loads(line)
        tasks.append(x)
        round_of[x["id"]] = rnd
    queries.update({json.loads(l)["id"]: json.loads(l) for l in (S4 / f"queries{suf}.jsonl").open()})
    rank.update(json.loads((S4 / f"rankings{suf}.json").read_text()))
    oracle.update({json.loads(l)["id"]: json.loads(l) for l in (S4 / f"oracle{suf}.jsonl").open()})
by = {t["id"]: t for t in tasks}
profiles = json.loads((G / "profiles.json").read_text())
s = Session(Index.load(DEFAULT_INDEX_DIR))
results = {t["id"]: s.search_skills(queries=queries[t["id"]]["q3"], profile=profiles[t["repo"]]) for t in tasks}
assert all([r["id"] for r in results[tid]["results"]] == rank[tid]["q3"] for tid in results)


def item(tid):
    return (f"### {tid}\nTask:\n{by[tid]['text']}\n\nsearch_skills result:\n"
            f"{json.dumps(results[tid], ensure_ascii=False)}")


jobs = []
for rnd, _ in ROUNDS:
    rt = [t for t in tasks if round_of[t["id"]] == rnd]
    pre = "" if rnd == "1" else f"r{rnd}-"
    jobs += [(f"{pre}select-{n // 20 + 1:02d}", G / "sys-select.txt",
              "TASKS\n\n" + "\n\n".join(item(t["id"]) for t in rt[n: n + 20])) for n in range(0, len(rt), 20)]
res = run_all(jobs, workers=5)
cost = sum((r.get("cost_usd") or 0) for r in res)
sel, dropped = {}, []
for r in res:
    assert not r["is_error"], r["name"]
    for x in parse_json_last(r["text"]):
        ids, bad = resolve_ids(x.get("skills") or [], {y["id"] for y in results[x["id"]]["results"]})
        dropped += [(x["id"], b) for b in bad]
        sel[x["id"]] = ids[:3]
redo = sorted({d[0] for d in dropped} | {t["id"] for t in tasks if t["id"] not in sel})
if redo:
    res1 = run_all([(f"select1-{tid}", G / "sys-select.txt", "TASKS\n\n" + item(tid)) for tid in redo], workers=6)
    cost += sum((r.get("cost_usd") or 0) for r in res1)
    for tid, r in zip(redo, res1):
        x = parse_json_last(r["text"])[0]
        sel[tid] = resolve_ids(x.get("skills") or [], {y["id"] for y in results[tid]["results"]})[0][:3]
rows = []
for t in tasks:
    tid = t["id"]
    R, S = set(oracle[tid]["relevant"]), set(sel[tid])
    rk = rank[tid]
    if not R:
        cls = "over_load" if S else "ok"
    elif S & R:
        cls = "ok"
    elif R & set(rk["q3"][:50]):
        cls = "select_fail"
    elif R & (set(rk["q1"][:50]) | set(rk["q2"][:50])):
        cls = "restate_fail"
    else:
        cls = "search_fail"
    rows.append({"id": tid, "round": round_of[tid], "repo": t["repo"], "queries": queries[tid]["q3"],
                 "skills": sel[tid], "class": cls,
                 **({"redone_alone": True} if tid in redo else {})})
(S4 / "offline.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
counts = Counter(r["class"] for r in rows)
pick, short = {}, {}
for cls in CLASSES:
    chosen = []
    for rnd, _ in ROUNDS:  # a later round only fills what the earlier ones could not
        pool = [r for r in rows if r["class"] == cls and r["round"] == rnd]
        random.Random(f"pick-{cls}" + ("" if rnd == "1" else f"-r{rnd}")).shuffle(pool)
        groups = defaultdict(list)
        for r in pool:
            groups[by[r["id"]]["task_type"]].append(r)
        order = sorted(groups)
        while len(chosen) < 10 and any(groups.values()):
            for tt in order:
                if groups[tt] and len(chosen) < 10:
                    chosen.append(groups[tt].pop(0))
    pick[cls] = [r["id"] for r in chosen]
    if len(chosen) < 10:
        short[cls] = 10 - len(chosen)
out = []
for cls in CLASSES:
    for tid in pick[cls]:
        t = by[tid]
        out.append({**t, "prompt": t["text"], "offline_class": cls, "offline_skills": sel[tid],
                    "offline_queries": queries[tid]["q3"]})
(S4 / "tasks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
(S4 / "picks.json").write_text(json.dumps({"class_counts": counts, "picked": pick, "shortfall": short,
                                           "redone_alone": redo, "cost_usd": round(cost, 2)}, indent=1))
print(dict(counts), "| picked", {k: len(v) for k, v in pick.items()}, "| shortfall", short, "| redo", len(redo),
      "| repos", Counter(r["repo"] for r in out), "| cost", round(cost, 2))
