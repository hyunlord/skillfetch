"""Stage 9 shared loaders (plain Python; no skillfetch import)."""
import json
import os
import re
from pathlib import Path

S9 = Path(__file__).resolve().parents[1]
E2E = S9.parent
S8 = E2E / "stage8"
BASE_INDEX = Path.home() / ".skillfetch" / "index"
RUN = os.environ.get("S9_RUN", "")  # "" = first run (stage9/), e.g. "run-b" -> stage9/run-b/
OUT = S9 / RUN if RUN else S9
OUT.mkdir(exist_ok=True)


def jl(p):
    return [json.loads(l) for l in Path(p).open() if l.strip()]


def by_id(p):
    return {r["id"]: r for r in jl(p)}


tasks = by_id(E2E / "stage3" / "tasks.jsonl")
v3 = by_id(E2E / "stage3" / "followup" / "oracle-v3.jsonl")
vb = by_id(S8 / "oracle-v5-ss-b.jsonl")
GAP = sorted(t for t in tasks if not v3[t]["relevant"] and not tasks[t]["expect_none"] and tasks[t]["task_type"] != "trivial")


def records(index_dir):
    return by_id(Path(index_dir) / "skills.jsonl")


def repo_of(rec):
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/", rec.get("source_url") or "")
    return m.group(1).lower() if m else None


def rel_sets(oracle, index_ids=None):
    """{task: relevant keys}; with index_ids, only keys that are records of that index."""
    out = {}
    for t, o in oracle.items():
        r = {x["skill"] for x in o["pool"] if x["grade"] >= 2}
        out[t] = r if index_ids is None else r & index_ids
    return out
