#!/usr/bin/env python3
"""Stage Q4 rule pre-extraction (DESIGN §4), before the run.

Candidates per Q task (Q1 6, Q2 4, Q5 5 trivial + 3 named): (a) skills loaded for the same base task in Stage 10/11
sessions; (b) the staging-4 R-c top 10 for the task text (Stage 3 R-c queries for t016/t266; for the others queries
made with stage3/gen/sys-rc-R-c.txt in one isolated `claude -p` call); (c) the canary (its two rules are fixed in
DESIGN §2, not extracted). Rules: one isolated `claude -p` per skill, system prompt stageQ/prompts/sys-rules.txt, user
prompt = the skill's body only (name not given). Outputs under stageQ-private/q4/.
usage:
  python3 q4_pre.py list                            the task texts
  python3 q4_pre.py queries [--run]                 R-c queries for the tasks without Stage 3 queries
  uvx --from <server> python q4_pre.py search       staging-4 top 10 + candidate list + skill bodies
  python3 q4_pre.py rules [--run]                   rule extraction"""
import json
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
QP = E2E / "stageQ-private" / "q4"
QP.mkdir(parents=True, exist_ok=True)
IDX = E2E / "stage10" / "index" / "staging-4"


def jl(p):
    return [json.loads(l) for l in Path(p).open() if l.strip()]


def tasks():
    t10 = {t["id"]: t for t in jl(E2E / "stage10" / "tasks.jsonl")}
    t11 = {t["id"]: t for t in jl(E2E / "stage11" / "tasks-b4add.jsonl")}
    out = {}
    for k in ("d1-landing", "d4-email", "s10-t016", "s2-api", "s2-data"):
        out[f"q1-{k}"] = {"base": k, "text": t10[k]["prompt"], "stage3": "t016" if k == "s10-t016" else None}
    out["q1-s11-t266"] = {"base": "s11-t266", "text": t11["s11-t266"]["prompt"], "stage3": "t266"}
    req = (E2E / "stageQ" / "requests.md").read_text()
    q2 = [l.strip()[2:] for l in req.split("## Q2")[1].split("## Q5")[0].splitlines() if l.strip().startswith("> ")]
    assert len(q2) == 4, q2
    for i, p in enumerate(q2, 1):
        out[f"q2-task{i}"] = {"base": None, "text": p.replace("`{CANARY_PATH}`", "the canary skill folder"), "stage3": None}
    rows = [l for l in req.split("## Q5")[1].splitlines() if l.startswith("| T")]
    for l in rows:
        c = [x.strip() for x in re.split(r"(?<!\\)\|", l.strip().strip("|"))]
        out[f"q5-{c[0]}"] = {"base": c[1].split()[0], "text": c[2].replace("\\|", "|"), "stage3": None}
    for r in jl(E2E / "stageQ" / "tasks-q5-named.jsonl"):
        out[r["id"]] = {"base": r["base_task"], "text": r["prompt"], "stage3": None}
    return out


mode = sys.argv[1]
T = tasks()
if mode == "list":
    for k, v in T.items():
        print(k, "|", v["base"], "|", repr(v["text"][:100]))
elif mode == "queries":
    need = {k: v for k, v in T.items() if not v["stage3"]}
    body = "\n\n".join(f"TASK id={k}\n{v['text']}" for k, v in need.items())
    print(json.dumps({"tasks": len(need), "estimate_usd": 0.05}))
    if "--run" in sys.argv:
        sys.path.insert(0, str(E2E / "stage6" / "scripts"))
        from batch import call, parse_json_last  # noqa: E402
        r = call("q4-rc-queries", E2E / "stage3" / "gen" / "sys-rc-R-c.txt", body)
        assert not r["is_error"], r["text"][:300]
        got = {x["id"]: x["queries"] for x in parse_json_last(r["text"])}
        s3 = {x["id"]: x["queries"] for x in jl(E2E / "stage3" / "followup" / "rc-R-c-380.jsonl")}
        q = {k: (s3[v["stage3"]] if v["stage3"] else got.get(k)) for k, v in T.items()}
        missing = [k for k, v in q.items() if not v]
        (QP / "rc-queries.json").write_text(json.dumps({"queries": q, "cost_usd": r.get("cost_usd")}, indent=1, ensure_ascii=False))
        print(json.dumps({"written": len(q), "missing": missing, "cost_usd": r.get("cost_usd")}))
