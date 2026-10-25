# 라우터 1단계 규칙 비교 — 승자 R-c

**`assets/router-skill/SKILL.md`를 아래 전문으로 바꾼다.** 오프라인 측정이다(세션 없음). 각 후보 SKILL.md의 1단계 문구를 잘라 격리 `claude -p`(도구·MCP·사용자 설정 없음) 프롬프트에 그대로 넣고, 380태스크의 `queries`를 생성했다. 검색은 skillfetch `a1cbcd5`의 `search_skills(queries=…)`(서버 RRF k=60, compact k=50, profile 없음)다. main `f9d2546`까지 `index/`·`mcp/`·`assets/router-skill`의 변경은 없다.

## 후보

- **R-a**: 머지된 규칙(`a1cbcd5`). (b) 작업 방식은 사용자가 말했을 때만 쓴다.
- **R-b**: 항상 세 문장. (b)는 사용자가 말한 방식, 말하지 않았으면 태스크에 가장 맞는 방식을 쓴다(3단계 Q3와 같은 조건).
- **R-c**: R-b에 (d) 사용자 요청 원문을 그대로 4번째 쿼리로 추가한다. 4단계 문구를 `(a)–(d)`로 바꾸고, 원문 검색을 금하던 Rules 한 줄("Search with the task, not with the user's literal wording or a list of keywords.")을 지웠다.
- 줄 수: R-a 59, R-b 60, R-c 60.

## 수치

### 380태스크 recall — oracle v3

v3 = 3단계 v2 + 세 후보의 top-10 중 풀 밖이던 2143개를 같은 2b 프롬프트로 채점한 것이다. 새로 관련이 된 것은 100개로, 관련 쌍은 915개에서 1015개가 됐다($7.06). n은 전체 284, 2a 209, 프로세스 213.

| 규칙 | 전체 @10 | 전체 @50 | 2a @10 | 2a @50 | 프로세스 @50 |
|---|---|---|---|---|---|
| R-a | 0.409 | 0.737 | 0.42 | 0.696 | 0.656 |
| R-b | 0.464 | 0.807 | 0.449 | 0.773 | 0.774 |
| R-c | 0.457 | 0.808 | 0.467 | 0.746 | 0.77 |
| (참고) 3단계 Q3 | 0.49 | 0.822 | 0.474 | 0.764 | 0.761 |

### 380태스크 recall — oracle v2(3단계 동결본; 풀 보정 전)

| 규칙 | 전체 @10 | 전체 @50 | 2a @10 | 2a @50 | 프로세스 @50 |
|---|---|---|---|---|---|
| R-a | 0.403 | 0.732 | 0.42 | 0.696 | 0.647 |
| R-b | 0.461 | 0.802 | 0.449 | 0.773 | 0.766 |
| R-c | 0.454 | 0.799 | 0.467 | 0.746 | 0.76 |
| (참고) 3단계 Q3 | 0.535 | 0.835 | 0.474 | 0.764 | 0.783 |

### 짝지은 차이(v3, 태스크별 recall 차의 평균, 부트스트랩 95% 구간 4,000회, 나음/못함 태스크 수)

| 지표 | R-b − R-a | R-c − R-a | R-c − R-b |
|---|---|---|---|
| 전체 @10 | +0.055 [+0.014, +0.095] 90/56 | +0.048 [+0.005, +0.088] 88/59 | -0.007 [-0.044, +0.029] 58/68 |
| 전체 @50 | +0.069 [+0.035, +0.105] 68/30 | +0.071 [+0.035, +0.108] 79/38 | +0.001 [-0.028, +0.032] 45/45 |
| 2a @10 | +0.029 [-0.014, +0.074] 28/22 | +0.046 [-0.003, +0.097] 35/20 | +0.018 [-0.025, +0.057] 22/17 |
| 2a @50 | +0.077 [+0.033, +0.122] 32/11 | +0.050 [+0.005, +0.096] 32/18 | -0.026 [-0.072, +0.020] 19/26 |
| 프로세스 @50 | +0.118 [+0.062, +0.176] 51/22 | +0.114 [+0.059, +0.173] 57/27 | -0.004 [-0.046, +0.040] 29/30 |

### 반복 3회 — 50태스크(표현 5종 × 10), 같은 10태스크 묶음을 독립 생성

