# skillfetch 4단계 — 실제 레포에서 라우터가 실제로 무엇을 로드하나 (report)

## 0. 설정

| 항목 | 값 |
|---|---|
| skillfetch | `a1cbcd5` 고정: 라우터 SKILL.md(세 문장 재진술 → `queries`), 서버 `git+…@a1cbcd5`(다중쿼리 RRF), index-2026-10-22 |
| 레포 | 브랜치 `s4` = `s1-a` + 라우터 + `.mcp.json`(같은 고정): fastapi `af31086`, nextjs `d191fc6`. 세션마다 새 worktree + 1단계 `prepare`(fastapi: uv sync·DB·alembic, ui면 bun install; nextjs: npm ci) |
| 세션 | `claude -p` stream-json, `--include-hook-events`, `--max-turns 16`, 허용 도구 Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*, 동시 4, 고정 시드 큐 `runs/_queue.txt` |
| E1 깨끗 | `--setting-sources project --strict-mcp-config --mcp-config mcp-e1.json` (P0에서 격리 확인: `report-p0.md`) |
| E2 사용자 | 전역 `~/.claude` 그대로 (아래 E2 구성 표) |
| 태스크 | 29개 (분류별 목표 10). 후보: 3단계 python/ts_react_next 130 + 다른 스택 expect_none 26 (1차), 1차에 모자란 분류를 채우려 다른 스택의 3단계 select/restate/search 실패 40 (2차). 실제 레포에 맞춰 고쳐 씀(`gen/sys-adapt.txt`), 제목 토큰 누출 0 |
| oracle | 3단계와 같은 파이프라인(2a → 2b → 3-0, 같은 프롬프트), 검색은 그 레포의 `profile_repo` 결과로; 3-0은 Q2·Q3 top-10 추가; 1차: 관련 쌍 94 → 116 (3-0 새 관련 22), 관련 없음 1/40; 2차: 관련 쌍 293 → 369 (3-0 새 관련 76), 관련 없음 42/156 |
| 오프라인 분류 | 라우터의 실제 질의 = Q3(라우터 1단계 규칙으로 쓴 문장들, `queries`) + profile, k=50 compact → 라우터 'When'·4단계로 선택. select_fail = 관련이 Q3 top-50에 있는데 안 고름 · restate_fail = Q3 top-50 밖, Q1 또는 Q2 top-50 안 · search_fail = 어디에도 없음 · over_load = 관련 없음인데 로드 |
| 분류별 후보 수 (1+2차 전체) | over_load 14, ok 158, search_fail 7, select_fail 15, restate_fail 2 |
| 선정 | select_fail 10, restate_fail 2, search_fail 7, over_load 10; 모자람: restate_fail 8, search_fail 3 |
| 세션 수 | 174 (= 29 × 2 환경 × 3) |
| 4-0 보정 (실행 후) | 세션이 로드했거나 오프라인 선택이 고른 스킬 중 oracle 풀에 없던 35개를 같은 2b 프롬프트로 채점(20태스크, $0.22), 그중 등급≥2 13. 아래 지표는 이 v3 라벨 기준. 층(오프라인 분류)은 선정 때 값 그대로 두고, v3로 다시 매기면 바뀌는 태스크 8개: s4-t027 select_fail→ok, s4-t253 select_fail→ok, s4-t055 restate_fail→ok, s4-t033 search_fail→ok, s4-t130 search_fail→ok, s4-t224 search_fail→ok, s4-t280 over_load→select_fail, s4-t001 over_load→search_fail |
| 준비 비용 | 배치 호출(고쳐 쓰기·2a·2b·쿼리·3-0·선택·4-0, `gen/raw/*.json`의 cost_usd 합) $29.85 (설계 추정 $8–15) |
| 정리 | 본 실행 후 stage-4 DB 158개(fastapi 세션 + P0) 삭제, Postgres(55432) 정지, worktree prune. E2의 <E2 MCP server> SessionStart 훅이 백그라운드로 만든 `<E2 MCP server>/` 색인이 worktree 삭제 뒤 3개 남아 있어 지웠다(세션 작업물 아님) |
| 로컬 skill 핀 | 1세션이 레포의 `.claude/skills/` skill을 `path:`로 핀 → 등급 없음, precision·잘못 로드에서 뺌 |

## 환경 구성 (init 이벤트, 세션별)

