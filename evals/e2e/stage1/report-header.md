실행 2026-10-22 KST 17:16:45–18:04:25, 110세션 (전문가 스킬 있는 15태스크 × A/B/C × 2회 = 90, 없는 5태스크 × A/C × 2회 = 20). 순서는 고정 시드(20261022)로 섞은 큐 `runs/_queue.txt`, 동시 4. 숫자는 `scripts/extract_s1.py`, 표는 `scripts/report_s1.py`.

## 0. 설정

| 항목 | 값 |
|---|---|
| 모델/CLI | Claude Code 2.1.280, 기본 모델(`claude-opus-5-5[1m]`), 구독 플랜. `claude -p "<prompt>" --output-format stream-json --verbose --max-turns 25 --allowedTools "Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*" --debug-file …` (전 조건 동일; B만 `--append-system-prompt-file` 추가) |
| 트리 | A·B: 업스트림 (`repos/fastapi` `b1125d88`, `repos/nextjs` `76de3ce2`), 브랜치 `s1-a`. C: `s1-c` = 업스트림 + skillfetch `main@96f0f3b`의 `assets/router-skill/SKILL.md`(59줄, PR #19 머지본) + `claude mcp add -s project` 로 만든 `.mcp.json` (fastapi `00d0b3be`, nextjs `e59cccf6`) |
| skillfetch | 서버 `uvx --from git+https://github.com/hyunlord/skillfetch` HEAD `96f0f3b` (시작·종료 동일). 인덱스 `~/.skillfetch/index` `built_at` 2026-10-22T06:15:43Z — 110세션 전부 동일 (meta `index_built_at`, 파일 mtime 15:36:26 이후 변화 없음) |
| B 입력 | `stage1/expert-content/<id>.md` = 전문가 id를 `resolve_set(auto_ids=[], pinned_ids=…)` → `load_skills` 한 `content` 그대로 (15세트, errors/excluded/warnings 0) |
| 레포 내장 스킬 | fastapi 레포의 `.claude/skills/{library-skills, fastapi, sqlmodel}` 전 조건 유지 |
| 체크 | `stage1/checks/` (세션 전 작성·검증·동결, `FROZEN.sha256` 53파일 실행 전후 일치). 각 세션 종료 후 하네스가 실행. 시각 판정 항목은 `pass: null`로 자동 판정에서 제외 |
| 스크린샷 | UI 태스크(s1-fa-03, s1-nx-01, s1-nx-03, s1-nx-04, s1-nx-05)의 PNG만 `screens-blind/<task>/<code>/`에 복사, 조건 매핑은 `screens-key.jsonl` (블라인드 폴더 밖). 시각 판정은 수행하지 않음 |
| 환경 | 사용자 전역 `~/.claude`(CLAUDE.md, 플러그인, 훅) 상속 — 0단계와 동일. 태스크별 Postgres DB(:55432), fastapi 세션 env에 `DATABASE_URL`만 주입. s1-fa-03은 세션 전 `bun install --frozen-lockfile` |
| 도구 승인 | 110세션 모두 `permission_denials: []`, timeout 0 |

### 실행 중 발생한 하네스 수정 (기록)

- 첫 실패 판정(B s1-fa-03 r2)이 `bunx biome ci`에서 났고, 원인은 세션 코드가 아니라 사용자 전역 <E2 plugin> 훅이 쓴 `frontend/<E2 plugin>/state/idle-notif-cooldown.json`의 포맷이었음. 동결된 체크는 그대로 두고, 17:28:51부터 러너가 체크 직전에 worktree의 `<E2 plugin>/` 디렉터리를 지우도록 수정(전 조건 동일). 그 전에 체크가 돈 세션은 실행 종료 후 같은 방식으로 재검사(`scripts/recheck_s1.py`); 원래 결과는 meta의 `check_original`, 표는 재검사 결과. 재검사로 판정이 바뀐 세션은 아래 1절 끝에 나열.

### stage1/README.md 질문 11개 중 지시 기본값과 다르거나 지시에 없던 항목 (⚑)

- ⚑ 조건 라벨: 초안은 A 없음 / B 라우터 / C 전문가. 지시(“C는 search·load·MCP ready 추가”, “C에서 로컬 스킬 pin 허용”, “전문가 스킬 없는 5개는 A vs C”)에 맞춰 **A 없음 / B 전문가 / C 라우터**로 실행.
- ⚑ Q1 (전문가 스킬 전달 방식): 지시 없음 → load_skills 출력 형식 그대로 `--append-system-prompt-file`. 사용자 프롬프트는 전 조건 동일, B에는 MCP·라우터 없음.
- ⚑ Q6 (뮤턴트): 세션이 대상 코드를 바꿔 뮤턴트가 적용되지 않으면 `not_applicable`(잡음도 실패도 아님, `pass: null`), 체크 `pass`는 적용 가능한 뮤턴트만으로 판정.
- ⚑ Q7 (스크린샷 판정자): 미정 → 블라인드 폴더만 생성, 판정 안 함.
- Q2·Q3·Q4·Q5는 지시대로(5개 A/C만, 내장 스킬 유지, C = 머지된 라우터만·훅 없음, 2회). Q8 max-turns 25, Q9 프롬프트 초안 그대로, Q10 전역 환경 상속, Q11 음성 대조군 없음 — 0단계 하네스 그대로.
- 체크 작성 시 해석(`checks/VALIDATION.md` deviations): hidden test 위치 `backend/tests/hidden_s1/`, “58 existing pass” = 비-hidden 전부 pass이고 ≥58 pass, s1-fa-02 “previous head” = 업스트림 head `fe56fa70289e` 등.
- 세션이 Bash에서 `initdb`로 자체 Postgres를 띄운 세션: A 4 (s1-fa-01-r2, s1-fa-02-r1, s1-fa-06-r1, s1-fa-06-r2), B 3 (s1-fa-01-r2, s1-fa-02-r1, s1-fa-02-r2), C 5 (s1-fa-01-r2, s1-fa-02-r1, s1-fa-06-r1, s1-fa-09-r1, s1-fa-09-r2). 종료 후 남아 있던 서버 1개(C s1-fa-09-r2, `/tmp/pgcase.gg3d`, :54329)는 하네스가 정지·삭제. 체크는 세션 DB와 무관하게 하네스의 `chk_` DB에서 실행.
