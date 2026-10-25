#!/usr/bin/env python3
"""Stage 8 §4: 1) 194-task final load (v5-ss), 3) hit@10/25/50 (v5-ss-b; v5-ss lower bound), 4) candidate-balance
sensitivity (v5-ss, SS search candidates cut to top-10 per condition), 5) short-query experiment (v3 and v5-ss-b).
Writes followup-8.json. Parts needing oracle-v5-ss-b.jsonl are skipped while it does not exist."""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ss_parse import parse_load, parse_search  # noqa: E402

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
jl = lambda p: {json.loads(l)["id"]: json.loads(l) for l in Path(p).open()}  # noqa: E731
tasks = jl(E2E / "stage3" / "tasks.jsonl")
v5 = jl(S8 / "oracle-v5-ss.jsonl")
v3 = jl(E2E / "stage3" / "followup" / "oracle-v3.jsonl")
cands = json.loads((S8 / "cands.json").read_text())
ss_map = json.loads((S8 / "ss-map.json").read_text())
sel = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()}
       for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
sk = json.loads((S8 / "search-kw.json").read_text())
main = {}
for l in (S8 / "raw" / "main.jsonl").open():
    r = json.loads(l)
    main[(r["task"], r["kind"])] = r
REFUSAL = ["t311", "t317", "t327", "t330"]
key = lambda sid: (ss_map.get(sid) or {}).get("merged_into") or "ss:" + sid.lower()  # noqa: E731
ssrank = {k: {t: [key(x["id"]) for x in parse_search(main[(t, k)]["text"]) if x["id"]] for t in tasks} for k in ("SS-q1", "SS-q3", "SS-kw")}


def loaded(t, kind):
    if parse_load(main[(t, kind)]["text"]) is None:
        return set()
    return {k for k, e in cands[t].items() if kind in e["sources"]}


def rel(o):
    return {t: set(x["relevant"]) for t, x in o.items()}


def hit(rank, R, ts, k):
    return round(sum(bool(set(rank[t][:k]) & R[t]) for t in ts) / len(ts), 3) if ts else None


out = {}
# ---- 1) 194-task final load (v5-ss)
R5 = rel(v5)
idx194 = [t for t in tasks if not tasks[t]["expect_none"] and any(not k.startswith("ss:") for k in R5[t])]


def load_stats(L, ts, R):
    loaded_ts = [t for t in ts if L[t]]
    return {"rel_load_rate": round(sum(bool(L[t] & R[t]) for t in ts) / len(ts), 3),
            "rel_load_n": sum(bool(L[t] & R[t]) for t in ts), "loaded_tasks": len(loaded_ts),
            "precision_task": round(sum(bool(L[t] & R[t]) for t in loaded_ts) / len(loaded_ts), 3) if loaded_ts else None,
            "precision_skill": round(sum(len(L[t] & R[t]) for t in ts) / max(1, sum(len(L[t]) for t in ts)), 3),
            "loaded_skills": sum(len(L[t]) for t in ts)}


fl = {f"SF S-b' r{i + 1}": load_stats({t: set(s.get(t, [])) for t in tasks}, idx194, R5) for i, s in enumerate(sel)}
fl["SF S-b' mean"] = {m: round(st.mean(fl[f"SF S-b' r{i}"][m] for i in (1, 2, 3)), 3) for m in fl["SF S-b' r1"]}
fl["SS-load-kw (short)"] = load_stats({t: loaded(t, "SS-load-kw") for t in tasks}, idx194, R5)
fl["SS-load-full"] = load_stats({t: loaded(t, "SS-load-full") for t in tasks}, idx194, R5)
out["1_final_load_194"] = {"n": len(idx194), **fl}

# ---- 4) candidate-balance sensitivity (v5-ss): SS search candidates cut to top-10 per condition
keep = {}
for t in tasks:
    kk = set()
    for k, e in cands[t].items():
        if any(s.startswith("SF-") or s.startswith("SS-load") for s in e["sources"]):
            kk.add(k)
    for c in ssrank:
        kk |= set(ssrank[c][t][:10])
    keep[t] = kk
