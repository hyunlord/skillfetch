#!/usr/bin/env python3
"""Stage 12 O prompts (stage12/DESIGN.md §3): for each task, resolve_and_load(<the task's required Northwind ids>) on
index-nw with the experiment's server build, and write its `content` (the exact text load_skills returns; same bytes R
gets when it loads these skills) to <task>.md. max_tokens is raised so no required skill is dropped; any exclusion,
warning or error is recorded in o-build.json and stops the build. The body cache is a private folder here, not
~/.skillfetch/cache. usage: uvx --from ~/skillfetch-e2e-wt/s26-server/c55d561 python make_o.py"""
import hashlib
import json
from pathlib import Path

from skillfetch.index.fetch import BodyCache
from skillfetch.index.loader import Index
from skillfetch.mcp.session import Session

HERE = Path(__file__).resolve().parent
PRIV = HERE.parent
idx = Index.load(PRIV / "index-nw")
s = Session(idx, bodies=BodyCache(root=HERE / ".body-cache"))
full = {i.split("@")[0]: i for i in idx.records if i.startswith("northwind/")}
log, bad = {}, []
for line in (PRIV / "tasks.jsonl").open():
    t = json.loads(line)
    ids = [full[f"northwind/{n}"] for n in t["required_skills"]]
    r = s.resolve_and_load(ids, None, max_tokens=10**6)
    inc = [x if isinstance(x, str) else x.get("id") for x in r.get("included", [])]
    log[t["id"]] = {"asked": ids, "included": inc, "excluded": r.get("excluded"), "warnings": r.get("warnings"),
                    "notes": r.get("notes"), "errors": r.get("errors"), "chars": len(r.get("content") or ""),
                    "token_estimate": len(r.get("content") or "") // 4}
    if r.get("excluded") or r.get("errors") or set(inc) != set(ids):
        bad.append(t["id"])
    (HERE / f"{t['id']}.md").write_text(r["content"])
    log[t["id"]]["sha256"] = hashlib.sha256(r["content"].encode()).hexdigest()
(HERE / "o-build.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
for k, v in log.items():
    print(k, len(v["asked"]), "inc", len(v["included"]), "tok", v["token_estimate"], "warn", len(v["warnings"] or []), v["sha256"][:12])
assert not bad, f"exclusions/errors: {bad}"
