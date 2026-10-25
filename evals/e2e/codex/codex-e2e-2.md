Codex CLI 0.164.0 | 모델: gpt-6-astra (reasoning: medium) | 인증: ChatGPT Pro 구독 로그인 (`chatgpt`), API 키 환경변수 미상속

# Codex E2E 재실행: skillfetch 전용 자동 승인

같은 19개 태스크를 각각 한 번 실행했다. **발화율은 19/19 (100.0%)**다. 발화는 모델이 skillfetch 도구 호출을 요청한 세션을 뜻한다. 실제 MCP 프로토콜 성공 응답을 받은 세션은 **19/19**, 반환된 스킬 ID가 확인된 세션은 **19/19**다. 승인 차단은 **0건**이었다.

이번 변경은 skillfetch 서버의 MCP 도구 승인 설정 한 줄이다. 전역 `approval_policy = "never"`, `workspace-write`, 셸 네트워크 차단 등 나머지 설정과 라우터 AGENTS.md는 이전 실행과 같다. 코딩 결과물은 평가하지 않았다.

| 지표 | 결과 |
|---|---:|
| 실제 태스크 제출 | 19개, 각 1회 |
| skillfetch 호출 요청 세션 | 19/19 (100.0%) |
| MCP 성공 응답 세션 | 19/19 (100.0%) |
| search_skills 호출 세션 / 호출 수 | 19/19 / 19회 |
| 네 번째 질의가 원문과 일치한 검색 호출¹ | 19/19 |
| load_skills 호출 세션 / 호출 수 | 19/19 / 19회 |
| 실제 반환 ID가 확인된 세션 | 19/19 |
| 반환 ID 건수 / 고유 ID | 20 / 18 |
| load 반환 관찰 충돌 | 0회 |
| 정상적인 모델 최종 응답으로 종료 | 19/19 |
| worktree 정리 완료 | 19/19 |

도구별 호출 수: `profile_repo` 19회, `search_skills` 19회, `resolve_set` 19회, `load_skills` 19회. 전체 호출 76회 중 서버 결과 76회, 프로토콜 성공 76회다. 정상 프로토콜 응답 안의 도메인 오류는 별도로 아래 기록한다.

¹ 모든 lifecycle 인자 관찰에서 `queries.length === 4`, 모든 값이 문자열, `queries[3] === tasks.jsonl의 prompt`를 검사했다. 공백·줄바꿈·Unicode를 정규화하지 않았다. 미호출은 일치로 세지 않는다.

## 정확한 설정과 사전 검증

