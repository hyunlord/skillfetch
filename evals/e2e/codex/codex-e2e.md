Codex CLI 0.164.0 | 모델: gpt-6-astra (reasoning: medium) | 인증: ChatGPT Pro 구독 로그인 (`chatgpt`), API 키 환경변수 미상속

# Codex E2E: 호출 시도 19/19, 실제 MCP 실행 성공 0/19

19개 태스크를 각각 정확히 한 번 실행했다. **발화율은 19/19 = 100%**다. 여기서 발화는 모델이 skillfetch 도구 호출을 요청한 경우를 뜻한다. 그러나 **실행기가 선택한 `approval_policy = "never"` 때문에 23개 MCP 호출 시도 전부가 서버 실행 전에 거절됐다.** 따라서 검색·로드가 동작한 실험이라고 해석하면 안 된다. 승인 정책은 이번 하네스의 설정이며, 이 결과만으로 skillfetch 서버나 Codex의 MCP 프로토콜이 호환되지 않는다고 결론 내릴 수 없다.

관측된 오류는 모든 호출에서 같았다:

```text
MCP tool call requires approval, but approval policy is never
```

| 지표 | 결과 |
|---|---:|
| 실제 태스크 실행 | 19/19, 각 1회 |
| skillfetch 호출 요청이 나온 세션 | **19/19 (100%)** |
| 실제 MCP 도구 실행 성공 세션 | **0/19** |
| search_skills 호출 요청이 나온 세션 | 4/19 (21.1%) |
| 검색 응답을 받은 세션 | 0/19 |
| load_skills 호출 / 받은 스킬 ID | 0회 / 0개 |
| 첫 skillfetch 호출 | 모두 profile_repo, 모델 응답 회차 2 |
| 정상적인 모델 최종 응답으로 종료 | 19/19 |
| 타임아웃·추론 오류로 종료 | 0/19 |

호출 시도 합계는 `profile_repo` 19회 + `search_skills` 4회 = 23회다. `COMPLETED`는 Codex가 최종 응답을 반환했다는 실행 상태이며, 코딩 결과물의 정확성 판정이 아니다. 작업 결과물은 평가하지 않았다. 성공적인 검색·선택·로드의 성능이나 Stage 5의 로드율과 비교할 근거는 이번 실행에서 얻지 못했다.

## 세션별 기록

각 태스크 ID는 실제 측정 세션의 원시 로그로 연결된다. 호출 열의 “예”는 **요청 시도**이며 모두 승인 차단됐다. queries가 “없음”이면 실제 `search_skills` 요청이 없었다는 뜻이다. 모델이 별도로 만들어 두기만 한 질의는 기록에 섞지 않았다. 받은 스킬 ID의 `[]`는 로드된 스킬이 없다는 뜻이다.

