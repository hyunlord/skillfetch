# 5단계 설계 — 발화 레버 (실행 승인됨; 시작 조건: 라우터 승자 R-c가 main에 머지된 커밋으로 고정)

**개정 (2026-10-23)** — `14d2020`(PR #45, feat `d95e3f0`): `assets/router-skill/SKILL.md`가 `stage3/router-cands/R-c/SKILL.md`와 바이트 단위로 같음, `a1cbcd5` 이후 `src/`는 `cli.py`·`evals.py`만 변경(검색·MCP 불변).
- V0 = 새 라우터(R-c, `stage3/router-winner.md`)를 머지 커밋 `14d2020`에 고정한 것.
- 4단계에서 "코드가 없다"로 끝난 7개 태스크를 다시 쓰고 oracle을 재라벨했다(아래 "태스크").
- 4단계 수치와 직접 비교하는 것은 바뀌지 않은 10태스크로 한정한다. 이 비교에는 라우터 변경이 함께 섞인다.

**목적**: 4단계에서 사소하지 않은 태스크의 라우터 발화는 E1 23/57, E2 22/57이었다. 무엇을 바꿔야 발화가 오르는지 찾는다.
- 발화 경로는 전부 (a) 라우터 skill 경유였고, (b) MCP 직접 호출은 0이었다.
- 첫 도구는 E1에서도 탐색(Read·Grep·Bash)이 64/87이었다. 전역 RULES.md·훅이 없는 환경에서도 같다.
- 후속 분석 1: 발화는 태스크에 일부 묶이지만 확률적인 부분이 크다(태스크별 발화 수 분산이 이항의 1.7배, χ² 31.0 / 18 df). 그래서 변형 간 차이는 태스크를 짝지어 본다.

## 구성 — 4 변형 × 19 태스크 × 3 반복 = 228세션, E1만

| 항목 | 값 |
|---|---|
| 태스크 | `stage5/tasks.jsonl` 19개 = 4단계의 사소하지 않은 태스크. 그중 9개는 레포 실제 코드를 가리키도록 다시 썼다. 처음 7개(s4-t027·t033·t203·t211·t224·t229·t253)는 키워드 집계로 골랐다. 본 실행 시작 직후 `stage4/missing-code.json`(손 분류, 전 회차 "코드 없음")에 2개(s4-t026·t177)가 더 있음을 확인했다. 그래서 큐를 멈추고 같은 방법(3차, 두 규칙 모두)으로 다시 썼다. 첫 7개는 레포 실제 코드를 가리키도록 다시 썼다(`stage4/scripts/readapt_missing.py`). 방법: `sys-adapt.txt` 규칙에 "존재한다고 말하는 것은 아래 소스에 있어야 한다"를 더하고, 레포 `s4` 브랜치 소스 전체를 시스템 프롬프트에 넣었다. 1차에서 t027·t033이 한 줄 수정(라우터 skip 대상)으로 나와, 이 둘만 "한 줄 수정보다 큰 작업" 규칙을 더해 2차로 다시 썼다. 각 태스크가 말한 함수·필드·동작은 `git show s4:<file>`로 하나씩 대조해 모두 확인했다. 작업종류·표현·레포는 유지했다. oracle은 `stage5/oracle.jsonl`이다. 바뀌지 않은 10개는 4단계 v3 라벨이다. 다시 쓴 9개는 4단계 파이프라인(2a → 2b → 3-0)을 다시 돌렸다(7개 $0.56, 2개 $0.85). 관련 없음 태스크는 19개 중 4개 |
| 환경 | 4단계 E1 그대로: `--setting-sources project --strict-mcp-config --mcp-config <skillfetch만>`, `--include-hook-events`, `--max-turns 16`, 같은 허용 도구, 1단계 `prepare`, 세션마다 새 worktree |
| 서버 설치 | 네 변형 모두 같은 방식이다. 로컬 worktree에서 `uvx --from <worktree 경로> skillfetch serve`. V0–V2는 `14d2020` 그대로, V3는 `14d2020` + `INSTRUCTIONS` 한 곳만 바꾼 로컬 브랜치 `exp/mcp-instructions-v3`(push하지 않음) |
| V0 | 새 라우터. 레포 브랜치 `s5` = `s4` + `14d2020`의 `assets/router-skill/SKILL.md`(`.claude/skills/skillfetch-router/`) + `.mcp.json` 핀 `@14d2020`. 4단계 `s4`와는 이 두 파일만 다르다. V1 = `s5-v1`(description만), V2 = `s5-v2`(`CLAUDE.md` 추가). 서버는 `--mcp-config`로 로컬 worktree를 가리킨다(E1은 `--strict-mcp-config`라 레포 `.mcp.json`은 쓰이지 않는다) |
| V1 | 라우터 SKILL.md의 frontmatter `description`만 바꾼다(아래 문구). 본문은 그대로 |
| V2 | V0 + 레포 루트에 프로젝트 `CLAUDE.md` 한 줄(아래). 이 템플릿 레포에는 원래 CLAUDE.md가 없다. 있으면 맨 끝에 붙인다 |
| V3 | V0 + MCP 서버 `INSTRUCTIONS`만 바꾼다(아래). 라우터 skill은 그대로 |
| 큐 | 고정 시드로 변형·태스크·반복을 섞는다. 동시 4. 같은 태스크의 네 변형이 비슷한 시각에 돌도록 블록 순서로 짠다 |

## 각 변형의 정확한 문구

**V0 — description** (`a1cbcd5`와 같다. R-c는 description을 바꾸지 않았다):
> Use at the start of any coding task that adds or changes code, tests, docs or config (more than a one-line edit in one file), fixes a bug, or starts a feature — before reading the codebase. Skip only a one-line edit in a single file, a rename, or answering a question.

**V0 — MCP instructions** (server.py; `14d2020`에서 `a1cbcd5`와 같음을 확인):
> skillfetch finds vetted skills (SKILL.md instructions) for one task at a time. Before non-trivial work, restate the task in one sentence with its stack and target files and call search_skills; read the 50 summaries and pick 1-3; call resolve_set (user-named skills go in pinned_ids); then load_skills and follow the returned content. Skip this for trivial edits.

**V1 — description 재작성** (첫 행동 지시를 맨 앞에, 탐색 도구를 이름으로 막음):
> Run this before your first tool call — before git status, Read, Grep, Glob or ls — whenever the user asks for a code change: a feature, a bug fix, a refactor, tests, docs, config, CI or deploy work, even if it looks small. It loads the skills for the task in four quick MCP calls. Skip it only for a one-line edit in one file, a rename, or a question with no edits.

**V2 — 프로젝트 `CLAUDE.md` 한 줄**:
> Before your first tool call on any coding task in this repository (anything beyond a one-line edit, a rename or a question), run the `skillfetch-router` skill and follow its steps.

**V3 — MCP instructions 강화** (MCP 직접 경로 (b)를 열 수 있는지 본다):
> Call this server first, before reading or searching the repository, for every coding task that is more than a one-line edit, a rename or a question. Restate the task as three short English sentences (what it builds or fixes; the kind of work and how to do it; the stack and files), add the user's request word for word, and pass all four to search_skills as `queries`; read the 50 summaries and pick 1-3; call resolve_set; then load_skills and follow the returned content.

V3의 instructions에서 재진술 문장이 새 라우터 1단계(R-c: 세 문장 + 원문)와 맞게 바뀐다. 이 차이는 V3 결과에 함께 섞인다(기록).

## 지표 (변형마다; 4단계와 같은 정의, 같은 추출 스크립트)

| 지표 | 정의 |
|---|---|
| 발화율 | (a) 라우터 경유 / (b) MCP 직접 / 라우터만(MCP 없음) 분리. 다시 쓴 9개와 바뀌지 않은 10개를 따로도 |
| 검색 도달률·로드율 | search 1회 이상, load_skills 1개 이상 |
| 첫 search 턴 | 중앙·범위. 16턴 캡 세션 수 |
| 첫 도구 귀속 | 4단계 표 1b 분류(⑤ 라우터 먼저의 비율이 주 관심) |
| 비용 | 세션 비용·입력 토큰·시간 |
| 변형 효과 | 태스크마다 3회 발화 수(0–3)로 Vk − V0의 짝지은 차이. 평균 차, 증가/감소/같음 태스크 수, 부호 검정 |

**검출력**: 변형당 57세션(p ≈ 0.4)에서 두 비율 차의 95% 오차는 약 ±0.18이다. 태스크 짝짓기로 조금 줄어든다. 차이가 그보다 작으면 "구별 불가"로 적는다. ±0.13이 필요하면 반복을 6회로 늘린다(456세션).

## 비용 추정 (4단계 E1 실측: 사소하지 않은 태스크 세션 평균 $0.233, 발화 세션 $0.331, 비발화 $0.167, 세션 시간 중앙 33 s)

| 시나리오 | 세션당 | 228세션 |
|---|---|---|
| 발화율 그대로(0.4) | $0.23 | 약 $53 |
| 변형이 발화를 끝까지 올림(1.0) | $0.33 | 약 $75 |

- 합계 약 **$55–80**(API 환산). 준비 비용은 거의 없다(배치 호출 없음; 라벨은 4단계 v3 재사용).
- 실행 후 4-0식 보정이 있다. 로드됐거나 R-c 쿼리 top-10에 들었는데 풀에 없던 스킬을 같은 2b 프롬프트로 채점한다. 4단계에서는 35개에 $0.22였다.
- 동시 4로 벽시계 약 35–45분(설치 포함).
- 선택 사항: 오발화를 보려면 trivial 10개 × 4변형 × 1회 = 40세션(약 $5)을 더한다.

## 알려진 한계
- 다시 쓴 7개 중 5개(t203·t211·t224·t229·t253)는 1차와 2차에서 텍스트가 같다. 그런데도 oracle 재실행으로 관련 세트가 달라졌다: t224 0 → 2, t203 1 → 2, t211 3 → 3(1개 교체), t253 4 → 4(1개 교체), t229 2 → 2(같음). 같은 텍스트의 라벨 재현성 한계다. 2차 라벨을 쓴다(1차는 `prep/oracle-rfix-pass1.jsonl`).
- 실행 순서: 머지 → `14d2020` 기입 → `s5` 브랜치 → V0·V3 각 1세션 격리·설치 확인(4단계 P0 기준 4가지 + 로드된 SKILL.md가 R-c인지) → 228세션.
- V1·V2·V3는 각각 하나만 바꾼다. 조합 효과는 보지 않는다.
- 같은 모델, n=3 반복.
