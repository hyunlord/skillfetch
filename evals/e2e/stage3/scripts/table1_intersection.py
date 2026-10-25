#!/usr/bin/env python3
"""Table 1 (recall@10/@50) on the 120 cross-label tasks, three label versions: Opus (oracle v2), GPT, and the
intersection (both grade >= 2). 2a subset = relevant and picked by oracle 2a; process subset = relevant and process
flag set by both (Opus only / GPT only for the single-label versions). Same macro recall as eval_recall.py.
Writes cross-label-table1.json."""
import json
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
METHODS = ["bm25_q1", "emb_q1", "rrf_q1", "bm25_q2", "emb_q2", "rrf_q2", "bm25_q3"]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
ids = json.loads((S3 / "blind-pool-120-ids.json").read_text())
ids = ids["task_ids"] if isinstance(ids, dict) else ids
gpt = {}
for r in map(json.loads, (S3 / "gpt-grades-120.jsonl").open()):
    gpt.setdefault(r["task_id"], {})[r["candidate_id"]] = r
rk = json.loads((S3 / "rankings.json").read_text())


def sets(tid, version):
    o, g = orc[tid], gpt[tid]
    a2 = set(o["relevant_2a"])
    pool = {x["skill"]: x for x in o["pool"]}
    out = {"all": set(), "process": set()}
    for s, x in pool.items():
        go = x["grade"] >= 2
        gg = s in g and int(g[s]["grade"]) >= 2
        po, pg = x["process"], s in g and bool(g[s]["process"])
        rel = {"opus": go, "gpt": gg, "both": go and gg}[version]
        proc = {"opus": po, "gpt": pg, "both": po and pg}[version]
        if rel:
            out["all"].add(s)
            if proc:
                out["process"].add(s)
    out["2a"] = out["all"] & a2
    return out


res = {"n_tasks": len(ids)}
for version in ("opus", "gpt", "both"):
    acc = {}
    nrel = 0
    for tid in ids:
        if tasks[tid]["expect_none"]:
            continue
        ss = sets(tid, version)
        nrel += len(ss["all"])
        for m in METHODS:
            pos = {s: i + 1 for i, s in enumerate(rk[tid][m])}
            for k, rel in ss.items():
                if not rel:
                    continue
                for cut in (10, 50):
                    acc.setdefault(f"{m}|{k}|{cut}", []).append(sum(pos.get(s, 999) <= cut for s in rel) / len(rel))
    res[version] = {"relevant_pairs": nrel,
                    **{key: {"mean": round(sum(v) / len(v), 3), "n": len(v)} for key, v in acc.items()}}
(S3 / "cross-label-table1.json").write_text(json.dumps(res, indent=1))
for version in ("opus", "gpt", "both"):
    r = res[version]
    print(f"== {version}  relevant pairs {r['relevant_pairs']}  n(all)={r['bm25_q1|all|50']['n']} n(2a)={r['bm25_q1|2a|50']['n']} n(proc)={r['bm25_q1|process|50']['n']}")
    for m in METHODS:
        print(m.ljust(8), *[r[f"{m}|{k}|{c}"]["mean"] for k in ("all", "2a", "process") for c in (10, 50)])
