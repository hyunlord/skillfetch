#!/usr/bin/env python3
"""Step T1: candidates = stage-3 tasks on the python / ts_react_next stacks (130) + the expect_none tasks of the other
stacks (26), adapted to repos/fastapi or repos/nextjs (gen/sys-adapt.txt, both file lists in the system prompt),
10 per call. Title-token leaks (stage 3 rule) are rewritten with gen/sys-rewrite.txt (max 3 rounds).
Writes gen/candidates.jsonl {id, src, repo, ui, task_type, stack, phrasing, pair_id, pair_side, direction,
expect_none, text, title_leaks}."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S4, call, parse_json, parse_json_last, run_all  # noqa: E402

E2E = S4.parent
TOK = re.compile(r"[a-z0-9]+(?:[-_.+][a-z0-9]+)*")
titles = {(json.loads(l).get("title") or json.loads(l)["name"]).lower() for l in (Path.home() / ".skillfetch/index/skills.jsonl").open()}


def leaks(text):
    toks = set(TOK.findall(text.lower()))
    toks |= {p for t in toks for p in re.split(r"[-_.+]", t)}
    return sorted(t for t in toks if t in titles)


ROUND = os.environ.get("S4_ROUND", "1")
SUF, PRE = ("", "") if ROUND == "1" else (f"-r{ROUND}", f"r{ROUND}-")
src = [json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()]
if ROUND == "1":
    cands = [t for t in src if t["stack"] in ("python", "ts_react_next") or t["expect_none"]]
else:  # round 2: the other stacks' stage-3 select / restate / search failures (classes short after round 1)
    s3cls = {json.loads(l)["id"]: json.loads(l)["class"] for l in (E2E / "stage3" / "selection-eval.jsonl").open()}
    used = {json.loads(l)["src"] for l in (S4 / "gen" / "candidates.jsonl").open()}
    cands = [t for t in src if t["id"] not in used and s3cls[t["id"]] in ("select_fail", "restate_fail", "search_fail")]
jobs = []
for n in range(0, len(cands), 10):
    chunk = cands[n: n + 10]
    prompt = "REQUESTS\n\n" + "\n\n".join(
        f"### {t['id']}\ntask type: {t['task_type']}; phrasing: {t['phrasing']}; original stack: {t['stack']}"
        + (f"; direction: {t['direction']}" if t.get("direction") else "") + f"\n{t['text']}" for t in chunk)
    jobs.append((f"{PRE}adapt-{n // 10 + 1:02d}", S4 / "gen" / "sys-adapt.txt", prompt))
res = run_all(jobs, workers=6)
got = {}
for r in res:
    assert not r["is_error"], r["name"]
    for x in parse_json_last(r["text"]):
        got[x["id"]] = x
missing = [t["id"] for t in cands if t["id"] not in got]
assert not missing, missing
rows = []
for t in cands:
    x = got[t["id"]]
    rows.append({"id": "s4-" + t["id"], "src": t["id"], "repo": x["repo"], "ui": bool(x.get("ui")) and x["repo"] == "fastapi",
                 **{k: t.get(k) for k in ("task_type", "stack", "phrasing", "pair_id", "pair_side", "direction", "expect_none")},
                 "text": x["text"]})
for rnd in range(1, 4):
    bad = [r for r in rows if leaks(r["text"])]
    if not bad:
        break
    prompt = "\n\n".join(f"### {r['id']}\nforbidden: {', '.join(leaks(r['text']))}\nrequest:\n{r['text']}" for r in bad)
    new = parse_json(call(f"{PRE}adapt-rewrite-r{rnd}", S4 / "gen" / "sys-rewrite.txt", prompt)["text"])
    for r in bad:
        if r["id"] in new:
            r["text"], r["rewritten"] = new[r["id"]], True
for r in rows:
    r["title_leaks"] = leaks(r["text"])
(S4 / "gen" / f"candidates{SUF}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
from collections import Counter
print(len(rows), "candidates", Counter(r["repo"] for r in rows), "ui", sum(r["ui"] for r in rows),
      "| still leaking", [(r["id"], r["title_leaks"]) for r in rows if r["title_leaks"]])
print("cost", round(sum((x.get("cost_usd") or 0) for x in res), 3))
