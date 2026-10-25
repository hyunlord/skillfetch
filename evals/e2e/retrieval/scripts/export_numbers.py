#!/usr/bin/env python3
"""data/e2e/router-e2e.json for skillfetch's numbers.md §11: stage 1 and 1b aggregates recomputed from the
session extracts; selection-match counts and blind aggregates copied from the hand-judged report files named
in `sources` (stage1/report-stage1-extra.md §1, stage1/blind-ranking-results.md, stage1b/blind-ranking-results.md)."""
import json
import statistics
import sys
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]


def passed(check):
    return (check.get("pass") if isinstance(check, dict) else check) is True


def agg(rows):
    return {"sessions": len(rows), "check_pass": sum(1 for r in rows if passed(r["check"])),
            "median_turns": statistics.median(r["num_turns"] for r in rows),
            "median_input_tokens": int(statistics.median(r["input_tokens_total"] for r in rows)),
            "searched": sum(1 for r in rows if r["search_calls"]),
            "loaded": sum(1 for r in rows if r["load_calls"])}


def stage(extract, tasks_yaml):
    rows = [r for r in json.loads(Path(extract).read_text()) if r["cond"] in ("A", "B", "C")]  # C2: session_costs
    tasks = {t["id"]: t for t in yaml.safe_load(Path(tasks_yaml).read_text())["tasks"]}
    expert = {t for t, v in tasks.items() if v.get("expert_skills")}
    out = {"tasks": len(tasks), "expert_tasks": len(expert), "sessions": len(rows), "by_condition": {}}
    for scope, keep in (("expert_tasks", lambda r: r["task_id"] in expert), ("all_tasks", lambda r: True)):
        for cond in "ABC":
            sel = [r for r in rows if r["cond"] == cond and keep(r)]
            if sel:
                out["by_condition"].setdefault(scope, {})[cond] = agg(sel)
    c = [r for r in rows if r["cond"] == "C" and r["task_id"] in expert]
    out["c_loaded_an_expert_id"] = sum(1 for r in c if set(map(str, r["loaded_ids"])) & set(tasks[r["task_id"]]["expert_skills"]))
    out["c_runs_on_expert_tasks"] = len(c)
    return out


def stage4_results(pattern):
    """The result event (total_cost_usd) of each stage-4 session log matching pattern."""
    out = []
    for f in sorted((E2E / "stage4/runs").glob(f"E*/{pattern}")):
        res = [json.loads(l) for l in f.read_text().splitlines() if '"type":"result"' in l.replace(" ", "")]
        out.append({"total_cost_usd": res[-1].get("total_cost_usd") if res else 0})
    return out


def result_costs(folder):
    """The result event (total_cost_usd) of every session log t*.jsonl in folder."""
    out = []
    for f in sorted(folder.glob("t*.jsonl")):
        res = [json.loads(l) for l in f.read_text().splitlines() if '"type":"result"' in l.replace(" ", "")]
        out.append({"total_cost_usd": res[-1].get("total_cost_usd") if res else None})
    return out


STAGE3_STEPS = (  # gen/raw/<name>.json prefix -> step
    ("gen-", "generation"), ("rewrite-", "generation"), ("oracle2a-", "labelling"), ("grade2b-", "labelling"),
    ("grade2c-", "labelling"), ("grade3x-", "3-0 pool correction"), ("q2-", "queries"), ("q3", "queries"),
    ("select1-", "selection"), ("select-", "selection"), ("dirclass", "direction classes"))


ROUTER_RULE_RAW = ("rc-R", "grade-rc")  # router step-1 comparison (after the post), also in stage3/gen/raw


def stage3_prep():
    """Stage-3 isolated batch calls by step (cost_usd per cached call in stage3/gen/raw)."""
    steps = {}
    for f in sorted((E2E / "stage3/gen/raw").glob("*.json")):
        if f.name.startswith(ROUTER_RULE_RAW):
            continue
        step = next((s for pre, s in STAGE3_STEPS if f.name.startswith(pre)), "other")
        c = json.loads(f.read_text()).get("cost_usd")
        x = steps.setdefault(step, {"calls": 0, "cost_usd": 0.0, "no_cost": 0})
        x["calls"] += 1
        x["cost_usd"] += c or 0
        x["no_cost"] += c is None
    return {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in steps.items()}


