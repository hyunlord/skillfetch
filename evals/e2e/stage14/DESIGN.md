# Stage 14 설계 — 연속 작업 세션: 고정 설치(P) vs 작업별 적용(R) (설계만, 실행 전)

작성 2026-10-27. **실행하지 않는다.** 세션 수와 환산 비용을 보고하고 멈춘다. 보고는 숫자와 인용만 쓰고, 비용은 구독 사용량을 API 단가로 환산한 값이다("API 단가 환산"). 아래 정의는 결과를 본 뒤 바꾸지 않는다. 바꿀 일이 생기면 날짜와 함께 §9에 따로 적는다.

사용자 지시(원문):
> Stage 14 설계만(실행 X): 연속 작업 세션에서 고정 설치 vs 작업별 적용.
> - 레포: 여러 영역이 한 레포에 있는 모노레포 하나(웹 프런트, Python API, Rust 크레이트, 문서). Stage Q의 sq-mono를 키우거나 새로 만든다.
> - 한 세션(--resume)에서 종류가 다른 작업 6개를 연달아: 랜딩 페이지 → API 엔드포인트 추가 → 그 API 테스트 → Rust 동시성 수정 → README 문서 → 데이터 스크립트.
>   작업마다 기존 체크·루브릭 방식으로 숨은 체크를 만든다. 순서 효과를 보려고 두 가지 순서(위 순서와 역순)로 돌린다.
> - 조건: A(스킬 없음), P(Stage 13의 인기 스킬 8개 고정 설치), R(skillfetch 라우터, release index). 조건 × 순서 2 × 3회.
> - 측정(작업별, 실행 전 고정): 블라인드 점수, 체크, 그 작업에서 실제로 적용·로드된 스킬, 앞 작업 스킬이 뒤 작업 결과물에 흔적을 남겼는지
>   (예: 디자인 규칙이 백엔드 코드에, 앞 스킬 이름 언급), 작업 시작 시점의 컨텍스트 크기, 작업별·세션 전체 턴과 토큰과 환산 비용.
> - 판정 기준(실행 전 고정): 작업 6개 평균 점수 R − P, R − A, 그리고 영역이 바뀐 직후 작업(2~6번째)만 따로 본 R − P. 비용 대비 효과도 같이 보고한다.
> - 세션 수와 환산 비용을 추정해서 보고하고 멈춘다.

참고: 사용자는 2026-10-27에 "실험 단계는 Stage 13으로 마무리한다"고 했다. 같은 날 이 설계를 새로 지시했으므로 설계만 하고, 실행 여부는 사용자가 정한다.

## 1. 레포 `s14-mono` (새로 만든다)

sq-mono(web 정적 HTML, py CLI, Rust 포맷 라이브러리)는 영역별 숨은 체크가 없다(Stage Q2는 체크 없이 canary만 봤다). 그래서 **체크가 이미 검증된 Stage 10·11·Q 태스크 레포의 시작 트리를 한 레포의 하위 디렉터리로 합친다.** 각 영역의 체크·루브릭·참고 해답을 경로만 바꿔 다시 쓸 수 있다.

| 디렉터리 | 출처(시작 커밋의 파일 트리) | 기술 | 파일 수 |
|---|---|---|---:|
| `web/` | `nextjs` `s6b-a`(d1-landing의 시작점, with-typescript 예제 앱, 사용자 4명 샘플 데이터) | Next.js pages, TypeScript | 16 |
| `api/` | `s2-api` `s6b-a`(북마크 API의 빈 시작점) | FastAPI, SQLite, pytest, uv | 4 |
| `media/` | `s11-t266` `s11-a`(axum CMS의 이미지 리사이즈) | Rust, tokio, axum, image | 15 |
| `data/` | `s2-data` `s6b-a`(지저분한 `orders.csv`) | Python, uv | 4 |
| 루트 | 없음(루트 README 없음, 하위 README는 출처 그대로) | – | – |

- 커밋 작성자는 `e2e <e2e@local>`, 날짜는 고정한다(Stage 12 레포의 시작 커밋처럼 실제 이름이 들어가지 않게).
- 같은 태스크를 Stage 13에서 따로(새 세션) 돌린 결과가 있다(d1-landing, s2-api, s11-t266, s2-data, 그리고 테스트·문서는 비슷한 종류 s2-tests, s2-docs). 이것은 **참고 줄**로만 쓴다(레포·경로가 달라 같은 조건이 아니다).
- 출처 레포 사이의 충돌 점검: 루트에 `package.json`·`pyproject.toml`·`Cargo.toml`을 두지 않는다. 각 영역은 자기 디렉터리에서 빌드·테스트한다. 준비 단계에서 네 영역의 시작 상태 빌드·테스트가 루트 clone에서 그대로 도는지 확인한다.

## 2. 작업 6개와 순서

요청 원문은 출처 태스크의 원문을 그대로 쓰고, 경로만 하위 디렉터리로 바꾼다(아래 "바뀌는 부분"). 바꾼 원문은 준비 단계에서 `stage14/requests.md`에 고정하고 해시를 남긴다.

