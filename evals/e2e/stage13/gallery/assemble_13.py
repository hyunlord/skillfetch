#!/usr/bin/env python3
"""Stage 13 gallery data: every main run of A (off), P and R (on) for the 18 tasks, m1–m3 (162 runs; the same runs as
stage13/report-13.md), each with screenshots, diff path, check result and items, skills (P: the P skills it used, from
stage13-private/usage.json; R: skills the router loaded, same file; all three: every Skill tool call), turns, wall,
API-price equivalent (the session's result event), judge scores and reasons of the Stage 13 judging (p1, p2: A, P and R
judged in one set, joined through stage13-private/keys) and the automatic metrics of gallery v2 (autometrics.py).
Writes stage13-private/gallery-data-13.json. No model calls.
usage: assemble_13.py"""
import json
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
PRIV = E2E / "stage13-private"
sys.path.insert(0, str(E2E / "stageQ" / "scripts"))
sys.path.insert(0, str(E2E / "stageQ" / "gallery"))
sys.path.insert(0, str(E2E / "stage13" / "scripts"))
import run_q  # noqa: E402
from autometrics import metrics  # noqa: E402
from build_blind_13 import P_NAMES, Q1, TASKS, source  # noqa: E402

STACK = {"d1-landing": "디자인", "d4-email": "디자인", "d2-redesign": "디자인", "d3-dashboard": "디자인",
         "s10-t016": "Rust", "s11-t266": "Rust", "s10-t263": "Rust", "s10-t115": "Rust", "s10-t198": "Swift",
         "s11-t160": "Go", "s11-t118": "Java", "s2-docs": "TypeScript", "s10-t033": "TypeScript",
         "s2-api": "Python", "s2-data": "Python", "s2-tests": "Python", "s10-t001": "Python", "s6b-t179": "Python"}


def judged(pas):
    k = {x["code"]: x for x in map(json.loads, (PRIV / "keys" / f"blind-key-{pas}.jsonl").open())}
    out = {}
    for f in (PRIV / "judge" / pas).glob("*.md"):
        lines = f.read_text().splitlines()
        head = next((l for l in lines if l.startswith("| code |")), None)
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


def session(jsonl):
    res, skills = {}, []
    for line in Path(jsonl).open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "result":
            res = d
        elif d.get("type") == "assistant":
            for c in (d.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                    skills.append((c.get("input") or {}).get("skill") or "")
    return res, skills


tasks = run_q.all_tasks()
usage = json.loads((PRIV / "usage.json").read_text())
sc = {p: judged(p) for p in ("p1", "p2")}
runs = []
for t in TASKS:
    for cond in ("A", "P", "R"):
        for tag in ("m1", "m2", "m3"):
            base = source(t, cond, tag)
            meta = json.loads(Path(str(base) + ".meta.json").read_text())
            cdir = Path(str(base) + ".check")
            shots = {sub: [str(p) for p in sorted((cdir / sub).glob("*.png"))] for sub in ("screens", "screens-375") if (cdir / sub).exists()}
            res, skill_calls = session(str(base) + ".jsonl")
            diff = Path(str(base) + ".diff").read_text(errors="replace") if Path(str(base) + ".diff").exists() else ""
            if cond == "P":
                loaded = [n for n in usage[t]["P"][f"{base.name}.jsonl"]["used"] if n in P_NAMES]  # the 8 P skills only
            elif cond == "R":
                loaded = [n.rsplit("/", 1)[-1] + " (레포 경로)" if "/" in n else n for n in usage[t]["R"].get(f"{base.name}.jsonl", [])]
            else:
                loaded = []
            chk = meta.get("check") or {}
            key = (t, cond, tag)
            runs.append({"task": t, "bundle": tasks[t]["bundle"], "stack": STACK[t], "source": "Q" if t in Q1 else "Q1x",
                         "cond": cond, "tag": tag, "shots": shots, "diff_path": str(base) + ".diff",
                         "check_pass": chk.get("pass"), "check_items": chk.get("items", []),
                         "loaded": loaded, "skill_calls": skill_calls, "turns": res.get("num_turns"),
                         "result": res.get("subtype"), "wall_s": (res.get("duration_ms") or 0) / 1000 or None,
                         "cost_usd": res.get("total_cost_usd"), "auto": metrics(diff),
                         "scores": {p: {k: v for k, v in sc[p][key].items() if k != "reason"} for p in sc if key in sc[p]},
                         "reasons": {p: {"reason": sc[p][key]["reason"]} for p in sc if key in sc[p]}})
data = {"tasks": {t: {"bundle": tasks[t]["bundle"], "stack": STACK[t], "source": "Q" if t in Q1 else "Q1x",
                      "prompt": tasks[t]["prompt"], "repo": tasks[t]["repo"], "base_branch": tasks[t]["base_branch"]} for t in TASKS},
        "runs": runs}
(PRIV / "gallery-data-13.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
print(json.dumps({"runs": len(runs), "tasks": len(data["tasks"]),
                  "with_p1_p2": sum("p1" in r["scores"] and "p2" in r["scores"] for r in runs),
                  "max_turns_results": sum(r["result"] == "error_max_turns" for r in runs)}))