STAGE5_RAW = ("readapt", "rfix", "s5-")  # stage-5 calls cached in stage4/gen/raw
STAGE6_RAW = ("s6b-", "rs6b-")  # stage-6b calls cached in stage4/gen/raw (after the post)


def stage4_prep():
    """Stage-4 isolated batch calls (task rewrite, oracle 2a/2b/3-0, queries, selection, 4-0): cost_usd per call.
    The stage-5 calls cached in the same folder (STAGE5_RAW prefixes) are left out."""
    calls = [json.loads(f.read_text()) for f in (E2E / "stage4/gen/raw").glob("*.json")
             if not f.name.startswith(STAGE5_RAW + STAGE6_RAW)]
    return {"calls": len(calls), "cost_usd": round(sum(c.get("cost_usd") or 0 for c in calls), 2)}


def stage5_prep():
    """Stage-5 isolated batch calls cached in stage4/gen/raw, by step: task rewrite (readapt), oracle relabel of the
    rewritten tasks (rfix, rfix3), 4-0 grading (s5-)."""
    steps = {}
    for f in sorted((E2E / "stage4/gen/raw").glob("*.json")):
        step = next((s for pre, s in (("readapt", "task rewrite"), ("rfix", "oracle relabel"),
                                      ("s5-", "4-0 grading")) if f.name.startswith(pre)), None)
        if step:
            x = steps.setdefault(step, {"calls": 0, "cost_usd": 0.0})
            x["calls"] += 1
            x["cost_usd"] += json.loads(f.read_text()).get("cost_usd") or 0
    return {k: {**v, "cost_usd": round(v["cost_usd"], 2)} for k, v in steps.items()}


def stage5_results(pattern, folder="stage5/runs"):
    """The result event (total_cost_usd) of each stage-5 session log matching pattern under folder/V*/."""
    out = []
    for f in sorted((E2E / folder).glob(f"V*/{pattern}")):
        res = [json.loads(l) for l in f.read_text().splitlines() if '"type":"result"' in l.replace(" ", "")]
        out.append({"total_cost_usd": res[-1].get("total_cost_usd") if res else 0})
    return out


def session_costs():
    """Sessions and Claude Code's reported total_cost_usd per e2e stage, from the run extracts and the
    smoke logs (API-price equivalent, billed to the Claude Code plan)."""
    def cost(rows):
        return {"sessions": len(rows), "cost_usd": round(sum(r["total_cost_usd"] or 0 for r in rows), 2)}
    load = lambda f: json.loads((E2E / f).read_text())
    s1b = load("stage1b/runs/_extract.json")
    smoke = [json.loads(l) for f in sorted((E2E / "smoke").glob("smoke*.jsonl"))
             for l in f.read_text().splitlines() if l.startswith("{") and '"total_cost_usd"' in l]
    return {"stage0": cost(load("runs/_extract.json")), "stage0.5": cost(load("runs-0.5/_extract.json")),
            "stage1": cost(load("stage1/runs/_extract.json")),
            "stage1b": cost([r for r in s1b if r["cond"] != "C2"]),
            "c2": cost([r for r in s1b if r["cond"] == "C2"]),
            "stage2": cost(load("stage2/runs/_extract.json")),
            "stage3_run1": cost(result_costs(E2E / "stage3/runs")),
            "stage3_run2": cost(result_costs(E2E / "stage3/runs-stub")),
            "stage4_pilot": cost(stage4_results("*-p0.jsonl")),
            "stage4": cost([{"total_cost_usd": r["cost_usd"]} for r in
                            (json.loads(l) for l in (E2E / "stage4/sessions.jsonl").read_text().splitlines())]),
            "stage5": cost([{"total_cost_usd": r["cost_usd"]} for r in
                            (json.loads(l) for l in (E2E / "stage5/sessions.jsonl").read_text().splitlines())]),
            "stage5_check": cost(stage5_results("*-chk.jsonl")),
            "stage5_trivial": cost(stage5_results("*-t[123].jsonl")),
            "stage5_discarded": cost(stage5_results("*.jsonl", "stage5/runs/_discarded-old-t026")),
            "smoke": cost(smoke)}


