C2 실행 2026-10-22 KST 22:54–23:05, 10세션 (5태스크 × C2 × 2회), 고정 시드 큐 `runs/_queue_c2.txt`, 동시 4. A·B·C는 1b 첫 실행(20:59–21:31) 그대로. 숫자는 `scripts/report_s1b.py`(`report(..., conds=ABC+C2)`), 블라인드는 `rejudge/`.

## 0. 설정

| 항목 | 값 |
|---|---|
| C2 | C와 같은 하네스·태스크·체크·`--max-turns 40`. 차이: 라우터 SKILL.md와 MCP 서버가 skillfetch `main@e2a1b65`(PR #23: search_skills 기본 k=50, 압축 결과 `{id, title, 한 줄 summary, tier, token_estimate}`, 라우터 4단계 "50개 한 줄 요약을 모두 읽고 1–3개"). 레포 브랜치 `s1b-c2`(fastapi `aa3241d`, nextjs `3212825`) = `s1-c` + SKILL.md 교체(5줄 diff) |
| 서버 버전 | `.mcp.json`은 C와 동일(`uvx --from git+https://github.com/hyunlord/skillfetch`). 실행 전 `uvx --refresh`로 캐시 갱신, `--refresh` 없는 uvx에서 `DEFAULT_K == 50` 확인. 원격 HEAD 실행 전후 `e2a1b65` |
| 인덱스 | `built_at` 2026-10-22T06:15:43Z — A/B/C와 같음 |
| 체크 | 1b 동결 체크 그대로(`checks/FROZEN.sha256`) |
| 블라인드 | 새 세트 `rejudge/`: 랜딩 2태스크 각 8세트(A·B·C·C2 × 2, 데스크톱+375px), 플랜 8세트(PLAN.md + impl.diff, 1b와 같은 redaction, 6회). 새 무작위 코드, 키 `rejudge/*-key.jsonl` |

### 기록 사항

- **판정자: 정답·조건 비공개 하위 에이전트 3개**(같은 모델; 랜딩 nx·랜딩 fa·플랜 각 1). 이 세션은 1b 첫 판정 뒤 A/B/C 매핑을 unblind해 알고 있어 같은 세트를 다시 판정하면 블라인드가 아니다. 그래서 A/B/C/C2 전부를 새 코드로 섞어 하위 에이전트가 같은 루브릭(`rubric.md` = 1b 판정 기준 번역)으로 판정했다. 하위 에이전트에게는 루브릭과 해당 세트 폴더만 줬다(키·runs·다른 폴더 열지 말 것). 1b 첫 판정(이 세션, A/B/C만)은 참고로 나란히 둔다 — 판정자가 달라 두 판정의 점수를 직접 비교하지 않는다.
- **이 세션이 판정 전에 본 것**: 실행 중 C2 세션 4개의 skillfetch 호출 목록(로드한 스킬)을 확인했다. 판정은 하위 에이전트가 했고 이 세션은 판정에 관여하지 않았다.
- **체크 실패 2건(C2)**: s1b-fa-tags-plan r2 — 세션이 고친 `frontend/src/components/Items/columns.tsx`, `src/routes/_layout/items.tsx`가 biome 포맷 불일치(세션은 40턴 한도 도달). s1b-fa-landing r2 — 세션이 실행한 Playwright가 남긴 `frontend/test-results/.last-run.json`이 biome 포맷 검사에 걸림(기존 C r1과 같은 원인).
- **C2 s1b-fa-tags-plan r2**: `resolve_set`에 넣은 `uasl/fastapi-endpoint`가 로컬 fastapi·sqlmodel 핀과 합쳐 8000토큰을 넘어 `load_skills`에서 빠짐(errors에 기록).
- s1b-fa-tags-plan은 C2 2세션도 `--max-turns 40`에 도달.
