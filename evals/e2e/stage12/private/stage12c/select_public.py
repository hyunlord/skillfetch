#!/usr/bin/env python3
"""Stage 12c public skills (stage12c/DESIGN.md §1): search staging-4 (server c55d561, default tiers A·B, k=50) with each
of the 10 Stage 12 tasks' R-c queries (search-check/queries.jsonl), merge the ten ranked lists round-robin by rank
(rank 1 of T1..C2, then rank 2, ...), drop duplicates and any skill whose name (frontmatter/title) collides with an
already chosen name or a Northwind name, and take the first 200 (the first 50 = scale 100). If fewer than 200, fill
from tier A·B by random.Random("s12c"). Bodies: BodyCache(root=public-bodies/) materialize (hash-verified; the
server's own fetch). Output public.json [{id, name, rank_order, scale}] .
usage: uvx --from ~/skillfetch-e2e-wt/s26-server/c55d561 python select_public.py"""
import json
import random
import re
from pathlib import Path

from skillfetch.index.fetch import BodyCache
from skillfetch.index.loader import Index
from skillfetch.mcp.session import Session

HERE = Path(__file__).resolve().parent
PRIV = HERE.parent
E2E = PRIV.parent
idx = Index.load(E2E / "stage10" / "index" / "staging-4")
s = Session(idx, bodies=BodyCache(root=HERE / "public-bodies"))
qs = [json.loads(l) for l in (PRIV / "search-check" / "queries.jsonl").open()]
lists = [[r["id"] for r in s.search_skills(None, queries=[q for q in x["queries"] if q.strip()][:4], k=50)["results"]]
         for x in qs]
NW = {d.name for d in (PRIV / "northwind-skills").iterdir()}


def name_of(i):
    r = idx.records[i]
    return re.sub(r"[^a-z0-9-]+", "-", (r.get("name") or r.get("title") or i.split("/")[1].split("@")[0]).lower()).strip("-")


chosen, names = [], set(NW)
order = [lists[t][k] for k in range(50) for t in range(len(lists)) if k < len(lists[t])]
for i in order:
    n = name_of(i)
    if i in chosen or n in names:
        continue
    chosen.append(i)
    names.add(n)
    if len(chosen) == 200:
        break
filled = 0
if len(chosen) < 200:
    pool = sorted(i for i, r in idx.records.items() if r.get("tier") in ("A", "B") and i not in chosen)
    random.Random("s12c").shuffle(pool)
    for i in pool:
        n = name_of(i)
        if n in names:
            continue
        chosen.append(i)
        names.add(n)
        filled += 1
        if len(chosen) == 200:
            break
out, fails = [], []
for k, i in enumerate(chosen):
    try:
        folder = s.bodies.materialize(idx.records[i], allow_file=False)
    except Exception as e:  # noqa: BLE001
        fails.append({"id": i, "error": str(e)[:200]})
        continue
    out.append({"id": i, "name": name_of(i), "order": k, "scale": 100 if k < 50 else 300, "folder": str(folder.relative_to(HERE)),
                "content_hash": idx.records[i]["content_hash"], "from_search": k < len(chosen) - filled})
(HERE / "public.json").write_text(json.dumps({"chosen": out, "fetch_failures": fails, "filled_random": filled}, indent=1))
print("chosen", len(chosen), "materialized", len(out), "failures", len(fails), "filled_random", filled)