def stage2():
    """Stage 2 (domain generalisation): per domain and condition, from stage2/runs/_extract.json and the two judging
    passes; C2 search hits. The landing row is 1b's (rejudge, one pass)."""
    S2 = E2E / "stage2"
    if not (S2 / "judged-p2.json").exists():
        return None
    rows = json.loads((S2 / "runs/_extract.json").read_text())
    j = {}
    for n in (1, 2):
        for x in json.loads((S2 / f"judged-p{n}.json").read_text()):
            j.setdefault(x["name"] + x["cond"], {})[n] = x["총점 1-5"]
    out = {"tasks": {}, "consistency": json.loads((S2 / "judge-consistency.json").read_text())}
    for t in ("s2-tests", "s2-api", "s2-docs", "s2-data"):
        out["tasks"][t] = {}
        for c in ("A", "B", "C2"):
            rr = [r for r in rows if r["task_id"] == t and r["cond"] == c]
            p1 = [j[r["name"] + c][1] for r in rr]
            p2 = [j[r["name"] + c][2] for r in rr]
            a = {"sessions": len(rr), "score_p1": round(statistics.mean(p1), 2), "score_p2": round(statistics.mean(p2), 2),
                 "score": round(statistics.mean(p1 + p2), 2), "check_pass": sum(1 for r in rr if passed(r["check"])),
                 "median_turns": statistics.median(r["num_turns"] for r in rr),
                 "median_input_tokens": int(statistics.median(r["input_tokens_total"] for r in rr)),
                 "median_cost_usd": round(statistics.median(r["total_cost_usd"] or 0 for r in rr), 2)}
            m = [r["check"].get("metrics", {}) for r in rr]
            if t == "s2-tests":
                a["mean_branch_cov"] = round(statistics.mean(x.get("rules_branch_pct") or 0 for x in m), 1)
            if t == "s2-api":
                a["mean_contract_pass"] = round(statistics.mean(x.get("contract_pass") or 0 for x in m), 1)
            if c == "C2":
                a.update(b_skill=rr[0]["b_skill"], router_fired=sum(r["router_fired"] for r in rr),
                         b_in_top50=sum(r["b_in_top50"] for r in rr), b_picked=sum(r["b_picked"] for r in rr),
                         b_excluded=sum(r["b_excluded"] for r in rr), b_loaded=sum(r["b_loaded"] for r in rr),
                         b_ranks=[r["b_rank"] for r in rr])
            out["tasks"][t][c] = a
    return out


def embedding_eval():
    """retrieval/report-embedding.md: gold-rank top-k for BM25, embedding alone and BM25 + embedding RRF over the
    34 gold queries (computed from emb-ranks.jsonl), the pick rows copied from the report, model facts from
    emb-timing.json."""
    rows = [json.loads(l) for l in (E2E / "retrieval/emb-ranks.jsonl").read_text().splitlines()]
    def top(key, k):
        return sum(1 for r in rows if r[key] is not None and r[key] <= k)
    out = {"queries": len(rows)}
    for name, key in (("bm25", "bm25_best"), ("embedding", "emb_best"), ("rrf", "rrf_best")):
        out[name] = {f"top{k}": top(key, k) for k in (3, 10, 50)}
    out["picks_top3"] = {"bm25_top50": 18, "rrf_top50": 18}  # report-embedding.md, sub-agent picks
    timing = json.loads((E2E / "retrieval/emb-timing.json").read_text())
    out["model"] = {k: timing[k] for k in ("model", "params", "dim", "max_seq_length", "docs", "docs_truncated",
                                           "model_cache_bytes", "index_s", "model_load_s", "query_latency_ms")}
    return out


