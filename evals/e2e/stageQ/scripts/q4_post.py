#!/usr/bin/env python3
"""Stage Q4 post-hoc rule extraction (DESIGN §4): skills loaded in the main run that are not in the pre-extracted
rules (stageQ-private/q4/rules.json) get rules from their body only, with the same prompt and procedure as
q4_pre.py rules (one isolated `claude -p` per skill, stageQ/prompts/sys-rules.txt, user prompt = "SKILL\\n" + body),
before any judging output is read. Marked "post" in the Q4 key.
usage:
  python3 q4_post.py list <requests.jsonl>                    the loaded ids without rules -> q4/post-ids.json
  uvx --from <server> python q4_post.py bodies                fetch their bodies (staging-4) into q4/bodies/
  python3 q4_post.py rules [--run]                            extract -> q4/rules-post.json"""
import json
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
QP = E2E / "stageQ-private" / "q4"
IDX = E2E / "stage10" / "index" / "staging-4"
mode = sys.argv[1]
bdir = QP / "bodies"
if mode == "list":
    pre = json.loads((QP / "rules.json").read_text())["rules"]
    rows = [json.loads(l) for l in open(sys.argv[2]) if l.strip()]
    ids = sorted({s for r in rows if r["tag"].startswith("m") for s in r["loaded"]} - set(pre))
    (QP / "post-ids.json").write_text(json.dumps(ids, indent=1))
    print(json.dumps({"post_ids": len(ids), "ids": ids}))
elif mode == "bodies":
    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session
    s = Session(Index.load(IDX))
    errs = []
    for i in json.loads((QP / "post-ids.json").read_text()):
        res = s.resolve_set([i], [])
        ld = s.load_skills(res["set_id"], max_tokens=100000)
        if ld.get("errors") or not ld.get("content"):
            errs.append({"id": i, "errors": ld.get("errors")})
            continue
        body = ld["content"].split("\n", 2)[2] if ld["content"].startswith("## 1.") else ld["content"]
        (bdir / (i.replace("/", "__") + ".md")).write_text(body)
    print(json.dumps({"body_errors": errs}))
elif mode == "rules":
    ids = json.loads((QP / "post-ids.json").read_text())
    have = [i for i in ids if (bdir / (i.replace("/", "__") + ".md")).exists()]
    print(json.dumps({"skills": len(have), "estimate_usd": round(len(have) * 0.047, 2)}))
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
        cost = round(sum(r.get("cost_usd") or 0 for r in res), 3)
        (QP / "rules-post.json").write_text(json.dumps({"rules": out, "failed": bad, "cost_usd": cost}, indent=1, ensure_ascii=False))
        print(json.dumps({"rules_for": len(out), "failed": len(bad), "cost_usd": cost}))
