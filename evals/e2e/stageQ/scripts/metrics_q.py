#!/usr/bin/env python3
"""Stage Q numbers (DESIGN §1–§6; no gate) from stageQ-private/requests-<tags>.jsonl (extract_q.py), the Q1 judge
scores (judge/scores-p1.jsonl, scores-p2.jsonl, scores-gpt.jsonl if present) and the Q4 verdicts (judge/scores-q4-p*.jsonl).
Writes stageQ-private/metrics-q.json.
  Q1  per task × on/off: Claude score (mean of p1, p2 per output, then mean), per pass, GPT if present, check pass,
      loaded skills, median turns, wall, cost, input tokens; judge agreement p1–p2
  Q2  per arm (S, C) × task position 1–4: premise (task 1: canary read, F/R kept), F (hits / new files), R, other
      occurrences, canary re-read in tasks 2–4
  Q3  per arm × position: skillfetch calls by name, search again (tasks 2–4), reuse of ids loaded in earlier tasks,
      mention of an earlier task's skill name in a reply or diff without loading it in this task
  Q4  per pass: kept / broken / n/a for on loads and for the off baseline (same rules on the paired Q1 off run);
      compliance = kept / (kept + broken); by stage (Q1, Q2, Q5) and by rules source (pre, post); pass agreement
  Q5  trivial: skipped (no load_skills / resolve_and_load call), search calls, turns, cost; named: the named id in
      pinned_ids, loaded, other loads
  Q6  (a) Q1 on vs off medians (wall, turns, input tokens, cost, first skillfetch turn); (b) on-run replies naming a
      loaded skill / using the word skill; (c) blocked: result subtype, timeouts, check, turns and wall vs Q1 on of the
      same task, load attempts, load errors
usage: metrics_q.py <requests.jsonl>"""
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
PRIV = SQ.parent / "stageQ-private"
rows = [r for r in map(json.loads, open(sys.argv[1])) if r["tag"].startswith("m")]


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 3) if xs else None


def short(i):
    return i.split("/")[-1]


out = {}
# ---------------------------------------------------------------- Q1
sc = {}
for p in ("p1", "p2", "gpt"):
    f = PRIV / "judge" / f"scores-{p}.jsonl"
    if f.exists():
        sc[p] = {(s["task"], s["cond"], s["tag"]): s for s in map(json.loads, f.open())}
q1 = {}
for r in rows:
    if r["kind"] != "q1":
        continue
    cond = r["job"].split(":")[2]
    q1.setdefault((r["task"], cond), []).append(r)
out["Q1"] = {}
for (task, cond), rs in sorted(q1.items()):
    per = {p: [sc[p][(task, cond, r["tag"])]["score"] for r in rs if (task, cond, r["tag"]) in sc[p]] for p in sc}
    claude = [(sc["p1"][(task, cond, r["tag"])]["score"] + sc["p2"][(task, cond, r["tag"])]["score"]) / 2 for r in rs]
    out["Q1"][f"{task} {cond}"] = {
        "n": len(rs), "score_claude": mean(claude), **{f"score_{p}": mean(v) for p, v in per.items()},
        "scores_by_tag": {r["tag"]: {p: sc[p][(task, cond, r["tag"])]["score"] for p in sc} for r in rs},
        "ai_look_by_tag": {r["tag"]: {p: sc[p][(task, cond, r["tag"])].get("ai_look") for p in sc} for r in rs},
        "check_pass": sum(r["check_pass"] is True for r in rs), "loaded": {r["tag"]: [short(i) for i in r["loaded"]] for r in rs},
        "turns_med": med([r["turns"] for r in rs]), "wall_med": med([r["wall_s"] for r in rs]),
        "cost_med": med([r["cost_usd"] for r in rs]), "input_tokens_med": med([r["input_tokens"] for r in rs]),
        "first_sf_turn": [r["first_sf_turn"] for r in rs]}
ks = [k for k in sc.get("p1", {}) if k in sc.get("p2", {})]
out["Q1_agreement_p1_p2"] = {"n": len(ks), "same": sum(sc["p1"][k]["score"] == sc["p2"][k]["score"] for k in ks),
                             "within1": sum(abs(sc["p1"][k]["score"] - sc["p2"][k]["score"]) <= 1 for k in ks)}
