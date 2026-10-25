#!/usr/bin/env python3
"""Step 2b pools: per task, oracle-2a picks ∪ search_skills top-10 on the raw task text (k=50 compact, no profile,
default tiers) ∪ 2 seeded random tier A/B canonical skills; shuffled (seeded) so the grader cannot tell the source.
Run with skillfetch main: uvx --from git+https://github.com/hyunlord/skillfetch@a671e6a python scripts/make_pools.py
Writes gen/pools.json {task_id: {"order": [...], "sources": {skill: [2a|bm25|random]}, "bm25_top50": [...]}}."""
import json
import random
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S3 = Path(__file__).resolve().parents[1]
s = Session(Index.load(DEFAULT_INDEX_DIR))
cat = [l.split(" | ")[0] for l in (S3 / "gen" / "catalog.md").read_text().splitlines()]
o2a = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle-2a.jsonl").open()}
pools = {}
for line in (S3 / "tasks.jsonl").open():
    t = json.loads(line)
    rng = random.Random(f"pool-{t['id']}")
    top = [r["id"] for r in s.search_skills(t["text"])["results"]]
    src = {}
    for sid in o2a[t["id"]]["skills"]:
        src.setdefault(sid, []).append("2a")
    for sid in top[:10]:
        src.setdefault(sid, []).append("bm25")
    rest = [c for c in cat if c not in src]
    for sid in rng.sample(rest, 2):
        src.setdefault(sid, []).append("random")
    order = list(src)
    rng.shuffle(order)
    pools[t["id"]] = {"order": order, "sources": src, "bm25_top50": top}
(S3 / "gen" / "pools.json").write_text(json.dumps(pools, indent=1))
sizes = sorted(len(p["order"]) for p in pools.values())
print(len(pools), "pools; size min/median/max", sizes[0], sizes[len(sizes) // 2], sizes[-1],
      "| 2a picks outside bm25 top10:", sum(1 for p in pools.values() for v in p["sources"].values() if v == ["2a"]))
