# skillfetch의 Codex 이식성 조사

조사일: 2026-10-23. 로컬 설치 `codex-cli 0.164.0`, macOS arm64 기준. 지정한 router `SKILL.md`와 `README.md`를 전체 읽고 서버 구현·설치된 Codex CLI 도움말·생성된 app-server 프로토콜 스키마를 확인했다. 인터넷 문서를 조회하지 않았다. 레포 파일과 사용자의 실제 Codex 설정은 수정하지 않았다.

**결론: MCP 서버 자체는 Codex에서 작동한다. 실제 Codex app-server에 `skillfetch serve`를 stdio MCP로 연결했고, Codex의 MCP 클라이언트를 통해 `search_skills`를 한 번 호출해 5개 결과를 받았다. `isError: false`였다.** Claude Code에 맞춘 라우터 안내는 그대로 옮기면 안 된다. 특히 `ToolSearch`와 `.claude/skills` 가정, AGENTS.md를 읽기 전 검색하라는 해석을 수정해야 한다. AGENTS.md에 라우팅 절차를 넣는 것은 가능하며, 임시 AGENTS.md가 실제 Codex 모델 입력에 포함되는 것까지 확인했다. 자동 발동률과 전체 작업 품질은 이번 시험의 측정 대상이 아니다.

## 1. Codex의 MCP 설정 방법

`skillfetch serve`는 HTTP 서버가 아니라 stdio 서버다. 따라서 Codex의 `--url` 옵션이 아니라 실행 명령과 인자를 등록한다. 구현 근거: [server.py:89](<skillfetch>/src/skillfetch/mcp/server.py:89). CLI에는 `serve --index PATH`가 있다([cli.py:113](<skillfetch>/src/skillfetch/cli.py:113)).

이미 설치된 로컬 실행 파일과 인덱스를 사용하는 명령은 다음과 같다. 이 경로는 이번 머신의 실제 경로이며 다른 머신에서는 바꿔야 한다.

```sh
codex mcp add skillfetch -- \
  <skillfetch>/.venv/bin/skillfetch serve \
  --index ~/.skillfetch/index
codex mcp get skillfetch --json
codex mcp list --json
```

동등한 TOML 설정:

```toml
[mcp_servers.skillfetch]
command = "<skillfetch>/.venv/bin/skillfetch"
args = ["serve", "--index", "~/.skillfetch/index"]
```

Codex CLI의 기본 설정 파일은 `~/.codex/config.toml`이며 `CODEX_HOME`으로 설정 루트를 바꿀 수 있다. 이번에는 실제 설정을 건드리지 않도록 아래처럼 격리했다. `Added global MCP server 'skillfetch'.`는 **격리된 CODEX_HOME 안에 등록했다**는 뜻이다.

```sh
CODEX_HOME=/tmp/skillfetch-codex-portability/home \
  codex mcp add skillfetch -- \
  <skillfetch>/.venv/bin/skillfetch serve \
  --index ~/.skillfetch/index
```

[CLI 도움말](codex-portability-evidence/codex-mcp-add-help.txt), [실제 저장된 config](codex-portability-evidence/isolated-config.toml), [실제 `mcp get` 출력](codex-portability-evidence/codex-mcp-get.json)에 명령 형식과 등록 결과가 남아 있다. 등록만으로 연결 검증이 끝나는 것은 아니다. 새 Codex 세션에서 서버가 시작되어 도구가 노출되는지 확인해야 한다. 이번 시험은 아래 5절의 `runtimeStatus: connected`와 실제 검색 응답으로 이를 확인했다.

README의 `uvx --from git+https://...` 방식도 Codex의 command/args 형식에 넣을 수 있지만, 최초 패키지 확보나 `skillfetch sync`는 다운로드를 요구한다. 이번에는 이미 존재하는 venv와 인덱스를 사용해 설치·sync를 실행하지 않았다. 인덱스가 없으면 먼저 확보해야 하며, 갱신 후에는 서버를 다시 시작해야 한다([README 스냅샷:57](<e2e>/codex-portability-evidence/README.snapshot.md:57)).

