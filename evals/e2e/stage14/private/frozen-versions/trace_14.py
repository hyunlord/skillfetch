#!/usr/bin/env python3
"""Stage 14 trace (c) (DESIGN §4 item 4(c)): did a skill used in an earlier request of the same session leave its rules in a
later request's output?
  build   stage14-private/trace-package/: one item per (main session, request k >= 2) whose earlier requests used or
          loaded at least one skill (P skills, router-loaded skills, other Skill calls; not the router itself; from
          stage14-private/usage-14.json). Item folder <id>/ = TASK.md (that request, verbatim), diff.patch (that request's
          diff, build_blind_s2.clean_diff, worktree paths replaced), skills.md (each earlier skill: name and its one-line
          description — P skills from their SKILL.md front matter, router skills from the index record, others name
          only; no bodies). No condition names. Item ids random; key in stage14-private/keys/trace-key.jsonl.
  verify  stage14-private/trace/<id>.json from the judge: {"skills": [{"name", "trace": "yes"|"no", "quote": "..."}]}.
          A "yes" counts only if its quote is a substring of that item's diff.patch (else counted as "no", listed as
          unverified). Writes stage14-private/trace-14.json (per item and per condition × task).
usage: trace_14.py build | verify"""
import json
import re
import secrets
import sys
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
E2E = S14.parent
PRIV = E2E / "stage14-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
from build_blind_s2 import clean_diff  # noqa: E402

WT = re.compile(r"/\S*?skillfetch-e2e-wt/sq/[A-Za-z0-9_.-]+")
PKG, OUT = PRIV / "trace-package", PRIV / "trace"


def descriptions():
    d = {}
    for f in (E2E / "stage13-private" / "p-skills").glob("*/SKILL.md"):
        m = re.search(r"^description:\s*(.+)$", f.read_text(errors="replace"), re.M)
        d[f.parent.name] = (m.group(1).strip().strip('"') if m else "")[:300]
    for line in (E2E / "stage10" / "index" / "staging-4" / "skills.jsonl").open():
        r = json.loads(line)
        d.setdefault(r.get("name"), (r.get("description") or "")[:300])
    return d


def build():
    assert not PKG.exists(), "trace package already built"
    rows = json.loads((PRIV / "usage-14.json").read_text())
    desc = descriptions()
    reqs = (S14 / "requests.md").read_text()
    keys = []
    for r in rows:
        if r["k"] < 2 or not r["prior_skills"]:
            continue
        iid = secrets.token_hex(4)
        d = PKG / iid
        d.mkdir(parents=True)
        prompt = re.search(rf"^## \d {r['task']} \(\w+\)\n((?:> .*\n?)+)", reqs, re.M).group(1)
        (d / "TASK.md").write_text("# Request (verbatim)\n\n" + "\n".join(l[2:] for l in prompt.strip().splitlines()) + "\n")
        base = PRIV / "runs" / f"{r['session']}.p{r['k']}"
        (d / "diff.patch").write_text(WT.sub("<worktree>", clean_diff(Path(str(base) + ".diff"))))
        (d / "skills.md").write_text("# Skills used earlier in the same conversation\n\n" + "".join(
            f"- **{n}**: {desc.get(n) or '(no description)'}\n" for n in r["prior_skills"]))
        keys.append({"id": iid, "session": r["session"], "cond": r["cond"], "order": r["order"], "tag": r["tag"], "k": r["k"],
                     "task": r["task"], "skills": r["prior_skills"]})
    (PRIV / "keys").mkdir(exist_ok=True)
    (PRIV / "keys" / "trace-key.jsonl").write_text("".join(json.dumps(k) + "\n" for k in keys))
    (PKG / "README.md").write_text(README)
    print(f"{len(keys)} items")


README = """# Trace check

Each folder is one output (`diff.patch`) of one request (`TASK.md`) in a longer conversation. `skills.md` lists skills
(instruction packs) that were used earlier in the same conversation, for other requests, with a one-line description.

For each listed skill, decide whether this diff shows that skill's rules or style applied to this request although the
request did not need them (examples: design-system or visual rules in backend code, a testing methodology's file layout
in a docs change, the skill's name in comments or files). Ordinary good practice that any engineer would use for this
request is not a trace.

Write `<folder>.json` into the output folder you are given:
{"skills": [{"name": "<skill>", "trace": "yes" | "no", "quote": "<exact text copied from diff.patch that shows it, or empty>"}]}
Every listed skill exactly once. A "yes" needs a quote copied exactly from `diff.patch` (one line or part of a line).
"""


def verify():
    keys = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "keys" / "trace-key.jsonl").open()}
    items, problems = [], []
    for iid, k in keys.items():
        f = OUT / f"{iid}.json"
        if not f.exists():
            problems.append(f"{iid}: missing")
            continue
        j = json.loads(f.read_text())
        diff = (PKG / iid / "diff.patch").read_text()
        got = {s["name"]: s for s in j.get("skills", [])}
        if set(got) != set(k["skills"]):
            problems.append(f"{iid}: skills {sorted(got)} != {k['skills']}")
        res = []
        for n in k["skills"]:
            s = got.get(n, {})
            yes = s.get("trace") == "yes"
            ok = yes and bool(s.get("quote")) and s["quote"] in diff
            res.append({"skill": n, "trace": ok, "claimed": yes, "unverified": yes and not ok, "quote": s.get("quote", "")})
        items.append({**k, "results": res, "any_trace": any(x["trace"] for x in res)})
    if problems:
        sys.exit("problems:\n" + "\n".join(problems))
    agg = {}
    for it in items:
        a = agg.setdefault(it["cond"], {"items": 0, "with_trace": 0, "skill_pairs": 0, "traces": 0, "unverified": 0})
        a["items"] += 1
        a["with_trace"] += it["any_trace"]
        a["skill_pairs"] += len(it["results"])
        a["traces"] += sum(x["trace"] for x in it["results"])
        a["unverified"] += sum(x["unverified"] for x in it["results"])
    (PRIV / "trace-14.json").write_text(json.dumps({"by_condition": agg, "items": items}, indent=1, ensure_ascii=False))
    print(json.dumps(agg, indent=1))


if __name__ == "__main__":
    {"build": build, "verify": verify}[sys.argv[1]]()