| # | 작업 | 출처 원문 | 바뀌는 부분 | 숨은 체크(기존 방식) | 루브릭 |
|---|---|---|---|---|---|
| 1 | 랜딩 페이지 | d1-landing | "이 앱" → "`web/` 앱" | 6b d1 체크(빌드, `/landing` 응답, 1280·375 스크린샷, 가로 넘침) | rubric-design |
| 2 | API 엔드포인트 추가 | s2-api | 경로 `app/main.py` → `api/app/main.py` 등 | s2 계약 검사(27항목) | rubrics-s2 (api) |
| 3 | 그 API 테스트 | **새 원문**(아래) | – | 새 체크: 변이 검사(아래) | rubrics-s2 (tests) 일반 부분 + 이 태스크 행(실행 전 작성) |
| 4 | Rust 동시성 수정 | s11-t266 | `routes/media.rs` → `media/src/routes/media.rs` | t266 probe 체크(spawn_blocking·Semaphore, 판정 불가 규칙 그대로) | rubric-b4-add (t266 행) |
| 5 | README 문서 | s2-docs | "이 레포" 그대로(루트 README가 없는 모노레포) | s2 docs 체크를 모노레포용으로 다시 만든다(아래) | rubrics-s2 (docs) |
| 6 | 데이터 스크립트 | s2-data | `data/orders.csv` → `data/data/orders.csv` 등 | s2 data 체크(출력 파일, 요약 리포트 항목) | rubrics-s2 (data) |

- **작업 3 원문(새로 씀, 실행 전 고정)**: "`api/`의 북마크 API에 테스트를 보강해줘. 엔드포인트별 정상·오류 경로와 엣지케이스까지." 체크:
  - (a) 세션이 쓴 테스트가 세션 자신의 API에서 통과한다.
  - (b) 세션이 쓴 테스트를 **참고 구현**(s2-api 참고 해답, 같은 계약)에 돌려서 통과한다. 계약 밖의 내부 구현에 묶인 테스트를 걸러 낸다.
  - (c) 참고 구현의 **변이 8개**(준비 단계에서 고정: 404 대신 200, 검증 누락, 페이지 경계, 중복 허용 등)에서 실패하는 테스트가 있는 변이의 수. 체크 통과는 (a)·(b) 통과로 하고, (c)는 숫자로 보고한다.
- **작업 5 체크(모노레포용)**: 출처 s2 docs 체크 방식(문서에 있어야 하는 사실 목록을 레포에서 뽑아 확인, 없는 명령·경로를 쓰면 실패)을 따르되, 사실 목록은 `s14-mono` 시작 커밋에서 뽑는다(네 영역의 실행·테스트 명령, 환경변수 `BOOKMARKS_DB` 등). 앞 작업이 만든 것(랜딩, 엔드포인트)을 문서에 쓰는 것은 실패도 가산도 아니다.
- **순서**:
  - 정순 F: 1 → 2 → 3 → 4 → 5 → 6.
  - 역순 B: 6 → 5 → 4 → **2 → 3** → 1. "그 API 테스트"(3)는 엔드포인트(2)가 있어야 하므로 이 쌍만 순서를 유지한다(순수 역순이면 3이 2보다 먼저 와서 대상이 없다). 이 예외는 실행 전에 고정한다.
- **영역이 바뀐 직후 작업**: 앞 요청과 영역(web / api / media / docs / data)이 다른 요청. 정순에서는 2·4·5·6번째(3번째인 API 테스트는 같은 api 영역이라 뺀다), 역순에서는 2·3·4·6번째(5번째인 API 테스트는 뺀다). 사용자 지시의 "2~6번째"를 이렇게 정의한다.

## 3. 조건과 하네스

| 조건 | 설치 | MCP | 시작 브랜치 |
|---|---|---|---|
| A | 없음 | 없음 | `s14-a` |
| P | Stage 13의 P 스킬 8개를 `.claude/skills/`에(Stage 13 고정 커밋·해시 그대로, `p-skills-manifest.json`) | 없음 | `s14-p` |
| R | 라우터 S-b′(현재 main의 출시본) | skillfetch MCP, **release index**(2,785 스킬, `~/.skillfetch/index`의 사본을 해시로 고정) | `s14-r` |

- 환경은 E1(Stage 11·12·13과 같음: 프로젝트 설정만, strict MCP 설정, 요청마다 `--max-turns 40`).
- **한 세션**: 첫 요청은 `claude -p`, 이어지는 요청은 `claude -p --resume <session_id>`로 같은 작업 트리에서 보낸다(Stage Q2 S와 같은 방식, 하네스 `run_q.py`의 q2 S 경로를 넓힌다).
- **요청마다 스냅샷 커밋**(Stage 12 `snapshot_commit` 방식). 작업 k의 결과물은 스냅샷 k−1 → k의 diff다. 체크도 그 스냅샷을 따로 꺼낸 디렉터리에서 돌린다(랜딩 스크린샷은 랜딩 요청이 끝난 시점의 트리로 찍는다. 뒤 작업이 `web/`을 고쳐도 영향이 없다).
- 그 밖의 격리 규칙은 그대로: `--no-local` 단일 브랜치 clone, 무작위 디렉터리, 중립 커밋 메시지, 사전 점검, 남은 프로세스 검사. 큐가 도는 동안 e2e 경로가 들어간 명령을 실행하지 않는다.
- 반복: 조건 3 × 순서 2 × 3회 = **18세션, 요청 108개**. 파일럿은 조건마다 정순 1세션씩 3세션(요청 18개)이며 본 실행에 넣지 않는다.

