"""Condition B input: for each stage-1 task with expert_skills, resolve the ids as pinned and
write exactly what load_skills returns (precedence header + bodies) to expert-content/<id>.md (+ .json)."""
import json
import sys
from pathlib import Path

import yaml
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

ROOT = Path(__file__).resolve().parent.parent
tasks = yaml.safe_load((ROOT / "tasks-stage1.yaml").read_text())["tasks"]
s = Session(Index.load(DEFAULT_INDEX_DIR))
out = ROOT / "expert-content"
for t in tasks:
    ids = t.get("expert_skills") or []
    if not ids:
        continue
    r = s.resolve_set([], ids)
    loaded = s.load_skills(r["set_id"])
    (out / f"{t['id']}.md").write_text(loaded["content"])
    (out / f"{t['id']}.json").write_text(json.dumps({"pinned": ids, "resolve": r, "skills": loaded["skills"], "errors": loaded["errors"]}, indent=1))
    print(t["id"], [x["id"] for x in loaded["skills"]], sum(x["token_estimate"] for x in loaded["skills"]), "errors", loaded["errors"], "excluded", r["excluded"], "warnings", len(r["warnings"]))
