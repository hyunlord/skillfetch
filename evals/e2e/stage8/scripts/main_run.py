#!/usr/bin/env python3
"""Stage 8 main run (DESIGN §2-추가 2): 380 tasks x 5 sequential calls on one skillselion-mcp process
(SS-q1, SS-q3, SS-kw, SS-load-kw, SS-load-full), >= 1 s apart, GITHUB_TOKEN in the server env only.
Appends to raw/main.jsonl; resumable (a (task, kind) with a non-error record is skipped). Load bodies are copied
from the client's temp folder to raw/load/<kind>/<task>/ right after each call (the folder is emptied before)."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ss_client import SS  # noqa: E402

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
tasks = [json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()]
rc = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
kw = {json.loads(l)["id"]: json.loads(l)["query"] for l in (S8 / "kw-queries.jsonl").open()}
TMP = Path(os.environ.get("TMPDIR", "/tmp")) / "skillselion"
done = set()
if (S8 / "raw" / "main.jsonl").exists():
    for l in (S8 / "raw" / "main.jsonl").open():
        r = json.loads(l)
        if not (r["error"] or r["is_error"]):
            done.add((r["task"], r["kind"]))
ss = SS("main", gh_token=True)
(S8 / "raw" / "main-server.json").write_text(json.dumps(ss.server_info, indent=1))
n = 0
for t in tasks:
    tid, text = t["id"], t["text"]
    calls = [("SS-q1", "search_skillselion", {"query": text, "type": "skill", "limit": 25}),
             ("SS-q3", "search_skillselion", {"query": rc[tid][0], "type": "skill", "limit": 25}),
             ("SS-kw", "search_skillselion", {"query": kw[tid], "type": "skill", "limit": 25}),
             ("SS-load-kw", "load_skill", {"query": kw[tid], "context": text}),
             ("SS-load-full", "load_skill", {"query": text, "context": text})]
    for kind, tool, args in calls:
        if (tid, kind) in done:
            continue
        if tool == "load_skill":
            shutil.rmtree(TMP, ignore_errors=True)
        rec = ss.tool(tid, kind, tool, args)
        if tool == "load_skill":
            m = re.search(r"saved locally → (\S+)", rec["text"])
            dest = S8 / "raw" / "load" / kind / tid
            shutil.rmtree(dest, ignore_errors=True)
            if m and Path(m.group(1)).is_dir():
                shutil.copytree(m.group(1), dest)
        n += 1
        if n % 25 == 0:
            print(f"{n} calls, at {tid} {kind}", flush=True)
ss.close()
print("done", n, flush=True)
