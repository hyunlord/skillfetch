#!/usr/bin/env python3
"""Stage 12 offline search check (stage12/DESIGN.md §1.4; report only, nothing is changed from its result).
gen:  one isolated `claude -p` with the Stage 3 R-c step (stage3/gen/sys-rc-R-c.txt, unchanged) over the 10 task
      prompts (stage12-private/tasks.jsonl) -> queries.jsonl, gen-raw.json.
rank: under the experiment's server build, Session(index-nw).search_skills(queries=<first 4>) with k=50, the same call
      as the router's search step; for each task, the rank of each required Northwind skill -> ranks.json.
usage: search_check.py gen
       uvx --from ~/skillfetch-e2e-wt/s26-server/c55d561 python search_check.py rank"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIV = HERE.parent
E2E = PRIV.parent
TASKS = [json.loads(l) for l in (PRIV / "tasks.jsonl").open()]


def gen():
    out = HERE / "queries.jsonl"
    assert not out.exists(), "queries already generated (frozen)"
    sysf = E2E / "stage3" / "gen" / "sys-rc-R-c.txt"
    prompt = "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['prompt']}" for t in TASKS)
    iso = Path(tempfile.mkdtemp(prefix="s12sc-"))
    (iso / "mcp.json").write_text('{"mcpServers":{}}')
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "VIRTUAL_ENV", "UV") and not k.startswith("CLAUDE_CODE_")}
    cmd = ["claude", "-p", prompt, "--system-prompt-file", str(sysf), "--tools", "", "--strict-mcp-config",
           "--mcp-config", str(iso / "mcp.json"), "--setting-sources", "project", "--output-format", "json",
           "--no-session-persistence"]
    p = subprocess.run(cmd, cwd=iso, env=env, capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL)
    j = json.loads(p.stdout)
    (HERE / "gen-raw.json").write_text(json.dumps({"result": j.get("result"), "usage": j.get("usage"),
                                                   "cost_usd": j.get("total_cost_usd"), "is_error": j.get("is_error")},
                                                  ensure_ascii=False, indent=1))
    txt = j["result"]
    arr = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
    got = {x["id"]: x["queries"] for x in arr}
    assert set(got) == {t["id"] for t in TASKS}, sorted(got)
    out.write_text("".join(json.dumps({"id": t["id"], "queries": got[t["id"]]}, ensure_ascii=False) + "\n" for t in TASKS))
    print("cost_usd", j.get("total_cost_usd"))


def rank():
    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session
    s = Session(Index.load(PRIV / "index-nw"))
    qs = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (HERE / "queries.jsonl").open()}
    res = {}
    for t in TASKS:
        q = [x for x in qs[t["id"]] if isinstance(x, str) and x.strip()][:4]
        ids = [r["id"] for r in s.search_skills(None, queries=q, k=50)["results"]]
        nw = {i.split("@")[0]: n + 1 for n, i in enumerate(ids) if i.startswith("northwind/")}
        req = {name: nw.get(f"northwind/{name}") for name in t["required_skills"]}
        res[t["id"]] = {"required": req, "n_results": len(ids),
                        "top10": sum(1 for r in req.values() if r and r <= 10),
                        "top50": sum(1 for r in req.values() if r),
                        "northwind_in_top50": nw}
    (HERE / "ranks.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k, f"top10 {v['top10']}/{len(v['required'])} top50 {v['top50']}/{len(v['required'])}", v["required"])


if __name__ == "__main__":
    {"gen": gen, "rank": rank}[sys.argv[1]]()
