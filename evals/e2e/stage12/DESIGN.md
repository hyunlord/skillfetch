# Stage 12 설계 — 모델이 알 수 없는 사내 규칙 (설계만, 실행 전)

작성 2026-10-26. **설계만 한다. 세션을 띄우지 않고 보고한 뒤 멈춘다**(사용자 계획 4단계). 아래 정의와 게이트는 결과를 보기 전에 고정하며, 바꿀 일이 생기면 날짜와 함께 이 문서에 따로 적는다. 보고는 숫자와 인용만 쓴다("라우터가 낫다/나쁘다" 같은 판정 문장은 쓰지 않음). 비용은 구독 사용량의 API 단가 환산으로 적는다.

## 0. 가설과 왜 지금까지 측정이 약했나

- **가설**: 스킬이 모델이 알 수 없는 지식(그 회사만의 규칙)을 담고 있으면, 라우터가 로드한 스킬이 결과를 크게 바꾼다.
- Stage 10·11의 작업은 공개 생태계 지식(FastAPI, Rust, 디자인)이라, 스킬이 없어도 모델이 대부분 알았다. 그래서 차이가 판정자 불일치(D) 안에 머문 묶음이 많았다.
- Stage 12는 정답이 **스킬에만** 있는 작업을 만든다. 정답은 숨은 체크가 규칙 하나씩 객관적으로 확인한다. 1–5 종합 점수는 보조다.

## 1. 가상 회사 Northwind

### 1.1 레포 2개 (새로 만든다, 작고 실행 가능)

| 레포 | 스택 | 내용 | 시작 커밋 |
|---|---|---|---|
| `nw-orders` | Python 3.12, FastAPI, SQLite, pytest, uv | 주문 서비스: 주문 생성·조회, 가격 계산 모듈, 마이그레이션 디렉터리, 설정 모듈 | `nw-a` |
| `nw-web` | TypeScript, Next.js(pages), vitest | 주문 내역 화면을 붙일 작은 웹 앱 | `nw-a` |

- **추론 불가 조건**(태스크 8개용 시작 커밋 `nw-a`): 레포 안에는 아래 사내 규칙의 **예시가 없다**. 기존 코드는 규칙과 무관한 중립 스타일이다(예: 오류는 FastAPI 기본 `{"detail": ...}`). README와 주석에도 규칙을 적지 않는다. 다만 규칙이 가리키는 파일(예: `api/routes.toml`, `errors/catalog.yaml`)은 **빈 껍데기나 무관한 항목 하나만** 두어, 규칙을 아는 세션이 실제로 지킬 수 있게 한다. 앱은 그 파일이 없어도 돌아간다(숨은 체크만 확인).
- **추론 가능 대조**(태스크 2개용 시작 커밋 `nw-b`): 같은 레포에 규칙을 지키는 기존 예시가 들어 있다(엔드포인트 2개, 화면 1개). 스킬 없이도 레포를 읽으면 규칙을 따라 할 수 있다.
- 준비 때 점검: 규칙 토큰(오류 코드 접두사 `NW-`, `nwlog.event`, `flags.is_on`, `V<날짜>_` 등)이 `nw-a` 트리, 출시 index, 공개 스킬 본문 어디에도 없는지 grep으로 확인한다.

### 1.2 사내 규칙 스킬 16개 (Northwind 플랫폼팀)

각 스킬은 일반 SKILL.md 형식(frontmatter name·description + 본문)이다. 본문에는 규칙, 좋은 예와 나쁜 예, 이유 한두 줄이 있다. 규칙 하나하나는 diff에서 객관적으로 확인할 수 있게 쓴다.

