#!/usr/bin/env python3
"""§11 rule: pass = (A) or ((B) and (C)).
 (A) §2 fixed-label check (from <OUT>/regress.json).
 (B) full-label R-c hit@50 (baseline relevant ∪ new-record grade>=2 from v5-ss-b-s9g) on the baseline denominators
     (v3 284, v5-ss-b 270) drops <= 0.01 on both.
 (C) S-b' unneeded-load rate on no-match tasks (expect_none or no staging-index relevant under full labels) <= 0.300.
Also reports: full-label R-c hit@10/@50 (own and baseline denominators), index-relevant tasks, gap-56 recovery, S-b'
relevant load / precision / unneeded load, and grade>=2 share of the top-50 (and top-10) slots taken by new records,
by repo. usage: S9_RUN=<run> s9_verdict_c.py <staging_dir> <baseline_results> <staging_results> <staging_select>"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from s9_common import BASE_INDEX, GAP, OUT, by_id, records, tasks, v3, vb

stg = records(sys.argv[1])
base_ids, stg_ids = set(records(BASE_INDEX)), set(stg)
new_ids = stg_ids - base_ids
ids = lambda p: {t: [x["id"] for x in r.get("results", [])] for t, r in json.loads(Path(p).read_text()).items()}  # noqa: E731
RB, RS = ids(sys.argv[2]), ids(sys.argv[3])
sel = {json.loads(l)["id"]: json.loads(l)["skills"] for l in Path(sys.argv[4]).open()}
gp = OUT / "oracle-v5-ss-b-s9g.jsonl"
if not gp.exists():
    sys.exit("oracle-v5-ss-b-s9g.jsonl missing: §5 grading has not run")
so = by_id(gp)
grade = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in so.items()}
newrel = {t: {k for k, g in grade[t].items() if k in new_ids and g >= 2} for t in tasks}
base_v3 = {t: set(v3[t]["relevant"]) for t in tasks}
base_v5 = {t: {x["skill"] for x in vb[t]["pool"] if x["grade"] >= 2 and x["skill"] in base_ids} for t in tasks}
full_v3 = {t: base_v3[t] | newrel[t] for t in tasks}
full_v5 = {t: {k for k, g in grade[t].items() if g >= 2 and k in stg_ids} for t in tasks}
den_v3 = [t for t in tasks if not tasks[t]["expect_none"] and base_v3[t]]
den_v5 = [t for t in tasks if not tasks[t]["expect_none"] and base_v5[t]]
hit = lambda rk, R, ts, k: round(sum(bool(set(rk[t][:k]) & R[t]) for t in ts) / len(ts), 4)  # noqa: E731
rec = lambda rk, R, ts: round(st.mean(len(set(rk[t][:50]) & R[t]) / len(R[t]) for t in ts), 4)  # noqa: E731
unl = sum(len(set(RS[t][:50]) - set(grade[t])) for t in tasks) + sum(1 for t in tasks for k in sel.get(t, []) if k not in grade[t])
out = {"unlabeled_left (top-50 + picks)": unl}
reg = json.loads((OUT / "regress.json").read_text())
A = not reg["reject"]
B = {}
for ln, R, den, Rb in (("v3", full_v3, den_v3, base_v3), ("v5-ss-b", full_v5, den_v5, base_v5)):
    b50, s50 = hit(RB, Rb, den, 50), hit(RS, R, den, 50)
    B[ln] = {"n": len(den), "baseline_hit@50": b50, "staging_hit@50_full": s50, "delta": round(s50 - b50, 4),
             "baseline_hit@10": hit(RB, Rb, den, 10), "staging_hit@10_full": hit(RS, R, den, 10),
             "staging_recall@50_full": rec(RS, R, den)}
B_pass = all(B[l]["delta"] >= -0.01 for l in B)
nomatch = [t for t in tasks if tasks[t]["expect_none"] or not full_v5[t]]
L = {t: set(sel.get(t, [])) for t in tasks}
unneeded = round(sum(bool(L[t]) for t in nomatch) / len(nomatch), 4)
C_pass = unneeded <= 0.300
out["verdict_rule_11"] = {"A_fixed_label_pass": A, "B_full_label_hit50_pass": B_pass, "C_unneeded_load_pass": C_pass,
                          "pass": A or (B_pass and C_pass)}
out["B"] = B
idx_s = [t for t in tasks if not tasks[t]["expect_none"] and full_v5[t]]
out["full_label_own_denominator"] = {"n": len(idx_s), "hit@10": hit(RS, full_v5, idx_s, 10), "hit@50": hit(RS, full_v5, idx_s, 50),
                                     "recall@50": rec(RS, full_v5, idx_s)}
rel_all = [t for t in tasks if not tasks[t]["expect_none"] and any(g >= 2 for g in grade[t].values())]
out["index_relevant_tasks"] = {"relevant_tasks_all": len(rel_all), "baseline": len(den_v5), "staging": len(idx_s),
                               "staging_searchable": sum(any(stg[k]["tier"] in ("A", "B") and stg[k].get("canonical_id", k) == k for k in full_v5[t]) for t in idx_s)}
out["gap56"] = {"baseline": sum(bool(base_v5[t]) for t in GAP), "staging": sum(bool(full_v5[t]) for t in GAP),
                "recovered": sum(bool(full_v5[t]) and not base_v5[t] for t in GAP)}
lt = [t for t in idx_s if L[t]]
out["sbp"] = {"rel_load": round(sum(bool(L[t] & full_v5[t]) for t in idx_s) / len(idx_s), 4),
              "precision_task": round(sum(bool(L[t] & full_v5[t]) for t in lt) / len(lt), 4),
              "precision_skill": round(sum(len(L[t] & full_v5[t]) for t in idx_s) / max(1, sum(len(L[t]) for t in idx_s)), 4),
              "unneeded_load_rate": unneeded, "nomatch_n": len(nomatch),
              "unneeded_expect_none": f"{sum(bool(L[t]) for t in nomatch if tasks[t]['expect_none'])}/{sum(tasks[t]['expect_none'] for t in nomatch)}",
              "unneeded_other": f"{sum(bool(L[t]) for t in nomatch if not tasks[t]['expect_none'])}/{sum(not tasks[t]['expect_none'] for t in nomatch)}",
              "picks": sum(len(v) for v in L.values()), "picks_new_records": sum(1 for v in L.values() for k in v if k in new_ids),
              "picks_new_records_grade_ge2": sum(1 for t, v in L.items() for k in v if k in new_ids and grade[t].get(k, 0) >= 2)}
slots = defaultdict(lambda: {"top50": 0, "top50_ge2": 0, "top10": 0, "top10_ge2": 0, "top50_g3": 0})
for t in tasks:
    for i, k in enumerate(RS[t][:50]):
        if k in new_ids:
            s = slots[k.split("/")[0]]
            g = grade[t].get(k, 0)
            s["top50"] += 1
            s["top50_ge2"] += g >= 2
            s["top50_g3"] += g == 3
            if i < 10:
                s["top10"] += 1
                s["top10_ge2"] += g >= 2
tot = {k: sum(v[k] for v in slots.values()) for k in ("top50", "top50_ge2", "top10", "top10_ge2", "top50_g3")}
fmt = lambda v: {**v, "top50_ge2_rate": round(v["top50_ge2"] / v["top50"], 4) if v["top50"] else None,  # noqa: E731
                 "top10_ge2_rate": round(v["top10_ge2"] / v["top10"], 4) if v["top10"] else None}
out["new_record_slots_by_repo"] = {r: fmt(v) for r, v in sorted(slots.items(), key=lambda x: -x[1]["top50"])}
out["new_record_slots_total"] = fmt(tot)
# for comparison: grade>=2 share of top-50 slots held by baseline-index records (staging and baseline rankings)
bs = [(grade[t].get(k, 0) if k in grade[t] else None) for t in tasks for k in RS[t][:50] if k in base_ids]
bb = [(grade[t].get(k, 0) if k in grade[t] else None) for t in tasks for k in RB[t][:50]]
out["baseline_record_slots"] = {"staging_ranking": {"n": len(bs), "labeled": sum(x is not None for x in bs), "ge2": sum(1 for x in bs if x is not None and x >= 2)},
                                "baseline_ranking": {"n": len(bb), "labeled": sum(x is not None for x in bb), "ge2": sum(1 for x in bb if x is not None and x >= 2)}}
(OUT / "verdict-11.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
