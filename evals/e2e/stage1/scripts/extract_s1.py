#!/usr/bin/env python3
"""stage1/runs/<cond>/<id>-r<rep>.* -> stage1/runs/_extract.json (session facts + check + skillfetch timing)."""
import json
import sys
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S1 = E2E / "stage1"
sys.path.insert(0, str(E2E / "scripts"))
import extract as ex  # noqa: E402
import extract05 as ex05  # noqa: E402


def main():
    tasks = {t["id"]: t for t in yaml.safe_load((S1 / "tasks-stage1.yaml").read_text())["tasks"]}
    rows = []
    for cond in ("A", "B", "C"):
        runs = S1 / "runs" / cond
        if not runs.exists():
            continue
        ex.RUNS = runs
        for meta_path in sorted(runs.glob("*.meta.json")):
            meta = json.loads(meta_path.read_text())
            name = meta_path.name[: -len(".meta.json")]
            t = dict(tasks[meta["task"]["id"]], id=name)
            r = ex.extract(t)
            r.update(task_id=meta["task"]["id"], cond=cond, rep=meta["rep"], name=name,
                     check=meta["check"], check_original=meta.get("check_original"), diff=meta["diff"], blind_code=meta.get("blind_code"),
                     index_built_at=meta.get("index_built_at"), base_commit=meta["base_commit"],
                     wall_s=meta["session"]["wall_s"], exit_code=meta["session"]["exit_code"],
                     timed_out=meta["session"]["timed_out"])
            r["timing"] = ex05.timing(runs, name, meta["session"]["spawn_epoch_ms"])
            if cond == "B":
                bj = json.loads((S1 / "expert-content" / f"{r['task_id']}.json").read_text())
                r["expert_ids"] = [s["id"] for s in bj["skills"]]
                r["expert_tokens"] = sum(s["token_estimate"] for s in bj["skills"])
            r.pop("meta", None)
            rows.append(r)
    (S1 / "runs" / "_extract.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for r in rows:
        print(r["cond"], r["name"], r["result_subtype"], r["num_turns"], "check", r["check"].get("pass"), r["chain"], r["loaded_ids"])


if __name__ == "__main__":
    main()
