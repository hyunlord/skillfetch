#!/usr/bin/env python3
"""Step 5 metrics: what the 40 real sessions loaded vs the offline selection (selection.jsonl) for the same tasks.
Writes e2e.jsonl (per session) and e2e-summary.json.
  loaded   ids returned in load_skills `skills` (index ids only; the empty repos have no local skills)
  agreement: identical set; Jaccard; both none / both some; same 'hit' (loaded set ∩ oracle relevant ≠ ∅);
             same failure class (the e2e class uses the session's own search results for select_fail)"""
import json
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
S3 = E2E / "stage3"
sys.path.insert(0, str(E2E / "scripts"))
import extract as ex  # noqa: E402


def jac(a, b):
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def main():
    stub = "--stub" in sys.argv  # run 2: stub repos (runs-stub/), else run 1: empty repos (runs/)
    suffix = "-stub" if stub else ""
    ids = json.loads((S3 / "e2e-sample.json").read_text())
    tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
    orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
    off = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "selection-eval.jsonl").open()}
    offq = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "selection.jsonl").open()}
    ex.RUNS = S3 / ("runs-stub" if stub else "runs")
    rows = []
    for tid in ids:
        t = tasks[tid]
        r = ex.extract({"id": tid, "repo": "s3", "kind": t["task_type"], "lang": "-", "prompt": t["text"]})
        S = {i for i in r["loaded_ids"] if i and not str(i).startswith("path:")}
        R = set(orc[tid]["relevant"])
        returned = set()
        for c in r["search_calls"]:
            try:
                returned |= {x["id"] for x in json.loads(c["result"])["results"]}
            except Exception:  # noqa: BLE001
                pass
        if not R:
            cls = "over_load" if S else "ok"
        elif S & R:
            cls = "ok"
        elif R & returned:
            cls = "select_fail"
        else:
            cls = "not_in_results"  # restate_fail vs search_fail needs the offline Q1/Q3 runs; kept apart
        O = set(off[tid]["selected"])
        rk2 = set(json.loads((S3 / "rankings.json").read_text())[tid]["bm25_q2"])
        top50_jaccard = round(len(returned & rk2) / len(returned | rk2), 3) if returned else None
        first_tool = None
        for line in (ex.RUNS / f"{tid}.jsonl").open():
            e = json.loads(line)
            if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
                tu = [c for c in e["message"]["content"] if c["type"] == "tool_use"]
                if tu:
                    first_tool = tu[0]["name"] + (f"({tu[0]['input'].get('skill')})" if tu[0]["name"] == "Skill" else "")
                    break
        fired = any((c["input"] or {}).get("skill") == "skillfetch-router" for c in r["skill_tool_calls"]) or r["router_skill_reads"] > 0
        rows.append({"id": tid, "offline_class": off[tid]["class"], "e2e_class": cls, "router_fired": fired, "chain": r["chain"],
                     "e2e_queries": [(c["input"] or {}).get("query") for c in r["search_calls"]],
                     "offline_query": offq[tid]["query"], "e2e_loaded": sorted(S), "offline_selected": sorted(O),
                     "resolve_excluded": [e for c in r["resolve_calls"] for e in (json.loads(c["result"] or "{}").get("excluded") or [])] if r["resolve_calls"] else [],
                     "load_errors": r["load_errors"], "identical": S == O, "jaccard": round(jac(S, O), 3),
                     "none_agree": (not S) == (not O), "hit_agree": bool(S & R) == bool(O & R), "class_agree": cls == off[tid]["class"] or (cls == "not_in_results" and off[tid]["class"] in ("restate_fail", "search_fail")),
                     "num_turns": r["num_turns"], "result_subtype": r["result_subtype"],
                     "results_vs_offline_q2_top50_jaccard": top50_jaccard, "first_tool": first_tool})
    (S3 / f"e2e{suffix}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    n = len(rows)

    def rate(k, sel=rows):
        return f"{sum(1 for r in sel if r[k])}/{len(sel)}"
    summary = {"sessions": n, "router_fired": rate("router_fired"), "searched": f"{sum(1 for r in rows if r['e2e_queries'])}/{n}",
               "loaded_any": f"{sum(1 for r in rows if r['e2e_loaded'])}/{n}", "identical_set": rate("identical"),
               "mean_jaccard": round(sum(r["jaccard"] for r in rows) / n, 3), "none_agree": rate("none_agree"),
               "hit_agree": rate("hit_agree"), "class_agree": rate("class_agree"),
               "by_offline_class": {c: {"n": sum(1 for r in rows if r["offline_class"] == c),
                                        "identical": sum(1 for r in rows if r["offline_class"] == c and r["identical"]),
                                        "class_agree": sum(1 for r in rows if r["offline_class"] == c and r["class_agree"]),
                                        "mean_jaccard": round(sum(r["jaccard"] for r in rows if r["offline_class"] == c) / max(1, sum(1 for r in rows if r["offline_class"] == c)), 3)}
                                    for c in ("over_load", "select_fail", "restate_fail", "search_fail", "ok")}}
    fired = [r for r in rows if r["e2e_queries"]]
    summary["searched_only"] = {"sessions": len(fired), "identical_set": rate("identical", fired),
                                "mean_jaccard": round(sum(r["jaccard"] for r in fired) / max(1, len(fired)), 3),
                                "none_agree": rate("none_agree", fired), "hit_agree": rate("hit_agree", fired),
                                "class_agree": rate("class_agree", fired)}
    from collections import Counter
    summary["searched_only"]["mean_top50_jaccard_vs_offline_q2"] = round(
        sum(r["results_vs_offline_q2_top50_jaccard"] for r in fired) / max(1, len(fired)), 3)
    summary["first_tool_when_not_searched"] = dict(Counter(r["first_tool"] for r in rows if not r["e2e_queries"]))
    (S3 / f"e2e{suffix}-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
