#!/usr/bin/env python3
"""stage2/runs -> stage2/runs/_extract.json: per session turns, tokens, cost, check metrics; for C2 also router
fired, search queries, B skill's rank in the returned results, whether it was picked / excluded / loaded."""
import json
import sys
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S2 = E2E / "stage2"
sys.path.insert(0, str(E2E / "scripts"))
import extract as ex  # noqa: E402

TASKS = {t["id"]: t for t in yaml.safe_load((S2 / "tasks-stage2.yaml").read_text())["tasks"]}
B_SKILL = {k: json.loads((S2 / "expert-content" / f"{k}.json").read_text())["pinned"][0] for k in TASKS}


def jload(text):
    try:
        return json.loads(text or "")
    except (json.JSONDecodeError, TypeError):
        return None


def main():
    rows = []
    for cond in ("A", "B", "C2"):
        runs = S2 / "runs" / cond
        if not runs.is_dir():
            continue
        ex.RUNS = runs
        for mp in sorted(runs.glob("*.meta.json")):
            meta = json.loads(mp.read_text())
            name = mp.name[: -len(".meta.json")]
            t = TASKS[meta["task"]["id"]]
            r = ex.extract({"id": name, "repo": t["repo"], "kind": t["domain"], "lang": "ko", "prompt": t["prompt"]})
            r.pop("meta", None)
            r.update(task_id=t["id"], cond=cond, rep=meta["rep"], name=name, check=meta["check"], diff=meta["diff"],
                     wall_s=meta["session"]["wall_s"], exit_code=meta["session"]["exit_code"],
                     timed_out=meta["session"]["timed_out"], index_built_at=meta.get("index_built_at"),
                     base_commit=meta["base_commit"])
            res = [json.loads(l) for l in (runs / f"{name}.jsonl").read_text().splitlines() if '"type":"result"' in l]
            if len(res) > 1:  # follow-up turns after background agents: sum all segments
                u = [x.get("usage") or {} for x in res]
                r.update(num_turns=sum(x.get("num_turns") or 0 for x in res),
                         duration_ms=sum(x.get("duration_ms") or 0 for x in res),
                         output_tokens=sum(x.get("output_tokens") or 0 for x in u),
                         input_tokens_total=sum((x.get("input_tokens") or 0) + (x.get("cache_creation_input_tokens") or 0)
                                                + (x.get("cache_read_input_tokens") or 0) for x in u),
                         total_cost_usd=sum(x.get("total_cost_usd") or 0 for x in res),
                         result_subtype=res[0].get("subtype") + f" (+{len(res) - 1} follow-up)", final_text=res[-1].get("result"))
            r["result_events"] = len(res)
            b = B_SKILL[t["id"]]
            r["b_skill"] = b
            if cond == "C2":
                r["router_fired"] = any((c["input"] or {}).get("skill") == "skillfetch-router" for c in r["skill_tool_calls"]) or r["router_skill_reads"] > 0
                r["searches"] = []
                for c in r["search_calls"]:
                    j = jload(c["result"])
                    ids = [x["id"] for x in (j or {}).get("results", [])] if isinstance(j, dict) else []
                    r["searches"].append({"query": (c["input"] or {}).get("query"), "k": (c["input"] or {}).get("k"),
                                          "returned": len(ids), "b_rank": ids.index(b) + 1 if b in ids else None})
                r["b_in_top50"] = any(s["b_rank"] for s in r["searches"])
                r["b_rank"] = min((s["b_rank"] for s in r["searches"] if s["b_rank"]), default=None)
                picked, excluded = [], []
                for c in r["resolve_calls"]:
                    inp = c["input"] or {}
                    picked += list(inp.get("auto_ids") or []) + list(inp.get("pinned_ids") or [])
                    j = jload(c["result"])
                    if isinstance(j, dict):
                        excluded += [{"id": e.get("id"), "reason": e.get("reason"), "conflicts_with": e.get("conflicts_with")} for e in j.get("excluded") or []]
                r["picked_ids"] = picked
                r["b_picked"] = b in picked
                r["resolve_excluded"] = excluded
                r["b_excluded"] = any(e["id"] == b for e in excluded)
                r["b_loaded"] = b in r["loaded_ids"]
                r["b_load_error"] = [e for e in r["load_errors"] if isinstance(e, dict) and e.get("id") == b]
            rows.append(r)
    (S2 / "runs" / "_extract.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(len(rows), "sessions")


if __name__ == "__main__":
    main()
