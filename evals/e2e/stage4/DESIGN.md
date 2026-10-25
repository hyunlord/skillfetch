# 4단계 설계 — 실제 레포에서 라우터가 실제로 무엇을 로드하나 (실행 전, 설계만)

**목적**: 3단계 e2e가 못 한 검증을 다시 한다. 3단계는 빈/스텁 레포라 search까지 간 세션이 40개 중 12개였다. 이번에는 실제 레포(manifest 포함)에서 라우터 발화 → 검색 → 로드가 오프라인 예측과 얼마나 맞는지, 사용자 설정이 그것을 얼마나 바꾸는지 잰다.
**실행 조건**: 다중쿼리(Q3: 도메인·작업방식·스택 3문장 검색 후 RRF)가 skillfetch main의 search_skills(또는 라우터 4단계)에 머지된 뒤 실행한다. 그 커밋에 서버·라우터를 고정한다(`.mcp.json`의 `git+…@<sha>`). 순서는 P0 파일럿 4세션 → 파일럿 결과(격리 확인·비용) 보고 → 승인 → 본 실행 240세션이다.

## 구성 — 2 레포 × 40 태스크 × 2 환경 × 3 반복 = 240세션

| 축 | 값 |
|---|---|
| 레포 | 1단계와 같은 `repos/fastapi`(full-stack template, `b1125d88`, uv/bun manifest)와 `repos/nextjs`(with-typescript, `76de3ce2`, package.json). 세션마다 새 worktree, 의존성 설치(1단계 `prepare`) |
| 태스크 40 | 실패 분류별 10개: select_fail · restate_fail · search_fail · over_load. 3단계 태스크 중 python / ts_react_next(각 50)와 expect_none·관련 없음 태스크를 후보로 하고, 실제 레포의 파일·모듈을 가리키도록 배치 프롬프트로 고쳐 쓴다(작업종류·표현·방향은 유지). 고친 태스크는 3단계 파이프라인(2a → 2b → 3-0 확장, 같은 프롬프트)으로 oracle을 다시 만들고, **그 레포의 `profile_repo` 결과를 넣은** 오프라인 Q2·Q3 검색과 선택으로 분류를 다시 매긴 뒤 분류별 10개를 고른다. 10개가 안 되는 분류(3단계 search_fail은 380개 중 7개)는 후보를 더 만들고, 그래도 모자라면 모자란 대로 기록한다 |
| 환경 E1 깨끗 | 전역 RULES.md·CLAUDE.md·훅·플러그인·다른 스킬 없음. skillfetch MCP와 레포의 라우터 skill만. 방법: `--setting-sources project` + `--strict-mcp-config --mcp-config <skillfetch만>`. 사용자 메모리(`~/.claude/CLAUDE.md`)가 이 모드에서도 실리면 `CLAUDE_CONFIG_DIR`를 비어 있는 설정 디렉터리로 바꾸고 로그인을 다시 한다. `--bare`는 API 키 전용이라 못 쓴다 |
| 환경 E2 사용자 | 지금 그대로(1–3단계와 같음: 전역 `~/.claude` 상속, <E2 plugin>·<E2 plugin>·<E2 plugin> 훅과 스킬 포함) |
| 반복 | 3회, 같은 프롬프트, 새 worktree |
| 세션 | 1–3단계 하네스(`claude -p` stream-json, 허용 도구 Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*, debug log). 두 환경 모두 `--include-hook-events`를 켜서 훅이 넣은 문맥까지 기록한다. **`--max-turns 16`**: 1단계에서 load_skills는 중앙 6번째 메시지였지만, E2는 "git status 먼저" 같은 규칙 때문에 검색이 뒤로 밀린다. 12턴에서 끊으면 E2 발화율이 깎일 수 있어 16턴으로 했다. 작업 결과물은 채점하지 않는다 |

**P0 파일럿(본 실행 전, 4세션 — 결과는 본 실행 전에 보고하고, 승인을 받은 뒤 본 실행)**: E1 격리 확인. 기준은 4가지다.
- init 이벤트의 `mcp_servers`가 skillfetch 하나다.
- `plugins`에 사용자 플러그인이 없다.
- `skills`에 router(와 내장 스킬)만 있다.
- `--include-hook-events`에 사용자 훅이 없다.

E1·E2 각 2세션으로 비용과 시간도 실측해 아래 추정을 고친다.

## 지표 (태스크 × 환경마다, 반복 3회 기준)

