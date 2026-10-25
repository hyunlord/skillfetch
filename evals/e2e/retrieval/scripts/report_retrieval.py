#!/usr/bin/env python3
"""retrieval/report-retrieval.md from the eval outputs (bm25-ranks, picks-b, usecase-ranks, scores, pick-sizes)."""
import json
import statistics as st
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def jl(n):
    return [json.loads(l) for l in (R / n).read_text().splitlines() if l.strip()]


def short(i):
    return i.split("@")[0]


def main():
    ev = jl("retrieval-eval.jsonl")
    bm = {x["qid"]: x for x in jl("bm25-ranks.jsonl")}
    uc = {x["qid"]: x for x in jl("usecase-ranks.jsonl")}
    pk = json.loads((R / "picks-b.json").read_text())
    sc = jl("scores.jsonl")
    sz = [x["tokens_est"] for x in jl("pick-sizes.jsonl")]
    n = len(ev)
    hit_b = {q["qid"]: any(g in pk[q["qid"]]["ids"] for g in q["gold"]) for q in ev}

    def k_of(d, k):
        return sum(1 for x in d.values() if x["best_rank"] and x["best_rank"] <= k)

    in50 = k_of(bm, 50)
    L = ["# 검색 수리 — 평가 (세션 실행 없음)", "",
         "데이터: `retrieval-eval.jsonl` (정답 있음), `retrieval-nogold.jsonl` (정답 없음, 임계값용). 스크립트 `scripts/`. "
         "검색 코드 skillfetch `main@53b81df`(수정 없는 checkout에서 `uv run`), 인덱스 `~/.skillfetch/index` built_at "
         "2026-10-22T06:15:43Z(1단계·1b 세션과 같음). 재실행한 BM25 top-k가 41개 쿼리 모두 세션에 기록된 결과와 일치.", "",
         "## 평가 세트", "",
         f"- 1단계 C 30 run(전문가 태스크 15개 × 2) + 1b C 10 run = 40 run 중 search_skills를 부른 run은 {len({q['run'] for q in ev})}개, 쿼리 {n}개(run당 1회). "
         "부르지 않은 6 run: s1-fa-01-r2, s1-fa-04-r1, s1-fa-04-r2, s1-fa-05-r2, s1-fa-10-r2, s1-nx-10-r2. 그래서 40이 아니라 34.",
         "- 정답 = 그 태스크의 전문가 스킬 id(`tasks-stage1.yaml`, `tasks-1b.yaml`). 정답이 2개인 태스크(s1-fa-08, s1-nx-02)는 둘 중 하나라도 들면 적중. "
         "id가 같아야 적중 — 예: `uasl/frontend-design`(별도 id)은 `anthropics-skills/frontend-design` 적중으로 세지 않음.",
         f"- 정답 없는 5태스크의 쿼리 {len([x for x in sc if not x['has_gold']])}개는 임계값 분석에만 사용.", "",
         "## 세 방법 비교", "",
         "| 방법 | 정답 top-1 | 정답 top-3 (b: 고른 1~3개에 포함) | top-10 | top-50 | 비고 |",
         "|---|---|---|---|---|---|",
         f"| (a) 현행 BM25 | {k_of(bm,1)}/{n} | **{k_of(bm,3)}/{n} = {k_of(bm,3)/n:.2f}** | {k_of(bm,10)}/{n} = {k_of(bm,10)/n:.2f} | {in50}/{n} = {in50/n:.2f} | 랭킹에 아예 없음 {sum(1 for x in bm.values() if x['has_gold'] and not x['best_rank'])} (caveman 2) |",
         f"| (b) BM25 top-50 → 모델이 1~3개 선택 | - | **{sum(hit_b.values())}/{n} = {sum(hit_b.values())/n:.2f}** | - | - | 정답이 top-50에 있던 {in50}개 중 {sum(1 for q in ev if hit_b[q['qid']])}개 적중. 쿼리당 {st.mean(len(pk[q['qid']]['ids']) for q in ev):.2f}개 선택, 빈 선택 0 |",
         f"| (c) use_case 태그 필터 → BM25 | {k_of(uc,1)}/{n} | **{k_of(uc,3)}/{n} = {k_of(uc,3)/n:.2f}** | {k_of(uc,10)}/{n} = {k_of(uc,10)/n:.2f} | - | 필터로 정답이 빠짐 {sum(1 for x in uc.values() if x['best_rank'] is None)} |",
         "",
         f"구현 조건(b 또는 c의 top-3 ≥ 0.7): **미충족** — (b) {sum(hit_b.values())/n:.2f}, (c) {k_of(uc,3)/n:.2f}. "
         "(b)의 상한은 정답이 BM25 top-50에 드는 비율 " f"{in50/n:.2f}.", "",
         "### (b) 비용: 쿼리당 요약 50개", "",
         f"- `id — title: summary` 50줄 블록: 토큰(문자/4, skillfetch `token_estimate`와 같은 추정) 최소 {min(sz)} · 중앙 {int(st.median(sz))} · 최대 {max(sz)}.",
         "- 참고: 현행 search_skills JSON 응답(tags·match_reasons 포함) k=10 중앙 2,257, k=50 중앙 9,909 (최소 8,481, 최대 11,597).", "",
         "### (c) 태그", "",
         "- 태그 15개: `use-case-tags.md`. 인덱스의 tier A/B canonical 1489개 모두에 1~3개(1개 1098, 2개 353, 3개 38).",
         "- 분포: other 1081, ui-component 148, planning 121, code-review 77, data-ai 74, devops 67, testing 64, security-review 63, refactor 49, docs 47, debugging 45, landing-page 35, api-endpoint 21, database 18, concise-output 8.",
         "- 쿼리 용례 분포(정답 있는 34 + 없는 7): testing 10, ui-component 7, refactor 7, debugging 4, landing-page 4, api-endpoint 3, database 2, docs 2, planning 2.",
         "- 결과물: `use-cases.json`(스킬 → 태그), `query-use-cases.json`. 인덱스 파일(`~/.skillfetch/index`)에는 쓰지 않았다 — 평가는 사이드카 파일로 필터.", "",
         "## 임계값: top-1 점수로 '아무것도 로드하지 않음'", "",
         "search_skills는 점수를 반환하지 않는다. `scripts/scores.py`가 Searcher.search와 같은 계산(BM25 × 프로필 부스트)으로 재계산, top-10이 실제 결과와 같음을 assert.", "",
         "| 쿼리 | n | top-1 점수 (정렬) |", "|---|---|---|",
         f"| 정답 있음 | {sum(x['has_gold'] for x in sc)} | {', '.join(f'{v:.1f}' for v in sorted(x['top1'] for x in sc if x['has_gold']))} |",
         f"| 정답 없음 | {sum(not x['has_gold'] for x in sc)} | {', '.join(f'{v:.1f}' for v in sorted(x['top1'] for x in sc if not x['has_gold']))} |",
         "", "| 임계값 (top-1 < t면 로드 안 함) | 정답 없는 쿼리 중 로드 안 함 | 정답 있는 쿼리 중 로드 안 함 |", "|---|---|---|"]
    g = [x["top1"] for x in sc if x["has_gold"]]
    ng = [x["top1"] for x in sc if not x["has_gold"]]
    for t in (32.0, 35.0, 38.7, 45.0, 51.3, 53.7):
        L.append(f"| {t} | {sum(v < t for v in ng)}/{len(ng)} | {sum(v < t for v in g)}/{len(g)} |")

    def auc(p, q):
        return sum((a > b) + 0.5 * (a == b) for a in p for b in q) / (len(p) * len(q))
    L += ["", f"- AUC(정답 있음 > 없음): top-1 점수 {auc(g, ng):.2f}, top-1/쿼리 토큰 수 "
          f"{auc([x['top1']/x['query_tokens'] for x in sc if x['has_gold']], [x['top1']/x['query_tokens'] for x in sc if not x['has_gold']]):.2f}, "
          f"top-1 − top-10 {auc([x['top1']-x['top10'] for x in sc if x['has_gold']], [x['top1']-x['top10'] for x in sc if not x['has_gold']]):.2f}.",
          "- 정답 없는 쿼리의 최고 점수(78.0, s1-nx-05-r2, top-1 vercel-react-best-practices)가 정답 있는 쿼리 34개 전부보다 높다. 정답 있는 쿼리 중 top-1이 정답인 것은 5개.",
          "- 규칙은 라우터에 넣지 않았다(구현 조건 미충족으로 search_skills·라우터 변경 없음).", "",
          "## 쿼리별", "",
          "| qid | 정답 | (a) BM25 순위 | (b) 고른 스킬 | (b) | (c) 용례 · 후보 수 | (c) 순위 | top-1 점수 |",
          "|---|---|---|---|---|---|---|---|"]
    scm = {x["qid"]: x for x in sc}
    for q in ev:
        qid = q["qid"]
        a = ", ".join(f"{short(g)} {r if r else '-'}" for g, r in bm[qid]["gold_ranks"].items())
        c = ", ".join(f"{short(g)} {r if r else '-'}" for g, r in uc[qid]["gold_ranks"].items())
        L.append(f"| {qid} | {', '.join(map(short, q['gold']))} | {a} | {', '.join(map(short, pk[qid]['ids']))} | "
                 f"{'적중' if hit_b[qid] else '-'} | {uc[qid]['use_case']} · {uc[qid]['pool']} | {c} | {scm[qid]['top1']:.1f} |")
    L += ["", "## 진행 방식과 공개 사항", "",
          "- (b)의 선택, (c)의 스킬 태그·쿼리 용례는 이 세션이 아니라 **정답을 모르는 하위 에이전트**(같은 모델, Opus 5.5)가 했다. 이 세션은 정답(전문가 스킬)을 알고 있어서 직접 하면 결과가 정답 쪽으로 기운다. "
          "하위 에이전트에게는 입력 파일만 줬다(정답·조건·실험 목적 없음, 다른 파일 열지 말 것). 입력: (b) 저장소 설명 + 사용자 태스크 원문 + 보낸 쿼리 + top-50(id·title·summary, 순위순), 4묶음. "
          "(c) 태그 정의 + 스킬별 id·title·summary·keywords, 4묶음; 쿼리 용례는 태그 정의 + 태스크 원문 + 쿼리.",
          "- 판정자 대신 하위 에이전트를 쓴 것은 지시(\"네가\")와 다르다.",
          "- (b)는 정답이 없는 7개 쿼리에 대해서는 돌리지 않았다.",
          "- 같은 쿼리의 run 2개는 쿼리 문장이 비슷해 독립 표본이 아니다(태스크 기준으로는 정답 있는 태스크 20개).",
          "- 1단계·1b 보고서의 '중앙 턴'은 반올림 값이었다(1단계 A 14 → 실제 14.5, 1b A 20 → 19.5). numbers.md §11은 실제 값."]
    (R / "report-retrieval.md").write_text("\n".join(L) + "\n")
    print(R / "report-retrieval.md")


if __name__ == "__main__":
    main()