## 2. 그대로 옮겼을 때 안 되거나 보장되지 않는 부분

| 문제 | 근거와 영향 | Codex에서의 처리 |
|---|---|---|
| Claude의 MCP 등록 명령 | README 54행은 `claude mcp add`다. Codex 설정을 만들지 않는다. | `codex mcp add NAME -- COMMAND ARGS` 또는 위 TOML을 사용한다. |
| `ToolSearch` 하드코딩 | [router:36–37](<skillfetch>/assets/router-skill/SKILL.md:36)는 도구가 안 보이면 반드시 서버 시작 중이라고 보고 `ToolSearch(+skillfetch)`를 지시한다. 이 도구 이름·탐색 방식은 모든 Codex 호스트의 계약이 아니다. 미설정·실패·비활성화도 가능하다. | 현재 Codex 호스트가 실제 제공하는 도구 목록/탐색 수단을 사용한다. 없다면 연결 실패를 보고한다. 대기·재검색을 무조건 반복하지 않는다. |
| `.claude/skills` 전용 가정 | [router:22–23](<skillfetch>/assets/router-skill/SKILL.md:22) 예시와 README 설치 관례가 Claude 중심이다. | Codex가 실제 발견한 로컬 스킬의 절대 경로를 사용한다. 호스트가 보유한 스킬 목록과 skillfetch MCP 등록은 별개다. |
| MCP 등록이 라우터 설치를 대신하지 않음 | [server.py:18–23](<skillfetch>/src/skillfetch/mcp/server.py:18)의 서버 instructions는 한 문장으로 재진술하라고 한다. router 30–40행의 최대 세 문장·`queries` 배열·명시된 작업 방식과 세부적으로 다르다. | AGENTS.md 또는 Codex 네이티브 스킬에 전체 절차를 제공한다. MCP 서버를 연결했다는 사실만으로 원래 8단계 절차를 따른다고 주장하지 않는다. |
| “코드베이스를 읽기 전에”의 충돌 | Codex는 적용되는 AGENTS.md를 작업 지침으로 읽어야 한다. 이를 금지하면 라우터 규칙을 읽는 행위 자체와 충돌한다. 사용자 요청에 없는 스택/파일도 사전 탐색 없이 알 수 없다. | 적용 지침을 먼저 읽는 것을 허용하고, 작업 소스를 탐색하기 전에 이미 알려진 정보만 검색 질의로 만든다. 1단계 수정안은 4절. |
| `path:`는 AGENTS.md를 직접 받지 않음 | [session.py:133–155](<skillfetch>/src/skillfetch/mcp/session.py:133)는 디렉터리와 그 아래 `SKILL.md`를 요구한다. 추출 캐시가 없으면 “included without conflict checks” 메모를 남긴다. | `path:/.../AGENTS.md`를 pin하지 않는다. 실제 로컬 스킬 디렉터리만 pin한다. AGENTS.md로 옮긴 라우터는 호스트 지침으로 유지한다. |
| 호스트 지침까지 충돌 검사하지 않음 | `resolve_set`은 받은 스킬들의 추출 constraints를 비교한다([session.py:176](<skillfetch>/src/skillfetch/mcp/session.py:176)). Codex의 AGENTS.md, 시스템·개발자 지침을 자동 입력으로 포함하지 않는다. | “conflict-free”를 모든 세션 지침에 대한 보장으로 해석하지 않는다. 로드된 내용은 적용되는 상위 지침·사용자 요구를 따라 사용한다. |
| 전 과정 오프라인은 아님 | 검색은 로컬 BM25/RRF다([search.py:72](<skillfetch>/src/skillfetch/index/search.py:72)). 반면 `load_skills`는 유효한 캐시가 없으면 pinned source에서 파일을 가져온다([fetch.py:125–134](<skillfetch>/src/skillfetch/index/fetch.py:125)). | 검색 한 번의 성공과 원격 스킬 본문 로드 성공을 구분한다. 네트워크가 금지된 세션에서는 본문 캐시가 없는 스킬을 로드할 수 없다. |
| 로드한 개별 스킬의 Codex 호환성은 별개 | [session.py:247](<skillfetch>/src/skillfetch/mcp/session.py:247)는 스킬 본문을 섹션으로 이어서 반환할 뿐, Claude 전용 도구명·명령·스크립트 의존성을 Codex용으로 번역하지 않는다. | 각 스킬이 요구하는 도구와 실행 파일이 현재 Codex 환경에 있는지 확인한다. MCP 검색·로드 성공을 모든 본문의 실행 가능성으로 확대하지 않는다. |
| 태스크 종료 시 지침 제거·격리 미구현 | README 150–151행은 현재 컨텍스트에 본문을 넣고 진정한 격리용 subagent runner는 없다고 명시한다. | AGENTS.md로 옮겨도 스킬 본문이 태스크 종료 후 자동 제거되거나 다음 작업에 영향을 주지 않는다는 보장은 생기지 않는다. |
| Claude 실측을 Codex 성능으로 일반화 불가 | README 47행과 117행의 실행 근거는 Claude Code다. | 이번 결과는 Codex 연결·검색 호환성의 한 건 증거다. 자동 발동, 선택 품질, 비용, 실제 코딩 성과는 Codex에서 별도로 측정해야 한다. |

