# 4단계 P0 파일럿 (4세션, 격리 확인·비용)

skillfetch `a1cbcd5`(서버 `.mcp.json`/`mcp-e1.json` 모두 `git+…@a1cbcd5`, 라우터 SKILL.md도 a1cbcd5). 레포 브랜치 `s4`(fastapi `af31086`, nextjs `d191fc6`) = `s1-a` + 라우터 + `.mcp.json`. 태스크 s1-fa-06(fastapi 테스트), s1-nx-08(nextjs 테스트). `--max-turns 16`, `--include-hook-events`, 동시 4. 러너 `scripts/run_session.py`, 집계 `scripts/pilot_report.py`.

## E1 격리 기준

| 기준 | E1 s1-fa-06 | E1 s1-nx-08 | E2 (대조) |
|---|---|---|---|
| init `mcp_servers` | skillfetch 1개 | skillfetch 1개 | 14개 (skillfetch + <E2 MCP server> 13) |
| `plugins` | agents-md, telemetry (내장) | 같음 | 14개 (<E2 plugin> 12 + 내장 2) |
| `skills` | 22: skillfetch-router, 레포 동봉 library-skills·fastapi·sqlmodel, 내장 18 | 19: skillfetch-router, 내장 18 | 137 / 134 (plugin and user skills; names not published) |
| 훅 이벤트 (`--include-hook-events`) | 0 | 0 | SessionStart 9, UserPromptSubmit 4, Pre/PostToolUse 전 도구 (<E2 plugin>·<E2 MCP server> 3개가 SessionStart에 문맥 주입) |
| 사용자 `~/.claude/CLAUDE.md` (debug log) | 언급 0 | 언급 0 | 로드됨 |
| agents / tools | 5 / 34 | 5 / 34 | 54 / 147·151 |

auto memory 경로(`~/.claude/projects/…repos-{fastapi,nextjs}/memory/`)는 비어 있었고 실행 후에도 비어 있다. → `CLAUDE_CONFIG_DIR` 교체 불필요.

## 세션별

| 환경 | 태스크 | 결과 | num_turns | 비용 $ | 입력 토큰 | 세션 s | 준비 s | 첫 도구 | skillfetch 호출 |
|---|---|---|---|---|---|---|---|---|---|
| E1 | s1-fa-06 | success | 18 | 0.50 | 624,834 | 91.3 | 4.9 | Skill(skillfetch-router) | profile → search → resolve → load |
| E1 | s1-nx-08 | success | 16 | 0.43 | 402,350 | 57.0 | 7.5 | Skill(skillfetch-router) | profile → search → resolve → load |
| E2 | s1-fa-06 | error_max_turns | 17 | 1.28 | 1,528,636 | 90.6 | 4.9 | Skill(skillfetch-router) | profile → search → resolve → load |
| E2 | s1-nx-08 | error_max_turns | 17 | 1.08 | 1,519,872 | 93.3 | 7.4 | Skill(skillfetch-router) | profile → search → resolve → load |

파일럿 합계 $3.29.

## 본 실행 추정 (240세션) 수정

E1 평균 $0.46 × 120 = $56, E2 평균 $1.18 × 120 = $142 → 세션 약 $200, 준비 단계 $8–15 포함 약 $210–215 (설계 추정 $180–260 안). 세션 57–93 s + 준비 5–8 s(캐시 있음), 동시 4로 벽시계 약 1.5시간.

## 기록 사항

- E2 2세션 모두 16턴 캡(`error_max_turns`); E1은 둘 다 캡 전에 끝남. 설계상 E2 캡 비율이 10%를 넘으면 발화율·검색 도달률에 "16턴 내"를 붙인다.
- E1의 레포 동봉 skill(fastapi 레포의 `.claude/skills/library-skills`, `fastapi`, `sqlmodel`)은 두 환경에 같이 있다(사용자 설정 아님).
- E1 세션의 stream-json은 E2보다 늦게 몰아서 나왔다(실행 중 0줄). 결과에는 영향 없음.
- 4세션 모두 라우터가 첫 도구였고 체인 전체를 호출했다(파일럿 n=4, 발화율 추정 아님).
