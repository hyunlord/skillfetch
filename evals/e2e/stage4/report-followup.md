# 4단계 후속 분석 1·2 (기존 데이터·오프라인, 세션 실행 없음)

## 1. 발화 패턴 — 사소하지 않은 태스크 19개, 발화 수 / 6 (E1 3 + E2 3)

| 태스크 | 발화/6 | E1/3 | E2/3 | 작업종류 | 표현 | 레포 | 단어 수 | 오프라인 분류 | '코드 없음' 응답/6 |
|---|---|---|---|---|---|---|---|---|---|
| s4-t177 | 5 | 3 | 2 | data | spec | fastapi | 128 | search_fail | 4 |
| s4-t027 | 4 | 3 | 1 | bugfix | spec | fastapi | 113 | select_fail | 6 |
| s4-t182 | 4 | 2 | 2 | data | korean | fastapi | 35 | select_fail | 1 |
| s4-t055 | 4 | 2 | 2 | refactor | terminal | fastapi | 9 | restate_fail | 0 |
| s4-t224 | 4 | 3 | 1 | ml | korean | nextjs | 21 | search_fail | 6 |
| s4-t176 | 3 | 2 | 1 | data | normal | fastapi | 70 | select_fail | 1 |
| s4-t153 | 3 | 1 | 2 | deploy | korean | fastapi | 29 | select_fail | 3 |
| s4-t130 | 3 | 3 | 0 | ci_infra | terminal | nextjs | 18 | search_fail | 1 |
| s4-t354 | 3 | 1 | 2 | deploy | directive | fastapi | 48 | over_load | 4 |
| s4-t342 | 3 | 2 | 1 | feature | directive | fastapi | 70 | over_load | 0 |
| s4-t211 | 2 | 0 | 2 | ml | korean | fastapi | 31 | search_fail | 6 |
| s4-t101 | 2 | 1 | 1 | docs | normal | fastapi | 43 | over_load | 0 |
| s4-t280 | 2 | 0 | 2 | ui_design | terminal | fastapi | 16 | over_load | 0 |
| s4-t001 | 2 | 0 | 2 | feature | terminal | fastapi | 13 | over_load | 1 |
| s4-t253 | 1 | 0 | 1 | performance | korean | fastapi | 33 | select_fail | 6 |
| s4-t203 | 0 | 0 | 0 | ml | korean | fastapi | 27 | restate_fail | 6 |
| s4-t033 | 0 | 0 | 0 | bugfix | directive | fastapi | 57 | search_fail | 6 |
| s4-t229 | 0 | 0 | 0 | security_review | directive | fastapi | 67 | search_fail | 6 |
| s4-t026 | 0 | 0 | 0 | bugfix | normal | fastapi | 49 | search_fail | 1 |

- 분포(발화/6 → 태스크 수): 0→4, 1→1, 2→4, 3→5, 4→4, 5→1, 6→0. 전체 발화율 p=0.395로 같은 확률의 이항이라면 기대값은 0→0.9, 1→3.7, 2→6.0, 3→5.2, 4→2.5, 5→0.7, 6→0.1.
- 태스크별 발화 수의 분산은 2.47이고 이항 분산은 1.43이다(1.72배). 과분산 χ² = 31.0, 18 df, p≈0.03. 태스크가 일부를 결정하지만, 6/6 태스크는 없고 1–5에 15개가 퍼져 있다.
- E1·E2 둘 다 발화한 태스크 10, E1만 1, E2만 4, 둘 다 0인 태스크 4.
- 작업종류별 발화율: data 0.67(3태스크), refactor 0.67(1), ci_infra·deploy 0.50, feature 0.42, ml·docs·ui 0.33, bugfix 0.22(3), performance 0.17(1), security_review 0(1). 표현별: spec 0.75(2), terminal 0.46(4), korean 0.39(6), normal 0.28(3), directive 0.25(4). 레포별: fastapi 0.37(17), nextjs 0.58(2).
- 길이: Spearman(단어 수, 발화 수) = 0.07. 30단어 미만 0.43, 30–60단어 0.29, 60단어 이상 0.50.
- 오프라인 분류별 발화율: select_fail 0.50, over_load 0.40, restate_fail 0.33, search_fail 0.33.
- '코드 없음' 응답(최종 응답 첫 600자의 '없다/doesn't exist/couldn't find' 류 키워드, 근사): 114세션 중 58. 그 세션들의 발화 20/58, 나머지 25/56. 한 번도 발화하지 않은 태스크 4개 중 3개(t033·t203·t229)는 6/6 모두 '코드 없음'이었다. 4단계 태스크 고쳐 쓰기가 레포에 없는 코드를 가리키는 문제다.

### 발화하지 않은 세션 10개의 첫 assistant 메시지 (seed `nonfire-10`, 태스크당 1개, 환경당 5개)

10개 모두 첫 메시지는 텍스트 없는 도구 호출이다. thinking 블록은 있으나 스트림에는 서명만 있고 내용은 비어 있다(redacted). 그래서 '고려 후 건너뜀'은 transcript로 판정할 수 없다. 보이는 텍스트(모든 assistant 텍스트와 최종 응답)에서 skillfetch·router·skill을 언급한 세션은 0/10이다. → 보이는 범위에서는 10개 모두 '고려 흔적 없음'. 예외로 E1 s4-t153 r2는 첫 Bash에서 `cat .mcp.json`을 실행했다(설정은 읽었으나 호출하지 않음).

