#!/usr/bin/env python3
"""7a-pool steps 2-3 on oracle-v5-direction-b.jsonl. Direction match is judged (one isolated call, the §2 instructions in
scripts/sys-diag-match.txt) for EVERY grade >= 2 skill of each side of the 20 pairs. Coverage: side s covered = some
grade >= 2 skill on s matches s's direction. Router denominator = pairs whose two relevant sets differ AND both sides are
covered; the rest of the differing pairs = "direction coverage gap". S-b' (and 6a S-b) 3 runs: pairs moved on both bases,
none accuracy, hit, and the §2 diagnosis (M_s = side-specific relevant ∩ matching). Writes rediag-b.json."""
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
ORC = sys.argv[1] if len(sys.argv) > 1 else "oracle-v5-direction-b.jsonl"
TAG = sys.argv[2] if len(sys.argv) > 2 else "b"
orc = {json.loads(l)["id"]: json.loads(l) for l in (S7 / ORC).open()}
top50 = {t: [x["id"] for x in v["results"]] for t, v in json.loads((S6 / "gen" / "results-rc.json").read_text()).items()}
grade = {t: {x["skill"]: x["grade"] for x in orc[t]["pool"]} for t in orc}
rel = {t: set(orc[t]["relevant"]) for t in orc}
pairs = {}
for t in tasks.values():
    if t["pair_id"]:
        pairs.setdefault(t["pair_id"], {})[t["pair_side"]] = t
items = []
for p in sorted(pairs):
    s = pairs[p]
    blk = [f"### {p}\nrequest (side a wording):\n{s['a']['text']}\n\nside a direction: {s['a']['direction']}\nside b direction: {s['b']['direction']}"]
    for side in ("a", "b"):
        blk.append(f"\nside {side} only — relevant skills:\n" + ("\n".join(card(x) for x in sorted(rel[s[side]['id']])) or "(none)"))
    items.append("\n".join(blk))
r = call(f"s7-cover-{TAG}", S7 / "scripts" / "sys-diag-match.txt", "ITEMS\n\n" + "\n\n".join(items))
assert not r["is_error"]
match = {(x["pair"], x["side"], x["skill"]): bool(x["matches_direction"]) for x in parse_json_last(r["text"])}
miss = [(p, sd, k) for p in pairs for sd in ("a", "b") for k in rel[pairs[p][sd]["id"]] if (p, sd, k) not in match]
assert not miss, miss[:5]
cover = {p: {sd: [k for k in sorted(rel[pairs[p][sd]["id"]]) if match[(p, sd, k)]] for sd in ("a", "b")} for p in pairs}
differ = sorted(p for p in pairs if rel[pairs[p]["a"]["id"]] != rel[pairs[p]["b"]["id"]])
DEN = [p for p in differ if cover[p]["a"] and cover[p]["b"]]
GAP = [p for p in differ if p not in DEN]
M = {p: {sd: [k for k in cover[p][sd] if k not in rel[pairs[p]["b" if sd == "a" else "a"]["id"]]] for sd in ("a", "b")} for p in pairs}


def moved(Sa, Sb, Ra, Rb):
    if Sa == Sb:
        return False
    ea, eb = Sa - Sb, Sb - Sa
    return bool(ea | eb) and all(x in Ra for x in ea) and all(x in Rb for x in eb) \
        and not any(x in Rb and x not in Ra for x in ea) and not any(x in Ra and x not in Rb for x in eb)


cov_t = [t for t in orc if rel[t] and not tasks[t]["expect_none"]]
nor = [t for t in orc if not rel[t]]


def run(files):
    gens = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f).open()} for f in files]
    per, cases = [], []
    for gi, g in enumerate(gens, 1):
        mv = [p for p in differ if moved(set(g[pairs[p]["a"]["id"]]), set(g[pairs[p]["b"]["id"]]), rel[pairs[p]["a"]["id"]], rel[pairs[p]["b"]["id"]])]
        for p in DEN:
            a, b = pairs[p]["a"]["id"], pairs[p]["b"]["id"]
            if p in mv:
                cls = "moved"
            elif not M[p]["a"] and not M[p]["b"]:
                cls = "c_label"
            elif all(not any(k in top50[pairs[p][sd]["id"]] for k in M[p][sd]) for sd in ("a", "b") if M[p][sd]):
                cls = "a_search"
            else:
                cls = "b_select"
            cases.append({"pair": p, "gen": gi, "class": cls, "sel_a": sorted(g[a]), "sel_b": sorted(g[b]), "M_a": M[p]["a"], "M_b": M[p]["b"],
                          "M_a_rank": {k: (top50[a].index(k) + 1 if k in top50[a] else None) for k in M[p]["a"]},
                          "M_b_rank": {k: (top50[b].index(k) + 1 if k in top50[b] else None) for k in M[p]["b"]}})
        per.append({"moved_den": sum(p in mv for p in DEN), "moved_all_differ": len(mv), "moved_pairs": mv,
                    "none_acc": round(sum(not g[t] for t in nor) / len(nor), 3),
                    "hit": round(sum(any(grade[t].get(s, 0) >= 2 for s in g[t]) for t in cov_t) / len(cov_t), 3)})
    m = lambda k: round(sum(x[k] for x in per) / 3, 3)  # noqa: E731
    return {"per_generation": per, "mean_moved_den": m("moved_den"), "mean_ratio_den": round(m("moved_den") / len(DEN), 3) if DEN else None,
            "mean_moved_all_differ": m("moved_all_differ"), "mean_ratio_all_differ": round(m("moved_all_differ") / len(differ), 3),
            "mean_none_acc": m("none_acc"), "mean_hit": m("hit"), "counts_cases": dict(Counter(c["class"] for c in cases)),
            "by_pair": {p: Counter(c["class"] for c in cases if c["pair"] == p).most_common(1)[0][0] for p in DEN}, "cases": cases}


out = {"oracle": ORC, "differ": differ, "n_differ": len(differ), "denominator": DEN, "n_den": len(DEN), "coverage_gap": GAP,
       "same_sets": sorted(set(pairs) - set(differ)), "cover": cover, "M": M, "match_cost_usd": r.get("cost_usd"),
       "n_no_relevant": len(nor), "n_cov": len(cov_t), "threshold_ratio": round(13 / 16, 4),
       "S-bp": run(["select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl"]),
       "S-b": run(["select-S-b.jsonl", "select-S-b-rep2.jsonl", "select-S-b-rep3.jsonl"])}
out["baseline_meets"] = bool(out["S-bp"]["mean_ratio_den"] is not None and out["S-bp"]["mean_ratio_den"] >= 13 / 16)
(S7 / f"rediag-{TAG}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
for k in ("n_differ", "same_sets", "n_den", "denominator", "coverage_gap", "n_no_relevant", "n_cov", "baseline_meets"):
    print(k, out[k])
for c in ("S-bp", "S-b"):
    x = out[c]
    print(c, "den moved/gen", [g["moved_den"] for g in x["per_generation"]], "mean", x["mean_moved_den"], "ratio", x["mean_ratio_den"],
          "| all-differ", [g["moved_all_differ"] for g in x["per_generation"]], x["mean_ratio_all_differ"], "| none", x["mean_none_acc"], "hit", x["mean_hit"])
    print("   cases", x["counts_cases"], "by_pair", x["by_pair"])
