# Stage Q 요청 원문 (실행 전 고정, 2026-10-26)

DESIGN §2(Q2), §5(Q5)의 요청 문구. `sq-mono` 레포는 이 문구의 경로·이름에 맞춰 만든다. 세션에는 아래 문구를 **그대로**
보낸다. `{CANARY_PATH}`만 실행 때 canary 스킬 디렉터리의 절대 경로(무작위 이름, 레포 밖)로 바꾼다.

## Q2 — 한 세션에 연달아 보내는 작업 4개 (S, C, S-B 공통)

1. **디자인**
   > Add a testimonials section to the landing page in `web/` (`web/index.html`, `web/styles.css`), between the features and the pricing sections. Three short customer quotes with name and role; match the existing visual style. For this task, use my local skill at `{CANARY_PATH}`.
2. **Rust**
   > In `rust/`, add a new module `src/duration.rs` with `pub fn parse_duration(s: &str) -> Result<std::time::Duration, ParseDurationError>` that accepts strings like `1h30m`, `45s`, `2h` and `90m`, export it from `lib.rs`, and add unit tests for valid and invalid inputs.
3. **사소한 수정**
   > Fix the typo "recieve" in the top-level README.md.
4. **무관한 Python**
   > Add a script `py/tools/export_csv.py` that reads the inventory JSON file (same format as `py/inventory/data/items.json`) and writes a CSV with the columns sku, name, quantity, unit_price. Take the input and output paths as command-line arguments, and add a test under `py/tests/`.

- C(대조)는 같은 문구를 작업마다 새 세션에 보낸다(같은 작업 트리).
- S·S-B는 1번을 `claude -p`로, 2–4번을 같은 세션 `claude -p --resume <session_id>`로 보낸다.

## Q5 — 사소한 작업 5개 (기존 레포, 켬만)

| # | 레포(시작 커밋) | 요청 |
|---|---|---|
| T1 | s10-t016 (`s10-a`) | Change the default chat address in `src/main.rs` from `127.0.0.1:7000` to `127.0.0.1:7100`. |
| T2 | s2-api (`s6b-a`) | Bump the version in `pyproject.toml` from 0.1.0 to 0.1.1. |
| T3 | s11-t160 (`s11-a`) | Change the default listen address of tracker-ingest from `:8081` to `:8082`. |
| T4 | nextjs (`s6b-a`) | Change the page title on the home page from "Home \| Next.js + TypeScript Example" to "Home \| Example App". |
| T5 | s10-t001 (`s10-a`) | Rename the constant `REASON_UNKNOWN` to `REASON_UNKNOWN_PAYOUT` in `scripts/reconcile_payouts.py`. |

- 각 요청의 대상이 시작 커밋에 실제로 있는지 점검했다(2026-10-26).
  - 처음 문구 가운데 T1(README 오타 "recieve"), T2(`app/main.py`의 쓰지 않는 import), T5(`reconcile_payouts.py`의 버전 문자열 1.2.0)는 대상이 없었다.
  - 레포 15개의 시작 커밋을 다시 찾아봤지만 실제 오타는 없었고, 쓰지 않는 import는 `__init__.py`의 의도적 재노출뿐이었다.
  - 그래서 레포는 바꾸지 않고, 그 레포에 실제로 있는 사소한 대상으로 문구를 바꿨다.
    - T1: 기본 주소 상수(`src/main.rs:6`의 `127.0.0.1:7000`)
    - T2: `pyproject.toml`의 버전 0.1.0
    - T5: 상수 이름 `REASON_UNKNOWN`(`reconcile_payouts.py:32`)
  - T3(`cmd/tracker-ingest/main.go:17`의 `:8081`), T4(`pages/index.tsx:5`의 제목)는 처음 문구 그대로다.
- 이름 지정 작업 3개는 아래(Q index 확정 뒤 고정).

### 이름 지정 작업 3개 (2026-10-26 고정, Q index = staging-4)

요청 = Q1과 같은 태스크 원문 + 빈 줄 + 지정 문장 하나(아래 블록이 세션에 보내는 문자열 그대로).
기준: 이름 부분(`<source>/<name>@<hash>`의 `<name>`)이 지정한 이름과 같은 id가 `pinned_ids`에 들어갔는지(같은 이름의 어느 판본이든 인정, 어느 것인지 기록), 로드됐는지. auto로만 들어가면 "pinned 아님".

**N-s10-t016** — `rust-testing` (staging-4 id 5개: `affaan-m-ecc/rust-testing@054179efdbc5`, `affaan-m-ecc/rust-testing@2787e8fd4247`, `affaan-m-ecc/rust-testing@68e797f602f9`, `affaan-m-ecc/rust-testing@c604055ce387`, `affaan-m-ecc/rust-testing@dea9424b442e`)

```text
tokio 기반 채팅 서버(src/room.rs)에 방 입장 시 최근 메시지 50개를 다시 보내주는 history replay 기능 추가해줘. 메모리는 방마다 VecDeque로 링버퍼처럼 관리하면 될 것 같아.

Use the rust-testing skill for the tests.
```

**N-d1-landing** — `frontend-design` (staging-4 id 2개: `anthropics-skills/frontend-design@0a5ff23f1022`, `uasl/frontend-design@5da82907743d`)

```text
이 앱의 제품 랜딩 페이지를 신규 라우트 /landing에 처음부터 만들어줘 — 히어로, 기능 3개, 가격, CTA 포함

Use the frontend-design skill for this.
```

**N-s2-api** — `fastapi-patterns` (staging-4 id 2개: `affaan-m-ecc/fastapi-patterns@419da9966f07`, `affaan-m-ecc/fastapi-patterns@5bd0ca7d3e93`)

```text
북마크를 저장하는 REST API를 FastAPI로 설계하고 구현해줘. 스키마, 에러 처리, 테스트까지 포함해서.
- 앱은 `app/main.py`의 `app`
- 저장은 SQLite, 파일 경로는 환경변수 `BOOKMARKS_DB` (없으면 `bookmarks.db`)
- 북마크: url(필수, http/https만), title(필수), tags(문자열 목록), created_at
- 엔드포인트: `POST /bookmarks`, `GET /bookmarks` (태그 필터 `?tag=`, 페이지네이션 `?limit=&offset=`), `GET /bookmarks/{id}`, `PATCH /bookmarks/{id}`, `DELETE /bookmarks/{id}`
- 같은 url은 두 번 저장할 수 없음
- 상태 코드는 REST 관례대로 (생성 201, 삭제 204, 없음 404, 중복 409, 검증 실패 422)

Use the fastapi-patterns skill for this.
```
