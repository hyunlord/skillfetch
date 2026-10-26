#!/usr/bin/env python3
"""Gallery v2 data: every Q1 run of Stage Q (stageQ-private, 6 tasks × on/off × m1–m2) and of the Q1 extension
(stageQ1x-private, 12 tasks × on/off × m1–m3), each with screenshots, diff path, check items, loaded skills, turns,
wall, API-price equivalent, judge scores and reasons (p1, p2, gpt when present; joined through that source's blind keys)
and the automatic metrics (autometrics.py). Writes stageQ-private/gallery-data-v2.json.
usage: assemble_v2.py"""
import json
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(E2E / "stageQ" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_q  # noqa: E402
from autometrics import metrics  # noqa: E402

SOURCES = [("Q", E2E / "stageQ-private", ("d1-landing", "d4-email", "s10-t016", "s11-t266", "s2-api", "s2-data"), ("m1", "m2")),
           ("Q1x", E2E / "stageQ1x-private", ("d2-redesign", "d3-dashboard", "s10-t263", "s10-t115", "s10-t198", "s11-t160",
                                              "s11-t118", "s2-docs", "s10-t033", "s2-tests", "s10-t001", "s6b-t179"), ("m1", "m2", "m3"))]
STACK = {"d1-landing": "디자인", "d4-email": "디자인", "d2-redesign": "디자인", "d3-dashboard": "디자인",
         "s10-t016": "Rust", "s11-t266": "Rust", "s10-t263": "Rust", "s10-t115": "Rust", "s10-t198": "Swift",
         "s11-t160": "Go", "s11-t118": "Java", "s2-docs": "TypeScript", "s10-t033": "TypeScript",
         "s2-api": "Python", "s2-data": "Python", "s2-tests": "Python", "s10-t001": "Python", "s6b-t179": "Python"}


def reasons(priv, pas):
    keyf = priv / "keys" / f"blind-key-{pas}.jsonl"
    if not keyf.exists():
        return {}
    k = {x["code"]: x for x in map(json.loads, keyf.open())}
    out = {}
    for f in (priv / "judge" / pas).glob("*.md"):
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
                out[(x["task"], x["cond"], x["tag"])] = {"score": int(row.get("(b) 쓸만함 1-5") or row.get("총점 1-5")),
                                                         "ai_look": int(row["(a) AI느낌 수"]) if "(a) AI느낌 수" in row else None,
                                                         "reason": row.get("근거", "")}
    return out


tasks = run_q.all_tasks()
runs = []
for src, priv, tids, tags in SOURCES:
    rqf = sorted(priv.glob("requests-*.jsonl"))
    rq = {}
    for f in rqf:
        for r in map(json.loads, f.open()):
            if r["kind"] == "q1":
                rq[(r["task"], r["job"].split(":")[2], r["tag"])] = r
    rs = {p: reasons(priv, p) for p in ("p1", "p2", "gpt")}
    for t in tids:
        for cond in ("off", "on"):
            for tag in tags:
                base = priv / "runs" / f"q1-{t}-{cond}-{tag}"
                if not Path(str(base) + ".meta.json").exists():
                    continue
                meta = json.loads(Path(str(base) + ".meta.json").read_text())
                cdir = Path(str(base) + ".check")
                shots = {sub: [str(p) for p in sorted((cdir / sub).glob("*.png"))] for sub in ("screens", "screens-375") if (cdir / sub).exists()}
                r = rq.get((t, cond, tag), {})
                diff = Path(str(base) + ".diff").read_text(errors="replace") if Path(str(base) + ".diff").exists() else ""
                key = (t, cond, tag)
                runs.append({"source": src, "task": t, "bundle": tasks[t]["bundle"], "stack": STACK[t], "cond": cond, "tag": tag,
                             "repo": tasks[t]["repo"], "base_branch": tasks[t]["base_branch"], "shots": shots,
                             "diff_path": str(base) + ".diff", "diff": (meta.get("check") or {}).get("diff", {}),
                             "check_pass": (meta.get("check") or {}).get("pass"), "check_items": (meta.get("check") or {}).get("items", []),
                             "loaded": r.get("loaded", []), "fired": r.get("fired"), "turns": r.get("turns"), "wall_s": r.get("wall_s"),
                             "cost_usd": r.get("cost_usd"), "auto": metrics(diff),
                             "scores": {p: {k: v for k, v in rs[p][key].items() if k != "reason"} for p in rs if key in rs[p]},
                             "reasons": {p: {"reason": rs[p][key]["reason"]} for p in rs if key in rs[p]}})
data = {"tasks": {r["task"]: {"bundle": r["bundle"], "stack": r["stack"], "source": r["source"], "prompt": tasks[r["task"]]["prompt"],
                              "repo": r["repo"], "base_branch": r["base_branch"]} for r in runs}, "runs": runs}
(E2E / "stageQ-private" / "gallery-data-v2.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
print(json.dumps({"runs": len(runs), "tasks": len(data["tasks"]), "with_p1_p2": sum("p1" in r["scores"] and "p2" in r["scores"] for r in runs),
                  "with_gpt": sum("gpt" in r["scores"] for r in runs)}))
