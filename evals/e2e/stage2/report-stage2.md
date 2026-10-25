# skillfetch 2단계 — 도메인 일반화 (report)

60세션 (4도메인 × A/B/C2 × 5회), 고정 시드 큐 `runs/_queue.txt`, 동시 4. 숫자는 `scripts/extract_s2.py` → `scripts/report_s2.py`, 채점 `judge-p1.md`·`judge-p2.md` → `scripts/unblind_s2.py`.

## 0. 설정

| 항목 | 값 |
|---|---|
| 하네스 | 1b/C2와 같음: `stage1/scripts/run_stage1.py`의 `run_session`/`collect_diff`/`strip_env_noise` 재사용, `claude -p <prompt> --output-format stream-json --verbose --max-turns 40 --allowedTools "Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*"`, 같은 env 정리, 사용자 전역 `~/.claude` 상속. 러너 `scripts/run_s2.py` |
| A | 레포 `s2-a` 브랜치 그대로 |
| B | A + 전문가 스킬 1개의 `load_skills` 출력(`expert-content/<task>.md`)을 `--append-system-prompt-file` — 1b의 B와 같은 방식. 선정 기록 `b-skills.md` |
| C2 | 레포 `s2-c2` = `s2-a` + `.claude/skills/skillfetch-router/SKILL.md` + `.mcp.json`. skillfetch `e2a1b65`에 고정(라우터 파일 = 1b `s1b-c2`와 동일, search k=50 압축) |
| 인덱스 | `~/.skillfetch/index` built_at 2026-10-22T06:15:43Z (index-2026-10-22) |
| 레포 | `repos/s2-tests` (`recur` 패키지, `src/recur/rules.py` 280줄 + `__init__` 24줄, 테스트 0개), `repos/s2-api` (빈 FastAPI 프로젝트), `repos/s2-docs` (1단계 nextjs `s1-a`에서 README.md 삭제), `repos/s2-data` (시드 생성 `data/orders.csv` 375행, 심은 문제 10종 — `rubrics.md`, `reference/orders-truth.json`) |
| 프롬프트 | `tasks-stage2.yaml`, 조건 간 동일(글자 하나 안 바뀜) |
| 체크 | `checks/check_s2.py`(+ `api_contract.py` 27호출). 실행 전 동결(`checks/FROZEN.sha256`: 루브릭·태스크·B 선정·B 내용·체크·러너). 수정 없는 레포에서 4개 모두 실패, 참조 구현에서 4개 모두 통과(`checks/VALIDATION.md`) |
| 채점 | 도메인별 블라인드 세트(15개씩, 조건 숨김, `blind-p<N>/`, 키 `blind-key-p<N>.jsonl`), 정답·조건 비공개 하위 에이전트가 `rubrics.md`로 채점. 2회(p1, p2): 코드 새로 뽑고 판정자 새로 |

### 기록 사항

