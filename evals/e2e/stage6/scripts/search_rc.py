#!/usr/bin/env python3
"""The exact search_skills output (compact, k=50, no profile) for the R-c queries of the 380 stage-3 tasks
(stage3/followup/rc-R-c-380.jsonl). Run under uvx --from git+https://github.com/hyunlord/skillfetch@cc5d16c.
Writes gen/results-rc.json {task: <search_skills result dict>}."""
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S6 = Path(__file__).resolve().parents[1]
s = Session(Index.load(DEFAULT_INDEX_DIR))
q = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (S6.parent / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
(S6 / "gen" / "results-rc.json").write_text(json.dumps({t: s.search_skills(None, queries=qs) for t, qs in q.items()}, ensure_ascii=False))
