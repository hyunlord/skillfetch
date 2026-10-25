#!/usr/bin/env python3
"""Stage 8 §2 metrics on oracle v5-ss only: hit@1/5/10 (SF R-c ranking, SS-q1, SS-q3, SS-kw), final load (SF S-b'
3 runs vs SS-load-kw vs SS-load-full), empty results per condition, out-of-index relevant skills (and the 56 gap
tasks: v3 oracle relevant 0, not expect_none, not trivial), latency per call kind. Writes metrics-8.json."""
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ss_parse import fetch_skill_md, id_repo, index, parse_load, parse_search, sha  # noqa: E402

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
recs, by_rp, by_name = index()
tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S8 / "oracle-v5-ss.jsonl").open()}
v3 = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "followup" / "oracle-v3.jsonl").open()}
rc = json.loads((E2E / "stage6" / "gen" / "results-rc.json").read_text())
sel = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()}
       for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
ss_map = json.loads((S8 / "ss-map.json").read_text())
cands = json.loads((S8 / "cands.json").read_text())
main = {}
for l in (S8 / "raw" / "main.jsonl").open():
    r = json.loads(l)
    main[(r["task"], r["kind"])] = r
grade = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in orc.items()}
R = {t: set(o["relevant"]) for t, o in orc.items()}
REL = sorted(t for t in tasks if not tasks[t]["expect_none"] and R[t])
IRR = sorted(t for t in tasks if tasks[t]["expect_none"] or not R[t])
GAP = sorted(t for t in tasks if not v3[t]["relevant"] and not tasks[t]["expect_none"] and tasks[t]["task_type"] != "trivial")


def key(sid):
    m = ss_map.get(sid) or {}
    return m.get("merged_into") or "ss:" + sid.lower()


def loaded_key(tid, kind):
    ld = parse_load(main[(tid, kind)]["text"])
    if not ld:
        return None
    for k, e in cands[tid].items():
        if kind in e["sources"]:
            return k
    raise KeyError((tid, kind))


rank = {"SF": {t: [x["id"] for x in rc[t]["results"]] for t in tasks}}
for k in ("SS-q1", "SS-q3", "SS-kw"):
    rank[k] = {t: [key(x["id"]) for x in parse_search(main[(t, k)]["text"]) if x["id"]] for t in tasks}
out = {"denominators": {"relevant_tasks": len(REL), "irrelevant_tasks": len(IRR),
                        "irrelevant_expect_none": sum(tasks[t]["expect_none"] for t in IRR), "gap56": len(GAP)}}
out["hit"] = {c: {f"@{k}": round(sum(bool(set(rank[c][t][:k]) & R[t]) for t in REL) / len(REL), 3) for k in (1, 5, 10)}
              for c in rank}
out["hit_counts"] = {c: {f"@{k}": sum(bool(set(rank[c][t][:k]) & R[t]) for t in REL) for k in (1, 5, 10)} for c in rank}
out["results_len_median"] = {c: st.median(len(rank[c][t]) for t in tasks) for c in rank}
# empty results / errors per condition (all 380)
emp = {"SF R-c top-50 empty": sum(not rc[t]["results"] for t in tasks)}
for i, s in enumerate(sel):
    emp[f"SF S-b' r{i + 1} none"] = sum(not s.get(t) for t in tasks)
for k in ("SS-q1", "SS-q3", "SS-kw"):
    emp[k] = sum(not parse_search(main[(t, k)]["text"]) for t in tasks)
for k in ("SS-load-kw", "SS-load-full"):
    emp[k] = sum(parse_load(main[(t, k)]["text"]) is None for t in tasks)
out["empty"] = emp
out["errors"] = dict(Counter(k for (t, k), r in main.items() if r["error"] or r["is_error"]))
for k in ("SS-q1", "SS-q3", "SS-kw"):
    out.setdefault("empty_by_group", {})[k] = {"relevant": sum(not rank[k][t] for t in REL), "irrelevant": sum(not rank[k][t] for t in IRR)}
for k in ("SS-load-kw", "SS-load-full"):
    out["empty_by_group"][k] = {"relevant": sum(parse_load(main[(t, k)]["text"]) is None for t in REL),
                                "irrelevant": sum(parse_load(main[(t, k)]["text"]) is None for t in IRR)}


