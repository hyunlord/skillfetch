#!/usr/bin/env python3
"""report-stage4.md from sessions.jsonl (scripts/eval_stage4.py) and the frozen prep files. Numbers only."""
from __future__ import annotations

import itertools
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

S4 = Path(__file__).resolve().parents[1]
ENVS = ("E1", "E2")
CLASSES = ("select_fail", "restate_fail", "search_fail", "over_load")


def jl(p):
    return [json.loads(l) for l in Path(p).open() if l.strip()]


def med(v):
    v = [x for x in v if x is not None]
    return statistics.median(v) if v else None


def f(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def frac(n, d):
    return f"{n}/{d}"


def jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def main():
    rows = jl(S4 / "sessions.jsonl")
    tasks = {t["id"]: t for t in jl(S4 / "tasks.jsonl")}
    oracle = {}
    for p in (S4 / "oracle.jsonl", S4 / "oracle-r2.jsonl", S4 / "oracle-v3.jsonl"):
        oracle.update({o["id"]: o for o in jl(p)})
    g40 = json.loads((S4 / "grade-4-0.json").read_text())
    rank = {}
    for p in sorted(S4.glob("rankings*.json")):
        rank.update(json.loads(p.read_text()))
    picks = json.loads((S4 / "picks.json").read_text())
    offline = {o["id"]: o for o in jl(S4 / "offline.jsonl")}
    exp = [json.loads(p.read_text()) for p in sorted(S4.glob("pool-expansion*.json"))]
    by_env = {e: [r for r in rows if r["env"] == e] for e in ENVS}
    L = ["# skillfetch 4단계 — 실제 레포에서 라우터가 실제로 무엇을 로드하나 (report)", ""]

    # --- 0. setup
    n_tasks = len(tasks)
    L += ["## 0. 설정", ""]
    L += table(("항목", "값"), [
        ("skillfetch", "`a1cbcd5` 고정: 라우터 SKILL.md(세 문장 재진술 → `queries`), 서버 `git+…@a1cbcd5`(다중쿼리 RRF), index-2026-10-22"),
        ("레포", "브랜치 `s4` = `s1-a` + 라우터 + `.mcp.json`(같은 고정): fastapi `af31086`, nextjs `d191fc6`. 세션마다 새 worktree + 1단계 `prepare`(fastapi: uv sync·DB·alembic, ui면 bun install; nextjs: npm ci)"),
        ("세션", "`claude -p` stream-json, `--include-hook-events`, `--max-turns 16`, 허용 도구 Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*, 동시 4, 고정 시드 큐 `runs/_queue.txt`"),
        ("E1 깨끗", "`--setting-sources project --strict-mcp-config --mcp-config mcp-e1.json` (P0에서 격리 확인: `report-p0.md`)"),
        ("E2 사용자", "전역 `~/.claude` 그대로 (아래 E2 구성 표)"),
        ("태스크", f"{n_tasks}개 (분류별 목표 10). 후보: 3단계 python/ts_react_next 130 + 다른 스택 expect_none 26 (1차), 1차에 모자란 분류를 채우려 다른 스택의 3단계 select/restate/search 실패 40 (2차). 실제 레포에 맞춰 고쳐 씀(`gen/sys-adapt.txt`), 제목 토큰 누출 0"),
        ("oracle", "3단계와 같은 파이프라인(2a → 2b → 3-0, 같은 프롬프트), 검색은 그 레포의 `profile_repo` 결과로; 3-0은 Q2·Q3 top-10 추가"
                   + "".join(f"; {'1차' if i == 0 else '2차'}: 관련 쌍 {e['relevant_v1']} → {e['relevant_v2']} (3-0 새 관련 {e['added_relevant']}), 관련 없음 {e['no_relevant']}/{e['tasks']}"
                             for i, e in enumerate(exp))),
        ("오프라인 분류", "라우터의 실제 질의 = Q3(라우터 1단계 규칙으로 쓴 문장들, `queries`) + profile, k=50 compact → 라우터 'When'·4단계로 선택. select_fail = 관련이 Q3 top-50에 있는데 안 고름 · restate_fail = Q3 top-50 밖, Q1 또는 Q2 top-50 안 · search_fail = 어디에도 없음 · over_load = 관련 없음인데 로드"),
        ("분류별 후보 수 (1+2차 전체)", ", ".join(f"{k} {v}" for k, v in picks["class_counts"].items())),
        ("선정", ", ".join(f"{k} {len(v)}" for k, v in picks["picked"].items()) + "; 모자람: " + (", ".join(f"{k} {v}" for k, v in picks["shortfall"].items()) or "없음")),
        ("세션 수", f"{len(rows)} (= {n_tasks} × 2 환경 × 3)"),
        ("4-0 보정 (실행 후)", f"세션이 로드했거나 오프라인 선택이 고른 스킬 중 oracle 풀에 없던 {g40['added']}개를 같은 2b 프롬프트로 채점({g40['tasks_graded']}태스크, ${g40['cost_usd']}), 그중 등급≥2 {g40['added_relevant']}. 아래 지표는 이 v3 라벨 기준. 층(오프라인 분류)은 선정 때 값 그대로 두고, v3로 다시 매기면 바뀌는 태스크 {len(g40['offline_class_changed'])}개: " + ", ".join(f"{k} {a}→{b}" for k, (a, b) in g40['offline_class_changed'].items())),
        ("준비 비용", "배치 호출(고쳐 쓰기·2a·2b·쿼리·3-0·선택·4-0, `gen/raw/*.json`의 cost_usd 합) $" + f"{sum((json.loads(x.read_text()).get('cost_usd') or 0) for x in (S4 / 'gen' / 'raw').glob('*.json')):.2f}" + " (설계 추정 $8–15)"),
        ("정리", "본 실행 후 stage-4 DB 158개(fastapi 세션 + P0) 삭제, Postgres(55432) 정지, worktree prune. E2의 <E2 MCP server> SessionStart 훅이 백그라운드로 만든 `<E2 MCP server>/` 색인이 worktree 삭제 뒤 3개 남아 있어 지웠다(세션 작업물 아님)"),
        ("로컬 skill 핀", f"{sum(1 for r in rows if r.get('local_pins'))}세션이 레포의 `.claude/skills/` skill을 `path:`로 핀 → 등급 없음, precision·잘못 로드에서 뺌"),
    ])
    L += [""]

    # --- environment composition
    L += ["## 환경 구성 (init 이벤트, 세션별)", ""]
    comp = []
    for e in ENVS:
        rs = by_env[e]
        mcp = Counter(s for r in rs for s in set(r["init"]["mcp_servers"]))
        plug = Counter(p for r in rs for p in set(r["init"]["plugins"]))
        builtin = {"agents-md", "telemetry"}
        user_plugins = sorted(p for p in plug if p not in builtin)
        skills = [r["init"]["skills_n"] for r in rs]
        hooks = Counter(h for r in rs for h in r["hook_events"])
        comp.append((e,
                     f"{len(mcp)}: " + ", ".join(sorted(mcp)),
                     f"사용자 {len(user_plugins)} + 내장 {len(plug) - len(user_plugins)}" + (": " + ", ".join(user_plugins) if user_plugins else ""),
                     f"{min(skills)}–{max(skills)}",
                     f"{min(r['init']['agents_n'] for r in rs)}–{max(r['init']['agents_n'] for r in rs)}",
                     f"{min(r['init']['tools_n'] for r in rs)}–{max(r['init']['tools_n'] for r in rs)}",
                     ", ".join(f"{h} ({n}/{len(rs)})" for h, n in sorted(hooks.items())) or "없음"))
    L += table(("환경", "MCP 서버", "플러그인", "skill 수", "agent 수", "도구 수", "훅 이벤트 종류 (발생 세션)"), comp)
    L += [""]

    # --- Table 1
    L += ["## 표 1. 환경 × 지표", ""]
    t1 = []
    for e in ENVS:
        rs = by_env[e]
        n = len(rs)
        fst = [r["first_search_turn"] for r in rs if r["first_search_turn"]]
        t1.append((e, n, frac(sum(r["fired"] for r in rs), n), frac(sum(r["path"] == "a" for r in rs), n),
                   frac(sum(r["path"] == "b" for r in rs), n), frac(sum(r["router_no_mcp"] for r in rs), n),
                   frac(sum(r["searched"] for r in rs), n), frac(sum(r["resolved"] for r in rs), n),
                   frac(sum(r["loaded_any"] for r in rs), n), frac(sum(r["capped"] for r in rs), n),
                   f"{f(med(fst), 1)} ({min(fst) if fst else '-'}–{max(fst) if fst else '-'})",
                   f(med([r["first_search_ms"] for r in rs]) and med([r["first_search_ms"] for r in rs]) / 1000, 1),
                   f(med([r["mcp_ready_ms"] for r in rs]) and med([r["mcp_ready_ms"] for r in rs]) / 1000, 1)))
    L += table(("환경", "세션", "발화", "(a) 라우터 경유", "(b) MCP 직접", "라우터만(MCP 없음)", "search 도달", "resolve_set",
                "load 1개 이상", "16턴 캡", "첫 search 턴 중앙 (범위)", "첫 search 시각 중앙 s", "MCP ready 중앙 s"), t1)
    capped_e2 = sum(r["capped"] for r in by_env["E2"]) / max(1, len(by_env["E2"]))
    L += ["", f"E2 캡 도달 비율 {capped_e2:.0%}" + (" (> 10%: E2의 발화율·검색 도달률은 '16턴 내')" if capped_e2 > 0.10 else ""), ""]

    L += ["### 사소한 태스크(라우터가 건너뛰라는 종류) vs 그 외", ""]
    L += table(("환경", "태스크 종류", "세션", "발화", "search 도달", "load 1개 이상", "16턴 캡"),
               [(e, label, len(rs), frac(sum(r["fired"] for r in rs), len(rs)), frac(sum(r["searched"] for r in rs), len(rs)),
                 frac(sum(r["loaded_any"] for r in rs), len(rs)), frac(sum(r["capped"] for r in rs), len(rs)))
                for e in ENVS for label, triv in (("trivial", True), ("그 외", False))
                for rs in [[r for r in by_env[e] if (tasks[r["task"]]["task_type"] == "trivial") == triv]]])
    L += [""]
    L += ["### search까지 갔지만 load_skills를 안 부른 세션", "",
          "원인: 16턴 캡 = 마지막 skillfetch 호출 뒤 도구 2번 안에 캡으로 끝남 · resolve_set 후 멈춤 = resolve_set을 불렀고 캡 때문이 아님 · 선택에서 none = resolve_set을 안 불렀고 캡 때문이 아님", ""]
    L += table(("환경", "search 도달", "그중 load 없음", "16턴 캡", "resolve_set 후 멈춤", "선택에서 none"),
               [(e, sum(r["searched"] for r in by_env[e]),
                 sum(1 for r in by_env[e] if r["searched_no_load"]),
                 sum(1 for r in by_env[e] if r["searched_no_load"] == "cap"),
                 sum(1 for r in by_env[e] if r["searched_no_load"] == "resolve_stop"),
                 sum(1 for r in by_env[e] if r["searched_no_load"] == "none")) for e in ENVS])
    L += [""]

    # --- Table 1b
    L += ["## 표 1b. 첫 도구 귀속", "",
          "① <E2 plugin> 훅(UserPromptSubmit 훅이 <E2 hook text>를 넣고 첫 도구가 Skill(<E2 plugin>:*)) · ② 다른 skill · ③ 전역 규칙(git status/branch) · ④ 규칙 없이 탐색 · ⑤ 라우터가 먼저", ""]
    order = ("omc_hook", "other_skill", "rules_git", "explore", "router_first", "none")
    names = {"omc_hook": "① <E2 plugin> 훅", "other_skill": "② 다른 skill", "rules_git": "③ 전역 규칙 git", "explore": "④ 탐색",
             "router_first": "⑤ 라우터 먼저", "none": "도구 없음"}
    L += table(("환경", *(names[o] for o in order), "첫 도구 상위"),
               [(e, *(sum(r["first_tool_class"] == o for r in by_env[e]) for o in order),
                 ", ".join(f"{k} {v}" for k, v in Counter(r["first_tool"] for r in by_env[e]).most_common(5))) for e in ENVS])
    L += [""]

    # --- Table 2
    L += ["## 표 2. 오프라인 분류 × 환경: 세션 분류", "",
          "세션 분류: no_search = search 안 함 · 나머지는 오프라인 규칙(관련이 세션 자신의 top-50에 있으면 select_fail, 아니면 오프라인 Q1/Q2/Q3 top-50에 있으면 restate_fail)", ""]
    cls_order = ("ok", "select_fail", "restate_fail", "search_fail", "over_load", "no_search")
    t2 = []
    for oc in CLASSES:
        for e in ENVS:
            rs = [r for r in by_env[e] if r["offline_class"] == oc]
            if rs:
                t2.append((oc, e, len(rs), *(sum(r["class"] == c for r in rs) for c in cls_order)))
    L += table(("오프라인 분류", "환경", "세션", *cls_order), t2)
    L += [""]

    # --- Table 3
    L += ["## 표 3. 반복 간 Jaccard (첫 search top-50)", ""]
    t3 = []
    for e in ENVS:
        per = defaultdict(list)
        for r in by_env[e]:
            per[r["task"]].append(r)
        js, qdiff, voff = [], 0, []
        for tid, rs in per.items():
            srs = [r for r in rs if r["top50"]]
            for a, b in itertools.combinations(srs, 2):
                js.append(jac(a["top50"], b["top50"]))
            qs = {json.dumps(r["queries"]) for r in srs}
            qdiff += len(srs) >= 2 and len(qs) > 1
            voff += [jac(r["top50"], rank[tid]["q3"][:50]) for r in srs]
        t3.append((e, len(js), f(statistics.mean(js), 3) if js else "-", f(med(js), 3),
                   f"{sum(j == 1.0 for j in js)}/{len(js)}", qdiff, f(statistics.mean(voff), 3) if voff else "-"))
    L += table(("환경", "쌍 수", "평균", "중앙", "완전 일치 쌍", "반복 간 쿼리 문장이 달랐던 태스크", "세션 top-50 vs 오프라인 Q3 top-50 평균"), t3)
    L += [""]

    # --- Table 4
    L += ["## 표 4. 로드 세트 vs oracle, 오프라인 선택 대비", ""]
    t4 = []
    for e in ENVS:
        rs = by_env[e]
        withR = [r for r in rs if oracle[r["task"]]["relevant"]]
        noR = [r for r in rs if not oracle[r["task"]]["relevant"]]
        loaded = [r for r in rs if r["loaded"]]
        prec = [r["precision"] for r in loaded if r["precision"] is not None]
        loaded_withR = [r for r in withR if set(r["loaded"]) - set(r.get("local_pins") or [])]
        t4.append((e, f(statistics.mean(prec), 3) if prec else "-",
                   f(statistics.mean([r["recall"] for r in withR]), 3) if withR else "-",
                   frac(sum(bool(r["hit"]) for r in withR), len(withR)),
                   frac(sum(bool(r["hit"]) for r in loaded_withR), len(loaded_withR)),
                   sum(r["wrong_loads"] for r in rs),
                   frac(sum(bool(r["loaded"]) for r in noR), len(noR)),
                   frac(sum(set(r["loaded"]) == set(r["offline_skills"]) for r in rs), len(rs)),
                   f(statistics.mean([jac(r["loaded"], r["offline_skills"]) for r in rs]), 3),
                   frac(sum(r["class"] == r["offline_class"] for r in rs), len(rs))))
    L += table(("환경", "precision (로드한 세션)", "recall (관련 있는 태스크)", "적중 (관련 있는 태스크 세션)", "적중 (그중 로드한 세션)", "잘못 로드 합", "과잉 로드율 (관련 없는 태스크)",
                "오프라인과 세트 완전 일치", "오프라인 대비 Jaccard 평균", "분류 일치"), t4)
    L += [""]
    L += ["오프라인 분류별 (세션 수, 세트 완전 일치, 분류 일치, Jaccard 평균):", ""]
    t4b = []
    for oc in CLASSES:
        for e in ENVS:
            rs = [r for r in by_env[e] if r["offline_class"] == oc]
            if rs:
                t4b.append((oc, e, len(rs), sum(set(r["loaded"]) == set(r["offline_skills"]) for r in rs),
                            sum(r["class"] == oc for r in rs), f(statistics.mean([jac(r["loaded"], r["offline_skills"]) for r in rs]), 3)))
    L += table(("오프라인 분류", "환경", "세션", "세트 일치", "분류 일치", "Jaccard"), t4b)
    L += [""]

    # --- environment effect
    L += ["## 환경 효과 (태스크별 3회 평균, E1 − E2)", ""]
    te = []
    for key, label in (("fired", "발화"), ("searched", "search 도달"), ("loaded_any", "load 1개 이상"), ("capped", "16턴 캡")):
        diffs = []
        for tid in tasks:
            a = [r[key] for r in by_env["E1"] if r["task"] == tid]
            b = [r[key] for r in by_env["E2"] if r["task"] == tid]
            if a and b:
                diffs.append(statistics.mean(map(float, a)) - statistics.mean(map(float, b)))
        te.append((label, len(diffs), f(statistics.mean(diffs), 3) if diffs else "-",
                   sum(d > 0 for d in diffs), sum(d < 0 for d in diffs), sum(d == 0 for d in diffs)))
    L += table(("지표", "태스크", "평균 차 (E1−E2)", "E1 > E2", "E1 < E2", "같음"), te)
    L += [""]

    # --- cost
    L += ["## 비용·시간", ""]
    L += table(("환경", "세션", "비용 합 $", "세션 비용 중앙 $", "입력 토큰 중앙", "턴 중앙", "세션 시간 중앙 s"),
               [(e, len(by_env[e]), f(sum(r["cost_usd"] or 0 for r in by_env[e])), f(med([r["cost_usd"] for r in by_env[e]])),
                 f(med([r["input_tokens"] for r in by_env[e]]), 0), f(med([r["num_turns"] for r in by_env[e]]), 1),
                 f(med([r["wall_s"] for r in by_env[e]]), 1)) for e in ENVS])
    L += [""]

    # --- conclusion
    def rate(e, k):
        rs = by_env[e]
        return f"{sum(bool(r[k]) for r in rs)}/{len(rs)}"
    L += ["## 결론 (숫자만)", "",
          " ".join([
              f"태스크 {n_tasks}개(그중 trivial {sum(t['task_type'] == 'trivial' for t in tasks.values())}; 분류별 목표 10; 모자람 " + (", ".join(f"{k} {v}" for k, v in picks["shortfall"].items()) or "없음") + f"), 세션 {len(rows)}.",
              f"발화: E1 {rate('E1', 'fired')}, E2 {rate('E2', 'fired')}; search 도달: E1 {rate('E1', 'searched')}, E2 {rate('E2', 'searched')};",
              f"load 1개 이상: E1 {rate('E1', 'loaded_any')}, E2 {rate('E2', 'loaded_any')}; 16턴 캡: E1 {rate('E1', 'capped')}, E2 {rate('E2', 'capped')}.",
              "trivial 외 태스크의 발화: " + "; ".join(
                  f"{e} {sum(r['fired'] for r in by_env[e] if tasks[r['task']]['task_type'] != 'trivial')}/{sum(1 for r in by_env[e] if tasks[r['task']]['task_type'] != 'trivial')}"
                  for e in ENVS) + ".",
              "로드 세트(v3 라벨): " + "; ".join(
                  f"{e} 로드한 세션 {sum(1 for r in by_env[e] if set(r['loaded']) - set(r.get('local_pins') or []))}, 그중 관련 적중 {sum(1 for r in by_env[e] if r['hit'])}"
                  for e in ENVS) + ".",
              "오프라인 선택과 세트 완전 일치: " + "; ".join(
                  f"{e} {sum(set(r['loaded']) == set(r['offline_skills']) for r in by_env[e])}/{len(by_env[e])}" for e in ENVS) + ".",
              "비용: " + "; ".join(f"{e} ${sum(r['cost_usd'] or 0 for r in by_env[e]):.2f}" for e in ENVS) + ".",
              "search 후 load 없음 (캡 / resolve 후 멈춤 / none): " + "; ".join(
                  f"{e} {sum(1 for r in by_env[e] if r['searched_no_load'] == 'cap')} / {sum(1 for r in by_env[e] if r['searched_no_load'] == 'resolve_stop')} / {sum(1 for r in by_env[e] if r['searched_no_load'] == 'none')}"
                  for e in ENVS) + ".",
          ]), ""]
    (S4 / "report-stage4.md").write_text("\n".join(L) + "\n")
    print(S4 / "report-stage4.md")


if __name__ == "__main__":
    main()
