#!/usr/bin/env python3
"""retrieval/report-embedding.md: (a) BM25, (b) BM25 top-50 + pick, (i) embedding, (ii) RRF, (ii)+pick. Table only."""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def main():
    ev = [json.loads(l) for l in (R / "retrieval-eval.jsonl").read_text().splitlines()]
    er = {x["qid"]: x for x in map(json.loads, (R / "emb-ranks.jsonl").read_text().splitlines())}
    pb = json.loads((R / "picks-b.json").read_text())
    pr = json.loads((R / "picks-rrf.json").read_text())
    tm = json.loads((R / "emb-timing.json").read_text())
    n = len(ev)

    def k_of(key, k):
        return sum(1 for q in ev if er[q["qid"]][key] and er[q["qid"]][key] <= k)

    def pick_hits(p):
        return sum(1 for q in ev if any(g in p[q["qid"]]["ids"] for g in q["gold"]))

    def cell(h):
        return f"{h}/{n} = {h / n:.2f}"
    L = ["# 임베딩 오프라인 평가 (세션 아님, 런타임 코드 변경 없음)", "",
         "34쿼리(`retrieval-eval.jsonl`), 정답 = 전문가 스킬 id. 스크립트 `scripts/eval_embed.py`, `scripts/report_embed.py`.", "",
         "| 방법 | top-3 | top-10 | top-50 |", "|---|---|---|---|",
         f"| (a) BM25 (현행 순위) | {cell(k_of('bm25_best', 3))} | {cell(k_of('bm25_best', 10))} | {cell(k_of('bm25_best', 50))} |",
         f"| (i) 임베딩 단독 | {cell(k_of('emb_best', 3))} | {cell(k_of('emb_best', 10))} | {cell(k_of('emb_best', 50))} |",
         f"| (ii) BM25 + 임베딩 RRF (k=60) | {cell(k_of('rrf_best', 3))} | {cell(k_of('rrf_best', 10))} | {cell(k_of('rrf_best', 50))} |",
         f"| (b) BM25 top-50 → 1~3개 선택 | {cell(pick_hits(pb))} | - | - |",
         f"| (ii) RRF top-50 → 1~3개 선택 | {cell(pick_hits(pr))} | - | - |", "",
         "선택 행의 top-3 = 하위 에이전트(정답 비공개, 같은 프롬프트·형식)가 고른 1~3개에 정답 포함.", "",
         "## 비용", "",
         "| 항목 | 값 |", "|---|---|",
         f"| 모델 | `{tm['model']}`, 파라미터 {tm['params']:,}, 차원 {tm['dim']}, max_seq_length {tm['max_seq_length']} |",
         f"| 모델 크기 (HF 캐시) | {tm['model_cache_bytes'] / 1e6:.1f} MB |",
         f"| 임베딩 저장 (float32, {tm['docs']}×{tm['dim']}) | {tm['embeddings_bytes_float32'] / 1e6:.2f} MB |",
         f"| 인덱싱 시간 ({tm['docs']}개 인코딩, CPU {tm['cpu']}코어, batch 64) | {tm['index_s']} s |",
         f"| 모델 로드 (import 포함) | {tm['model_load_s']} s |",
         f"| 쿼리 지연 (인코딩 + 코사인 {tm['docs']}개) | 중앙 {tm['query_latency_ms']['median']} ms, 최대 {tm['query_latency_ms']['max']} ms |",
         f"| 256 토큰 넘어 잘린 문서 | {tm['docs_truncated']}/{tm['docs']} |",
         "| 런타임 의존성 | sentence-transformers + torch (스크래치 venv에 설치; skillfetch 의존성 아님) |", "",
         "## 쿼리별 정답 순위", "",
         "| qid | 정답 | BM25 | 임베딩 | RRF | (b) 선택 | RRF 선택 |", "|---|---|---|---|---|---|---|"]
    s = lambda i: i.split("@")[0]  # noqa: E731
    for q in ev:
        x = er[q["qid"]]
        hit = lambda p: "적중" if any(g in p[q["qid"]]["ids"] for g in q["gold"]) else ", ".join(map(s, p[q["qid"]]["ids"]))  # noqa: E731
        L.append(f"| {q['qid']} | {', '.join(map(s, q['gold']))} | {x['bm25_best'] or '-'} | {x['emb_best'] or '-'} | "
                 f"{x['rrf_best'] or '-'} | {hit(pb)} | {hit(pr)} |")
    L += ["", "## 기록 사항", "",
          "- 문서 텍스트 = title + description + summary + synthetic_queries (줄바꿈으로 연결). 임베딩은 프로필 부스트 없음; RRF의 BM25 쪽은 search_skills 순위(프로필 부스트 포함) 그대로. BM25 히트가 없는 스킬은 임베딩 순위만 기여.",
          "- 모델은 Hugging Face에서 한 번 내려받음(외부 API 호출 아님). 측정은 이 Mac의 CPU.",
          "- RRF 선택은 (b)와 같은 지시문·같은 입력 형식(태스크 원문, 쿼리, 50개 id·title·전체 summary)으로 새 하위 에이전트 4개가 수행."]
    (R / "report-embedding.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
