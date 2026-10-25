#!/usr/bin/env python3
"""report-stage5.md + summary.json from sessions.jsonl (numbers and quotes only)."""
import json
import statistics as st
from collections import Counter
from itertools import combinations
from math import comb
from pathlib import Path

S5 = Path(__file__).resolve().parents[1]
E2E = S5.parent
jl = lambda p: [json.loads(l) for l in p.open() if l.strip()]  # noqa: E731
V = ("V0", "V1", "V2", "V3")
rows = jl(S5 / "sessions.jsonl")
tasks = {t["id"]: t for t in jl(S5 / "tasks.jsonl")}
oracle = {o["id"]: o for o in jl(S5 / ("oracle-4-0.jsonl" if (S5 / "oracle-4-0.jsonl").exists() else "oracle.jsonl"))}
s4 = [r for r in jl(E2E / "stage4" / "sessions.jsonl") if r["env"] == "E1" and r["task"] in tasks]
g40 = json.loads((S5 / "grade-4-0.json").read_text()) if (S5 / "grade-4-0.json").exists() else None
by = {v: [r for r in rows if r["variant"] == v] for v in V}
TIDS = sorted(tasks)
REW = [t for t in TIDS if tasks[t].get("rewritten_s5")]
UNC = [t for t in TIDS if t not in REW]


def rate(xs):
    return f"{sum(xs)}/{len(xs)} ({sum(xs) / len(xs):.2f})" if xs else "–"


def med(xs, d=1):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), d) if xs else "–"


def fires(v, tids, src=None):
    src = src if src is not None else by[v]
    return {t: sum(r["fired"] for r in src if r["task"] == t) for t in tids}


def sign_p(up, down):
    n = up + down
    if n == 0:
        return 1.0
    k = min(up, down)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


L, S = [], {}
L.append("# skillfetch 5단계 — 발화 레버 (report)\n")
L.append("설계는 `DESIGN.md`, 확인 세션은 `report-check.md`, 입력 해시는 `FROZEN.sha256`에 있다. 세션 행은 `sessions.jsonl`이다(4단계 파서 그대로). 작업 결과물은 채점하지 않는다.\n")
L.append("## 0. 설정\n")
L.append("| 항목 | 값 |\n|---|---|")
L.append("| skillfetch | `14d2020`(PR #45). 라우터 SKILL.md = `stage3/router-cands/R-c/SKILL.md`(바이트 동일). 서버는 로컬 worktree(V0–V2 `14d2020`, V3 `exp/mcp-instructions-v3` = `14d2020` + `INSTRUCTIONS`, push 안 함) |")
L.append("| 환경 | 4단계 E1: `--setting-sources project --strict-mcp-config --mcp-config <skillfetch만>`, `--include-hook-events`, `--max-turns 16`, 허용 도구 `Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*`, 세션마다 새 worktree + 의존성 설치 |")
L.append(f"| 태스크 | 19 = 4단계 사소하지 않은 태스크. 그중 {len(REW)}개를 레포 실제 코드를 가리키도록 다시 썼다({', '.join(REW)}). 바뀌지 않은 것 {len(UNC)}개 |")
L.append(f"| 세션 | 4 변형 × 19 × 3 = {len(rows)} (변형별 " + ", ".join(f"{v} {len(by[v])}" for v in V) + "). 확인 2세션, 버린 옛 t026 4세션은 제외 |")
if g40:
    L.append(f"| oracle | `oracle.jsonl` + 4-0 보정(세션이 로드했거나 첫 search top-10에 들었는데 풀 밖이던 {g40['added']}개, 같은 2b 프롬프트, ${g40['cost_usd']}; 새 관련 {g40['added_relevant']}). 관련 쌍 {g40['relevant_before']} → {g40['relevant_after']}, 관련 없음 태스크 {g40['no_relevant_after']}/19 |")
L.append("")
# Table 1
L.append("## 표 1. 변형별 발화·검색·로드\n")
L.append("| 지표 | " + " | ".join(V) + " |\n|---|" + "---|" * len(V))
def line(name, f):
    L.append(f"| {name} | " + " | ".join(f(by[v]) for v in V) + " |")
