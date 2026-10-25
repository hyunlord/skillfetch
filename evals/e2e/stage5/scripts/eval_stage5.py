#!/usr/bin/env python3
"""Stage 5 per-session rows from runs/V{0,1,2,3}/<task>-r{1,2,3}.* -> sessions.jsonl.
The session parser is stage 4's (stage4/scripts/eval_stage4.py: fired, path (a)/(b), first search turn, capped,
first-tool class, load vs oracle, offline-style class); `env` holds the variant. Labels: stage5/oracle.jsonl, plus
oracle-4-0.jsonl when it exists (post-run grading of loaded / first-search top-10 skills outside the pool).
Rankings for the class rule: stage 4 rankings (unchanged tasks), stage5/prep/rankings-rfix*.json (rewritten tasks).
Added per session: R-c step-1 text in the session's context, number of queries, 4th query == request."""
import json
import sys
from pathlib import Path

S5 = Path(__file__).resolve().parents[1]
E2E = S5.parent
sys.path.insert(0, str(E2E / "stage4" / "scripts"))
from eval_stage4 import jl, session  # noqa: E402

VARIANTS = ("V0", "V1", "V2", "V3")
RC_LINE = "Add (d), the user's request copied word for word"


def load_oracle():
    o = {x["id"]: x for x in jl(S5 / "oracle.jsonl")}
    p = S5 / "oracle-4-0.jsonl"
    if p.exists():
        o.update({x["id"]: x for x in jl(p)})
    return o


def main():
    tasks = {t["id"]: t for t in jl(S5 / "tasks.jsonl")}
    oracle = load_oracle()
    rank = {}
    for path in sorted((E2E / "stage4").glob("rankings*.json")):
        rank.update(json.loads(path.read_text()))
    for path in sorted((S5 / "prep").glob("rankings-rfix*.json")):
        rank.update(json.loads(path.read_text()))
    rows = []
    for v in VARIANTS:
        for f in sorted((S5 / "runs" / v).glob("s4-*-r[123].jsonl")):
            if not Path(str(f)[: -len(".jsonl")] + ".meta.json").exists():
                continue
            r = session(v, f, tasks, oracle, rank)
            r["variant"] = r.pop("env")
            r["rewritten"] = bool(tasks[r["task"]].get("rewritten_s5"))
            r["rc_text_in_context"] = RC_LINE in f.read_text()
            q = r["queries"] or []
            r["n_queries"] = len(q) if r["searched"] else None
            r["q4_is_request"] = (len(q) >= 4 and " ".join(q[3].split()) == " ".join(tasks[r["task"]]["prompt"].split())) if r["searched"] else None
            rows.append(r)
    (S5 / "sessions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(len(rows), "sessions")


if __name__ == "__main__":
    main()
