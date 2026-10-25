# 10단계 파일럿 보고 (2026-10-25)

판정자가 볼 수 있는 `stage10/`에 두지 않는다(조건별 결과가 들어 있음, DESIGN §4.4).

- **실행**: 묶음 (4) 4태스크 × {A, R0, R1} × 1회(E1) = 12세션 + E2 격리 확인 2세션(s10-t016 A, R1).
  - 태그 `p0`, 원자료는 `runs/E*/*/*-p0.*`, 행은 `sessions-p0.jsonl`이다.
  - 14세션 모두 `success`이다. 사용량 한도 0, 타임아웃 0. 매 세션 전후 index 해시가 맞았다.
- **비용**: **$6.66**(14세션, API 환산; 예상 약 $11)

## 세션별

| 환경 | 태스크 | 조건 | 발화(첫 search 턴) | 로드 (run-c 등급) | 턴 | 입력 토큰 | $ | 체크 |
|---|---|---|---|---|---:|---:|---:|---|
| E1 | t016 | A | – | – | 5 | 143,569 | 0.220 | 통과 |
| E1 | t016 | R0 | 5 | 없음 | 10 | 301,708 | 0.359 | 통과 |
| E1 | t016 | R1 | 5 | m07-concurrency (3), rust-testing (2) | 14 | 422,833 | 0.483 | 통과 |
| E1 | t263 | A | – | – | 5 | 143,409 | 0.218 | 통과 |
| E1 | t263 | R0 | 5 | 없음 | 12 | 391,757 | 0.336 | 통과 |
| E1 | t263 | R1 | 5 | m01-ownership (3), m10-performance (3) | 21 | 449,097 | 0.576 | 통과 |
| E1 | t115 | A | – | – | 6 | 116,529 | 0.315 | **실패**(불건전 지적 항목) |
| E1 | t115 | R0 | 5 | 없음 | 14 | 316,233 | 0.456 | 통과 |
| E1 | t115 | R1 | 5 | unsafe-checker (3), domain-embedded (2) | 14 | 407,498 | 0.433 | **실패**(불건전 지적 항목) |
| E1 | t198 | A | – | – | 7 | 151,002 | 0.328 | 통과 |
| E1 | t198 | R0 | 5 | 없음 | 12 | 311,268 | 0.475 | 통과 |
| E1 | t198 | R1 | 5 | migration-patterns (3), core-data (3), swiftdata-architecture (2) | 14 | 431,579 | 0.484 | 통과 |
| E2 | t016 | A | – | – | 9 | 581,051 | 0.888 | 통과 |
| E2 | t016 | R1 | 5 | m07-concurrency (3), rust-testing (2) | 23 | 1,318,729 | 1.093 | 통과 |

- 로드한 스킬은 모두 run-c 라벨에 있다(추가 채점 0).
- E1 R0는 4태스크 모두 search 뒤 로드 0이다(release index에 관련 스킬 없음). E1 R1은 4/4가 등급 3 스킬을 로드했다.

## 체크 문제: t115 "불건전 지적" 항목

- A와 R1은 두 불건전 블록(`adc::sample_at`, `DmaBuffer::window`)에 SAFETY 주석을 달지 않고 그대로 두었다. 그리고 최종 답에서 둘을 이름으로 짚어 이유와 고칠 방법을 적었다.
  - A: "Not sound: no SAFETY comment added … `adc::sample_at` … undefined behaviour reachable from safe code"
  - R1: "The other 2 aren't sound, so I left them without a comment … `src/hal/adc.rs:79` – `adc::sample_at(buf, idx)`"
- R0는 코드 주석(`// FIXME(unsound): …`)으로 지적해 통과했다.
- 현재 항목은 "코드 주석에 지적어"만 인정한다(DESIGN §7에 적은 해석). 그래서 요청("Flag any you think aren't sound instead of making something up")의 타당한 수행 방식 하나를 실패로 센다.