line("발화 (skillfetch 호출 ≥1)", lambda rs: rate([r["fired"] for r in rs]))
line("  (a) 라우터 경유", lambda rs: rate([r["path"] == "a" for r in rs]))
line("  (b) MCP 직접", lambda rs: rate([r["path"] == "b" for r in rs]))
line("  라우터만(MCP 없음)", lambda rs: rate([r["router_no_mcp"] for r in rs]))
line("발화 — 다시 쓴 9개", lambda rs: rate([r["fired"] for r in rs if r["rewritten"]]))
line("발화 — 바뀌지 않은 10개", lambda rs: rate([r["fired"] for r in rs if not r["rewritten"]]))
line("search ≥1", lambda rs: rate([r["searched"] for r in rs]))
line("load_skills로 1개 이상 로드", lambda rs: rate([r["loaded_any"] for r in rs]))
line("첫 search 턴 중앙 [범위]", lambda rs: (lambda xs: f"{med(xs, 0)} [{min(xs)}–{max(xs)}]" if xs else "–")([r["first_search_turn"] for r in rs if r["first_search_turn"]]))
line("16턴 캡 도달", lambda rs: rate([r["capped"] for r in rs]))
line("세션 비용 중앙 / 평균 ($)", lambda rs: f"{med([r['cost_usd'] for r in rs], 3)} / {round(st.mean([r['cost_usd'] or 0 for r in rs]), 3)}")
line("세션 비용 합 ($)", lambda rs: f"{round(sum(r['cost_usd'] or 0 for r in rs), 2)}")
line("입력 토큰 중앙 (k)", lambda rs: f"{med([r['input_tokens'] / 1000 for r in rs], 0)}")
line("세션 시간 중앙 (s)", lambda rs: f"{med([r['wall_s'] for r in rs], 0)}")
L.append("")
# Table 2 paired
L.append("## 표 2. 태스크별 발화 수(0–3), V0 대비 짝지은 차이\n")
f0 = fires("V0", TIDS)
L.append("| 비교 | 대상 태스크 | 평균 차 (발화/3회) | 늘어남 / 줄어듦 / 같음 | 부호 검정 p (양측) |\n|---|---|---|---|---|")
S["paired"] = {}
for v in V[1:]:
    for lab, tids in (("19", TIDS), ("바뀌지 않은 10", UNC), ("다시 쓴 9", REW)):
        fv = fires(v, tids)
        d = [fv[t] - f0[t] for t in tids]
        up, dn = sum(x > 0 for x in d), sum(x < 0 for x in d)
        p = sign_p(up, dn)
        S["paired"][f"{v}|{lab}"] = {"mean_diff": round(st.mean(d), 3), "up": up, "down": dn, "same": len(d) - up - dn, "sign_p": round(p, 3)}
        L.append(f"| {v} − V0 | {lab} | {st.mean(d):+.2f} | {up} / {dn} / {len(d) - up - dn} | {p:.3f} |")
L.append("\n태스크별 발화 수 (4단계 E1은 같은 태스크 ID의 4단계 세션이다; 다시 쓴 태스크는 4단계에서는 옛 텍스트였다):\n")
f4 = fires(None, TIDS, s4)
L.append("| 태스크 | 작업종류 · 표현 | 다시 씀 | 4단계 E1 | " + " | ".join(V) + " |\n|---|---|---|---|" + "---|" * len(V))
fv = {v: fires(v, TIDS) for v in V}
for t in TIDS:
    L.append(f"| {t} | {tasks[t]['task_type']} · {tasks[t]['phrasing']} | {'예' if t in REW else ''} | {f4[t]} | " + " | ".join(str(fv[v][t]) for v in V) + " |")
L.append(f"| 합 | | | {sum(f4.values())}/57 | " + " | ".join(f"{sum(fv[v].values())}/57" for v in V) + " |")
L.append("")
# Table 3 first tool
L.append("## 표 3. 첫 도구 귀속 (세션당 하나, 4단계 규칙)\n")
cls = ["router_first", "explore", "rules_git", "other_skill", "omc_hook", "none"]
L.append("| 분류 | " + " | ".join(V) + " |\n|---|" + "---|" * len(V))
for c in cls:
    L.append(f"| {c} | " + " | ".join(str(sum(r['first_tool_class'] == c for r in by[v])) for v in V) + " |")
L.append("\n첫 도구 이름 분포:\n")
for v in V:
    L.append(f"- {v}: " + ", ".join(f"{k} {n}" for k, n in Counter(r["first_tool"] for r in by[v]).most_common(6)))
