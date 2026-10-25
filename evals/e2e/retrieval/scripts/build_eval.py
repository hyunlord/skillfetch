#!/usr/bin/env python3
"""retrieval-eval.jsonl: every search_skills call made by condition C in stage 1 (20 tasks) and 1b (5 tasks),
with the task's expert skills as gold. Tasks without an expert skill go to retrieval-nogold.jsonl (used only for
the score threshold). Recorded result ids are kept so the re-run can be checked against them."""
import json
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
OUT = E2E / "retrieval"
SOURCES = [("stage1", E2E / "stage1/tasks-stage1.yaml", E2E / "stage1/runs/_extract.json"),
           ("stage1b", E2E / "stage1b/tasks-1b.yaml", E2E / "stage1b/runs/_extract.json")]


def main():
    rows, nogold, runs_without = [], [], []
    for stage, tasks_path, extract_path in SOURCES:
        tasks = {t["id"]: t for t in yaml.safe_load(tasks_path.read_text())["tasks"]}
        for r in json.loads(extract_path.read_text()):
            if r["cond"] != "C":
                continue
            task = tasks[r["task_id"]]
            gold = list(task.get("expert_skills") or [])
            if not r["search_calls"]:
                runs_without.append(r["id"])
            for i, call in enumerate(r["search_calls"]):
                inp = call.get("input") or {}
                try:
                    recorded = [x["id"] for x in json.loads(call["result"])["results"]]
                except Exception:
                    recorded = None
                row = {"qid": f"{r['id']}#{i + 1}", "stage": stage, "task_id": r["task_id"], "run": r["id"],
                       "repo": r["repo"], "prompt": r["prompt"], "query": inp.get("query", ""),
                       "profile": inp.get("profile"), "k_called": inp.get("k", 10), "gold": gold,
                       "recorded_ids": recorded}
                (rows if gold else nogold).append(row)
    (OUT / "retrieval-eval.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
    (OUT / "retrieval-nogold.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in nogold))
    print(f"gold queries {len(rows)} ({len({x['run'] for x in rows})} runs), no-gold queries {len(nogold)}; "
          f"C runs without search_skills: {len(runs_without)} {runs_without}")


if __name__ == "__main__":
    main()