`search_skills`, `profile_repo`, `resolve_set`, `load_skills`의 JSON 도구 스키마에는 이번 Codex와의 프로토콜 불일치가 관찰되지 않았다. 네 도구가 모두 목록에 표시되었다. 다만 목록에 있다는 사실만으로 뒤의 세 도구 실행까지 검증한 것은 아니다.

## 3. 라우터를 AGENTS.md에 넣을 수 있는가

**가능하다.** 라우터의 When/Steps/Rules 본문을 프로젝트의 적용 범위에 맞는 AGENTS.md에 지침으로 넣을 수 있다. 이는 `SKILL.md`를 네이티브 스킬로 등록하는 것과 다르다. YAML `name`/`description` frontmatter를 AGENTS.md에 붙인다고 스킬 탐색·메타데이터 트리거가 생기는 것은 아니다. 일반 지침으로서 언제 호출하고 언제 생략할지를 본문에 명시해야 한다.

로컬 검증에서는 레포 밖 `/tmp/skillfetch-codex-portability/work/AGENTS.md`에 `PORTABILITY_ROUTER_SENTINEL_20261023`과 Codex용 라우팅 안내를 작성했다. 그 cwd에서 네트워크를 차단한 상태로 다음 명령을 실행했다.

```sh
CODEX_HOME=/tmp/skillfetch-codex-portability/home \
  /usr/bin/sandbox-exec \
  -f /tmp/skillfetch-codex-portability/network-deny.sb \
  /opt/homebrew/bin/codex debug prompt-input \
  '설정 폼의 키보드 탐색을 개선해 줘.'
```

결과는 유효한 JSON 배열이었고 sentinel이 정확히 1회 들어 있었다. 해당 입력의 `role`은 `user`, 내부 provenance는 `agents_md`였다. [실제 입력 발췌](codex-portability-evidence/agents-prompt-evidence.json), [시험용 AGENTS.md](codex-portability-evidence/AGENTS.probe.md), [명령 도움말](codex-portability-evidence/codex-prompt-input-help.txt)을 보존했다. 시험용 AGENTS.md는 입력 포함 여부를 확인하기 위한 축약 예시이며 배포용 전체 라우터가 아니다. 특히 실제 이식안에서는 원본 When의 “bug fix, even when you expect the fix to be one line” 조건과 예외 범위를 함께 보존해야 한다. 이 시험은 **Codex가 AGENTS.md 내용을 모델 입력에 넣음**을 입증하며, 모델이 매번 지침을 실행한다는 증거는 아니다. CODEX_HOME은 격리했으나 HOME은 유지했으므로 사용자 환경 전체를 비운 무설치 코호트 시험도 아니다.