## 4. 측정 (작업별, 실행 전 고정)

1. **블라인드 점수**: 작업마다 한 세트(조건 3 × 순서 2 × 3회 = 결과물 18개, 무작위 코드). 새 판정자 두 명(p1, p2, fork 아님). 위 표의 루브릭, Stage 13과 같은 형식 검사 → 키 공개 순서. 점수는 (p1+p2)/2. 작업 4의 최종 답 가림은 Stage 10 §4.6 규칙(`redact_s11.process`)을 세 조건에 같게 쓴다.
2. **체크**: 위 표의 숨은 체크. 판정 불가는 따로 센다.
3. **적용·로드된 스킬(그 요청 구간 안에서)**:
   - P: Skill 도구 호출 + `.claude/skills/<이름>/` 아래 파일 읽기(Stage 13 `usage_13.py` 규칙).
   - R: `resolve_set`/`resolve_and_load`/`load_skills` 결과의 `included`, 그리고 라우터 Skill 호출 여부(Stage RF의 "Skill"/"MCP만" 구분).
   - A·P·R 공통: 모든 Skill 도구 호출 이름(레포·기본 제공 스킬 포함).
4. **앞 작업 스킬의 흔적**(작업 k, 그 세션에서 1…k−1 요청에 적용·로드된 스킬이 하나라도 있을 때):
   - (a) **이름 언급**: 앞 스킬의 이름이나 id가 작업 k의 최종 답, diff, 새 파일에 나온 수.
   - (b) **영역 밖 수정**: 작업 k의 diff가 그 작업 영역 디렉터리(+ 루트 README·lock 파일) 밖의 파일을 바꾼 수. 예: Rust 작업 중 `web/` 수정.
   - (c) **규칙 흔적 판정**: 새 판정자(조건 이름 없음)에게 작업 k의 diff와 "이 세션에서 앞서 쓰인 스킬의 이름·설명"(본문 아님)을 주고, 그 스킬의 규칙이 이 결과물에 적용된 흔적이 있는지 예/아니오와 diff 인용을 받는다. 인용은 diff 원문과 대조해 맞지 않으면 "아니오"로 센다. A는 앞 스킬이 없으므로 대상이 아니다(레포·기본 제공 스킬을 부른 경우는 그 스킬로 똑같이 센다).
5. **작업 시작 시점의 컨텍스트 크기**: 그 요청의 첫 assistant 이벤트 usage의 input + cache read + cache creation 토큰.
6. **턴·토큰·비용**: 요청마다 result 이벤트의 `num_turns`, usage 합, `total_cost_usd`. 세션 전체는 그 합이다. 40턴 한도(`error_max_turns`)로 끝난 요청 수를 따로 센다.

## 5. 판정 기준 (실행 전 고정)

점수는 Claude (p1+p2)/2, 조건별로 그 작업 18개 결과물 중 해당 조건 6개(순서 2 × 3회)의 평균이다.

| 이름 | 정의 |
|---|---|
| (i) 6작업 평균 R − P | 작업 6개 점수 평균(조건마다 결과물 36개)의 차 |
| (ii) 6작업 평균 R − A | 같은 방식 |
| (iii) 영역 바뀐 직후 R − P | §2의 "영역이 바뀐 직후 작업"(정순 2·4·5·6번째, 역순 2·3·4·6번째)만, 조건마다 결과물 24개 |
| (iv) 비용 대비 | 조건별 세션 평균 API 단가 환산, 그리고 (R − P) / (R 비용 − P 비용), (R − A) / (R 비용 − A 비용). 분모가 0 이하이면 "R이 같거나 더 적은 비용"으로 적는다 |

- 함께 내는 줄: 순서별(F, B) 같은 차, 작업별 차, 판정자별(p1, p2) 차, 체크 통과 수.
- **노이즈 폭(제안, 사용자 확인 필요)**: Stage 11의 D 방식대로 D = max(조건별 |p1 − p2| 평균의 최댓값, 0.25). |차| ≤ D이면 보고에 "판정자 차이 폭 안"이라고 숫자와 함께 적는다. 통과/불통과 게이트는 지시에 없으므로 두지 않는다.

## 6. 세션과 비용 추정 (API 단가 환산)

**근거 1 — 같은 종류 작업의 새 세션 비용**(Stage 13 조건별 평균, 달러):

