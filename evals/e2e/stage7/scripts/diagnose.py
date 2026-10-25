#!/usr/bin/env python3
"""7a diagnosis (DESIGN.md §1-2). For the 16 direction pairs (pairs-16.json), side-specific relevant skills T_s
(oracle v4r2: grade >= 2 on side s, < 2 on the other side). One isolated claude -p call (stage6 batch helper) judges,
per pair, whether each skill in T_s handles side s's direction -> diag-match.json; M_s = the matching ones.
Each of the 48 (pair, generation) cases of 6a S-b (select-S-b.jsonl, -rep2, -rep3) that did not move with the
direction is classed: (c) label (M_a and M_b both empty) > (a) search (no M_s in side s's R-c top-50, for every side
with M_s) > (b) selection. Writes diagnosis.json."""
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
orc = {json.loads(l)["id"]: json.loads(l) for l in (S6 / "oracle-v4r2.jsonl").open()}
res = json.loads((S6 / "gen" / "results-rc.json").read_text())
top50 = {t: [x["id"] for x in v["results"]] for t, v in res.items()}
gens = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f).open()} for f in ("select-S-b.jsonl", "select-S-b-rep2.jsonl", "select-S-b-rep3.jsonl")]
P16 = json.loads((S7 / "pairs-16.json").read_text())
pairs = {}
for t in tasks.values():
    if t["pair_id"] in P16:
        pairs.setdefault(t["pair_id"], {})[t["pair_side"]] = t
grade = {t: {x["skill"]: x["grade"] for x in orc[t]["pool"]} for t in orc}
rel = {t: set(orc[t]["relevant"]) for t in orc}
T = {}
for p, s in pairs.items():
    a, b = s["a"]["id"], s["b"]["id"]
    T[p] = {"a": sorted(rel[a] - rel[b]), "b": sorted(rel[b] - rel[a])}

SYS = S7 / "scripts" / "sys-diag-match.txt"
SYS.write_text("""You check skill labels for a study of how a coding agent follows a working direction. Each item is one request
written twice, with two different working directions (side a and side b). For each side you get the skills judged
relevant to that side only, as cards. For every listed skill, answer whether the skill handles that side's working
direction itself (for example a test-first skill for "test-first (TDD)", an accessibility skill for "accessibility
first", a dependency-minimising skill for "no new dependencies") — not merely the task's subject.
Output JSON only: [{"pair": "<pair id>", "side": "a" | "b", "skill": "<skill id>", "matches_direction": true | false}]
for every listed skill, in the order given.
""")
items = []
for p in sorted(pairs):
    s = pairs[p]
    blk = [f"### {p}\nrequest (side a wording):\n{s['a']['text']}\n\nside a direction: {s['a']['direction']}\nside b direction: {s['b']['direction']}"]
    for side in ("a", "b"):
        blk.append(f"\nside {side} only — relevant skills:\n" + ("\n".join(card(x) for x in T[p][side]) or "(none)"))
    items.append("\n".join(blk))
r = call("s7-diag-match", SYS, "ITEMS\n\n" + "\n\n".join(items))
assert not r["is_error"]
match = {}
for x in parse_json_last(r["text"]):
    match[(x["pair"], x["side"], x["skill"])] = bool(x["matches_direction"])
missing = [(p, sd, k) for p in T for sd in ("a", "b") for k in T[p][sd] if (p, sd, k) not in match]
assert not missing, missing
M = {p: {sd: [k for k in T[p][sd] if match[(p, sd, k)]] for sd in ("a", "b")} for p in T}
(S7 / "diag-match.json").write_text(json.dumps({"T": T, "M": M, "match": [{"pair": k[0], "side": k[1], "skill": k[2], "matches": v} for k, v in match.items()],
                                                "cost_usd": r.get("cost_usd")}, indent=1))


def moved(Sa, Sb, Ra, Rb):
    if Sa == Sb:
        return False
    ea, eb = Sa - Sb, Sb - Sa
    return bool(ea | eb) and all(x in Ra for x in ea) and all(x in Rb for x in eb) \
        and not any(x in Rb and x not in Ra for x in ea) and not any(x in Ra and x not in Rb for x in eb)


cases = []
for p in sorted(pairs):
    a, b = pairs[p]["a"]["id"], pairs[p]["b"]["id"]
    for g, sel in enumerate(gens, 1):
        Sa, Sb = set(sel[a]), set(sel[b])
        if moved(Sa, Sb, rel[a], rel[b]):
            cls = "moved"
        elif not M[p]["a"] and not M[p]["b"]:
            cls = "c_label"
        elif all(not any(k in top50[pairs[p][sd]["id"]] for k in M[p][sd]) for sd in ("a", "b") if M[p][sd]):
            cls = "a_search"
        else:
            cls = "b_select"
        cases.append({"pair": p, "gen": g, "class": cls, "dir_a": pairs[p]["a"]["direction"], "dir_b": pairs[p]["b"]["direction"],
                      "sel_a": sorted(Sa), "sel_b": sorted(Sb), "M_a": M[p]["a"], "M_b": M[p]["b"],
                      "M_a_rank": {k: (top50[a].index(k) + 1 if k in top50[a] else None) for k in M[p]["a"]},
                      "M_b_rank": {k: (top50[b].index(k) + 1 if k in top50[b] else None) for k in M[p]["b"]},
                      "T_a": T[p]["a"], "T_b": T[p]["b"]})
by_pair = {}
for p in sorted(pairs):
    cs = Counter(c["class"] for c in cases if c["pair"] == p)
    by_pair[p] = cs.most_common(1)[0][0] if cs else None
out = {"cases": cases, "counts_cases": dict(Counter(c["class"] for c in cases)), "counts_pairs_majority": dict(Counter(by_pair.values())),
       "by_pair": by_pair, "moved_per_gen": [sum(c["class"] == "moved" for c in cases if c["gen"] == g) for g in (1, 2, 3)]}
(S7 / "diagnosis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps({k: out[k] for k in ("counts_cases", "counts_pairs_majority", "moved_per_gen", "by_pair")}, indent=1))
