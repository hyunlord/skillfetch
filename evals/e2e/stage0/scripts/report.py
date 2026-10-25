#!/usr/bin/env python3
"""runs/_extract.json -> report.md (stage 0). Numbers are computed; the judgment dicts below are hand-written."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
R = json.loads((RUNS / "_extract.json").read_text())
BY = {r["id"]: r for r in R}

# ---- hand judgments (적합성: 적합/부적합/모호 + 한 줄 근거) ----
FIT = {
    ("fa-01", "uasl/api-design@bba608f8c974"): ("적합", "본문에 Rate Limiting 절(429, Retry-After, X-RateLimit-* 헤더, 티어 표)이 있음. 예시는 언어 중립."),
    ("fa-02", "path:…/fastapi/.agents/skills/fastapi"): ("적합", "Query 파라미터를 `Annotated`로 선언하라는 규칙이 이 태스크(쿼리 파라미터 추가)에 직접 해당. 인덱스 결과가 아니라 레포 .venv 안의 로컬 스킬을 pinned로 넣음."),
    ("fa-02", "path:…/sqlmodel/.agents/skills/sqlmodel"): ("적합", "`session.exec(select(...))`·`col()` 쿼리 작성 규칙이 title 필터 쿼리 작성에 해당. 로컬 pinned 스킬."),
    ("fa-05", "uasl/radar@a47ea6fd5f95"): ("모호", "테스트 추가 일반 규칙(변경 전후 테스트 실행, AAA, 50줄)은 해당되나, 본문 상당 부분이 다른 에이전트(Scout/Builder/Voyager)로의 라우팅·NEXUS_HANDOFF·AUTORUN 프로토콜이고 `references/` 파일 참조는 로드되지 않음."),
    ("fa-06", "uasl/python-testing-patterns@e62d0f1ca316"): ("적합", "pytest fixture·parametrize·AAA 패턴 중심. pytest 기반 페이지네이션 테스트 작성에 해당."),
    ("nx-03", "uasl/next-best-practices@ee058f89acea"): ("모호", "주제(App Router, async params, metadata)는 맞으나 본문 942토큰 대부분이 `See [async-patterns.md](./async-patterns.md)` 형태의 하위 문서 링크이고, 세션은 그 하위 파일을 읽지 않음."),
    ("nx-05", "uasl/unit-testing@6c5fbb821103"): ("모호", "Vitest/Jest AAA 예시는 해당되나 5809토큰 중 대부분이 C#/Java/Go/Python 절이고 React 컴포넌트 렌더링(Testing Library) 내용은 없음."),
    ("nx-06", "uasl/radar@a47ea6fd5f95"): ("모호", "fa-05와 동일 스킬. 테스트 추가 규칙은 해당, 라우팅/핸드오프 프로토콜 비중이 큼."),
    ("nx-06", "uasl/tdd-workflow@6eadb0bf0ea8"): ("모호", "Next.js API route 통합 테스트 예시(`NextRequest`, App Router `route.ts`)가 있으나 핵심 규칙 '테스트 먼저 쓰고 구현'은 기존 코드에 테스트만 추가하는 태스크와 맞지 않음. 예시는 Pages Router 핸들러(이 레포)와 형태가 다름."),
}

# ---- 준수: 스킬 규칙 1개 + 출력에서 확인한 사실 ----
COMPLY = {
    "fa-01": ("api-design", "한도 초과 시 `429 Too Many Requests` + `Retry-After` 헤더", "준수",
              "login.py diff: `status_code=status.HTTP_429_TOO_MANY_REQUESTS`, `headers={\"Retry-After\": ...}`; 테스트에서 `r.status_code == 429`, `int(r.headers[\"Retry-After\"]) > 0` 검증. (같은 절의 X-RateLimit-* 헤더는 diff에 없음)"),
    "fa-02": ("fastapi", "파라미터 선언은 `Annotated` 스타일 (`Query` 포함)", "준수",
              "items.py diff: `title: Annotated[ ... Query( ... description=\"Case-insensitive substring match on the item title\"`"),
    "fa-05": ("radar", "Always: Run tests before and after changes", "준수",
              "load_skills 이후 첫 Edit 전에 `uv run pytest tests/api/routes/test_login.py` 실행(DB 없어 실패 → 세션이 자체 Postgres를 initdb로 띄운 뒤 재실행), Edit 후 `pytest tests/api/routes/test_login.py`·전체 스위트 실행."),
    "fa-06": ("python-testing-patterns", "Pattern 3: 여러 입력 케이스는 `@pytest.mark.parametrize`", "준수",
              "test_items.py diff: `@pytest.mark.parametrize((\"skip\", \"limit\"), [pytest.param(0, 2, id=\"first-page\"), ...`"),
    "nx-03": ("next-best-practices", "Async Patterns: Next.js 15+에서 `params`는 async (await)", "준수",
              "app/users/[id]/page.tsx diff: `params: Promise<{ id: string }>`, `const { id } = await params;` (generateMetadata·page 둘 다)"),
    "nx-05": ("unit-testing", "AAA (Arrange-Act-Assert) 구조", "준수(구조상)",
              "List.test.tsx: 데이터 준비 → `render(...)` → 빈 줄 → `expect(...)` 순서. Arrange/Act/Assert 주석은 없음."),
    "nx-06": ("radar (precedence 1위)", "Always: Run tests before and after changes", "부분",
              "변경 전 테스트 실행 없음(레포에 테스트 러너가 없어 vitest를 먼저 설치), 테스트 작성 후 `npm test` 3회 실행. 2순위 tdd-workflow의 'Tests BEFORE Code'는 구현 변경이 없는 태스크라 확인 불가."),
}

OUTCOME = {  # 성공/실패/부분 + 근거
    "fa-05": ("부분", "error_max_turns로 종료(최종 보고 없음). 작성된 테스트 10 pass + 1 xfail, 기존 58 pass."),
}

TRIVIAL = {"fa-10", "nx-09", "nx-10"}


def fmt_int(n):
    return f"{n:,}" if isinstance(n, int) else "-"


def clean_diff(tid):
    """git numstat minus environment noise (graft .gitignore/.ignore block, .omc state) with lockfiles split out."""
    patch = (RUNS / f"{tid}.diff").read_text()
    chunks = re.split(r"(?=^diff --git )", patch, flags=re.M)
    add = dele = lock_add = lock_del = 0
    noise, side = [], []
    for ch in chunks:
        if not ch.startswith("diff --git"):
            continue
        head = ch.split("\n", 1)[0]
        m = re.match(r"diff --git a/(.*?) b/(.*)$", head)
        path = m.group(2) if m else head
        lines = ch.split("\n")
        body = [l for l in lines if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---"))]
        if "/.omc/" in "/" + path or path == ".ignore":
            noise.append(path)
            continue
        if path == ".gitignore":
            graft = {"+", "+# graft's local graph cache — regenerable, not committed (run `graft build`).", "+/graft/"}
            body = [l for l in body if l not in graft]
            if not body:
                noise.append(path)
                continue
        a = sum(1 for l in body if l.startswith("+"))
        d = sum(1 for l in body if l.startswith("-"))
        if path.endswith(("package-lock.json", "uv.lock", "bun.lock")):
            lock_add += a
            lock_del += d
            continue
        if path == "AGENTS.md":
            side.append("AGENTS.md(`next dev` 실행이 생성)")
        add += a
        dele += d
    return add, dele, lock_add, lock_del, noise, side


def turns_quote(r):
    out = []
    for i, t in enumerate(r["first3_turns"], 1):
        parts = []
        for it in t["items"]:
            if "text" in it:
                parts.append(f"text: “{it['text'].strip()[:200]}”")
            else:
                inp = it["input"]
                key = next((k for k in ("command", "pattern", "file_path", "skill", "query") if k in inp), None)
                val = str(inp.get(key, ""))[:120].replace("\n", " ").replace("|", "\\|") if key else json.dumps(inp)[:120]
                val = val.replace(f"<worktrees>/{r['id']}/", "")
                parts.append(f"`{it['tool_use']}`({key}=`{val}`)")
        out.append(f"  - T{i}: " + "; ".join(parts))
    return "\n".join(out)


def main():
    nontriv = [r for r in R if r["id"] not in TRIVIAL]
    triv = [r for r in R if r["id"] in TRIVIAL]
    fired = [r for r in nontriv if r["search_calls"]]
    misfired = [r for r in triv if r["search_calls"]]
    L = []
    w = L.append
    w("# skillfetch 실사용 테스트 0단계 — 라우터 발화 측정 (report)")
    w("")
    w("실행일 2026-10-22 (KST 15:34–15:44). 숫자는 `scripts/extract.py`가 `runs/<id>.jsonl`에서 추출, 표는 `scripts/report.py`가 생성. 적합성·준수·결과 판정 열만 수기.")
    w("")
    w("## 0. 조건 (기록)")
    w("")
    w("| 항목 | 값 |")
    w("|---|---|")
    w("| 하네스 루트 | `<e2e>` (지시의 `~/skillfetch-e2e/`는 존재하지 않아 현재 디렉터리 사용) |")
    w("| Claude Code | 2.1.280, 모델 기본값 → init `claude-opus-5-5[1m]` (사용자 설정 `model: opus[1m]`, effort high). 구독 플랜, `ANTHROPIC_API_KEY` 없음 |")
    w("| 실행 명령 | `claude -p \"<task>\" --output-format stream-json --verbose --max-turns 25 --allowedTools \"Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*\"` — `--verbose`는 print 모드 stream-json 필수 옵션이라 추가. stdin=/dev/null. 동시 4세션 |")
    w("| skillfetch | `uvx --from git+https://github.com/hyunlord/skillfetch` — 시작 시 HEAD `ccb5abd`, 종료 시 `9afa309` (실행 중 push됨; 두 커밋 차이는 README.md 1개 파일뿐) |")
    w("| 인덱스 | `skillfetch sync` 시점(준비 단계) `index-2026-10-22` built 2026-10-22T04:45:24Z. **실행 도중 15:36:26 KST에 `~/.skillfetch/index`가 외부에서 교체됨** (파일 mtime, `manifest.built_at` = 2026-10-22T06:15:43Z; 이 하네스가 한 것 아님). 서버는 시작 시 인덱스를 읽으므로 15:36:26 이전 시작 세션(fa-01, fa-02, fa-03, fa-04, fa-10)은 04:45 빌드, 나머지 15세션은 06:15 빌드 |")
    w("| 라우터 스킬 | `assets/router-skill/SKILL.md` (main) → 각 레포 `.claude/skills/skillfetch-router/SKILL.md` |")
    w("| MCP | 각 레포 `claude mcp add -s project skillfetch -- uvx --from git+… skillfetch serve` → `.mcp.json`. init 시점 skillfetch 상태: `pending` 13 / `connected` 7 (세션별 값은 요약 표 'init MCP' 열). `connected`면 init `tools`에 `mcp__skillfetch__*` 4개가 이미 있고, `pending`이면 없음. 발화 7세션은 모두 `ToolSearch`로 skillfetch 도구를 로드한 뒤 호출 |")
    w("| fastapi 레포 | `fastapi/full-stack-fastapi-template` @ `b1125d88`, 베이스라인(라우터+.mcp.json 커밋) `91132287`. 기존 테스트 58 pass. 레포 자체에 `.claude/skills/{library-skills, fastapi→.venv 심볼릭, sqlmodel→.venv 심볼릭}` 포함(업스트림 tracked; `uv sync` 후 활성). CLAUDE.md 없음 |")
    w("| nextjs 레포 | `vercel/next.js` `examples/with-typescript` @ `fa3830c4`를 독립 레포로 복사(npm install + 첫 build 후 커밋 `76de3ce2`), 베이스라인 `415e4893`. next 16.4.2, react 18.3.1. 테스트 러너 없음 → 기존 검사 = `npm run type-check` + `next build` 통과. CLAUDE.md 없음 |")
    w("| 격리 | 태스크마다 `git worktree` (`~/skillfetch-e2e-wt/<id>`, 하네스 루트 밖 — 하네스 디렉터리의 `.claude/settings.local.json`이 섞이지 않게). 세션 전 `uv sync`/`npm ci` 선실행 |")
    w("| DB | Docker 데몬 미실행 → 하네스 전용 Postgres 16 (`infra/pgdata`, :55432), 태스크별 DB `app_<id>` + alembic upgrade. 세션 env에 `DATABASE_URL`만 주입 (`.env`는 5432 그대로). `FASTAPI_ENV`는 주입 안 함 |")
    w("| 사용자 전역 환경 (그대로 상속) | `~/.claude/CLAUDE.md`, <E2 plugin> 12개, <E2 hook>, <E2 MCP server> 4개. init `skills` 목록 137개(fastapi)/134개(nextjs) 중 skillfetch-router 포함 |")
    w("| 도구 승인 | 20세션 모두 `permission_denials: []`. `Skill`·`ToolSearch`는 allowedTools에 없지만 거부 없이 실행됨. 승인 대기로 멈춘 세션 없음 |")
    w("")

    # 1
    w("## 1. 발화율")
    w("")
    w(f"- 비트리비얼 17개 중 `search_skills` 호출 세션: **{len(fired)}/17** ({', '.join(r['id'] for r in fired)})")
    w(f"- 트리비얼 3개(fa-10, nx-09, nx-10) 중 호출(오발화): **{len(misfired)}/3**")
    w(f"- `Skill(skillfetch-router)` 호출 세션: {sum(1 for r in R if any(c['input'].get('skill')=='skillfetch-router' for c in r['skill_tool_calls']))}/20 — 발화 7세션 모두 search 전에 Skill(skillfetch-router) 호출, 미발화 13세션은 0회")
    w("- 레포별: fastapi 비트리비얼 9개 중 4 (fa-01, 02, 05, 06) / nextjs 비트리비얼 8개 중 3 (nx-03, 05, 06)")
    w("- 종류별(비트리비얼): " + ", ".join(
        f"{k} {sum(1 for r in fired if r['kind']==k)}/{sum(1 for r in nontriv if r['kind']==k)}"
        for k in ("feature", "refactor", "test", "bugfix", "docs")))
    w("- 언어별(비트리비얼): " + ", ".join(
        f"{k} {sum(1 for r in fired if r['lang']==k)}/{sum(1 for r in nontriv if r['lang']==k)}" for k in ("en", "ko")))
    for st in ("pending", "connected"):
        g = [r for r in nontriv if r["init_skillfetch_status"] == st]
        w(f"- init MCP `{st}`인 비트리비얼 세션 중 발화: {sum(1 for r in g if r['search_calls'])}/{len(g)}")
    others = [(r["id"], c["input"].get("skill")) for r in R for c in r["skill_tool_calls"] if c["input"].get("skill") != "skillfetch-router"]
    w(f"- 라우터 외 Skill 호출: {', '.join(f'{i}→`{s}`' for i, s in others)} (레포 내장 `.claude/skills/` 스킬)")
    w("")

    # 2
    w("## 2. 체인 완주")
    w("")
    w("| 세션 | ToolSearch | profile_repo | search_skills | resolve_set | load_skills | load errors | 끊긴 지점 |")
    w("|---|---|---|---|---|---|---|---|")
    for r in fired:
        w(f"| {r['id']} | {len(r['toolsearch_calls'])} | {len(r['profile_calls'])} | {len(r['search_calls'])} | {len(r['resolve_calls'])} | {len(r['load_calls'])} | {len(r['load_errors'])} | 없음 (완주) |")
    w("")
    w(f"- search → resolve_set → load_skills 완주: **{sum(1 for r in fired if r['chain']=='search+resolve+load')}/{len(fired)}** (발화 세션 기준), 17개 기준 {sum(1 for r in fired if r['chain']=='search+resolve+load')}/17")
    w("- search만 하고 미로드 0, resolve 에러 0 (`errors: []`, `excluded: []`, `warnings: []` 전부), load 실패 0")
    w("- 모든 search_skills 호출에 `profile_repo` 결과를 `profile`로 전달함. fastapi 레포 profile: `frameworks: []`, `languages: [javascript, python]`, `package_managers: [bun, uv]` (FastAPI 미검출)")
    w("- fa-02: search 결과 10개 중 아무것도 고르지 않고 `auto_ids: []`, `pinned_ids: [path:…/.venv/…/fastapi/.agents/skills/fastapi, path:…/sqlmodel/.agents/skills/sqlmodel]`로 resolve. resolve notes: `no extracted constraints (run skillfetch ingest … --with-api); included without conflict checks` ×2")
    w("- fa-02 세션 텍스트 인용: “The search results from the skillfetch skill index assumed async SQLAlchemy, which this sync SQLModel codebase doesn't use”")
    w("")

    # 3
    w("## 3. 쿼리 품질 (search_skills에 넘긴 query 전부)")
    w("")
    w("| 세션 | 언어 | 원 태스크 | query | 영어 재서술 |")
    w("|---|---|---|---|---|")
    for r in fired:
        for c in r["search_calls"]:
            q = c["input"].get("query", "")
            w(f"| {r['id']} | {r['lang']} | {r['prompt']} | {q} | {'예' if r['lang']=='ko' else '(원문 영어)'} |")
    w("")
    w("- 세션당 search_skills 호출 1회 (재검색 0). 한국어 발화 4세션(fa-01, fa-06, nx-03, nx-06) 모두 영어 1문장으로 재서술, 4개 모두 대상 파일 경로 포함.")
    w("")

    # 4
    w("## 4. 선택 적합성")
    w("")
    w("| 세션 | 태스크 | 로드된 스킬 | search 결과 내 순위 | token_estimate | 판정 | 근거 |")
    w("|---|---|---|---|---|---|---|")
    n = {"적합": 0, "부적합": 0, "모호": 0}
    for r in fired:
        lc = json.loads(r["load_calls"][0]["result"])
        results = json.loads(r["search_calls"][0]["result"])["results"]
        rank = {x["id"]: i + 1 for i, x in enumerate(results)}
        for s in lc["skills"]:
            sid = s["id"]
            key_id = sid if not sid.startswith("path:") else "path:…/" + sid.split("site-packages/")[1]
            j = FIT[(r["id"], key_id)]
            n[j[0]] += 1
            rk = f"{rank[sid]}/{len(results)}" if sid in rank else "검색 결과 밖 (pinned)"
            w(f"| {r['id']} | {r['prompt']} | `{key_id}` | {rk} | {s['token_estimate']} | **{j[0]}** | {j[1]} |")
    w("")
    w(f"- 집계(스킬-태스크 쌍 {sum(n.values())}개): 적합 {n['적합']} / 부적합 {n['부적합']} / 모호 {n['모호']}")
    w("- 각 세션 search 결과 상위 10개 id는 `runs/_extract.json`의 `search_calls[].result`에 전부 있음.")
    w("")

    # 5
    w("## 5. 비용")
    w("")
    w("입력 토큰 = `usage.input_tokens + cache_creation_input_tokens + cache_read_input_tokens` (result 이벤트). 턴 = result `num_turns`. 시간 = result `duration_ms` / 하네스 측정 벽시계. load 토큰 = load_skills 응답의 `skills[].token_estimate` 합 (skillfetch 자체 추정치), 괄호는 응답 전체 문자 수.")
    w("")
    w("| 세션 | 발화 | 턴 | 입력 합계 | (uncached / cache write / cache read) | 출력 | duration_ms | 벽시계 s | API 환산 $ | load_skills 토큰 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for r in R:
        lt = f"{r['load_tokens_reported']:,} ({r['load_result_chars']:,} chars)" if r["load_tokens_reported"] else "-"
        w(f"| {r['id']} | {'Y' if r['search_calls'] else '-'} | {r['num_turns']} | {fmt_int(r['input_tokens_total'])} | {r['input_tokens_uncached']} / {fmt_int(r['cache_creation'])} / {fmt_int(r['cache_read'])} | {fmt_int(r['output_tokens'])} | {fmt_int(r['duration_ms'])} | {r['meta']['session']['wall_s']} | {r['total_cost_usd']:.2f} | {lt} |")
    def avg(rows, k):
        v = [x[k] for x in rows if isinstance(x[k], (int, float))]
        return sum(v) / len(v) if v else 0
    fired_ids = {r["id"] for r in fired}
    nf_nt = [r for r in nontriv if r["id"] not in fired_ids]
    w("")
    w("| 집단 | n | 평균 턴 | 평균 입력 | 평균 출력 | 평균 duration_ms | 평균 load 토큰 |")
    w("|---|---|---|---|---|---|---|")
    for name, rows in (("발화(비트리비얼)", fired), ("미발화(비트리비얼)", nf_nt), ("트리비얼", triv)):
        lt = avg(rows, "load_tokens_reported") if name.startswith("발화") else 0
        w(f"| {name} | {len(rows)} | {avg(rows,'num_turns'):.1f} | {avg(rows,'input_tokens_total'):,.0f} | {avg(rows,'output_tokens'):,.0f} | {avg(rows,'duration_ms'):,.0f} | {lt:,.0f} |")
    w("")
    w("- 비용은 구독 플랜 실행이라 실제 과금 아님; `total_cost_usd`는 Claude Code가 보고한 API 환산값 그대로.")
    w("- `--max-turns 25`인데 result `num_turns`가 25를 넘은 세션: " + ", ".join(f"{r['id']}({r['num_turns']}, {r['result_subtype']})" for r in R if (r['num_turns'] or 0) > 25) + ". `error_max_turns`로 끝난 세션은 fa-05(num_turns 26)뿐.")
    w("- 서브에이전트 이벤트: nx-05에서만 2건 (parent_tool_use_id 있는 이벤트), 나머지 0.")
    w("")

    # 6
    w("## 6. 준수 (로드된 스킬 규칙 1개씩)")
    w("")
    w("| 세션 | 스킬 | 확인한 규칙 | 판정 | 출력에서 확인한 사실 |")
    w("|---|---|---|---|---|")
    for r in fired:
        s, rule, v, ev = COMPLY[r["id"]]
        w(f"| {r['id']} | {s} | {rule} | **{v}** | {ev} |")
    w("")

    # 7
    w("## 7. 태스크 결과")
    w("")
    w("세션 종료 후 하네스가 worktree에서 직접 실행: fastapi `uv run pytest tests/` (`FASTAPI_ENV=development`, 태스크 DB), nextjs `npm run type-check` + `next build` (+ `test` 스크립트가 생겼으면 `npm test`). 기존 = 베이스라인에서 수집된 58개 테스트 id. diff = 베이스라인 커밋 대비 (미추적 포함) — <E2 MCP server> 훅이 쓴 `.gitignore`/`.ignore` 블록과 `<E2 plugin>/` 상태 파일은 제외, lockfile 줄은 별도 열.")
    w("")
    w("| 세션 | 기존 테스트 | 새 테스트 | type-check / build | diff +/- (정제) | lockfile +/- | 변경 파일 | 판정 |")
    w("|---|---|---|---|---|---|---|---|")
    for r in R:
        t = r["meta"]["tests"]
        a, d, la, ld, noise, side = clean_diff(r["id"])
        files = [f["file"] for f in r["meta"]["diff"]["files"] if f["file"] not in noise and "/.omc/" not in "/" + f["file"]]
        if r["repo"] == "fastapi":
            j = r["junit"]
            ex = f"{j['existing']['pass']}/58 pass"
            nw = f"{j['new']['pass']} pass" + (f", {j['new']['skipped']} xfail" if j['new']['skipped'] else "") + (f", {j['new']['fail']} fail" if j['new']['fail'] else "") if (j['new']['pass'] or j['new']['skipped'] or j['new']['fail']) else "-"
            tb = "n/a"
            ok = j["existing"]["fail"] == 0 and j["new"]["fail"] == 0 and t["pytest_rc"] == 0
        else:
            ex = "러너 없음"
            if "npm_test_rc" in t:
                m = re.search(r"Tests:?\s*(?:\S*\s*)?(\d+) passed", re.sub(r"\x1b\[[0-9;]*m", "", t["npm_test_tail"]))
                nw = f"{m.group(1) if m else '?'} pass (`{t['npm_test_script']}`, rc={t['npm_test_rc']})"
            else:
                nw = "-"
            tb = f"{'pass' if t['type_check_rc']==0 else 'FAIL'} / {'pass' if t['build_rc']==0 else 'FAIL'}"
            ok = t["type_check_rc"] == 0 and t["build_rc"] == 0 and t.get("npm_test_rc", 0) == 0
        if r["id"] in OUTCOME:
            verdict = f"{OUTCOME[r['id']][0]} — {OUTCOME[r['id']][1]}"
        else:
            verdict = "성공" if ok and r["result_subtype"] == "success" else "실패"
        sidetxt = f" (+{', '.join(side)})" if side else ""
        w(f"| {r['id']} | {ex} | {nw} | {tb} | +{a}/-{d} | {('+%d/-%d' % (la, ld)) if (la or ld) else '-'} | {len(files)}{sidetxt} | {verdict} |")
    w("")
    w("- '성공' 기준: 세션 `subtype: success` + 위 검사 전부 통과 + diff가 태스크 대상 파일을 변경. UI 동작(nx-01 검색창 등)은 브라우저로 확인하지 않음 — build 통과까지만.")
    w("- nx-05: `@types/react`·`@types/react-dom` 17→18 업그레이드 포함 (jest/RTL 설치 중 peer 충돌). nx-06: `npm install -D vitest --legacy-peer-deps`.")
    w("- fa-05: 세션이 `.env`(5432)를 보고 주입된 `DATABASE_URL`을 쓰지 않고, `initdb`로 자체 Postgres(/tmp, :54329)를 띄워 테스트 실행. 세션 종료 후에도 남아 있어 하네스가 정지·삭제함. nx-07: `next dev -p 3917` 실행 (종료 후 프로세스 없음, `AGENTS.md` 생성됨).")
    w("- 자체 브랜치 생성 4세션: fa-01 `feature/login-rate-limit`, nx-02 `feature/user-email`, nx-03 `feature/users-app-router`, nx-05 `test/list-components`. 커밋한 세션 0. diff는 베이스라인 커밋 대비.")
    w("")

    # per-session table
    w("## 세션별 한 줄 요약")
    w("")
    w("| id | 종류/언어 | 태스크 | init MCP | 발화 | 체인 | 로드 스킬 | 턴 | 결과 |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in R:
        ld = ", ".join("`" + (i.split("site-packages/")[1].split("/")[0] + "(local)" if i.startswith("path:") else i.split("@")[0]) + "`" for i in r["loaded_ids"]) or "-"
        a, d, *_ = clean_diff(r["id"])
        res = OUTCOME.get(r["id"], ("성공",))[0]
        tag = " (음성 대조군)" if r["id"] in TRIVIAL else ""
        w(f"| {r['id']} | {r['kind']}/{r['lang']}{tag} | {r['prompt']} | {r['init_skillfetch_status']} | {'Y' if r['search_calls'] else 'N'} | {r['chain']} | {ld} | {r['num_turns']} | {res}, +{a}/-{d} |")
    w("")

    # quotes
    w("## 라우터 미발화 세션의 첫 3턴 (인용)")
    w("")
    w("턴 = 메인 스레드 assistant 메시지 1개(같은 메시지 안의 병렬 도구 호출은 한 턴). 경로의 worktree 접두사는 생략. 텍스트는 200자, 인자는 120자에서 자름.")
    w("")
    for r in R:
        if r["search_calls"]:
            continue
        tag = " — 트리비얼(음성 대조군)" if r["id"] in TRIVIAL else ""
        w(f"- **{r['id']}** “{r['prompt']}”{tag}")
        w(turns_quote(r))
    w("")
    w("## 파일")
    w("")
    w("- `tasks.yaml` — 20 태스크 + 레포 커밋 해시")
    w("- `runs/<id>.jsonl` — 세션 전체 stream-json / `runs/<id>.stderr` / `runs/<id>.diff` / `runs/<id>.meta.json` (명령, 종료코드, 벽시계, diff numstat, 사후 테스트 출력) / `runs/<id>.junit.xml` (fastapi)")
    w("- `runs/loaded/<id>.md` — load_skills가 반환한 스킬 본문")
    w("- `runs/_extract.json` — 추출 결과 전체, `runs/baseline_fastapi_tests.txt` — 기존 테스트 id 58개")
    w("- `scripts/run_task.py`, `scripts/extract.py`, `scripts/report.py`; `smoke/` — 본 실행 전 환경 확인용 세션 2개 (태스크 아님)")
    (ROOT / "report.md").write_text("\n".join(L) + "\n")
    print("wrote report.md", len(L), "lines")


if __name__ == "__main__":
    main()
