# 6b 파일럿 3세션 (d1-landing, 태그 p0; 판정에서 제외)

| 항목 | A | C0 | Cb |
|---|---|---|---|
| init mcp_servers | [] | ['skillfetch'] | ['skillfetch'] |
| init plugins | ['agents-md', 'telemetry'] | ['agents-md', 'telemetry'] | ['agents-md', 'telemetry'] |
| init skills | 18: deep-research, design, design-sync, dataviz, update-config, verify, debug, code-review, simplify, batch, fewer-permission-prompts, doctor, loop, schedule, claude-api, workflow-authoring, run, run-skill-generator | 19: skillfetch-router, deep-research, design, design-sync, dataviz, update-config, verify, debug, code-review, simplify, batch, fewer-permission-prompts, doctor, loop, schedule, claude-api, workflow-authoring, run, run-skill-generator | 19: skillfetch-router, deep-research, design, design-sync, dataviz, update-config, verify, debug, code-review, simplify, batch, fewer-permission-prompts, doctor, loop, schedule, claude-api, workflow-authoring, run, run-skill-generator |
| 훅 이벤트 | [] | [] | [] |
| 발화 | False | True | True |
| skillfetch 호출 | [] | ['mcp__skillfetch__profile_repo', 'mcp__skillfetch__search_skills', 'mcp__skillfetch__resolve_set', 'mcp__skillfetch__load_skills'] | ['mcp__skillfetch__profile_repo', 'mcp__skillfetch__search_skills', 'mcp__skillfetch__resolve_set', 'mcp__skillfetch__load_skills'] |
| 세션 문맥에 S-0 4단계 문구 | False | True | False |
| 세션 문맥에 S-b′ 문장 | False | False | True |
| 결과 | success | success | success |
| 턴 | 7 | 16 | 25 |
| 비용 $ | 0.2650476 | 0.6981406 | 0.9256510000000001 |
| 입력 토큰 | 183679 | 567883 | 960970 |
| 세션 시간 s | 63.0 | 134.8 | 177.7 |
| 체크 통과 | True | True | True |
| 실패한 체크 항목 | [] | [] | [] |

## 격리 확인 결과와 고친 것

- **첫 파일럿 A에서 `skills`에 `skillfetch-router`가 있었다**(19개).
  - 원인: `repos/nextjs`·`repos/fastapi`의 메인 체크아웃이 브랜치 `e2e-baseline`에 있었고, 그 브랜치가 `.claude/skills/skillfetch-router`(2026-10-22, 옛 라우터)를 추적한다. Claude Code는 git worktree에서 메인 체크아웃의 프로젝트 skill도 읽는다.
  - A에는 MCP 서버가 없어 발화할 수 없었고, 발화하지도 않았다.
  - 1b·1단계의 A 세션 3개를 샘플로 확인했더니 그때는 `skills`에 라우터가 없었다.
- **고친 것**: 두 레포의 메인 체크아웃을 `s6b-a`(업스트림)로 바꿨다. 되돌릴 수 있는 변경이고, 세션 worktree의 base는 바꾸지 않았다.
  - 다시 돌린 파일럿 A의 `skills`는 내장 18개이고, 라우터는 없다. 위 표의 A 열이 다시 돌린 세션이다. 첫 세션은 `runs/_superseded/`에 두었다.
  - C0·Cb 파일럿은 메인 체크아웃을 바꾸기 전에 돌았다. 세션 문맥에 각자 worktree의 라우터 문구만 있었으므로(S-0은 C0에만, S-b′은 Cb에만) 다시 돌리지 않았다.
- **격리 기준 통과**:
  - `mcp_servers`: A 0개, C0·Cb skillfetch 1개
  - `plugins`: 내장 2개
  - 사용자 skill: 없음
  - 훅 이벤트: 0
  - 로드된 라우터 본문: 조건과 맞음
- 본 실행은 격리 확인 통과에 따라 바로 시작한다(승인 조건).
