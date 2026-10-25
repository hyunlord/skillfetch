#!/usr/bin/env python3
"""blind-run-c-gap.jsonl: for the 54 non-trivial tasks of blind-run-b-60, every (task, skill) not yet GPT-graded among
run-c R-c top-10, baseline-index R-c top-10, run-c S-b' picks and baseline S-b' r1-r3 picks; one row per (task, skill).
Same format as blind-run-b-60 (task_id, task_text, candidate_id, title, summary; no source / earlier grade / index),
shuffled within a task (seed s9c-gap-<task>), ids h01... Key in blind-run-c-gap-key.json."""
import json
import random
import re

from s9_common import BASE_INDEX, E2E, S9, records, tasks

stg = records(str(__import__("pathlib").Path.home() / "github/skillfetch/data/index-staging-3"))
base = records(BASE_INDEX)
key60 = json.loads((S9 / "blind-run-b-60-key.json").read_text())
seen = {(t, v["skill"]) for t, vv in key60.items() for v in vv.values()}
D = sorted(t for t in key60 if not tasks[t]["expect_none"])
ld = lambda p: {t: [x["id"] for x in r["results"]] for t, r in json.loads(p.read_text()).items()}  # noqa: E731
RC, RB = ld(S9 / "run-c" / "results-rc-staging-3.json"), ld(S9 / "dry" / "results-rc-baseline.json")
selc = {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S9 / "run-c" / "select-S-bp-staging-3.jsonl").open()}
selb = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()} for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731
blind, key = [], {}
cnt = {"runc_top10": 0, "base_top10": 0, "runc_picks": 0, "base_picks": 0}
for t in D:
    need = {}
    for k in RC[t][:10]:
        need.setdefault(k, set()).add("runc_top10")
    for k in RB[t][:10]:
        need.setdefault(k, set()).add("base_top10")
    for k in selc.get(t, []):
        need.setdefault(k, set()).add("runc_picks")
    for s in selb:
        for k in s.get(t, []):
            need.setdefault(k, set()).add("base_picks")
    rows = sorted(k for k in need if (t, k) not in seen)
    for k in rows:
        for w in need[k]:
            cnt[w] += 1
    random.Random(f"s9c-gap-{t}").shuffle(rows)
    key[t] = {}
    for i, k in enumerate(rows):
        r = stg.get(k) or base[k]
        cid = f"h{i + 1:02d}"
        blind.append({"task_id": t, "task_text": tasks[t]["text"], "candidate_id": cid, "title": r["name"], "summary": desc220(r.get("description"))})
        key[t][cid] = {"skill": k, "where": sorted(need[k])}
(S9 / "blind-run-c-gap.jsonl").write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in blind))
(S9 / "blind-run-c-gap-key.json").write_text(json.dumps(key, indent=0, ensure_ascii=False))
print(json.dumps({"tasks": len(D), "rows": len(blind), "tasks_with_rows": sum(bool(v) for v in key.values()),
                  "rows_by_membership (a row can be in several)": cnt,
                  "rows_only_in_picks": sum(1 for v in key.values() for x in v.values() if not set(x["where"]) & {"runc_top10", "base_top10"})}))
