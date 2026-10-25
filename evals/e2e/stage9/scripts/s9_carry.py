#!/usr/bin/env python3
"""§13 label step 2: carry run-b §5 grades (rows with source s9-grade in run-b/oracle-v5-ss-b-s9g.jsonl) into
<OUT>/oracle-v5-ss-b-s9.jsonl when the id exists in the target staging index, the grading card (name, 220-char
description) is identical to run-b's (grade-labels-s9.json + run-b staging records), and the task has no grade for it
yet. usage: S9_RUN=run-c s9_carry.py <target_staging_dir> <runb_staging_dir>"""
import json
import re
import sys
from collections import Counter

from s9_common import OUT, S9, by_id, records

tgt, rb = records(sys.argv[1]), records(sys.argv[2])
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731
card = lambda r: (r["name"], desc220(r.get("description")))  # noqa: E731
src = by_id(S9 / "run-b" / "oracle-v5-ss-b-s9g.jsonl")
dst = by_id(OUT / "oracle-v5-ss-b-s9.jsonl")
stat = Counter()
for t, o in dst.items():
    have = {x["skill"] for x in o["pool"]}
    add = []
    for x in src[t]["pool"]:
        if "s9-grade" not in x.get("sources", []):
            continue
        k = x["skill"]
        if k not in tgt:
            stat["not_in_target"] += 1
        elif k in have:
            stat["already_graded_in_target"] += 1
        elif card(tgt[k]) != card(rb[k]):
            stat["card_differs"] += 1
        else:
            add.append({**x, "sources": ["s9-grade (carried from run-b)"]})
            stat["carried"] += 1
    o["pool"] += add
    o["relevant"] = [x["skill"] for x in o["pool"] if x["grade"] >= 2]
(OUT / "oracle-v5-ss-b-s9.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in dst.values()))
(OUT / "carry.json").write_text(json.dumps(dict(stat), indent=1))
print(json.dumps(dict(stat)))
