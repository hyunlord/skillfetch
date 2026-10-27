# Stage 14 rubrics (fixed before the main run, 2026-10-27; DESIGN §2, §4)

Sets 1, 2, 4, 6 use the existing rubrics unchanged:

| set | rubric |
|---|---|
| s14-landing | `rubric-design.md` (the d1-landing rubric; route `/landing` of the `web/` app) |
| s14-api | `rubrics-s2.md`, section s2-api (the app lives in `api/`; contract-script results are in `check.txt`) |
| s14-rust | `rubric-b4-add.md`, row s11-t266 (the crate lives in `media/`) |
| s14-data | `rubrics-s2.md`, section s2-data (the script lives in `data/scripts/`, the CSV in `data/data/`) |

Sets 3 and 5 are new tasks. Same 1–5 anchors, 총점, rank lines and output format as `rubrics-s2.md`
(general part and output format apply unchanged):

## s14-apitests — more tests for the bookmarks API in `api/`

Request: "`api/`의 북마크 API에 테스트를 보강해줘 — 엔드포인트별 정상·오류 경로와 엣지케이스까지 다뤄줘." The API was written
earlier in the same conversation (the contract: POST/GET list with `?tag`, `?limit`, `?offset`/GET one/PATCH/DELETE,
url http/https only, duplicate url blocked, 201/204/404/409/422). Context: the diff of this request only, and the check
output (the suite passes or not; collected tests before/after; how many of 8 contract-level mutants the suite catches —
404→200, 409→201, 422 accepted, POST 201→200, DELETE 204→200, `limit` / `tag` / `offset` ignored).

| criterion | what earns a 5 |
|---|---|
| 동작 범위 1-5 | every endpoint's success and error paths: create, list with tag filter and pagination, get, partial update, delete; 404 on every id route; 409 on create and on update to an existing url; 422 for bad url scheme, missing title, wrong types |
| 엣지케이스 1-5 | boundaries the contract implies: limit/offset at 0 and past the end, tag that matches nothing, url with/without trailing differences, empty tags, PATCH with no fields / unknown fields, persisted data across a new app instance where the API supports it |
| 단언 품질 1-5 | exact status codes and bodies (fields, values, order where defined), not only "status < 400"; a wrong implementation (see the mutants) would fail them |
| 구조·가독성 1-5 | isolated database per test, fixtures and parametrisation where cases repeat, names that state the behaviour, fits the existing tests |
| 정확성 1-5 | the suite passes against the API; tests do not assert behaviour the contract does not have; the API code is not changed to make tests pass unless the request's tests found a real contract bug (then say so in 근거) |

## s14-docs — root README and usage docs for the monorepo

Request: "이 레포 루트에는 README가 없어. README와 사용 문서를 써줘." The repository has four independent areas: `web/`
(Next.js pages app), `api/` (FastAPI bookmarks service; may not exist yet, depending on the conversation), `media/`
(axum CMS crate with image resize), `data/` (Python data folder with `data/orders.csv`). Context: the diff of this request,
the repository's tree after it (the judge checks claims against the files), and the check output (root README present,
the four areas named, npm scripts named in the docs exist in `web/package.json`, repository paths in backticks exist).

| criterion | what earns a 5 |
|---|---|
| 정확성 1-5 | every command, script, path, env var and behaviour described matches the files; nothing invented (an invented feature or wrong command caps this at 2) |
| 완전성 1-5 | what the repository is; for each area: what it is, requirements, install, run, test; where to look first |
| 명확성 1-5 | a newcomer can go from clone to running any one area without reading the code; scannable structure |
| 간결성 1-5 | no padding, marketing language or generic boilerplate; length fits four small projects |
| 문서 구성 1-5 | root README vs per-area / extra usage docs split sensibly, linked, no duplication |