- **B 적용 방식**: 지시문의 "~/.claude/skills에 설치"와 "1b의 B 설치 방식 그대로"가 다르다. 1b의 B는 `~/.claude/skills`가 아니라 `--append-system-prompt-file`이었다. 전역 설치는 동시에 도는 A·C2 세션에도 보이므로(조건 오염) 1b 방식을 따랐다.
- **C2 버전 고정**: 실행 시점 skillfetch main은 `a671e6a`(PR #27: `load_skills`가 precedence header를 더 이상 붙이지 않음, 라우터 7단계 문구 변경). "≥ e2a1b65"를 만족하면서 1b/C2와 조건을 같게 하려고 `e2a1b65`에 고정(`.mcp.json`의 `git+…@e2a1b65`). B 내용도 `e2a1b65`의 `load_skills` 출력(precedence header 포함, 1b와 같음).
- **B 선정 쿼리**: B는 `tasks-stage2.yaml`의 `search_sentence`(이 세션이 쓴 영어 재서술)로 뽑은 top-50에서 골랐다. C2 세션은 자기 쿼리로 검색하므로 B의 순위가 달라질 수 있다.
- **태스크 크기**: "한 세션 15턴 이상" 목표로 만들었지만 일부 세션은 15턴 미만으로 끝났다(세션별 표).
- **판정자**: 하위 에이전트(같은 모델). 이 세션은 판정에 관여하지 않았고, 실행 중 일부 C2 세션의 skillfetch 호출 목록을 확인했다.
- **API 체크 수정 후 재체크**: 동결한 `api_contract.py`가 `TestClient`를 열지 않아 FastAPI lifespan(시작 시 테이블 생성)이 돌지 않았다. 그 결과 B s2-api r3이 계약 5/27(자체 테스트 61개는 통과)로 나왔다. 실행 중(01:00경) `c.__enter__()` 한 줄을 고쳐 다시 검증했다(수정 없는 레포 0/27, 참조 구현 27/27). 큐가 끝난 뒤 s2-api 15세션 전부를 고친 스크립트로 재체크했고, 그 결과 B r3만 False→True(27/27)로 바뀌었다. 표의 체크 값은 재체크 결과다. 원 결과는 meta의 `check_original`, 기록은 `checks/VALIDATION.md`, `checks/FROZEN.after-fix.sha256`.
- **문서 세트 맥락 메모**: C2 레포에는 `.mcp.json`과 `.claude/`가 있다. C2 문서 2개가 이를 "Claude Code 설정, 앱 실행과 무관"이라고 적었다. 판정자에게 주는 공유 맥락(`s2-a` 소스)에는 이 파일들이 없어 '지어낸 내용'으로 판정될 수 있다. 그래서 두 채점 모두 문서 세트의 `_context/NOTE.txt`에 "일부 사본에는 `.mcp.json`과 `.claude/`가 있었고, 언급해도 안 해도 정확하다"는 중립 문장을 넣었다(조건 언급 없음). 그 두 문서의 "MCP 서버(skillfetch)"는 `[redacted]` 처리했다(전체 redaction 각 채점 1회).
- **이 세션이 본 매핑**: 위 누출 여부를 확인하다가 블라인드 코드와 조건 매핑 일부가 이 세션의 출력에 찍혔다. 판정은 하위 에이전트가 했으므로 블라인드에는 영향이 없다.
- **천장 효과**: 테스트 도메인 15세션 모두 branch 커버리지 100%이고, API 15세션 모두 계약 27/27, 체크는 60세션 전부 통과했다. 객관 지표로는 조건 간 차이가 없다.
- **랜딩 행**: 1b 재판정 결과를 그대로 옮겼다. 채점 1회(p2 없음)이고, 루브릭이 다르다((b) 쓸만함 1-5).

## 표 1. 도메인 × 조건

점수 = 총점 1-5, 두 채점(p1·p2) 평균의 조건 평균 (괄호: p1 / p2). 랜딩 행 = 1b 재판정(1회, 루브릭 (b) 쓸만함 1-5, n=4: nx 2 + fa 2), 턴·토큰·비용은 같은 1b 세션. 턴·입력 토큰·비용은 중앙값. C2≥B / C2≥A = 두 채점 평균 기준; 괄호 안은 p1·p2 각각에서도 성립하는지.

| 도메인 | 조건 | n | 점수 (p1 / p2) | 객관 지표 | 중앙 턴 | 중앙 입력 토큰 | 중앙 비용 $ | C2≥B | C2≥A |
|---|---|---|---|---|---|---|---|---|---|
| 랜딩 페이지 (1b) | A | 4 | 3.50 | 체크 통과 4/4 | 21.5 | 1,695,734.5 | 1.25 | | |
| 랜딩 페이지 (1b) | B | 4 | 4.75 | 체크 통과 4/4 | 27 | 2,137,064.5 | 1.44 | | |
| 랜딩 페이지 (1b) | C2 | 4 | 4.75 | 체크 통과 3/4 | 28 | 2,295,534 | 1.50 | Y | Y |
| 테스트 작성 (s2-tests) | A | 5 | 4.90 (5.00 / 4.80) | 테스트 통과 중앙 166, 실패 합 0, 커버리지 line 100.0% / branch 100.0%, 모듈 수정 0 | 10 | 783,055 | 1.10 | | |
| 테스트 작성 (s2-tests) | B | 5 | 5.00 (5.00 / 5.00) | 테스트 통과 중앙 169, 실패 합 0, 커버리지 line 100.0% / branch 100.0%, 모듈 수정 0 | 9 | 833,147 | 1.19 | | |
| 테스트 작성 (s2-tests) | C2 | 5 | 5.00 (5.00 / 5.00) | 테스트 통과 중앙 762, 실패 합 0, 커버리지 line 100.0% / branch 100.0%, 모듈 수정 0 | 16 | 1,493,714 | 1.61 | Y (both) | Y (both) |
| 백엔드 API (s2-api) | A | 5 | 4.20 (4.20 / 4.20) | 계약 호출 평균 27.0/27 (전부 통과 5/5), 자체 테스트 통과 5/5 | 15 | 899,707 | 0.88 | | |
| 백엔드 API (s2-api) | B | 5 | 4.20 (4.40 / 4.00) | 계약 호출 평균 27.0/27 (전부 통과 5/5), 자체 테스트 통과 5/5 | 14 | 871,226 | 0.93 | | |
| 백엔드 API (s2-api) | C2 | 5 | 4.80 (4.80 / 4.80) | 계약 호출 평균 27.0/27 (전부 통과 5/5), 자체 테스트 통과 5/5 | 23 | 1,870,639 | 1.43 | Y (both) | Y (both) |
| 문서화 (s2-docs) | A | 5 | 4.10 (4.00 / 4.20) | README 중앙 372단어, 없는 npm 스크립트 언급 0/5, build 통과 5/5 | 10 | 687,962 | 0.65 | | |
| 문서화 (s2-docs) | B | 5 | 4.70 (4.80 / 4.60) | README 중앙 363단어, 없는 npm 스크립트 언급 0/5, build 통과 5/5 | 9 | 733,233 | 0.64 | | |
| 문서화 (s2-docs) | C2 | 5 | 4.40 (4.40 / 4.40) | README 중앙 332단어, 없는 npm 스크립트 언급 0/5, build 통과 5/5 | 17 | 1,332,644 | 0.90 | N (neither) | Y (both) |
| 데이터 스크립트 (s2-data) | A | 5 | 4.50 (4.60 / 4.40) | 스크립트 실행·출력 체크 통과 5/5 | 12 | 909,068 | 0.94 | | |
| 데이터 스크립트 (s2-data) | B | 5 | 4.50 (5.00 / 4.00) | 스크립트 실행·출력 체크 통과 5/5 | 12 | 854,603 | 0.99 | | |
| 데이터 스크립트 (s2-data) | C2 | 5 | 4.50 (4.60 / 4.40) | 스크립트 실행·출력 체크 통과 5/5 | 18 | 1,518,055 | 1.15 | Y (one) | Y (both) |

## 표 2. C2 검색 적중 (n=5 중; 랜딩은 n=4)

| 도메인 | B 스킬 | 라우터 발화 | search 호출 | B가 top-50에 | B 평균 순위 (들어간 run) | B를 고름 (resolve에 넣음) | resolve_set이 B 제외 | B 로드 |
|---|---|---|---|---|---|---|---|---|
| 랜딩 페이지 (1b) | `anthropics-skills/frontend-design` | 4/4 | 4/4 | 4/4 | 29.2 | 4/4 | 0/4 | 4/4 |
| 테스트 작성 (s2-tests) | `uasl/python-testing-patterns` | 5/5 | 5/5 | 5/5 | 1.0 | 5/5 | 0/5 | 5/5 |
| 백엔드 API (s2-api) | `uasl/fastapi-templates` | 5/5 | 5/5 | 5/5 | 2.0 | 4/5 | 0/5 | 4/5 |
| 문서화 (s2-docs) | `uasl/quill` | 5/5 | 5/5 | 5/5 | 1.8 | 5/5 | 0/5 | 5/5 |
| 데이터 스크립트 (s2-data) | `uasl/data-analyst-engine` | 5/5 | 5/5 | 5/5 | 2.0 | 5/5 | 0/5 | 5/5 |

## 표 3. C2가 B 스킬을 로드하지 않은 run: 대신 로드한 스킬과 점수

| 도메인 | run | 원인 | B 순위 | 로드한 스킬 | 점수 (p1 / p2) | 같은 도메인 B 평균 점수 |
|---|---|---|---|---|---|---|
| 백엔드 API | r1 | top-50 안, 모델이 안 고름 | 2 | `uasl/api-design`, `uasl/fastapi-endpoint` | 5.0 (5 / 5) | 4.20 |

## 채점 일관성 (p1 vs p2, 같은 루브릭, 새 코드·새 판정자)

| 도메인 | n | 총점 일치 | 평균 절대 차 | 최대 차 | C2≥B 판단 두 채점 같음 | C2≥A 판단 두 채점 같음 |
|---|---|---|---|---|---|---|
| 테스트 작성 | 15 | 14/15 | 0.07 | 1 | Y | Y |
| 백엔드 API | 15 | 13/15 | 0.13 | 1 | Y | Y |
| 문서화 | 15 | 11/15 | 0.27 | 1 | Y | Y |
| 데이터 스크립트 | 15 | 8/15 | 0.47 | 1 | N | Y |

## 결론 (숫자만)

C2가 B를 재현한 도메인(두 채점 평균 점수 C2 ≥ B) 3/4 (s2-tests, s2-api, s2-data); 랜딩 포함 4/5. C2가 B 스킬을 로드한 run: s2-tests 5/5, s2-api 4/5, s2-docs 5/5, s2-data 5/5 (랜딩 4/4). B를 로드하지 않은 run의 원인: s2-api: top-50 안, 모델이 안 고름 1. 재현 못 한 도메인 s2-docs: C2 4.40 < B 4.70, C2가 B를 로드한 run 5/5, 원인 분류(top-50 밖 / 안 고름 / 제외) 해당 run 0. 

## 세션별

| 도메인 | 조건 | run | subtype | 턴 | 입력 토큰 | 출력 토큰 | 비용 $ | 체크 | 점수 p1 / p2 | C2: 쿼리 | C2: 로드 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s2-tests | A | r1 | success | 10 | 891,729 | 26,954 | 1.17 | True | 5 / 5 |  |  |
| s2-tests | A | r2 | success | 13 | 847,570 | 21,556 | 1.01 | True | 5 / 4 |  |  |
| s2-tests | A | r3 | success | 10 | 783,055 | 24,372 | 1.07 | True | 5 / 5 |  |  |
| s2-tests | A | r4 | success | 7 | 653,545 | 23,569 | 1.31 | True | 5 / 5 |  |  |
| s2-tests | A | r5 | success | 8 | 677,443 | 26,552 | 1.10 | True | 5 / 5 |  |  |
| s2-tests | B | r1 | success | 9 | 836,867 | 24,252 | 1.49 | True | 5 / 5 |  |  |
| s2-tests | B | r2 | success | 6 | 515,712 | 23,876 | 1.35 | True | 5 / 5 |  |  |
| s2-tests | B | r3 | success | 9 | 833,147 | 23,883 | 1.07 | True | 5 / 5 |  |  |
| s2-tests | B | r4 | success | 9 | 862,931 | 27,803 | 1.19 | True | 5 / 5 |  |  |
| s2-tests | B | r5 | success | 9 | 738,004 | 23,667 | 1.04 | True | 5 / 5 |  |  |
| s2-tests | C2 | r1 | success | 19 | 1,728,026 | 32,424 | 1.66 | True | 5 / 5 | Add a pytest test suite with edge cases and higher coverage for the Python recurrence rules module src/recur/rules.py | `uasl/python-testing-patterns`, `uasl/property-based-testing` |
| s2-tests | C2 | r2 | success | 15 | 1,203,924 | 20,179 | 1.19 | True | 5 / 5 | Add a pytest test suite with edge-case coverage for the Python recurrence rules module src/recur/rules.py | `uasl/python-testing-patterns`, `uasl/verification-loop` |
| s2-tests | C2 | r3 | success | 17 | 1,602,826 | 31,570 | 1.61 | True | 5 / 5 | Add a pytest test suite with edge cases and high coverage for the Python recurrence rules module src/recur/rules.py | `uasl/python-testing-patterns`, `uasl/property-based-testing` |
| s2-tests | C2 | r4 | success | 16 | 1,493,714 | 31,837 | 1.88 | True | 5 / 5 | Add a pytest test suite for the Python recurrence rules module src/recur/rules.py, covering edge cases and raising coverage | `uasl/python-testing-patterns`, `uasl/property-based-testing` |
| s2-tests | C2 | r5 | success | 16 | 1,206,343 | 22,272 | 1.61 | True | 5 / 5 | Add a pytest test suite for the Python recur package's recurrence-rule module src/recur/rules.py, covering edge cases and raising coverage | `uasl/python-testing-patterns`, `uasl/property-based-testing` |
| s2-api | A | r1 | success | 14 | 814,111 | 18,658 | 0.88 | True | 4 / 4 |  |  |
| s2-api | A | r2 | success | 16 | 899,707 | 17,373 | 0.87 | True | 4 / 4 |  |  |
| s2-api | A | r3 | success | 15 | 1,033,352 | 21,189 | 1.00 | True | 4 / 4 |  |  |
| s2-api | A | r4 | success | 12 | 616,597 | 18,451 | 0.83 | True | 4 / 4 |  |  |
| s2-api | A | r5 | success | 18 | 1,285,870 | 27,511 | 1.52 | True | 5 / 5 |  |  |
| s2-api | B | r1 | success | 15 | 1,216,629 | 17,155 | 0.93 | True | 4 / 4 |  |  |
| s2-api | B | r2 | success | 14 | 953,548 | 17,211 | 1.21 | True | 4 / 4 |  |  |
| s2-api | B | r3 | success | 15 | 871,226 | 18,993 | 0.91 | True | 5 / 4 |  |  |
| s2-api | B | r4 | success | 14 | 870,756 | 20,035 | 0.94 | True | 5 / 4 |  |  |
| s2-api | B | r5 | success | 14 | 857,782 | 16,523 | 0.85 | True | 4 / 4 |  |  |
| s2-api | C2 | r1 | success | 25 | 2,050,584 | 26,800 | 1.81 | True | 5 / 5 | Design and implement a bookmarks REST API with FastAPI and SQLite in app/main.py, including Pydantic schemas, error handling with proper status codes, and pytest tests | `uasl/api-design`, `uasl/fastapi-endpoint` |
| s2-api | C2 | r2 | success | 23 | 1,559,133 | 26,993 | 1.43 | True | 5 / 5 | Design and implement a bookmarks REST API in FastAPI (app/main.py) with SQLite storage, Pydantic schemas, error handling with REST status codes, and pytest tests | `uasl/fastapi-templates`, `uasl/api-design` |
| s2-api | C2 | r3 | success | 29 | 1,927,426 | 26,063 | 1.48 | True | 5 / 5 | Design and implement a FastAPI REST API for bookmarks backed by SQLite in app/main.py with Pydantic schemas, error handling (404/409/422), tag filtering, pagination, and pytest tests | `uasl/api-design`, `uasl/fastapi-templates` |
| s2-api | C2 | r4 | success | 23 | 1,870,639 | 19,541 | 1.30 | True | 4 / 4 | Design and implement a FastAPI REST API for bookmarks in app/main.py with SQLite storage, Pydantic schemas, error handling, and pytest tests | `uasl/api-design`, `uasl/fastapi-templates` |
| s2-api | C2 | r5 | success | 20 | 1,202,286 | 25,091 | 1.30 | True | 5 / 5 | Design and implement a FastAPI REST API for bookmarks in app/main.py with SQLite storage, Pydantic schemas, error handling (404/409/422), pagination, tag filtering, and pytest tests | `uasl/api-design`, `uasl/fastapi-templates` |
| s2-docs | A | r1 | success | 10 | 685,830 | 9,017 | 0.89 | True | 4 / 4 |  |  |
| s2-docs | A | r2 | success | 9 | 595,837 | 7,798 | 0.55 | True | 4 / 5 |  |  |
| s2-docs | A | r3 | success | 9 | 687,962 | 8,234 | 0.60 | True | 4 / 4 |  |  |
| s2-docs | A | r4 | success | 15 | 1,234,602 | 11,865 | 0.81 | True | 4 / 4 |  |  |
| s2-docs | A | r5 | success | 10 | 785,875 | 9,577 | 0.65 | True | 4 / 4 |  |  |
| s2-docs | B | r1 | success | 8 | 733,233 | 9,689 | 0.64 | True | 5 / 5 |  |  |
| s2-docs | B | r2 | success | 13 | 1,053,458 | 13,077 | 0.81 | True | 4 / 4 |  |  |
| s2-docs | B | r3 | success | 10 | 831,163 | 9,081 | 0.64 | True | 5 / 5 |  |  |
| s2-docs | B | r4 | success | 8 | 639,418 | 8,905 | 0.60 | True | 5 / 5 |  |  |
| s2-docs | B | r5 | success | 9 | 724,544 | 8,404 | 1.07 | True | 5 / 4 |  |  |
| s2-docs | C2 | r1 | success | 21 | 1,944,352 | 13,883 | 1.20 | True | 4 / 4 | Write a README.md and usage documentation for a Next.js TypeScript example project at the repository root | `uasl/quill` |
| s2-docs | C2 | r2 | success | 15 | 1,103,444 | 7,104 | 0.74 | True | 5 / 4 | Write a README and usage documentation for a Next.js TypeScript example project | `uasl/quill` |
| s2-docs | C2 | r3 | success | 15 | 1,016,661 | 7,846 | 0.75 | True | 5 / 5 | Write a README.md and usage documentation for a Next.js TypeScript example project | `uasl/quill` |
| s2-docs | C2 | r4 | success | 20 | 1,645,874 | 10,372 | 1.42 | True | 4 / 4 | Write a README and usage documentation for a Next.js TypeScript example project | `uasl/quill` |
| s2-docs | C2 | r5 | success | 17 | 1,332,644 | 10,048 | 0.90 | True | 4 / 5 | Write a README and usage documentation for a Next.js TypeScript example app (pages router, API routes) in README.md and docs/ | `uasl/quill`, `uasl/spec-miner` |
| s2-data | A | r1 | success | 12 | 909,068 | 12,304 | 0.79 | True | 5 / 4 |  |  |
| s2-data | A | r2 | success | 16 | 1,187,114 | 20,222 | 1.37 | True | 4 / 4 |  |  |
| s2-data | A | r3 | success | 9 | 641,312 | 17,057 | 0.86 | True | 4 / 4 |  |  |
| s2-data | A | r4 | success | 20 | 1,469,249 | 23,043 | 1.30 | True | 5 / 5 |  |  |
| s2-data | A | r5 | success | 9 | 747,728 | 18,703 | 0.94 | True | 5 / 5 |  |  |
| s2-data | B | r1 | success | 18 | 1,199,671 | 16,448 | 0.99 | True | 5 / 4 |  |  |
| s2-data | B | r2 | success | 14 | 991,464 | 16,776 | 0.94 | True | 5 / 4 |  |  |
| s2-data | B | r3 | success | 12 | 769,067 | 16,746 | 0.88 | True | 5 / 4 |  |  |
| s2-data | B | r4 | success | 11 | 782,432 | 15,401 | 1.18 | True | 5 / 4 |  |  |
| s2-data | B | r5 | success | 9 | 854,603 | 17,602 | 1.31 | True | 5 / 4 |  |  |
| s2-data | C2 | r1 | success | 16 | 1,359,890 | 14,609 | 1.06 | True | 4 / 4 | Write a Python pandas script scripts/clean_orders.py that cleans a messy orders CSV (missing values, inconsistent formats) and writes a clean CSV plus a summary report to out/, run with uv | `uasl/data-analyst-engine`, `uasl/python-error-handling` |
| s2-data | C2 | r2 | success | 18 | 1,594,654 | 15,970 | 1.15 | True | 5 / 4 | Write a Python pandas script scripts/clean_orders.py that cleans a messy orders CSV (missing values, inconsistent formats) and writes a clean CSV plus a summary report to out/, run with uv | `uasl/data-analyst-engine`, `uasl/python-error-handling` |
| s2-data | C2 | r3 | success | 25 | 1,518,055 | 18,586 | 1.25 | True | 4 / 4 | Write a Python pandas script scripts/clean_orders.py that cleans a messy orders CSV (missing values, inconsistent formats) and writes a clean CSV plus a summary report to out/, run with uv | `uasl/data-analyst-engine`, `uasl/python-error-handling` |
| s2-data | C2 | r4 | success | 26 | 2,031,182 | 22,836 | 1.74 | True | 5 / 5 | Write a Python pandas script scripts/clean_orders.py, run with uv, that cleans a messy data/orders.csv (missing values, inconsistent formats) and writes a clean CSV and a summary report to out/ | `uasl/data-analyst-engine`, `uasl/python-error-handling` |
| s2-data | C2 | r5 | success | 16 | 1,387,734 | 16,166 | 1.13 | True | 5 / 5 | Write a Python pandas script scripts/clean_orders.py that cleans a messy data/orders.csv (missing values, inconsistent formats) and writes a clean CSV plus a summary report to out/, run with uv | `uasl/data-analyst-engine`, `uasl/python-error-handling` |
