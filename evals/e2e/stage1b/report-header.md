실행 2026-10-22 KST 20:59–21:31, 30세션 (5태스크 × A/B/C × 2회), 고정 시드 큐(`runs/_queue.txt`), 동시 4. 숫자는 `scripts/report_s1b.py`, 블라인드 판정 원본 `blind-ranking.md`, unblind 결과 `blind-ranking-results.md`.

## 0. 설정

| 항목 | 값 |
|---|---|
| 하네스 | 1단계와 동일(`stage1/scripts/run_stage1.py`의 prepare/세션/diff 함수 재사용). 차이: `--max-turns 40`, 프론트 태스크(s1b-fa-landing, s1b-fa-tags-plan)는 세션 전 `bun install --frozen-lockfile`, 체크는 `checks/run_check_1b.py` |
| 조건 | A 업스트림 트리(레포 내장 fastapi/sqlmodel 스킬 유지) / B A + 전문가 스킬의 `load_skills` 출력(`expert-content/<id>.md`)을 `--append-system-prompt-file` / C 머지된 라우터(`main@96f0f3b` SKILL.md, 1단계와 같은 `s1-c` 브랜치) + `.mcp.json` |
| 전문가 스킬(B) | s1b-nx-landing·s1b-fa-landing `anthropics-skills/frontend-design`(2268 tok), s1b-fa-tags-plan `uasl/writing-plans`(1315), s1b-fa-service `uasl/caveman`(401), s1b-fa-utils-tests `uasl/tdd`(1032). 5번은 `uasl/tdd`(top-50 #44)가 `uasl/test-driven-development`(#47)보다 상위라 선택. 인덱스 순위(내 영어 재서술 쿼리, k=50): frontend-design nx #34·fa #9, writing-plans #38, caveman >50, tdd #44 — `expert-index-ranks.txt` |
| skillfetch | 서버 `uvx --from git+…` HEAD `53b81df`(실행 전후 동일). 1단계(`96f0f3b`) 이후 변경은 `cli.py`, `ingest/obedience.py`, 문서·테스트뿐 — `mcp/`, `index/`, `resolve/`, 라우터 스킬 변경 없음. 인덱스 `built_at` 2026-10-22T06:15:43Z(30세션 동일) |
| 체크 | 세션 전 작성·검증·동결(`checks/FROZEN.sha256`: run_check_1b.py + 재사용한 1단계 run_check.py·screenshot.py). 업스트림 트리에서 5개 모두 실패, 최소 참조 구현에서 5개 모두 통과(`checks/VALIDATION.md`). 체크 직전 `<E2 plugin>/` 제거(1단계와 동일) |
| 블라인드 | 랜딩 2태스크 PNG(데스크톱 1280 + 모바일 375) → `screens-blind/`, 플랜 태스크 PLAN.md + 구현 diff → `plans-blind/`(skill·skillfetch·router 도구 이름 `[redacted]` 6회). 매핑은 `screens-key.jsonl`, `plans-key.jsonl` |
| 도구 승인 | 30세션 모두 `permission_denials: []` |

### 기록 사항

- **판정자 1명(이 세션)**. 판정 전 1b `runs/`·키 파일은 열지 않았다. 실행 후 남은 프로세스 정리 중 `s1b-fa-tags-plan-A-r1` worktree 경로가 프로세스 목록에 보였다(그 세션이 띄운 vite dev 서버와 `/tmp/pgtags.*` Postgres를 하네스가 정지·삭제).
- **플랜 형식 단서**: 플랜 2개(c92f3fba, f8953e63)는 writing-plans 계열 형식("For agentic workers … subagent-driven-development / executing-plans", 체크박스 단계)이 redaction 후에도 남아 판정 시 보였다. unblind 결과 두 개 모두 **B**(writing-plans 주입 조건)였다.
- **결과 이벤트가 여러 개인 세션**: B s1b-fa-tags-plan r1·r2는 stream에 result 이벤트가 3개씩 있다(첫 번째 `error_max_turns` 41턴, 이어서 백그라운드 Agent 완료 후 후속 턴 2개). 표의 턴·시간·토큰은 세 구간 합계, subtype은 `error_max_turns (+2 follow-up)`. 0단계·0.5단계·1단계 180세션은 모두 result 이벤트 1개.
- **체크 실패 2건의 원인(세션 산출물)**: A s1b-fa-tags-plan r1 — 세션이 고친 `frontend/tests/items.spec.ts`가 biome 포맷 불일치. C s1b-fa-landing r1 — 세션이 실행한 Playwright가 남긴 `frontend/test-results/.last-run.json`이 biome 포맷 검사에 걸림.
- **s1b-fa-tags-plan은 6세션 모두 `--max-turns 40`에 도달**(B 2개는 그 뒤 후속 턴 진행).
