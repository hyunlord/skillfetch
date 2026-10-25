#!/usr/bin/env python3
"""report-trivial.md: V1 pre-release check on the 10 trivial stage-4 tasks (runs/V{0,1}/<task>-t{1,2,3}.*).
Per session (stage 4 parser): fired (any skillfetch call), path, reached load_skills / loaded >= 1, turns, cost; the
first main-thread assistant message (text and tool calls) of every V1 session that fired. Writes trivial.jsonl."""
import json
import statistics as st
import sys
from pathlib import Path

S5 = Path(__file__).resolve().parents[1]
E2E = S5.parent
sys.path.insert(0, str(E2E / "stage4" / "scripts"))
from eval_stage4 import SF, is_router, jl, json_payload, parse  # noqa: E402

tasks = {t["id"]: t for t in jl(E2E / "stage4" / "tasks.jsonl") if t["task_type"] == "trivial"}
rows = []
for v in ("V0", "V1"):
    for f in sorted((S5 / "runs" / v).glob("s4-*-t[123].jsonl")):
        meta, init, result, calls, results, _ = parse(f)
        sf = [c for c in calls if c["name"].startswith(SF)]
        ridx = next((i for i, c in enumerate(calls) if is_router(c)), None)
        loads = [c for c in sf if c["name"] == SF + "load_skills"]
        loaded = []
        for c in loads:
            p = json_payload(results.get(c["id"], "")) or {}
            loaded += [s["id"] for s in p.get("skills", []) if isinstance(s, dict) and "id" in s]
        first_msg = None
        for line in f.read_text().splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
                content = e["message"].get("content", [])
                first_msg = (first_msg or []) + content  # stream-json splits one message: thinking, then text / tool_use
                if any(c.get("type") in ("text", "tool_use") for c in content):
                    break
        rows.append({"variant": v, "task": meta["task"], "rep": meta["tag"], "fired": bool(sf),
                     "path": ("a" if ridx is not None and ridx < calls.index(sf[0]) else "b") if sf else None,
                     "router_called": ridx is not None, "searched": any(c["name"] == SF + "search_skills" for c in sf),
                     "load_called": bool(loads), "loaded": list(dict.fromkeys(loaded)),
                     "num_turns": result.get("num_turns"), "subtype": result.get("subtype"),
                     "cost_usd": result.get("total_cost_usd"), "wall_s": meta.get("wall_s"),
                     "first_tool": calls[0]["name"] + (f"({calls[0]['input'].get('skill')})" if calls[0]["name"] == "Skill" else "") if calls else None,
                     "first_message": first_msg})