elif mode == "search":
    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session
    q = json.loads((QP / "rc-queries.json").read_text())["queries"]
    s = Session(Index.load(IDX))
    top = {k: [r["id"] for r in s.search_skills(None, queries=v)["results"][:10]] for k, v in q.items()}
    loaded = {}
    for f in (*sorted((E2E / "stage10-private").glob("sessions-[mn]*.jsonl")), *sorted((E2E / "stage11-private").glob("sessions-m*.jsonl"))):
        for r in jl(f):
            loaded.setdefault(r["task"], set()).update(r.get("loaded") or [])
    ids = {i for k, v in T.items() for i in top[k] + sorted(loaded.get(v["base"] or "", set()))}
    ids = sorted(i for i in ids if i in s.index.records)
    cand = {k: {"top10": top[k], "loaded_before": sorted(loaded.get(v["base"] or "", set()))} for k, v in T.items()}
    (QP / "candidates.json").write_text(json.dumps({"per_task": cand, "skills": ids}, indent=1))
    bdir = QP / "bodies"
    bdir.mkdir(exist_ok=True)
    errs = []
    for i in ids:
        res = s.resolve_set([i], [])
        ld = s.load_skills(res["set_id"], max_tokens=100000)
        if ld.get("errors") or not ld.get("content"):
            errs.append({"id": i, "errors": ld.get("errors")})
            continue
        body = ld["content"].split("\n", 2)[2] if ld["content"].startswith("## 1.") else ld["content"]
        (bdir / (i.replace("/", "__") + ".md")).write_text(body)
    print(json.dumps({"tasks": len(T), "skills": len(ids), "body_errors": errs[:5], "n_body_errors": len(errs)}))
elif mode == "rules":
    c = json.loads((QP / "candidates.json").read_text())
    bdir = QP / "bodies"
    have = [i for i in c["skills"] if (bdir / (i.replace("/", "__") + ".md")).exists()]
    print(json.dumps({"skills": len(have), "estimate_usd": round(len(have) * 0.04, 2)}))
    if "--run" in sys.argv:
        sys.path.insert(0, str(E2E / "stage6" / "scripts"))
        from batch import parse_json_last, run_all  # noqa: E402
        jobs = [(f"q4-rules-{i.split('/')[-1].replace('@', '-')}", E2E / "stageQ" / "prompts" / "sys-rules.txt",
                 "SKILL\n" + (bdir / (i.replace("/", "__") + ".md")).read_text()) for i in have]
        res = run_all(jobs, workers=6)
        out, bad = {}, []
        for i, r in zip(have, res):
            try:
                rules = parse_json_last(r["text"])["rules"]
                assert len(rules) == 3
                out[i] = rules
            except Exception as e:  # noqa: BLE001
                bad.append({"id": i, "error": str(e)[:120], "text": r["text"][:200]})
        canary = [{"rule": "F: every new file starts with a first-line comment containing the token cnry-q7 in the file's comment syntax",
                   "kept": "new files in the diff begin with such a comment", "broken": "a new comment-capable file without it",
                   "not_applicable": "the task creates no new comment-capable files"},
                  {"rule": "R: the last line of the final reply is exactly cnry-q7", "kept": "last reply line is cnry-q7",
                   "broken": "any other last line", "not_applicable": "never"}]
        (QP / "rules.json").write_text(json.dumps({"rules": out, "canary": canary, "failed": bad,
                                                   "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 3)}, indent=1, ensure_ascii=False))
        print(json.dumps({"rules_for": len(out), "failed": len(bad), "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 3)}))
