"""Distinct new skills (lint/scan ok, content_hash not in the index, deduplicated within the given repos only)."""
import json, subprocess, sys
from pathlib import Path
from skillfetch.ingest.build import _record
from skillfetch.ingest.skillfile import discover_skills
from skillfetch.ingest.snapshot import Snapshot
from skillfetch.ingest.sources import Source
W = Path("~/.skillfetch/work-staging").expanduser()
EXCLUDE = ["template", "templates", "fixtures", "__fixtures__", "testdata", "test-fixtures"]
idx = {json.loads(l)["content_hash"] for f in ("skills.jsonl", "rejected.jsonl") for l in open(f"data/index/{f}")}
def new_counts(repos):
    seen, out = set(), {}
    for repo in repos:
        d = W / repo.replace("/", "__")
        src = Source(id=repo.replace("/", "__"), kind="dir", url=str(d), exclude=EXCLUDE, publisher="x", publisher_trust="unknown")
        recs = [_record(Snapshot(src, d, "x", None), s).record for s in discover_skills(d, EXCLUDE, base=d)]
        n = 0
        for r in recs:
            if r.status == "ok" and r.content_hash not in idx and r.content_hash not in seen:
                seen.add(r.content_hash); n += 1
        out[repo] = n
    return out
if __name__ == "__main__":
    print(json.dumps(new_counts(sys.argv[1:])))