def main(dest):
    data = {
        "sources": ["e2e/stage1/runs/_extract.json", "e2e/stage1b/runs/_extract.json",
                    "e2e/stage1/report-stage1-extra.md §1", "e2e/stage1/blind-ranking-results.md",
                    "e2e/stage1b/blind-ranking-results.md", "e2e/retrieval/ (retrieval eval)"],
        "stage1": stage(E2E / "stage1/runs/_extract.json", E2E / "stage1/tasks-stage1.yaml"),
        "stage1b": stage(E2E / "stage1b/runs/_extract.json", E2E / "stage1b/tasks-1b.yaml"),
        # hand-judged, copied from the report files above
        "stage1_selection_match": {"same": 3, "equivalent": 15, "different": 4, "not_loaded": 8},
        "stage1_blind": {"screens_abc_usefulness": {"A": 4.00, "B": 4.25, "C": 4.00, "n": 4},
                         "screens_ac_usefulness": {"A": 3.50, "C": 3.83, "n": 6},
                         "docs_merge": {"A": 4.75, "B": 5.00, "C": 5.00, "n": 4}},
        "stage1b_blind": {"screens_usefulness": {"A": 3.50, "B": 5.00, "C": 3.75, "n": 4},
                          "screens_ai_look": {"A": 1.75, "B": 0.50, "C": 2.00, "n": 4},
                          "plans_norm_rank": {"A": 0.30, "B": 0.00, "C": 0.80, "n": 2},
                          "plan_followed": {"A": 5.0, "B": 5.0, "C": 3.0, "n": 2}},
    }
    rk = [json.loads(l) for l in (E2E / "retrieval/bm25-ranks.jsonl").read_text().splitlines()]
    g = [x for x in rk if x["has_gold"]]
    data["retrieval_bm25"] = {"queries": len(g), **{f"top{k}": sum(1 for x in g if x["best_rank"] and x["best_rank"] <= k)
                                                   for k in (3, 10, 50)}}
    data["session_costs"] = session_costs()
    data["stage4_prep"] = stage4_prep()
    data["stage3_prep"] = stage3_prep()
    data["stage5_prep"] = stage5_prep()
    data["embedding_eval"] = embedding_eval()
    # stage2/report-stage2.md §0 (repos)
    data["stage2_setup"] = {"tests_module_lines": 280, "orders_csv_rows": 375, "orders_planted_problems": 10,
                            "api_contract_calls": 27}
    # stage1b/report-1b-c2.md §1 (median turns, all 5 tasks) and §4 (rejudge/, sub-agent judges, A/B/C/C2 together)
    data["stage1b_rejudge"] = {"usable": {"A": 3.50, "B": 4.75, "C": 4.50, "C2": 4.75, "n": 4},
                               "ai_tells": {"A": 2.00, "B": 0.50, "C": 2.00, "C2": 0.50, "n": 4},
                               "plan_norm_rank": {"A": 0.36, "B": 0.00, "C": 0.79, "C2": 0.71, "n": 2},
                               "median_turns": {"A": 19.5, "B": 24, "C": 34, "C2": 26.5, "n": 10}}
    rk = {json.loads(l)["qid"]: json.loads(l) for l in (E2E / "retrieval/bm25-ranks.jsonl").read_text().splitlines()}
    data["landing_expert_ranks"] = {
        # C (k=10): its 4 landing queries re-ranked by the current BM25 (bm25-ranks.jsonl)
        "c_k": 10, "c_bm25": [rk[q]["best_rank"] for q in sorted(rk) if q.startswith(("s1b-fa-landing", "s1b-nx-landing"))],
        # C2 (k=50): rank in the results each session received (stage1b/report-1b-c2.md §2)
        "c2_k": 50, "c2_session": [47, 41, 16, 13]}
    s2 = stage2()
    if s2:
        data["stage2"] = s2
        data["stage2_landing_from_1b"] = {"usefulness": {"A": 3.50, "B": 4.75, "C2": 4.75, "n": 4},
                                          "c2_loaded_expert": 4, "c2_runs": 4, "c2_in_top50": 4, "c2_picked": 4}  # stage1b/report-1b-c2.md §2, §4
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(json.dumps(data, indent=1) + "\n")
    print(json.dumps(data, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