| # | 스킬 | 규칙(요지) | 숨은 체크가 보는 것 |
|---|---|---|---|
| 1 | `nw-error-responses` | API 오류 본문 `{"error": {"code": "NW-<AREA>-<NNN>", "message", "trace_id"}}`, 새 코드는 `errors/catalog.yaml`에 등록 | 오류 응답 JSON 형태, 코드 형식, 카탈로그 항목 |
| 2 | `nw-structured-logging` | 로그는 `nwlog.event("<domain>.<action>", tenant_id=…, trace_id=…)`만, `print`·`logging.*` 금지 | 새 코드의 로그 호출 AST |
| 3 | `nw-feature-flags` | 새 동작은 `flags.is_on("<team>.<flag>", tenant)` 뒤에, `flags/registry.toml`에 owner·expires 등록 | 호출과 레지스트리 항목 |
| 4 | `nw-migrations` | 파일 이름 `db/migrations/V<YYYYMMDD>_<NN>__<snake>.sql`, 파일 끝에 `-- rollback:` 구간 | 새 파일 이름 정규식, 구간 |
| 5 | `nw-endpoint-registry` | 새 HTTP 경로는 `api/routes.toml`에 method·path·owner·rate_limit 등록 | 레지스트리와 앱 라우트 일치 |
| 6 | `nw-deploy-checklist` | 설정·마이그레이션을 건드리면 `deploy/CHECKLIST.md`의 "Unreleased"에 한 줄 | 해당 변경 시 항목 존재 |
| 7 | `nw-config` | 설정은 접두사 `NW_ORDERS_` 환경 변수를 `settings.get()`으로 읽고 `config/ENV.md`에 문서화 | 이름, 읽는 방식, 문서 |
| 8 | `nw-money` | 금액은 정수 `amount_minor` + `currency`(ISO 4217), float 금지 | 스키마 필드와 타입 |
| 9 | `nw-public-ids` | 공개 id는 `nwids.new("<prefix>")`(접두사 + ULID), DB 정수 id 노출 금지 | 응답 id 형식, 호출 |
| 10 | `nw-timestamps` | 시각 필드는 `_at` 접미사, UTC RFC 3339 `Z` | 응답 필드 이름과 형식 |
| 11 | `nw-pagination` | 목록은 `?cursor=&limit=`(최대 100), 응답 `{"data": [...], "next_cursor": ...}` | 실제 호출 결과 |
| 12 | `nw-python-tests` | 테스트 파일 `test_<module>__<behavior>.py`, `nw_factory` 픽스처, API 테스트에 `@pytest.mark.contract` | 파일 이름, 픽스처, 마커 |
| 13 | `nw-web-i18n` | 화면 문자열은 `t("<page>.<key>")`, 키는 `locales/en.json`·`locales/ko.json` 둘 다 | 하드코딩 문자열, 키 양쪽 존재 |
| 14 | `nw-web-analytics` | 사용자 동작은 `track("<page>_<action>", {...})`, 이벤트 이름은 `analytics/events.ts`에 선언 | 호출과 선언 일치 |
| 15 | `nw-ui-tokens` | 색·간격은 `var(--nw-*)` 토큰만, 원시 hex·px 간격 금지 | 새 스타일의 값 |
| 16 | `nw-changelog` | 변경마다 `changes/<feat\|fix\|chore>-<slug>.md` 조각 하나 | 새 파일 존재와 이름 |

### 1.3 방해 스킬 8개 (다른 팀 규칙)

같은 회사의 다른 팀 규칙이다. 설명에 팀 이름을 쓰고(예: "Payments team"), 일부는 플랫폼팀 규칙과 **충돌**한다. 로드되면 결과를 틀리게 만들 수 있다.

| # | 스킬 | 요지 |
|---|---|---|
| D1 | `nw-payments-errors` | Payments 팀 오류 형식 `{"err_code", "detail"}` |
| D2 | `nw-data-logging` | Data 플랫폼 로그는 `logger.info(json.dumps(...))` |
| D3 | `nw-legacy-migrations` | 레거시 모놀리스 Alembic 이름 `YYYY_MM_DD_<desc>.py` |
| D4 | `nw-mobile-strings` | 모바일 앱 문자열 `strings.xml` |
| D5 | `nw-marketing-analytics` | 마케팅 사이트 `gtag('event', ...)` |
| D6 | `nw-payments-ids` | Payments id `pay_` + UUID4 |
| D7 | `nw-infra-runbooks` | 인프라팀 런북 작성 규칙 |
| D8 | `nw-ml-experiments` | ML 실험 이름·추적 규칙 |

### 1.4 index

- 출시 index(index-staging-4, Stage 11 통과)의 **복사본** `index-nw`에 `dir` 소스 `northwind`(위 24개, publisher "Northwind", trust "known")를 더한다. 원래 index와 서버 코드는 바꾸지 않는다. 본문은 `file://`로 가져온다(`dir` 소스는 서버가 지원함).
- **추출기 차이**: 출시 index의 추출 모델은 외부 API 모델이라 쓸 수 없다(외부 API 키 금지). Northwind 24개는 skillfetch의 Claude Code 백엔드(격리 `claude -p`, `ClaudeCliBackend`)로 추출한다. 나머지 기록은 그대로다. 이 차이는 보고서 한계에 적는다. 준비 때 ingest가 이 백엔드를 받는지 확인하고, 받지 않으면 같은 ingest 함수를 이 백엔드로 부르는 작은 빌드 스크립트를 쓴다.
- **충돌 판정(pairs)은 하지 않는다**(2026-10-27 사용자 결정). 이유: 판정은 resolve 경고만 줄이고 로드되는 스킬은 바꾸지 않는다. 출시 index에도 판정 없는 쌍이 있다. 그래서 `index-nw`는 Northwind 24개 추출까지만 하고, `pairs.jsonl`에 Northwind 판정 행을 더하지 않는다.
- **오프라인 검색 점검**(보고만, 고치지 않음): 태스크 10개의 R-c 쿼리(Stage 3 프롬프트, 격리 `claude -p` 1회)로 `index-nw`를 검색해, 태스크마다 필요한 Northwind 스킬이 top 10, top 50에 드는지 적는다. 스킬 설명은 점검 **전에** 고정하고 점검 결과로 고치지 않는다(검색기에 맞춘 튜닝 방지).

