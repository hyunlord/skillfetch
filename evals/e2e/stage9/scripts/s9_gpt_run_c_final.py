#!/usr/bin/env python3
"""When gpt-run-c-gap.jsonl arrives (task_id, candidate_id, grade, process; every blind-run-c-gap row): merge with
gpt-run-b-60.jsonl by (task, skill) and recompute on the 54 non-trivial tasks, intersection labels (relevant = Opus >= 2
and GPT >= 2), R-c hit@10 and S-b' relevant load for run-c and the baseline index (r1-r3), with the same confirmed-hit /
confirmed-miss / undetermined split as s9_gpt_run_c.py; undetermined must be 0. Writes gpt-run-c-final.json."""
import json
import sys

from s9_common import E2E, S9, by_id, tasks

gp = S9 / "gpt-run-c-gap.jsonl"
if not gp.exists():
    sys.exit("gpt-run-c-gap.jsonl not found — waiting for the GPT labels")
k60 = json.loads((S9 / "blind-run-b-60-key.json").read_text())
kgap = json.loads((S9 / "blind-run-c-gap-key.json").read_text())
gpt = {}
for r in map(json.loads, (S9 / "gpt-run-b-60.jsonl").open()):
    gpt[(r["task_id"], k60[r["task_id"]][r["candidate_id"]]["skill"])] = int(r["grade"])
gap = [json.loads(l) for l in gp.open() if l.strip()]
got = {(r["task_id"], r["candidate_id"]) for r in gap}
miss = [(t, c) for t, v in kgap.items() for c in v if (t, c) not in got]
extra = [x for x in got if x[0] not in kgap or x[1] not in kgap[x[0]]]
if miss or extra:
    sys.exit(f"gap file: {len(miss)} rows missing, {len(extra)} unknown, e.g. {(miss + extra)[:3]}")
for r in gap:
    gpt[(r["task_id"], kgap[r["task_id"]][r["candidate_id"]]["skill"])] = int(r["grade"])
D = sorted(t for t in k60 if not tasks[t]["expect_none"])
opus_c = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in by_id(S9 / "run-c" / "oracle-v5-ss-b-s9g.jsonl").items()}
vb = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in by_id(E2E / "stage8" / "oracle-v5-ss-b.jsonl").items()}
ld = lambda p: {t: [x["id"] for x in r["results"]] for t, r in json.loads(p.read_text()).items()}  # noqa: E731
RC, RB = ld(S9 / "run-c" / "results-rc-staging-3.json"), ld(S9 / "dry" / "results-rc-baseline.json")
selc = {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S9 / "run-c" / "select-S-bp-staging-3.jsonl").open()}
selb = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()} for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]


def classify(items, opus):
    hit = miss = und = 0
    for t in D:
        it = items.get(t, [])
        if any((t, k) in gpt and opus[t].get(k, 0) >= 2 and gpt[(t, k)] >= 2 for k in it):
            hit += 1
        elif all((t, k) in gpt for k in it):
            miss += 1
        else:
            und += 1
    return {"D": len(D), "confirmed_hit": hit, "confirmed_miss": miss, "undetermined": und, "rate": round(hit / len(D), 3) if und == 0 else None,
            "range": [round(hit / len(D), 3), round((hit + und) / len(D), 3)]}


opus_only = lambda items, opus: round(sum(any(opus[t].get(k, 0) >= 2 for k in items.get(t, [])) for t in D) / len(D), 3)  # noqa: E731
top_c, top_b = {t: RC[t][:10] for t in D}, {t: RB[t][:10] for t in D}
out = {"gpt_rows_total": len(gpt), "gap_rows": len(gap),
       "coverage_top10": {"run-c": f"{sum((t, k) in gpt for t in D for k in top_c[t])}/{sum(len(v) for v in top_c.values())}",
                          "baseline": f"{sum((t, k) in gpt for t in D for k in top_b[t])}/{sum(len(v) for v in top_b.values())}"},
       "rc_hit@10": {"run-c": {"intersection": classify(top_c, opus_c), "opus_only": opus_only(top_c, opus_c)},
                     "baseline": {"intersection": classify(top_b, vb), "opus_only": opus_only(top_b, vb)}},
       "sbp_rel_load": {"run-c": {"intersection": classify(selc, opus_c), "opus_only": opus_only(selc, opus_c)},
                        **{f"baseline r{i + 1}": {"intersection": classify(s, vb), "opus_only": opus_only(s, vb)} for i, s in enumerate(selb)}}}
gap_rows = [(r["task_id"], kgap[r["task_id"]][r["candidate_id"]]) for r in gap]
both = lambda t, k, opus: opus[t].get(k, 0) >= 2 and gpt[(t, k)] >= 2  # noqa: E731
out["gap_rows_relevance"] = {"opus_ge2": sum((vb if "base_top10" in v["where"] or "base_picks" in v["where"] else opus_c)[t].get(v["skill"], 0) >= 2 for t, v in gap_rows),
                             "gpt_ge2": sum(gpt[(t, v["skill"])] >= 2 for t, v in gap_rows)}
out["all_undetermined_zero"] = all(x["intersection"]["undetermined"] == 0 for d in (out["rc_hit@10"], out["sbp_rel_load"]) for x in d.values())
(S9 / "gpt-run-c-final.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