실제로 옮길 때는 기존 AGENTS.md를 덮어쓰지 말고 라우팅 섹션으로 병합해야 한다. 라우터를 적용하려는 프로젝트 범위, 다른 지침과의 우선순위, 명시적으로 사용자가 지정한 스킬을 보존하는 규칙을 유지한다. 이번에는 사용자 요청에 따라 레포 AGENTS.md를 생성하거나 수정하지 않았다.

## 4. 1단계 문구 수정안

핵심은 “영어로 답변하라”가 아니라 “검색 도구에 전달할 질의를 영어로 만들라”이다. AGENTS.md 읽기와 `profile_repo`의 manifest 읽기를 금지하지 않고, 모르는 스택·파일을 지어내지 않게 구분해야 한다. 아래 문구로 기존 1단계를 교체하면 된다. 실제 파일에는 적용하지 않았다.

```markdown
1. After loading the applicable AGENTS.md instructions, and before exploring
   source files for this task, prepare 1–3 short English search sentences from
   the user's request and context already available:
   (a) what to build or fix, using concrete domain nouns;
   (b) how the user explicitly asked you to work, if specified;
   (c) the stack and target files, only when already known.
   Omit unknown details instead of guessing or reading source merely to fill
   them in. Pass these sentences as the `queries` array to `search_skills` in
   step 4. Keep user-facing communication in the user's language.
   This does not prevent loading applicable instructions or calling
   `profile_repo` to read manifests in step 3.
```

예: “Go 상품 API의 ETag를 수정해 줘. 테스트부터 작성해.”라는 요청에서 저장소 파일 경로가 아직 알려지지 않았다면:

```json
{
  "queries": [
    "Fix conditional GET and ETag handling for the product catalog API.",
    "Use test-driven development: write failing tests first.",
    "Go HTTP API."
  ]
}
```

`internal/catalog/` 같은 경로를 임의로 추가하지 않는다. `profile_repo` 결과는 질의 문장에 섞지 않고 별도 `profile` 필드로 전달한다([server.py:55–59](<skillfetch>/src/skillfetch/mcp/server.py:55)).

1단계만 고쳐도 2단계의 Claude 전용 의존성은 남는다. 함께 필요한 2단계 대체 문구:

```markdown
2. Use the skillfetch MCP tools exposed by this Codex session. If the host
   provides tool discovery, use that supported mechanism to find skillfetch.
   If the tools remain unavailable, report the MCP connection problem and
   continue under the task's existing instructions. Do not assume a tool named
   ToolSearch exists or that missing tools always mean the server is starting.
```

7단계에는 “Follow the returned instructions subject to the user's request and applicable higher-priority instructions.”를 권한다. 호스트 지침과 로드된 외부 본문 사이의 우선순위를 오해하지 않게 하는 변경이다. 원래 3–8단계의 profile·pinned_ids·resolve·budget·load 오류 보고 절차는 별도로 유지한다.

## 5. 실제 Codex MCP 호출 기록

### 실행 환경과 경로

- Codex 실행 파일: `/opt/homebrew/bin/codex`, `codex-cli 0.164.0`.
- 서버: `<skillfetch>/.venv/bin/skillfetch serve --index ~/.skillfetch/index`.
- MCP가 보고한 서버 이름/버전: `skillfetch` / `0.0.1`.
- 로컬 인덱스: built_at `2026-10-22T06:15:43Z`; A 19, B 1,470, C 235, 합계 1,724. 이 manifest의 extraction model 표기는 이전 인덱스 생성 이력이며 이번 실행에서 그 모델을 호출했다는 뜻이 아니다.
- 격리 CODEX_HOME: `/tmp/skillfetch-codex-portability/home`; 시험 cwd: `/tmp/skillfetch-codex-portability/work`.
- 실행 시각: 2026-10-23 07:49:19–20 UTC, 한국 시각 16:49:19–20.
- 네트워크 정책: macOS `sandbox-exec` 프로파일 `(version 1) (allow default) (deny network*)`; 프로세스와 그 하위 MCP 서버에 적용.