| 작업 | 근거 태스크 | A | P | R |
|---|---|---:|---:|---:|
| 1 랜딩 | d1-landing | 0.35 | 3.20(40턴 한도 ×3) | 0.96 |
| 2 API 추가 | s2-api | 0.49 | 0.61 | 0.86 |
| 3 API 테스트 | s2-tests | 0.66 | 0.67 | 0.90 |
| 4 Rust 동시성 | s11-t266 | 0.30 | 0.35 | 0.52 |
| 5 README | s2-docs | 0.35 | 0.32 | 0.52 |
| 6 데이터 | s2-data | 0.64 | 0.61 | 0.77 |
| 합 | | 2.79 | 5.76 | 4.53 |

**근거 2 — 이어진 세션의 문맥 누적**: Stage RF(현재 라우터, 한 세션 4작업)의 요청별 비용은 $0.35 → $0.74 → $0.81(README 오타, 새 세션이면 $0.2 안팎) → $1.19였다. 작업 4의 입력 토큰은 52–63만이었다. 앞 요청 하나당 뒤 요청에 붙는 비용을 R $0.30, A $0.15(새 세션 토큰이 R의 약 절반), P $0.25(랜딩이 먼저 오는 정순은 $0.35)로 잡는다. 6요청 세션이면 앞 요청 수의 합이 0+1+…+5 = 15다.

| 조건 | 세션당 추정 | 세션 수 | 합 |
|---|---|---:|---:|
| A | 2.79 + 0.15×15 = $5.0 | 6 | $30.2 |
| P 정순 | 5.76 + 0.35×15 = $11.0 | 3 | $33.1 |
| P 역순 | 5.76 + 0.25×15 = $9.5 | 3 | $28.5 |
| R | 4.53 + 0.30×15 = $9.0 | 6 | $54.2 |
| **본 실행** | | **18** | **$146** |
| 여유 10% | | | $15 |
| 파일럿(조건마다 정순 1) | 5.0 + 11.0 + 9.0 | 3 | $25 |
| **합계 추정** | | **21** | **약 $186** |

- **불확실성**:
  - 누적 비용은 4요청 세션 하나(RF)에서 잰 값을 6요청으로 늘린 것이다.
  - P 역순은 랜딩이 마지막이라, 40턴 한도에 다시 걸리면 그 요청 하나가 쌓인 문맥(30만+ 토큰)을 40번 다시 읽는다. 그러면 P 역순 세션이 $15 이상이 될 수 있다.
  - 낮은 쪽 약 $140, 높은 쪽 약 $220으로 본다.
- **상한 제안**: $200. 큐는 Stage 12·13과 같은 투영 규칙(쓴 것 + 남은 세션 × 추정 > 상한이면 멈추고 보고)을 쓴다.
- **줄이는 안**(참고): 3회 → 2회(12세션 + 파일럿 3)면 약 $125다.
- 판정(작업 6 × 2 패스 = 12세트, 결과물 216개 × 2)과 흔적 판정 (c)는 Claude 하위 에이전트로 하고 세션 큐에 넣지 않는다(이전 단계와 같음).
- **시간**: 요청 하나 5–15분, 세션 하나 약 40–80분이다. 4병렬로 본 실행 약 4–6시간.

## 7. 준비 순서 (사용자 확인 뒤, 모델 호출 없음)

1. `s14-mono` 조립(§1), 작성자 `e2e`, 시작 상태 빌드·테스트 확인.
2. 요청 원문 6개 고정(`stage14/requests.md`, 해시).
3. 체크 이식(경로 바꿈)과 새 체크 2개(작업 3 변이 검사, 작업 5 모노레포 문서 사실 목록).
   - 참고 해답: 출처 태스크의 참고 해답을 하위 디렉터리로 옮긴다. 작업 3 참고는 새로 쓴다.
   - 시작 상태는 실패, 참고는 통과, 오류 사례는 실패하는지 확인한다.
4. 하네스: `run_q.py` S 경로를 6요청으로 넓히고 조건 A/P/R과 순서 F/B, 요청마다 스냅샷 커밋을 넣는다. dry-run 후 `FROZEN-14.sha256`에 고정한다.
5. 파일럿 3세션 → 보고 → 본 실행 18세션 → 판정 → 흔적 판정 → `report-14.md`.

## 8. 한계 (미리 적어 둠)

- 모노레포는 기존 태스크 레포를 합친 것이라, 영역 사이의 실제 의존(웹이 API를 부르는 등)은 작업 2–3 쌍 말고는 없다.
- 순서는 두 가지뿐이라, 순서 효과와 "어떤 작업 뒤에 오느냐"를 나눠 볼 수 없다.
- P의 8개는 Stage 13 선정 그대로라 웹 쪽으로 치우쳐 있다(Stage 13 한계와 같음).
- 판정 세트가 18개로 Stage 13(9개)보다 크다.
- 흔적 (c)는 모델 판정이다. 인용 대조로 근거 없는 "예"를 막지만, 놓치는 흔적은 남을 수 있다.

## 9. 기록

