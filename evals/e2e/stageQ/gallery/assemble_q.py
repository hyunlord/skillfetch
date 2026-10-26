#!/usr/bin/env python3
"""Stage Q, Q1 gallery data (as stage10/gallery/assemble_s10.py): every Q1 main run (6 tasks × on/off × m1, m2) with its
screenshots, diff path and stats, check items, loaded skills, turns, wall, cost, and the judge scores and reasons
(p1, p2, and gpt when present) joined through the blind keys. Writes stageQ-private/gallery-data.json.
usage: assemble_q.py"""
import json
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
SQ, PRIV = E2E / "stageQ", E2E / "stageQ-private"
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
from run_s11 import load_tasks  # noqa: E402

TASKS = ("d1-landing", "d4-email", "s10-t016", "s11-t266", "s2-api", "s2-data")


def reasons(pas):
    keyf = PRIV / "keys" / f"blind-key-{pas}.jsonl"
    if not keyf.exists():
        return {}
    k = {x["code"]: x for x in map(json.loads, keyf.open())}
    out = {}
    for f in (PRIV / "judge" / pas).glob("*.md"):
        lines = f.read_text().splitlines()
        head = next((l for l in lines if l.startswith("| code |")), None)
        if not head:
            continue
        cols = [c.strip() for c in head.strip("|").split("|")]
        for l in lines:
            m = re.match(r"\|\s*([0-9a-f]{8})\s*\|", l)
            if m and m.group(1) in k:
                row = dict(zip(cols, [c.strip() for c in l.strip("|").split("|")]))
                x = k[m.group(1)]
                score = int(row.get("(b) 쓸만함 1-5") or row.get("총점 1-5"))
                out[(x["task"], x["cond"], x["tag"])] = {"score": score, "ai_look": int(row["(a) AI느낌 수"]) if "(a) AI느낌 수" in row else None,
                                                         "reason": row.get("근거", "")}
    return out


tasks = load_tasks()
rq = {(r["task"], r["job"].split(":")[2], r["tag"]): r for r in map(json.loads, (PRIV / "requests-m1-m2-m3-m4-m5.jsonl").open())
      if r["kind"] == "q1"}
rs = {p: reasons(p) for p in ("p1", "p2", "gpt")}
runs = []
for t in TASKS:
    for cond in ("off", "on"):
        for tag in ("m1", "m2"):
            base = PRIV / "runs" / f"q1-{t}-{cond}-{tag}"
            meta = json.loads(Path(str(base) + ".meta.json").read_text())
            cdir = Path(str(base) + ".check")
            shots = {sub: [str(p) for p in sorted((cdir / sub).glob("*.png"))] for sub in ("screens", "screens-375") if (cdir / sub).exists()}
            r = rq[(t, cond, tag)]
            runs.append({"task": t, "bundle": tasks[t]["bundle"], "cond": cond, "tag": tag, "shots": shots,
                         "diff_path": str(base) + ".diff", "diff": meta["check"].get("diff", {}),
                         "check_pass": meta["check"].get("pass"), "check_items": meta["check"].get("items", []),
                         "loaded": r["loaded"], "fired": r["fired"], "turns": r["turns"], "wall_s": r["wall_s"],
                         "cost_usd": r["cost_usd"],
                         "scores": {p: {k: v for k, v in rs[p][(t, cond, tag)].items() if k != "reason"} for p in rs if (t, cond, tag) in rs[p]},
                         "reasons": {p: {"reason": rs[p][(t, cond, tag)]["reason"]} for p in rs if (t, cond, tag) in rs[p]}})
data = {"tasks": {t: {"bundle": tasks[t]["bundle"], "prompt": tasks[t]["prompt"]} for t in TASKS}, "runs": runs}
(PRIV / "gallery-data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
print(json.dumps({"runs": len(runs), "with_p1_p2": sum("p1" in r["scores"] and "p2" in r["scores"] for r in runs),
                  "with_gpt": sum("gpt" in r["scores"] for r in runs)}))