L.append("")
# Table 4 loads
L.append("## 표 4. 로드 vs oracle (로드한 세션만; 관련 = 등급 ≥2)\n")
L.append("| 지표 | " + " | ".join(V) + " |\n|---|" + "---|" * len(V))
ld = {v: [r for r in by[v] if r["loaded_any"]] for v in V}
L.append("| 로드한 세션 | " + " | ".join(str(len(ld[v])) for v in V) + " |")
L.append("| 로드 스킬 수 중앙 | " + " | ".join(str(med([len([s for s in r['loaded'] if not s.startswith('path:')]) for r in ld[v]], 0)) for v in V) + " |")
L.append("| precision 평균 | " + " | ".join(str(round(st.mean([r['precision'] for r in ld[v] if r['precision'] is not None]), 3)) if ld[v] else "–" for v in V) + " |")
L.append("| recall 평균 (관련 있는 태스크) | " + " | ".join((lambda xs: str(round(st.mean(xs), 3)) if xs else "–")([r['recall'] for r in ld[v] if r['recall'] is not None]) for v in V) + " |")
L.append("| 적중 (관련 1개 이상 로드) | " + " | ".join(rate([r['hit'] for r in ld[v] if r['hit'] is not None]) for v in V) + " |")
L.append("| 관련 없음 태스크에서 로드 (과잉) | " + " | ".join(rate([r['loaded_any'] for r in by[v] if not oracle[r['task']]['relevant'] and r['searched']]) + " (search한 세션 중)" for v in V) + " |")
L.append("| 잘못 로드(등급<2) 평균 | " + " | ".join(str(round(st.mean([r['wrong_loads'] for r in ld[v]]), 2)) if ld[v] else "–" for v in V) + " |")
L.append("\n분류(search한 세션):\n")
L.append("| 분류 | " + " | ".join(V) + " |\n|---|" + "---|" * len(V))
for c in ("ok", "select_fail", "restate_fail", "search_fail", "over_load"):
    L.append(f"| {c} | " + " | ".join(str(sum(r['class'] == c for r in by[v] if r['searched'])) for v in V) + " |")
L.append("\nsearch했지만 로드 없음, 원인:\n")
for v in V:
    L.append(f"- {v}: " + (", ".join(f"{k} {n}" for k, n in Counter(r['searched_no_load'] for r in by[v] if r['searched_no_load']).items()) or "0"))
L.append("")
# Table 5 R-c check and Jaccard
L.append("## 표 5. 라우터 R-c 적용 확인, 반복 간 top-50 Jaccard\n")
L.append("| 지표 | " + " | ".join(V) + " |\n|---|" + "---|" * len(V))
L.append("| 라우터 경유 발화 중 R-c 1단계 (d) 문구가 세션 문맥에 있음 | " + " | ".join(rate([r['rc_text_in_context'] for r in by[v] if r['path'] == 'a']) for v in V) + " |")
L.append("| search 쿼리 수 분포 | " + " | ".join(", ".join(f"{k}개 {n}" for k, n in sorted(Counter(r['n_queries'] for r in by[v] if r['searched']).items())) or "–" for v in V) + " |")
L.append("| 4번째 쿼리 = 요청 원문 | " + " | ".join(rate([r['q4_is_request'] for r in by[v] if r['searched']]) for v in V) + " |")
def jrows(v):
    out = []
    for t in TIDS:
        tops = [r["top50"] for r in by[v] if r["task"] == t and r["top50"]]
        out += [jac(a, b) for a, b in combinations(tops, 2)]
    return out
L.append("| 같은 태스크 2회 이상 search한 쌍의 top-50 Jaccard 평균 (쌍 수) | " + " | ".join((lambda xs: f"{round(st.mean(xs), 3)} ({len(xs)})" if xs else "–")(jrows(v)) for v in V) + " |")
L.append("")
import difflib
L.append("4번째 쿼리와 요청 원문의 유사도(difflib 비율, 공백 정규화), 요청 길이별(search한 세션 전체):\n")
L.append("| 요청 길이(자) | 세션 | 글자 그대로 | 비율 ≥0.9 | 0.5–0.9 | <0.5 (요약으로 바뀜) | 4번째 쿼리 길이 중앙 |\n|---|---|---|---|---|---|---|")
for lo, hi in ((0, 400), (400, 800), (800, 10 ** 6)):
    rs = [r for r in rows if r["searched"] and lo <= len(" ".join(tasks[r["task"]]["prompt"].split())) < hi]
    rat = [difflib.SequenceMatcher(None, " ".join(tasks[r["task"]]["prompt"].split()), " ".join(r["queries"][3].split())).ratio() for r in rs]
    L.append(f"| {lo}–{hi if hi < 10 ** 6 else ''} | {len(rs)} | {sum(r['q4_is_request'] for r in rs)} | {sum(x >= 0.9 for x in rat)} | {sum(0.5 <= x < 0.9 for x in rat)} | {sum(x < 0.5 for x in rat)} | {med([len(r['queries'][3]) for r in rs], 0)} |")
