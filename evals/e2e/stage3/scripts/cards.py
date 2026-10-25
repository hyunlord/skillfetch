"""Candidate card shown to the grader (2b, 2c, 3-0): id, title, full summary, tags."""
import json
from pathlib import Path

recs = {}
for l in (Path.home() / ".skillfetch/index/skills.jsonl").open():
    r = json.loads(l)
    recs[r["id"]] = r


def card(sid):
    r = recs[sid]
    tags = "; ".join(f"{k}: {', '.join(map(str, v))}" for k, v in (r.get("tags") or {}).items() if v)
    return f"- id: {sid}\n  title: {r.get('title') or r['name']}\n  summary: {r.get('summary') or r.get('description', '')}\n  tags: {tags}"