| 규칙 | top-50 쌍별 Jaccard 평균 | 중앙 | 최소 | 쿼리 목록이 완전히 같은 쌍 | 전체 @10 (v3) | 전체 @50 (v3) | 2a @50 | 프로세스 @50 (v3) |
|---|---|---|---|---|---|---|---|---|
| R-a | 0.569 | 0.585 | 0.279 | 0/150 | 0.444 | 0.769 | 0.743 | 0.59 |
| R-b | 0.554 | 0.549 | 0.268 | 0/150 | 0.517 | 0.858 | 0.814 | 0.727 |
| R-c | 0.706 | 0.705 | 0.458 | 0/150 | 0.476 | 0.865 | 0.81 | 0.771 |

### 교차 라벨 120태스크(Opus·GPT 둘 다 등급≥2인 교집합 라벨, v2 풀)

| 규칙 | 전체 @10 | 전체 @50 | 2a @50 | 프로세스 @50 |
|---|---|---|---|---|
| R-a | 0.413 | 0.745 | 0.657 | 0.682 |
| R-b | 0.496 | 0.827 | 0.754 | 0.812 |
| R-c | 0.511 | 0.845 | 0.759 | 0.816 |
| (참고) 3단계 Q3 | 0.584 | 0.846 | 0.736 | 0.783 |

### 기타

- 쿼리 수(380): R-a 1개 1 · 2개 198 · 3개 181; R-b 3개 380; R-c 4개 380.
- R-c (d)가 요청 원문과 글자 그대로 같은 경우: 529/530(380 + 반복 150). 다른 1건은 한국어 요청의 한 어미가 바뀐 것이다.
- 생성 비용: 102회 호출, $7.35. 풀 보정: 373회, $7.06.

## 판정 규칙과 결과

규칙은 이렇다. R-a보다 recall이 오르는 후보 가운데, recall이 떨어지지 않으면서(짝지은 95% 구간이 0을 포함하거나 양수) 반복 간 Jaccard가 가장 높은 것을 고른다.
- R-b와 R-c는 R-a보다 전체 @50, 2a @50, 프로세스 @50에서 높고, 구간이 모두 0보다 위다.
- R-c − R-b의 다섯 지표 구간은 모두 0을 포함한다.
- Jaccard는 R-b 0.554, R-c 0.706이다.
- 그래서 **R-c**다.

**단서:**
- R-c의 (d)는 원문 쿼리다. 원문 BM25 top-10은 처음부터 oracle 풀에 들어 있어서 "전체" 지표에서 R-c에 유리하다.
- 검색과 독립인 2a 기준으로는 R-c − R-b가 @10 +0.018, @50 −0.026이고, 두 구간 모두 0을 포함한다.
- oracle과 생성 모델이 같다(Opus 5.5).
- 생성은 배치(20태스크/호출)여서 실제 세션의 1단계와 같은 조건이 아니다.

## 레포에 반영할 것

1. `assets/router-skill/SKILL.md` ← 아래 전문(60줄).
2. `CLAUDE.md` "Router skill" 절:
   - "Short (< 60 lines)"는 이 파일이 정확히 60줄이므로 "≤ 60 lines"로 고친다.
   - 1번 항목의 "how the user asked to work (…; omitted when they did not say)"는 새 규칙과 어긋난다. 새 규칙은 "말하지 않았으면 가장 맞는 방식", 그리고 "(d) 요청 원문"이다.
3. `src/skillfetch/mcp/server.py`의 `INSTRUCTIONS`는 아직 "restate the task in one sentence"이다. 이번 측정 대상이 아니라서 바꾸지 않아도 된다(5단계 V3이 이 문구를 다룬다).

## SKILL.md 전문 (R-c)

````markdown
---
name: skillfetch-router
description: Use at the start of any coding task that adds or changes code, tests, docs or config (more than a one-line edit in one file), fixes a bug, or starts a feature — before reading the codebase. Skip only a one-line edit in a single file, a rename, or answering a question.
---

# skillfetch router

Use the skillfetch MCP tools to pick skills for this task. Nothing gets installed.

## When

Run the steps first, before you grep, glob or read the codebase, for:

- a feature, even one that fits in a single file
- a bug fix, even when you expect the fix to be one line
- a refactor: splitting, moving or extracting code
- tests: adding, extending or repairing them
- documentation: README sections, guides, docstrings, comments across a file
- configuration: build, lint, CI, dependency or framework config
- a review, a migration, a new document

"It looks small" is not a reason to skip. Neither is a project skill that seems to fit
(for example one in `.claude/skills/`): run the steps and pin it (step 5).

