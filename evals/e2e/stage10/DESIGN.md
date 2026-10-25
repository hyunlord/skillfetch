# 10단계 설계 — 최종 스택 실제 세션 검증

실행 전에 고정한다(2026-10-25). §4 판정 규칙과 §3 지표 정의는 결과를 본 뒤 바꾸지 않는다. 순서는 설계 → 비용 추정 보고(멈춤) → 승인 → 파일럿 → 본 실행이다.

## 0. 고정 대상

- **skillfetch**: main `57acc45c8132b826c7393e1c553d880f41deea10`(2026-10-25T01:16:49+09:00, PR #73 머지).
  - 라우터 자산 `assets/router-skill/SKILL.md`는 S-b′(`stage6/select-cands/S-bp/SKILL.md`)와 바이트 단위로 같다.
  - `38dcb69`..`57acc45` 사이에 `assets/router-skill`, `src/skillfetch/mcp`, `src/skillfetch/index` 변경은 없다.
  - MCP 서버는 `uvx --from <57acc45 worktree> skillfetch serve --index <index 사본>`이다.
- **index 사본**(해시 고정, 쓰기 1회):
  - **release**: `~/.skillfetch/index`(index-2026-10-22, 1,724 레코드)를 `stage10/index/release/`로 복사한다.
  - **staging-4**: `~/github/skillfetch/data/index-staging-4`(빌드 2026-10-24T15:58:48Z)를 `stage10/index/staging-4/`로 복사한다. 이 index는 staging-3의 skills·rejected·constraints·dupgroups와 바이트 단위로 같고, release의 `pairs.jsonl`(2,005줄, 동일)을 더한 것이다.
  - 복사 직후 파일별 sha256을 `stage10/index/HASHES.sha256`에 기록하고 읽기 전용(chmod a-w)으로 둔다.
  - **매 단계 재확인**: 각 세션 큐 시작 전, 각 세션 직전, 채점·판정 전에 `scripts/verify_index.py`가 해시를 다시 확인한다. 하나라도 다르면 큐를 멈추고 보고한다.
- **#26**(collapse search→resolve→load into one call)은 2026-10-25 현재 open issue다(머지된 PR 없음). 본 실행 직전에 다시 확인한다. 그때도 머지되지 않았으면 **R1s는 생략**하고 그렇게 기록한다.
- **본 실행 고정 변경**(2026-10-25, 파일럿 뒤·본 실행 전, 사용자 결정):
  - #26은 PR #75(`resolve_and_load`)로 main `3fef3f82c7b478b3730853c2eb6efef41ac54741`에 머지됐다. **R1s를 넣는다**(§1).
  - **모든 조건의 MCP 서버를 `3fef3f8`에 고정**한다(`~/skillfetch-e2e-wt/s10-server/3fef3f8`). 파일럿 14세션은 `57acc45` 서버로 돌았다.
  - `57acc45` 대비 `3fef3f8` 동일성:
    - `assets/router-skill/SKILL.md`: 같다(sha256 `3efef1e0…f040`, S-b′와 같음).
    - 서버 `INSTRUCTIONS`(362자): 같다(sha256 `04b1093f…bb50`).
    - `src/` 변경은 `mcp/server.py`(+15줄)·`mcp/session.py`(+26줄)뿐이고 지운 줄이 없다. 기존 네 도구의 코드·설명은 같다.
    - 다른 점: 도구 목록에 `resolve_and_load`가 하나 더 보인다(R0·R1에도). R0·R1의 라우터 SKILL.md는 이 도구를 언급하지 않는다.

## 1. 조건과 환경

| 조건 | 라우터 스킬 | MCP | index |
|---|---|---|---|
| **A** | 없음 | 없음 | – |
| **R0** | `57acc45` 라우터(V1 description + R-c 검색 + S-b′ 선택) | skillfetch serve | release 사본 |
| **R1** | 같은 라우터 | skillfetch serve | staging-4 사본 |
| **R1s** | `3fef3f8` `assets/router-skill/variants/fast.md`(58줄, 3단계를 `resolve_and_load` 한 번으로) | skillfetch serve | staging-4 사본 |

- **라우터 설치**: 각 태스크 레포에 조건 브랜치를 둔다.
  - `s10-a`: 시작 커밋 그대로
  - `s10-r`: 시작 커밋 + `.claude/skills/skillfetch-router/SKILL.md`(main `57acc45` 자산 = `3fef3f8` 자산)
  - `s10-rs`: 시작 커밋 + 같은 경로에 `variants/fast.md`(sha256 `c04e8db3…228b`). R1s는 E1에서만 돈다.
  - MCP 서버는 `--mcp-config` 파일로만 준다. R0·R1은 같은 브랜치·같은 라우터이고, MCP 설정 파일의 `--index`만 다르다.
  - 레포의 메인 체크아웃은 라우터가 없는 시작 커밋에 둔다. Claude Code가 worktree의 메인 체크아웃 스킬도 읽기 때문이다(6b에서 확인).
- **E1 깨끗한 환경**(모든 조건): `claude -p --setting-sources project --strict-mcp-config --mcp-config <조건 파일> --include-hook-events --max-turns 40 --allowedTools Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*`. 사용자 설정·플러그인·사용자 스킬·사용자 MCP는 없다.
- **E2 사용자 설정 환경**(A, R1만): 같은 `claude -p`에서 `--setting-sources`·`--strict-mcp-config`를 빼서 기본(user, project, local)으로 둔다.
  - R1은 `--mcp-config <staging-4 파일>`을 더한다(사용자 MCP 서버에 추가).
  - 그 밖의 플래그는 E1과 같다. 사용자 설정·플러그인·사용자 스킬(`~/.claude/skills`: 사용자 스킬 3개)·전역 CLAUDE.md·훅이 그대로 적용된다.
  - **E2 격리 확인**(파일럿): 세션 전후로 `~/.claude/skills`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md`의 해시를 비교한다(바뀌면 안 됨). 세션의 init 이벤트에서 실제로 로드된 MCP 서버·플러그인·스킬 목록을 기록한다. worktree 밖에 쓴 파일이 있는지도 본다.
- **모델**: 세션 모델은 `claude -p` 기본값이다. init 이벤트의 모델 id를 기록한다. 외부 API 키는 쓰지 않는다. 크리덴셜 파일은 읽지 않는다.

## 2. 태스크 묶음

| 묶음 | 태스크 | 레포 | 객관 체크 | 루브릭 |
|---|---|---|---|---|
| (1) 디자인 | d1-landing, d2-redesign, d3-dashboard, d4-email (6b 그대로) | nextjs, fastapi | `stage6/6b/checks/check_6b.py`(동결) | `stage6/6b/rubric-design.md` |
| (2) 천장 도메인 | s2-tests, s2-api, s2-docs, s2-data (Stage 2 그대로) | s2-* | `stage2/checks/check_s2.py`(동결) | `stage2/rubrics.md` |
| (3) 맞는 스킬 없음 | s6b-t133, s6b-t179, s6b-t354 (6b 묶음 (3)에서 t004 제외) | nextjs, fastapi | `check_6b.py`(동결) | `stage6/6b/rubric-b3.md`의 해당 행 |
| (4) 새로 커버된 비 Python | §2.1 | 새 레포 4개 | `stage10-private/b4/checks/`(§2.1에서 검증 후 동결) | `stage10/rubric-b4.md` |

- 묶음 (1)–(3)의 시작 커밋은 6b의 `s6b-a`와 같다. 요청 원문은 `stage6/6b/tasks.jsonl` 그대로다.

### 2.1 묶음 (4) 선택

- **후보 기준**(Stage 9 run-c 라벨 `stage9/run-c/oracle-v5-ss-b-s9g.jsonl`):
  - 공백 56 태스크(v3 관련 0·expect_none 아님·trivial 아님) 중 다음을 모두 만족하는 것
    - staging-4에 등급 3인 새 레코드(tier A/B)가 있다
    - release index에 등급 ≥2 스킬이 없다(v5-ss-b 기준)
  - → 16개다.

| 태스크 | 작업 | 스택 | 등급 3 스킬 (staging-4) | 이 Mac에서 빌드·테스트 |
|---|---|---|---|---|
| t016 | feature | rust | m07-concurrency | 가능 (cargo 1.93.1) |
| t017 | feature | rust | domain-iot | 가능하나 MQTT·TLS 의존성이 무겁다 |
| t115 | docs | rust | unsafe-checker | 가능 |
| t198 | data | mobile(iOS) | core-data, migration-patterns | 가능: Swift 패키지 + SwiftData·Core Data를 `swift test`(Xcode SDK 27.0, macOS 14 타깃)로 확인했다 |
| t199 | data | mobile(Flutter) | offline-queue, offline-first | 불가 (Flutter 없음) |
| t213 | ml | rust | domain-ml | candle·모델 다운로드가 무겁다 |
| t217 | ml | java_kotlin | ml-adoption-playbook | 불가 (JDK 없음) |
| t263 | performance | rust | m10-performance, m01-ownership | 가능 |
| t266 | performance | rust | m07-concurrency | 가능하나 동시성 성능 체크가 시간 의존적 |
| t267 | performance | rust | m10-performance | 가능하나 객관 체크가 약하다(해셔 교체 확인) |
| t272 | performance | mobile(SwiftUI) | image-loading 외 | UI 스크롤 성능이라 객관 체크가 어렵다 |
| t273 | performance | mobile(Android) | jetpack-compose | 불가 |
| t288 | ui_design | rust | domain-cli | 가능 (ratatui TestBackend로 확인 가능) |
| t293 | ui_design | java_kotlin | jetpack-compose | 불가 (JDK 없음) |
| t350 | ml | java_kotlin | mle-workflow | 불가 (JDK 없음) |
| t374 | ml | java_kotlin | kotlin-ktor-patterns | 불가 (JDK 없음) |

- **이 Mac의 툴체인**: cargo 1.93.1, Swift 6.4(Xcode 27.0)가 있다. Go, Gradle, JDK는 없다. node 25, bun 1.4도 있지만 후보 중 JS/TS 스택은 없다.
- **선택(4개)**: t016(Rust, async 기능), t263(Rust, 성능/소유권), t115(Rust, 문서·unsafe), t198(Swift 패키지, 데이터 이전).
  - **한계**: "스택이 겹치지 않게"는 이 Mac의 툴체인으로 다 지킬 수 없다. Rust 3개는 작업 종류와 등급 3 스킬이 서로 다르게 골랐다.
  - JDK·Gradle을 설치하면 Kotlin 후보(t293/t350/t374/t217)를 더할 수 있다. 시스템 변경이고 의존성 다운로드가 크므로 사용자 결정으로 남긴다.
  - t288(ratatui)은 5번째 후보로 둔다.
- **요청 원문**: Stage 3 태스크 텍스트 그대로다. 레포는 그 텍스트의 경로·이름(`src/room.rs`, `feed/l2.rs`, `src/hal/adc.rs`·`src/dma.rs`, `HabitEntity`·`CheckInEntity`)에 맞춰 만든다. 그래서 run-c 라벨이 (태스크, 스킬)에 그대로 적용된다.
- **레포**: `e2e/repos/s10-<태스크>/`. 시작 커밋은 브랜치 `s10-a`이고, 메인 체크아웃은 그 커밋이다.
- **참조 구현**: 레포 밖 `stage10-private/b4/ref/<태스크>.patch`다. 레포 안 어떤 브랜치에도 두지 않는다. 2026-10-25에 `stage10/b4/`에서 옮겼다(§4.4).
- **숨김 테스트·체크**: 레포 밖 `stage10-private/b4/checks/`에 둔다. 체크 때 worktree에 복사해 실행한다.
- **검증**(동결 조건): 체크가 손대지 않은 시작 커밋에서 **실패**하고, 참조 구현에서 **통과**해야 한다. 결과는 §7에 기록하고 체크 파일 해시를 동결한다.

## 3. 지표

- **세션 단위**:
  - 발화: 첫 `search_skills` 턴 번호. 없으면 미발화.
  - 로드한 스킬 id(`load_skills` 결과의 `skills`; R1s의 `resolve_and_load`는 `content`의 절 머리 `## n. 제목 (id)` 중 호출 인자에 있는 id)
  - 턴 수, 입력 토큰(캐시 포함 합), 비용(API 환산), 벽시계 시간, 객관 체크 통과
- **로드 적중**: 로드한 스킬 중 등급 ≥2가 있으면 적중이다.
  - 등급은 Stage 9와 같은 2b 형식으로 매긴다(title = 이름, summary = 220자 description, `stage3/gen/sys-grade.txt`, 격리 `claude -p`, 태스크마다 1회, 블라인드).
  - 묶음 (4)는 run-c 라벨(같은 요청 원문)을 먼저 쓰고, 없는 (태스크, 스킬)만 채점한다.
  - 묶음 (1)–(3)은 요청이 Stage 3 세트와 달라서, 로드된 (태스크, 스킬)을 모두 채점한다.
- **관련 스킬 로드 비율**(조건 × 묶음): 등급 ≥2 스킬을 1개 이상 로드한 세션 수 / 세션 수
- **불필요 로드**(묶음 (3)): 스킬을 1개 이상 로드한 세션 수(묶음 (3)은 맞는 스킬 없음 묶음)
- **턴·입력 토큰**: 조건 × 묶음 중앙값
- **블라인드 점수**: Claude 두 패스(p1, p2)다. 6b와 같은 방식으로 판정마다 새 무작위 코드를 쓰고, 정답·조건을 모르는 하위 에이전트가 루브릭과 세트 폴더만 받는다.
  - 세트는 태스크 단위이고, 그 태스크의 모든 세션(E1 A·R0·R1·R1s와 E2 A·R1)을 한 세트에 넣는다.
  - 세션 점수 = (p1 + p2) / 2, 조건 점수 = 세션 점수 평균이다.
  - **GPT 세 번째 판정자용 블라인드 패키지**를 내보낸다. p1과 같은 세트 형식이고 별도 코드다. GPT 결과가 오면 판정 (ii)의 GPT 쪽을 계산한다.

## 4. 판정 규칙 (실행 전 고정)

### 4.1 staging-4 release 게이트 — R1 vs R0, E1 기준

아래 넷을 **모두** 만족하면 release 승인이다. 하나라도 아니면 승인하지 않는다.

- **(i)** 묶음 (4)에서 R1의 관련 스킬 로드 비율 **>** R0 (세션 12개 중)
- **(ii)** 어느 묶음에서도 R1 평균 점수가 R0보다 D 넘게 낮지 않다. 판정자별로 따로 본다.
  - **Claude**: 조건 점수 = (p1 + p2) / 2의 평균이다. D_claude(b) = max over c ∈ {A, R0, R1} |mean_p1(c, b) − mean_p2(c, b)|. 6b와 같은 정의다.
  - **GPT**: 조건 점수 = GPT 점수의 평균이다. D_gpt(b) = 세 판정 패스 {p1, p2, gpt}의 모든 쌍 x, y에 대해 max over c ∈ {A, R0, R1} |mean_x(c, b) − mean_y(c, b)|. `codex-judge-6b.md`의 "세 패스 전체 D"와 같다.
  - GPT 결과가 오기 전에는 (ii)-GPT가 "미정"이고, 게이트도 미정이다.
- **(iii)** 묶음 (3)의 불필요 로드: R1 ≤ R0 + 1 (각 9세션 중)
- **(iv)** 어느 묶음에서도 R1 중앙 턴 ≤ R0 + 2

### 4.2 라우터 효과 — R1 vs A (게이트 아님, 보고만)

- 묶음별 점수 차이(R1 − A)를 Claude·GPT 각각 낸다. |차이| ≤ D(그 판정자 정의)면 "판정 차이 안"으로 표기한다.
- **묶음 (4)는 별도 절**로 둔다. 체크, 점수, 로드, 턴을 조건별로 낸다.

### 4.3 E2

- A·R1의 발화와 위 지표를 E1과 나란히 낸다. 게이트에는 쓰지 않는다.

### 4.4 판정자 노출 규칙 (2026-10-25 기록, 결과를 보기 전)

- **사건**: GPT가 `stage10/b4/`를 열었다. 그 폴더에는 참조 패치와 숨긴 검사 코드가 있었다. 내용을 읽었는지는 GPT가 보고할 예정이다.
- **규칙**:
  - GPT가 그 폴더의 파일 내용까지 읽었다고 보고하면, 묶음 (4)의 GPT 판정은 보고서에 **"판정자가 참조 구현을 사전에 봄"**으로 표시한다.
  - 게이트 (ii)의 GPT 쪽 판정에서 묶음 (4)는 **참고로만** 쓴다. 이 경우 (ii)-GPT는 묶음 (1)–(3)으로만 정한다.
  - 내용을 읽지 않았다고 보고하면 묶음 (4)도 그대로 쓴다. 보고가 오기 전까지 묶음 (4)의 GPT 판정은 "보고 대기"로 둔다.
- **GPT 보고(2026-10-25)**: `stage10/b4/`의 파일 목록만 봤고 내용은 읽지 않았다. 이 규칙의 표시는 적용하지 않는다. 묶음 (4) GPT 판정은 그대로 쓴다.
- **파일 위치**(이후 모든 단계):
  - 판정자가 보면 안 되는 파일은 `stage10/` 밖 `e2e/stage10-private/`에 둔다. 참조 구현, 숨긴 테스트·검사 코드, 조건 매핑(블라인드 키), 세션 원자료가 해당한다.
  - 판정 패키지는 `stage10/judge-package/` 한 폴더에만 내보낸다.
  - `stage10/`에는 설계·루브릭·태스크·index 사본·보고서와 판정 패키지만 둔다.
  - 이동한 파일의 경로는 `FROZEN.sha256`에 `../stage10-private/…`로 기록한다. 해시는 이동 전과 같다.

### 4.5 R1s vs R1 (게이트 아님, 보고만; 2026-10-25 기록, 결과를 보기 전)

- `fast.md` 배포 여부는 이 측정 뒤에 정한다. 이 절은 숫자만 낸다.
- 묶음별, E1: 중앙 턴, 중앙 입력 토큰, 중앙 비용, 첫 skillfetch 호출부터 마지막 skillfetch 호출까지의 턴 수, 관련 스킬 로드 비율, 묶음 (3) 불필요 로드, 객관 체크 통과, 점수 차이(R1s − R1, Claude·GPT 각각; |차이| ≤ D면 "판정 차이 안").
- D는 §4.1과 같은 정의(조건 집합 {A, R0, R1})를 쓴다.
- **R1s 판정 기준**(2026-10-25 기록. 사용자가 본 실행 전 지시(02:09)에서 지정했으나 이 절에 옮기지 않아 빠졌다. 결과를 본 뒤 기록하지만 기준은 그 지시 그대로다):
  - (a) 네 묶음 중 셋 이상에서 R1s 중앙 턴 ≤ R1 중앙 턴 − 2
  - (b) 어느 묶음에서도 R1s 점수가 R1보다 D 넘게 낮지 않음(Claude·GPT 판정자 각각, 각자의 D)
  - (c) 묶음 (3) 불필요 로드 R1s ≤ R1 + 1건
  - (d) 묶음 (4) 관련 스킬 로드 비율이 R1보다 0.1 넘게 낮지 않음
  - (a)가 불통과면 보고서에 "fast 판본은 배포하지 않음"으로 적는다.

### 4.6 묶음 (4) 판정 자료에 최종 답변 추가 — 가림 규칙 (2026-10-25 기록, 판정 시작 전, 사용자 승인)

- **이유**: t115 체크 개정(§7)으로 불건전 지적을 최종 답에서도 인정한다. 루브릭 기준 2(불건전 지적)를 판정자가 보려면 최종 답이 필요하다.
- **범위**: 묶음 (4)의 모든 세션(A·R0·R1·R1s, E1·E2)에 `reply.md`(가린 최종 답)를 더한다. 묶음 (1)–(3)은 6b와 비교할 수 있도록 지금처럼 diff와 체크 결과만 준다.
- **가림 규칙**(모든 조건에 같게, A 포함; `scripts/redact_replies.py`):
  - 다음 중 하나가 든 **문장**을 `[redacted]`로 바꾼다.
    - "skill"(대소문자 무관, skills·skillfetch·SKILL.md 포함) 또는 "스킬"
    - "MCP"(대소문자 무관, 단어 또는 `mcp_` 앞)
    - 도구 이름: search_skills, resolve_set, load_skills, resolve_and_load, profile_repo
    - 이번 Stage 10 실행(모든 묶음·조건)에서 로드된 모든 스킬의 전체 id, id의 이름 부분(`/`와 `@` 사이), index 제목. 대소문자 무관, 앞뒤가 글자·숫자·`_`·`-`가 아닌 토큰으로 맞춘다.
  - 문장: 줄마다 ". ", "! ", "? " 뒤에서 나눈다(다음 글자가 새 문장 시작일 때). 줄 앞의 목록·제목·인용 표시는 남긴다. 코드 블록 안은 한 줄이 한 문장이다.
- **기록·보고**: 조건별로 가린 문장 수, 가린 문장이 있는 세션 수, 가린 뒤 남은 글자 수 분포(최소·중앙·평균·최대)를 `stage10-private/redacted/stats.json`에 쓰고 보고서에 낸다. 조건 간 차이가 크면(예: 라우터 조건만 가린 문장이 있음) 그 사실을 보고서에 적는다.
- **파일럿 미리보기**(규칙 확인용, 판정에 쓰지 않음; `stage10-private/redacted-pilot-preview/`): E1 A 0문장(4세션), R0 4문장(4세션 모두 1문장), R1 0문장(4세션), R1s 1문장(1세션), E2 A·R1 0문장. R0에서 가린 문장은 "검색에서 맞는 스킬이 없어 로드하지 않았다"는 보고였다. `[redacted]` 표시 자체가 라우터 조건 신호가 될 수 있다.

- **변경(2026-10-25, 묶음 (4) 판정 시작 전, 사용자 결정): `[redacted]` 표시 대신 표시 없는 제거 + 제거 전 감사.**
  - 이유: 본 실행 답변에서 가림 대상 문장이 라우터 조건에 몰렸다(조건별 12세션 중 E1 A 0, R0 8, R1 1, R1s 3, E2 A 1, E2 R1 0). 표시가 남으면 표시 자체가 조건 신호가 된다.
  - 대상 문장 판정은 위 규칙 그대로다.
  - **감사**: 대상 문장마다 "과제 내용 포함" 여부를 기록한다(`stage10-private/redacted/audit.jsonl`). 과제 내용 = 그 태스크 레포 `s10-a`의 파일(경로·파일명), 그 안에서 정의된 fn/struct/enum/trait/type/const/func/class/protocol 이름(일반 단어 제외 목록 있음), `rubric-b4.md`의 그 태스크 행에 백틱으로 적힌 이름, 그리고 t115는 체크의 지적어(unsound, not sound, …n't sound, undefined behaviour, out of bounds, UB). 대소문자를 구분해 토큰으로 맞춘다.
  - **제거**: 과제 내용이 없는 대상 문장은 통째로 지운다. 과제 내용이 있는 대상 문장은 흔적 부분(위 규칙에 걸린 토큰, 그것만 감싼 백틱·괄호 포함)만 지우고 나머지는 둔다. 어느 쪽도 표시를 넣지 않는다. 표시만 남은 목록·제목 줄은 지운다.
  - t115 객관 체크 (b)는 가리기 전 원문 답으로 계산한 그대로 둔다.
  - 보고: 조건별 통째 제거 수, 일부 제거 수, 영향 받은 세션 수, 제거 뒤 글자 수 분포.
  - 본 실행 결과(판정 전): 대상 문장 13개 모두 과제 내용 없음 → 통째 제거 13, 일부 제거 0. 조건별 통째 제거: E1 A 0, R0 8, R1 1, R1s 3, E2 A 1, E2 R1 0. 제거 뒤 글자 수 중앙값: E1 A 1,837, R0 1,874, R1 1,927, R1s 1,773, E2 A 2,262, E2 R1 2,075.

### 4.7 보고

- `report-10.md`에는 판정 규칙과 지표별 숫자만 쓴다. "라우터가 낫다/못하다" 같은 총평 문장은 쓰지 않는다.

## 5. 반복과 세션 수

- **반복**: 태스크 × 조건 × 환경마다 3회, `--max-turns 40`.
- **세션 수**: 태스크 15개(4 + 4 + 3 + 4)
  - E1 {A, R0, R1}: 15 × 3 × 3 = 135
  - E2 {A, R1}: 15 × 2 × 3 = 90
  - E1 R1s: 15 × 3 = 45
  - 합계 270
- **제외 규칙**(6b와 같음): 사용량·지출 한도 메시지로 1턴 $0에 끝난 세션은 하네스 실패다. 출력을 따로 옮기고 다시 실행한다. 그 밖의 실패(타임아웃, 체크 실패)는 결과로 센다.
- **예산**(승인 2026-10-25): 약 270세션, $230–280. 누적 지출(API 환산, 파일럿 포함)이 **$300에 닿으면 큐를 멈추고 보고**한다.

## 6. 비용 규칙

- 계획에 없던 지출이 $10을 넘을 것 같으면 먼저 묻는다.
- 비용 추정은 §8에 쓰고, 보고 후 멈춘다(승인 전 파일럿 없음).

## 7. 묶음 (4) 검증 기록 (2026-10-25)

| 태스크 | 레포 (`repos/`) | 시작 커밋 `s10-a` | 체크 항목 | 손대지 않은 레포 | 참조 구현 (3회) |
|---|---|---|---|---|---|
| t016 | s10-t016 (tokio 채팅 서버, `src/room.rs`) | b59cb9c | 빌드 · 기존 테스트 · 숨김 테스트(입장 시 최근 50개를 순서대로, 짧은 기록 전체, 방별, 재생 뒤 실시간) | **실패**(숨김) | 통과 3/3 |
| t263 | s10-t263 (`src/feed/l2.rs` L2 파서) | 4b89110 | 빌드 · 기존 테스트 · 제로 카피(필드가 입력 버퍼 안을 가리킴, 값 동일) · 할당(2,000레벨에 ≤40회) | **실패**(제로 카피·할당) | 통과 3/3 |
| t115 | s10-t115 (`src/hal/adc.rs`·`src/dma.rs`, unsafe 블록 20개 중 불건전 2개) | fa17ff7 | 테스트 · 두 불건전 함수 밖 코드 불변(주석만 변경 가능) · 건전한 블록 모두 SAFETY 주석(clippy `undocumented_unsafe_blocks`) · 불건전 2개(`adc::sample_at`, `DmaBuffer::window`)는 주석에 지적어(unsound/undefined behavior/out of bounds/UB/FIXME/XXX/BUG/TODO) | **실패**(SAFETY·지적) | 통과 3/3 |
| t198 | s10-t198 (Swift 패키지, Core Data 스택 + SwiftData 모델 + `AppStartup.run`) | a628f3b | 빌드 · 기존 테스트 · 숨김 XCTest 4개(필드·체크인·연속 기록 복사와 저장, 두 번째 실행 중복 없음, UserDefaults 완료 플래그로 재실행 막음, 빈 저장소도 완료 표시) | **실패**(숨김) | 통과 3/3 |

- **체크 실행**: `stage10-private/b4/checks/check_b4.py <태스크> <worktree> <outdir> [--reply <최종 답 파일>]`. 숨김 파일을 worktree에 복사해 실행하고 지운 뒤 `check.json`을 쓴다(6b 형식). 통과 = 모든 항목 통과.
- **t115 체크의 해석**(파일럿 뒤 개정, §9):
  - ~~"지적"은 코드 안 주석이어야 한다.~~ 파일럿 뒤 마지막 항목을 둘로 나눴다.
    - (a) 두 불건전 함수 범위(앞 주석 포함)의 연속 주석 묶음 중, `SAFETY:`가 있고 지적어가 없는 묶음이 있으면 정당화로 보고 실패.
    - (b) 두 함수 각각을 코드 주석(지적어 포함)이나 최종 답에서 지적했다. 최종 답은 함수 이름과 지적어(unsound/not sound/undefined behavior/out of bounds/UB)가 한 문장에 있거나, 함수 이름이 지적어 있는 제목(마크다운 제목 또는 굵은 "제목:" 줄) 아래에 있으면 지적이다. "not unsound"류 부정은 뺀다.
  - 두 불건전 함수를 고치는 것은 허용한다(그 함수 밖 코드만 불변 검사).
  - 개정 체크 확인: 참조 구현 통과, 손대지 않은 시작 커밋 실패(SAFETY·(b)), 정당화 주석을 단 합성 사례 (a)·(b) 실패, "`sample_at`은 unsound… `window`는 괜찮다" 합성 답에서 `window` 미지적.
- **참조 구현**: `stage10-private/b4/ref/<태스크>.patch`. 레포 밖이다.
- **숨김 테스트**: `stage10-private/b4/checks/<태스크>/`.
- **레포 상태**: 메인 체크아웃은 `s10-a`에서 깨끗하다(worktree 1개). 이 세션의 훅이 만든 `<E2 plugin>/`(HUD 캐시)를 지웠고, `<E2 plugin>/`를 각 레포의 `.git/info/exclude`에 넣었다. worktree도 같은 exclude를 쓰므로 E2 세션 훅이 만드는 `<E2 plugin>/`가 diff에 섞이지 않는다. 묶음 (1)–(3) 레포에도 파일럿 준비 때 같은 줄을 넣는다.
- **index 사본**(`stage10/index/`, 읽기 전용):
  - release 6개 파일, staging-4 6개 파일. sha256은 `index/HASHES.sha256`에 있다.
  - 원본과 바이트 단위로 같은 것을 확인했다.
  - `scripts/verify_index.py` 통과(12개 파일).
  - 같은 서버 코드(`~/skillfetch-e2e-wt/s10-server/main` = `57acc45`)로 두 사본을 `Index.load`했다(1,724 / 2,785 레코드).
- **조건 브랜치 `s10-r`**(라우터 스킬 추가)와 MCP 설정 파일은 승인 뒤 파일럿 준비 때 만든다.

## 8. 비용·시간 추정 (2026-10-25, 승인 전)

- **세션 단가**(API 환산, 6b 실측; 6b는 E1이고 같은 모델·같은 플래그):

| 묶음 | A | 라우터 (6b C0·Cb 평균) |
|---|---:|---:|
| (1) 디자인 | $0.425 | $0.75 |
| (2) 천장 도메인 | $0.492 | $0.74 |
| (3) 맞는 스킬 없음 | $0.392 | $0.51 |
| (4) 새 비 Python | 실측 없음: (2) × 1.2로 둔다 | $0.59 / $0.89 |

- **E2 단가**: 실측이 없다. 사용자 설정은 전역 CLAUDE.md·플러그인·훅·사용자 MCP 도구 설명이 매 턴 입력에 더해진다. E1의 1.5–2.5배로 범위를 둔다. 파일럿 E2 2세션으로 실제 배수를 잰다.

| 항목 | 세션 | 추정 |
|---|---:|---:|
| E1 A | 45 | $21.6 |
| E1 R0 | 45 | $33.2 |
| E1 R1 | 45 | $33.2 |
| E2 A | 45 | $32–54 |
| E2 R1 | 45 | $50–83 |
| **세션 합계** | **225** | **$170–225** |
| (R1s, #26 머지 시) | +45 | +$33 |
| 로드 스킬 채점(2b, 격리 `claude -p`) | – | < $2 |
| **파일럿**: 묶음 (4) × {A, R0, R1} × 1 (E1) + E2 2세션 | 14 | 약 $11 |

- **블라인드 판정 두 패스**: 6b처럼 하위 에이전트(Claude Code 플랜 사용)로 한다. API 환산에 넣지 않는다.
  - 규모는 패스당 15세트, 세트당 15개 결과물이다(디자인 4세트는 스크린샷 포함).
  - GPT 패키지 내보내기에는 비용이 없다.
- **시간**: 6b는 4개 병렬로 세션당 약 4.3분(준비·체크 포함)이었다.
  - 225세션이면 4–5시간이다. Rust·Swift 빌드(세션 worktree마다 새로 컴파일)로 묶음 (4)는 더 길 수 있다.
  - 판정·채점·보고에 2–3시간을 더한다.
- **위험**: 6b에서는 지출 한도와 세션 한도로 116세션이 1턴 $0으로 끝나 재실행했다. 큐는 한도 메시지를 보면 멈춘다.

## 9. 파일럿 (2026-10-25)

- **결과**: 14세션, $6.66. 세부는 `../stage10-private/report-pilot.md`에 있다. 조건별 결과라 판정자가 보는 `stage10/`에 두지 않는다.
- **본 실행 전에 결정할 것**(제안이며, 승인 전에는 적용하지 않음):
  1. **t115 체크 "불건전 지적" 항목**: 지금은 코드 주석만 인정한다. 다음 둘로 나누는 것을 제안한다.
     - (a) 두 불건전 블록에 정당화하는 SAFETY 주석이 없다(지적어 없는 SAFETY 주석이면 실패).
     - (b) 두 함수를 코드 주석이나 세션 최종 답에서 지적어와 함께 이름으로 짚었다.
  2. **E2 <E2 MCP server> 잡음**: 사용자 <E2 MCP server> 훅이 쓴 `.gitignore`의 <E2 MCP server> 블록과 `.ignore`(<E2 MCP server> 템플릿과 같을 때)를 diff 수집 전에 되돌리거나 지운다. `<E2 plugin>`처럼 환경 잡음으로 처리하는 것이고, 지운 내용은 meta에 기록한다.
  3. **수정 비용 추정**: $180–257(중앙 약 $210). 앞의 §8 추정은 $170–225였다.
- **하네스 수정**(적용함): worktree 생성·삭제를 레포별 파일 락으로 직렬화했다.
- **결정**(2026-10-25, 사용자): 1·2 승인, 예산 $230–280(R1s 포함 약 270세션) 승인, $300 도달 시 멈춤. 적용한 것:
  1. t115 체크 개정(§7). 파일럿 t115 3세션을 저장된 diff·최종 답으로 다시 검사했다(`recheck_s10.py`): A·R0·R1 모두 통과(A·R1은 (b)를 최종 답에서, R0은 코드 주석에서).
  2. <E2 MCP server> 잡음: `run_s10.py`가 diff 수집 전에 <E2 MCP server> 훅이 쓴 `.gitignore` 블록(정확한 두 줄), `.ignore`의 <E2 MCP server> 줄, `<E2 MCP server>/` 디렉터리를 지우고 meta `graft_removed`에 기록한다(모든 조건; E1에는 지울 것 없음). 지우기 전 `git status --porcelain --ignored`도 meta `status_before_strip`에 남긴다(환경 흔적 감사용).
     - 파일럿 E2 2세션 재수집: 지운 것 `.gitignore`·`.ignore`, 남은 diff 파일은 A·R1 모두 `src/lib.rs`, `src/room.rs`, `tests/history.rs`. E1 t016(A·R1: `README.md`, `src/room.rs`, `tests/broadcast.rs`)과 비교해 다른 환경 흔적(<E2 MCP server>·omc·플러그인 이름)이 diff에 없다.
  3. 최종 답을 `<out>.reply.txt`로 저장하고 묶음 (4) 체크에 `--reply`로 넘긴다.
  4. 묶음 (1)–(3) 레포(nextjs·fastapi·s2-*)에 `s10-r`·`s10-rs`, 묶음 (4) 레포에 `s10-rs`를 만들었다. nextjs·fastapi 메인 체크아웃이 6b 뒤 `e2e-baseline`(옛 라우터 skill 추적)으로 돌아가 있어서 `s6b-a`로 바꿨다(6b 파일럿과 같은 조치). 여섯 레포의 `.git/info/exclude`에 `<E2 plugin>/`를 넣었다.
- **R1s 파일럿**(E1, 2세션: s10-t016, s2-api): 결과는 `../stage10-private/report-pilot.md`.

## 10. 본 실행 중 기록

- **2026-10-25, 62세션 시점: 사용 한도 중단과 검출 수정.**
  - 큐가 하네스 실패로 멈췄다. 세션 4개가 최종 답 "You've hit your org's monthly spend limit …"로 9–17턴 만에 끊겼다(s2-data E1 A·R0, d4-email E1 R0·E2 R1). 출력은 `stage10-private/runs/harness-fail/`로 옮겼고 다시 돌린다. 비용($2.36)은 누적 지출에 그대로 센다.
  - 검출기 결함: `"num_turns":1`을 문자열로 찾아서, 11·14·17턴 세션은 우연히 잡고 9턴 세션(s2-data E1 R0)은 놓쳤다(체크 실패로 기록됐었다). 이제 최종 답에 한도 문구가 있으면 턴 수와 상관없이 하네스 실패로 본다. §5 제외 규칙의 "1턴 $0"을 "사용·지출 한도로 끊긴 세션"으로 넓힌다(사용자 지시 "사용 한도로 끊긴 세션은 따로 두고 재실행").
- **2026-10-25: t115 체크 구현 결함 수정(정의 변경 없음).**
  - clippy 경고 줄을 감싸는 함수를 찾을 때 주석 안의 "safe fn and …", "safe fn can …"을 함수 선언으로 읽었다. 그래서 E1 A·R0 m1에서 불건전 두 블록의 경고를 함수 `and`·`can`에 붙여 "건전한 블록 SAFETY 누락"으로 실패시켰다. 같은 결함이 함수 범위 끝 찾기에도 있었다(지적 위치를 코드 대신 최종 답으로 기록; 통과 여부는 같았음).
  - 세 곳의 `fn` 검색이 `//` 앞 코드만 보도록 고쳤다. 참조 구현 통과·시작 커밋 실패는 그대로다.
  - 끝난 t115 세션 8개(본 실행 m1 5개, 파일럿 3개)를 저장된 diff·최종 답으로 다시 검사했다: 8개 모두 통과. meta의 `check`를 새 결과로 바꾸고 이전 결과는 `check_original`에 남겼다. 이후 세션은 고친 체크로 돈다.
- **2026-10-25, 126세션 시점: t115 지적어의 축약형 누락 수정(정의 변경 없음).**
  - E1 R1 m2의 최종 답은 `window`를 "## Two blocks that aren't sound" 제목 아래 번호 항목으로 짚었다. 지적어 목록에 "isn't sound"는 있고 "aren't sound"가 없어서 (b)가 실패했다.
  - 지적어의 축약 부정을 "(is|are|was|were)n't sound"(곧은·굽은 따옴표)로 넓혔다. 코드 주석 패턴, 최종 답 패턴, 부정("… n't unsound") 패턴 모두 같게 바꿨다.
  - 끝난 t115 세션 11개를 모두 다시 검사했다: 11개 통과(처음 기록 기준 실패였던 5개 포함: E1 A m1·p0, R0 m1, R1 m2·p0). 참조 구현 통과, 시작 커밋 실패는 그대로다. 합성 사례(문단 안 섞임, 부정 제목, 지적 없음)의 결과도 그대로다.
  - 보고서에는 t115 체크가 처음 기록·개정 뒤 결과를 둘 다 낸다(meta `check_original`·`check`).
- **2026-10-25, 본 실행 뒤: 세션이 만든 git 브랜치(세션 간 공유).**
  - worktree는 레포의 ref를 공유한다. 세션이 `git checkout -b`로 만든 브랜치는 이후 모든 세션의 `git branch`에 보였다. 본 실행 중 브랜치 18개가 생겼고 모두 E2 세션이 만들었다(E2 사용자 전역 규칙 "git status && git branch", "Feature branches only"). 목록·SHA: `stage10-private/session-created-branches.txt`.
  - 18개 모두 시작 커밋(`s6b-a`/`s10-a`) 또는 조건 브랜치 커밋(`s10-r`)을 가리키고 그 위 커밋이 0개다. 세션 작업 내용이 다른 세션으로 넘어간 경로는 없다. 넘어간 것은 브랜치 이름과(일부는 worktree 경로에서 따온 `…-s10-e2-r1` 꼴) `s10-r`·`s10-rs` 브랜치의 커밋 제목 "stage10: router skill"이다.
  - 조건 브랜치(`s10-r`, `s10-rs`)와 그 커밋 제목은 설계상 처음부터 모든 세션에 보였다(6b의 `s6b-c0`/`s6b-cb`와 같다). 세션 worktree 경로(`…/s10-<env>-<cond>-<task>-<tag>`)에도 조건 이름이 들어 있다(6b와 같은 명명).
  - 도구 결과에 그 브랜치 이름이나 `s10-r`·"stage10: router"가 나온 본 실행 세션(각 45개 중): E2 A 25, E2 R1 12, E1 R0 1, E1 A·R1·R1s 0. 판정 자료(diff·체크·답)에는 이런 이름이 없다(판정 패키지 감사 0건).
  - 18개 브랜치는 기록 뒤 지웠다(커밋 손실 없음).

## 11. 묶음 (3) 정의 수정 (2026-10-25, Stage 10 판정 뒤, 사용자 결정)

- **Stage 10 판정은 불통과 그대로다.** 이 절은 묶음 (3)을 다시 재는 추가 측정의 정의다. §4.1의 판정을 바꾸지 않는다.
- **새 정의**: "맞는 스킬 없음" = 비교하는 두 index 모두에서 등급 ≥2 스킬이 없는 태스크(라벨 기준).
  - release: v5-ss-b 라벨(`stage8/oracle-v5-ss-b.jsonl`)에서 release 사본에 있는 스킬 중 등급 ≥2가 0개.
  - staging-4: run-c 라벨(`stage9/run-c/oracle-v5-ss-b-s9g.jsonl`)에서 staging-4 사본에 있는 스킬 중 등급 ≥2가 0개.
  - 라벨 없는 스킬은 판정에 쓰지 않는다(미정으로 따로 센다).
- **지금 묶음 (3) 세 태스크에 적용**(Stage 3 원문 기준 라벨):

| 태스크 | release 등급 ≥2 | staging-4 등급 ≥2 | 새 정의 |
|---|---|---|---|
| t133 | uasl/scaffold | docker-patterns, deployment-patterns, uasl/scaffold | 빠짐 |
| t179 | 없음 | python-testing | 빠짐 |
| t354 | 없음 | database-migrations, deployment-patterns | 빠짐 |

  - 6b는 레포에 맞게 다시 쓴 텍스트로 v4 oracle 재라벨을 했다(그때 관련 0). staging-4 스킬에 대한 다시 쓴 텍스트의 라벨은 없다. 위 표는 Stage 3 원문 라벨이다.
- **후보 선택 기준**(결과를 보기 전에 기록):
  1. 새 정의를 만족: 380개 중 38개.
  2. `expect_none`이 아니고 task_type이 trivial이 아님(Stage 9 GAP·§2.1과 같은 조건): 12개.
  3. 이 Mac의 기존 툴체인(Python, Node, Rust, Swift 패키지)으로 레포·객관 체크를 만들 수 있음: 4개 — t001(python feature), t033(ts_react_next bugfix), t114(rust docs), t276(python ui_design, Textual).
     - 빠진 8개: Go 4(t160, t162, t284, t286; Go 툴체인 없음), JDK 2(t118, t292), Android 1(t222), fastlane·iOS 앱 1(t172).
- **결정 대기**: 세 태스크가 모두 빠지므로 대체 수(1개 vs 3–4개)와 후보 중 선택은 사용자 확인 뒤에 정한다. 레포·체크는 그 뒤 §7과 같은 방식(시작 커밋에서 실패, 참조 구현에서 통과)으로 만들고 검증한다.

### 11.1 실행 전 확인·범위 (2026-10-25, 사용자 결정)

- **교체**: 묶음 (3)을 t001, t033, t114, t276 네 개로 바꾼다(s6b-t133·t179·t354는 새 정의에서 빠짐).
- **실행 전 확인 규칙**: 레포에 맞게 다시 쓴 태스크 문장으로 release와 staging-4 각각의 R-c top-50을 2b 형식(블라인드, 격리 `claude -p`)으로 채점한다. R0·R1 파일럿 선택이 있으면 그것도 채점한다. 어느 쪽에도 등급 ≥2가 없는 태스크만 묶음에 넣는다. 걸리는 태스크는 빼고 기록한다(대체하지 않음).
- **실행**: 새 묶음 (3) × {R0, R1, R1s} × E1 × 3회. 판정은 같은 방식(Claude p1·p2, GPT 패키지).
- **D**: 이 재측정의 D는 조건 집합 {R0, R1}로 계산한다.
- **게이트 재평가 범위**: 새 묶음 (3)이 (ii)·(iii)·(iv)의 묶음 (3) 항목을 대체하고, 나머지 묶음은 본 실행 결과 그대로 쓴다. 첫 평가가 불통과였고 그 원인이 묶음 (3) 정의였다는 것을 보고서에 그대로 남긴다.
- **비용**: 레포·체크·문장 확인 뒤 추정을 보고한다. 추정이 $18 이하면 승인 없이 실행한다.

### 11.2 실행 전 확인 결과 (2026-10-25)

- 태스크 문장: 네 태스크 모두 Stage 3 원문 그대로 쓴다. 레포를 그 문장의 경로·이름에 맞춰 만든다(§2.1 묶음 (4)와 같은 방식). 그래서 R-c 쿼리는 `stage3/followup/rc-R-c-380.jsonl` 그대로다.
- R-c top-50(서버 코드 `3fef3f8`, release·staging-4 사본)의 합집합을 2b 블라인드 채점했다(`scripts/s10_b3_precheck.py`, 304행, $0.359, 누락 0). 파일럿 선택은 없다.

| 태스크 | 채점 | 등급 ≥2 | 묶음 (3) |
|---|---|---|---|
| t001 | 80 | 없음 | 넣음 |
| t033 | 72 | 없음 | 넣음 |
| t114 | 76 | 없음 | 넣음 |
| t276 | 76 | uasl/anvil (2) | **뺌**(대체 없음) |

- 새 묶음 (3) = t001, t033, t114. 재측정 세션 = 3 × {R0, R1, R1s} × E1 × 3 = 27.

### 11.3 레포·체크 검증과 실행 (2026-10-25)

- 레포(`e2e/repos/`, 시작 커밋 `s10-a`, 작성자 `e2e <e2e@local>`, 커밋 1개): s10-t001 `7c02bf4`(Python, `scripts/reconcile_payouts.py`), s10-t033 `4b60c5a`(TS/React, `lib/sanitizeHtml.ts`·`components/editor/RichTextField.tsx`·`Toolbar.tsx`, 새 패키지 없음), s10-t114 `a020d0a`(Rust workspace, `telemetry-codec/src/lib.rs`, 20바이트 헤더 + 페이로드 + CRC-16/CCITT-FALSE, little-endian). 조건 브랜치 `s10-r`(S-b′), `s10-rs`(fast.md)는 본 실행과 같은 파일.
- 숨긴 체크: `stage10-private/b3new/checks/<t>/check.py`, 참조 구현: `stage10-private/b3new/ref/<t>.patch`(레포 밖).
  - t001: 기존 테스트, `--dry-run`이 DB를 바꾸지 않음(sha256), 쓸 행의 payout_id와 금액 차이를 stdout에 출력, 플래그 없이는 기존과 같은 행, `--help`에 플래그.
  - t033: 타입체크, 기존·세션 테스트, 숨긴 테스트(Google 래퍼 3종 → 실제 URL, 래핑된 javascript: 거부, 일반 링크 그대로, 비Google `/url?q=` 미변경, script 제거), 의존성·lock 불변, Toolbar 불변.
  - t114: `cargo test`(doctest 포함), `cargo doc -D warnings`, 코드 불변(주석·공백·doc 속성·내부 lint 속성 제외 토큰 비교), crate 문서 ≥15줄, 바이트 설명 용어 12묶음(매직, 버전, flags, sensor, seq, timestamp, length, payload, crc, little-endian, CRC 변형, 헤더 20).
- 하네스 경로(`run_s10.prepare`·`run_check`)로 독립 검증: 세 체크 모두 시작 커밋에서 **실패**(t001 b·c·e, t033 hidden, t114 d·e), 참조 구현에서 **통과**(t001 3/3, t033·t114 각 1회 + 제작 때 3/3). 체크 뒤 worktree 변경 없음. t001 체크가 `--base` 인자를 받지 않아 받도록 고쳤다(무시).
- 루브릭: `stage10/rubric-b3new.md`(레포를 만들기 전에 고정).
- 실행: `runs/jobs-b3new.txt`(27개, 태그 n1–n3, 반복 안에서 섞음), 비용 상한 = 실행 전 누적 + $18.

### 11.4 재평가 결과와 Stage 10 최종 판정 (2026-10-25)

- 새 묶음 (3) GPT 판정(gptn, 27점) 형식 검증 뒤 키를 읽었다. GPT 점수 R0 4.889, R1 4.667, R1s 4.889, D_gpt({p1n, p2n, gptn} × {R0, R1}) = 0.111.
- 재평가: (i) 예, (ii)-Claude 예, (ii)-GPT 묶음 (1)·(2)·(4) 예·묶음 (3) **아니오**(4.667 < 4.889 − 0.111), (iii) 예(R1 4/9 vs R0 9/9), (iv) 예(14 vs 15) → **불통과**.
- Stage 10 최종 판정: 첫 평가 불통과((iii)), 재평가 불통과((ii)-GPT 묶음 (3)). R1s (a) 불통과 → fast 판본 배포하지 않음.
- 보고서: `stage10/report-10.md`(GPT 판정이 끝난 뒤 `stage10-private/`에서 옮김).