## 2. 태스크 10개

각 태스크 요청은 평범한 개발 요청이다. 규칙 이름이나 "사내 규칙"을 말하지 않는다. 태스크마다 **확인할 규칙 항목**을 미리 고정한다(아래 수).

| # | 레포·커밋 | 요청(요지) | 필요한 스킬 | 규칙 항목 |
|---|---|---|---|---:|
| T1 | nw-orders `nw-a` | 환불 엔드포인트 `POST /refunds` 추가(금액, 사유, 없는 주문 오류) | 1, 2, 5, 8, 9, 16 | 8 |
| T2 | nw-orders `nw-a` | 주문 목록 `GET /orders`(상태 필터, 페이지) | 5, 10, 11, 16 | 6 |
| T3 | nw-orders `nw-a` | 주문에 `refund_reason` 컬럼 추가 | 4, 6, 16 | 5 |
| T4 | nw-orders `nw-a` | 결제 대기 시간 제한 설정 추가 | 6, 7, 16 | 5 |
| T5 | nw-orders `nw-a` | 할인 계산 변경을 단계적으로 배포할 수 있게 | 2, 3, 16 | 5 |
| T6 | nw-orders `nw-a` | 가격 모듈 테스트 추가 | 12 | 3 |
| T7 | nw-web `nw-a` | 주문 내역 페이지 추가 | 13, 15, 16 | 5 |
| T8 | nw-web `nw-a` | 주문 취소 버튼과 확인 창 추가 | 13, 14, 15 | 5 |
| C1 | nw-orders `nw-b` | 고객 조회 `GET /customers/{id}` 추가(대조: 레포에 예시 있음) | 1, 5, 9, 10 | 6 |
| C2 | nw-web `nw-b` | 설정 페이지 추가(대조: 레포에 예시 있음) | 13, 15 | 4 |

- 규칙 항목은 태스크마다 3–8개, T1–T8 합 42개, C1·C2 합 10개다.
- **기능 체크**(규칙과 별개): 기존·새 테스트 통과, 빌드, 요청한 동작(엔드포인트 호출 결과, 화면 렌더). 보고만 하고 게이트에 넣지 않는다.

## 3. 조건과 반복

| 조건 | 내용 |
|---|---|
| **A** | 라우터 없음, MCP 없음(Stage 10·11의 A) |
| **R** | 출시 라우터 S-b′(레포에 중립 커밋) + skillfetch MCP(`index-nw`) |
| **O** | 천장: 그 태스크에 필요한 Northwind 스킬 본문을 **첫 사용자 메시지 앞에** `load_skills` 출력과 같은 형식으로 넣음(라우터·MCP 없음) |

- 환경 E1만(`--setting-sources project --strict-mcp-config`). 하네스는 Stage 11 `run_s11.py`를 그대로 쓴다(격리 clone, 사전 점검, 정리, 한도 감지).
- O에 넣는 본문은 R이 로드할 때 받는 본문과 같은 바이트다(`load_skills` 출력에서 가져옴).
- **O의 위치(2026-10-27 사용자 지시로 고정)**: 스킬 본문은 `--append-system-prompt`가 아니라 첫 사용자 메시지 앞에 `load_skills` 출력과 같은 형식으로 넣는다.
  - 이유: R에서 로드된 스킬은 시스템 프롬프트가 아니라 대화 안(도구 결과)에 들어온다. O도 대화 안에 두어야 위치와 형식이 R과 같고, 차이는 "고르는 단계가 있느냐"만 남는다.
  - 시스템 프롬프트에 넣으면 위치가 달라 천장 비교가 흐려진다.
- **반복**: 10 태스크 × 3 조건 × 3회 = **90세션**.

## 4. 지표

- **규칙 체크 통과율**(주 지표): 조건별로 (통과한 규칙 항목 수) / (전체 규칙 항목 수). 숨은 체크가 판정 불가인 항목은 분모에서 빼고 따로 센다.
  - 주 집계는 추론 불가 태스크 T1–T8(세션당 42개 중 해당 태스크 몫)이다. C1·C2는 따로 낸다.
- **방해 스킬 로드율**(기록): R 세션 중 방해 스킬을 하나라도 로드한 세션 비율. 함께 낸다:
  - 방해 로드 수 / Northwind 로드 수
  - 방해 스킬이 로드된 세션에서 그 방해 규칙을 따른 항목 수(충돌 규칙을 따라 틀린 경우)
