#!/usr/bin/env python3
"""Re-adapt the 7 non-trivial stage-4 tasks whose sessions all ended with "the code it describes is not in the
repository" (missing-code.json minus the trivial ones). Same rules as gen/sys-adapt.txt plus one rule that everything
the request presents as existing must be in the code, with the source of both repos (branch s4) in the system prompt
(gen/sys-readapt.txt). One call for the 7, same repo as before, then the stage-4 title-leak rewrite (max 3 rounds).
Writes gen/candidates-rfix.jsonl (candidates.jsonl format) for prep_oracle.py with S4_ROUND=fix."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S4, call, parse_json, parse_json_last  # noqa: E402
TOK = re.compile(r"[a-z0-9]+(?:[-_.+][a-z0-9]+)*")
titles = {(json.loads(l).get("title") or json.loads(l)["name"]).lower() for l in (Path.home() / ".skillfetch/index/skills.jsonl").open()}


def leaks(text):  # same as adapt_tasks.leaks (that module runs its batch on import)
    toks = set(TOK.findall(text.lower()))
    toks |= {p for t in toks for p in re.split(r"[-_.+]", t)}
    return sorted(t for t in toks if t in titles)


E2E = S4.parent
IDS = ["s4-t027", "s4-t033", "s4-t203", "s4-t211", "s4-t224", "s4-t229", "s4-t253"]
# pass 2 (READAPT_PASS=2): t027 and t033 came back as one-line edits in one file (the router's skip case), so they are
# redone with one more rule; the other five keep their pass-1 text
# pass 3 (READAPT_PASS=3): s4-t026 and s4-t177 are in missing-code.json (hand-classified, all runs) but were left out of
# the first 7 (a keyword count); redone with both rules, the 7 keep their pass-1/2 text
PASS = os.environ.get("READAPT_PASS", "1")
if PASS == "3":
    IDS = IDS + ["s4-t026", "s4-t177"]
REDO = {"1": IDS, "2": ["s4-t027", "s4-t033"], "3": ["s4-t026", "s4-t177"]}[PASS]
RULE = """- Everything the request presents as already there (a function, field, module, dependency, setting, data file,
  behaviour or bug) must be in the source below; read it. A bug fix or a performance request describes a defect or a
  slow path this code really has, with its real names. When the task needs code, data or config the repository does
  not have, the request asks for it to be created and says where, and never presents it as existing.
"""
RULE2 = """- None of these is a trivial task: the work must take more than a one-line edit in a single file.
"""


def src(repo, prefixes, skip):
    files = subprocess.run(["git", "-C", str(E2E / "repos" / repo), "ls-tree", "-r", "--name-only", "s4", "--", *prefixes],
                           capture_output=True, text=True, check=True).stdout.split()
    out = []
    for f in files:
        if any(s in f for s in skip):
            continue
        body = subprocess.run(["git", "-C", str(E2E / "repos" / repo), "show", f"s4:{f}"], capture_output=True, text=True).stdout
        out.append(f"--- {repo}/{f}\n{body}")
    return "\n".join(out)


base = (S4 / "gen" / "sys-adapt.txt").read_text()
head, tail = base.split("\nOutput JSON only:")
sysp = (head.rstrip() + "\n" + RULE + (RULE2 if PASS in ("2", "3") else "") + "\nOutput JSON only:" + tail.split("\n\nREPO fastapi")[0]
        + "\n\n" + "REPO fastapi" + tail.split("REPO fastapi", 1)[1]
        + "\n\nSOURCE (branch used for the sessions)\n"
        + src("fastapi", ["backend/app", "backend/tests", "backend/pyproject.toml", "frontend/src", "frontend/package.json", "compose.yml"],
              ["components/ui/", "/client/", "routeTree.gen", "alembic/versions/", "email-templates/"])
        + "\n" + src("nextjs", ["."], ["package-lock", ".claude/", ".mcp.json"]))
SYSF = S4 / "gen" / ("sys-readapt.txt" if PASS == "1" else "sys-readapt-2.txt")  # pass 3 = pass 2 prompt
SYSF.write_text(sysp)
old = {json.loads(l)["id"]: json.loads(l) for l in (S4 / "tasks.jsonl").open()}
s3 = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
prompt = "REQUESTS\n\n" + "\n\n".join(
    f"### {i}\ntask type: {old[i]['task_type']}; phrasing: {old[i]['phrasing']}; repository: {old[i]['repo']}"
    + (f"; direction: {old[i]['direction']}" if old[i].get("direction") else "")
    + f"\noriginal request:\n{s3[old[i]['src']]['text']}\nprevious adaptation (it named code that is not in the repository; agents given it "
      f"stopped and said so):\n{old[i]['text']}" for i in REDO)
r = call({"1": "readapt-7", "2": "readapt-2", "3": "readapt-3"}[PASS], SYSF, prompt)
assert not r["is_error"]
got = {x["id"]: x for x in parse_json_last(r["text"])}
assert set(got) == set(REDO), set(REDO) - set(got)
if PASS in ("2", "3"):  # keep the earlier text for the others
    prev = {json.loads(l)["id"]: json.loads(l) for l in (S4 / "gen" / ("candidates-rfix-pass1.jsonl" if PASS == "2" else "candidates-rfix-pass2.jsonl")).open()}
rows = []
for i in IDS:
    if i not in got:
        rows.append(prev[i])
        continue
    t, x = old[i], got[i]
    rows.append({"id": i, "src": t["src"], "repo": x["repo"], "ui": bool(x.get("ui")) and x["repo"] == "fastapi",
                 **{k: t.get(k) for k in ("task_type", "stack", "phrasing", "pair_id", "pair_side", "direction", "expect_none")},
                 "text": x["text"]})
for rnd in range(1, 4):
    bad = [x for x in rows if leaks(x["text"])]
    if not bad:
        break
    p = "\n\n".join(f"### {x['id']}\nforbidden: {', '.join(leaks(x['text']))}\nrequest:\n{x['text']}" for x in bad)
    new = parse_json(call(f"readapt{PASS}-rewrite-r{rnd}", S4 / "gen" / "sys-rewrite.txt", p)["text"])
    for x in bad:
        if x["id"] in new:
            x["text"], x["rewritten"] = new[x["id"]], True
for x in rows:
    x["title_leaks"] = leaks(x["text"])
(S4 / "gen" / "candidates-rfix.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
print("cost", r.get("cost_usd"), "| sys chars", len(sysp))
for x in rows:
    print("\n##", x["id"], x["repo"], "ui" if x["ui"] else "", x["title_leaks"], "\n" + x["text"])
