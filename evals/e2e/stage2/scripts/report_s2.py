#!/usr/bin/env python3
"""stage2/report-stage2.md from runs/_extract.json, judged-p1.json, judged-p2.json, judge-consistency.json and the
1b landing data (stage1b/runs/_extract.json, stage1b/rejudge/). Numbers only."""
import json
import statistics as st
from pathlib import Path

S2 = Path(__file__).resolve().parents[1]
S1B = S2.parent / "stage1b"
TASKS = [("s2-tests", "테스트 작성"), ("s2-api", "백엔드 API"), ("s2-docs", "문서화"), ("s2-data", "데이터 스크립트")]
CONDS = ("A", "B", "C2")


def med(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return st.median(v) if v else None


def mean(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return st.mean(v) if v else None


def f(x, d=0):
    if x is None:
        return "-"
    if isinstance(x, float) and d == 0 and x != int(x):
        d = 1
    return f"{x:,.{d}f}"


def short(i):
    return i.rstrip("/").rsplit("/", 1)[-1] + "(local)" if str(i).startswith("path:") else str(i).split("@")[0]


def landing():
    """1b landing tasks: A, B, C2 (C2 = rerun with k=50), scores from the 1b rejudge (one pass, n=4 per cond)."""
    rows = [r for r in json.loads((S1B / "runs" / "_extract.json").read_text())
            if r["task_id"] in ("s1b-nx-landing", "s1b-fa-landing") and r["cond"] in CONDS]
    key = {k["code"]: k for k in map(json.loads, (S1B / "rejudge" / "screens-key.jsonl").read_text().splitlines())}
    import re
    txt = (S1B / "rejudge" / "blind-ranking.md").read_text()
    score = {}
    for m in re.finditer(r"^\| ([0-9a-f]{8}) \| (\d+) \| (\d+) \|", txt, re.M):
        if m.group(1) in key:
            k = key[m.group(1)]
            score[(k["task"], k["cond"], k["rep"])] = int(m.group(3))
    out = {}
    for c in CONDS:
        rr = [r for r in rows if r["cond"] == c]
        out[c] = {"score": mean([score[(r["task_id"], c, r["rep"])] for r in rr]), "n": len(rr),
                  "check": f"{sum(1 for r in rr if r['check'].get('pass') is True)}/{len(rr)}",
                  "turns": med([r["num_turns"] for r in rr]), "tokens": med([r["input_tokens_total"] for r in rr]),
                  "cost": med([r.get("total_cost_usd") for r in rr])}
        if c == "C2":
            ranks = [s["expert_rank"].get("anthropics-skills/frontend-design") for r in rr for s in r.get("searches", [])]
            out[c]["b_top50"] = sum(1 for x in ranks if x)
            out[c]["b_rank"] = mean([x for x in ranks if x])
            out[c]["b_loaded"] = sum(1 for r in rr if any(str(i).startswith("anthropics-skills/frontend-design") for i in r["loaded_ids"]))
    return out


def objective(task, rr):
    if task == "s2-tests":
        cov = [r["check"]["metrics"].get("rules_branch_pct") for r in rr]
        line = [r["check"]["metrics"].get("rules_line_pct") for r in rr]
        passed = [(r["check"]["metrics"].get("junit") or {}).get("passed") for r in rr]
        failed = [((r["check"]["metrics"].get("junit") or {}).get("failures") or 0) + ((r["check"]["metrics"].get("junit") or {}).get("errors") or 0) for r in rr]
        mod = sum(1 for r in rr if r["check"]["metrics"].get("module_modified"))
        return f"테스트 통과 중앙 {f(med(passed))}, 실패 합 {sum(failed)}, 커버리지 line {f(mean(line), 1)}% / branch {f(mean(cov), 1)}%, 모듈 수정 {mod}"
    if task == "s2-api":
        cp = [r["check"]["metrics"].get("contract_pass") for r in rr]
        own = sum(1 for r in rr if r["check"]["items"][0]["pass"])
        return f"계약 호출 평균 {f(mean(cp), 1)}/27 (전부 통과 {sum(1 for x in cp if x == 27)}/{len(rr)}), 자체 테스트 통과 {own}/{len(rr)}"
    if task == "s2-docs":
        miss = sum(1 for r in rr if r["check"]["metrics"].get("scripts_missing"))
        words = med([r["check"]["metrics"].get("readme_words") for r in rr])
        return f"README 중앙 {f(words)}단어, 없는 npm 스크립트 언급 {miss}/{len(rr)}, build 통과 {sum(1 for r in rr if r['check']['items'][2]['pass'])}/{len(rr)}"
    ok = sum(1 for r in rr if r["check"].get("pass") is True)
    return f"스크립트 실행·출력 체크 통과 {ok}/{len(rr)}"


def main():
    rows = json.loads((S2 / "runs" / "_extract.json").read_text())
    j1 = {x["name"] + x["cond"]: x for x in json.loads((S2 / "judged-p1.json").read_text())}
    j2 = {x["name"] + x["cond"]: x for x in json.loads((S2 / "judged-p2.json").read_text())}
    cons = json.loads((S2 / "judge-consistency.json").read_text())
    for r in rows:
        k = r["name"] + r["cond"]
        r["s1"], r["s2"] = j1[k]["총점 1-5"], j2[k]["총점 1-5"]
        r["score"] = (r["s1"] + r["s2"]) / 2
    by = {(t, c): sorted([r for r in rows if r["task_id"] == t and r["cond"] == c], key=lambda x: x["rep"]) for t, _ in TASKS for c in CONDS}
    L = ["# skillfetch 2단계 — 도메인 일반화 (report)", ""]
    hdr = S2 / "report-header.md"
    if hdr.exists():
        L += [hdr.read_text().rstrip(), ""]
    L += ["## 표 1. 도메인 × 조건", "",
          "점수 = 총점 1-5, 두 채점(p1·p2) 평균의 조건 평균 (괄호: p1 / p2). 랜딩 행 = 1b 재판정(1회, 루브릭 (b) 쓸만함 1-5, n=4: nx 2 + fa 2), 턴·토큰·비용은 같은 1b 세션. 턴·입력 토큰·비용은 중앙값. "
          "C2≥B / C2≥A = 두 채점 평균 기준; 괄호 안은 p1·p2 각각에서도 성립하는지.", "",
          "| 도메인 | 조건 | n | 점수 (p1 / p2) | 객관 지표 | 중앙 턴 | 중앙 입력 토큰 | 중앙 비용 $ | C2≥B | C2≥A |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    land = landing()
    for c in CONDS:
        x = land[c]
        mark = ""
        if c == "C2":
            mark = f"| {'Y' if x['score'] >= land['B']['score'] else 'N'} | {'Y' if x['score'] >= land['A']['score'] else 'N'} |"
        else:
            mark = "| | |"
        L.append(f"| 랜딩 페이지 (1b) | {c} | {x['n']} | {f(x['score'], 2)} | 체크 통과 {x['check']} | {f(x['turns'])} | {f(x['tokens'])} | {f(x['cost'], 2)} {mark}")
    summary = {}
    for t, label in TASKS:
        sc = {c: mean([r["score"] for r in by[(t, c)]]) for c in CONDS}
        p = {c: (mean([r["s1"] for r in by[(t, c)]]), mean([r["s2"] for r in by[(t, c)]])) for c in CONDS}
        summary[t] = sc
        for c in CONDS:
            rr = by[(t, c)]
            mark = "| | |"
            if c == "C2":
                both_b = "both" if p["C2"][0] >= p["B"][0] and p["C2"][1] >= p["B"][1] else ("one" if (p["C2"][0] >= p["B"][0]) != (p["C2"][1] >= p["B"][1]) else "neither")
                both_a = "both" if p["C2"][0] >= p["A"][0] and p["C2"][1] >= p["A"][1] else ("one" if (p["C2"][0] >= p["A"][0]) != (p["C2"][1] >= p["A"][1]) else "neither")
                mark = f"| {'Y' if sc['C2'] >= sc['B'] else 'N'} ({both_b}) | {'Y' if sc['C2'] >= sc['A'] else 'N'} ({both_a}) |"
            L.append(f"| {label} ({t}) | {c} | {len(rr)} | {f(sc[c], 2)} ({f(p[c][0], 2)} / {f(p[c][1], 2)}) | {objective(t, rr)} | "
                     f"{f(med([r['num_turns'] for r in rr]))} | {f(med([r['input_tokens_total'] for r in rr]))} | {f(med([r.get('total_cost_usd') for r in rr]), 2)} {mark}")
    L += ["", "## 표 2. C2 검색 적중 (n=5 중; 랜딩은 n=4)", "",
          "| 도메인 | B 스킬 | 라우터 발화 | search 호출 | B가 top-50에 | B 평균 순위 (들어간 run) | B를 고름 (resolve에 넣음) | resolve_set이 B 제외 | B 로드 |",
          "|---|---|---|---|---|---|---|---|---|"]
    x = land["C2"]
    L.append(f"| 랜딩 페이지 (1b) | `anthropics-skills/frontend-design` | 4/4 | 4/4 | {x['b_top50']}/4 | {f(x['b_rank'], 1)} | 4/4 | 0/4 | {x['b_loaded']}/4 |")
    for t, label in TASKS:
        rr = by[(t, "C2")]
        L.append(f"| {label} ({t}) | `{short(rr[0]['b_skill'])}` | {sum(r['router_fired'] for r in rr)}/{len(rr)} | {sum(1 for r in rr if r['search_calls'])}/{len(rr)} | "
                 f"{sum(r['b_in_top50'] for r in rr)}/{len(rr)} | {f(mean([r['b_rank'] for r in rr if r['b_rank']]), 1)} | {sum(r['b_picked'] for r in rr)}/{len(rr)} | "
                 f"{sum(r['b_excluded'] for r in rr)}/{len(rr)} | {sum(r['b_loaded'] for r in rr)}/{len(rr)} |")
    L += ["", "## 표 3. C2가 B 스킬을 로드하지 않은 run: 대신 로드한 스킬과 점수", "",
          "| 도메인 | run | 원인 | B 순위 | 로드한 스킬 | 점수 (p1 / p2) | 같은 도메인 B 평균 점수 |", "|---|---|---|---|---|---|---|"]
    causes = {}
    for t, label in TASKS:
        for r in by[(t, "C2")]:
            if r["b_loaded"]:
                continue
            if not r["search_calls"]:
                cause = "search 안 함"
            elif not r["b_in_top50"]:
                cause = "top-50 밖"
            elif r["b_excluded"]:
                cause = "resolve_set 제외"
            elif r["b_picked"]:
                cause = "골랐지만 로드 안 됨" + (f" ({r['b_load_error'][0]['error'][:60]})" if r["b_load_error"] else "")
            else:
                cause = "top-50 안, 모델이 안 고름"
            causes.setdefault(t, []).append(cause)
            L.append(f"| {label} | r{r['rep']} | {cause} | {r['b_rank'] or '-'} | {', '.join('`' + short(i) + '`' for i in r['loaded_ids']) or '-'} | "
                     f"{f(r['score'], 1)} ({r['s1']} / {r['s2']}) | {f(summary[t]['B'], 2)} |")
    L += ["", "## 채점 일관성 (p1 vs p2, 같은 루브릭, 새 코드·새 판정자)", "",
          "| 도메인 | n | 총점 일치 | 평균 절대 차 | 최대 차 | C2≥B 판단 두 채점 같음 | C2≥A 판단 두 채점 같음 |", "|---|---|---|---|---|---|---|"]
    for t, label in TASKS:
        c = cons[t]
        L.append(f"| {label} | {c['n']} | {c['total_exact_agree']}/{c['n']} | {c['total_mean_abs_diff']} | {c['total_max_abs_diff']} | {'Y' if c['c2_ge_b_same_in_both'] else 'N'} | {'Y' if c['c2_ge_a_same_in_both'] else 'N'} |")
    repro = [t for t, _ in TASKS if summary[t]["C2"] >= summary[t]["B"]]
    found = {t: sum(r["b_loaded"] for r in by[(t, "C2")]) for t, _ in TASKS}
    cause_txt = "; ".join(f"{t}: " + ", ".join(f"{k} {v}" for k, v in sorted({c: causes[t].count(c) for c in causes[t]}.items())) for t in causes) or "없음"
    L += ["", "## 결론 (숫자만)", "",
          f"C2가 B를 재현한 도메인(두 채점 평균 점수 C2 ≥ B) {len(repro)}/4 ({', '.join(repro) or '없음'}); 랜딩 포함 {len(repro) + (1 if land['C2']['score'] >= land['B']['score'] else 0)}/5. "
          f"C2가 B 스킬을 로드한 run: " + ", ".join(f"{t} {found[t]}/5" for t, _ in TASKS) + f" (랜딩 {land['C2']['b_loaded']}/4). "
          f"B를 로드하지 않은 run의 원인: {cause_txt}. "
          + "".join(f"재현 못 한 도메인 {t}: C2 {f(summary[t]['C2'], 2)} < B {f(summary[t]['B'], 2)}, C2가 B를 로드한 run {found[t]}/5, 원인 분류(top-50 밖 / 안 고름 / 제외) 해당 run {len(causes.get(t, []))}. "
                    for t, _ in TASKS if t not in repro), ""]
    L += ["## 세션별", "", "| 도메인 | 조건 | run | subtype | 턴 | 입력 토큰 | 출력 토큰 | 비용 $ | 체크 | 점수 p1 / p2 | C2: 쿼리 | C2: 로드 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t, label in TASKS:
        for c in CONDS:
            for r in by[(t, c)]:
                q = "; ".join(s["query"] or "" for s in r.get("searches", [])).replace("|", "/") if c == "C2" else ""
                lo = ", ".join("`" + short(i) + "`" for i in r["loaded_ids"]) if c == "C2" else ""
                L.append(f"| {t} | {c} | r{r['rep']} | {r['result_subtype']} | {r['num_turns']} | {f(r['input_tokens_total'])} | {f(r['output_tokens'])} | "
                         f"{f(r.get('total_cost_usd'), 2)} | {r['check'].get('pass')} | {r['s1']} / {r['s2']} | {q} | {lo} |")
    (S2 / "report-stage2.md").write_text("\n".join(L) + "\n")
    print("wrote", S2 / "report-stage2.md", len(L))


if __name__ == "__main__":
    main()
