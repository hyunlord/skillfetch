#!/usr/bin/env python3
"""report-6b.md: tables 1-4 and the DESIGN.md §5 verdict, from sessions.jsonl and judge/scores-p{1,2}.jsonl."""
import json
import statistics as st
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
jl = lambda p: [json.loads(l) for l in p.open() if l.strip()]  # noqa: E731
sess = jl(S6B / "sessions.jsonl")
tasks = {t["id"]: t for t in jl(S6B / "tasks.jsonl")}
sc = {p: {(r["task"], r["cond"], r["rep"]): r for r in jl(S6B / "judge" / f"scores-{p}.jsonl")} for p in ("p1", "p2")}
C = ("A", "C0", "Cb")
B = (1, 2, 3)


def in_verdict(r):  # §5.5: bundle-(3) tasks with relevant skills found are excluded
    return not (r["bundle"] == 3 and r["relevant_found"])


def sel(b, c, verdict=True):
    return [r for r in sess if r["bundle"] == b and r["cond"] == c and (in_verdict(r) or not verdict)]


def score(r, p=None):
    k = (r["task"], r["cond"], r["rep"])
    if p:
        return sc[p][k]["score"]
    return (sc["p1"][k]["score"] + sc["p2"][k]["score"]) / 2


mean = lambda xs: round(st.mean(xs), 3) if xs else None  # noqa: E731
med = lambda xs: st.median(xs) if xs else None  # noqa: E731
S = {(b, c): mean([score(r) for r in sel(b, c)]) for b in B for c in C}
P = {(b, c, p): mean([score(r, p) for r in sel(b, c)]) for b in B for c in C for p in ("p1", "p2")}
D = {b: round(max(abs(P[(b, c, "p1")] - P[(b, c, "p2")]) for c in C), 3) for b in B}
T = {(b, c): med([r["turns"] for r in sel(b, c)]) for b in B for c in C}
K = {(b, c): med([r["input_tokens"] for r in sel(b, c)]) for b in B for c in C}
reject = S[(1, "Cb")] <= S[(1, "C0")] - 0.3
cond = {b: {"T": T[(b, "Cb")] < T[(b, "C0")], "K": K[(b, "Cb")] < K[(b, "C0")], "S": S[(b, "Cb")] >= S[(b, "C0")] - D[b]} for b in (2, 3)}
adopt = not reject and all(all(v.values()) for v in cond.values())
verdict = "기각" if reject else ("채택" if adopt else "보류")
L = ["# 6b — 효과 게이트 결과 (report)\n",
     "설계와 판정 규칙은 `../DESIGN.md`(§5는 실행 전 고정), 파일럿은 `report-pilot.md`, 해시는 `FROZEN.sha256`에 있다. 세션 행은 `sessions.jsonl`, 판정 점수는 `judge/scores-p{1,2}.jsonl`이다.\n",
     f"## 판정: **{verdict}**\n",
     "| 규칙 | 값 | 성립 |\n|---|---|---|",
     f"| 기각: S(Cb,1) ≤ S(C0,1) − 0.3 | S(Cb,1) {S[(1, 'Cb')]} · S(C0,1) {S[(1, 'C0')]} · 차 {S[(1, 'Cb')] - S[(1, 'C0')]:+.3f} | {'예' if reject else '아니오'} |"]
for b in (2, 3):
    L.append(f"| ({b}) T(Cb) < T(C0) (턴 중앙) | {T[(b, 'Cb')]} vs {T[(b, 'C0')]} | {'예' if cond[b]['T'] else '아니오'} |")
    L.append(f"| ({b}) K(Cb) < K(C0) (입력 토큰 중앙) | {K[(b, 'Cb')]:,.0f} vs {K[(b, 'C0')]:,.0f} | {'예' if cond[b]['K'] else '아니오'} |")
    L.append(f"| ({b}) S(Cb) ≥ S(C0) − D | {S[(b, 'Cb')]} vs {S[(b, 'C0')]} − D {D[b]} = {S[(b, 'C0')] - D[b]:.3f} | {'예' if cond[b]['S'] else '아니오'} |")
excl = sorted({r["task"] for r in sess if not in_verdict(r)})
L.append(f"\n판정에서 뺀 태스크(§5.5, 묶음 (3)에서 관련 생김): {', '.join(excl) or '없음'}. 아래 표 1–3은 판정 대상만, 표 1b는 그 태스크를 따로 보인다.\n")
L.append("## 표 1. 묶음 × 조건\n")
L.append("| 묶음 | 조건 | n | 점수 (p1 / p2) | 체크 통과 | 턴 중앙 (평균) | 입력 토큰 중앙 | 비용 중앙 $ | 발화 | 로드 ≥1 | 로드 수 평균 |\n|---|---|---|---|---|---|---|---|---|---|---|")
for b in B:
    for c in C:
        rs = sel(b, c)
        L.append(f"| ({b}) | {c} | {len(rs)} | {S[(b, c)]} ({P[(b, c, 'p1')]} / {P[(b, c, 'p2')]}) | {sum(bool(r['check_pass']) for r in rs)}/{len(rs)} | "
                 f"{T[(b, c)]} ({mean([r['turns'] for r in rs])}) | {K[(b, c)]:,.0f} | {med([r['cost_usd'] for r in rs]):.3f} | "
                 f"{sum(r['fired'] for r in rs)}/{len(rs)} | {sum(r['n_loaded'] > 0 for r in rs)}/{len(rs)} | {mean([r['n_loaded'] for r in rs])} |")