L.append("\n오프라인(3단계 배치 생성, 20태스크/호출)에서는 529/530이 글자 그대로였다(`stage3/router-winner.md`).")
L.append("")
# Table 6 vs stage 4
L.append("## 표 6. 바뀌지 않은 10태스크: 4단계 E1(라우터 R-a, `a1cbcd5`) vs 5단계 V0(R-c, `14d2020`)\n")
s4u = [r for r in s4 if r["task"] in UNC]
v0u = [r for r in by["V0"] if r["task"] in UNC]
L.append("| 지표 | 4단계 E1 | 5단계 V0 |\n|---|---|---|")
for name, k in (("발화", "fired"), ("search ≥1", "searched"), ("로드 ≥1", "loaded_any"), ("16턴 캡", "capped")):
    L.append(f"| {name} | {rate([r[k] for r in s4u])} | {rate([r[k] for r in v0u])} |")
L.append(f"| 세션 비용 중앙 ($) | {med([r['cost_usd'] for r in s4u], 3)} | {med([r['cost_usd'] for r in v0u], 3)} |")
L.append("\n이 비교에는 라우터 1단계 변경, 날짜·세션 간 변동이 함께 섞인다.\n")
L.append("## 비용 합계 (API 환산)\n")
L.append("| 항목 | $ |\n|---|---|")
L.append(f"| 본 실행 228세션 | {round(sum(r['cost_usd'] or 0 for r in rows), 2)} |")
L.append("| 확인 세션 2 + V2 CLAUDE.md 확인 호출 1(1턴, 도구 없음) | 0.53 + 0.05 |")
L.append("| 버린 옛 s4-t026 r2 4세션 | 1.16 |")
L.append("| 태스크 다시 쓰기(3회 호출 + 제목 누출 재작성 1) | 2.25 |")
L.append("| oracle 재라벨: 7개 1차 1.24(버림) + 7개 2차 0.56 + 2개 0.85 | 2.65 |")
L.append(f"| 4-0 보정 | {g40['cost_usd'] if g40 else '–'} |")
L.append("")
L.append("## 결론 (숫자만)\n")
fr = {v: sum(r["fired"] for r in by[v]) for v in V}
L.append(f"- 발화(57세션 중): V0 {fr['V0']}, V1 {fr['V1']}, V2 {fr['V2']}, V3 {fr['V3']}. V1 − V0와 V2 − V0는 태스크 19개 중 늘어남 9, 줄어듦 0(부호 검정 p 0.004). V3 − V0는 늘어남 4, 줄어듦 5(p 1.000).")
L.append(f"- V3의 발화 36 중 19는 (b) MCP 직접(ToolSearch 먼저)이었다. V0–V2의 (b)는 0이다.")
L.append(f"- 첫 도구가 탐색(Read·Grep·Bash)인 세션: V0 18, V1 2, V2 0, V3 20.")
L.append(f"- 로드한 세션의 적중(관련 1개 이상): V0 0.81, V1 0.78, V2 0.76, V3 0.76. 관련 없음 태스크 2개에서 search한 세션 중 1개 이상 로드: V0 3/3, V1 5/6, V2 6/6, V3 2/2.")
L.append(f"- 세션 비용 평균: V0 $0.396, V1 $0.455, V2 $0.533, V3 $0.384.")
L.append(f"- 4번째 쿼리가 요청 원문과 글자 그대로 같은 세션: 요청 400자 미만 100/120, 800자 이상 0/40.")
L.append(f"- 바뀌지 않은 10태스크의 발화: 4단계 E1 14/30, 5단계 V0 19/30.\n")
L.append("## 알려진 한계\n")
L.append("- 같은 모델, 반복 3회. 변형당 57세션이라 두 비율 차의 95% 오차는 약 ±0.18이다.")
L.append("- E1(깨끗한 환경)만 돌렸다. 사용자 전역 설정이 있는 환경(4단계 E2)에서는 재지 않았다.")
L.append("- oracle과 세션 모델이 같다(Opus 5.5). 3단계 GPT 교차 라벨의 관련 여부 kappa는 0.482였다(`stage3/report-cross-label.md`).")
L.append("- 다시 쓴 9개 중 5개는 같은 텍스트로 oracle을 두 번 돌렸는데, 4개의 관련 세트가 달랐다(`DESIGN.md`).")
L.append("- 작업 결과물은 채점하지 않았다. 발화 뒤의 작업 품질이 나아졌는지는 이 보고서로 알 수 없다.")
L.append("- 결과는 공개 이후 측정이다. numbers.md에서는 레포 세션의 \"after the post\" 규칙(§7 합계 밖 별도 행)으로 들어간다.")
S["fire"] = {v: sum(r["fired"] for r in by[v]) for v in V}
S["n"] = {v: len(by[v]) for v in V}
S["cost_total"] = round(sum(r["cost_usd"] or 0 for r in rows), 2)
(S5 / "summary.json").write_text(json.dumps(S, indent=1, ensure_ascii=False))
(S5 / "report-stage5.md").write_text("\n".join(L) + "\n")
print("\n".join(L[:60]))
