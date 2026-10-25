#!/usr/bin/env python3
"""Stage 8 §4-7: when gpt-ss-60.jsonl arrives (one row per blind-ss-60.jsonl row: task_id, candidate_id, grade 0-3,
process), compare with the Opus v5-ss grades of the same rows: exact, ±1, relevance (grade >= 2) kappa, process kappa.
Then table 1 (hit@1/5/10) and final load on the 60 tasks under Opus labels and under the intersection (both >= 2).
Writes gpt-kappa-8.json. Refuses to run while the GPT file is missing or does not cover every blind row."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
S8 = Path(__file__).resolve().parents[1]
gp = S8 / "gpt-ss-60.jsonl"
if not gp.exists():
    raise SystemExit("gpt-ss-60.jsonl not found — waiting for the GPT labels")
import metrics_8 as m  # noqa: E402

labels = json.loads((S8 / "grade-labels.json").read_text())
blind = [json.loads(l) for l in (S8 / "blind-ss-60.jsonl").open()]
gpt = {(r["task_id"], r["candidate_id"]): r for r in (json.loads(l) for l in gp.open() if l.strip())}
miss = [(b["task_id"], b["candidate_id"]) for b in blind if (b["task_id"], b["candidate_id"]) not in gpt]
if miss:
    raise SystemExit(f"GPT file misses {len(miss)} of {len(blind)} blind rows, e.g. {miss[:3]}")
opus = {t: {x["label"]: x for x in m.orc[t]["pool"]} for t in {b["task_id"] for b in blind}}
pairs = [(opus[b["task_id"]][b["candidate_id"]], gpt[(b["task_id"], b["candidate_id"])]) for b in blind]


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


og, gg = [o["grade"] for o, _ in pairs], [int(g["grade"]) for _, g in pairs]
out = {"rows": len(pairs), "tasks": len(opus), "exact": round(sum(a == b for a, b in zip(og, gg)) / len(og), 3),
       "within1": round(sum(abs(a - b) <= 1 for a, b in zip(og, gg)) / len(og), 3),
       "relevance_kappa": kappa([a >= 2 for a in og], [b >= 2 for b in gg]),
       "process_kappa": kappa([o["process"] for o, _ in pairs], [bool(g.get("process")) for _, g in pairs]),
       "opus_ge2": sum(a >= 2 for a in og), "gpt_ge2": sum(b >= 2 for b in gg), "both_ge2": sum(a >= 2 and b >= 2 for a, b in zip(og, gg))}
T = sorted(opus)
inter = {t: {labels[t][l] for l, x in opus[t].items() if x["grade"] >= 2 and int(gpt[(t, l)]["grade"]) >= 2} for t in T}
for name, R in (("opus", {t: m.R[t] for t in T}), ("intersection", inter)):
    rel = [t for t in T if not m.tasks[t]["expect_none"] and R[t]]
    irr = [t for t in T if m.tasks[t]["expect_none"] or not R[t]]
    tab = {c: {f"@{k}": round(sum(bool(set(m.rank[c][t][:k]) & R[t]) for t in rel) / len(rel), 3) for k in (1, 5, 10)} for c in m.rank}
    fl = {}
    for i, s in enumerate(m.sel):
        L = {t: set(s.get(t, [])) for t in T}
        fl[f"SF r{i + 1}"] = {"rel_load": round(sum(bool(L[t] & R[t]) for t in rel) / len(rel), 3),
                              "irr_loaded": round(sum(bool(L[t]) for t in irr) / len(irr), 3) if irr else None}
    for k in ("SS-load-kw", "SS-load-full"):
        L = {t: ({m.loaded_key(t, k)} - {None}) for t in T}
        fl[k] = {"rel_load": round(sum(bool(L[t] & R[t]) for t in rel) / len(rel), 3),
                 "irr_loaded": round(sum(bool(L[t]) for t in irr) / len(irr), 3) if irr else None}
    out[name] = {"relevant_tasks": len(rel), "irrelevant_tasks": len(irr), "table1": tab, "final_load": fl}
(S8 / "gpt-kappa-8.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