| 지표 | 정의 |
|---|---|
| 발화율 | skillfetch를 쓴 세션의 비율. **발화 경로를 둘로 나눠** 센다. (a) 라우터 skill 경유: 첫 `mcp__skillfetch__*` 호출보다 앞에 `Skill(skillfetch-router)` 호출이나 라우터 SKILL.md Read가 있다. (b) skill 없이 MCP 직접: 그런 호출 없이 `mcp__skillfetch__*`(ToolSearch로 로드한 뒤 포함)를 불렀다. (a)는 skill description이 레버라는 근거, (b)는 MCP 서버 instructions가 레버라는 근거가 된다. 라우터를 불렀지만 MCP 호출이 없는 세션도 따로 센다 |
| 검색 도달률 | search_skills를 1회 이상 부른 세션 비율. 세션마다 **search_skills가 처음 불린 턴 번호**(메인 스레드 assistant 메시지 순번)와 시각, 첫 skillfetch 호출 시각, MCP ready 시각을 기록한다. **캡(16턴)에 걸려 끝난 세션 수**(`error_max_turns`)는 환경별로 따로 보고한다. E2에서 그 비율이 10%를 넘으면 발화율과 검색 도달률은 "16턴 내"라고 범위를 붙여 적는다 |
| top-50 반복 간 Jaccard | 같은 태스크·환경의 3회 사이, 첫 search 결과 50개 id 집합의 쌍별 Jaccard 평균(3쌍). 쿼리 문장 자체의 차이도 기록. 3단계 오프라인 Q2 대비 Jaccard도 함께 |
| 로드 세트 vs oracle | load_skills 결과의 precision, recall, 적중(관련 1개 이상), 잘못 로드(등급<2) 수. 실패 분류별로, 그리고 오프라인 선택과의 일치(완전 일치, Jaccard, 분류 일치) |
| 과잉 로드율 | oracle 관련 없음인 태스크(over_load 10개 + 다른 분류의 관련 없음)에서 1개 이상 로드한 세션 비율 |
| 첫 도구 귀속 (E2) | 라우터 대신 세션의 첫 행동을 차지한 것을 세션당 하나로 귀속해 표로 만든다. 판정 순서(앞이 우선): ① **<E2 plugin> 훅** — 첫 도구 직전에 UserPromptSubmit 훅이 문맥을 넣었고(`<E2 hook text>` 등, 훅 이벤트로 확인) 첫 도구가 그 지시를 따른다(예: `Skill(<E2 plugin>:*)`). ② **다른 skill** — 첫 도구가 라우터 아닌 `Skill(...)`. ③ **전역 RULES.md 규칙** — 첫 도구가 `git status`/`git branch`를 포함한 Bash(RULES.md "Start every session with git status"). ④ **규칙 없이 탐색** — 첫 도구가 Read/Glob/Grep 또는 git 아닌 Bash. ⑤ **라우터가 먼저**. E1에도 같은 분류를 적용해 대조군으로 쓴다 |
| 환경 효과 | 위 지표들을 E1−E2로 비교. 태스크마다 3회 평균을 내고, 태스크 40개에 대해 짝지은 차이와 그 부호 개수를 본다 |

## 비용 추정 (API 환산, 실측 기반)

1–3단계에서 실제로 잰 세션 중앙값을 기준으로 했다.

| 근거 | 세션당 비용 | 입력 토큰 | 턴 | 시간 |
|---|---|---|---|---|
| 1단계 C (실제 레포, max-turns 25) | $0.91 | 1.23M | 19 | 75 s |
| 2단계 C2 (max-turns 40) | $1.30 | 1.54M | 18.5 | 181 s |
| 3단계 e2e (스텁 레포, max-turns 12) | $0.61 | 0.40M | 6 | 35 s |

- **240세션, max-turns 16**: 실제 레포에서는 세션이 작업까지 이어지므로 3단계 12턴 값($0.61, 중앙 6턴)보다 1단계 값($0.91, 중앙 19턴)에 가깝게 본다. 세션당 $0.7–1.0 → 약 **$170–240**. 동시 4개로 벽시계 약 1.5–2시간(설치 포함). E1은 전역 지시문이 빠져 턴당 입력이 줄어들므로 이 범위의 아래쪽일 것으로 본다(P0에서 확인).
- **준비 단계**(태스크 고쳐 쓰기, oracle 재라벨, 오프라인 재분류): 배치 호출 약 150–250회, 약 $8–15(3단계 2a·2b·3-0 실측 단가 기준).
- **합계 약 $180–260**, P0 포함. 반복을 5회로 늘리면 약 $290–420.

## 산출물
`stage4/`에 다음을 둔다.
- 데이터: `tasks.jsonl`(40), `oracle.jsonl`, `offline.jsonl`, `runs/E{1,2}/<task>-r{1,2,3}.*`, `sessions.jsonl`
- 보고서: `report-stage4.md`
  - 표 1: 환경 × 지표(발화 경로 (a)/(b) 분리, 첫 search 턴 분포, 캡 도달 세션 수 포함)
  - 표 1b: 첫 도구 귀속(E2, E1 대조)
  - 표 2: 실패 분류 × 환경
  - 표 3: 반복 간 Jaccard 분포
  - 표 4: 오프라인 대비 일치
  - 결론 한 문단(숫자만)

## 알려진 한계
- oracle과 라우터가 같은 모델이다.
- 태스크를 실제 레포에 맞춰 고쳐 쓰므로, 3단계 분류는 그대로 옮기지 않고 다시 매긴다.
- nextjs 스타터는 작아서(추적 파일 16개) 일부 태스크 유형을 담기 어렵다. 그런 태스크는 fastapi 쪽으로 몰린다.
- n=3 반복이라 세션 간 변동의 추정치는 거칠다.