Skip only: a one-line edit in a single file (a typo, a constant, an import), a rename
with no other change, or answering a question without editing files.

## Steps

1. **Restate the task in English**, whatever language the user wrote in, as three short
   sentences: (a) what it builds or fixes, in domain nouns ("Conditional GET with ETags
   for the product catalog API"); (b) the kind of work and how to do it: the approach the
   user asked for ("Test-driven: write failing tests first", "Minimal diff", "Security
   first"), or, if they did not say, the one that fits this task best ("Bug fix: find the
   root cause first"); (c) the stack and target files ("Go net/http, `internal/catalog/`").
   Add (d), the user's request copied word for word, as a fourth query. Do not explore
   the code first; the search needs the task, not the code.
2. If no `mcp__skillfetch__*` tool is listed yet, the server is starting: load them with
   ToolSearch (query `+skillfetch`), and search again if it says it is connecting.
3. Call `profile_repo` with the repository root once per session (it reads manifest files
   only) and pass the result as `profile` to `search_skills`.
4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line
   summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is
   often not near the top. Each result has a `token_estimate`: when two fit equally, take
   the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default).
5. If the user named a skill ("use the pdf skill"), call `search_skills` with that name,
   take the id of the result whose title matches, and put it in `pinned_ids`. A local
   skill folder (one the user named, or a project skill that fits) is pinned as
   `path:/absolute/path`. If nothing matches, say so.
6. Call `resolve_set` with your picks as `auto_ids` (in order of preference) and the
   pinned skills as `pinned_ids`. Respect `excluded`; read every warning's two quoted
   lines and decide whether they matter for this task.
7. Call `load_skills` with the `set_id` and follow the returned instructions.
8. Do the work. If `load_skills` lists a skill in `errors` (hash mismatch, fetch error,
   dropped for the token budget), continue without it and say so.

## Rules

- Never load a skill that `resolve_set` excluded.
- Do not search again mid-task unless the task changes.
````

## a1cbcd5 대비 diff

```diff
@@ -27,17 +27,19 @@
 
 ## Steps
 
-1. **Restate the task in English**, whatever language the user wrote in, as up to three
-   short sentences: (a) what it builds or fixes, in domain nouns ("Conditional GET with
-   ETags for the product catalog API"); (b) how the user asked you to work, if they did
-   ("Test-driven: write failing tests first", "Minimal diff", "Security first"), else
-   leave it out; (c) the stack and target files ("Go net/http, `internal/catalog/`").
-   Do not explore the code first; the search needs the task, not the code.
+1. **Restate the task in English**, whatever language the user wrote in, as three short
+   sentences: (a) what it builds or fixes, in domain nouns ("Conditional GET with ETags
+   for the product catalog API"); (b) the kind of work and how to do it: the approach the
+   user asked for ("Test-driven: write failing tests first", "Minimal diff", "Security
+   first"), or, if they did not say, the one that fits this task best ("Bug fix: find the
+   root cause first"); (c) the stack and target files ("Go net/http, `internal/catalog/`").
+   Add (d), the user's request copied word for word, as a fourth query. Do not explore
+   the code first; the search needs the task, not the code.
 2. If no `mcp__skillfetch__*` tool is listed yet, the server is starting: load them with
    ToolSearch (query `+skillfetch`), and search again if it says it is connecting.
 3. Call `profile_repo` with the repository root once per session (it reads manifest files
    only) and pass the result as `profile` to `search_skills`.
-4. Call `search_skills` with those sentences as `queries`. It returns 50 one-line
+4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line
    summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is
    often not near the top. Each result has a `token_estimate`: when two fit equally, take
    the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default).
@@ -54,6 +56,5 @@
 
 ## Rules
 
-- Search with the task, not with the user's literal wording or a list of keywords.
 - Never load a skill that `resolve_set` excluded.
 - Do not search again mid-task unless the task changes.
```

## 재현

e2e 작업 공간 `stage3/` 기준:
- 후보: `router-cands/R-{a,b,c}/SKILL.md`. 프롬프트: `gen/sys-rc-R-*.txt`.
- 생성: `scripts/gen_router_cands.py`.
- 검색: `uvx --from git+https://github.com/hyunlord/skillfetch@a1cbcd5 python scripts/rank_router_cands.py`.
- 풀 보정: `scripts/expand_pools_rc.py`. 결과: `followup/oracle-v3.jsonl`.
- 지표: `scripts/eval_router_cands.py`. 결과: `followup/router-cands.json`, `followup/router-cands-paired.json`.