- 2026-10-27 설계 작성. 실행 안 함.
- **2026-10-27 승인(사용자)**. 원문:
  > Stage 14 승인: 2회 버전(조건 × 순서 2 × 2회 = 12세션 + 파일럿 3세션), 상한 $140. 설계는 그대로이고, 판정자 차이 D(최소 0.25) 안의 차이는
  > 보고서에서 "판정 노이즈 안"으로 표시한다(게이트 아님). 파일럿에서 P 역순의 랜딩(마지막 작업)이 40턴 한도에 걸리면 그대로 기록한다(실험 대상인 현상이다).
  > 라우터 스킬은 지금 배포본 바이트 그대로 쓴다. 끝나면 report-14.md와 갤러리(작업별 A/P/R, 앞 작업 스킬 흔적 사례 포함)를 보고한다.
  - 반복은 2회(m1, m2): 본 실행 12세션(요청 72개), 상한 $140(투영 규칙 그대로). 판정 세트는 작업마다 결과물 12개다.
  - 파일럿 3세션은 A 정순, **P 역순**, R 정순으로 한다(사용자가 P 역순 랜딩의 40턴 한도를 파일럿에서 볼 현상으로 적었으므로). 파일럿 결과는 본 실행 집계에 넣지 않는다.
  - §5의 D는 보고 표시용으로 확정: D = max(조건별 |p1 − p2| 평균의 최댓값, 0.25), |차| ≤ D이면 "판정 노이즈 안"(게이트 아님).
  - 라우터: `~/github/skillfetch` origin/main(99fe08e)의 `assets/router-skill/SKILL.md` 바이트 그대로, sha256 3efef1e0b7cf…f040(마지막 변경 d242b66, 2026-10-24). Stage 11·Q·13의 R 라우터와 같은 바이트다.
  - index: 출시 index(`~/.skillfetch/index`, 2,785 스킬)의 `skills.jsonl` sha256 54b2e303…이 Stage 10 `index/staging-4` 사본과 같다. 하네스는 그 사본(`verify_index.py`로 해시 검사)을 쓴다.
  - MCP 서버: Stage 11·Q·13 R과 같은 `3fef3f8` 고정 venv를 쓴다. main에는 그 뒤 `find_skills`·`scan_skill` 도구가 더해졌지만 배포 라우터 문구는 그 도구를 부르지 않는다. Stage 13 R과 같은 서버로 두어 P·R 비교의 변수를 하나 줄인다(이 선택은 보고서 한계에 적는다).
- **2026-10-27 준비 기록(파일럿 전, 모델 호출 없음)**
  - 레포 `repos/s14-mono`: s14-a 7e143b2c73(네 출처 트리, 파일 39개, 작성자 `e2e <e2e@local>`, 날짜 고정), s14-r 4968ec38e0(라우터 1파일, 3efef1e0…), s14-p 8ca0677708(P 스킬 143파일, Stage 13 매니페스트 해시와 같음).
  - 요청 원문 `stage14/requests.md`. 출처 원문에서 바꾼 곳:
    - 1·4·6은 경로만 바꿨다.
    - 2는 앞에 "`api/` 디렉터리에"를 붙이고 앱 경로를 `api/app/main.py`로 바꿨다.
    - 5는 "이 레포에는 README가 없어"를 "이 레포 루트에는 README가 없어"로 바꿨다. `web/`·`media/`에 출처 README가 있어 원문 그대로면 사실과 다르기 때문이다.
    - 3은 §2의 새 원문이다.
  - **체크 실행 방식**: 요청마다 그 영역의 하위 트리로 따로 레포를 만든다(커밋 1 = 요청 전, 커밋 2 = 요청 후, 문서 작업은 전체 트리). 출처 체크를 코드 변경 없이 그대로 돌린다.
  - **작업 3 체크 확정**(§2의 (b)를 바꿈, 실행 전): 통과 = (a) 세션 테스트가 자기 API에서 통과 + (b) 이 요청이 수집된 테스트 수를 늘림.
    - 변이 8개는 참고 구현이 아니라 세션 자신의 API에 ASGI 층으로 씌운다. 404→200, 409→201, 422→201/200, POST 201→200, DELETE 204→200, 목록의 `limit`·`tag`·`offset` 무시.
    - Starlette·FastAPI의 `__call__`을 감싸므로 테스트가 앱을 어떻게 만들든 적용된다. 죽인 변이 수(0–8)는 숫자로만 낸다.
    - 이유: 세션마다 내부 구조가 달라서, 참고 구현에 세션 테스트를 돌리면 계약과 무관한 import 실패가 대부분이 된다. 계약 수준 변이는 어느 구현에나 같게 걸린다.
  - **작업 5 체크**(`check_docs14.py`), 통과 = 아래 넷 모두:
    - 루트 README.md;
    - 이 요청이 쓴 문서가 `web/`·`api/`·`media/`·`data/`를 모두 언급;
    - 문서의 npm 스크립트가 `web/package.json`에 있음;
    - 백틱 안 저장소 경로가 실제로 있음.
  - **검증**(`stage14/scripts/validate_14.py`, `stage14-private/validation/validation.json`): 참고 6개는 모두 통과했다.
    - 작업 3 참고는 변이 8/8을 죽였다. 작업 2 참고(Stage Q R s2-api m2)의 자체 테스트 49개도 8/8을 죽였다.
    - 변경 없는 트리 6개는 모두 실패했다.
    - 첫 검증에서 두 가지를 고쳤다: 스크린샷 잠금 폴더가 없었고, FastAPI가 자체 `build_middleware_stack`을 써서 변이가 걸리지 않았다(0/8 → 8/8).
  - 큐 `stage14/scripts/run_queue_14.py`: 3병렬, 상한 $140(파일럿 포함 투영). 세션당 추정은 A $5.0, P 정순 $11.0, P 역순 $9.5, R $9.0이고 파일럿 뒤에 갱신한다. 본 실행 순서는 시드 `s14-<tag>`로 섞는다.
  - 해시: `stage14-private/FROZEN-14.sha256`(18개: 하네스·큐·검증 스크립트, 요청 원문, 새 체크·참고, 이식한 출처 체크, 레포 브랜치 3개. 이 문서는 기록이 계속 붙으므로 넣지 않았다).
