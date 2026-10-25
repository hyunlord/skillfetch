#!/usr/bin/env python3
"""stage1 follow-ups -> stage1/report-stage1-extra.md: (1) C's loaded skills vs B's expert set per task/run,
(2) tool-call mix per condition and C's turns before load_skills. MATCH verdicts are hand-written."""
import json
import statistics as st
from collections import Counter
from pathlib import Path

import yaml

S1 = Path(__file__).resolve().parents[1]
R = json.loads((S1 / "runs" / "_extract.json").read_text())
T = {t["id"]: t for t in yaml.safe_load((S1 / "tasks-stage1.yaml").read_text())["tasks"]}

# (task, rep) -> (verdict, reason). 같음 = same id set; 동급 = different set that covers what the expert set
# covers for this task (incl. expert set ⊂ C set); 다름 = does not; 로드 없음 = C loaded nothing.
MATCH = {
    ("s1-fa-01", 1): ("동급", "fastapi(local)의 `Annotated`/`Query`·`Field` 제약 선언이 허용값 외 422를 다룸. api-design의 정렬 파라미터 관례(`?sort=-created_at`)는 없음."),
    ("s1-fa-02", 1): ("다름", "B(postgresql-table-design)는 행이 있는 테이블의 NOT NULL+default 컬럼 추가(safe schema evolution)를 다룸. sqlmodel(local)은 \"Changing the model does not alter existing columns\" 한 줄뿐, alembic 없음."),
    ("s1-fa-03", 1): ("동급", "design-to-code \"prioritizing alignment with … the existing project … reusable components\"가 '기존 UI 컴포넌트 스타일에 맞춰' 부분을 다룸. shadcn 컴포넌트·CLI 규칙은 없음."),
    ("s1-fa-03", 2): ("동급", "r1과 같은 스킬."),
    ("s1-fa-05", 1): ("동급", "fastapi(local) Dependency Injection 절 \"Use dependencies when the logic … is shared across endpoints\"가 공통 페이지네이션 의존성에 해당. B는 일반 DI(생성자 주입)."),
    ("s1-fa-06", 1): ("동급", "python-testing-patterns의 pytest fixture·격리 패턴이 B(integration-testing)의 API+DB 테스트 범위를 다룸. Testcontainers/CI 절은 없음."),
    ("s1-fa-06", 2): ("다름", "radar 본문은 테스트 일반 규칙 + 에이전트 핸드오프 프로토콜. B의 API 통합 테스트·DB 정리 패턴 없음."),
    ("s1-fa-07", 1): ("같음", ""),
    ("s1-fa-07", 2): ("다름", "fastapi(local)에는 테스트 내용 없음. B(python-testing-patterns)의 예외·monkeypatch·에러 경로 테스트 패턴 없음."),
    ("s1-fa-08", 1): ("동급", "fastapi(local) Pydantic `Field` 검증 + fastapi-endpoint의 Pydantic 스키마가 null 입력을 API 계층에서 막는 부분을 다룸. defense-in-depth의 계층별 검증 원칙, api-design의 422 상태코드 표는 없음."),
    ("s1-fa-08", 2): ("동급", "fastapi(local) `Field` 검증 + sqlmodel(local) Creates and Updates(`exclude_unset`)가 같은 부분을 다룸. 계층별 검증 원칙·상태코드 표는 없음."),
    ("s1-nx-02", 1): ("동급", "api-design 공통(1/2). backend-patterns 대신 next-best-practices(App Router 하위 문서 링크; Route Handlers는 App Router 기준)."),
    ("s1-nx-02", 2): ("동급", "r1과 같은 세트."),
    ("s1-nx-04", 1): ("동급", "B 세트 포함 + vercel-react-best-practices."),
    ("s1-nx-04", 2): ("동급", "r1과 같은 세트."),
    ("s1-nx-06", 1): ("다름", "next-best-practices(App Router 링크 목록)는 B(refactoring-patterns)의 동작 보존 리팩토링 절차를 다루지 않음."),
    ("s1-nx-06", 2): ("동급", "zen \"refactor code … while preserving behavior … verifying changes\"가 refactoring-patterns의 동작 보존·검증 부분을 다룸. 본문 다수가 핸드오프 프로토콜."),
    ("s1-nx-07", 1): ("동급", "unit-testing과 tdd-workflow 모두 일반 테스트 스킬, Vitest 설정 예시 있음. React Testing Library 예시는 tdd-workflow에만 있음."),
    ("s1-nx-07", 2): ("같음", ""),
    ("s1-nx-08", 1): ("동급", "typescript-unit-testing(TS 단위 테스트, Jest/NestJS 지향) + radar가 B(unit-testing)의 TS 단위 테스트 부분을 다룸."),
    ("s1-nx-08", 2): ("동급", "radar(테스트 추가 일반 규칙, JS/TS 지원)가 B(unit-testing, 다언어 일반 단위 테스트)와 같은 수준의 일반 규칙을 다룸."),
    ("s1-nx-10", 1): ("같음", ""),
}


