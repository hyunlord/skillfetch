#!/usr/bin/env python3
"""report-stage3.md from the frozen stage-3 files. Numbers only."""
import json
from collections import defaultdict
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]


def jl(n):
    return [json.loads(l) for l in (S3 / n).open()]


def short(i):
    return str(i).split("@")[0]


def f3(x):
    return "-" if x is None else f"{x:.3f}"


def main():
    tasks = {t["id"]: t for t in jl("tasks.jsonl")}
    orc = {o["id"]: o for o in jl("oracle.jsonl")}
    q = {x["id"]: x for x in jl("queries.jsonl")}
    rs = json.loads((S3 / "retrieval-summary.json").read_text())
    ss = json.loads((S3 / "selection-summary.json").read_text())
    sev = {x["id"]: x for x in jl("selection-eval.jsonl")}
    rk = json.loads((S3 / "rankings.json").read_text())
    pe = json.loads((S3 / "pool-expansion.json").read_text())
    la = json.loads((S3 / "label-agreement.json").read_text())
    tm = json.loads((S3 / "rank-timing.json").read_text())
    L = ["# skillfetch 3단계 — 검색·선택 품질 광범위 평가 (report)", ""]
    hdr = S3 / "report-header.md"
    if hdr.exists():
        L += [hdr.read_text().rstrip(), ""]

    # coverage
    L += ["## 커버리지: 작업종류별로 index에 관련 스킬(등급≥2)이 있는 태스크", "",
          "관련 스킬이 없는 일반 태스크는 'index에 해당 스킬이 없음' 결과이며, 검색 지표와 선택 precision/recall 계산에서 제외했다(선택의 과잉 로드·none 정확도에는 포함).", "",
          "| 작업종류 | 태스크 | 관련 없음 (v1: 2b 풀) | 관련 없음 (v2: 3-0 확장 후) | 관련 스킬 평균 (v2) | 프로세스성 관련이 있는 태스크 (v2) |", "|---|---|---|---|---|---|"]
    by = defaultdict(list)
    for t in tasks.values():
        if not t["expect_none"]:
            by[t["task_type"]].append(orc[t["id"]])
    for tt, v in by.items():
        L.append(f"| {tt} | {len(v)} | {sum(1 for o in v if not o['relevant_v1'])} | {sum(1 for o in v if not o['relevant'])} | "
                 f"{sum(len(o['relevant']) for o in v) / len(v):.2f} | {sum(1 for o in v if o['relevant_process'])} |")
    allv = [o for v in by.values() for o in v]
    L.append(f"| **전체(일반)** | {len(allv)} | {sum(1 for o in allv if not o['relevant_v1'])} | {sum(1 for o in allv if not o['relevant'])} | "
             f"{sum(len(o['relevant']) for o in allv) / len(allv):.2f} | {sum(1 for o in allv if o['relevant_process'])} |")
    en = [orc[t["id"]] for t in tasks.values() if t["expect_none"]]
    L += ["", f"expect_none 40개 중 관련 스킬이 붙은 태스크: v1 {sum(1 for o in en if o['relevant_v1'])}, v2 {sum(1 for o in en if o['relevant'])}.", ""]

    # pool expansion
    L += ["## 3-0 풀 보정 (Q2·Q3·MiniLM·RRF top-10 추가 채점)", "",
          f"추가 채점 {pe['added']}개(태스크 {pe['tasks_with_new_candidates']}개), 그중 등급≥2 **{pe['added_relevant']}개** "
          f"(등급 분포 0/1/2/3 = {'/'.join(str(pe['grade_dist_added'][str(g)] if str(g) in pe['grade_dist_added'] else pe['grade_dist_added'].get(g, 0)) for g in range(4))}). "
          f"관련 쌍 {pe['relevant_v1']} → {pe['relevant_v2']} (+{(pe['relevant_v2'] - pe['relevant_v1']) / pe['relevant_v1']:.0%}); 처음으로 관련 스킬이 생긴 태스크 {pe['tasks_gaining_first_relevant']}개. "
          "원래 풀(2a ∪ BM25 원문 top-10 ∪ 무작위 2)이 BM25 원문 쿼리 쪽으로 치우쳐 있었다는 근거다. 아래 모든 지표는 v2 라벨 기준.", "",
          "| 추가 출처(top-10) | 새로 채점 | 그중 등급≥2 |", "|---|---|---|"]
    for m, c in pe["by_method"].items():
        L.append(f"| {m} | {c['added']} | {c.get('relevant', 0)} |")
    L += ["", f"라벨 일치(2c, 40태스크 500쌍): 완전 {la['exact']:.1%}, ±1 {la['within_1']:.1%}, 관련 여부 kappa {la['relevant_kappa']}.", ""]

    # table 1
    o = rs["overall"]
    rows = [("Q1 원문", "BM25", "bm25_q1"), ("Q1 원문", "MiniLM", "emb_q1"), ("Q1 원문", "BM25+MiniLM RRF", "rrf_q1"),
            ("Q2 재진술", "BM25", "bm25_q2"), ("Q2 재진술", "MiniLM", "emb_q2"), ("Q2 재진술", "BM25+MiniLM RRF", "rrf_q2"),
            ("Q3 다중쿼리(3문장 RRF)", "BM25", "bm25_q3")]
    n_all, n_2a, n_p = o["bm25_q1|all|50"]["n"], o["bm25_q1|2a|50"]["n"], o["bm25_q1|process|50"]["n"]
    L += ["## 표 1. 검색 recall@10 / @50", "",
          f"(i) 전체 관련 세트(등급≥2, n={n_all}태스크) · (ii) 2a 출처 관련 스킬만(검색과 독립, n={n_2a}) · 프로세스성 관련 스킬만(n={n_p}). 태스크별 recall의 평균. "
          "(i)과 (ii)의 차이가 @50에서 최대 0.07이라 (i)을 주 지표로 두었다. Q3 × MiniLM은 지시 범위 밖이라 계산하지 않았다.", "",
          "| 쿼리 | 방법 | (i) @10 | (i) @50 | (ii) @10 | (ii) @50 | 프로세스 @10 | 프로세스 @50 |", "|---|---|---|---|---|---|---|---|"]
    for qn, mn, key in rows:
        c = lambda k, cut: f3(o[f"{key}|{k}|{cut}"]["mean"])  # noqa: E731
        L.append(f"| {qn} | {mn} | {c('all', 10)} | {c('all', 50)} | {c('2a', 10)} | {c('2a', 50)} | {c('process', 10)} | {c('process', 50)} |")
    for axis, label in (("task_type", "작업종류"), ("stack", "스택"), ("phrasing", "표현")):
        L += ["", f"### 표 1-{label}: (i) recall@50 (괄호 안 n)", "", "| " + label + " | n | Q1 BM25 | Q2 BM25 | Q3 BM25 | Q2 MiniLM | Q2 RRF |", "|---|---|---|---|---|---|---|"]
        for g, a in rs["by"][axis].items():
            if a["bm25_q1|all|50"]["n"] == 0:
                continue
            L.append(f"| {g} | {a['bm25_q1|all|50']['n']} | " + " | ".join(f3(a[f"{m}|all|50"]["mean"]) for m in ("bm25_q1", "bm25_q2", "bm25_q3", "emb_q2", "rrf_q2")) + " |")
    L += ["", f"MiniLM 비용: 모델 {tm['model_cache_mb']} MB(HF 캐시), 임베딩 {tm['docs']}개 계산 {tm['index_embed_s']} s(CPU), 저장 {tm['embeddings_mb_float32']} MB(float32), "
          f"모델 로드 {tm['model_load_s']} s, 쿼리당 {tm['emb_query_ms_median']} ms(중앙; BM25 {tm['bm25_query_ms_median']} ms), 256토큰 넘어 잘린 문서 {tm['truncated_docs']}.", ""]

    # table 2
    s = ss["overall"]
    p = ss["pairs"]
    L += ["## 표 2. 선택 (Q2 top-50 compact → 1–3개 또는 none, 라우터 4단계·skip 규칙 그대로)", "",
          "| 지표 | 값 |", "|---|---|",
          f"| precision (선택 세트 중 등급≥2) | {f3(s['precision'])} (n={s['precision_n']}) |",
          f"| recall (관련 세트 중 선택된 비율) | {f3(s['recall'])} (n={s['recall_n']}) |",
          f"| 적중 (관련 1개 이상 선택) | {f3(s['hit_rate'])} (n={s['recall_n']}) |",
          f"| 태스크당 로드 수 | {f3(s['mean_loaded'])} |",
          f"| 잘못 로드(등급<2) | {s['wrong_loads_total']}개, {s['tasks_with_wrong_load']}태스크 |",
          f"| 과잉 로드 (oracle 관련 없음인데 로드) | {s['over_load_tasks']}태스크 |",
          f"| none 정확도 — oracle 기준 (관련 없음 {s['none_acc_oracle_n']}태스크) | {f3(s['none_acc_oracle'])} |",
          f"| none 정확도 — expect_none 기준 (40태스크) | {f3(s['none_acc_expect_none'])} |",
          f"| 방향 쌍: 세트가 바뀜 | {p['selection_changed']}/{p['pairs']} (oracle 세트가 다른 쌍 {p['oracle_sets_differ']}) |",
          f"| 방향 쌍: 방향대로 바뀜 | {p['moved_with_direction']}/{p['pairs']} |", ""]
    L += ["| 표현 | 태스크 | precision | recall | 적중 | 과잉 로드 | none 정확도(oracle) |", "|---|---|---|---|---|---|---|"]
    for g, a in ss["by"]["phrasing"].items():
        L.append(f"| {g} | {a['tasks']} | {f3(a['precision'])} | {f3(a['recall'])} | {f3(a['hit_rate'])} | {a['over_load_tasks']} | {f3(a['none_acc_oracle'])} |")

    # table 3
    cls_order = ["ok", "select_fail", "restate_fail", "search_fail", "over_load"]
    L += ["", "## 표 3. 실패 분류", "",
          "ok = 관련 세트가 없고 아무것도 안 고름, 또는 관련 1개 이상 고름 · select_fail = 관련 스킬이 Q2 top-50에 있는데 안 고름 · restate_fail = Q2 top-50 밖, Q1 또는 Q3 top-50 안 · "
          "search_fail = 어느 쿼리로도 top-50 밖 · over_load = 관련 없음인데 로드.", "",
          "| 층 | 그룹 | n | " + " | ".join(cls_order) + " |", "|---|---|---|" + "---|" * len(cls_order)]
    L.append("| 전체 | - | " + str(s["tasks"]) + " | " + " | ".join(str(s["classes"].get(c, 0)) for c in cls_order) + " |")
    for axis, label in (("task_type", "작업종류"), ("stack", "스택"), ("phrasing", "표현")):
        for g, a in ss["by"][axis].items():
            L.append(f"| {label} | {g} | {a['tasks']} | " + " | ".join(str(a["classes"].get(c, 0)) for c in cls_order) + " |")
    L += ["", "### 분류별 대표 사례 3개", ""]
    for c in ["select_fail", "restate_fail", "search_fail", "over_load"]:
        L += [f"#### {c}", ""]
        ex = [x for x in sev.values() if x["class"] == c][:3]
        for x in ex:
            tid = x["id"]
            rel = x["relevant"]
            ranks = "; ".join(f"`{short(r)}` Q1 #{(rk[tid]['bm25_q1'].index(r) + 1) if r in rk[tid]['bm25_q1'] else '>50'}, Q2 #{(rk[tid]['bm25_q2'].index(r) + 1) if r in rk[tid]['bm25_q2'] else '>50'}, Q3 #{(rk[tid]['bm25_q3'].index(r) + 1) if r in rk[tid]['bm25_q3'] else '>50'}" for r in rel) or "-"
            L += [f"- **{tid}** ({tasks[tid]['task_type']}, {tasks[tid]['stack']}, {tasks[tid]['phrasing']})", f"  - 태스크: {tasks[tid]['text'][:400].replace(chr(10), ' / ')}",
                  f"  - Q2: {q[tid]['q2']}", f"  - 선택: {', '.join('`' + short(i) + '`' for i in x['selected']) or 'none'}",
                  f"  - oracle 관련(등급≥2)과 순위: {ranks}", ""]

    # table 4
    runs4 = [(n, json.loads((S3 / f"e2e{x}-summary.json").read_text()), jl(f"e2e{x}.jsonl"))
             for n, x in (("run 1: 빈 레포", ""), ("run 2: 스텁 레포", "-stub")) if (S3 / f"e2e{x}-summary.json").exists()]
    if runs4:
        L += ["## 표 4. e2e 40세션 vs 오프라인 선택", "",
              "같은 40태스크를 실제 Claude Code 세션(skillfetch MCP + 라우터 main 64f4bd8, --max-turns 12)으로 돌려 실제 load_skills 결과를 오프라인 선택(표 2)과 비교. 작업 결과물은 채점하지 않았다. "
              "run 1은 라우터·.mcp.json만 있는 빈 레포, run 2는 태스크가 이름을 댄 파일·디렉터리와 스택별 소스 파일 1개를 빈 스텁으로 만든 레포(manifest·lockfile 없음 → profile_repo 결과는 빈 프로필, 오프라인과 같음). "
              "세션이 search를 안 하면 로드 세트는 빈 집합으로 비교했다.", "",
              "| 지표 | " + " | ".join(n for n, _, _ in runs4) + " |", "|---|" + "---|" * len(runs4)]
        for key, label in (("router_fired", "라우터 발화"), ("searched", "search 호출"), ("loaded_any", "1개 이상 로드"), ("identical_set", "로드 세트 완전 일치 (40 기준)"),
                           ("mean_jaccard", "평균 Jaccard (40 기준)"), ("none_agree", "none/로드 여부 일치"), ("hit_agree", "관련 적중 여부 일치"), ("class_agree", "실패 분류 일치")):
            L.append(f"| {label} | " + " | ".join(str(e[key]) for _, e, _ in runs4) + " |")
        for key, label in (("sessions", "search한 세션"), ("identical_set", "그중 세트 완전 일치"), ("mean_jaccard", "그중 평균 Jaccard"), ("class_agree", "그중 분류 일치"),
                           ("mean_top50_jaccard_vs_offline_q2", "그중 search 결과 top-50 vs 오프라인 Q2 top-50 Jaccard")):
            L.append(f"| {label} | " + " | ".join(str(e["searched_only"].get(key, "-")) for _, e, _ in runs4) + " |")
        L.append("| search 안 한 세션의 첫 도구 | " + " | ".join(", ".join(f"{k} {v}" for k, v in sorted(e["first_tool_when_not_searched"].items(), key=lambda x: -x[1])) for _, e, _ in runs4) + " |")
        name, e2s, e2 = runs4[-1]
        L += ["", f"{name}, 오프라인 분류별:", "", "| 오프라인 분류 | n | 세트 완전 일치 | 분류 일치 | 평균 Jaccard |", "|---|---|---|---|---|"]
        for c, v in e2s["by_offline_class"].items():
            L.append(f"| {c} | {v['n']} | {v['identical']} | {v['class_agree']} | {v['mean_jaccard']} |")
        L += ["", f"{name}, 세션별:", "", "| 태스크 | 오프라인 분류 | e2e 분류 | 오프라인 선택 | e2e 로드 | e2e 쿼리 |", "|---|---|---|---|---|---|"]
        for x in e2:
            L.append(f"| {x['id']} | {x['offline_class']} | {x['e2e_class']} | {', '.join(map(short, x['offline_selected'])) or 'none'} | {', '.join(map(short, x['e2e_loaded'])) or 'none'} | "
                     f"{'; '.join((qq or '')[:120] for qq in x['e2e_queries']).replace('|', '/') or '-'} |")
        L.append("")
    e2s = runs4[-1][1] if runs4 else None

    # conclusion
    cl = s["classes"]
    covered = s["recall_n"]
    d_q3 = o["bm25_q3|all|50"]["mean"] - o["bm25_q2|all|50"]["mean"]
    d_q3p = o["bm25_q3|process|50"]["mean"] - o["bm25_q2|process|50"]["mean"]
    d_emb = o["rrf_q2|all|50"]["mean"] - o["bm25_q2|all|50"]["mean"]
    d_embp = o["rrf_q2|process|50"]["mean"] - o["bm25_q2|process|50"]["mean"]
    d_emb1 = o["rrf_q1|all|50"]["mean"] - o["bm25_q1|all|50"]["mean"]
    verdict = "채택 검토" if max(d_emb, d_embp, d_emb1) >= 0.10 else "효과 없음 확정"
    L += ["## 결론 (숫자만)", "",
          f"관련 세트가 있는 일반 태스크 {covered}개 중 실패는 select_fail {cl.get('select_fail', 0)}, restate_fail {cl.get('restate_fail', 0)}, search_fail {cl.get('search_fail', 0)}; "
          f"관련 없는 {s['none_acc_oracle_n']}태스크 중 과잉 로드 {cl.get('over_load', 0)} (none 정확도 oracle 기준 {f3(s['none_acc_oracle'])}, expect_none 기준 {f3(s['none_acc_expect_none'])}). "
          f"선택은 precision {f3(s['precision'])}, recall {f3(s['recall'])}, 적중 {f3(s['hit_rate'])}. "
          f"검색 recall@50(i): Q1 {f3(o['bm25_q1|all|50']['mean'])} → Q2 {f3(o['bm25_q2|all|50']['mean'])} → Q3 {f3(o['bm25_q3|all|50']['mean'])}; "
          f"다중쿼리 효과(Q3−Q2) @50 {d_q3:+.3f}, 프로세스 층 {d_q3p:+.3f}. "
          f"MiniLM(BM25+MiniLM RRF − BM25) @50: Q2 {d_emb:+.3f}, Q1 {d_emb1:+.3f}, 프로세스 층(Q2) {d_embp:+.3f} → **{verdict}** (기준 +0.10). "
          f"병목 순서(태스크 수): 선택 {cl.get('select_fail', 0) + cl.get('over_load', 0)} (select_fail {cl.get('select_fail', 0)} + over_load {cl.get('over_load', 0)}) > 재진술 {cl.get('restate_fail', 0)} > 검색 {cl.get('search_fail', 0)}. "
          + (f"e2e(run 2, 스텁 레포) 40세션: search까지 간 세션 {e2s['searched']}, 그 {e2s['searched_only']['sessions']}개에서 로드 세트 완전 일치 {e2s['searched_only']['identical_set']}, 평균 Jaccard {e2s['searched_only']['mean_jaccard']}, "
             f"세션 search 결과 top-50과 오프라인 Q2 top-50의 Jaccard {e2s['searched_only']['mean_top50_jaccard_vs_offline_q2']}; 40개 전체 기준 세트 일치 {e2s['identical_set']}, 분류 일치 {e2s['class_agree']} — "
             "오프라인 선택이 실제 세션의 로드를 재현한다는 근거로는 성립하지 않는다." if e2s else ""), ""]
    (S3 / "report-stage3.md").write_text("\n".join(L) + "\n")
    print("wrote", S3 / "report-stage3.md", len(L))


if __name__ == "__main__":
    main()
