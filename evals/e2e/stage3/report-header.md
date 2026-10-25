태스크 380개, oracle 라벨, 검색(오프라인 Python), 선택(배치 프롬프트), e2e 40세션(실행 2회). 생성물은 모두 jsonl로 동결했고 해시는 `FROZEN.sha256`에 있다. 이후 단계는 동결본만 읽었다. 스크립트는 `scripts/`.

## 0. 설정

| 항목 | 값 |
|---|---|
| index | index-2026-10-22 (`built_at` 2026-10-22T06:15:43Z). 평가 대상은 search_skills가 돌려줄 수 있는 canonical tier A/B 1,489개 |
| skillfetch | 검색 `main@64f4bd8`(최신). 2b 풀은 `a671e6a`로 만들었는데, 원문 쿼리 top-50이 380/380 동일함을 확인했다(`index/search.py`·`bm25.py` 변경 없음) |
| 배치 프롬프트 | 격리한 `claude -p`(Opus 5.5): 도구 없음, MCP 없음, `--setting-sources project`(사용자 훅·플러그인·CLAUDE.md 미적용), 고정 부분은 system prompt(1h 캐시). 태스크 생성 14회, 제목 누출 재작성 1회, 2a 38회, 2b 380회, 2c 40회, 3-0 380회, Q2 19회, Q3 19회, 선택 19회 + 단독 재실행 31회 |
| 태스크 | `tasks.jsonl` 380개 = 층화 300(12×6×5 셀 중 300, 셀당 1; 작업종류당 25 · 스택당 50 · 표현당 60) + expect_none 40 + 방향 쌍 20쌍(40). 생성 후 1,707개 제목과 토큰을 대조해 20개를 재작성했다(이어 붙인 식별자의 부분까지 대조) |
| oracle | 2a 카탈로그(id · title · 10단어 요약; 요약 앞 상투구 제거 후 10단어 절단, 약 83k 토큰) 10태스크씩 → 2b 풀(2a ∪ BM25 원문 top-10 ∪ 무작위 2) 0–3점 + 프로세스 표시 → **3-0 보정**: Q2·Q3·MiniLM·RRF 각 top-10을 풀에 추가하고 새 후보만 같은 프롬프트로 채점(v1 라벨 불변). 관련 = 등급 ≥2 |
| 쿼리 | Q1 원문 · Q2 라우터 1단계 규칙 그대로의 1문장 재진술 · Q3 Q2를 도메인/작업방식/스택 3문장으로 나눠 각각 검색 후 RRF(k=60). 프로필 없음(오프라인) |
| MiniLM | all-MiniLM-L6-v2, sentence-transformers, CPU. 필드 title+description+summary+keywords+synthetic_queries. RRF는 BM25 전체 순위 + 임베딩 전체 순위 |
| 선택 | 라우터 SKILL.md(main 64f4bd8)의 'When' 절 + 4단계 원문 + "1–3개 또는 none", 입력은 Q2의 실제 search_skills 출력(compact 50개), 20태스크씩 |
| e2e | 실패 분류별 층화 40개(over_load 10, select_fail 10, restate_fail 10, search_fail 7, ok 3 — search_fail은 7개뿐). 1–2단계와 같은 하네스(`claude -p` stream-json, 같은 허용 도구, 사용자 전역 `~/.claude` 상속), `--max-turns 12`, 라우터와 `.mcp.json`은 skillfetch `64f4bd8` |

### 기록 사항

- **oracle을 만든 모델이 라우터와 같다(Opus 5.5).** 2c 일치율(±1 100%, kappa 0.873)은 같은 모델 안의 일관성이고, 정답성 검증은 아니다.
- **풀링 편향**: 원래 풀이 BM25 원문 쪽으로 치우쳐 있었다(3-0에서 관련 스킬 +354개, 63% 증가). 그래도 풀 밖의 스킬은 관련이 될 수 없으므로, 남은 편향은 Q1·Q2·Q3·MiniLM·RRF가 모두 놓친 스킬 쪽이다.
- **배치 선택의 교차 오염**: 20태스크를 한 번에 주니 모델이 다른 태스크의 목록에 있던 id를 고른 경우가 31건 나왔다. 그 31개 태스크는 한 태스크씩 다시 돌려 그 결과를 썼다(`redone_alone`).
- **e2e run 1(빈 레포)은 목적을 달성하지 못했다.** 40개 중 라우터 발화 7, search 5. 세션은 사용자 전역 RULES.md의 "git status 먼저" 규칙대로 레포를 먼저 보고, 코드가 없으니 멈췄다. 그래서 run 2를 했다. 태스크가 이름을 댄 파일·디렉터리와 스택별 소스 파일 1개를 빈 스텁으로 넣고, manifest·lockfile은 넣지 않았다(profile이 비게 두어 오프라인과 같은 조건). 두 run 모두 표 4에 있다.
- **방향 지시 표현의 편중**: 생성기가 "Plan before coding"을 많이 썼다(표현 샘플 40개 중 directive 8개 가운데 4개).
