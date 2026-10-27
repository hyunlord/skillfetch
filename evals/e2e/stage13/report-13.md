# Stage 13 — 인기 스킬 묶음(P) 대 skillfetch(R) 보고

실행 2026-10-27. 설계는 `stage13/DESIGN.md`(기록 §7), 고정 파일은 `stage13-private/FROZEN-13.sha256`이다. 이 보고에는 숫자와 인용만 적는다. 비용은 구독 사용량을 API 단가로 환산한 값이다.

- **조건**(E1, Q1·Q1 확장의 18개 태스크 × 3회):
  - **A**: 라우터·MCP 없음(Stage Q / Q1 확장 실행 재사용. Q1 6개의 3회차는 이번에 돌림)
  - **P**: 인기 스킬 8개를 `.claude/skills`에 설치, 라우터·MCP 없음. 8개는 improve-codebase-architecture, tdd, frontend-design, domain-modeling, vercel-react-best-practices, web-design-guidelines, design-taste-frontend, vercel-composition-patterns다(선정 규칙 DESIGN §1.2, 웹 편중은 §6 한계).
  - **R**: 라우터 S-b′ + skillfetch MCP(staging-4)(재사용. Q1 6개의 3회차는 이번에 돌림)
- **판정**: A·P·R 결과물 9개를 한 세트에 섞어 새로 블라인드 판정했다(Claude p1·p2, 새 판정자 8명, Q1·Q1 확장과 같은 루브릭).

## 1. 태스크별 A / P / R

점수는 판정자 두 명의 평균이다. 디자인은 `(b) 쓸만함 1-5`, 나머지는 `총점 1-5`다. 체크는 태스크 원래 체크(3회 중 통과)다. 턴은 중앙값, 비용은 평균 API 단가 환산이다.

| 묶음 | 태스크 | 점수 A / P / R | 체크 A / P / R | 턴 A / P / R | 비용 A / P / R | 참고: 이전 판정 A / R |
|---|---|---|---|---|---|---|
| 디자인 | d1-landing | 3.00 / **1.33** / 4.67 | 3 / 3 / 3 | 6 / 41 / 27 | $0.35 / $3.20 / $0.96 | 3.00 / 5.00 |
| 디자인 | d2-redesign | 3.50 / 4.50 / 3.67 | 3 / 3 / 3 | 9 / 24 / 16 | $0.29 / $1.19 / $0.58 | 4.00 / 4.33 |
| 디자인 | d3-dashboard | 4.00 / 3.67 / 3.00 | 3 / 3 / 3 | 15 / 25 / 25 | $0.51 / $1.17 / $0.90 | 4.00 / 3.17 |
| 디자인 | d4-email | 4.33 / 4.67 / 4.00 | 3 / 3 / 3 | 16 / 15 / 16 | $0.49 / $0.54 / $0.63 | 4.50 / 4.00 |
| Rust | s10-t016 | 5.00 / 5.00 / 5.00 | 3 / 3 / 3 | 5 / 4 / 14 | $0.23 / $0.28 / $0.49 | 5.00 / 5.00 |
| Rust | s10-t263 | 4.83 / 4.83 / 4.83 | 3 / 3 / 3 | 4 / 4 / 14 | $0.25 / $0.25 / $0.42 | 4.83 / 4.83 |
| Rust | s10-t115 | 5.00 / 5.00 / 5.00 | 3 / 3 / 3 | 8 / 7 / 34 | $0.35 / $0.37 / $0.58 | 4.67 / 4.67 |
| Rust | s11-t266 | 4.67 / 4.67 / 4.67 | 3 / 3 / 3 | 6 / 7 / 17 | $0.30 / $0.35 / $0.52 | 4.50 / 5.00 |
| Swift | s10-t198 | 4.67 / 5.00 / 5.00 | 3 / 3 / 3 | 7 / 9 / 15 | $0.33 / $0.48 / $0.63 | 4.50 / 4.83 |
| Go | s11-t160 | 5.00 / 5.00 / 5.00 | 3 / 3 / 3 | 5 / 6 / 10 | $0.23 / $0.23 / $0.35 | 5.00 / 5.00 |
| Java | s11-t118 | 4.67 / 4.00 / 3.67 | 2 / **0** / 1 | 8 / 7 / 15 | $0.24 / $0.24 / $0.44 | 4.33 / 3.50 |
| TS | s2-docs | 4.67 / 4.83 / 5.00 | 3 / 3 / 3 | 8 / 7 / 14 | $0.35 / $0.32 / $0.52 | 4.67 / 5.00 |
| TS | s10-t033 | 4.83 / 5.00 / 5.00 | 3 / 3 / 3 | 9 / 9 / 13 | $0.27 / $0.29 / $0.36 | 4.83 / 5.00 |
| Python | s2-api | 4.50 / 4.83 / 5.00 | 3 / 3 / 3 | 10 / 12 / 19 | $0.49 / $0.61 / $0.86 | 4.50 / 5.00 |
| Python | s2-data | 4.33 / 4.67 / 4.83 | 3 / 3 / 3 | 12 / 13 / 18 | $0.64 / $0.61 / $0.77 | 4.25 / 4.50 |
| Python | s2-tests | 5.00 / 5.00 / 5.00 | 3 / 3 / 3 | 9 / 6 / 13 | $0.66 / $0.67 / $0.90 | 4.83 / 5.00 |
| Python | s10-t001 | 4.67 / 5.00 / 5.00 | 3 / 3 / 3 | 10 / 9 / 16 | $0.30 / $0.33 / $0.43 | 4.67 / 5.00 |
| Python | s6b-t179 | 4.83 / 4.67 / 5.00 | 3 / 3 / 3 | 11 / 11 / 14 | $0.39 / $0.43 / $0.45 | 4.83 / 5.00 |

