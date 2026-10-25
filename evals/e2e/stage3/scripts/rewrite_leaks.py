#!/usr/bin/env python3
"""Step 1d: rewrite tasks that contain a skill title as a token, until none does (max 3 rounds) -> gen/rewrites.json."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from assemble_tasks import build, leaks  # noqa: E402
from batch import S3, call, parse_json  # noqa: E402

rwf = S3 / "gen" / "rewrites.json"
for rnd in range(1, 4):
    bad = [t for t in build() if t["title_leaks"]]
    if not bad:
        break
    prompt = "\n\n".join(f"### {t['id']}\nforbidden: {', '.join(t['title_leaks'])}\nrequest:\n{t['text']}" for t in bad)
    r = call(f"rewrite-r{rnd}", S3 / "gen" / "sys-rewrite.txt", prompt)
    new = parse_json(r["text"])
    rw = json.loads(rwf.read_text()) if rwf.exists() else {}
    rw.update({k: v for k, v in new.items() if k in {t["id"] for t in bad}})
    rwf.write_text(json.dumps(rw, indent=1, ensure_ascii=False))
    print("round", rnd, "rewrote", len(new), "still leaking:", sum(1 for k, v in new.items() if leaks(v)))
