#!/usr/bin/env python3
"""6b bundle (3): adapt the 4 stage-3 tasks with no relevant skill in oracle v4 that sit on stacks these repos hold
(t004, t133, t179, t354) to repos/fastapi or repos/nextjs. System prompt = stage4/gen/sys-readapt-2.txt (stage-4 adapt
rules + "everything presented as existing must be in the source" + "not a trivial task" + both repos' source); one call
(stage-4 batch cache, name s6b-adapt-b3); title-leak rewrite as in stage 4 (max 3 rounds).
Writes stage4/gen/candidates-rs6b.jsonl (input of stage4/scripts/prep_oracle.py with S4_ROUND=s6b) and prep/candidates-b3.jsonl."""
import json
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(E2E / "stage4" / "scripts"))
from batch import S4, call, parse_json, parse_json_last  # noqa: E402

IDS = ["t004", "t133", "t179", "t354"]
TOK = re.compile(r"[a-z0-9]+(?:[-_.+][a-z0-9]+)*")
titles = {(json.loads(l).get("title") or json.loads(l)["name"]).lower() for l in (Path.home() / ".skillfetch/index/skills.jsonl").open()}


def leaks(text):  # stage-4 rule (adapt_tasks.leaks)
    toks = set(TOK.findall(text.lower()))
    toks |= {p for t in toks for p in re.split(r"[-_.+]", t)}
    return sorted(t for t in toks if t in titles)


s3 = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
prompt = "REQUESTS\n\n" + "\n\n".join(
    f"### {i}\ntask type: {s3[i]['task_type']}; phrasing: {s3[i]['phrasing']}; original stack: {s3[i]['stack']}"
    + (f"; direction: {s3[i]['direction']}" if s3[i].get("direction") else "") + f"\noriginal request:\n{s3[i]['text']}" for i in IDS)
r = call("s6b-adapt-b3", S4 / "gen" / "sys-readapt-2.txt", prompt)
assert not r["is_error"]
got = {x["id"]: x for x in parse_json_last(r["text"])}
assert set(got) == set(IDS), set(IDS) - set(got)
rows = []
for i in IDS:
    t, x = s3[i], got[i]
    rows.append({"id": "s6b-" + i, "src": i, "repo": x["repo"], "ui": bool(x.get("ui")) and x["repo"] == "fastapi",
                 **{k: t.get(k) for k in ("task_type", "stack", "phrasing", "pair_id", "pair_side", "direction", "expect_none")},
                 "text": x["text"]})
for rnd in range(1, 4):
    bad = [x for x in rows if leaks(x["text"])]
    if not bad:
        break
    p = "\n\n".join(f"### {x['id']}\nforbidden: {', '.join(leaks(x['text']))}\nrequest:\n{x['text']}" for x in bad)
    new = parse_json(call(f"s6b-adapt-b3-rewrite-r{rnd}", S4 / "gen" / "sys-rewrite.txt", p)["text"])
    for x in bad:
        if x["id"] in new:
            x["text"], x["rewritten"] = new[x["id"]], True
for x in rows:
    x["title_leaks"] = leaks(x["text"])
body = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows)
(S4 / "gen" / "candidates-rs6b.jsonl").write_text(body)
(Path(__file__).resolve().parents[1] / "prep" / "candidates-b3.jsonl").write_text(body)
print("cost", r.get("cost_usd"))
for x in rows:
    print("\n##", x["id"], x["repo"], "ui" if x["ui"] else "", x["title_leaks"], "\n" + x["text"])