- **2026-10-27 파일럿**(A 정순, P 역순, R 정순, 각 6요청, 모두 6/6 완료). API 단가 환산은 A $9.30, P $14.79, R $18.93, 합 $43.02다(추정 $25의 약 1.7배).
  - P 역순의 마지막 랜딩은 40턴 한도(`error_max_turns`, 41턴)에서 끝났고 $7.28이었다. 사용자 지시대로 그대로 기록한다.
  - 요청별 비용이 앞 요청 수에 따라 커지는 폭이 추정보다 컸다. A: $0.34 → 0.79 → 1.24 → 1.70 → 2.18 → 3.06.
  - 체크는 18개 중 17개 통과했다. R 정순의 README 체크 (d)가 `data/orders.csv`에서 실패했다. 이 경로는 `data/` 폴더 기준으로는 실제로 있다.
- **2026-10-27 사용자 결정**(본 실행 추정 $175, 파일럿 포함 약 $218로 상한 초과). 원문:
  > 1회로 줄여서 진행한다(조건 × 순서 2 × 1회, 상한 $140 그대로). 본 실행 전에 파일럿 3세션의 작업별 결과를 먼저 보고한다: 작업별 체크 통과, 로드·적용된 스킬, 작업별 비용과 턴, 앞 작업 스킬의 흔적이 보인 사례. 판정은 본 실행과 함께 한다. 보고 후 바로 본 실행으로 넘어간다.
  - 본 실행은 6세션(요청 36개, m1)이다. 판정 세트는 작업마다 결과물 6개다. 세션당 추정은 A $9.3, P 정순 $16.0, P 역순 $14.8, R $18.9로 바꿨다. 투영은 $43.0 + $87.2 = $130.2다.
  - 파일럿 판정 "판정은 본 실행과 함께 한다": 파일럿 결과물은 본 실행 세트와 섞지 않는다(§3 "파일럿은 본 실행에 넣지 않는다"). 흔적 (c) 판정은 파일럿에도 따로 돌려 보고한다.
- **2026-10-27 본 실행 전 수정**(파일럿에서 찾음, 본 실행 전에 고정):
  - `check_docs14.py` (d): 백틱 경로를 루트 기준이나 네 영역 폴더 기준으로 찾는다. R 정순 파일럿 README는 다시 돌리면 통과하고, 변경 없는 트리는 그대로 실패한다.
  - `run_14.py`: 요청 diff 끝에 줄바꿈을 붙인다. `git apply`로 다시 적용할 수 있게 하려는 것이다. 판정 재료에는 영향이 없다.
  - `FROZEN-14.sha256`을 24개로 다시 썼다(수정한 체크·하네스, 루브릭 `rubrics-14.md`, 판정·흔적·집계 스크립트 추가). 본 실행 시작 후에는 체크를 바꾸지 않는다.
  - 파일럿 큐가 도는 동안 e2e 경로가 들어간 명령을 두 번 실행했다(`cat`, `grep`, 각각 바로 끝남). 세 세션 모두 남은 프로세스 0이고 사전 점검 실패는 없었다.

- **2026-10-27 판정 패키지 누락(기록)**: `rubric-b4-add.md`는 척도·형식을 `stage10/rubric-b4.md`에서 가져온다고 적혀 있는데, 이 파일을 판정 패키지 `rubrics/`에 넣지 않았다(`build_blind_14.py` RUBRIC 목록 누락).
  - p1 판정자가 이를 알렸고, `rubrics-s2.md`의 1–5 기준과 judge-README의 열 형식으로 s14-rust를 판정했다.
  - 두 파일의 1–5 기준 문장은 같다. 빠진 내용은 "reply.md의 설명도 기준에 반영한다"는 한 줄이다.
  - p1·p2 모두 같은 패키지로 판정했다. 다시 판정하지 않고 보고서 한계에 적는다.