| 환경 | MCP 서버 | 플러그인 | skill 수 | agent 수 | 도구 수 | 훅 이벤트 종류 (발생 세션) |
|---|---|---|---|---|---|---|
| E1 | 1: skillfetch | 사용자 0 + 내장 2 | 19–22 | 5–5 | 34–34 | 없음 |
| E2 | 14 (skillfetch + <E2 MCP server> 13) | 사용자 12 + 내장 2 (<E2 plugin> 12) | 134–137 | 54–54 | 119–151 | PostToolUse (87/87), PostToolUseFailure (11/87), PreToolUse (87/87), SessionStart (87/87), Stop (82/87), UserPromptSubmit (87/87) |

## 표 1. 환경 × 지표

| 환경 | 세션 | 발화 | (a) 라우터 경유 | (b) MCP 직접 | 라우터만(MCP 없음) | search 도달 | resolve_set | load 1개 이상 | 16턴 캡 | 첫 search 턴 중앙 (범위) | 첫 search 시각 중앙 s | MCP ready 중앙 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 87 | 23/87 | 23/87 | 0/87 | 0/87 | 22/87 | 16/87 | 14/87 | 1/87 | 5.0 (5–7) | 15.4 | 1.6 |
| E2 | 87 | 23/87 | 23/87 | 0/87 | 1/87 | 22/87 | 19/87 | 17/87 | 5/87 | 5.0 (5–10) | 16.9 | 2.9 |

E2 캡 도달 비율 6%

### 사소한 태스크(라우터가 건너뛰라는 종류) vs 그 외

| 환경 | 태스크 종류 | 세션 | 발화 | search 도달 | load 1개 이상 | 16턴 캡 |
|---|---|---|---|---|---|---|
| E1 | trivial | 30 | 0/30 | 0/30 | 0/30 | 0/30 |
| E1 | 그 외 | 57 | 23/57 | 22/57 | 14/57 | 1/57 |
| E2 | trivial | 30 | 1/30 | 1/30 | 1/30 | 1/30 |
| E2 | 그 외 | 57 | 22/57 | 21/57 | 16/57 | 4/57 |

### search까지 갔지만 load_skills를 안 부른 세션

원인: 16턴 캡 = 마지막 skillfetch 호출 뒤 도구 2번 안에 캡으로 끝남 · resolve_set 후 멈춤 = resolve_set을 불렀고 캡 때문이 아님 · 선택에서 none = resolve_set을 안 불렀고 캡 때문이 아님

| 환경 | search 도달 | 그중 load 없음 | 16턴 캡 | resolve_set 후 멈춤 | 선택에서 none |
|---|---|---|---|---|---|
| E1 | 22 | 8 | 0 | 2 | 6 |
| E2 | 22 | 5 | 0 | 2 | 3 |

## 표 1b. 첫 도구 귀속

① <E2 plugin> 훅(UserPromptSubmit 훅이 <E2 hook text>를 넣고 첫 도구가 Skill(<E2 plugin>:*)) · ② 다른 skill · ③ 전역 규칙(git status/branch) · ④ 규칙 없이 탐색 · ⑤ 라우터가 먼저

| 환경 | ① <E2 plugin> 훅 | ② 다른 skill | ③ 전역 규칙 git | ④ 탐색 | ⑤ 라우터 먼저 | 도구 없음 | 첫 도구 상위 |
|---|---|---|---|---|---|---|---|
| E1 | 0 | 0 | 0 | 64 | 23 | 0 | Read 25, Grep 23, Skill(skillfetch-router) 23, Bash 15, Glob 1 |
| E2 | 0 | 0 | 12 | 52 | 23 | 0 | Read 25, Skill(skillfetch-router) 23, Grep 20, Bash 15, Glob 4 |

## 표 2. 오프라인 분류 × 환경: 세션 분류

세션 분류: no_search = search 안 함 · 나머지는 오프라인 규칙(관련이 세션 자신의 top-50에 있으면 select_fail, 아니면 오프라인 Q1/Q2/Q3 top-50에 있으면 restate_fail)

