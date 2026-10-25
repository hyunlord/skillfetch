"""Condition B input for stage 2: load_skills output of the pinned B skill -> expert-content/<task>.md (+ .json)."""
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S2 = Path(__file__).resolve().parents[1]
B = {"s2-tests": "uasl/python-testing-patterns@e62d0f1ca316", "s2-api": "uasl/fastapi-templates@effcd0de0b4c",
     "s2-docs": "uasl/quill@336ba74b0e79", "s2-data": "uasl/data-analyst-engine@79799e01e2dd"}
s = Session(Index.load(DEFAULT_INDEX_DIR))
for task, sid in B.items():
    r = s.resolve_set([], [sid])
    out = s.load_skills(r["set_id"])
    (S2 / "expert-content" / f"{task}.md").write_text(out["content"])
    (S2 / "expert-content" / f"{task}.json").write_text(json.dumps({"pinned": [sid], "resolve": r, "skills": out["skills"], "errors": out["errors"]}, indent=1))
    print(task, [x["id"] for x in out["skills"]], [x["token_estimate"] for x in out["skills"]], out["errors"], r["excluded"])