- **관련 로드율**: R 세션 중 그 태스크에 필요한 Northwind 스킬을 하나 이상 로드한 비율과, 필요한 스킬 중 로드한 비율(태스크별).
- **보조**: 블라인드 1–5 종합 점수(Claude p1·p2, GPT는 사용자 선택), 턴, API 단가 환산, 입력 토큰, 기능 체크.

## 5. 게이트 (실행 전 고정)

추론 불가 태스크 T1–T8의 규칙 체크 통과율로 본다.

1. **R − A ≥ 30%p**
2. **R ≥ O − 15%p**

- 둘 다 맞으면 "가설에 맞는 결과"로 보고한다. 하나라도 어긋나면 어긋난 항목과 숫자를 그대로 보고한다.
- 방해 스킬 로드율은 게이트가 아니라 기록이다.
- **실행 전 유효성 점검**(파일럿, 게이트 아님): A 파일럿에서 T1–T8 규칙 통과율이 40%를 넘으면 규칙이 레포에서 추론 가능하다는 뜻이다. 그때는 본 실행 전에 멈추고 보고한다(레포를 고치려면 사용자 승인 뒤 다시 고정).
- O 파일럿에서 통과율이 60% 아래면 규칙이나 체크가 모호하다는 뜻이다. 그때도 멈추고 보고한다.

## 6. 숨은 체크

- 태스크마다 `check.py`가 규칙 항목마다 pass, fail, undecidable을 낸다. 정적 검사(AST, 정규식, 파일 존재)와 실행 검사(앱을 띄워 엔드포인트 호출, vitest, `next build`)를 쓴다.
- 준비 때 태스크마다 **참조 해답 두 개**를 만든다. 규칙을 다 지킨 해답은 모든 항목이 pass여야 하고, 규칙을 하나도 모르는 평범한 해답(같은 기능)은 모든 항목이 fail이어야 한다. 이 둘이 맞을 때만 체크를 고정한다.
- 체크와 참조 해답은 `stage12-private/`에 두고 해시로 고정한다.

## 7. 판정

- Stage 10·11과 같다. Claude 블라인드 p1·p2(새 하위 에이전트, 무작위 코드)와 GPT 패키지(사용자 선택)를 쓴다. 대상은 diff, 체크 결과, 가린 최종 답(Stage 10 §4.6 규칙)이다. 루브릭은 일반 코드 루브릭(`rubrics-s2.md` 일반 부분)에 "그 회사의 기존 관례를 따랐는가"를 넣지 **않는다**. 규칙 준수는 체크가 재고, 판정은 종합 품질만 본다.
- 1–5 점수는 보고만 한다(게이트 아님).

## 8. 세션과 비용 추정 (API 단가 환산)

세션당 추정은 Stage 10 E1 묶음 (2) 일반 코딩의 평균이다(m1–m3, 12세션씩). A는 $0.497, R1은 $0.682다. O는 A에 스킬 본문 3–6개(약 6–12k 토큰, 매 호출 캐시 읽기)가 더해져 약 $0.58로 잡는다.

| 항목 | 계산 | 추정 |
|---|---|---:|
| 본 실행 A | 30 × $0.50 | $15.0 |
| 본 실행 R | 30 × $0.68 | $20.4 |
| 본 실행 O | 30 × $0.58 | $17.4 |
| 파일럿 | 대표 태스크 2개(T1, T7) × 3조건 × 1 = 6세션 | $3.5 |
| index 추출 | 24–30회 × ~$0.08(레포 세션 추정; 충돌 판정은 하지 않음, §1.4) | $2.5 |
| 오프라인 검색 점검 쿼리 | 격리 `claude -p` 1회 | $0.1 |
| 다시 돌림 여유 10% | | $6.0 |
| **합계** | | **약 $66** |

- 판정(Claude 하위 에이전트)은 API 단가 환산에 넣지 않는다(Stage Q §8과 같음).
- **상한 제안: $75.** 큐는 "쓴 것 + 남은 세션 × 추정 > 상한"이면 띄우기 전에 멈추고 보고한다. 어느 세션도 건너뛰지 않는다.
- **세션 수**: 본 실행 90 + 파일럿 6 = 96.
- **시간**: 세션 평균 약 90초, 4병렬로 본 실행 약 40분이다. 체크(앱 기동, `next build`)를 더하면 약 1.5시간이다.
- **준비 작업량**(모델 세션 없음): 레포 2개 × 시작 커밋 2개, 스킬 24개, 체크 10개, 참조 해답 20개, index 복사·빌드, 하네스 조건 O 추가, dry run.

## 9. 순서 (실행할 때)