# final load
def load_metrics(L):
    rel_hit = sum(bool(L[t] & R[t]) for t in REL)
    rel_loaded = sum(bool(L[t]) for t in REL)
    return {"rel_hit_over_relevant": round(rel_hit / len(REL), 3), "rel_hit_n": rel_hit,
            "rel_hit_over_loaded": round(rel_hit / rel_loaded, 3) if rel_loaded else None, "relevant_loaded_n": rel_loaded,
            "irrelevant_loaded_rate": round(sum(bool(L[t]) for t in IRR) / len(IRR), 3), "irrelevant_loaded_n": sum(bool(L[t]) for t in IRR),
            "expect_none_loaded_n": sum(bool(L[t]) for t in IRR if tasks[t]["expect_none"]),
            "mean_loaded_relevant_tasks": round(sum(len(L[t]) for t in REL) / len(REL), 3)}


fl = {}
for i, s in enumerate(sel):
    fl[f"SF S-b' r{i + 1}"] = load_metrics({t: set(s.get(t, [])) for t in tasks})
fl["SF S-b' mean"] = {m: round(st.mean(fl[f"SF S-b' r{i}"][m] for i in (1, 2, 3)), 3) for m in fl["SF S-b' r1"] if fl["SF S-b' r1"][m] is not None}
for k in ("SS-load-kw", "SS-load-full"):
    L = {t: ({loaded_key(t, k)} if loaded_key(t, k) else set()) for t in tasks}
    fl[k] = load_metrics(L)
    fl[k]["loaded_grade_dist"] = dict(sorted(Counter(grade[t][next(iter(L[t]))] for t in tasks if L[t]).items()))
out["final_load"] = fl

# out-of-index relevant skills found by SS
ss_rel = {}
for t in tasks:
    for k in R[t]:
        if k.startswith("ss:"):
            ss_rel.setdefault(k, set()).add(t)


def classify(k):
    e = next(cands[t][k] for t in ss_rel[k])
    sid = e["ss_ids"][0]
    why = (ss_map.get(sid) or {}).get("why")
    if why == "repo_name_match_hash_differs":
        return "same_repo_name_body_differs"
    if why == "repo_name_match_body_unavailable":
        return "same_repo_name_body_unavailable"
    same = by_name.get(e["title"].lower(), [])
    if not same:
        return "out_of_index"
    repo, slug = id_repo(sid)
    body = fetch_skill_md(repo, slug)
    if body is None:
        return "same_name_body_unavailable"
    return "same_name_same_body" if any((recs[s].get("files") or {}).get("SKILL.md") == sha(body) for s in same) else "out_of_index"


cls = {k: classify(k) for k in ss_rel}
ooi = [k for k, c in cls.items() if c == "out_of_index"]
out["ss_relevant"] = {"unique_ss_keys_grade_ge2": len(ss_rel), "classification": dict(Counter(cls.values())),
                      "out_of_index_unique": len(ooi), "out_of_index_task_pairs": sum(len(ss_rel[k]) for k in ooi),
                      "relevant_tasks_with_out_of_index": sum(any(t in ss_rel[k] for k in ooi) for t in REL),
                      "relevant_tasks_relevant_only_from_ss": sum(all(x.startswith("ss:") for x in R[t]) for t in REL),
                      "gap56_with_out_of_index": sum(any(t in ss_rel[k] for k in ooi) for t in GAP),
                      "gap56_out_of_index_unique": len({k for k in ooi if ss_rel[k] & set(GAP)}),
                      "gap56_with_any_relevant_v5ss": sum(bool(R[t]) for t in GAP),
                      "gap56_with_index_relevant_v5ss": sum(any(not x.startswith("ss:") for x in R[t]) for t in GAP),
                      "gap56_by_type": dict(Counter(tasks[t]["task_type"] for t in GAP if any(t in ss_rel[k] for k in ooi)))}
out["ss_relevant_examples"] = sorted(((len(ss_rel[k]), k, next(cands[t][k]["title"] for t in ss_rel[k])) for k in ooi), reverse=True)[:15]
# latency
lat = {}
for k in ("SS-q1", "SS-q3", "SS-kw", "SS-load-kw", "SS-load-full"):
    w = sorted(r["wall_s"] for (t, kk), r in main.items() if kk == k)
    lat[k] = {"n": len(w), "median_s": round(st.median(w), 3), "p95_s": round(w[int(0.95 * (len(w) - 1))], 3), "max_s": max(w)}
out["latency"] = lat
(S8 / "metrics-8.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