if excl:
    L.append("\n### 표 1b. 판정에서 뺀 태스크\n")
    L.append("| 태스크 | 조건 | n | 점수 (p1 / p2) | 체크 통과 | 턴 중앙 | 입력 토큰 중앙 | 로드 ≥1 |\n|---|---|---|---|---|---|---|---|")
    for t in excl:
        for c in C:
            rs = [r for r in sess if r["task"] == t and r["cond"] == c]
            L.append(f"| {t} | {c} | {len(rs)} | {mean([score(r) for r in rs])} ({mean([score(r, 'p1') for r in rs])} / {mean([score(r, 'p2') for r in rs])}) | "
                     f"{sum(bool(r['check_pass']) for r in rs)}/{len(rs)} | {med([r['turns'] for r in rs])} | {med([r['input_tokens'] for r in rs]):,.0f} | {sum(r['n_loaded'] > 0 for r in rs)}/{len(rs)} |")
L.append("\n## 표 2. 태스크별 점수 평균 (두 판정 평균) · 턴 중앙\n")
L.append("| 묶음 | 태스크 | " + " | ".join(f"{c} 점수" for c in C) + " | " + " | ".join(f"{c} 턴" for c in C) + " |\n|---|---|" + "---|" * 6)
for t, tt in tasks.items():
    rs = {c: [r for r in sess if r["task"] == t and r["cond"] == c] for c in C}
    L.append(f"| ({tt['bundle']}) | {t}{' (판정 제외)' if t in excl else ''} | " + " | ".join(str(mean([score(r) for r in rs[c]])) for c in C) + " | "
             + " | ".join(str(med([r['turns'] for r in rs[c]])) for c in C) + " |")
L.append("\n## 표 3. 로드 세트 (C0 · Cb; 세션별 로드한 스킬)\n")
L.append("| 태스크 | 조건 | r1 | r2 | r3 |\n|---|---|---|---|---|")
for t in tasks:
    for c in ("C0", "Cb"):
        cells = []
        for k in ("r1", "r2", "r3"):
            r = next((x for x in sess if x["task"] == t and x["cond"] == c and x["rep"] == k), None)
            cells.append("–" if r is None else (", ".join(s.split("/")[-1].split("@")[0] for s in r["loaded"]) or ("없음" + (" (발화)" if r["fired"] else ""))))
        L.append(f"| {t} | {c} | " + " | ".join(cells) + " |")
L.append("\n## 표 4. 판정 일치 (p1 vs p2, 같은 루브릭, 새 코드·새 판정자)\n")
L.append("| 묶음 | n | 세션 점수 일치 | 평균 절대 차 | 최대 차 | D(b) = 조건 평균 차 최대 |\n|---|---|---|---|---|---|")
for b in B:
    rs = [r for r in sess if r["bundle"] == b and in_verdict(r)]
    d = [abs(score(r, "p1") - score(r, "p2")) for r in rs]
    L.append(f"| ({b}) | {len(rs)} | {sum(x == 0 for x in d)}/{len(rs)} | {mean(d)} | {max(d)} | {D[b]} |")
L.append("\n## 실행 기록\n")
L.append("- **1차 큐(108세션 중 39세션 유효)**: 02:03 KST부터 세션이 1턴 $0으로 끝났다. 결과는 \"You've hit your org's monthly spend limit\"였다(69세션). 그 계정의 한도 소진 때문이고, 세션이 작업을 시작하지 못한 하네스 실패라 §5.6에 따라 제외했다. 출력은 `runs/_spendlimit/`에 있다.")
L.append("- **2차 큐(계정 전환 뒤, 69세션 재실행 중 22세션 유효)**: 47세션이 \"You've hit your session limit · resets 3:10am\"로 1턴 $0에 끝났다. 같은 방식으로 제외했다(`runs/_sessionlimit/`).")
L.append("- **3차 큐**: 나머지 47세션을 재실행했다. 사용량 한도 메시지는 0건이었고, 108/108 모두 `success`이며 1턴 $0 세션은 0이다.")
L.append("- **세션별 계정**: 처음 39세션과 재실행 69세션은 서로 다른 로그인 계정에서 돌았다. 큐 순서는 처음과 같다(`runs/_queue.txt`, 고정 시드). 재실행은 (태스크, 반복, 조건) 단위로 빠진 것만 다시 돌렸다.")
L.append("- **파일럿**: 조건 A의 skill 목록에 메인 체크아웃의 옛 라우터가 보였다. 메인 체크아웃을 `s6b-a`로 바꿔 고쳤다(`report-pilot.md`).")
L.append("- **판정**: 24패스(12 세트 × p1·p2), 각 패스는 새 하위 에이전트이고 루브릭과 세트 폴더만 받았다. 형식 검증 뒤에 키를 읽었다(`scripts/unblind_6b.py`).")
cost = sum(r["cost_usd"] or 0 for r in sess)
L.append(f"\n## 비용\n\n본 실행 {len(sess)}세션 ${cost:.2f}(API 환산). 파일럿은 `report-pilot.md`.\n")
(S6B / "report-6b.md").write_text("\n".join(L) + "\n")
(S6B / "verdict.json").write_text(json.dumps({"verdict": verdict, "reject": reject, "conds": cond, "S": {f"{b}|{c}": S[(b, c)] for b in B for c in C},
                                              "D": D, "T": {f"{b}|{c}": T[(b, c)] for b in B for c in C}, "K": {f"{b}|{c}": K[(b, c)] for b in B for c in C}}, indent=1))
print("\n".join(L[:14]))