# ---------------------------------------------------------------- Q2 / Q3
q2 = [r for r in rows if r["kind"] == "q2"]
out["Q2"], out["Q3"] = {}, {}
for arm in ("S", "C"):
    jobs = sorted({r["tag"] for r in q2 if r["job"] == f"q2:{arm}"})
    by = {(r["tag"], r["k"]): r for r in q2 if r["job"] == f"q2:{arm}"}
    prem = {t: bool(by[(t, 1)]["canary_read"] or by[(t, 1)]["canary_pinned"]) and by[(t, 1)]["R"] for t in jobs}
    q2arm, q3arm = {}, {}
    for k in (1, 2, 3, 4):
        rs = [by[(t, k)] for t in jobs]
        base = [by[(t, k)] for t in jobs if prem[t]]
        q2arm[k] = {"n": len(rs), "premise_runs": len(base), "F_hit": sum(r["F_hit"] for r in base),
                    "F_new": sum(r["F_new"] for r in base), "R": sum(r["R"] for r in base),
                    "other": sum(r["other"] for r in base), "canary_reread": sum(bool(r["canary_read"] or r["canary_pinned"]) for r in rs),
                    "runs_with_other": [r["tag"] for r in base if r["other"]]}
        calls = Counter(c for r in rs for c in r["sf_calls"])
        reuse = mention = 0
        for t in jobs:
            r = by[(t, k)]
            earlier = {i for j in range(1, k) for i in by[(t, j)]["loaded"]}
            reuse += bool(earlier & set(r["auto_ids"] + r["pinned_ids"]))
            names = {short(i).split("@")[0] for i in earlier} - {short(i).split("@")[0] for i in r["loaded"]}
            txt = (PRIV / "runs" / f"q2-{arm}-{t}.p{k}.reply.txt").read_text() + \
                (PRIV / "runs" / f"q2-{arm}-{t}.p{k}.diff").read_text(errors="replace")
            mention += any(n in txt for n in names)
        q3arm[k] = {"n": len(rs), "calls": dict(calls), "fired": sum(r["fired"] for r in rs),
                    "searched": sum("search_skills" in r["sf_calls"] for r in rs), "loaded_any": sum(bool(r["loaded"]) for r in rs),
                    "loaded": Counter(short(i) for r in rs for i in r["loaded"]), "reuse_earlier_ids": reuse,
                    "mention_earlier_skill_without_load": mention, "turns_med": med([r["turns"] for r in rs]),
                    "cost_mean": mean([r["cost_usd"] for r in rs])}
    out["Q2"][arm] = {"premise": prem, "positions": q2arm}
    out["Q3"][arm] = q3arm
sbc = PRIV / "sb-condition.json"
out["Q2"]["S-B"] = {"run": False, "condition": json.loads(sbc.read_text())["condition_met"] if sbc.exists() else None}
# ---------------------------------------------------------------- Q4
out["Q4"] = {}
items_by_pass = {}
for p in ("p1", "p2"):
    f = PRIV / "judge" / f"scores-q4-{p}.jsonl"
    if not f.exists():
        continue
    v = list(map(json.loads, f.open()))
    items_by_pass[p] = {(x["request"], x["skill"], x["cond"], x["rule"]): x["verdict"] for x in v}
    agg = defaultdict(Counter)
    for x in v:
        stage = x["job"].split(":")[0]
        agg[f"{stage} {x['cond']}"][x["verdict"]] += 1
        agg[f"all {x['cond']}"][x["verdict"]] += 1
        agg[f"rules {x['rules_source']} {x['cond']}"][x["verdict"]] += 1
        agg[f"q1 {x['task']} {x['cond']}"][x["verdict"]] += 1 if stage == "q1" else 0
    out["Q4"][p] = {k: {**c, "compliance": round(c["kept"] / (c["kept"] + c["broken"]), 3) if c["kept"] + c["broken"] else None}
                    for k, c in sorted(agg.items()) if sum(c.values())}
