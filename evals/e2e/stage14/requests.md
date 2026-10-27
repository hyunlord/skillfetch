# Stage 14 요청 원문 (실행 전 고정, DESIGN §2)

출처 태스크의 원문에서 경로만 바꿨다. 줄마다 `> ` 뒤가 그대로 보내는 문장이다(여러 줄 요청은 `>` 줄을 이어 붙인다).

## 1 landing (web)
> `web/` 앱의 제품 랜딩 페이지를 신규 라우트 /landing에 처음부터 만들어줘 — 히어로, 기능 3개, 가격, CTA 포함

## 2 api (api)
> `api/` 디렉터리에 북마크를 저장하는 REST API를 FastAPI로 설계하고 구현해줘. 스키마, 에러 처리, 테스트까지 포함해서.
> - 앱은 `api/app/main.py`의 `app`
> - 저장은 SQLite, 파일 경로는 환경변수 `BOOKMARKS_DB` (없으면 `bookmarks.db`)
> - 북마크: url(필수, http/https만), title(필수), tags(문자열 목록), created_at
> - 엔드포인트: `POST /bookmarks`, `GET /bookmarks` (태그 필터 `?tag=`, 페이지네이션 `?limit=&offset=`), `GET /bookmarks/{id}`, `PATCH /bookmarks/{id}`, `DELETE /bookmarks/{id}`
> - 같은 url은 두 번 저장할 수 없음
> - 상태 코드는 REST 관례대로 (생성 201, 삭제 204, 없음 404, 중복 409, 검증 실패 422)

## 3 apitests (api)
> `api/`의 북마크 API에 테스트를 보강해줘 — 엔드포인트별 정상·오류 경로와 엣지케이스까지 다뤄줘.

## 4 rust (media)
> `media/src/routes/media.rs`에서 `image` crate로 하는 리사이즈를 axum async 핸들러 안에서 그냥 돌리고 있어서, 동시 요청이 20개만 넘어가도 다른 CMS API까지 전부 느려져요. `spawn_blocking`으로 빼고 `Semaphore`로 동시 처리 수 제한도 걸어주세요.

## 5 docs (root)
> 이 레포 루트에는 README가 없어. README와 사용 문서를 써줘.

## 6 data (data)
> `data/data/orders.csv`가 지저분해 (결측값, 형식 불일치 등). 이걸 정리해서 깨끗한 CSV를 만들고 요약 리포트를 내는 Python 스크립트를 써줘. 스크립트는 `data/scripts/clean_orders.py`이고, `data/`에서 `uv run python scripts/clean_orders.py`로 실행하면 결과를 `data/out/`에 쓰게 해줘.

## 순서
- F: 1 2 3 4 5 6
- B: 6 5 4 2 3 1