| 합계 | A | P | R |
|---|---|---|---|
| 점수 평균(18 태스크) | 4.528 | 4.537 | 4.630 |
| 점수 평균(d1-landing 제외 17) | 4.618 | 4.725 | 4.627 |
| 체크 | 53/54 | 51/54 | 52/54 |
| 평균 API 단가 환산 | $0.370 | $0.642 | $0.599 |

- **판정자 일치**: 162쌍 중 같은 점수 137, 1점 이내 162다.
- **"참고: 이전 판정"**은 Stage Q Q1·Q1 확장 때 A·R만 넣은 세트의 점수다(Q1 6개는 2회). 이번 세트의 A·R 점수와 같은 결과물이어도 세트 구성이 달라 점수가 다를 수 있다.
- **추가 테스트 함수 수**(평균, 같은 규칙으로 셈. Q1 확장 보고의 셈 방식과 다름):
  - s2-api A 28.7 / P 28.7 / R 30.3
  - s2-tests 82.3 / 72.0 / 74.7
  - s10-t198 4.0 / 5.0 / 4.3
  - s10-t016 1.7 / 2.7 / 3.3
  - s10-t001 1.3 / 2.3 / 1.3
  - s2-data 0 / 3.0 / 0
  - 그 밖은 0–2다(`stage13-private/metrics-13.json`).

### 1.1 d1-landing의 P

- **턴 한도**: 세 세션 모두 40턴 한도에서 끝났다(result `error_max_turns`, 41턴, $3.09–$3.28). 최종 답은 비어 있다.
- **디자인 스킬 파일 읽기**: m1의 도구 호출 중 26회가 design-taste-frontend 폴더 파일을 읽은 것이다. 이 스킬은 파일 39개, 2.4MB다.
- **스크롤 등장 애니메이션**: 세 세션의 페이지 모두 섹션을 `opacity: 0`으로 두고 `IntersectionObserver`로 보이게 한다(diff에서 opacity 0 줄 2–3개, IntersectionObserver 1–2개). 체크의 정지 화면 캡처에는 그 섹션이 빈칸으로 남는다.
- **판정자 근거**:
  - p2: "render the features and pricing sections as blank at both widths, so I scored them 1"
  - p1: "large blank areas where the features and pricing sections should be"
- 체크는 세 세션 모두 통과했다(파일과 빌드는 턴 한도 전에 끝남).

### 1.2 s11-t118의 P

체크(doclint) 통과 0/3이다(A 2/3, R 1/3). P는 이 태스크에서 스킬을 쓰지 않았다.

## 2. P가 실제로 쓴 스킬 대 R이 로드한 스킬

P는 Skill 도구 호출과 `.claude/skills/<이름>/` 파일 읽기를 센다. R은 `resolve_set`/`resolve_and_load`의 `included`다.

| 태스크 | P: 8개 중 쓴 스킬(세션 수) | P: 그 밖의 스킬 | R: 로드한 스킬(세션 수) |
|---|---|---|---|
| d1-landing | design-taste-frontend 3/3 | – | copywriting 3, frontend-design 3, next-best-practices 1 |
| d2-redesign | design-taste-frontend 2, frontend-design 1 (3/3 세션) | – | redesign-skill 3, responsive-design 3, frontend-design 1 |
| d3-dashboard | design-taste-frontend 1 (1/3) | dataviz 3 | next-best-practices 2, frontend-a11y 2, vercel-react-best-practices 2, frontend-design 1 |
| d4-email | frontend-design 2 (2/3) | – | email-marketing 3, frontend-design 2, redesign-skill 1 |
| s10-t016 | – | – | m07-concurrency 3, rust-patterns 2, rust-testing 1 |
| s10-t263 | – | – | m01-ownership 3, m10-performance 3 |
| s10-t115 | – | – | domain-embedded 3, unsafe-checker 3 |
| s11-t266 | – | – | domain-web 3, m07-concurrency 3 |
| s10-t198 | – | – | core-data 3, migration-patterns 3 |
| s11-t160 | – | – | – |
| s11-t118 | – | – | java-coding-standards 2, receiving-code-review 2 |
| s2-docs | – | – | quill 3 |
| s10-t033 | – | – | debug-root-cause 1 |
| s2-api | tdd 1 (1/3) | – | api-design 3, fastapi-patterns 3 |
| s2-data | – | – | data-analyst-engine 3 |
| s2-tests | tdd 1 (1/3) | – | python-testing 3, radar 2 |
| s10-t001 | – | – | – |
| s6b-t179 | – | sqlmodel 3 | sqlmodel 1(레포에 있던 프로젝트 스킬을 path:로 고정) |