def short(sid):
    return sid.rstrip("/").rsplit("/", 1)[-1] + "(local)" if sid.startswith("path:") else sid.split("@")[0]


def msgs(r):
    out, ids = [], {}
    for line in (S1 / "runs" / r["cond"] / f"{r['name']}.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            mid = e["message"]["id"]
            tools = [(x["name"], x["input"].get("skill")) for x in e["message"]["content"] if x["type"] == "tool_use"]
            if mid in ids:
                out[ids[mid]] += tools
            else:
                ids[mid] = len(out)
                out.append(tools)
    return out


def is_sf(t):
    return t[0] == "ToolSearch" or t[0].startswith("mcp__skillfetch__") or (t[0] == "Skill" and t[1] == "skillfetch-router")


def first(m, pred):
    return next((i for i, x in enumerate(m) if any(pred(t) for t in x)), None)


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def f(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def main():
    for r in R:
        r["_m"] = msgs(r)
    L = []
    w = L.append
    w("# skillfetch 1단계 — 추가 집계 (선택 일치, 턴/도구 분포)")
    w("")
    w("데이터: `runs/_extract.json` + 세션 jsonl. 표 생성 `scripts/report_s1_extra.py`. 1)의 판정 열만 수기.")
    w("")
    # 1
    w("## 1. 선택 일치: C가 로드한 스킬 vs B의 전문가 스킬 (전문가 태스크 15개 × C 2회)")
    w("")
    w("판정: **같음** = 같은 id 집합 · **동급** = 집합은 다르지만(전문가 세트 ⊂ C 세트 포함) 전문가 세트가 이 태스크에 대해 다루는 내용을 C 세트도 다룸 · **다름** = 다루지 않음 · **로드 없음** = C가 로드하지 않음(search 미호출 또는 search만).")
    w("")
    w("| 태스크 | run | B 전문가 스킬 | C 로드 스킬 | C 체인 | 전문가 스킬이 C search 상위 10에 있었나 | 판정 | 근거 |")
    w("|---|---|---|---|---|---|---|---|")
    cnt = Counter()
    for tid, t in T.items():
        if not t.get("expert_skills"):
            continue
        exp = [x.split("@")[0] for x in t["expert_skills"]]
        for r in sorted([r for r in R if r["task_id"] == tid and r["cond"] == "C"], key=lambda x: x["rep"]):
            top = [x["id"].split("@")[0] for x in json.loads(r["search_calls"][0]["result"])["results"]] if r["search_calls"] else []
            inres = ", ".join(f"`{e}` #{top.index(e)+1}" for e in exp if e in top) or ("없음" if r["search_calls"] else "search 안 함")
            if not r["loaded_ids"]:
                v, why = "로드 없음", ""
            else:
                v, why = MATCH[(tid, r["rep"])]
            cnt[v] += 1
            w(f"| {tid} | r{r['rep']} | {', '.join('`'+e+'`' for e in exp)} | {', '.join('`'+short(i)+'`' for i in r['loaded_ids']) or '-'} | {r['chain']} | {inres} | **{v}** | {why} |")
    w("")
    w(f"집계(30 run): 같음 {cnt['같음']} · 동급 {cnt['동급']} · 다름 {cnt['다름']} · 로드 없음 {cnt['로드 없음']}")
    w("")

    # 2
    w("## 2. C의 추가 턴: 도구 호출 분포와 스킬 로드 전 턴")
    w("")
    w("메시지 = 메인 스레드 assistant 메시지 1개(같은 메시지 안 병렬 도구 호출 포함). `num_turns` = result 이벤트 값. 체인 메시지 = `Skill(skillfetch-router)`, `ToolSearch`, `mcp__skillfetch__*` 중 하나라도 포함한 메시지.")
    w("")
    for scope, conds in (("전문가 태스크 15개", ("A", "B", "C")), ("전체 20개", ("A", "C"))):
        rows = [r for r in R if scope == "전체 20개" or T[r["task_id"]].get("expert_skills")]
        names = [k for k, _ in Counter(t[0] for r in rows for m in r["_m"] for t in m).most_common()]
        w(f"### 세션당 평균 도구 호출 수 — {scope}")
        w("")
        w("| 조건 | 세션 | num_turns | 메시지 | 체인 메시지 | 체인 외 메시지 | 첫 Edit/Write 메시지 순번(중앙) | " + " | ".join(n.replace("mcp__skillfetch__", "sf:") for n in names) + " |")
        w("|" + "---|" * (7 + len(names)))
        for c in conds:
            rr = [r for r in rows if r["cond"] == c]
            ctr = Counter(t[0] for r in rr for m in r["_m"] for t in m)
            chain = [sum(1 for x in r["_m"] if any(is_sf(t) for t in x)) for r in rr]
            fe = [first(r["_m"], lambda t: t[0] in ("Edit", "Write")) for r in rr]
            fe = [x + 1 for x in fe if x is not None]
            w(f"| {c} | {len(rr)} | {f(mean([r['num_turns'] for r in rr]),1)} | {f(mean([len(r['_m']) for r in rr]),1)} | {f(mean(chain),2)} | "
              f"{f(mean([len(r['_m']) - k for r, k in zip(rr, chain)]),2)} | {st.median(fe) if fe else '-'} | " + " | ".join(f(ctr[n] / len(rr)) for n in names) + " |")
        w("")
        skills = Counter((r["cond"], t[1]) for r in rows for m in r["_m"] for t in m if t[0] == "Skill")
        w("Skill 도구 호출(조건, 스킬): " + ", ".join(f"{c}·`{s}` {n}" for (c, s), n in sorted(skills.items())))
        w("")
    C = [r for r in R if r["cond"] == "C"]
    loaded = [r for r in C if first(r["_m"], lambda t: t[0] == "mcp__skillfetch__load_skills") is not None]
    w("### C: 스킬 로드 전 턴 (load_skills 호출이 있는 C 세션)")
    w("")
    w("| 세션 | 메시지 총수 | load_skills가 든 메시지 순번 | 그 전 메시지 | 그 전 체인 메시지 | 그 전 체인 외 메시지 | 체인 외 메시지에서 쓴 도구 |")
    w("|---|---|---|---|---|---|---|")
    pre_all, pre_sf, pre_other = [], [], []
    for r in sorted(loaded, key=lambda x: x["name"]):
        at = first(r["_m"], lambda t: t[0] == "mcp__skillfetch__load_skills")
        pre = r["_m"][:at]
        sfn = sum(1 for x in pre if any(is_sf(t) for t in x))
        other_tools = Counter(t[0] for x in pre if not any(is_sf(t) for t in x) for t in x)
        pre_all.append(at)
        pre_sf.append(sfn)
        pre_other.append(at - sfn)
        w(f"| {r['name']} | {len(r['_m'])} | {at + 1} | {at} | {sfn} | {at - sfn} | {', '.join(f'{k}×{v}' for k, v in other_tools.items()) or '-'} |")
    w("")
    w(f"- n={len(loaded)}: load 전 메시지 중앙 {st.median(pre_all)} (범위 {min(pre_all)}–{max(pre_all)}), 평균 {mean(pre_all):.2f} = 체인 {mean(pre_sf):.2f} + 체인 외 {mean(pre_other):.2f}")
    fired = [r for r in C if r["search_calls"]]
    w(f"- C 세션당 체인 메시지: search 호출 세션 {mean([sum(1 for x in r['_m'] if any(is_sf(t) for t in x)) for r in fired]):.2f} (n={len(fired)}), 미호출 세션 0 (n={len(C)-len(fired)})")
    w("- 체인 순서: 29세션 `Skill(skillfetch-router)` → `ToolSearch` → `profile_repo` → `search_skills` → `resolve_set` → `load_skills`, 2세션 `… → search_skills`에서 멈춤 (search 호출 31세션 전부)")
    (S1 / "report-stage1-extra.md").write_text("\n".join(L) + "\n")
    print("wrote report-stage1-extra.md", len(L), dict(cnt))


if __name__ == "__main__":
    main()