| 환경 | 태스크 | 반복 | 첫 도구 분류 | 첫 assistant 메시지 (도구 호출 원문) | 보이는 언급 |
|---|---|---|---|---|---|
| E1 | s4-t176 | r1 | explore | `Glob {"pattern": "backend/app/**/*.py"}` | 0 |
| E1 | s4-t001 | r2 | explore | `Read {"file_path": "<worktrees>/s4/s4-E1-s4-t001-r2/backend/app/initial_data.py"}` | 0 |
| E2 | s4-t342 | r3 | explore | `Read {"file_path": "<worktrees>/s4/s4-E2-s4-t342-r3/backend/app/initial_data.py"}` | 0 |
| E2 | s4-t253 | r1 | explore | `Read {"file_path": "<worktrees>/s4/s4-E2-s4-t253-r1/backend/app/api/routes/users.py"}` | 0 |
| E2 | s4-t101 | r2 | explore | `Read {"file_path": "<worktrees>/s4/s4-E2-s4-t101-r2/backend/app/utils.py"}` | 0 |
| E2 | s4-t033 | r1 | explore | `Grep {"pattern": "sanitiz/allow/google/href/url", "path": "frontend/src/utils.ts", "output_mode": "content", "-i": true}` | 0 |
| E1 | s4-t203 | r1 | explore | `Bash {"command": "ls backend/app/ml 2>&1; ls backend/app 2>&1 / head; git ls-files / grep -iE 'ml/classif/train' / head -30", "description": "Check whether the class` | 0 |
| E2 | s4-t354 | r3 | rules_git | `Bash {"command": "cd <worktrees>/s4/s4-E2-s4-t354-r3/backend && cat app/core/db.py app/initial_data.py scripts/prestart.sh && ls app/alembic/versi` | 0 |
| E1 | s4-t153 | r2 | explore | `Bash {"command": "ls -la; git ls-files / grep -iE 'compose/\\.env/docker' ; cat .mcp.json 2>/dev/null", "description": "List repo files and deploy configs"}` | 0 |
| E1 | s4-t182 | r3 | explore | `Bash {"command": "cat backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py; cat backend/app/models.py / head -120; ls backend/app/scripts 2>/` | 0 |

## 2. 원문 쿼리 추가 (오프라인, skillfetch a1cbcd5 `search_skills(queries=…)`, 3단계 oracle v2)

| 쿼리 | (i) @10 | (i) @50 | (ii) 2a @10 | (ii) 2a @50 | 프로세스 @10 | 프로세스 @50 |
|---|---|---|---|---|---|---|
| A: 3단계 Q3 (도메인/작업방식/스택 3문장) | 0.535 | 0.835 | 0.474 | 0.764 | 0.425 | 0.783 |
| A + 원문 (4쿼리) | 0.487 | 0.841 | 0.49 | 0.752 | 0.372 | 0.805 |
| B: 머지된 라우터 규칙 Q3 (최대 3문장, (b)는 사용자가 말했을 때만) | 0.398 | 0.729 | 0.41 | 0.699 | 0.266 | 0.636 |
| B + 원문 | 0.418 | 0.768 | 0.435 | 0.702 | 0.296 | 0.724 |

n: (i) 278, (ii) 209, 프로세스 207태스크. 비교: 3단계 Q2 단일 BM25 (i)@50 0.775, 프로세스@50 0.727.

### 재진술 분산 (50태스크 층화, B 규칙으로 격리 claude -p 3회 생성)

| | 반복 간 top-50 Jaccard 평균 (중앙) | (i) @10 | (i) @50 | (ii) @50 | 프로세스 @50 |
|---|---|---|---|---|---|
| 원문 미포함 | 0.608 (0.625) | 0.449 | 0.778 | 0.729 | 0.588 |
| 원문 포함 | 0.732 (0.752) | 0.426 | 0.812 | 0.721 | 0.673 |

생성 3회의 쿼리 목록이 똑같았던 태스크: r1–r2 2, r1–r3 0, r2–r3 2 (/50).

- 판정(기준: 원문을 넣으면 Jaccard가 오르고 recall이 떨어지지 않음):
  - 현재 라우터 규칙 B에서 Jaccard는 0.608 → 0.732로 오른다.
  - 380태스크 recall은 모든 칸에서 같거나 오른다((i)@50 +0.039, 프로세스@50 +0.088, (ii)@50 +0.003).
  - 분산 표본 50개에서는 @10이 0.449 → 0.426(−0.023), (ii)@50 0.729 → 0.721(−0.008)로 조금 내려간다.
  - → **라우터 변경 후보**로 둔다(단서: 위 소폭 하락; oracle 풀에 원문 top-10이 들어 있어 원문 쪽에 유리한 편향이 있다. 편향 없는 (ii)는 380에서 0.699 → 0.702).
- **더 큰 발견**: 머지된 라우터 규칙 B의 recall이 3단계에서 평가한 Q3(A)보다 낮다. (i)@50 0.729 vs 0.835, 프로세스@50 0.636 vs 0.783이다. 단일 Q2(0.775)보다도 낮다. B는 '작업 방식' 문장을 사용자가 말했을 때만 넣으므로 프로세스성 스킬이 특히 빠진다.

데이터: `stage3/followup/` (q3r-380.jsonl, variance-tasks.json, q3r-var-r{1,2,3}.jsonl, orig-query.json), 스크립트 `stage3/scripts/gen_q3r.py`, `eval_orig_query.py`.