if len(items_by_pass) == 2:
    a, b = items_by_pass["p1"], items_by_pass["p2"]
    common = [k for k in a if k in b]
    out["Q4"]["agreement"] = {"n": len(common), "same": sum(a[k] == b[k] for k in common),
                              "pairs": dict(Counter(f"{a[k]}|{b[k]}" for k in common if a[k] != b[k]))}
# ---------------------------------------------------------------- Q5
out["Q5"] = {}
for r in rows:
    if r["kind"] not in ("q5t", "q5n"):
        continue
    key = r["job"].split(":", 1)[1]
    d = out["Q5"].setdefault(key, [])
    e = {"tag": r["tag"], "skipped": r["load_attempts"] == 0, "sf_calls": r["sf_calls"], "turns": r["turns"],
         "cost": round(r["cost_usd"], 3), "wall": r["wall_s"], "loaded": [short(i) for i in r["loaded"]]}
    if r["kind"] == "q5n":
        meta = json.loads((PRIV / "runs" / f"{r['job'].replace(':', '-')}-{r['tag']}.meta.json").read_text())
        name = meta["named"]["named_skill"]
        e.update({"named": name, "pinned_named": [i for i in r["pinned_ids"] if short(i).split("@")[0] == name],
                  "loaded_named": [i for i in r["loaded"] if short(i).split("@")[0] == name], "check": r["check_pass"]})
    d.append(e)
# ---------------------------------------------------------------- Q6
q6a = {}
for task in sorted({t for t, _ in q1}):
    on, off = q1[(task, "on")], q1[(task, "off")]
    q6a[task] = {c: {"wall_med": med([r["wall_s"] for r in x]), "turns_med": med([r["turns"] for r in x]),
                     "input_tokens_med": med([r["input_tokens"] for r in x]), "cost_med": round(med([r["cost_usd"] for r in x]), 3),
                     "first_sf_turn": [r["first_sf_turn"] for r in x]} for c, x in (("on", on), ("off", off))}
vis = [r for r in rows if r["mcp"] == "on" and r["loaded"]]
q6b = {"requests_with_loads": len(vis), "reply_names_loaded": sum(bool(r["reply_mentions_loaded"]) for r in vis),
       "reply_word_skill": sum(r["reply_word_skill"] > 0 for r in vis),
       "by_stage": {s: {"n": sum(r["kind"].startswith(s) for r in vis),
                        "names_loaded": sum(bool(r["reply_mentions_loaded"]) for r in vis if r["kind"].startswith(s)),
                        "word_skill": sum(r["reply_word_skill"] > 0 for r in vis if r["kind"].startswith(s))} for s in ("q1", "q2", "q5")}}
q6c = {}
for r in rows:
    if r["kind"] != "q6":
        continue
    ref = q1.get((r["task"], "on"), [])
    q6c.setdefault(r["task"], []).append({
        "tag": r["tag"], "subtype": r["subtype"], "timed_out": r["timed_out"], "check": r["check_pass"], "turns": r["turns"],
        "wall": r["wall_s"], "cost": round(r["cost_usd"], 3), "load_attempts": r["load_attempts"], "load_errors": len(r["load_errors"]),
        "error_sample": r["load_errors"][:1], "q1_on_turns_med": med([x["turns"] for x in ref]), "q1_on_wall_med": med([x["wall_s"] for x in ref])})
out["Q6"] = {"a_time_turns": q6a, "b_visibility": q6b, "c_blocked": q6c}
# ---------------------------------------------------------------- usage
out["usage_api_equivalent"] = {"main_requests": round(sum(r["cost_usd"] or 0 for r in rows), 2),
                               "by_stage": {k: round(sum(r["cost_usd"] or 0 for r in rows if r["kind"].startswith(k)), 2)
                                            for k in ("q1", "q2", "q5", "q6")}}
(PRIV / "metrics-q.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=dict))
print(json.dumps({k: (v if k in ("Q1_agreement_p1_p2", "usage_api_equivalent") else "…") for k, v in out.items()}, ensure_ascii=False))
