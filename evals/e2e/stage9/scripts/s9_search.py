#!/usr/bin/env python3
"""R-c (4 queries, k=50, no profile, default tiers) on one index directory.
Run: uvx --from git+https://github.com/hyunlord/skillfetch@38dcb69 python scripts/s9_search.py <index_dir> <out.json>"""
import json
import sys
from pathlib import Path

from skillfetch.index.loader import Index
from skillfetch.mcp.session import Session

E2E = Path(__file__).resolve().parents[2]
s = Session(Index.load(Path(sys.argv[1]).expanduser()))
q = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
out = {t: s.search_skills(None, queries=qs) for t, qs in q.items()}
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False))
print(json.dumps({"tasks": len(out), "errors": sum("results" not in v for v in out.values())}))