- **2026-10-27 판정 한계(기록)**: s14-docs의 `_context/`는 시작 커밋 파일만 담는다. 그래서 앞 요청들이 만든 코드(API, 데이터 스크립트, 랜딩)에 대한 문서 주장은 판정자가 코드와 대조할 수 없었다(p2 판정자 보고). 그 부분은 check.txt의 "백틱 경로가 실제로 있음" 항목에 기댔다. 보고서 한계에 적는다.
- **2026-10-27 본 실행 완료**: 6/6세션, 36요청, API 단가 환산 $87.13(파일럿 포함 $130.15, 상한 $140). 판정은 새 판정자 4명(p1·p2, 세트마다 6개)이고, 흔적 (c)는 본 실행·파일럿 판정자 각 1명이다. 보고 `stage14/report-14.md`, 갤러리 `stage14/gallery/stage14-gallery.html`.
  - 흔적 (a)에 "같은 요청이 그 스킬을 다시 로드한 경우를 뺀 수" 열을 본 실행 뒤에 더했다. R 정순 데이터 요청의 python-testing 1건이 이 경우다.
  - 하네스가 요청 diff를 `str.strip()`으로 저장해, 마지막 줄이 빈 문맥 줄(" ")이면 빠진다. 갤러리 재구성은 이 줄을 되살려 다시 적용한다(`assemble_14.py`). 판정 재료에서는 마지막 문맥 한 줄이 빠졌을 수 있다.
- 2026-10-27 고정 뒤 바뀐 파일 두 개(`usage_14.py`, `trace_14.py`)의 기록과 두 버전 비교를 §11에 적었다(사용자 지시).

## 11. 고정(FROZEN-14) 뒤에 바뀐 파일 (2026-10-27 정리, 사용자 지시)

`stage14-private/FROZEN-14.sha256`(24개, 18:00:50 작성)의 항목을 다시 대조했다. 22개는 그대로다. 두 파일이 본 실행이 끝난 직후(18:51) 18:52:37에 바뀌었다. 체크, 하네스, 큐, 판정 패키지·키 스크립트는 바뀌지 않았다.

| 파일 | 고정 sha256 | 지금 sha256 | 언제 | 무엇을 | 왜 |
|---|---|---|---|---|---|
| `stage14/scripts/usage_14.py` | 502aae3cda7c6adb… | 01ec44cf6f67c34d… | 2026-10-27 18:52(본 실행 뒤, 판정 패키지 만들기 전) | 행마다 `trace_names_not_reloaded` 필드를 더했다. 흔적 (a) 이름 목록에서 그 요청이 스스로 다시 적용·로드한 스킬을 뺀 것이다. 문서 문자열 두 줄도 고쳤다. 기존 필드는 그대로다 | R 정순 데이터 요청에서 앞 요청의 python-testing이 이름으로 나왔다. 그런데 그 요청이 python-testing을 스스로 다시 로드했으므로, 앞 요청의 흔적과 구분하려고 더했다 |
| `stage14/scripts/trace_14.py` | 7a782659777fde5b… | 00d9af233b9ace24… | 같은 시각 | 두 번째 인자 `m|p`를 받아 파일럿용 경로(`usage-14-p.json`, `trace-package-p/`, `trace-p/`, `trace-key-p.jsonl`, `trace-14-p.json`)를 쓰게 했다. 기본값 `m`의 경로와 동작은 고정본과 같다 | 사용자 결정("판정은 본 실행과 함께 한다")에 따라 파일럿의 흔적 (c)도 따로 판정하려고 |

- **고정본 복원**: 두 파일의 고정본을 지금 파일에서 위 변경을 되돌려 만들었다. sha256이 FROZEN-14와 일치한다. `stage14-private/frozen-versions/usage_14.py`, `trace_14.py`에 있고, diff는 같은 폴더의 `usage_14.diff`, `trace_14.diff`다.
- **두 버전 비교**(`stage14-private/frozen-versions/compare.json`):
  - `usage_14.py`: 본 실행 36행과 파일럿 18행에서 다른 필드는 새 필드 `trace_names_not_reloaded` 하나뿐이다. 나머지 모든 필드가 행마다 같다. 스킬, 흔적 (a)(b), 비용, 턴, 컨텍스트, 체크, 라우터 경로, 영역 전환 표시가 모두 해당한다.
  - 조건별 통계도 모두 같다. 본 실행: 스킬 적용 요청 A 0 / P 2 / R 12, 흔적 (a) 0 / 0 / 1, 흔적 (b) 4 / 4 / 4, 40턴 한도 0 / 1 / 0, 체크 12 / 11 / 12. 새 필드만 있는 통계는 "(a) 다시 로드 제외" A 0 / P 0 / R 0이다.
  - `trace_14.py verify`(본 실행): 고정본과 지금 버전의 출력 `trace-14.json`이 바이트 단위가 아니라 내용(JSON)으로 같다. 파일럿 흔적 (c)는 지금 버전으로만 계산할 수 있다(고정본에는 파일럿 경로가 없다).
- 이 정리 때 고정본에 없던 분석·갤러리 스크립트(`metrics_14.py`, `gallery/assemble_14.py`, `gallery/build_gallery_14.py`)는 본 실행 뒤에 처음 썼다. 고정 대상이 아니었다.