Rt = {t: R5[t] & keep[t] for t in tasks}
REL5 = [t for t in tasks if not tasks[t]["expect_none"] and R5[t]]
RELt = [t for t in tasks if not tasks[t]["expect_none"] and Rt[t]]
ranks = {"SF": {t: sk["R-c"][t] for t in tasks}, **ssrank}
tab = lambda R, ts: {c: {f"@{k}": hit(ranks[c], R, ts, k) for k in (1, 5, 10)} for c in ranks}  # noqa: E731
out["4_balance"] = {"pool_mean_full": round(st.mean(len(cands[t]) for t in tasks), 1), "pool_mean_cut": round(st.mean(len(keep[t]) for t in tasks), 1),
                    "relevant_pairs_full": {"index": sum(1 for t in tasks for k in R5[t] if not k.startswith("ss:")), "ss": sum(1 for t in tasks for k in R5[t] if k.startswith("ss:"))},
                    "relevant_pairs_cut": {"index": sum(1 for t in tasks for k in Rt[t] if not k.startswith("ss:")), "ss": sum(1 for t in tasks for k in Rt[t] if k.startswith("ss:"))},
                    "relevant_tasks_full": len(REL5), "relevant_tasks_cut": len(RELt),
                    "ss_only_tasks_full": sum(all(k.startswith("ss:") for k in R5[t]) for t in REL5),
                    "ss_only_tasks_cut": sum(all(k.startswith("ss:") for k in Rt[t]) for t in RELt),
                    "table1_full": tab(R5, REL5), "table1_cut": tab(Rt, RELt)}

# ---- 3) hit@10/25/50 and 5) short-query experiment
vb_path = S8 / "oracle-v5-ss-b.jsonl"
out["3_hit_25_50"] = {"v5-ss_lower_bound": {"n": len(REL5), "SF": {f"@{k}": hit(ranks["SF"], R5, REL5, k) for k in (10, 25, 50)},
                                            **{c: {f"@{k}": hit(ssrank[c], R5, REL5, k) for k in (10, 25)} for c in ssrank}}}
labsets = {"v3": ({t: set(v3[t]["relevant"]) for t in tasks}, {t: {x["skill"] for x in v3[t]["pool"]} for t in tasks})}
if vb_path.exists():
    vb = jl(vb_path)
    Rb = rel(vb)
    RELb = [t for t in tasks if not tasks[t]["expect_none"] and Rb[t]]
    IDXb = [t for t in RELb if any(not k.startswith("ss:") for k in Rb[t])]
    out["3_hit_25_50"]["v5-ss-b"] = {
        dn: {"n": len(ts), "SF": {f"@{k}": hit(ranks["SF"], Rb, ts, k) for k in (10, 25, 50)},
             **{c: {f"@{k}": hit(ssrank[c], Rb, ts, k) for k in (10, 25)} for c in ssrank}}
        for dn, ts in (("all_relevant", RELb), ("index_relevant", IDXb))}
    out["3_hit_25_50"]["denominator_change"] = {"relevant_tasks_v5ss": len(REL5), "relevant_tasks_v5ssb": len(RELb),
                                                "index_relevant_v5ss": len(idx194), "index_relevant_v5ssb": len(IDXb)}
    flb = {f"SF S-b' r{i + 1}": load_stats({t: set(s.get(t, [])) for t in tasks}, IDXb, Rb) for i, s in enumerate(sel)}
    flb["SF S-b' mean"] = {m_: round(st.mean(flb[f"SF S-b' r{i}"][m_] for i in (1, 2, 3)), 3) for m_ in flb["SF S-b' r1"]}
    flb["SS-load-kw (short)"] = load_stats({t: loaded(t, "SS-load-kw") for t in tasks}, IDXb, Rb)
    flb["SS-load-full"] = load_stats({t: loaded(t, "SS-load-full") for t in tasks}, IDXb, Rb)
    out["1b_final_load_index_relevant_v5ssb"] = {"n": len(IDXb), **flb}
    Rbi = {t: {k for k in Rb[t] if not k.startswith("ss:")} for t in tasks}
    labsets["v5-ss-b (index skills)"] = (Rbi, {t: {x["skill"] for x in vb[t]["pool"]} for t in tasks})
exp = {}
for ln, (R, pool) in labsets.items():
    ts = [t for t in tasks if not tasks[t]["expect_none"] and R[t]]
    row = {"n": len(ts)}
    for c in ("R-c", "kw", "R-c+kw"):
        rk = sk[c]
        row[c] = {"hit@10": hit(rk, R, ts, 10), "hit@50": hit(rk, R, ts, 50),
                  "recall@50": round(st.mean(len(set(rk[t][:50]) & R[t]) / len(R[t]) for t in ts), 3),
                  "unlabeled_share_top50": round(sum(len(set(rk[t][:50]) - pool[t]) for t in tasks) / max(1, sum(len(rk[t][:50]) for t in tasks)), 3)}
    exp[ln] = row
out["5_short_query"] = exp
out["5_refusal_tasks"] = {t: {"expect_none": tasks[t]["expect_none"], "kw": json.loads([l for l in (S8 / "kw-queries.jsonl").open() if f'"{t}"' in l][0])["query"][:80],
                              "kw_top5": sk["kw"][t][:5], "R-c+kw_top10_changed_vs_R-c": sk["R-c+kw"][t][:10] != sk["R-c"][t][:10]} for t in REFUSAL}
out["5_kw_empty_tasks"] = [t for t in tasks if not sk["kw"][t]]
(S8 / "followup-8.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