1. 레포·스킬·체크·참조 해답 → 체크 고정(§6)
2. `index-nw` 빌드 → 오프라인 검색 점검(보고만)
3. 이 문서와 파일 해시 고정
4. 파일럿 6세션 → 유효성 점검(§5) → 본 실행 90세션(작업·조건 순서는 반복마다 섞음)
5. 블라인드 판정 → 키 공개 → 게이트 → `report-12.md`

## 9.1 공개와 index 사본 제약 (2026-10-27 사용자 지시)

- `index-nw`는 **실험용 사본으로만** 쓴다. release, `skillfetch sync`, `sources.yaml` 어디에도 들어가지 않는다. 레포 세션에 빌드를 맡길 때 이 제약을 함께 전달한다.
- Northwind 스킬 본문, 레포(`repos/nw-orders`, `repos/nw-web`), 태스크·규칙 항목은 **실험이 끝날 때까지 공개하지 않는다.** 그래서 `stage12-private/`에 둔다(공개 폴더 `stage12/`에는 이 문서와 하네스만 둔다).
- **2026-10-27 실험 종료, 공개 결정(사용자)**: Northwind 스킬·레포·태스크는 가상이므로 공개한다. 실제 사용자 경로·환경 이름은 지운다. 공개 형태는 §11의 같은 날 기록에 있다. `index-nw`가 release·sync·`sources.yaml`에 들어가지 않는다는 제약은 그대로다.

## 10. 한계 (미리 적어 둠)

- 가상 회사이고 규칙은 우리가 만든 것이라, 실제 사내 스킬의 길이·모호함과 다를 수 있다.
- Northwind 기록만 다른 추출기(Claude Code 백엔드)로 추출한다.
- 태스크 10개, 3회 반복이다.
- O는 필요한 스킬을 정확히 아는 천장이다. 실제로는 그런 선택을 해 줄 사람이 없다.

## 11. 기록

- 2026-10-27 체크·레포 수정(실행 전, 모델 호출 없음):
  - `nw-a`의 힌트 줄을 지웠다. 셸 파일의 "Add new ... below" 줄, CHECKLIST 예시 항목, 헬퍼 docstring, pytest `contract` 마커 등록, web의 `APP_LOADED`·`app.name` 예시가 대상이다. 세션이 `git log -p`로 지운 줄을 볼 수 없게 `nw-a`를 루트 커밋 하나로 다시 만들었다. 새 head는 nw-orders `nw-a` b3e1eec / `nw-b` 34adcb3, nw-web `nw-a` ef31a68 / `nw-b` 82e6242다.
  - T2-R2를 "`_at` 접미사"에서 "`limit` 최대 100(limit=101에 4xx 또는 정확히 100개)"으로 바꿨다. 기존 `orders` 표에 `created_at`이 있어 평범한 해답도 통과했기 때문이다. 항목 수는 6개 그대로이고, 스킬 10은 T2-R3이 계속 덮는다.
  - 다른 체크도 고쳤다. 판정 불가(None)가 실패로 바뀌었고, 실행 응답 검사가 늘었으며, JSX 하드코딩 문자열과 lib import를 요구한다. 기능 항목은 Northwind 형식과 무관하게 다시 썼다.
  - 참조 해답 20개 검증: `all`은 규칙 항목이 모두 통과, `none`은 모두 실패했고, 기능 항목은 둘 다 통과했다. 판정 불가는 0이다. `nw-a` 감사 PASS, `stage12-private/FROZEN.sha256` 57개.
  - 스킬 24개와 `tasks.jsonl`을 `stage12-private/`로 옮겼다(§9.1).
- 2026-10-27 `index-nw` 빌드 방식:
  - 레포 세션이 `<repo-session-work>/stage12-nw/`에서 빌드하고, 이 세션이 `stage12-private/index-nw`로 복사해 sha256으로 대조한다. 레포 세션은 e2e 안에서 프로세스를 띄우지 않는다는 사용자 규칙을 따른다.
  - 추출은 `ClaudeCliBackend`(격리 `claude -p`)로 하고, ingest 함수를 스크립트에서 직접 부른다.
  - Northwind와 기존 기록 사이 중복 묶기는 하지 않는다. 기존 2,785줄은 staging-4와 바이트 단위로 같다.
  - 충돌 판정은 하지 않는다(§1.4).
