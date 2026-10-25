#!/usr/bin/env python3
"""runs-0.5/_extract.json (+ stage-0 runs/_extract.json) -> report-0.5.md. FIT judgments are hand-written."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = json.loads((ROOT / "runs-0.5" / "_extract.json").read_text())
S0 = {r["id"]: r for r in json.loads((ROOT / "runs" / "_extract.json").read_text())}
TASKS = ["fa-03", "fa-04", "fa-07", "fa-08", "fa-09", "nx-01", "nx-02", "nx-04", "nx-07", "nx-08"]
CONDS = ["R1", "R1R2"]
BY = {(r["cond"], r["id"]): r for r in R}

FIT = {  # skill id prefix (before @, local skills by folder name) -> (verdict, reason), per task
    ("fa-03", "uasl/python-design-patterns"): ("적합", "'Pattern 3: Separation of Concerns' — API Layer(handlers) / Service / Repository Layer(data access) 분리 도식이 '쿼리를 crud.py로' 태스크에 해당."),
    ("fa-04", "uasl/refactoring-patterns"): ("적합", "'Copy-pasted logic → Extract Method', '테스트 통과 확인 → 작은 변경 → 재확인' 루프가 중복 이메일 체크 헬퍼 추출에 해당."),
    ("fa-04", "uasl/zen"): ("모호", "capabilities에 function_extraction이 있으나 본문 상당 부분이 Judge/Atlas/Radar 등과의 핸드오프 프로토콜이고 `references/refactoring-recipes.md`는 로드되지 않음."),
    ("fa-07", "fastapi(local)"): ("적합", "`Annotated[int, Path(ge=1, ...)]` 형태의 파라미터 제약 선언이 음수 limit을 422로 막는 수정에 해당. 레포 .venv의 로컬 스킬을 pinned."),
    ("fa-09", "uasl/quill"): ("모호", "readme_management 항목은 해당하나 본문이 JSDoc/TSDoc·Nexus 라우팅 중심이고 README 템플릿(`references/readme-templates.md`)은 로드되지 않음."),
    ("nx-08", "uasl/quill"): ("모호", "fa-09와 동일 스킬. README 갱신 항목은 해당, 템플릿 참조는 미로드."),
    ("nx-01", "uasl/frontend-patterns"): ("적합", "React state·controlled input·forms 패턴이 검색 입력으로 목록 필터링하는 태스크에 해당."),
    ("nx-01", "uasl/vercel-react-best-practices"): ("모호", "64개 성능 규칙 색인(waterfall, bundle, rerender 등). 4명짜리 정적 목록 필터에 직접 해당하는 규칙은 rerender 계열 정도."),
    ("nx-01", "uasl/next-best-practices"): ("부적합", "본문이 App Router/RSC/async API 하위 문서 링크 목록. 이 레포는 Pages Router이고 태스크는 클라이언트 입력 필터라 해당 항목 없음."),
    ("nx-01", "uasl/accessibility-compliance"): ("적합", "'Creating accessible forms with proper labeling' — 검색 입력의 label/ARIA에 해당."),
    ("nx-02", "uasl/next-best-practices"): ("부적합", "타입·샘플 데이터·상세 컴포넌트에 필드 추가 태스크. 본문의 App Router/RSC/async 링크 목록 중 해당 항목 없음."),
    ("nx-04", "uasl/web-component-design"): ("적합", "컴포넌트 composition 패턴, 'Refactoring legacy components into modern patterns'가 Layout → Header/Footer 분리에 해당."),
    ("nx-04", "uasl/next-best-practices"): ("부적합", "nx-02와 같은 이유. Pages Router 컴포넌트 분리에 해당하는 항목 없음."),
}


def short(sid):
    if sid.startswith("path:"):
        return sid.split("site-packages/")[1].split("/")[0] + "(local)"
    return sid.split("@")[0]


def fmt(v):
    return f"{v/1000:.1f}" if isinstance(v, (int, float)) else "-"


def main():
    L = []
    w = L.append
    w("# skillfetch 0.5단계 — 라우터 발화 수정 후 재측정 (report)")
    w("")
    w("실행 2026-10-22 KST 15:59–16:08. 0단계 미발화 10개 태스크 × (R1, R1R2) 각 1회 = 20세션. 숫자는 `scripts/extract05.py`, 표는 `scripts/report05.py`. 적합성 열만 수기.")
    w("")
    w("## 0. 조건")
    w("")
    w("| 항목 | 값 |")
    w("|---|---|")
    w("| 변경 위치 | skillfetch 레포 브랜치 `fix/router-trigger` (worktree `<workspace>/router-fix`, `origin/main`=`9afa309` 기준). 커밋 `c229053` (router skill + CLAUDE.md 라우터 절 5번), `65a1c2b` (hook + README). push 안 함 |")
    w("| R1 | 테스트 레포 브랜치 `e2e-r1` = 0단계 베이스라인 + 새 `SKILL.md` (59줄) |")
    w("| R1R2 | `e2e-r1r2` = R1 + `.claude/hooks/skillfetch-user-prompt-submit.sh` + `.claude/settings.json`(UserPromptSubmit) — README 안내 그대로 |")
    w("| 하네스 | 0단계와 동일 (`scripts/run_task.py`, 같은 명령·allowedTools·max-turns 25, 동시 4, worktree `~/skillfetch-e2e-wt/<id>-<cond>`, 태스크별 DB, 인덱스는 `~/.skillfetch/index` `manifest.built_at` 2026-10-22T06:15:43Z — 0단계 도중 15:36:26 KST에 외부에서 교체된 것으로, 0단계의 fa-01·02·03·04·10은 04:45:24Z 빌드, 나머지 0단계 15세션과 0.5단계 20세션은 06:15:43Z 빌드). 추가된 계측: `--debug-file <id>.debug.log`, stdout 줄별 수신 시각 `<id>.ts` (두 조건 동일) |")
    w("| skillfetch 서버 | `uvx --from git+…` HEAD `9afa309` (실행 전후 동일) |")
    w("| 훅 주입 확인 | debug log의 `Hook UserPromptSubmit … If this task is non-trivial and you have not yet called skillfetch's search_skills, do that first.` 줄: R1R2 10/10, R1 0/10. (사용자 전역 UserPromptSubmit 훅은 두 조건 모두 그대로 실행) |")
    w("| 도구 승인 | 20세션 모두 `permission_denials: []` |")
    w("")
    w("라우터 SKILL.md 변경 요지 (0단계 미발화 10세션 첫 3턴 인용에 맞춘 것):")
    w("")
    w("- nx-01·nx-04 “This is a small … so I'll make it directly”, nx-02 “Three small edits” → `\"It looks small\" is not a reason to skip`, `a feature, even one that fits in a single file`")
    w("- fa-04·fa-07·fa-08·nx-07: T1이 Grep/Glob, 이후 복귀 안 함 → description `— before reading the codebase`, When `Run the steps first, before you grep, glob or read the codebase`, Step 1 `Do not explore the code first`")
    w("- fa-03: T3 `Skill(sqlmodel)` (레포 내장 스킬로 대체) → `Neither is a project skill that seems to fit … run the steps and pin it`, Step 5 project skill을 `path:`로 pin")
    w("- fa-07·fa-08·nx-07 (bugfix), fa-09·nx-08 (docs) → When에 bug fix / documentation / configuration 명시")
    w("- 트리비얼 = 한 파일의 한 줄 수정, 이름 바꾸기(다른 변경 없음), 질문 답변")
    w("- Step 2 추가: skillfetch 도구가 아직 없으면 ToolSearch `+skillfetch`로 로드 (0단계 init 13/20이 `pending`)")
    w("")

    # 1
    w("## 1. 조건별 발화율 (`search_skills` 호출 세션)")
    w("")
    w("| 태스크 | 종류/언어 | 0단계 | R1 | R1R2 |")
    w("|---|---|---|---|---|")
    for t in TASKS:
        r1, r2 = BY[("R1", t)], BY[("R1R2", t)]
        w(f"| {t} | {r1['kind']}/{r1['lang']} | N | {'Y' if r1['search_calls'] else 'N'} | {'Y' if r2['search_calls'] else 'N'} |")
    w("")
    w("| 종류 | n | 0단계 | R1 | R1R2 |")
    w("|---|---|---|---|---|")
    for k in ("feature", "refactor", "bugfix", "docs"):
        ids = [t for t in TASKS if BY[("R1", t)]["kind"] == k]
        f = {c: sum(1 for t in ids if BY[(c, t)]["search_calls"]) for c in CONDS}
        w(f"| {k} | {len(ids)} | 0/{len(ids)} | {f['R1']}/{len(ids)} | {f['R1R2']}/{len(ids)} |")
    tot = {c: sum(1 for t in TASKS if BY[(c, t)]["search_calls"]) for c in CONDS}
    w(f"| **합계** | 10 | 0/10 | **{tot['R1']}/10** | **{tot['R1R2']}/10** |")
    w("")
    for c in CONDS:
        w(f"- {c} 언어별: " + ", ".join(f"{lg} {sum(1 for t in TASKS if BY[(c,t)]['lang']==lg and BY[(c,t)]['search_calls'])}/{sum(1 for t in TASKS if BY[(c,t)]['lang']==lg)}" for lg in ("en", "ko"))
        + f"; `Skill(skillfetch-router)` 호출 {sum(1 for t in TASKS if any(x['input'].get('skill')=='skillfetch-router' for x in BY[(c,t)]['skill_tool_calls']))}/10 (발화 세션과 일치)")
    w("- 라우터 외 Skill 호출: " + (", ".join(f"{c} {t}→`{x['input'].get('skill')}`" for c in CONDS for t in TASKS for x in BY[(c, t)]["skill_tool_calls"] if x["input"].get("skill") != "skillfetch-router") or "없음"))
    w("")
    w("미발화 세션 첫 3턴 (인용):")
    w("")
    for c in CONDS:
        for t in TASKS:
            r = BY[(c, t)]
            if r["search_calls"]:
                continue
            w(f"- **{c} {t}** “{r['prompt']}”")
            for i, turn in enumerate(r["first3_turns"], 1):
                parts = []
                for it in turn["items"]:
                    if "text" in it:
                        parts.append(f"text: “{it['text'].strip()[:220]}”")
                    else:
                        inp = it["input"]
                        key = next((k for k in ("command", "pattern", "file_path", "skill", "query") if k in inp), None)
                        val = str(inp.get(key, ""))[:110].replace("\n", " ").replace("|", "\\|").replace(f"<worktrees>/{t}-{c}/", "")
                        parts.append(f"`{it['tool_use']}`({key}=`{val}`)")
                w(f"  - T{i}: " + "; ".join(parts))
    w("- 위 미발화 세션의 text/thinking에 skill·router·skillfetch·hook·trivial 언급: 없음 (R1R2 fa-07의 “items router”는 FastAPI 라우터 언급).")
    w("")

    # 2
    w("## 2. 체인 완주")
    w("")
    w("| 조건 | 발화 | search→resolve→load 완주 | search만 | resolve 에러 | load 에러 |")
    w("|---|---|---|---|---|---|")
    for c in CONDS:
        rows = [BY[(c, t)] for t in TASKS if BY[(c, t)]["search_calls"]]
        w(f"| {c} | {len(rows)} | {sum(1 for r in rows if r['chain']=='search+resolve+load')} | {sum(1 for r in rows if r['chain']=='search')} | "
          f"{sum(1 for r in rows for x in r['resolve_calls'] if json.loads(x['result']).get('errors'))} | {sum(len(r['load_errors']) for r in rows)} |")
    w("")
    w("- R1 fa-08: search 후 resolve/load 없이 작업 진행. 최종 응답 인용: “The skill search found nothing that fit this bug, so I didn't load any skills.”")
    w("- resolve_set `excluded`/`warnings`: 전 세션 빈 배열. 세션당 search 1회.")
    w("")
    w("| 조건 | 태스크 | query |")
    w("|---|---|---|")
    for c in CONDS:
        for t in TASKS:
            for x in BY[(c, t)]["search_calls"]:
                w(f"| {c} | {t} ({BY[(c,t)]['lang']}) | {x['input'].get('query')} |")
    w("")

    # 3
    w("## 3. 선택 적합성")
    w("")
    w("| 조건 | 태스크 | 로드된 스킬 | search 순위 | token_estimate | 판정 | 근거 |")
    w("|---|---|---|---|---|---|---|")
    n = {c: {"적합": 0, "부적합": 0, "모호": 0} for c in CONDS}
    for c in CONDS:
        for t in TASKS:
            r = BY[(c, t)]
            if not r["load_calls"]:
                continue
            res = json.loads(r["search_calls"][0]["result"])["results"]
            rank = {x["id"]: i + 1 for i, x in enumerate(res)}
            for s in json.loads(r["load_calls"][0]["result"])["skills"]:
                v, why = FIT[(t, short(s["id"]))]
                n[c][v] += 1
                rk = f"{rank[s['id']]}/{len(res)}" if s["id"] in rank else "검색 결과 밖 (pinned)"
                w(f"| {c} | {t} | `{short(s['id'])}` | {rk} | {s['token_estimate']} | **{v}** | {why} |")
    w("")
    for c in CONDS:
        w(f"- {c}: 스킬-태스크 쌍 {sum(n[c].values())}개 — 적합 {n[c]['적합']} / 부적합 {n[c]['부적합']} / 모호 {n[c]['모호']}")
    w("- 참고 0단계(다른 태스크 7개): 9쌍 — 적합 4 / 부적합 0 / 모호 5")
    w("")

    # 4
    w("## 4. MCP ready 시각 (세션 프로세스 spawn 기준, 초)")
    w("")
    w("start = debug log `MCP server \"skillfetch\": Starting connection`, ready = `Successfully connected`, init = stream의 init 이벤트 수신, 첫 도구 = 메인 스레드 첫 tool_use 수신, ToolSearch·skillfetch = 각 첫 호출 수신. `connect` = Claude Code가 보고한 연결 소요(ms).")
    w("")
    w("| 조건 | 태스크 | init 상태 | MCP start | MCP ready | connect ms | init | 첫 도구 | ready − 첫 도구 | 첫 ToolSearch | 첫 skillfetch 호출 | 발화 |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in CONDS:
        for t in TASKS:
            r = BY[(c, t)]
            tm = r["timing"]
            d = (tm["mcp_ready_ms"] - tm["first_tool_ms"]) if "first_tool_ms" in tm else None
            w(f"| {c} | {t} | {r['init_skillfetch_status']} | {fmt(tm.get('mcp_start_ms'))} | {fmt(tm.get('mcp_ready_ms'))} | {tm.get('mcp_connect_reported_ms')} | {fmt(tm.get('init_ms'))} | {fmt(tm.get('first_tool_ms'))} | {('%+.1f' % (d/1000)) if d is not None else '-'} | {fmt(tm.get('first_toolsearch_ms'))} | {fmt(tm.get('first_sf_call_ms'))} | {'Y' if r['search_calls'] else 'N'} |")
    allr = [BY[(c, t)]["timing"] for c in CONDS for t in TASKS]
    ready = sorted(x["mcp_ready_ms"] for x in allr)
    w("")
    w(f"- MCP ready: 중앙값 {ready[len(ready)//2]/1000:.1f}s, 범위 {ready[0]/1000:.1f}–{ready[-1]/1000:.1f}s (20세션). 연결 실패 0.")
    w(f"- init 이벤트 시점에 `connected`: {sum(1 for c in CONDS for t in TASKS if BY[(c,t)]['init_skillfetch_status']=='connected')}/20, `pending`: {sum(1 for c in CONDS for t in TASKS if BY[(c,t)]['init_skillfetch_status']=='pending')}/20")
    w(f"- 첫 도구 호출이 MCP ready보다 먼저인 세션: {sum(1 for x in allr if x['first_tool_ms'] < x['mcp_ready_ms'])}/20 ("
      + ", ".join(f"{c} {t}" for c in CONDS for t in TASKS if BY[(c,t)]['timing']['first_tool_ms'] < BY[(c,t)]['timing']['mcp_ready_ms']) + ")")
    w("- 발화 세션의 첫 skillfetch 호출은 전부 ToolSearch 이후 (ToolSearch는 `select:mcp__skillfetch__…` 또는 `+skillfetch`).")
    w("")

    # 5 cost/outcome
    w("## 5. (참고) 비용·결과")
    w("")
    w("| 태스크 | 0단계 턴/입력/출력/s | R1 턴/입력/출력/s | R1R2 턴/입력/출력/s | R1 load 토큰 | R1R2 load 토큰 | 사후 검사 R1 / R1R2 |")
    w("|---|---|---|---|---|---|---|")
    def cell(r):
        return f"{r['num_turns']} / {r['input_tokens_total']/1e6:.2f}M / {r['output_tokens']:,} / {r['duration_ms']/1000:.0f}"
    def chk(r):
        t = r["meta"]["tests"]
        if r["repo"] == "fastapi":
            j = r["junit"]
            s = f"기존 {j['existing']['pass']}/58" + (f", 새 {j['new']['pass']}" if j['new']['pass'] else "") + (f" fail {j['existing']['fail']+j['new']['fail']}" if j['existing']['fail'] + j['new']['fail'] else "")
        else:
            s = f"tsc {'ok' if t['type_check_rc']==0 else 'FAIL'}, build {'ok' if t['build_rc']==0 else 'FAIL'}"
        return s + ("" if r["result_subtype"] == "success" else f" ({r['result_subtype']})")
    for t in TASKS:
        a, b = BY[("R1", t)], BY[("R1R2", t)]
        w(f"| {t} | {cell(S0[t])} | {cell(a)} | {cell(b)} | {a['load_tokens_reported'] or '-'} | {b['load_tokens_reported'] or '-'} | {chk(a)} / {chk(b)} |")
    w("")
    w("- 입력 = uncached + cache write + cache read. 20세션 모두 `subtype: success`.")
    w("")
    w("## 파일")
    w("")
    w("- `runs-0.5/{R1,R1R2}/<id>.{jsonl,ts,debug.log,stderr,diff,meta.json,junit.xml}`, `runs-0.5/loaded/<cond>-<id>.md`, `runs-0.5/_extract.json`")
    w("- skillfetch 변경: `router-fix/assets/router-skill/SKILL.md`, `router-fix/assets/hooks/user-prompt-submit.sh`, `router-fix/README.md`, `router-fix/CLAUDE.md`")
    (ROOT / "report-0.5.md").write_text("\n".join(L) + "\n")
    print("wrote report-0.5.md", len(L))


if __name__ == "__main__":
    main()