실행 명령:

```sh
CODEX_HOME=/tmp/skillfetch-codex-portability/home \
  /usr/bin/sandbox-exec \
  -f /tmp/skillfetch-codex-portability/network-deny.sb \
  /opt/homebrew/bin/codex app-server --stdio
```

로컬 제어 스크립트가 Codex app-server의 JSON-RPC를 사용했다. `codex app-server generate-json-schema --experimental`로 설치된 바이너리의 프로토콜을 생성하고 `mcpServer/tool/call` 지원을 확인했다. MCP 서버를 Python 클라이언트로 직접 호출한 결과를 Codex 연결이라고 간주한 것이 아니다. 실제 흐름은 **시험 스크립트 → Codex app-server → Codex MCP 클라이언트 → skillfetch stdio 서버**다.

송신한 메서드는 `initialize`, `initialized`, `thread/start`, `mcpServerStatus/list`, `mcpServer/tool/call`뿐이다. `turn/start`는 보내지 않았으며 새로운 모델 추론을 요청하지 않았다. thread ID는 `01a167bc-5aa9-7a70-89b3-03d020fc5623`이다.

연결 확인 결과:

```json
{
  "name": "skillfetch",
  "runtimeStatus": "connected",
  "toolsError": null,
  "authStatus": "unsupported",
  "tools": ["search_skills", "load_skills", "profile_repo", "resolve_set"]
}
```

위 JSON은 전체 응답에서 핵심 필드를 발췌해 tools 키를 이름 배열로 축약한 것이다. `authStatus: unsupported`는 이 로컬 stdio 서버가 OAuth 인증 방식을 제공하지 않는다는 상태이며 연결 실패가 아니다. 원본의 tool schema 전체는 [mcp-status.json](codex-portability-evidence/mcp-status.json)에 있다.

### 검색 요청 1회

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "mcpServer/tool/call",
  "params": {
    "threadId": "01a167bc-5aa9-7a70-89b3-03d020fc5623",
    "server": "skillfetch",
    "tool": "search_skills",
    "arguments": {
      "queries": [
        "Add keyboard navigation and accessible focus states to a React settings form.",
        "React and TypeScript."
      ],
      "k": 5
    }
  }
}
```

`search_skills`를 정확히 한 번 실행했다. 요청 자체를 간단히 검증하기 위해 `k: 5`를 명시했고 profile은 생략했다. 원래 라우터의 기본값 50개 전수 읽기나 `profile_repo → resolve_set → load_skills` 전체 절차를 재현한 시험은 아니다.

### 검색 결과

Codex 응답 `result.isError`는 **false**, `structuredContent.results` 길이는 **5**였다. 같은 결과가 MCP text content에도 JSON으로 들어 있었다.

| 순서 | title | id | tier | token_estimate |
|---:|---|---|---|---:|
| 1 | accessibility-compliance | `uasl/accessibility-compliance@696d2b4119ed` | B | 2962 |
| 2 | artisan | `uasl/artisan@1e09f38ffcab` | B | 2908 |
| 3 | web-artifacts-builder | `anthropics-skills/web-artifacts-builder@9c350d2f5f13` | A | 768 |
| 4 | frontend-patterns | `uasl/frontend-patterns@8f659ce2a0bd` | B | 3849 |
| 5 | next-upgrade | `uasl/next-upgrade@df465f7770a5` | B | 509 |

첫 결과는 키보드·접근성 요구에 맞는 지침이다. 5위처럼 작업과 직접 맞지 않는 후보도 있으므로 이 한 번의 검색 성공은 후보 선택 품질의 검증이 아니다. 호스트 모델의 재선별이 여전히 필요하다.

원본 증거: [전체 JSON-RPC transcript](codex-portability-evidence/transcript.jsonl), [검색 응답](codex-portability-evidence/search-result.json), [실행 스크립트](codex-portability-evidence/probe.cjs), [launch 설정](codex-portability-evidence/launch.json), [네트워크 차단 프로파일](codex-portability-evidence/network-deny.sb), [설치 바이너리의 호출 스키마](codex-portability-evidence/McpServerToolCallParams.json).

### 외부 API 제한과 로그의 정확한 해석

검색 구현은 로컬 인덱스의 BM25/RRF이며 embedding API나 모델 API를 호출하지 않는다. 이번에는 `load_skills`·sync·ingest도 실행하지 않았다. Codex와 서버는 네트워크 차단 프로파일 아래 실행했으며 외부 모델 호출을 요청하는 `turn/start`도 보내지 않았다.

다만 **Codex 시작 중 자체 Responses WebSocket 연결 시도 1건이 로그에 나타났고 주소 해석 단계에서 실패했다.** 로그는 `failed to connect to websocket ... failed to lookup address information ... wss://api.openai.com/v1/responses`이다. 이를 숨기고 “네트워크 시도 자체가 전혀 없었다”고 주장하지 않는다. 외부 통신은 샌드박스로 차단했고, 모델 응답 없이 MCP 연결과 검색을 완료했다. 정확한 로그는 [stderr.log](codex-portability-evidence/stderr.log)에 보존했다. 별도 AGENTS prompt 렌더링 시험의 stderr는 비어 있다.