- 2026-10-27 `index-nw` 받음(레포 세션 빌드, 추출만):
  - 기록 2,809개 = 기존 2,785 + Northwind 24다. 제약은 40,103줄이고, Northwind가 64줄이다.
  - 기존 기록·제약 줄은 staging-4와 순서까지 같다(이 세션에서 다시 확인). `pairs.jsonl`, `rejected.jsonl`, `dupgroups.json`은 파일째 같다.
  - `claude -p` 24회, API 단가 환산 $1.05다. 빌드 스크립트는 `<repo-session-work>/stage12-nw/build_nw.py`다.
  - 판정 안 한 Northwind 후보 쌍은 89개다(needs_review 88, tension 1). 실행 중 resolve 경고로만 나온다.
  - sha256: skills.jsonl `bce0855d…4416`, constraints.jsonl `e0416fed…a402`, manifest.json `d7156093…cdb5`이고, 나머지 셋은 staging-4와 같다.
- 2026-10-27 오프라인 검색 점검(§1.4, 보고만): R-c 쿼리는 격리 `claude -p` 1회(API 단가 환산 $0.05)로 만들었다. 서버 c55d561 `search_skills(queries=4개, k=50)`, 파일은 `stage12-private/search-check/`다.
  - 필요한 Northwind 스킬 32개(태스크별 합) 중 top 10에 16, top 50에 24다.
  - 태스크별 top 10 / top 50: T1 5/6·6/6, T2 2/4·3/4, T3 2/3·2/3, T4 2/3·2/3, T5 1/3·1/3, T6 0/1·1/1, T7 1/3·1/3, T8 0/3·2/3, C1 2/4·4/4, C2 1/2·2/2
  - top 50 밖: `nw-changelog` 5개 태스크 전부, `nw-ui-tokens` 3개 중 2(T7·T8), `nw-structured-logging`(T5)
  - 방해 스킬이 top 10에 든 경우: `nw-legacy-migrations` T1·T3 2위, `nw-payments-errors` C1 2위
  - 스킬 설명은 고치지 않았다.