## E2 격리 확인

- `~/.claude/skills`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md` 해시가 두 세션 모두 전후 같다.
- 쓴 도구는 Bash, Read, Edit, Write, Skill, ToolSearch, `mcp__skillfetch__*`뿐이다. permission_denials는 0이다.
- E2 init의 환경:
  - MCP 서버 26개: <E2 plugin> 서버, <E2 MCP server>, claude.ai 커넥터(<E2 MCP server>)
  - 플러그인 14개, 사용 가능한 스킬 129–130개
  - 모델 `claude-opus-5-5[1m]`(E1과 같음)
- **환경 잡음**: 사용자 <E2 MCP server> SessionStart 훅이 E2 세션의 worktree에 `.gitignore` 3줄(<E2 MCP server> 캐시 제외)과 새 파일 `.ignore`(5줄)를 썼다. 두 E2 세션 diff에 모두 들어 있고, E1 diff에는 없다.
  - 그대로 두면 블라인드 판정자가 E2 결과물을 구별할 수 있다.
  - `<E2 MCP server>/` 폴더 자체는 기존 diff 제외 목록에 있어 빠졌다.
- 레포 메인 체크아웃 4개는 모두 깨끗하다(worktree 1개, 변경 0).

## 하네스

- 첫 큐에서 s10-t016 A의 worktree 생성이 같은 레포의 동시 `git worktree add`와 충돌했다("failed to read .git/worktrees/…/commondir"). 세션은 시작하지 않았다.
- 레포별 파일 락을 넣고(`run_s10.py` `repo_lock`) 그 1건을 다시 돌렸다(통과).

## 단가와 수정 추정

- **묶음 (4) E1 실측 평균**: A $0.270, R0 $0.407, R1 $0.494. 6b 기반 가정($0.59/$0.89)보다 낮다.
- **E2 배수**(t016 한 태스크): A 4.0×($0.888 / $0.220), R1 2.3×($1.093 / $0.483). 가정했던 1.5–2.5×보다 넓다.

| 항목 | 세션 | 수정 추정 |
|---|---:|---:|
| E1 (A, R0, R1) | 135 | 약 $74 |
| E2 (A, R1) | 90 | $106–184 (배수 2.3–4.0) |
| **합계** | **225** | **$180–257** (중앙 약 $210) |

---

# 추가 (2026-10-25, 결정 1–4 반영 뒤)

## 서버 고정: 3fef3f8

- #26은 PR #75로 main `3fef3f82c7b478b3730853c2eb6efef41ac54741`에 머지됐다. 본 실행은 모든 조건(R0·R1·R1s)의 MCP 서버를 이 커밋 worktree(`~/skillfetch-e2e-wt/s10-server/3fef3f8`)로 돌린다. 앞의 파일럿 14세션은 `57acc45` 서버였다.
- `57acc45` 대비:

| 대상 | 결과 | sha256 (앞 8자) |
|---|---|---|
| `assets/router-skill/SKILL.md` | 같다 (S-b′와도 같다) | `3efef1e0` / `3efef1e0` |
| 서버 `INSTRUCTIONS`(362자) | 같다 | `04b1093f` / `04b1093f` |
| `src/` | `mcp/server.py` +15줄, `mcp/session.py` +26줄, 지운 줄 0 | – |

- 달라진 점은 도구 목록에 `resolve_and_load`가 더해진 것 하나다(R0·R1 세션에도 보인다).

## R1s 파일럿 (E1, `s10-rs` = `variants/fast.md`, staging-4, 서버 3fef3f8)

| 태스크 | 조건 | 턴 | 입력 토큰 | 비용 | skillfetch 호출 | 로드 | 체크 |
|---|---|---:|---:|---:|---|---|---|
| s10-t016 | R1s | 12 | 387,786 | $0.462 | profile_repo, search_skills, resolve_and_load | m07-concurrency, rust-testing | 통과 |
| s10-t016 | R1 (p0, 57acc45) | 14 | 422,833 | $0.483 | profile_repo, search_skills, resolve_set, load_skills | m07-concurrency, rust-testing | 통과 |
| s2-api | R1s | 15 | 534,196 | $0.717 | profile_repo, search_skills, resolve_and_load | fastapi-patterns, api-design | 통과 |

- 두 세션 모두 첫 search가 5턴째다. `resolve_and_load` 결과에서 로드 id를 뽑는 추출(절 머리 `## n. 제목 (id)` ∩ 호출 인자)이 두 세션에서 동작했다.
- 1회씩이라 R1 대비 숫자는 비교 근거가 아니다(§4.5는 본 실행 3회로 낸다).