(S5 / "trivial.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
by = {v: [r for r in rows if r["variant"] == v] for v in ("V0", "V1")}
s4 = [r for r in jl(E2E / "stage4" / "sessions.jsonl") if r["env"] == "E1" and r["task"] in tasks]
med = lambda xs: round(st.median(xs), 3) if xs else "–"  # noqa: E731
L = ["# 5단계 V1 배포 전 확인 — 사소한 태스크 발화 (report)\n",
     "사소한 태스크는 4단계의 trivial 10개다(`stage4/tasks.jsonl`, 텍스트 그대로). 10개 × 반복 3 × {V0 `s5`, V1 `s5-v1`} = 60세션이다.",
     "- 설정은 본 실행과 같다: E1, `--max-turns 16`, skillfetch `14d2020`, 격리, `scripts/run_session.py`. 태그는 `t1`–`t3`이다.",
     "- 큐 `runs/_queue-trivial.txt`, 행 `trivial.jsonl`.",
     "- 4단계 E1(라우터 R-a)에서 같은 10개는 발화 " + f"{sum(r['fired'] for r in s4)}/{len(s4)}였다.\n",
     "## 표 1. 발화와 비용\n", "| 지표 | V0 | V1 |\n|---|---|---|"]
def rate(xs):
    return f"{sum(xs)}/{len(xs)}"
for name, f in (("발화 (skillfetch 호출 ≥1)", lambda rs: rate([r["fired"] for r in rs])),
                ("  라우터 skill 호출(발화 포함)", lambda rs: rate([r["router_called"] for r in rs])),
                ("  발화 중 load_skills 호출", lambda rs: f"{sum(r['load_called'] for r in rs if r['fired'])}/{sum(r['fired'] for r in rs)}"),
                ("  발화 중 1개 이상 로드", lambda rs: f"{sum(bool(r['loaded']) for r in rs if r['fired'])}/{sum(r['fired'] for r in rs)}"),
                ("턴 중앙 / 평균", lambda rs: f"{med([r['num_turns'] for r in rs])} / {round(st.mean([r['num_turns'] for r in rs]), 2)}"),
                ("비용 중앙 / 평균 ($)", lambda rs: f"{med([r['cost_usd'] for r in rs])} / {round(st.mean([r['cost_usd'] for r in rs]), 3)}"),
                ("비용 합 ($)", lambda rs: f"{round(sum(r['cost_usd'] for r in rs), 2)}"),
                ("시간 중앙 (s)", lambda rs: f"{med([r['wall_s'] for r in rs])}"),
                ("16턴 캡", lambda rs: rate([r["subtype"] == "error_max_turns" for r in rs]))):
    L.append(f"| {name} | {f(by['V0'])} | {f(by['V1'])} |")
mv = {v: st.mean([r["cost_usd"] for r in by[v]]) for v in by}
mt = {v: st.mean([r["num_turns"] for r in by[v]]) for v in by}
L.append(f"\nV1/V0 비율(평균): 비용 {mv['V1'] / mv['V0']:.2f}, 턴 {mt['V1'] / mt['V0']:.2f}.\n")
L.append("## 표 2. 태스크별 발화 수 (0–3)\n\n| 태스크 | 표현 | 요청(앞 90자) | 4단계 E1 | V0 | V1 |\n|---|---|---|---|---|---|")
for t in sorted(tasks):
    fr = lambda src: sum(r["fired"] for r in src if r["task"] == t)  # noqa: E731
    L.append(f"| {t} | {tasks[t]['phrasing']} | {tasks[t]['prompt'][:90].replace(chr(10), ' ').replace('|', '/')} | {fr(s4)} | {fr(by['V0'])} | {fr(by['V1'])} |")
n1 = sum(r["fired"] for r in by["V1"])
L.append("\n## 판정\n")
L.append(f"V1 발화 {n1}/30. 기준은 \"≤ 3/30이면 배포 가능\"이다 → **{'배포 가능' if n1 <= 3 else '기준 초과'}**.\n")
if n1:
    L.append("## V1 발화 세션의 첫 assistant 메시지 (원문 그대로)" + ("" if n1 > 3 else " — 기준 이내지만 기록으로 남긴다") + "\n")
    for tid in sorted({r["task"] for r in by["V1"] if r["fired"]}):
        L.append(f"{tid} 요청 전문:\n\n> " + tasks[tid]["prompt"].replace("\n", "\n> ") + "\n")
    for r in by["V1"]:
        if not r["fired"]:
            continue
        L.append(f"**{r['task']} {r['rep']}** — 로드: {', '.join(x.split('/')[-1].split('@')[0] for x in r['loaded']) or '없음'}; 턴 {r['num_turns']}, ${round(r['cost_usd'], 3)}\n")
        for c in r["first_message"] or []:
            if c.get("type") == "text" and c.get("text", "").strip():
                L.append("> " + c["text"].strip().replace("\n", "\n> "))
            elif c.get("type") == "tool_use":
                L.append(f"> `{c['name']}` {json.dumps(c.get('input'), ensure_ascii=False)[:200]}")
            elif c.get("type") == "thinking":
                L.append("> (thinking 블록" + (": 내용 비어 있음/서명만" if not c.get("thinking", "").strip() else ": " + c["thinking"].strip()[:300].replace("\n", " ")) + ")")
        L.append("")
(S5 / "report-trivial.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
