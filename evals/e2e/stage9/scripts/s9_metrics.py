#!/usr/bin/env python3
"""§4 metrics, baseline index vs staging. Labels: v5-ss-b (baseline) and v5-ss-b-s9g (staging: migrated + §5 grades;
falls back to v5-ss-b-s9 when §5 has not run). index relevant = grade >= 2 keys that are records of that index.
usage: s9_metrics.py <staging_dir> <baseline_results.json> <staging_results.json> <staging_select.jsonl> -> metrics-9.json"""
import json
import statistics as st
import sys
from pathlib import Path

from s9_common import OUT, BASE_INDEX, E2E, GAP, S9, by_id, records, rel_sets, tasks, vb

base_ids, stg_ids = set(records(BASE_INDEX)), set(records(sys.argv[1]))
new_ids = stg_ids - base_ids
ids = lambda p: {t: [x["id"] for x in r.get("results", [])] for t, r in json.loads(Path(p).read_text()).items()}  # noqa: E731
RB, RS = ids(sys.argv[2]), ids(sys.argv[3])
sp = OUT / "oracle-v5-ss-b-s9g.jsonl"
so = by_id(sp if sp.exists() else OUT / "oracle-v5-ss-b-s9.jsonl")
Rb, Rs = rel_sets(vb, base_ids), rel_sets(so, stg_ids)
grade_s = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in so.items()}
REL_all = [t for t in tasks if not tasks[t]["expect_none"] and any(x["grade"] >= 2 for x in so[t]["pool"])]
idx_b = [t for t in tasks if not tasks[t]["expect_none"] and Rb[t]]
idx_s = [t for t in tasks if not tasks[t]["expect_none"] and Rs[t]]
hit = lambda rk, R, ts, k: round(sum(bool(set(rk[t][:k]) & R[t]) for t in ts) / len(ts), 3)  # noqa: E731
rec = lambda rk, R, ts: round(st.mean(len(set(rk[t][:50]) & R[t]) / len(R[t]) for t in ts), 3)  # noqa: E731
out = {"labels_staging": sp.name if sp.exists() else "oracle-v5-ss-b-s9.jsonl (no §5 grades yet)",
       "1_index_relevant_tasks": {"relevant_tasks_all": len(REL_all), "baseline": len(idx_b), "staging": len(idx_s)},
       "2_gap56": {"baseline": sum(bool(Rb[t]) for t in GAP), "staging": sum(bool(Rs[t]) for t in GAP),
                   "recovered": sum(bool(Rs[t]) and not Rb[t] for t in GAP)},
       "3_rc": {"own_denominator": {"baseline": {"n": len(idx_b), "hit@10": hit(RB, Rb, idx_b, 10), "hit@50": hit(RB, Rb, idx_b, 50), "recall@50": rec(RB, Rb, idx_b)},
                                    "staging": {"n": len(idx_s), "hit@10": hit(RS, Rs, idx_s, 10), "hit@50": hit(RS, Rs, idx_s, 50), "recall@50": rec(RS, Rs, idx_s)}},
                "baseline_270_fixed": {"n": len(idx_b), "staging_hit@10": hit(RS, Rs, idx_b, 10), "staging_hit@50": hit(RS, Rs, idx_b, 50)},
                "unlabeled_in_staging_top50": sum(len(set(RS[t][:50]) - set(grade_s[t])) for t in tasks),
                "new_records_in_staging_top50": sum(len(set(RS[t][:50]) & new_ids) for t in tasks),
                "new_records_in_staging_top10": sum(len(set(RS[t][:10]) & new_ids) for t in tasks)}}


def sel_stats(S, R, idx, grades, idset):
    nomatch = [t for t in tasks if tasks[t]["expect_none"] or not R[t]]
    en = [t for t in nomatch if tasks[t]["expect_none"]]
    other = [t for t in nomatch if not tasks[t]["expect_none"]]
    fixed = [t for t in tasks if tasks[t]["expect_none"] or not Rs[t]]
    L = {t: set(S.get(t, [])) for t in tasks}
    lt = [t for t in idx if L[t]]
    return {"rel_load": round(sum(bool(L[t] & R[t]) for t in idx) / len(idx), 3),
            "precision_task": round(sum(bool(L[t] & R[t]) for t in lt) / len(lt), 3) if lt else None,
            "precision_skill": round(sum(len(L[t] & R[t]) for t in idx) / max(1, sum(len(L[t]) for t in idx)), 3),
            "unneeded_load_rate": round(sum(bool(L[t]) for t in nomatch) / len(nomatch), 3), "nomatch_n": len(nomatch),
            "unneeded_expect_none": f"{sum(bool(L[t]) for t in en)}/{len(en)}", "unneeded_other": f"{sum(bool(L[t]) for t in other)}/{len(other)}",
            "unneeded_fixed_set": f"{sum(bool(L[t]) for t in fixed)}/{len(fixed)}",
            "only_grade_le1_loaded_on_relevant": sum(bool(L[t]) and not (L[t] & R[t]) for t in idx),
            "unlabeled_picks": sum(1 for t in tasks for k in L[t] if k not in grades[t]),
            "picks_new_records": sum(1 for t in tasks for k in L[t] if k in new_ids), "none": sum(not L[t] for t in tasks)}


gb = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in vb.items()}
base_sel = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()} for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
stg_sel = {json.loads(l)["id"]: json.loads(l)["skills"] for l in Path(sys.argv[4]).open()} if Path(sys.argv[4]).exists() else None
sb = {f"baseline r{i + 1}": sel_stats(s, Rb, idx_b, gb, base_ids) for i, s in enumerate(base_sel)}
num = [k for k, v in sb["baseline r1"].items() if isinstance(v, (int, float)) and v is not None]
sb["baseline range"] = {k: [min(sb[f"baseline r{i}"][k] for i in (1, 2, 3)), max(sb[f"baseline r{i}"][k] for i in (1, 2, 3))] for k in num}
if stg_sel:
    sb["staging r1"] = sel_stats(stg_sel, Rs, idx_s, grade_s, stg_ids)
    sb["staging outside baseline range"] = {k: not (sb["baseline range"][k][0] <= sb["staging r1"][k] <= sb["baseline range"][k][1]) for k in num if sb["staging r1"][k] is not None}
out["4_select"] = sb
(OUT / "metrics-9.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
