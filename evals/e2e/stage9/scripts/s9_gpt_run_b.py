#!/usr/bin/env python3
"""§12-2 after GPT labels arrive (gpt-run-b-60.jsonl: task_id, candidate_id, grade, process; every blind row):
agreement with Opus (exact, ±1, relevance kappa, process kappa; overall / new / old), then on the 60 tasks with
intersection labels (a GPT-seen row is relevant only if Opus >= 2 and GPT >= 2; unseen rows keep Opus): R-c hit@10
(v5-ss-b full labels; baseline vs staging; own and fixed denominators) and S-b' relevant load (baseline 3 runs vs
staging 1), plus GPT coverage of top-10 slots and picks. Refuses while the file is missing or incomplete."""
import json
import sys
from pathlib import Path

from s9_common import BASE_INDEX, E2E, S9, by_id, records, tasks

gp = S9 / "gpt-run-b-60.jsonl"
if not gp.exists():
    sys.exit("gpt-run-b-60.jsonl not found — waiting for the GPT labels")
key = json.loads((S9 / "blind-run-b-60-key.json").read_text())
gpt = {(r["task_id"], r["candidate_id"]): r for r in (json.loads(l) for l in gp.open() if l.strip())}
miss = [(t, c) for t, v in key.items() for c in v if (t, c) not in gpt]
if miss:
    sys.exit(f"GPT file misses {len(miss)} rows, e.g. {miss[:3]}")
base_ids = set(records(BASE_INDEX))
so = by_id(S9 / "run-b" / "oracle-v5-ss-b-s9g.jsonl")
opus = {t: {x["skill"]: x for x in o["pool"]} for t, o in so.items()}
T = sorted(key)


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def agree(rows):
    o = [opus[t][v["skill"]]["grade"] for t, c, v in rows]
    g = [int(gpt[(t, c)]["grade"]) for t, c, v in rows]
    return {"n": len(rows), "exact": round(sum(a == b for a, b in zip(o, g)) / len(o), 3), "within1": round(sum(abs(a - b) <= 1 for a, b in zip(o, g)) / len(o), 3),
            "relevance_kappa": kappa([a >= 2 for a in o], [b >= 2 for b in g]),
            "process_kappa": kappa([opus[t][v["skill"]]["process"] for t, c, v in rows], [bool(gpt[(t, c)].get("process")) for t, c, v in rows]),
            "opus_ge2": sum(a >= 2 for a in o), "gpt_ge2": sum(b >= 2 for b in g), "both_ge2": sum(a >= 2 and b >= 2 for a, b in zip(o, g))}


allr = [(t, c, v) for t in T for c, v in key[t].items()]
out = {"agreement": {"all": agree(allr), "new": agree([r for r in allr if r[2]["source"] == "new"]),
                     "old": agree([r for r in allr if r[2]["source"] != "new"]),
                     "old_staging_top10": agree([r for r in allr if r[2]["source"] == "old_staging_top10"]),
                     "old_baseline_top10": agree([r for r in allr if r[2]["source"] == "old_baseline_top10"])}}
seen = {(t, v["skill"]): int(gpt[(t, c)]["grade"]) for t, c, v in allr}


def rel(t, k, inter):
    g = opus[t].get(k, {}).get("grade", 0)
    if inter and (t, k) in seen:
        return g >= 2 and seen[(t, k)] >= 2
    return g >= 2


RS = {t: [x["id"] for x in r["results"]] for t, r in json.loads((S9 / "run-b" / "results-rc-staging-2.json").read_text()).items()}
RB = {t: [x["id"] for x in r["results"]] for t, r in json.loads((S9 / "dry" / "results-rc-baseline.json").read_text()).items()}
sel_s = {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S9 / "run-b" / "select-S-bp-staging-2.jsonl").open()}
sel_b = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()} for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
for nm, inter in (("opus", False), ("intersection", True)):
    Rb = {t: {k for k in opus[t] if k in base_ids and rel(t, k, inter)} for t in T}
    Rs = {t: {k for k in opus[t] if rel(t, k, inter)} - {k for k in opus[t] if k.startswith("ss:")} for t in T}
    db = [t for t in T if not tasks[t]["expect_none"] and Rb[t]]
    ds = [t for t in T if not tasks[t]["expect_none"] and Rs[t]]
    h = lambda rk, R, ts: round(sum(bool(set(rk[t][:10]) & R[t]) for t in ts) / len(ts), 3) if ts else None  # noqa: E731
    rl = lambda S, R, ts: round(sum(bool(set(S.get(t, [])) & R[t]) for t in ts) / len(ts), 3) if ts else None  # noqa: E731
    out[nm] = {"n_baseline_relevant": len(db), "n_staging_relevant": len(ds),
               "rc_hit@10_baseline": h(RB, Rb, db), "rc_hit@10_staging_own": h(RS, Rs, ds), "rc_hit@10_staging_on_baseline_denominator": h(RS, Rs, db),
               "sbp_rel_load_baseline_r1_r3": [rl(s, Rb, db) for s in sel_b], "sbp_rel_load_staging": rl(sel_s, Rs, ds)}
out["coverage"] = {"staging_top10_slots_seen": f"{sum((t, k) in seen for t in T for k in RS[t][:10])}/{sum(len(RS[t][:10]) for t in T)}",
                   "baseline_top10_slots_seen": f"{sum((t, k) in seen for t in T for k in RB[t][:10])}/{sum(len(RB[t][:10]) for t in T)}",
                   "staging_picks_seen": f"{sum((t, k) in seen for t in T for k in sel_s.get(t, []))}/{sum(len(sel_s.get(t, [])) for t in T)}",
                   "baseline_r1_picks_seen": f"{sum((t, k) in seen for t in T for k in sel_b[0].get(t, []))}/{sum(len(sel_b[0].get(t, [])) for t in T)}"}
(S9 / "gpt-run-b-60.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
