60세션 (4도메인 × A/B/C2 × 5회), 고정 시드 큐 `runs/_queue.txt`, 동시 4. 숫자는 `scripts/extract_s2.py` → `scripts/report_s2.py`, 채점 `judge-p1.md`·`judge-p2.md` → `scripts/unblind_s2.py`.

## 0. 설정

| 항목 | 값 |
|---|---|
| 하네스 | 1b/C2와 같음: `stage1/scripts/run_stage1.py`의 `run_session`/`collect_diff`/`strip_env_noise` 재사용, `claude -p <prompt> --output-format stream-json --verbose --max-turns 40 --allowedTools "Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*"`, 같은 env 정리, 사용자 전역 `~/.claude` 상속. 러너 `scripts/run_s2.py` |
| A | 레포 `s2-a` 브랜치 그대로 |
| B | A + 전문가 스킬 1개의 `load_skills` 출력(`expert-content/<task>.md`)을 `--append-system-prompt-file` — 1b의 B와 같은 방식. 선정 기록 `b-skills.md` |
| C2 | 레포 `s2-c2` = `s2-a` + `.claude/skills/skillfetch-router/SKILL.md` + `.mcp.json`. skillfetch `e2a1b65`에 고정(라우터 파일 = 1b `s1b-c2`와 동일, search k=50 압축) |
| 인덱스 | `~/.skillfetch/index` built_at 2026-10-22T06:15:43Z (index-2026-10-22) |
| 레포 | `repos/s2-tests` (`recur` 패키지, `src/recur/rules.py` 280줄 + `__init__` 24줄, 테스트 0개), `repos/s2-api` (빈 FastAPI 프로젝트), `repos/s2-docs` (1단계 nextjs `s1-a`에서 README.md 삭제), `repos/s2-data` (시드 생성 `data/orders.csv` 375행, 심은 문제 10종 — `rubrics.md`, `reference/orders-truth.json`) |
| 프롬프트 | `tasks-stage2.yaml`, 조건 간 동일(글자 하나 안 바뀜) |
| 체크 | `checks/check_s2.py`(+ `api_contract.py` 27호출). 실행 전 동결(`checks/FROZEN.sha256`: 루브릭·태스크·B 선정·B 내용·체크·러너). 수정 없는 레포에서 4개 모두 실패, 참조 구현에서 4개 모두 통과(`checks/VALIDATION.md`) |
| 채점 | 도메인별 블라인드 세트(15개씩, 조건 숨김, `blind-p<N>/`, 키 `blind-key-p<N>.jsonl`), 정답·조건 비공개 하위 에이전트가 `rubrics.md`로 채점. 2회(p1, p2): 코드 새로 뽑고 판정자 새로 |

### 기록 사항

- **B 적용 방식**: 지시문의 "~/.claude/skills에 설치"와 "1b의 B 설치 방식 그대로"가 다르다. 1b의 B는 `~/.claude/skills`가 아니라 `--append-system-prompt-file`이었다. 전역 설치는 동시에 도는 A·C2 세션에도 보이므로(조건 오염) 1b 방식을 따랐다.
- **C2 버전 고정**: 실행 시점 skillfetch main은 `a671e6a`(PR #27: `load_skills`가 precedence header를 더 이상 붙이지 않음, 라우터 7단계 문구 변경). "≥ e2a1b65"를 만족하면서 1b/C2와 조건을 같게 하려고 `e2a1b65`에 고정(`.mcp.json`의 `git+…@e2a1b65`). B 내용도 `e2a1b65`의 `load_skills` 출력(precedence header 포함, 1b와 같음).
- **B 선정 쿼리**: B는 `tasks-stage2.yaml`의 `search_sentence`(이 세션이 쓴 영어 재서술)로 뽑은 top-50에서 골랐다. C2 세션은 자기 쿼리로 검색하므로 B의 순위가 달라질 수 있다.
- **태스크 크기**: "한 세션 15턴 이상" 목표로 만들었지만 일부 세션은 15턴 미만으로 끝났다(세션별 표).
- **판정자**: 하위 에이전트(같은 모델). 이 세션은 판정에 관여하지 않았고, 실행 중 일부 C2 세션의 skillfetch 호출 목록을 확인했다.
- **API 체크 수정 후 재체크**: 동결한 `api_contract.py`가 `TestClient`를 열지 않아 FastAPI lifespan(시작 시 테이블 생성)이 돌지 않았다. 그 결과 B s2-api r3이 계약 5/27(자체 테스트 61개는 통과)로 나왔다. 실행 중(01:00경) `c.__enter__()` 한 줄을 고쳐 다시 검증했다(수정 없는 레포 0/27, 참조 구현 27/27). 큐가 끝난 뒤 s2-api 15세션 전부를 고친 스크립트로 재체크했고, 그 결과 B r3만 False→True(27/27)로 바뀌었다. 표의 체크 값은 재체크 결과다. 원 결과는 meta의 `check_original`, 기록은 `checks/VALIDATION.md`, `checks/FROZEN.after-fix.sha256`.
- **문서 세트 맥락 메모**: C2 레포에는 `.mcp.json`과 `.claude/`가 있다. C2 문서 2개가 이를 "Claude Code 설정, 앱 실행과 무관"이라고 적었다. 판정자에게 주는 공유 맥락(`s2-a` 소스)에는 이 파일들이 없어 '지어낸 내용'으로 판정될 수 있다. 그래서 두 채점 모두 문서 세트의 `_context/NOTE.txt`에 "일부 사본에는 `.mcp.json`과 `.claude/`가 있었고, 언급해도 안 해도 정확하다"는 중립 문장을 넣었다(조건 언급 없음). 그 두 문서의 "MCP 서버(skillfetch)"는 `[redacted]` 처리했다(전체 redaction 각 채점 1회).
- **이 세션이 본 매핑**: 위 누출 여부를 확인하다가 블라인드 코드와 조건 매핑 일부가 이 세션의 출력에 찍혔다. 판정은 하위 에이전트가 했으므로 블라인드에는 영향이 없다.
- **천장 효과**: 테스트 도메인 15세션 모두 branch 커버리지 100%이고, API 15세션 모두 계약 27/27, 체크는 60세션 전부 통과했다. 객관 지표로는 조건 간 차이가 없다.
- **랜딩 행**: 1b 재판정 결과를 그대로 옮겼다. 채점 1회(p2 없음)이고, 루브릭이 다르다((b) 쓸만함 1-5).