- 2026-10-27 참고 숫자(실행 전): 출시 라우터는 "pick up to 3"이라 R은 한 태스크에 스킬을 3개까지 로드한다. 필요한 스킬은 T1 6개, T2·C1 4개다. 가장 잘 고른 3개로 덮을 수 있는 규칙 항목은 52개 중 47개(0.904)이고, T만 보면 42개 중 38개(0.905)다. O는 52개 모두에 해당하는 스킬을 받는다. 설계와 게이트는 바꾸지 않았다.
- 2026-10-27 실행 준비(모델 세션 없음):
  - O 프롬프트 `stage12-private/o-prompts/<task>.md`는 index-nw에서 `resolve_and_load(필요한 Northwind id)`를 부른 결과의 `content`다(서버 c55d561, max_tokens를 올려 빠진 스킬 없음). 10개 태스크 모두 제외·경고·오류가 0이다. 토큰 추정은 T6 281부터 T1 1,371까지다(§8의 6–12k 가정보다 작음). 본문 캐시는 그 폴더 안 임시 폴더를 쓰고 지웠다.
  - R 브랜치: nw-orders `s12-r-nw-a` c718405 / `s12-r-nw-b` deadcfc, nw-web `s12-r-nw-a` 74407d1 / `s12-r-nw-b` 30bed8e다. 시작 커밋 위 커밋 하나("chore: add project skill")이고, 바뀐 파일은 라우터 S-b′ 하나다.
  - `stage12/mcp/mcp-r.json` = 서버 c55d561 `serve --index stage12-private/index-nw`.
  - R 세션의 서버는 Northwind 본문을 `~/.skillfetch/cache/<content_hash>`에 캐시한다(로컬, 비공개). 실험이 끝나면 Northwind 24개의 digest 폴더를 지운다.
  - 큐 `stage12/scripts/run_queue_12.py`(#26 큐 복사, 상한 $75, 4병렬)와 job 목록 `stage12-private/jobs-{pilot,main}.txt`(본 실행은 반복마다 seed "s12"로 섞음)를 만들었다. 이미 쓴 것은 $1.10이다(index 추출 $1.05 + 검색 점검 쿼리 $0.05).
  - dry run 8개(T1·T7 × A/R/O, C1 R, C2 O): clone·라우터 유무·MCP 설정·O 접두가 모두 맞다.
  - `stage12-private/FROZEN.sha256` 87개: 기존 57개에 index-nw 6, O 프롬프트 12, 검색 점검 4, job 목록 2, 하네스·큐·MCP 4, `run_s11.py`, 라우터 사본을 더했다. 이 문서는 기록이 계속 붙으므로 넣지 않았다.
- 2026-10-27 파일럿 6세션(T1·T7 × A/R/O, API 단가 환산 $2.21):
  - **하네스 결함**: 체크는 `git diff <base> HEAD`를 읽는데, 세션은 작업을 커밋하지 않는다. 그래서 첫 체크에서는 코드 항목이 모두 "추가 줄 없음"으로 떨어지고 런타임 항목만 통과했다(A 1/13, R 4/13, O 4/13). 예를 들어 O T7은 `t()`·`--nw-*` 토큰·`changes/` 조각을 다 썼는데 0/5였다.
  - **수정**: `run_12.run_check`가 체크 전에 작업 트리를 그대로 커밋한다(`snapshot_commit`, 수집한 diff와 같은 제외 목록). 체크 파일은 바꾸지 않았다.
  - 파일럿 6개는 `stage12/scripts/recheck_12.py`로 다시 쟀다. 참조 검증과 같은 방식(새 clone + 세션 diff 적용 + 커밋 + 체크)이다. 첫 결과는 meta `check_uncommitted`에 남겼다.
  - 다시 잰 결과(규칙 항목): A T1 1/8, T7 1/5 = 2/13(0.154). R T1 5/8, T7 2/5 = 7/13(0.538). O T1 7/8, T7 3/5 = 10/13(0.769). 기능 항목은 모두 통과했고 판정 불가는 0이다.
  - 유효성 점검(§5): A ≤ 0.40, O ≥ 0.60 둘 다 만족한다.
  - **확인할 점**: O T7은 `const tr = (key) => t(key, locale)`로 감싸 `tr('orders.heading')`처럼 불렀다. 키는 en·ko 모두에 있다. 체크(`_lib.py`)는 `t('…')` 글자 그대로만 찾기 때문에 T7-R1·R2가 실패로 나왔다.
- 2026-10-27 체크 수정 2건(사용자 결정, 본 실행 전). **본 실행 시작 후에는 체크를 바꾸지 않는다.**
  - **(1) `t()` 인정 범위**(`_lib.t_call_names`):
    - (a) i18n 모듈에서 import한 `t`, 또는 import alias `import { t as X }`
    - (b) 같은 파일에 정의된 래퍼 함수. 몸체가 (a)의 이름을 부르면서 래퍼의 첫 매개변수를 첫 인자로 그대로 넘겨야 한다. 예: `const tr = (key) => t(key, locale)`, `function tr(key) { return t(key) }`
    - 호출부는 문자열 리터럴 key여야 한다. import하지 않은 지역 함수 `t`는 인정하지 않는다.
    - T7·T8·C2의 `t()` 사용 항목과 locale 키 항목에 같이 적용된다.
  - **(2) 여러 줄 호출**(`_lib._check_added_lines`): 줄 단위로 못 찾으면, 파일의 추가 줄을 이어 붙인 텍스트에서도 찾는다. O T1의 `nwlog_event(` 다음 줄에 이벤트 이름이 오는 경우다. flag·settings 호출 항목에도 같이 적용된다.
  - **검증**(`stage12-private/refs/validate_12.py`, 결과 `refs/validation-2.json`): 28/28이 기대대로다.
    - 참조 해답 20개
    - 픽스처 8개(`refs/fixtures/*.patch`): 양성 3(화살표 래퍼, function 래퍼, alias)은 R1·R2 통과다. 음성은 ① key를 무시하고 리터럴을 돌려주는 래퍼, ② import하지 않은 지역 `t`, ③ `t`를 import했지만 문자열을 직접 렌더링이고, 셋 다 R1 실패다(③은 R2 통과). 여러 줄 로그는 양성 통과, 이벤트 이름이 틀린 음성은 실패다.
  - **파일럿 재채점**(규칙 항목; 커밋 전 → 커밋 수정 → 체크 수정):

    | 조건 | T1 | T7 | 합계 | 비율 |
    |---|---|---|---|---|
    | A | 1/8 → 1/8 → 1/8 | 0/5 → 1/5 → 1/5 | 1 → 2 → 2 / 13 | 0.077 → 0.154 → 0.154 |
    | R | 4/8 → 5/8 → 5/8 | 0/5 → 2/5 → 2/5 | 4 → 7 → 7 / 13 | 0.308 → 0.538 → 0.538 |
    | O | 4/8 → 7/8 → 8/8 | 0/5 → 3/5 → 5/5 | 4 → 10 → 13 / 13 | 0.308 → 0.769 → 1.000 |

    - meta에 `check_uncommitted`, `check_before_t-wrapper-multiline`, `check`가 모두 남아 있다.
    - 유효성(§5): A 0.154 ≤ 0.40, O 1.000 ≥ 0.60이다.
    - R에 남은 실패는 이렇다. T1: 이벤트 이름 `"refund_created"`(형식 아님), public id 없음(id=1), `changes/` 조각 없음. T7: 새 nav 링크의 raw `#0066cc`·`16px`, `changes/` 조각 없음.
  - **체크 코드 해시(동결)**:
    - `_lib.py` 90836c79bb9fb07ea3e137d7a8bc4fef51f92c602a655f4b4b0482b9d898715f
    - T1 check.py fde456f898dce53b32fe43d715ae54645c6d907ece08a69ba31c34b042a72195
    - T2 check.py 884ee035febbed46e30510b227fcaf2c0f11d87118611774b5e7418790b3651c
    - T3 check.py f80e05dd1dce1d9b560828aedff6915ba45fa8148df885c2722317199ec691e2
    - T4 check.py 8118fd1f30d8c87dffb4fcffabb25b189a9fbeaba385d89055c040988faa483b
    - T5 check.py 7a661a5071928ac26a067a0ca409d30f543906e88d5ecd932fc2bdb763ea891b
    - T6 check.py 52366f2a3dd13d2b29cb30c4e6961065c1285da3e9b105d219cfca7c7ed97151
    - T7 check.py 61ba206019db05f26931a825e5273012ef9a92306f1115c8a367e35a96df76a7
    - T8 check.py 347f1252152015ff222edb6e703a73fd637b962068848d8baf929604c1862152
    - C1 check.py c04d2f96c3706fa811f07a93b5213b37f6eb917394ad3d2aa9a9f809719a8cf4
    - C2 check.py be4ad09952f761e40a7736180825493c70a2ed696891fa4deaddccebfa0124f3
    - check.py 10개 + `_lib.py`를 이어 붙인 해시는 e4efa9ad9e4aff57531b7f5f92bd36e601e0ee54bf6f250b744ea572b14eccf5
    - `run_12.py`(스냅샷 커밋) bf96f0315c36d612030c9505e2c558facba6eb94efbd0087cb4d83aca26e1840
  - `FROZEN.sha256`은 99개다(재검사·지표·검증 스크립트, 픽스처 8개, `validation-2.json` 추가). 모두 OK다.
- 2026-10-27 본 실행 중단·재개:
  - 66번째 job까지 62개가 끝났다. m3의 4개(C1 R, C2 A, T2 A, T1 R)는 "You've hit your org's monthly spend limit"로 harness_fail이 되었고, 큐가 멈췄다.
  - 사용자가 다시 로그인한 뒤 같은 job 목록으로 재개했다. 끝난 job은 건너뛴다.
  - 실패한 4개의 파일은 `stage12-private/runs-hf/`로 옮겼다. 사용량 $0.77은 `spend-other.json`에 넣어 합계에 남겼다.
  - 체크·하네스·job 목록은 바꾸지 않았다.
  - 사용자 추가 요청(본 실행 시작 후): R 선택 분석 `stage12/scripts/selection_12.py`. 실행이 끝난 세션만 읽는다.
    - 세션마다 정답 세트 대비 로드 비율을 센다.
    - 정답 스킬을 "top 50에 있었는데 안 고름 / top 50에 없음 / 검색 없음"으로 나눈다.
    - 실패한 규칙 항목을 "안 고름 / 못 찾음 / 골랐는데 안 지킴"으로 분류한다.
- 2026-10-27 실험 단계 종료(사용자). Stage 13으로 마무리하고 stage26b와 12c는 하지 않는다. 원문:
  > 실험 단계는 Stage 13으로 마무리한다. stage26b와 12c는 하지 않는다. Stage 12, 12b, 13을 Stage 10/11과 같은 절차로 공개할 수 있게 정리한다 (Northwind 스킬·레포·태스크는 가상이고 실험이 끝났으니 공개해도 된다. 실제 사용자 경로·환경 이름은 지운다).
  - 공개 정리(이 세션, Stage 10/11과 같은 절차: 대화 기록 대신 derived 행, 비공개 폴더는 `private/`로, 경로·환경 이름 치환):
    - 레포 `nw-orders`, `nw-web`: 시작 커밋 `nw-a`, `nw-b`의 파일 트리를 그대로 풀어 `stage12-private/northwind-repos/<레포>/<브랜치>/`에 두었다. 조건 브랜치 6개(`s12-r-*`, `s12b-rp-*`, `s12b-n-*`)는 시작 커밋 대비 diff(`branches/*.patch`)로 두었다. 커밋 해시·트리 해시·제목은 `branches.json`에 있다. 시작 커밋 두 개의 작성자 정보에 실제 사용자 이름과 메일이 있어 git 번들은 만들지 않았다.
    - `index-nw`: 전체 사본(31 MB, 나머지 2,785행은 index-staging-4와 순서까지 같음)은 공개하지 않는다. Northwind 24행과 제약 64행, 파일 해시는 `stage12-private/index-nw-published/`에 따로 두었다.
    - 공개하지 않는 것: 대화 기록(derived 행만), 가린 최종 답변, 판정 패키지의 결과물(diff는 release asset), 12c 후보였던 공개 스킬 본문(`stage12c/public-bodies/`), 로그.
    - 작업 폴더의 `<E2 plugin>/`, `__pycache__/`를 지웠다(해시 대상 아님).
