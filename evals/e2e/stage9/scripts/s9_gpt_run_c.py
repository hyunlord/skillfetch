#!/usr/bin/env python3
"""GPT cross-labels (gpt-run-b-60.jsonl) applied to run-c. claude-run-b-60.jsonl (same model family) is not used.
1) relevance kappa and disagreement direction by row kind (new / existing): GPT-only relevant (Opus <2, GPT >=2) vs
   Opus-only relevant (Opus >=2, GPT <2).
2) On the 60 tasks (non-expect_none = D), with run-c R-c top-10 and run-c S-b' picks vs the baseline index top-10 and
   baseline S-b' r1-r3: intersection labels only where both judges graded a row; a row GPT did not grade is
   "unlabeled", never "not relevant". Per task: confirmed hit (a row both >= 2), confirmed miss (all rows double-graded,
   none both >= 2; for picks also: no picks), undetermined (otherwise). Rates as [confirmed hit / D,
   (confirmed hit + undetermined) / D]. Opus-only values (every row Opus-graded) for reference. Writes gpt-run-c-60.json."""
import json

from s9_common import E2E, S9, by_id, tasks

key = json.loads((S9 / "blind-run-b-60-key.json").read_text())
gpt = {}
for r in map(json.loads, (S9 / "gpt-run-b-60.jsonl").open()):
    gpt[(r["task_id"], key[r["task_id"]][r["candidate_id"]]["skill"])] = int(r["grade"])
T = sorted(key)
D = [t for t in T if not tasks[t]["expect_none"]]
opus_c = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in by_id(S9 / "run-c" / "oracle-v5-ss-b-s9g.jsonl").items()}
vb = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in by_id(E2E / "stage8" / "oracle-v5-ss-b.jsonl").items()}


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


rows = [(t, v["skill"], "new" if v["source"] == "new" else "existing", v["opus_grade"]) for t in T for v in key[t].values()]
out = {"excluded": "claude-run-b-60.jsonl (same family as Opus) not used; not present in stage9/", "direction": {}}
for kind in ("new", "existing"):
    rs = [r for r in rows if r[2] == kind]
    o = [r[3] >= 2 for r in rs]
    g = [gpt[(r[0], r[1])] >= 2 for r in rs]
    go, oo = sum(b and not a for a, b in zip(o, g)), sum(a and not b for a, b in zip(o, g))
    out["direction"][kind] = {"n": len(rs), "relevance_kappa": kappa(o, g), "both": sum(a and b for a, b in zip(o, g)),
                              "gpt_only": go, "opus_only": oo, "gpt_only_rate": round(go / len(rs), 3), "opus_only_rate": round(oo / len(rs), 3),
                              "opus_only_share_of_disagreements": round(oo / (go + oo), 3) if go + oo else None}
# rankings / picks
ld = lambda p: {t: [x["id"] for x in r["results"]] for t, r in json.loads(p.read_text()).items()}  # noqa: E731
RC, RB = ld(S9 / "run-c" / "results-rc-staging-3.json"), ld(S9 / "dry" / "results-rc-baseline.json")
selc = {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S9 / "run-c" / "select-S-bp-staging-3.jsonl").open()}
selb = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()} for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]


def classify(items_by_task, opus, empty_is_miss):
    hit = miss = und = 0
    for t in D:
        items = items_by_task.get(t, [])
        both = [k for k in items if (t, k) in gpt]
        if any(opus[t].get(k, 0) >= 2 and gpt[(t, k)] >= 2 for k in both):
            hit += 1
        elif len(both) == len(items) and (items or empty_is_miss):
            miss += 1
        else:
            und += 1
    return {"D": len(D), "confirmed_hit": hit, "confirmed_miss": miss, "undetermined": und,
            "rate_range": [round(hit / len(D), 3), round((hit + und) / len(D), 3)]}


def opus_only(items_by_task, opus):
    return round(sum(any(opus[t].get(k, 0) >= 2 for k in items_by_task.get(t, [])) for t in D) / len(D), 3)


cov = lambda R: (sum((t, k) in gpt for t in D for k in R[t][:10]), sum(len(R[t][:10]) for t in D))  # noqa: E731
top_c, top_b = {t: RC[t][:10] for t in D}, {t: RB[t][:10] for t in D}
out["coverage_top10"] = {"run-c": "%d/%d" % cov(RC), "baseline": "%d/%d" % cov(RB)}
out["coverage_picks"] = {"run-c": f"{sum((t, k) in gpt for t in D for k in selc.get(t, []))}/{sum(len(selc.get(t, [])) for t in D)}",
                         **{f"baseline r{i + 1}": f"{sum((t, k) in gpt for t in D for k in s.get(t, []))}/{sum(len(s.get(t, [])) for t in D)}" for i, s in enumerate(selb)}}
out["rc_hit@10"] = {"run-c": {"intersection": classify(top_c, opus_c, True), "opus_only": opus_only(top_c, opus_c)},
                    "baseline": {"intersection": classify(top_b, vb, True), "opus_only": opus_only(top_b, vb)}}
out["sbp_rel_load"] = {"run-c": {"intersection": classify(selc, opus_c, True), "opus_only": opus_only(selc, opus_c)},
                       **{f"baseline r{i + 1}": {"intersection": classify(s, vb, True), "opus_only": opus_only(s, vb)} for i, s in enumerate(selb)}}
(S9 / "gpt-run-c-60.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