각 세션의 격리된 `$CODEX_HOME/config.toml`에 다음 설정을 사용했다. 이전 입력에서 추가한 것은 `[mcp_servers.skillfetch]`의 `default_tools_approval_mode = "approve"` 한 줄뿐이며, 그 줄을 제거하면 이전 config와 바이트 단위로 일치한다. 이 설정은 등록된 skillfetch의 네 도구에만 적용된다. [공식 MCP 설정 문서](https://learn.chatgpt.com/docs/extend/mcp)의 서버별 승인 옵션을 설치된 CLI에서 확인했다.

```toml
model = "gpt-6-astra"
model_reasoning_effort = "medium"
forced_login_method = "chatgpt"
approval_policy = "never"
sandbox_mode = "workspace-write"
web_search = "disabled"

[features]
apps = false
plugins = false
remote_plugin = false
hooks = false
memories = false
multi_agent = false
multi_agent_v2 = false
browser_use = false
browser_use_external = false
computer_use = false
image_generation = false
skill_mcp_dependency_install = false

[analytics]
enabled = false

[sandbox_workspace_write]
network_access = false

[mcp_servers.skillfetch]
default_tools_approval_mode = "approve"
command = "<skillfetch>/.venv/bin/skillfetch"
args = ["serve", "--index", "/tmp/skillfetch-codex-e2e-prep-20261023T224338/index"]
startup_timeout_sec = 60
tool_timeout_sec = 120

[mcp_servers.skillfetch.env]
PYTHONPATH = "/tmp/skillfetch-codex-e2e-prep-20261023T224338/source/src"
PYTHONDONTWRITEBYTECODE = "1"
HOME = "<home>"
```

검증 명령은 동일한 격리 환경에서 실행했다:

```sh
codex mcp get skillfetch
codex app-server --strict-config --print-startup-config
```

plain `mcp get` 출력의 `default_tools_approval_mode: approve`를 확인했다. `mcp get --json`에는 이 승인 필드가 빠지므로 판정에 쓰지 않았다. 실행 thread의 유효 전역 승인 정책과 sandbox도 별도로 검증했다. 승인 요청 콜백에서 모든 요청을 허용하는 처리나 추가 대화는 넣지 않았다.

Codex는 실행 중 config 끝에 해당 템플릿 레포의 `trust_level = "trusted"` 메타데이터를 자동 추가했다. 이전 실행의 해당 태스크에도 같은 메타데이터가 있어, 이전·이번 최종 config 사이의 차이는 MCP 승인 한 줄뿐이었다. 최초 검증기는 입력 config와 최종 config의 바이트 동일성을 요구해 이 19건을 실패로 기록했다. 기존 메타데이터와의 정확한 일치를 검사하도록 검증기를 수정했으며, 최초 실패 기록은 삭제하지 않았다. [최초 검증 기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/audit-verification-initial.json) · [최종 검증](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/audit-verification.json)

본 실험 전에 별도 ChatGPT 구독 세션에서 **모델이 직접** `profile_repo → search_skills → resolve_set → load_skills`를 호출하도록 했다. 네 호출 모두 실제 결과를 받았고, `uasl/api-testing@4ada9a2fac88`가 로드됐다. 이 사전 검증은 19개 태스크 분모에 포함하지 않았다. [사전 검증 결과](codex-e2e-2-smoke/verification.json) · [원시 기록](codex-e2e-2-smoke/transcript.jsonl)

## 세션별 기록

“호출”은 모델의 요청 횟수다. 첫 호출 턴은 아래 설명한 모델 응답 회차다. ID는 load 요청의 ID가 아니라 성공한 반환 payload의 `skills[].id`에서 추출했다. `COMPLETED`는 모델이 최종 응답으로 종료했다는 뜻이다.

| 태스크 | 레포 | skillfetch 호출 | 첫 호출 턴² | queries 원문 | 4번째=요청 원문 | load_skills 반환 ID | 끝난 방식 | 정리 |
|---|---|---:|---:|---|---|---|---|---|
| [s4-t027](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t027/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t027) | 일치 | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `COMPLETED` | `DONE` |
| [s4-t176](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t176/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t176) | 일치 | `uasl/debugging-strategies@c55dad9c9654` | `COMPLETED` | `DONE` |
| [s4-t153](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t153/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t153) | 일치 | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `COMPLETED` | `DONE` |
| [s4-t253](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t253/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t253) | 일치 | `uasl/sql-optimization-patterns@389f90da7b56` | `COMPLETED` | `DONE` |
| [s4-t182](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t182/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t182) | 일치 | `uasl/stream@94a72913c590` | `COMPLETED` | `DONE` |
| [s4-t203](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t203/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t203) | 일치 | `uasl/data-analyst-engine@79799e01e2dd` | `COMPLETED` | `DONE` |
| [s4-t055](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t055/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t055) | 일치 | `uasl/zen@f72229d0a781` | `COMPLETED` | `DONE` |
| [s4-t033](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t033/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t033) | 일치 | `uasl/debug-root-cause@1d7ea4a832dc` | `COMPLETED` | `DONE` |
| [s4-t130](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t130/transcript.jsonl) | nextjs | 예 (4회) | 2 | [1회 원문](#queries-s4-t130) | 일치 | `uasl/github-workflow-automation@519f4ba6e482` | `COMPLETED` | `DONE` |
| [s4-t177](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t177/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t177) | 일치 | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` | `DONE` |
| [s4-t229](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t229/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t229) | 일치 | `uasl/auth-implementation-patterns@7a99b395d548` | `COMPLETED` | `DONE` |
| [s4-t026](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t026/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t026) | 일치 | `uasl/vercel-react-best-practices@70f3b5aaf775` | `COMPLETED` | `DONE` |
| [s4-t224](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t224/transcript.jsonl) | nextjs | 예 (4회) | 2 | [1회 원문](#queries-s4-t224) | 일치 | `uasl/radar@a47ea6fd5f95` | `COMPLETED` | `DONE` |
| [s4-t211](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t211/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t211) | 일치 | `uasl/software-architecture@011a6d823631` | `COMPLETED` | `DONE` |
| [s4-t354](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t354/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t354) | 일치 | `uasl/verification-loop@39d9be23cf50` | `COMPLETED` | `DONE` |
| [s4-t101](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t101/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t101) | 일치 | `uasl/quill@336ba74b0e79` | `COMPLETED` | `DONE` |
| [s4-t342](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t342/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t342) | 일치 | `uasl/coding-standards@f854e26a9529` | `COMPLETED` | `DONE` |
| [s4-t280](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t280/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t280) | 일치 | `uasl/interaction-design@7c9d38549c2b` | `COMPLETED` | `DONE` |
| [s4-t001](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t001/transcript.jsonl) | fastapi | 예 (4회) | 2 | [1회 원문](#queries-s4-t001) | 일치 | `uasl/coding-standards@f854e26a9529` | `COMPLETED` | `DONE` |

첫 호출은 19/19개 세션에서 profile_repo였고, 19/19개에서 모델 응답 회차 2로 추론됐다.

² “턴”은 고유 `rawResponse/completed.responseId`의 1-based 순서다. 외부 사용자 턴은 세션마다 1회다. MCP 호출은 `functions.exec` 안에서 수행되어 부모 ID가 직접 제공되지 않는 경우가 있다. 이때 같은 thread/turn에서 MCP 시작·완료를 감싸는 유일하게 닫힌 exec 구간과 코드의 도구 이름을 대조해 회차를 추론했다. 직접 연결인지 추론인지 및 근거 sequence는 관찰 JSON의 `first_call`에 보존했다. 애매하면 미확인으로 남긴다. Stage 4의 assistant-message 순번과 같은 단위로 취급하지 않는다.

## 반환 오류와 관측 한계

load_skills의 프로토콜 오류, payload `error`/`errors`, 반환 관찰 충돌은 발견되지 않았다.

AGENTS.md는 이전과 같은 1–4단계이며 1–3개 스킬 선택까지 명시한다. 측정을 위해 추가 load 지시나 후속 사용자 메시지를 넣지 않았다. 로드된 스킬 내용의 유용성·적용 여부·코드 정확성은 평가하지 않았다. 단일 실행 19개 표본이므로 일반적인 Codex 전체 성공률이나 다른 모델의 성능으로 일반화하지 않는다.

## 고정 조건·재현 기록

- skillfetch: `14d2020f1275e10a272eb46575c9bd6d4a2182e4`. 고정 소스 238개와 인덱스 6개의 해시를 세션마다 검증했다.
- FastAPI s5: `2b38acb4586092ef0318bc6a8ab36436ba8fc09a`.
- Next.js s5: `2a1df71575f0c45a0f7a999bf77f4286d81e8706`.
- 태스크: FastAPI 17개·Next.js 2개. tasks SHA256 `d8822df5b8afeb587fc209218ca3f81fbe9ec3153acb66348c3f6a132306e572`.
- AGENTS SHA256: `dca56403ca97103358387ce4683272b836710df86adcf366fe7aead40417bf59`. 새 config SHA256: `69fb11307213035fce1442078304ff1891a1b4b22e5254a75d9387884bb590e1`.
- 각 태스크는 s5 커밋의 새 detached worktree, 새 ephemeral thread, 격리된 HOME/CODEX_HOME을 사용했다. s5 브랜치를 새로 만들지 않았다. MCP는 skillfetch만 등록했다.
- 세션 환경은 PATH, HOME, CODEX_HOME, TMPDIR와 선택적인 LANG/LC_ALL/TERM만 전달했다. OPENAI_API_KEY 등 API 키 변수는 상속하지 않았다. forced_login_method="chatgpt", login status, account/read(chatgpt/pro)를 각 세션에서 확인했다.
- 기본 Codex 추론은 허용된 ChatGPT 구독 인증을 사용했다. API 키 기반 호출은 실행하지 않았다. 셸 네트워크 접근은 이전과 같이 차단했다. MCP 스킬 본문 조회는 이전과 같은 서버 환경을 사용했다.
- 동시 실행 4개, 세션 제한 2700초, 모델 응답 회차 상한 없음. 태스크 프롬프트 재제출·재시도 없음. 별도 사전 검증 1회.
- 실행 시간(UTC): 2026-10-23T15:42:03.646Z ~ 2026-10-23T15:53:37.444Z.
- 각 세션 종료 후 worktree와 Git worktree 등록, 인증 symlink를 제거했다. 실험의 임시 worktree 루트도 제거했다. 고정 소스·인덱스와 측정 기록은 재현 근거로 보존했다.
- 이전 [codex-e2e.md](codex-e2e.md) SHA256: `db5b22600f4d20048f5669a39221335d8b5f7106cd1824d4b2deb57848d139c5`. 이전 보고서는 변경하지 않았다.

실행 명령:

```sh
node codex-e2e-2-runner.cjs \
  --run-dir codex-e2e-runs/20261024-subscription-mcp-approved-14d2020 \
  --config-template codex-e2e-2-preparation/config-template.toml \
  --agents-file codex-e2e-2-preparation/AGENTS.md \
  --source-preflight codex-e2e-2-preparation/source-preflight.json \
  --cloud-skills-snapshot codex-e2e-2-preparation/cloud-skills.json \
  --auth-file "<home>/Library/Application Support/orca/codex-accounts/54be5844-95fd-4c46-925c-75327ccd186a/home/auth.json" \
  --model gpt-6-astra --concurrency 4 --allow-codex-inference
```

위 명령의 기준 디렉터리는 `<e2e>`다. 실행마다 새 run-dir이 필요하며, 기존 경로 재사용은 중복 제출 방지를 위해 거부한다.

[실행 manifest](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/manifest.json) · [전체 관찰 JSON](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/observations.json) · [독립 전수 검증](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/audit-verification.json) · [실행기](codex-e2e-2-runner.cjs) · [추출기](codex-e2e-2-extract.cjs)

## search_skills에 넘긴 queries 원문

다음 값은 실제 도구 인자에서 추출했으며 재생성·번역·요약하지 않았다. 같은 호출의 시작/완료에 반복된 동일 인자는 배열을 한 번만 싣고 모든 관찰 sequence를 나열했다. 인자가 서로 다르면 각각 별도로 남긴다.

### queries-s4-t027

호출 `exec-ee65228e-8b94-4704-bd4e-3e4d5b49eec3` · 질의 검증 `PASS`.

원시 sequence: 76, 77.

```json
[
  "Fix item and user update validation to reject null values on non-nullable fields with HTTP 422 while preserving nullable field clearing and response models.",
  "Add request model validation and API regression tests, then run the existing route test suite.",
  "Python SQLModel backend targets backend/app/models.py, backend/app/api/routes/items.py, backend/app/api/routes/users.py, backend/tests/api/routes/test_items.py and backend/tests/api/routes/test_users.py.",
  "Bug: `PUT /api/v1/items/{id}` returns a 500 instead of a validation error when the body sets `title` to null.\n- Repro: create an item, then `PUT /api/v1/items/{id}` with `{\"title\": null}`. `ItemUpdate` in `backend/app/models.py` accepts the null. `update_item` in `backend/app/api/routes/items.py` then copies it onto the row through `model_dump(exclude_unset=True)` and `sqlmodel_update`, and the commit fails on the non-null `title` column.\n- Same pattern in `PATCH /api/v1/users/{user_id}`: `UserUpdate` allows `email`, `is_active` and `is_superuser` to be null. `update_user` only checks `if user_in.email:` and `crud.update_user` writes the nulls through.\n- Explicit nulls on non-nullable fields must be rejected with a 422 before anything reaches the session.\n- `description` (items) and `full_name` (users) must stay clearable by sending null. This is a product decision; don't change it.\n- The `ItemPublic` and `UserPublic` response models must stay unchanged.\nAcceptance: new cases in `backend/tests/api/routes/test_items.py` and `backend/tests/api/routes/test_users.py` cover the null-title, null-email and cleared-description/full_name paths. All existing tests in `backend/tests/api/routes/` pass unchanged."
]
```

### queries-s4-t176

호출 `exec-9d89168d-3ff1-4e78-9eaf-6ad13ee746af` · 질의 검증 `PASS`.

원시 sequence: 83, 84.

```json
[
  "Build weekly new-item counts that count only the latest item per owner_id and title and regenerate September numbers for comparison with admin flags.",
  "Implement backend aggregation that deduplicates item rows by owner and title before counting weekly new items and validate the September report.",
  "The target is backend/app/reports/weekly_items.py and created_at comes from fe56fa70289e_add_created_at_to_user_and_item.py; the backend stack is unspecified.",
  "The weekly new-items numbers we pull from the item table (using the created_at column added in fe56fa70289e_add_created_at_to_user_and_item.py) are double counting items that users deleted and re-added with the same title, because both rows come back for the same owner_id. Can you put the aggregation in a new backend/app/reports/weekly_items.py so only the latest item per (owner_id, title) counts, and regenerate the September numbers to compare against what the admin team flagged?"
]
```

### queries-s4-t153

호출 `exec-ce67dbb9-b394-47cb-a9e3-6eec2301d01f` · 질의 검증 `PASS`.

원시 sequence: 91, 92.

```json
[
  "Update the backend container image tag, Uvicorn worker count, and staging environment configuration while preserving production.",
  "Inspect Docker Compose and environment configuration and make staging-scoped deployment configuration changes.",
  "Known target files are compose.deploy.yml and .env configuration; the backend uses Uvicorn and the remaining stack and image version are unspecified.",
  "백엔드 이미지를 새 버전으로 올리면서 staging 환경에 먼저 배포하고 싶은데, `compose.deploy.yml`에 backend 이미지 태그랑 uvicorn worker 수 정리해주고 staging은 `ENVIRONMENT=staging`으로 뜨게 `.env` 쪽 설정도 맞춰줘. prod는 아직 건드리지 말아줘."
]
```

### queries-s4-t253

호출 `exec-9ccc5607-bb27-4922-a309-f8f76e56135a` · 질의 검증 `PASS`.

원시 sequence: 96, 97.

```json
[
  "Optimize item listing and total counts for regular users and add an owner_id and created_at composite index.",
  "Combine count and paginated items into one database query and add an Alembic index migration.",
  "Python backend targets backend/app/api/routes/items.py and backend/app/alembic/versions/; other stack details are unspecified.",
  "`backend/app/api/routes/items.py`의 `read_items()`가 아이템이 많아지면 일반 사용자 요청에서 느려져요. 요청마다 count 쿼리와 목록 쿼리를 따로 날리고 있어요. 그런데 `Item.owner_id`와 `created_at`에 인덱스가 없어서 두 쿼리 모두 테이블 전체를 훑는 것 같아요. count와 목록을 한 번의 쿼리로 가져오도록 바꿔 주세요. 그리고 `backend/app/alembic/versions/`에 마이그레이션을 추가해서 (owner_id, created_at) 인덱스를 만들어 주세요."
]
```

### queries-s4-t182

호출 `exec-2d2ab2a1-0159-495b-a8d5-25e7c17f8090` · 질의 검증 `PASS`.

원시 sequence: 104, 106.

```json
[
  "Build an item created_at backfill script using each owner's creation timestamp, including items whose owner has been deleted.",
  "Implement a database backfill with an outer join to the user table so items with deleted owners are retained.",
  "The target is backend/app/scripts/backfill_item_created_at.py and the migration is backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py; the remaining stack details are unspecified.",
  "item 테이블에 created_at 컬럼이 새로 생겼는데(backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py) 기존 아이템은 전부 null입니다. owner의 생성 시각을 기준으로 값을 계산해서 채워 넣는 backfill 스크립트를 backend/app/scripts/backfill_item_created_at.py로 짜 주세요. owner가 이미 지워진 아이템도 있어서, user 테이블은 outer join으로 걸어야 값이 맞습니다."
]
```

### queries-s4-t203

호출 `exec-61efdf3d-74e3-49b3-bbed-f5c3846664d2` · 질의 검증 `PASS`.

원시 sequence: 94, 95.

```json
[
  "Build an item priority classifier from title and description with an imbalanced sample dataset containing very few urgent labels.",
  "Train a baseline and a class-weighted or focal-loss model, and compare per-class F1 on the same evaluation data.",
  "Target backend/app/ml/item_classifier.py and backend/app/ml/data/; the programming stack and ML framework are unspecified.",
  "아이템 title/description으로 우선순위를 분류하는 모델이 아직 없어서 새로 만들어 주세요. 모델은 `backend/app/ml/item_classifier.py`에 만들고, 학습 데이터도 없으니 `backend/app/ml/data/`에 샘플 데이터셋을 같이 만들어 주세요. 데이터셋은 '긴급' 라벨이 아주 적은 불균형 데이터로 구성하면 돼요. 기본 학습 버전과 class weight 또는 focal loss를 넣은 버전을 각각 학습하고, 클래스별 F1을 비교해 주세요."
]
```

### queries-s4-t055

호출 `exec-09210c14-e20f-471a-b77f-c1892670a8fb` · 질의 검증 `PASS`.

원시 sequence: 77, 78.

```json
[
  "Extract items query logic from the frontend items route into a reusable items hook.",
  "Refactor query logic into a custom hook while preserving existing behavior.",
  "The target files are frontend/src/routes/_layout/items.tsx and frontend/src/hooks/useItems.ts; the framework is unspecified.",
  "move items query logic out of frontend/src/routes/_layout/items.tsx into frontend/src/hooks/useItems.ts"
]
```

### queries-s4-t033

호출 `exec-aaf74601-1ca1-466f-ad11-2e1951b773c5` · 질의 검증 `PASS`.

원시 sequence: 81, 84.

```json
[
  "Fix frontend API error handling so permission-denied responses preserve the user session and show error toasts.",
  "Make a minimal change to log out on HTTP 401 or HTTP 403 with the exact detail Could not validate credentials, while retaining existing error toasts and adding no packages.",
  "The target files are frontend/src/main.tsx, frontend/src/components/UserSettings/DeleteConfirmation.tsx, and backend/app/api/deps.py; the frontend uses TSX and frontend/src/client must not be modified.",
  "In the frontend, any 403 from the API logs the user out. `handleApiError` in `frontend/src/main.tsx` clears `access_token` and redirects to `/login` for both 401 and 403. Ordinary permission errors therefore act like an expired session. One example is \"Not enough permissions\" from the items routes. Another is a superuser hitting Delete in `frontend/src/components/UserSettings/DeleteConfirmation.tsx`, which gets \"Super users are not allowed to delete themselves\". In both cases the user is kicked to the login page instead of seeing the error toast. The backend's real invalid-token case is the 403 with detail \"Could not validate credentials\" raised in `get_current_user` (`backend/app/api/deps.py`). Keep the diff minimal: only log out on 401 or on that specific credentials 403, and let every other 403 fall through to the existing `handleError` toast. Add no new packages, and don't touch the generated client in `frontend/src/client`."
]
```

### queries-s4-t130

호출 `exec-bef6e578-a014-44ae-bd14-7811f7d5a029` · 질의 검증 `PASS`.

원시 sequence: 75, 76.

```json
[
  "Fix CI restoration of the .next/cache build cache.",
  "Update the CI cache step to key on package-lock.json and source files with a usable restore fallback.",
  "The project uses Next.js and npm; the CI platform and target workflow files are unspecified.",
  ".next/cache never restored in ci, every build is cold. fix the cache step (key on package-lock + source)"
]
```

### queries-s4-t177

호출 `exec-d516b05f-a3d8-4411-903f-321befe94dbb` · 질의 검증 `PASS`.

원시 sequence: 73, 76.

```json
[
  "Build an idempotent partner item export importer with field mappings, UTC timestamps, owner resolution, deduplication, and manifest counts.",
  "Implement a Python CLI importer that transactionally replaces a date's imported items and verify repeated loads using a sample drop.",
  "The known stack is Python with uv; target files are backend/app/models.py and new backend/app/importers/load_items.py, mappings.py, and partner_timezones.csv.",
  "Goal: add an importer that loads item records from partner export drops into the `item` table (`Item` in backend/app/models.py). None of this exists yet.\n- Create a new package backend/app/importers/ with a CLI module `load_items.py`. It reads drops from `exports/items/dt=YYYY-MM-DD/*.json`, with the base directory taken from a `--source-dir` option. Each drop also contains a manifest.json with the per-partner item counts.\n- Three partner systems write these files, and their field names differ slightly (`created` vs `created_at`, `owner_email` vs `user_email`). Put the field mapping in a new backend/app/importers/mappings.py, one dict per partner.\n- Normalize `created_at` to UTC. One partner writes local time. For its files, use per-partner offsets from a new backend/app/importers/partner_timezones.csv.\n- Resolve `owner_id` from the email with `crud.get_user_by_email`.\n- Dedupe on (owner_id, title, created_at) before insert.\n- The load must be idempotent: rerunning a date replaces the items loaded from that date's drop and never appends.\n- Add a small sample drop for 2026-10-20, with its manifest.json, so the command can be run.\nAcceptance: running `uv run python -m app.importers.load_items --date 2026-10-20` from backend/ twice leaves the same row count in `item`, and the item count per partner matches that drop's manifest.json."
]
```

### queries-s4-t229

호출 `exec-a707384f-dcaa-47d8-9e43-76efb2f6302a` · 질의 검증 `PASS`.

원시 sequence: 70, 73.

```json
[
  "Prevent JWT access tokens and password-reset tokens from being accepted interchangeably by adding and checking a token type claim.",
  "Make a minimal security fix without changing function signatures and verify rejection of wrong token types.",
  "The stack is Python; target files are backend/app/core/security.py, backend/app/utils.py, and backend/app/api/deps.py; the framework is unspecified.",
  "Two kinds of JWT are signed with the same `SECRET_KEY` and `HS256`: access tokens from `create_access_token` in `backend/app/core/security.py`, and password-reset tokens from `generate_password_reset_token` in `backend/app/utils.py`. Neither carries a token-type claim. As a result, each kind decodes successfully wherever the other is expected, and only the `sub` lookup happens to fail. Please harden this: add a type claim to both, and make `get_current_user` in `backend/app/api/deps.py` and `verify_password_reset_token` reject tokens of the wrong type. Keep the diff minimal and don't change any function signatures, because the routes in `login.py` and `users.py` and the helpers in `backend/tests/utils/` call them by name."
]
```

### queries-s4-t026

호출 `exec-7800a623-d143-4d28-84c0-a8ca416ffb2a` · 질의 검증 `PASS`.

원시 sequence: 77, 80.

```json
[
  "Fix Items and admin Users table pagination so every record beyond the first 100 is accessible.",
  "Implement server-side pagination with skip and limit offsets and returned count, ensuring stable ordering and validating page navigation.",
  "Targets are frontend/src/routes/_layout/items.tsx, frontend/src/routes/_layout/admin.tsx, frontend/src/components/Common/DataTable.tsx, and backend/app/api/routes/; TSX frontend and backend framework unspecified.",
  "Users with more than 100 items only ever see their newest 100 on the Items page, and the admin page stops at 100 users. `getItemsQueryOptions` in `frontend/src/routes/_layout/items.tsx` always calls `ItemsService.readItems` with `skip: 0, limit: 100`, and `getUsersQueryOptions` in `frontend/src/routes/_layout/admin.tsx` does the same with `UsersService.readUsers`. `DataTable` in `frontend/src/components/Common/DataTable.tsx` then paginates only that first slice on the client and ignores the `count` that `read_items` and `read_users` in `backend/app/api/routes/` already return. Its \"of N entries\" text and page count are built from `data.length`, so anything past 100 never appears. Can you fix this so paging through the tables reaches every item and user exactly once, using `skip`/`limit` and the returned `count`?"
]
```

### queries-s4-t224

호출 `exec-2056477a-82d3-48dc-9896-5cd93d85099b` · 질의 검증 `PASS`.

원시 sequence: 89, 90.

```json
[
  "Add TensorFlow.js and a user profile photo preprocessing function with consistent input tensors in Safari and Chrome.",
  "Implement deterministic pixel extraction from an HTML canvas drawing surface with explicit RGB or BGR channel ordering and normalization.",
  "The specified files are pages/users/[id].tsx, package.json, and a new utils/preprocess.ts; the remaining stack is unspecified.",
  "`pages/users/[id].tsx`에 TensorFlow.js로 사용자 프로필 사진 분류를 붙이려고 해요. 아직 관련 코드가 전혀 없으니 `@tensorflow/tfjs`를 `package.json`에 추가하고, 전처리 함수를 `utils/preprocess.ts`에 새로 만들어 주세요. 2D 드로잉 표면(HTML 그리기 요소)에서 픽셀을 읽을 때 RGB/BGR 순서와 정규화가 브라우저마다 달라지지 않게 해서, Safari와 Chrome에서 같은 입력 텐서가 나오도록 해 주세요."
]
```

### queries-s4-t211

호출 `exec-96f1d055-ecd1-413f-bc87-f35f86ad6645` · 질의 검증 `PASS`.

원시 sequence: 84, 85.

```json
[
  "Build item click-through rate prediction serving with a training config and detect feature hashing bucket mismatches at application startup.",
  "Read feature hashing bucket counts from shared configuration instead of hardcoding and validate training and serving compatibility at startup.",
  "Python and JSON target files are backend/app/ml/ctr.py, backend/app/ml/ctr_config.json, and backend/app/main.py; frameworks are unspecified.",
  "아이템 클릭률(CTR) 예측 서빙 코드를 `backend/app/ml/ctr.py`에 새로 만들어 주세요. 학습 config도 아직 없으니 `backend/app/ml/ctr_config.json`으로 같이 만들어 주세요. 피처 해싱 버킷 수가 학습 때와 다르면 예측값이 전부 0.5 근처로 나오기 때문에, 버킷 수는 하드코딩하지 말고 이 config에서 읽어오게 해 주세요. 불일치하면 `backend/app/main.py`에서 앱이 시작할 때 에러가 나게 해 주세요."
]
```

### queries-s4-t354

호출 `exec-ea1b2fdd-b27d-46ee-bc33-22a1529f2fa1` · 질의 검증 `PASS`.

원시 sequence: 69, 72.

```json
[
  "Add a backend pre-deploy check that aborts rollout when the database Alembic revision differs from migration head.",
  "Make a minimal change with one new database function and one startup main call.",
  "The stack is Python with Alembic; target files are backend/app/core/db.py and backend/app/initial_data.py, run by backend/scripts/prestart.sh.",
  "Add a pre-deploy check to the backend startup that `backend/scripts/prestart.sh` runs. It should compare the database's Alembic revision with the head in `backend/app/alembic/versions/` and abort the rollout if they don't match. Minimal diff please: one new function in `backend/app/core/db.py` and one call to it inside `main()` in `backend/app/initial_data.py`."
]
```

### queries-s4-t101

호출 `exec-66c2675c-6018-417a-b9ad-f79081d214ef` · 질의 검증 `PASS`.

원시 sequence: 73, 75.

```json
[
  "Document utility functions, especially password reset token generation and verification, explaining expiration hours, JWT exp claims, and UTC versus local time.",
  "Write accurate Python docstrings based on the existing implementation to help new developers understand password reset token expiration.",
  "The target file is backend/app/utils.py in a Python backend; the framework and other stack details are unspecified.",
  "Can you write proper docstrings for the functions in backend/app/utils.py, especially generate_password_reset_token and verify_password_reset_token? New devs keep getting confused about how EMAIL_RESET_TOKEN_EXPIRE_HOURS interacts with the token's exp claim and UTC vs local time, and right now none of that is written down anywhere."
]
```

### queries-s4-t342

호출 `exec-bdbc4a96-1bf1-4082-ad27-d59a8541a827` · 질의 검증 `PASS`.

원시 sequence: 77, 78.

```json
[
  "Add a dry-run flag to initial superuser initialization and display email, superuser value, and existing or proposed creation status.",
  "Make a minimal change threading a command-line flag through main and init into init_db and skip crud.create_user during dry runs.",
  "The target files are backend/app/initial_data.py and backend/app/core/db.py; the language is Python and the remaining stack is unspecified.",
  "Add a `--dry-run` flag to the `backend/app/initial_data.py` script so ops can see whether the first superuser would be created without writing to the `user` table. It should print a summary table of the email, the `is_superuser` value and the old/new status (already exists / would be created). Keep the diff minimal: just thread the flag through the existing `main()` / `init()` into `init_db()` in `backend/app/core/db.py`, and skip the `crud.create_user` call."
]
```

### queries-s4-t280

호출 `exec-16278445-4492-4a42-b306-9bcfee18ffb1` · 질의 검증 `PASS`.

원시 sequence: 78, 80.

```json
[
  "Add a skeleton loader to the sidebar user block to prevent flicker while the current user loads.",
  "Fix loading-state rendering by showing a skeleton placeholder until the current user is available.",
  "The target is frontend/src/components/Sidebar/User.tsx, a TSX frontend component; the framework and styling stack are unspecified.",
  "add skeleton loader to the user block in frontend/src/components/Sidebar/User.tsx, flickers on load while current user loads"
]
```

### queries-s4-t001

호출 `exec-ba005081-6d63-4758-aa9e-c6f8faac3e36` · 질의 검증 `PASS`.

원시 sequence: 76, 77.

```json
[
  "Add a dry-run option to the initial database data script that prints rows that would be created.",
  "Implement command-line argument parsing and skip database writes during a dry run.",
  "The target is backend/app/initial_data.py in Python; the framework and database stack are unspecified.",
  "add --dry-run to backend/app/initial_data.py, print what would be created instead of writing rows"
]
```


## 후속 분석: oracle 관련성 및 Claude Code Stage 5 V2 비교

재채점 전 라벨 기준

기존 Codex 19회와 Claude Code V2의 r1·r2·r3 기록 57회만 읽어 계산했다. 새 세션 실행·MCP 호출·추가 채점은 하지 않았다. 지정한 [stage5/oracle.jsonl](stage5/oracle.jsonl)의 `pool[].grade`를 유일한 판정 근거로 사용했다. `relevant_grades`와도 전수 대조해 충돌이 없음을 확인했다.

V2는 같은 s5 기반에 아래 CLAUDE.md 한 줄을 추가한 조건이다. 두 레포의 기록된 V2 커밋과 해당 파일을 대조했다. V2 로그의 모델은 claude-opus-5-5[1m]이며, 성공 종료 41회와 error_max_turns 종료 16회를 모두 포함했다. 기록된 파일 조건은 검증했지만 stream-json만으로 개별 세션의 지침 주입 자체를 독립 입증한 것은 아니다.

```text
Before your first tool call on any coding task in this repository (anything beyond a one-line edit, a rename or a question), run the `skillfetch-router` skill and follow its steps.
```

**Codex에서 확인된 관련 스킬 적중은 4/19 (21.1%), 채점된 로드만의 micro precision은 4/11 (36.4%)다.** 로드 20건 중 9건(8개 세션)은 미채점이다. 따라서 전체 로드 정밀도를 확정할 수 없으며, 확인된 적중만 전체 로드로 나눈 값은 4/20 (20.0%)라는 하한이다.

### 계산 기준

- 관련: 해당 태스크의 oracle 등급 ≥2. 태스크 ID와 revision을 포함한 전체 스킬 ID가 정확히 일치해야 한다. 다른 태스크의 등급을 가져오거나 ID의 해시를 지우지 않았다.
- 로드 세트: `load_skills`의 실제 성공 반환 `skills[].id`를 세션 안에서 중복 제거했다. 요청한 ID, resolve 후보, 최종 발화의 주장만으로는 로드로 세지 않았다. 동일 스킬이 다른 세션에서 로드되면 각각 한 건이다.
- 확인된 세션 적중률: 관련 스킬을 하나 이상 로드한 세션 / 스킬을 하나 이상 로드한 세션. 미채점만 있어 적중 여부가 미확정인 세션은 별도로 표시한다.
- 채점된 로드 precision: 관련 로드 / 등급이 존재하는 전체 로드. 미채점은 분모에서 제외한다. 전체 로드 기준의 확인 적중 비율은 하한으로만 표시하며, 미채점을 0점으로 바꾸지 않는다.
- “관련 스킬 없음”은 oracle에서 등급 ≥2인 항목이 0개인 태스크를 뜻한다. 이 4개를 포함해 `expect_none`은 19개 모두 false이므로 해당 플래그로 집계하지 않았다. oracle 밖 미채점 스킬까지 무관하다는 뜻은 아니다.

### 관련성 지표

| 집계 | 로드 세션 / 전체 | 확인 적중 / 로드 세션 | precision: 채점된 로드만 | 전체 로드 기준 확인 적중 하한 | 미채점 로드 / 전체 로드 | 미채점 포함 세션 |
|---|---:|---:|---:|---:|---:|---:|
| Codex | 19/19 | 4/19 (21.1%) | 4/11 (36.4%) | 4/20 (20.0%) | 9/20 | 8 |
| Claude V2 r1 | 19/19 | 5/19 (26.3%) | 5/15 (33.3%) | 5/29 (17.2%) | 14/29 | 9 |
| Claude V2 r2 | 17/19 | 10/17 (58.8%) | 10/15 (66.7%) | 10/25 (40.0%) | 10/25 | 9 |
| Claude V2 r3 | 19/19 | 7/19 (36.8%) | 7/13 (53.8%) | 7/31 (22.6%) | 18/31 | 12 |
| Claude V2 합계 | 55/57 | 22/55 (40.0%) | 22/43 (51.2%) | 22/85 (25.9%) | 42/85 | 30 |

Codex의 19개 로드 세션은 확인 적중 4개, 채점된 스킬만으로 확인된 비적중 7개, 확인 적중은 없고 미채점 스킬이 있어 미확정인 세션 8개다. 미채점의 실제 등급을 모르므로 전체 세션 적중률의 가능한 범위는 21.1%–63.2%, 전체 로드 precision은 20.0%–65.0%다. 이는 신뢰구간이 아니라 미채점 항목 때문에 생기는 산술적 범위다.

Claude V2 합계는 57회 중 55회에서 로드했다. 로드하지 않은 세션도 원래 3회 비교표에서 제외하지 않았다. 종료 방식이 성공이 아니더라도 그 전에 실제 반환된 스킬은 포함했다. 두 조건은 모델·라우터 지침·세션 수·실행 한도 등이 다르므로 이 표만으로 모델 우열이나 지침의 인과 효과를 판정하지 않는다.

### oracle상 관련 스킬이 없는 태스크의 로드

대상은 `s4-t033`, `s4-t354`, `s4-t101`, `s4-t342` 4개다. **Codex는 4/4개 태스크에서 총 4개 스킬을 로드했다.** 이 중 1건은 등급 0–1, 3건은 미채점이다.

| 집계 | 로드한 세션 / 해당 세션 | 로드 스킬 수 | 그중 미채점 |
|---|---:|---:|---:|
| Codex | 4/4 | 4 | 3 |
| Claude V2 r1 | 4/4 | 7 | 4 |
| Claude V2 r2 | 4/4 | 5 | 2 |
| Claude V2 r3 | 4/4 | 7 | 5 |
| Claude V2 합계 | 12/12 | 19 | 11 |

### 요청 길이와 태스크별 로드 세트

요청 길이는 tasks.jsonl.prompt의 Unicode 코드포인트 수이며 공백·줄바꿈을 포함한다. **800자 이상 요청은 4/19개**: `s4-t027` 1219자, `s4-t033` 942자, `s4-t177` 1351자, `s4-t026` 823자. V2의 세 반복에선 같은 장문 요청이 12/57회 등장한다. V2 57회 메타데이터의 실제 -p 인자가 이 요청과 모두 일치한다.

Codex의 네 번째 쿼리는 19/19개 태스크에서 요청 원문과 정확히 일치했다. 검색 시작·완료의 인자 관찰 38개도 모두 일치하며, 800자 이상 요청 4개도 포함한다. 이는 MCP 호출 인자 기준의 비교다.

괄호는 해당 태스크의 oracle 등급이며, 등급이 없으면 **미채점**으로 표시했다. `∅`는 실제 반환된 로드 세트가 비어 있다는 뜻이다. ★는 800자 이상 요청, “관련 후보 0”은 위의 oracle상 무관련 태스크다.

| 태스크 | 요청 길이 | oracle 관련 후보 | Codex 4번째 쿼리 | Codex 로드 세트 | Claude V2 r1 | Claude V2 r2 | Claude V2 r3 |
|---|---:|---:|---|---|---|---|---|
| s4-t027 | 1219 ★ | 3 | 원문 일치 | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/tdd@ff86dad94075` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t027/transcript.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/coding-guidelines@0ec7e45f92f2` (미채점)<br>[기록](stage5/runs/V2/s4-t027-r1.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/coding-guidelines@0ec7e45f92f2` (미채점)<br>[기록](stage5/runs/V2/s4-t027-r2.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/tdd@ff86dad94075` (미채점)<br>[기록](stage5/runs/V2/s4-t027-r3.jsonl) |
| s4-t176 | 485 | 1 | 원문 일치 | `uasl/debugging-strategies@c55dad9c9654` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t176/transcript.jsonl) | `path:<worktrees>/s5/s5-V2-s4-t176-r1/.agents/skills/sqlmodel` (미채점)<br>`uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>[기록](stage5/runs/V2/s4-t176-r1.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>[기록](stage5/runs/V2/s4-t176-r2.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>[기록](stage5/runs/V2/s4-t176-r3.jsonl) |
| s4-t153 | 179 | 2 | 원문 일치 | `uasl/deployment-pipeline-design@2a89fc6f32ff` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t153/transcript.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t153-r1.jsonl) | `uasl/karpathy-guidelines@da897c8c3bab` (2)<br>[기록](stage5/runs/V2/s4-t153-r2.jsonl) | `uasl/karpathy-guidelines@da897c8c3bab` (2)<br>[기록](stage5/runs/V2/s4-t153-r3.jsonl) |
| s4-t253 | 303 | 4 | 원문 일치 | `uasl/sql-optimization-patterns@389f90da7b56` (3)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t253/transcript.jsonl) | `path:<worktrees>/s5/s5-V2-s4-t253-r1/.venv/lib/python3.14/site-packages/sqlmodel/.agents/skills/sqlmodel` (미채점)<br>`uasl/python-performance-optimization@bf455fd100bf` (미채점)<br>[기록](stage5/runs/V2/s4-t253-r1.jsonl) | `path:<worktrees>/s5/s5-V2-s4-t253-r2/.claude/skills/sqlmodel` (미채점)<br>`uasl/sql-optimization-patterns@389f90da7b56` (3)<br>[기록](stage5/runs/V2/s4-t253-r2.jsonl) | `path:<worktrees>/s5/s5-V2-s4-t253-r3/.claude/skills/sqlmodel` (미채점)<br>`uasl/schema@e6f260ce62e0` (미채점)<br>[기록](stage5/runs/V2/s4-t253-r3.jsonl) |
| s4-t182 | 294 | 1 | 원문 일치 | `uasl/stream@94a72913c590` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t182/transcript.jsonl) | `uasl/python-error-handling@8dc34883a143` (1)<br>[기록](stage5/runs/V2/s4-t182-r1.jsonl) | ∅ (로드 없음)<br>[기록](stage5/runs/V2/s4-t182-r2.jsonl) | `path:<worktrees>/s5/s5-V2-s4-t182-r3/.venv/lib/python3.14/site-packages/sqlmodel/.agents/skills/sqlmodel` (미채점)<br>[기록](stage5/runs/V2/s4-t182-r3.jsonl) |
| s4-t203 | 271 | 2 | 원문 일치 | `uasl/data-analyst-engine@79799e01e2dd` (2)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t203/transcript.jsonl) | `uasl/data-analyst-engine@79799e01e2dd` (2)<br>[기록](stage5/runs/V2/s4-t203-r1.jsonl) | `uasl/data-analyst-engine@79799e01e2dd` (2)<br>[기록](stage5/runs/V2/s4-t203-r2.jsonl) | `uasl/data-analyst-engine@79799e01e2dd` (2)<br>[기록](stage5/runs/V2/s4-t203-r3.jsonl) |
| s4-t055 | 103 | 3 | 원문 일치 | `uasl/zen@f72229d0a781` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t055/transcript.jsonl) | `uasl/refactoring-patterns@7283bad3e86e` (2)<br>[기록](stage5/runs/V2/s4-t055-r1.jsonl) | `uasl/refactoring-patterns@7283bad3e86e` (2)<br>`uasl/verification-loop@39d9be23cf50` (미채점)<br>[기록](stage5/runs/V2/s4-t055-r2.jsonl) | `uasl/refactoring-patterns@7283bad3e86e` (2)<br>`uasl/react-patterns@73d1ecc06997` (미채점)<br>[기록](stage5/runs/V2/s4-t055-r3.jsonl) |
| s4-t033 | 942 ★ | 0 | 원문 일치 | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t033/transcript.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/coding-guidelines@0ec7e45f92f2` (미채점)<br>`uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t033-r1.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t033-r2.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/coding-guidelines@0ec7e45f92f2` (미채점)<br>[기록](stage5/runs/V2/s4-t033-r3.jsonl) |
| s4-t130 | 104 | 2 | 원문 일치 | `uasl/github-workflow-automation@519f4ba6e482` (2)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t130/transcript.jsonl) | `uasl/github-actions-templates@ce03df93ccdf` (2)<br>[기록](stage5/runs/V2/s4-t130-r1.jsonl) | `uasl/github-actions-templates@ce03df93ccdf` (2)<br>[기록](stage5/runs/V2/s4-t130-r2.jsonl) | `uasl/github-actions-templates@ce03df93ccdf` (2)<br>[기록](stage5/runs/V2/s4-t130-r3.jsonl) |
| s4-t177 | 1351 ★ | 1 | 원문 일치 | `uasl/python-error-handling@8dc34883a143` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t177/transcript.jsonl) | `uasl/stream@94a72913c590` (2)<br>`uasl/python-error-handling@8dc34883a143` (미채점)<br>[기록](stage5/runs/V2/s4-t177-r1.jsonl) | `uasl/stream@94a72913c590` (2)<br>`uasl/python-error-handling@8dc34883a143` (미채점)<br>[기록](stage5/runs/V2/s4-t177-r2.jsonl) | `path:<worktrees>/s5/s5-V2-s4-t177-r3/.venv/lib/python3.14/site-packages/sqlmodel/.agents/skills/sqlmodel` (미채점)<br>`uasl/python-error-handling@8dc34883a143` (미채점)<br>`uasl/stream@94a72913c590` (2)<br>[기록](stage5/runs/V2/s4-t177-r3.jsonl) |
| s4-t229 | 731 | 2 | 원문 일치 | `uasl/auth-implementation-patterns@7a99b395d548` (2)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t229/transcript.jsonl) | `uasl/auth-implementation-patterns@7a99b395d548` (2)<br>`uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t229-r1.jsonl) | `uasl/auth-implementation-patterns@7a99b395d548` (2)<br>`uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t229-r2.jsonl) | `uasl/auth-implementation-patterns@7a99b395d548` (2)<br>`uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t229-r3.jsonl) |
| s4-t026 | 823 ★ | 1 | 원문 일치 | `uasl/vercel-react-best-practices@70f3b5aaf775` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t026/transcript.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/verification-loop@39d9be23cf50` (미채점)<br>[기록](stage5/runs/V2/s4-t026-r1.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/vercel-react-best-practices@70f3b5aaf775` (1)<br>[기록](stage5/runs/V2/s4-t026-r2.jsonl) | `uasl/debug-root-cause@1d7ea4a832dc` (미채점)<br>`uasl/verification-loop@39d9be23cf50` (미채점)<br>[기록](stage5/runs/V2/s4-t026-r3.jsonl) |
| s4-t224 | 273 | 2 | 원문 일치 | `uasl/radar@a47ea6fd5f95` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t224/transcript.jsonl) | `uasl/documentation-lookup@dee6d7478eab` (미채점)<br>[기록](stage5/runs/V2/s4-t224-r1.jsonl) | `uasl/documentation-lookup@dee6d7478eab` (미채점)<br>`uasl/next-best-practices@ee058f89acea` (2)<br>[기록](stage5/runs/V2/s4-t224-r2.jsonl) | `uasl/documentation-lookup@dee6d7478eab` (미채점)<br>[기록](stage5/runs/V2/s4-t224-r3.jsonl) |
| s4-t211 | 263 | 3 | 원문 일치 | `uasl/software-architecture@011a6d823631` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t211/transcript.jsonl) | `uasl/coding-standards@f854e26a9529` (1)<br>[기록](stage5/runs/V2/s4-t211-r1.jsonl) | `uasl/fastapi-templates@effcd0de0b4c` (2)<br>[기록](stage5/runs/V2/s4-t211-r2.jsonl) | `uasl/error-handling-patterns@4c19ee7d7821` (2)<br>[기록](stage5/runs/V2/s4-t211-r3.jsonl) |
| s4-t354 | 363 | 0 | 원문 일치 | `uasl/verification-loop@39d9be23cf50` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t354/transcript.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t354-r1.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t354-r2.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>[기록](stage5/runs/V2/s4-t354-r3.jsonl) |
| s4-t101 | 333 | 0 | 원문 일치 | `uasl/quill@336ba74b0e79` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t101/transcript.jsonl) | `uasl/quill@336ba74b0e79` (미채점)<br>[기록](stage5/runs/V2/s4-t101-r1.jsonl) | `uasl/quill@336ba74b0e79` (미채점)<br>[기록](stage5/runs/V2/s4-t101-r2.jsonl) | `uasl/quill@336ba74b0e79` (미채점)<br>`uasl/verification-before-completion@134bf517af69` (미채점)<br>[기록](stage5/runs/V2/s4-t101-r3.jsonl) |
| s4-t342 | 463 | 0 | 원문 일치 | `uasl/coding-standards@f854e26a9529` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t342/transcript.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>`uasl/coding-standards@f854e26a9529` (미채점)<br>[기록](stage5/runs/V2/s4-t342-r1.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>`uasl/coding-standards@f854e26a9529` (미채점)<br>[기록](stage5/runs/V2/s4-t342-r2.jsonl) | `uasl/verification-loop@39d9be23cf50` (1)<br>`uasl/coding-standards@f854e26a9529` (미채점)<br>[기록](stage5/runs/V2/s4-t342-r3.jsonl) |
| s4-t280 | 124 | 1 | 원문 일치 | `uasl/interaction-design@7c9d38549c2b` (미채점)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t280/transcript.jsonl) | `uasl/react-patterns@73d1ecc06997` (1)<br>`uasl/design-to-code@fae28f73cda0` (1)<br>[기록](stage5/runs/V2/s4-t280-r1.jsonl) | `uasl/artisan@1e09f38ffcab` (2)<br>[기록](stage5/runs/V2/s4-t280-r2.jsonl) | `uasl/design-to-code@fae28f73cda0` (1)<br>`uasl/react-patterns@73d1ecc06997` (1)<br>[기록](stage5/runs/V2/s4-t280-r3.jsonl) |
| s4-t001 | 97 | 1 | 원문 일치 | `uasl/coding-standards@f854e26a9529` (1)<br>[기록](codex-e2e-runs/20261024-subscription-mcp-approved-14d2020/tasks/s4-t001/transcript.jsonl) | `uasl/coding-standards@f854e26a9529` (1)<br>[기록](stage5/runs/V2/s4-t001-r1.jsonl) | ∅ (로드 없음)<br>[기록](stage5/runs/V2/s4-t001-r2.jsonl) | `uasl/coding-standards@f854e26a9529` (1)<br>`uasl/verification-loop@39d9be23cf50` (미채점)<br>[기록](stage5/runs/V2/s4-t001-r3.jsonl) |