- **P가 8개 중 하나라도 쓴 세션**: 54개 중 11개(디자인 9, Python 2)다. Rust·Swift·Go·Java·TS 태스크에서는 0이다.
- **8개 중 한 번도 쓰이지 않은 스킬**: improve-codebase-architecture, domain-modeling, vercel-react-best-practices, web-design-guidelines, vercel-composition-patterns.
- **로드 경로**: Skill 도구 호출과 SKILL.md·딸린 파일 읽기다. design-taste-frontend 세션은 둘 다 썼고, tdd 두 세션은 파일 읽기만 했다.
- **"그 밖의 스킬"**: `sqlmodel`은 fastapi 시작 커밋에 원래 있던 프로젝트 스킬이다(A·R에도 있음). `dataviz`는 P 8개에도 레포에도 없는 스킬로, Skill 도구 호출로 불렸다(출처는 확인하지 않음).
- **스킬 목록 크기**: P 8개의 이름·설명은 1,388자(약 347 토큰)다.

## 3. 비용과 실행 기록

- **API 단가 환산 $43.79**(상한: 처음 $42, 실행 중 사용자 결정으로 $48):
  - P 본 실행 $34.66
  - P 파일럿 $2.12
  - Q1 6개 A·R 3회차 $7.01
- **실행 결과**: 본 실행 66/66 성공(harness_fail, 남은 프로세스 0)이다.
- **상한 변경**:
  - 첫 12 job 뒤에 큐가 비용 투영($42.05)으로 멈췄다. 원인은 P d1-landing m1 $3.23이었다(추정 $1.24).
  - 사용자 선택: "Raise cap to $48". d1-landing P 추정을 $3.2로 바꿔 재개했다.
- **파일럿**(집계 밖): 세 세션 모두 init에 8개가 보였다.
  - d2-redesign $1.30, design-taste-frontend 사용
  - s10-t263 $0.29, 스킬 없음
  - s2-api $0.53, 스킬 없음, 체크 실패
- **판정 패키지 감사**: "canary"(s2-docs diff의 Next.js 브랜치 URL)는 Q1 확장 때처럼 감사어에서 뺐다(`cnry`는 유지).
- **판정자 접근**:
  - 판정자 2명이 자기 판정을 쓴 뒤 공용 출력 폴더의 다른 판정 파일 표 행 수만 셌다(점수·글은 안 봄, 판정자 회신).
  - 나머지는 허용 폴더 밖을 열지 않았다고 회신했다.

## 4. 한계

- P 8개는 skills.sh 설치 순위로 고른 인기 묶음이다. 8개 중 5개가 웹·프론트엔드이고, Rust·Swift·Go·Java 전용 스킬은 없다(DESIGN §1.3).
- 디자인 태스크 점수는 정지 화면 캡처(넓은 화면·좁은 화면)로 매긴다. 스크롤해야 보이는 섹션은 빈칸으로 찍힌다(§1.1).
- A·R은 다른 날짜의 실행을 재사용했다(Q1 6개의 3회차만 이번에 돌림). 같은 하네스·서버·index·체크다.
- 태스크 18개, 3회 반복이다. 판정은 Claude 하위 에이전트 두 명이다.

## 5. 파일

- **설계·기록**: `stage13/DESIGN.md`
- **스크립트**: `stage13/scripts/`(`run_13.py`, `run_queue_13.py`, `usage_13.py`, `metrics_13.py`, `redact_13.py`, `build_blind_13.py`, `unblind_13.py`)
- **비공개**: `stage13-private/`
  - 재료: `p-skills/`, `p-skills-manifest.json`
  - 결과: `runs/`, `usage.json`, `metrics-13.json`, `judging-13.json`
  - 판정: `judge/`, `judge-package/`, `keys/`
- skills.sh 스냅샷: `stage13/skillssh-alltime-2026-10-27.json`