## 6. 확인 범위와 재현 시 주의점

| 항목 | 판정 |
|---|---|
| Codex stdio MCP 설정 저장 | 확인: 격리 config와 `mcp get` |
| Codex가 실제 skillfetch 프로세스를 시작하고 도구 4개 발견 | 확인: ready 알림, connected 상태 |
| Codex MCP 클라이언트 경유 `search_skills` 1회 | 확인: 5개 결과, isError false |
| AGENTS.md가 Codex 모델 입력에 포함 | 확인: sentinel 1회, agents_md provenance |
| 모델이 AGENTS 라우터를 자동 발동 | 미측정: 모델 turn 없음 |
| profile/resolve/load 전체 실행 | 미시험: 검색 한 번이 요청 범위 |
| 본문 캐시 누락 시 네트워크 로드 | 구현으로 확인, 이번 실행에서는 미시험 |
| Codex 작업 결과 개선·비용·발동률 | 미측정, Claude 실측에서 추론하지 않음 |
| Codex App의 모든 UI·배포 버전 | 미시험: 설치된 CLI/app-server 0.164.0 기준 |

호스트가 제공하는 실험적 `mcpServer/tool/call`은 이번 버전에서 직접 확인한 시험 수단이다. 일반 사용자는 이 내부 프로토콜을 구현할 필요 없이 stdio 서버를 등록하고 Codex 세션의 도구로 사용하면 된다. 향후 버전에서 시험 API가 바뀔 가능성을 MCP 서버 자체의 비호환성과 혼동하지 않는다.

조사 중 다른 세션의 README 변경을 관찰했다. 최초 읽기 이후 real-repo 비율 문구가 수정되어 최신 파일을 다시 확인하고 스냅샷을 보존했다. 이 작업은 레포 파일을 수정하지 않았다. 조사 시작 HEAD는 `f9d2546bf6bbe3947c04de133cda73a2edc0c318`, 종료 시 다른 세션의 커밋 후 HEAD는 `67de4e13b46db47b41a8b861a7d52a5523638dfe`였다. 최초 README hash는 `346ee0aa8b61a7bece06f0b282b8d1a43fcd4afe4c6624a4af1792f54f4c3233`였고, 아래는 다시 읽고 보존한 최종 스냅샷 기준이다. 기준 SHA-256:

- router `SKILL.md`: `53b2a6df7c3ba762bd73f3245ac5a60864b95e273690e71b2ab3ed2ac60acb35`
- README 스냅샷: `615cee570fbb2c450fed821e3020674de20b89a9f1acf5dbcbe70d47f8e397e9`

[읽은 router 사본](codex-portability-evidence/router-skill.snapshot.md), [읽은 README 사본](codex-portability-evidence/README.snapshot.md)을 함께 보존했다. 다른 라벨 파일은 열지 않았다.