### 미채점 및 재현 근거

Codex의 미채점 9건은 8개 세션에 걸치며 고유 스킬 ID는 8개다. “미채점”은 태스크와 스킬의 쌍에 붙는다. 같은 스킬 ID라도 다른 태스크에서 받은 등급은 전용하지 않았다. Claude V2의 미채점은 42건, 30개 세션이다. 모든 미채점 쌍과 반환 근거는 아래 JSON에 보존했다.

V2가 path: 형식으로 반환한 6건도 반환 ID 그대로 표시했다. 이를 비슷한 카탈로그 ID로 바꾸거나 등급을 추정하지 않고 미채점으로 유지했다.

- [Codex·oracle 대조 및 지표 JSON](codex-e2e-2-oracle-analysis.json)
- [Claude V2 57회 반환 추출 및 원시 행 근거](codex-e2e-2-oracle-v2.json)
- [계산·추가 스크립트](codex-e2e-2-oracle-analysis.cjs)
- oracle SHA256: `52344710c155e141a978b31f4499591581430997d69dd99bb4da7b7b5ffb55c6`.
- 원래 보고서 35130바이트를 그대로 보존하고 이 절만 뒤에 추가했다. 기존 부분 SHA256: `d5b8d8ca79f8be1e4963532eb98d16a94c60b46ee018d64010507f28735113c3`.
- 작업 코드의 정확성이나 로드한 스킬의 실제 사용 여부는 평가하지 않았다. 다른 oracle·라벨 파일은 이 계산에 사용하지 않았다.
