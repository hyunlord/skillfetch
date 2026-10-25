#!/usr/bin/env python3
"""Pilot (tag p0) isolation and cost report: init mcp_servers / plugins / skills, hook events, fired, router body
loaded (S-0 vs S-b' marker lines), turns, cost, input tokens, check pass. Writes report-pilot.md."""
import json
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
S0_MARK = "read all 50 and pick 1–3 that fit"  # main step 4 (wrapped across lines in the file; compared after whitespace join)
SB_MARK = "Do not pick a skill unless you can say in one sentence"
rows = []
for cond in ("A", "C0", "Cb"):
    for f in sorted((S6B / "runs" / cond).glob("*-p0.jsonl")):
        ev = [json.loads(l) for l in f.read_text().splitlines() if l.startswith("{")]
        init = next((e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"), {})
        res = next((e for e in reversed(ev) if e.get("type") == "result"), {})
        hooks = sorted({e.get("hook_event") for e in ev if e.get("type") == "system" and e.get("subtype") == "hook_started"})
        calls = [c for e in ev if e.get("type") == "assistant" and not e.get("parent_tool_use_id") for c in e["message"]["content"] if c.get("type") == "tool_use"]
        sf = [c["name"] for c in calls if c["name"].startswith("mcp__skillfetch__")]
        blob = " ".join(json.dumps(ev, ensure_ascii=False).replace("\\n", " ").split())
        meta = json.loads(Path(str(f)[:-6] + ".meta.json").read_text())
        u = res.get("usage") or {}
        rows.append({"cond": cond, "task": meta["task"], "mcp": [s.get("name") for s in init.get("mcp_servers", [])],
                     "plugins": [p.get("name") if isinstance(p, dict) else p for p in init.get("plugins", [])],
                     "skills": init.get("skills", []), "hooks": hooks, "fired": bool(sf), "sf_calls": sf,
                     "router_S0_text": S0_MARK in blob, "router_Sb_text": SB_MARK in blob,
                     "turns": res.get("num_turns"), "subtype": res.get("subtype"), "cost": res.get("total_cost_usd"),
                     "input_tokens": sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
                     "wall_s": meta["wall_s"], "check": meta["check"].get("pass"),
                     "check_failed": [i["name"] for i in meta["check"].get("items", []) if i["pass"] is False]})
L = ["# 6b 파일럿 3세션 (d1-landing, 태그 p0; 판정에서 제외)\n", "| 항목 | " + " | ".join(r["cond"] for r in rows) + " |", "|---|" + "---|" * len(rows)]
for k, lab in (("mcp", "init mcp_servers"), ("plugins", "init plugins"), ("skills", "init skills"), ("hooks", "훅 이벤트"),
               ("fired", "발화"), ("sf_calls", "skillfetch 호출"), ("router_S0_text", "세션 문맥에 S-0 4단계 문구"),
               ("router_Sb_text", "세션 문맥에 S-b′ 문장"), ("subtype", "결과"), ("turns", "턴"), ("cost", "비용 $"),
               ("input_tokens", "입력 토큰"), ("wall_s", "세션 시간 s"), ("check", "체크 통과"), ("check_failed", "실패한 체크 항목")):
    L.append(f"| {lab} | " + " | ".join(f"{len(r[k])}: {', '.join(map(str, r[k]))}" if k == "skills" else str(r[k]) for r in rows) + " |")
(S6B / "report-pilot.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
