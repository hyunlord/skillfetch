#!/usr/bin/env python3
"""7a-relabel step 3: on oracle-v5-direction.jsonl, the new denominator (pairs whose two sides' relevant sets differ),
S-b' baseline 3 runs (pairs moved, none accuracy, hit) and the a/b/c diagnosis with the DESIGN §2 rules; the direction
match is judged again for the new side-specific relevant sets (one isolated call, same instructions as diagnose.py).
Also the 6a S-b 3 runs for comparison with the first diagnosis. Writes rediag.json."""
import json
import sys
from collections import Counter
from pathlib import Path

S7 = Path(__file__).resolve().parents[1]
S6 = S7.parent / "stage6"
sys.path.insert(0, str(S6 / "scripts"))
from batch import call, parse_json_last  # noqa: E402
from cards import card  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S7.parent / "stage3" / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S7 / "oracle-v5-direction.jsonl").open()}
top50 = {t: [x["id"] for x in v["results"]] for t, v in json.loads((S6 / "gen" / "results-rc.json").read_text()).items()}
grade = {t: {x["skill"]: x["grade"] for x in orc[t]["pool"]} for t in orc}
rel = {t: set(orc[t]["relevant"]) for t in orc}
pairs = {}
for t in tasks.values():
    if t["pair_id"]:
        pairs.setdefault(t["pair_id"], {})[t["pair_side"]] = t
DEN = sorted(p for p, s in pairs.items() if rel[s["a"]["id"]] != rel[s["b"]["id"]])
T = {p: {"a": sorted(rel[pairs[p]["a"]["id"]] - rel[pairs[p]["b"]["id"]]), "b": sorted(rel[pairs[p]["b"]["id"]] - rel[pairs[p]["a"]["id"]])} for p in DEN}
items = []
for p in DEN:
    s = pairs[p]
    blk = [f"### {p}\nrequest (side a wording):\n{s['a']['text']}\n\nside a direction: {s['a']['direction']}\nside b direction: {s['b']['direction']}"]
    for side in ("a", "b"):
        blk.append(f"\nside {side} only — relevant skills:\n" + ("\n".join(card(x) for x in T[p][side]) or "(none)"))
    items.append("\n".join(blk))
r = call("s7-rediag-match", S7 / "scripts" / "sys-diag-match.txt", "ITEMS\n\n" + "\n\n".join(items))
assert not r["is_error"]
match = {(x["pair"], x["side"], x["skill"]): bool(x["matches_direction"]) for x in parse_json_last(r["text"])}
assert all((p, sd, k) in match for p in T for sd in ("a", "b") for k in T[p][sd])
M = {p: {sd: [k for k in T[p][sd] if match[(p, sd, k)]] for sd in ("a", "b")} for p in T}


def moved(Sa, Sb, Ra, Rb):
    if Sa == Sb:
        return False
    ea, eb = Sa - Sb, Sb - Sa
    return bool(ea | eb) and all(x in Ra for x in ea) and all(x in Rb for x in eb) \
        and not any(x in Rb and x not in Ra for x in ea) and not any(x in Ra and x not in Rb for x in eb)


cov = [t for t in orc if rel[t] and not tasks[t]["expect_none"]]
nor = [t for t in orc if not rel[t]]


def run(files):
    gens = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f).open()} for f in files]
    per, cases = [], []
    for g_i, g in enumerate(gens, 1):
        mv = []
        for p in DEN:
            a, b = pairs[p]["a"]["id"], pairs[p]["b"]["id"]
            Sa, Sb = set(g[a]), set(g[b])
            if moved(Sa, Sb, rel[a], rel[b]):
                cls = "moved"
                mv.append(p)
            elif not M[p]["a"] and not M[p]["b"]:
                cls = "c_label"
            elif all(not any(k in top50[pairs[p][sd]["id"]] for k in M[p][sd]) for sd in ("a", "b") if M[p][sd]):
                cls = "a_search"
            else:
                cls = "b_select"
            cases.append({"pair": p, "gen": g_i, "class": cls, "sel_a": sorted(Sa), "sel_b": sorted(Sb), "M_a": M[p]["a"], "M_b": M[p]["b"],
                          "M_a_rank": {k: (top50[a].index(k) + 1 if k in top50[a] else None) for k in M[p]["a"]},
                          "M_b_rank": {k: (top50[b].index(k) + 1 if k in top50[b] else None) for k in M[p]["b"]}})
        per.append({"pairs_moved": len(mv), "moved_pairs": mv, "none_acc": round(sum(not g[t] for t in nor) / len(nor), 3),
                    "hit": round(sum(any(grade[t].get(s, 0) >= 2 for s in g[t]) for t in cov) / len(cov), 3)})
    by_pair = {p: Counter(c["class"] for c in cases if c["pair"] == p).most_common(1)[0][0] for p in DEN}
    return {"per_generation": per, "mean_pairs_moved": round(sum(x["pairs_moved"] for x in per) / 3, 3),
            "mean_ratio": round(sum(x["pairs_moved"] for x in per) / 3 / len(DEN), 3),
            "mean_none_acc": round(sum(x["none_acc"] for x in per) / 3, 3), "mean_hit": round(sum(x["hit"] for x in per) / 3, 3),
            "counts_cases": dict(Counter(c["class"] for c in cases)), "counts_pairs_majority": dict(Counter(by_pair.values())), "by_pair": by_pair, "cases": cases}


out = {"denominator": len(DEN), "pairs": DEN, "dropped_pairs": sorted(set(pairs) - set(DEN)), "n_no_relevant": len(nor), "n_cov": len(cov),
       "T": T, "M": M, "match_cost_usd": r.get("cost_usd"), "threshold_ratio": round(13 / 16, 4),
       "S-bp": run(["select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl"]),
       "S-b": run(["select-S-b.jsonl", "select-S-b-rep2.jsonl", "select-S-b-rep3.jsonl"])}
out["baseline_meets_pairs"] = out["S-bp"]["mean_ratio"] >= 13 / 16
(S7 / "rediag.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
for k in ("denominator", "dropped_pairs", "n_no_relevant", "n_cov", "baseline_meets_pairs"):
    print(k, out[k])
for c in ("S-bp", "S-b"):
    x = out[c]
    print(c, "moved/gen", [g["pairs_moved"] for g in x["per_generation"]], "mean", x["mean_pairs_moved"], "ratio", x["mean_ratio"], "none", x["mean_none_acc"], "hit", x["mean_hit"])
    print("   cases", x["counts_cases"], "| pairs", x["counts_pairs_majority"])
    print("   by_pair", x["by_pair"])