```diff
--- usage_14.py	2026-10-27 21:45:09
+++ ../../stage14/scripts/usage_14.py	2026-10-27 18:52:37
@@ -10,7 +10,8 @@
   conditions: every Skill tool call name; R also: router via the Skill tool ("skill") or skillfetch MCP only ("mcp") or not.
   trace (a) names: skills applied/loaded in requests 1..k-1 of the same session (P skills used, R loaded, other Skill
   calls; not the router) whose name appears in request k's final reply or diff (new files included), case-insensitive,
-  word-bounded.
+  word-bounded; trace_names_not_reloaded = the same without skills that request k also used or loaded itself
+  (added after the main run, 2026-10-27: a skill re-loaded by request k explains its own mention).
   trace (b) out_of_area: files changed by request k outside its area (web/, api/, media/, data/; for the README task:
   files that are not .md/.mdx/.txt).
 Writes stage14-private/usage-14.json and prints a table.
@@ -100,7 +101,8 @@
                          "after_domain_change": k > 1 and area != prev_area,
                          **{x: r[x] for x in ("turns", "result", "cost", "tokens_in", "tokens_out", "context_start", "skill_calls", "router")},
                          "skills": used, "other_skill_calls": others, "prior_skills": sorted(prior),
-                         "trace_names": named, "out_of_area": out_of_area(task, diff),
+                         "trace_names": named, "trace_names_not_reloaded": sorted(set(named) - set(used) - set(others)),
+                         "out_of_area": out_of_area(task, diff),
                          "check": chk.get("pass"), "undecidable": chk.get("undecidable"),
                          "mutants_killed": (chk.get("metrics") or {}).get("mutants_killed") if task == "apitests" else None})
             prior |= set(used) | set(others)
```

```diff
--- trace_14.py	2026-10-27 21:45:09
+++ ../../stage14/scripts/trace_14.py	2026-10-27 18:52:37
@@ -10,7 +10,7 @@
   verify  stage14-private/trace/<id>.json from the judge: {"skills": [{"name", "trace": "yes"|"no", "quote": "..."}]}.
           A "yes" counts only if its quote is a substring of that item's diff.patch (else counted as "no", listed as
           unverified). Writes stage14-private/trace-14.json (per item and per condition × task).
-usage: trace_14.py build | verify"""
+usage: trace_14.py build|verify [m|p]"""
 import json
 import re
 import secrets
@@ -24,7 +24,9 @@
 from build_blind_s2 import clean_diff  # noqa: E402
 
 WT = re.compile(r"/\S*?skillfetch-e2e-wt/sq/[A-Za-z0-9_.-]+")
-PKG, OUT = PRIV / "trace-package", PRIV / "trace"
+PRE = sys.argv[2] if len(sys.argv) > 2 else "m"  # m = main runs, p = pilot (reported apart)
+SUF = "" if PRE == "m" else f"-{PRE}"
+PKG, OUT = PRIV / f"trace-package{SUF}", PRIV / f"trace{SUF}"
 
 
 def descriptions():
@@ -40,7 +42,7 @@
 
 def build():
     assert not PKG.exists(), "trace package already built"
-    rows = json.loads((PRIV / "usage-14.json").read_text())
+    rows = json.loads((PRIV / f"usage-14{SUF}.json").read_text())
     desc = descriptions()
     reqs = (S14 / "requests.md").read_text()
     keys = []
@@ -59,7 +61,7 @@
         keys.append({"id": iid, "session": r["session"], "cond": r["cond"], "order": r["order"], "tag": r["tag"], "k": r["k"],
                      "task": r["task"], "skills": r["prior_skills"]})
     (PRIV / "keys").mkdir(exist_ok=True)
-    (PRIV / "keys" / "trace-key.jsonl").write_text("".join(json.dumps(k) + "\n" for k in keys))
+    (PRIV / "keys" / f"trace-key{SUF}.jsonl").write_text("".join(json.dumps(k) + "\n" for k in keys))
     (PKG / "README.md").write_text(README)
     print(f"{len(keys)} items")
 
@@ -81,7 +83,7 @@
 
 
 def verify():
-    keys = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "keys" / "trace-key.jsonl").open()}
+    keys = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "keys" / f"trace-key{SUF}.jsonl").open()}
     items, problems = [], []
     for iid, k in keys.items():
         f = OUT / f"{iid}.json"
@@ -110,7 +112,7 @@
         a["skill_pairs"] += len(it["results"])
         a["traces"] += sum(x["trace"] for x in it["results"])
         a["unverified"] += sum(x["unverified"] for x in it["results"])
-    (PRIV / "trace-14.json").write_text(json.dumps({"by_condition": agg, "items": items}, indent=1, ensure_ascii=False))
+    (PRIV / f"trace-14{SUF}.json").write_text(json.dumps({"by_condition": agg, "items": items}, indent=1, ensure_ascii=False))
     print(json.dumps(agg, indent=1))
```

