#!/usr/bin/env python3
"""7a-pool step 1a: search_skills(query=<direction phrase>) top-50 (BM25, no profile, default tiers), for every distinct
direction phrase of the 20 pairs. Run under uvx --from git+https://github.com/hyunlord/skillfetch@38dcb69.
Writes direction-top50.json {phrase: [50 ids]}."""
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S7 = Path(__file__).resolve().parents[1]
s = Session(Index.load(DEFAULT_INDEX_DIR))
tasks = [json.loads(l) for l in (S7.parent / "stage3" / "tasks.jsonl").open()]
phrases = sorted({t["direction"] for t in tasks if t.get("pair_id")})
out = {p: [r["id"] for r in s.search_skills(p)["results"]] for p in phrases}
(S7 / "direction-top50.json").write_text(json.dumps(out, indent=1))
print(len(phrases), "phrases", {p: len(v) for p, v in out.items()})