| 태스크 | 레포 | skillfetch 호출 시도 | 첫 호출 턴¹ | search_skills queries | load_skills로 받은 ID | 끝난 방식 | worktree 정리 |
|---|---|---|---:|---|---|---|---|
| [s4-t027](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t027/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t176](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t176/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t153](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t153/transcript.jsonl) | fastapi | 예 (2회, 모두 차단) | 2 | 4개 · [원문](#queries-s4-t153) | `[]` | `COMPLETED` | `DONE` |
| [s4-t253](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t253/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t182](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t182/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t203](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t203/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t055](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t055/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t033](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t033/transcript.jsonl) | fastapi | 예 (2회, 모두 차단) | 2 | 4개 · [원문](#queries-s4-t033) | `[]` | `COMPLETED` | `DONE` |
| [s4-t130](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t130/transcript.jsonl) | nextjs | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t177](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t177/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t229](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t229/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t026](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t026/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t224](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t224/transcript.jsonl) | nextjs | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t211](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t211/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t354](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t354/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t101](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t101/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |
| [s4-t342](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/tasks/s4-t342/transcript.jsonl) | fastapi | 예 (2회, 모두 차단) | 2 | 4개 · [원문](#queries-s4-t342) | `[]` | `COMPLETED` | `DONE` |
| [s4-t280](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t280/transcript.jsonl) | fastapi | 예 (2회, 모두 차단) | 2 | 4개 · [원문](#queries-s4-t280) | `[]` | `COMPLETED` | `DONE` |
| [s4-t001](codex-e2e-runs/20261023-subscription-14d2020/tasks/s4-t001/transcript.jsonl) | fastapi | 예 (1회, 모두 차단) | 2 | 없음 | `[]` | `COMPLETED` | `DONE` |

¹ “턴”은 최초 사용자 요청을 1턴이라고 부르는 단위가 아니라 **모델 응답 회차**다. 고유 `rawResponse/completed.responseId`의 1-based 순서를 사용했다. 이번 Codex는 `functions.exec` 안에서 MCP를 호출하므로 MCP ID와 부모 모델 호출 ID가 직접 연결되지 않는다. 같은 thread/turn에서 해당 MCP 시작·종료를 감싸는 유일한 완료된 exec 구간, 그 구간의 명시적인 도구 호출 코드, 동일 `call_id`의 반환 이벤트를 대조해 19개 모두 회차 2로 **추론**했다. 직접 제공된 parent ID 값은 아니며 Stage 4의 assistant-message 순번과 동일한 단위라고 간주하지 않는다. 연결 근거와 원시 sequence는 [관찰 JSON](codex-e2e-runs/cohort-observations.json)의 각 `first_call`에 보존했다.

## 실제 검색 요청의 queries 원문

아래 배열은 모델의 `search_skills` 도구 요청 인자에서 그대로 추출했다. **승인 단계에서 차단되어 서버에는 전달되지 않았다.** 문자열을 다시 생성·번역·요약하지 않았다. 네 건 모두 네 번째 문자열이 해당 태스크의 사용자 프롬프트와 정확히 일치한다.

### queries-s4-t153

호출 ID `exec-fac46e88-933b-446a-88f5-01d2add2a26f`, 원시 sequence `89`, 상태 `failed`.

```json
[
  "Update the backend container image tag and Uvicorn worker count for staging while preserving production.",
  "Inspect deployment configuration and adjust staging environment variables before deployment.",
  "The known stack is Docker Compose and Uvicorn, targeting compose.deploy.yml and .env settings; the image version and worker count are unspecified.",
  "백엔드 이미지를 새 버전으로 올리면서 staging 환경에 먼저 배포하고 싶은데, `compose.deploy.yml`에 backend 이미지 태그랑 uvicorn worker 수 정리해주고 staging은 `ENVIRONMENT=staging`으로 뜨게 `.env` 쪽 설정도 맞춰줘. prod는 아직 건드리지 말아줘."
]
```

### queries-s4-t033

호출 ID `exec-7cee29b7-f6e2-48fe-b857-e2ad934591c9`, 원시 sequence `74`, 상태 `failed`.

```json
[
  "Fix frontend API error handling so permission 403 responses show error toasts instead of logging users out.",
  "Make a minimal change that logs out only on 401 or a 403 with detail Could not validate credentials, without new packages or generated client edits.",
  "The known targets are TypeScript TSX frontend/src/main.tsx and frontend/src/components/UserSettings/DeleteConfirmation.tsx, with Python backend/app/api/deps.py providing authentication context; other stack details are unspecified.",
  "In the frontend, any 403 from the API logs the user out. `handleApiError` in `frontend/src/main.tsx` clears `access_token` and redirects to `/login` for both 401 and 403. Ordinary permission errors therefore act like an expired session. One example is \"Not enough permissions\" from the items routes. Another is a superuser hitting Delete in `frontend/src/components/UserSettings/DeleteConfirmation.tsx`, which gets \"Super users are not allowed to delete themselves\". In both cases the user is kicked to the login page instead of seeing the error toast. The backend's real invalid-token case is the 403 with detail \"Could not validate credentials\" raised in `get_current_user` (`backend/app/api/deps.py`). Keep the diff minimal: only log out on 401 or on that specific credentials 403, and let every other 403 fall through to the existing `handleError` toast. Add no new packages, and don't touch the generated client in `frontend/src/client`."
]
```

### queries-s4-t342

호출 ID `exec-741e14a0-05df-4451-8039-8050e6bf2a8c`, 원시 sequence `76`, 상태 `failed`.

```json
[
  "Add a dry-run flag for first-superuser initialization and print email, superuser value, and existing or proposed status.",
  "Make a minimal Python change by threading the flag through main and init into init_db and skipping crud.create_user.",
  "The targets are backend/app/initial_data.py and backend/app/core/db.py; other stack details are unspecified.",
  "Add a `--dry-run` flag to the `backend/app/initial_data.py` script so ops can see whether the first superuser would be created without writing to the `user` table. It should print a summary table of the email, the `is_superuser` value and the old/new status (already exists / would be created). Keep the diff minimal: just thread the flag through the existing `main()` / `init()` into `init_db()` in `backend/app/core/db.py`, and skip the `crud.create_user` call."
]
```

### queries-s4-t280

호출 ID `exec-128e1f34-ef5c-4042-ab36-aebefb0109c1`, 원시 sequence `67`, 상태 `failed`.

```json
[
  "Add a skeleton loader to the sidebar user block to prevent flickering while the current user loads.",
  "Update the user component to show a loading skeleton until current user data is ready.",
  "The target file is frontend/src/components/Sidebar/User.tsx; the frontend framework and styling stack are unspecified.",
  "add skeleton loader to the user block in frontend/src/components/Sidebar/User.tsx, flickers on load while current user loads"
]
```

## 실행 조건과 인증

- skillfetch 고정 커밋: `14d2020f1275e10a272eb46575c9bd6d4a2182e4`. 로컬 `git archive`로 추출한 소스를 `PYTHONPATH`에 고정했고 패키지를 원격 설치하지 않았다.
- fastapi `s5`: `2b38acb4586092ef0318bc6a8ab36436ba8fc09a`.
- nextjs `s5`: `2a1df71575f0c45a0f7a999bf77f4286d81e8706`. 두 브랜치는 다른 e2e 세션이 생성할 때까지 기다린 뒤 사용했으며 직접 생성하지 않았다.
- 태스크 입력: 실행 시점의 `stage5/tasks.jsonl`, SHA-256 `d8822df5b8afeb587fc209218ca3f81fbe9ec3153acb66348c3f6a132306e572`. 고정본을 두 실행 디렉터리에 보존했고 현재 Stage 5 FROZEN의 tasks 해시와도 일치한다.
- 매 태스크마다 새 detached worktree와 새 Codex thread를 사용했다. 실제 제출한 사용자 입력은 `prompt` 필드 원문뿐이며, offline_queries/offline_skills/offline_class나 oracle을 측정 모델에 전달하지 않았다.
- AGENTS.md에는 고정 커밋 라우터의 1–4단계만 Codex용으로 옮겼다. R-c의 영어 세 질의 + 요청 원문인 네 번째 질의를 유지했다. Codex 지침 읽기를 허용하고 ToolSearch 가정을 제거했다. 5–8단계를 추가해 로드를 더 강하게 유도하지 않았다. [실제 AGENTS.md](codex-e2e-runs/20261023-subscription-14d2020/AGENTS.input.md).
- MCP는 실제 상태 목록으로 skillfetch 하나임을 확인했고, 19개 모두 `connected`를 확인한 다음 프롬프트를 전송했다. 제어 스크립트가 MCP 도구를 대신 호출한 횟수는 0이다.
- 인증은 각 준비 세션의 `codex login status`와 app-server `account/read`를 확인했다. 모두 `chatgpt` / `pro`였고 `forced_login_method = "chatgpt"`로 API 키 인증을 배제했다. API 키 환경변수는 값을 비우는 방식이 아니라 프로세스 환경에 아예 넘기지 않았다. `OPENAI_API_KEY`, `CODEX_API_KEY`, `AZURE_OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY` 및 AWS 키 변수가 없는 것을 기록했다.
- 별도의 API 키 기반 추론·라벨링 호출은 하지 않았다. Codex 기본 추론은 사용자 허용 범위의 ChatGPT 구독 인증으로 실행했다. 인증 파일 내용은 보고서에 기록하지 않았으며 세션용 인증 symlink는 종료 후 제거했다.
- 글로벌 설정 대신 세션별 HOME/CODEX_HOME을 분리했다. 고정 입력 config 해시는 두 실행 묶음에서 같았다. Codex가 각 세션 config 끝에 template repo의 `trust_level = "trusted"`만 추가했으며 원래 설정 변경·삭제는 없었다. 최종 config 파일 해시와 고정 입력 config 해시를 같은 것으로 주장하지 않는다.
- 실행 설정: 동시 4, 세션 timeout 2700초, 셸 작업의 네트워크 차단. Stage 4의 16 assistant-message 제한은 적용하지 않았다. Codex의 모델 응답 회차와 같은 단위로 검증되지 않았기 때문이다. 실제 19개는 모두 timeout 전에 종료됐다. MCP의 공개 소스 본문 다운로드는 API 키를 사용하지 않지만, 이번에는 load 호출 자체가 없었다.
- 실제 측정 시간: `2026-10-23T13:53:29.690Z`부터 `2026-10-23T14:06:46.886Z`까지(UTC).

## 초기 연결 검사 실패와 정리

최초 실행기에는 MCP 상태가 `starting`일 때 기다리지 않고 거절하는 문제가 있었다. 이 때문에 7개 준비 세션이 프롬프트 전송 전에 종료됐다. 원시 `turn/start`가 0회임을 확인한 뒤, 연결을 최대 90초 기다리도록 실행기만 수정했다. 원래의 source/index/config/AGENTS/모델/브랜치 SHA를 그대로 유지한 상태에서 이 7개에 프롬프트를 처음 전송했다. 이미 제출된 태스크는 재실행하지 않았다.

최초 묶음의 실제 실행 12개 + 미제출 태스크의 첫 실행 7개 = 19개다. 각 ID의 원시 `turn/start`는 정확히 1회, 고유 thread와 turn ID는 각각 19개, 사용자 프롬프트 원문 일치는 19/19다. 준비 실패까지 포함해 만든 worktree 26개와 전용 worktree 루트 2개는 모두 삭제했고 git worktree 등록에서도 제거했다. 다른 실험의 worktree에는 손대지 않았다.

승인 차단을 발견한 후에는 같은 표본 안에서 정책을 바꾸거나 이미 실행한 태스크를 반복하지 않았다. 따라서 **19/19는 호출 의사의 발화율이며 성공적인 skillfetch 사용률이 아니다.** 승인 설정을 달리했을 때 검색·로드가 얼마나 이루어지는지는 이 결과로 알 수 없다.

## 검증 자료

- [19개 통합 관찰 JSON: 호출·queries·로드 ID·종료 상태·첫 회차 근거](codex-e2e-runs/cohort-observations.json)
- [전수 검증: 각 1회·인증·API 키 부재·MCP 격리·정리](codex-e2e-runs/verification.json)
- [최초 실행 manifest: 실제 12개 + 미제출 7개](codex-e2e-runs/20261023-subscription-14d2020/manifest.json)
- [미제출 태스크 첫 실행 manifest: 실제 7개](codex-e2e-runs/20261023-subscription-14d2020-unsubmitted/manifest.json)
- [고정 config](codex-e2e-runs/20261023-subscription-14d2020/config.input.toml), [소스·인덱스 파일 해시](codex-e2e-runs/20261023-subscription-14d2020/source-preflight.json)
- [실행기](codex-e2e-runner.cjs), [추출기](codex-e2e-extract.cjs). 각 세션 폴더에는 원시 transcript, 인증 상태, MCP 목록, thread/start, turn/start·completed와 정리 기록이 있다.