| 오프라인 분류 | 환경 | 세션 | ok | select_fail | restate_fail | search_fail | over_load | no_search |
|---|---|---|---|---|---|---|---|---|
| select_fail | E1 | 30 | 1 | 5 | 2 | 0 | 0 | 22 |
| select_fail | E2 | 30 | 2 | 4 | 0 | 0 | 0 | 24 |
| restate_fail | E1 | 6 | 1 | 1 | 0 | 0 | 0 | 4 |
| restate_fail | E2 | 6 | 2 | 0 | 0 | 0 | 0 | 4 |
| search_fail | E1 | 21 | 6 | 2 | 0 | 0 | 0 | 13 |
| search_fail | E2 | 21 | 2 | 1 | 0 | 2 | 0 | 16 |
| over_load | E1 | 30 | 0 | 0 | 0 | 0 | 4 | 26 |
| over_load | E2 | 30 | 5 | 0 | 0 | 0 | 4 | 21 |

## 표 3. 반복 간 Jaccard (첫 search top-50)

| 환경 | 쌍 수 | 평균 | 중앙 | 완전 일치 쌍 | 반복 간 쿼리 문장이 달랐던 태스크 | 세션 top-50 vs 오프라인 Q3 top-50 평균 |
|---|---|---|---|---|---|---|
| E1 | 14 | 0.618 | 0.626 | 1/14 | 8 | 0.439 |
| E2 | 7 | 0.688 | 0.667 | 0/7 | 7 | 0.464 |

## 표 4. 로드 세트 vs oracle, 오프라인 선택 대비

| 환경 | precision (로드한 세션) | recall (관련 있는 태스크) | 적중 (관련 있는 태스크 세션) | 적중 (그중 로드한 세션) | 잘못 로드 합 | 과잉 로드율 (관련 없는 태스크) | 오프라인과 세트 완전 일치 | 오프라인 대비 Jaccard 평균 | 분류 일치 |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 0.500 | 0.053 | 8/63 | 8/10 | 9 | 4/24 | 18/87 | 0.216 | 9/87 |
| E2 | 0.500 | 0.106 | 10/63 | 10/13 | 10 | 4/24 | 18/87 | 0.224 | 10/87 |

오프라인 분류별 (세션 수, 세트 완전 일치, 분류 일치, Jaccard 평균):

| 오프라인 분류 | 환경 | 세션 | 세트 일치 | 분류 일치 | Jaccard |
|---|---|---|---|---|---|
| select_fail | E1 | 30 | 14 | 5 | 0.467 |
| select_fail | E2 | 30 | 14 | 4 | 0.478 |
| restate_fail | E1 | 6 | 3 | 0 | 0.556 |
| restate_fail | E2 | 6 | 3 | 0 | 0.611 |
| search_fail | E1 | 21 | 1 | 0 | 0.071 |
| search_fail | E2 | 21 | 1 | 2 | 0.071 |
| over_load | E1 | 30 | 0 | 4 | 0.000 |
| over_load | E2 | 30 | 0 | 4 | 0.000 |

## 환경 효과 (태스크별 3회 평균, E1 − E2)

| 지표 | 태스크 | 평균 차 (E1−E2) | E1 > E2 | E1 < E2 | 같음 |
|---|---|---|---|---|---|
| 발화 | 29 | 0.000 | 6 | 7 | 16 |
| search 도달 | 29 | 0.000 | 6 | 6 | 17 |
| load 1개 이상 | 29 | -0.034 | 4 | 7 | 18 |
| 16턴 캡 | 29 | -0.046 | 0 | 4 | 25 |

## 비용·시간

| 환경 | 세션 | 비용 합 $ | 세션 비용 중앙 $ | 입력 토큰 중앙 | 턴 중앙 | 세션 시간 중앙 s |
|---|---|---|---|---|---|---|
| E1 | 87 | 17.27 | 0.16 | 163529 | 7 | 29.6 |
| E2 | 87 | 49.08 | 0.57 | 586997 | 9 | 47.3 |

## 결론 (숫자만)

태스크 29개(그중 trivial 10; 분류별 목표 10; 모자람 restate_fail 8, search_fail 3), 세션 174. 발화: E1 23/87, E2 23/87; search 도달: E1 22/87, E2 22/87; load 1개 이상: E1 14/87, E2 17/87; 16턴 캡: E1 1/87, E2 5/87. trivial 외 태스크의 발화: E1 23/57; E2 22/57. 로드 세트(v3 라벨): E1 로드한 세션 14, 그중 관련 적중 8; E2 로드한 세션 17, 그중 관련 적중 10. 오프라인 선택과 세트 완전 일치: E1 18/87; E2 18/87. 비용: E1 $17.27; E2 $49.08. search 후 load 없음 (캡 / resolve 후 멈춤 / none): E1 0 / 2 / 6; E2 0 / 2 / 3.