## t115 체크 개정 뒤 재검사 (저장된 diff + 최종 답)

| 조건 | 테스트 | 함수 밖 불변 | 건전 블록 SAFETY | (a) 정당화 없음 | (b) 지적 | 통과 |
|---|---|---|---|---|---|---|
| A | ✓ | ✓ | ✓ | ✓ | ✓ (최종 답) | **통과** (앞: 실패) |
| R0 | ✓ | ✓ | ✓ | ✓ | ✓ (코드 주석) | 통과 (앞: 통과) |
| R1 | ✓ | ✓ | ✓ | ✓ | ✓ (최종 답) | **통과** (앞: 실패) |

- 확인: 참조 구현 통과, 손대지 않은 시작 커밋 실패, 정당화 SAFETY 주석을 단 합성 사례 (a)·(b) 실패.
- 첫 개정안(문단 단위)은 합성 답 "`sample_at` is unsound … `DmaBuffer::window` is fine."에서 `window`도 지적으로 셌다. 문장 단위 + 제목 규칙으로 고친 뒤 `window`는 미지적이다. 파일럿 세 답의 결과는 두 판에서 같다.

## E2 <E2 MCP server> 잡음 제거와 diff 파일 목록

| 세션 | 지운 것 | 남은 diff 파일 |
|---|---|---|
| E2 A t016 | `.gitignore` 블록(3줄), `.ignore`(5줄) | `src/lib.rs`, `src/room.rs`, `tests/history.rs` |
| E2 R1 t016 | 같음 | `src/lib.rs`, `src/room.rs`, `tests/history.rs` |
| E1 A t016 | – | `README.md`, `src/room.rs`, `tests/broadcast.rs` |
| E1 R0 t016 | – | `README.md`, `src/room.rs`, `tests/broadcast.rs` |
| E1 R1 t016 | – | `README.md`, `src/room.rs`, `tests/broadcast.rs` |

- 제거 뒤 E2 diff의 추가 줄에 <E2 plugin>·<E2 MCP server> 이름 문자열이 없다. 남은 차이(새 테스트 파일 vs 기존 테스트에 추가, `lib.rs` 수정)는 작업 방식의 차이다.
- 본 실행부터 meta에 `status_before_strip`(`git status --porcelain --ignored`)을 남겨, ignore된 경로의 환경 흔적도 E1·E2를 비교할 수 있게 했다.

## 준비

- nextjs·fastapi 메인 체크아웃이 `e2e-baseline`(옛 라우터 skill 추적)에 있어서 `s6b-a`로 바꿨다(6b 파일럿과 같은 문제·조치). 묶음 (1)–(3) 여섯 레포에 `s10-r`·`s10-rs`, `<E2 plugin>/` exclude를 넣었다.
- 큐: 누적 세션 비용(파일럿 포함) $294에서 새 세션을 멈춘다(상한 $300 − 동시 4세션 × $1.5). 끝난 작업은 건너뛰므로 같은 목록으로 다시 돌릴 수 있다.
- 누적 지출(API 환산): 파일럿 14세션 $6.66 + R1s 2세션 $1.18 = **$7.84**.
