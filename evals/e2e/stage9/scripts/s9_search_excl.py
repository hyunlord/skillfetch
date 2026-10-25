#!/usr/bin/env python3
"""§12-3: R-c on a staging index with one source's records removed before the Searcher is built (offline stand-in for
a rebuild without that source). Run: uvx --from git+https://github.com/hyunlord/skillfetch@38dcb69 python
scripts/s9_search_excl.py <staging_dir> <source_prefix> <out.json>"""
import json
import sys
from pathlib import Path

from skillfetch.index.loader import Index
from skillfetch.mcp.session import Session

E2E = Path(__file__).resolve().parents[2]
idx = Index.load(Path(sys.argv[1]).expanduser())
drop = [i for i in idx.records if i.startswith(sys.argv[2])]
assert all(idx.records[i].get("canonical_id", i) == i for i in drop)
assert not any(str(r.get("canonical_id", "")).startswith(sys.argv[2]) for i, r in idx.records.items() if i not in drop)
for i in drop:
    del idx.records[i]
s = Session(idx)
q = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
out = {t: s.search_skills(None, queries=qs) for t, qs in q.items()}
Path(sys.argv[3]).write_text(json.dumps(out, ensure_ascii=False))
print(json.dumps({"dropped": len(drop), "records_left": len(idx.records), "errors": sum("results" not in v for v in out.values())}))
