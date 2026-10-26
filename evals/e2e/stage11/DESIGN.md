# 11단계 설계 — staging-4 release 게이트 재측정 (설계만, 실행 전)

작성 2026-10-25. **실행 여부는 출시(2026-10-26) 뒤에 정한다.** 이 문서는 실행 전에 고정할 내용과 비용 추정까지다. §4 게이트, §3 지표 정의는 결과를 본 뒤 바꾸지 않는다. 판정 기준·보고 기준은 모두 이 문서에 실행 전에 적는다(Stage 10에서 §4.5 (a)–(d)가 DESIGN에 옮겨지지 않은 일을 되풀이하지 않는다).

- **실행 조건**(2026-10-25 사용자 결정): 실행은 2026-10-27 이후, 파일럿 먼저. 비용 상한 $115(실행 전 확인·파일럿·본 실행·재실행·채점 합계). 넘을 것 같으면 멈추고 보고한다.

## 0. Stage 10과의 관계

- Stage 10 최종 판정은 불통과로 확정됐고 재해석하지 않는다(`stage10/report-10.md`).
- Stage 11은 새 측정이다. Stage 10에서 결과를 본 태스크(묶음 (3)의 t001·t033·t114)는 쓰지 않는다.

## 1. 고정 대상

- **skillfetch**: main `3fef3f82c7b478b3730853c2eb6efef41ac54741`(Stage 10과 같은 커밋), 서버 worktree `~/skillfetch-e2e-wt/s10-server/3fef3f8`.
- **라우터**: R0·R1 모두 `assets/router-skill/SKILL.md`(S-b′, sha256 `3efef1e0…f040`). `variants/fast.md`는 쓰지 않는다(Stage 10 §4.5 (a) 불통과).
- **index 사본**: Stage 10의 `stage10/index/{release,staging-4}`(읽기 전용, `stage10/index/HASHES.sha256` 12파일)를 그대로 쓴다. 복사하지 않고 같은 파일을 해시로 확인한다. 매 세션 전후·채점 전에 `verify_index.py`로 재확인한다(쓰기 1회 규칙).
- **환경**: E1만(`--setting-sources project --strict-mcp-config --mcp-config <조건 파일> --include-hook-events --max-turns 40 --allowedTools Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*`). E2 없음.

## 2. 조건

| 조건 | 라우터 | MCP index | 묶음 |
|---|---|---|---|
| R0 | S-b′ | release 사본 | (1)–(4) |
| R1 | S-b′ | staging-4 사본 | (1)–(4) |
| A | 없음 | 없음 | (4)만, **참고**(게이트·D에 쓰지 않음) |

## 3. 묶음과 반복

| 묶음 | 태스크 | 반복 | 조건별 세션 |
|---|---|---|---|
| (1) 디자인 | Stage 10 묶음 (1) 4개(d1-landing, d2-redesign, d3-dashboard, d4-email), 체크 `stage6/6b/checks/check_6b.py` | 3 | 12 |
| (2) 천장 도메인 | Stage 10 묶음 (2) 4개(s2-tests, s2-api, s2-docs, s2-data), 체크 `stage2/checks/check_s2.py` | 3 | 12 |
| (3) 맞는 스킬 없음 | t160, t162, t118 (§3.1–3.1.3, `stage11/tasks-b3.jsonl`) | 6 | 18 |
| (4) 새로 커버된 비 Python | Stage 10 묶음 (4) 4개(t016, t263, t115, t198) + t266(§3.2.2) | 6 | 30 |

- **세션 수**(2026-10-25 §3.2.2 뒤): R0·R1 각 (12 + 12 + 18 + 30) = 72 → 144, A(묶음 (4)) 30 → **합계 174**.
- 묶음 (1)–(2)의 요청 원문·시작 커밋은 Stage 10과 같다(`s6b-a`).

### 3.1 묶음 (3) 정의와 후보

- **정의**(Stage 10 §11과 같음): 비교하는 두 index(release, staging-4) 모두에서 등급 ≥2 스킬이 없는 사소하지 않은 태스크. 라벨 기준(release: v5-ss-b, staging-4: run-c), 라벨 없는 스킬은 미정으로 따로 센다.
- **실행 전 확인**(Stage 10 §11.1과 같음): 레포에 맞게 다시 쓴 문장(원문 그대로면 원문)으로 release와 staging-4 각각의 R-c top-50(그리고 파일럿 선택)을 2b 형식으로 블라인드 채점한다. 어느 쪽에도 등급 ≥2가 없는 태스크만 넣는다. 걸리면 빼고 기록한다.
- **후보 현황**(2026-10-25 조사):
  - 정의를 만족하는 Stage 3 태스크 38개 중 Stage 10에서 쓴 t001·t033·t114와 실행 전 확인에서 빠진 t276을 빼면 34개.
  - 그중 이 Mac의 기존 툴체인(Python, Node, Rust, Swift 패키지)으로 만들 수 있는 것은 모두 task_type `trivial`(이름 바꾸기, 오타, import 한 줄)이다. 사소하지 않은 후보는 남지 않는다.
  - 사소하지 않은 나머지 8개는 다른 툴체인이 필요하다: Go 4개(t160 ko 빌드 Makefile 타깃, t162 goreleaser 설정, t284 bubbletea 목록 UI, t286 Fyne 레이아웃), JDK 2개(t118 javadoc `@throws`, t292 Vaadin 그리드), Android 1개(t222), fastlane·iOS 앱 1개(t172).
- **결정 대기**(실행 전 사용자 결정):
  - (가) **Go 툴체인 설치**(`brew install go`, 필요하면 `goreleaser`): t284(bubbletea, `teatest`/렌더 출력으로 체크), t160(Makefile 타깃, `make -n`·타깃 내용 체크), t162(`.goreleaser.yaml`, `goreleaser check` 또는 스키마 체크). 라벨 출처(v5-ss-b/run-c)가 유지된다. 시스템 변경이다.
  - (나) **새 태스크 작성**(Python/TS/Rust/Swift): Stage 3 밖이라 v5-ss-b/run-c 라벨이 없다. 실행 전 확인의 R-c top-50 2b 채점이 유일한 라벨이 된다. R-c 쿼리도 새로 만들어야 한다(격리 `claude -p`, Stage 3과 같은 프롬프트).
  - (다) JDK 설치로 t118 추가(가·나와 섞기).

### 3.1.1 결정과 실행 전 확인 결과 (2026-10-25)

- **결정**(사용자): (가). `brew install go goreleaser` 승인. 실행 전 확인은 t284·t160·t162를 Stage 10 §11 방식으로 하고, 하나라도 걸리면 남은 Go 태스크로 교체, 그래도 모자라면 멈추고 보고.
- **설치 기록**(`stage11-private/toolchain/`): 설치 전후 `brew list --formula --versions`·`--cask --versions`. 차이는 formula 2개 추가(go 1.27.3, goreleaser 2.18.3), 그 밖의 변경 없음(cask 차이 0). `~/go`는 아직 없다(모듈을 받으면 생긴다). 남길지는 사용자에게 묻는다.
- **태스크 문장**: 네 태스크 모두 Stage 3 원문 그대로(레포를 그 경로·이름에 맞춰 만든다). R-c 쿼리는 `stage3/followup/rc-R-c-380.jsonl`.
- **라벨 정의 확인**: v5-ss-b(release 사본에 있는 스킬)·run-c(staging-4 사본에 있는 스킬) 모두 등급 ≥2 없음 — t284, t160, t162, t286 네 개 다.
- **2b 블라인드 채점**(`scripts/s11_b3_precheck.py`, Stage 10 `s10_b3_precheck.py`와 같은 절차, 시드 `s11-b3pre-<task>`, 서버 `3fef3f8`, index 해시 확인 뒤):

| 태스크 | 채점 | 등급 분포 (0/1/2) | 등급 ≥2 | 묶음 (3) |
|---|---:|---|---|---|
| t284 | 76 | 69/6/1 | uasl/anvil (2) | **뺌** |
| t160 | 81 | 75/6/0 | 없음 | 넣음 |
| t162 | 76 | 71/5/0 | 없음 | 넣음 |
| t286 (t284 교체 후보) | 76 | 73/2/1 | affaan-m-ecc/golang-patterns (2) | **뺌** |

  - t162 첫 호출은 채점 대신 "safety classifier에 막혔다"는 문장으로 돌아왔다(`stage11-private/b3/failed-calls/`). 같은 프롬프트로 한 번 다시 호출해 채점을 받았다(누락 0).
  - 비용: $0.40(실패 호출 $0.098 포함).
  - 스크립트 결함 1건: 결과 병합이 한 단계만 합쳐서 t286 검색이 앞 태스크의 top-50을 덮었다. 재귀 병합으로 고치고 네 태스크 검색을 다시 했다(결정적, t284·t160의 채점 합집합과 같음을 확인).
- **결과**: 남은 Go 태스크를 다 써도 묶음 (3)은 2개(t160, t162). 3개에 모자라서 **멈춤**. 사용자 결정 대기(레포·체크·루브릭은 만들지 않았다).

### 3.1.2 묶음 (3) 채우기 결정 (2026-10-25, 사용자, 실행 전 고정)

- **1순위**: `brew install openjdk`(사용자 승인), t118을 같은 실행 전 확인에 넣는다. JDK는 keg-only라 셸 프로필은 건드리지 않고, 체크·세션 환경에서만 `$(brew --prefix openjdk)/bin`(`/opt/homebrew/opt/openjdk/bin`)을 PATH 앞에 넣는다.
- **2순위**(t118도 등급 ≥2면): t160·t162 × 9회, 조건당 18세션, 게이트 (iii) "18 중 R0 + 2" 그대로. 비용은 다시 추정만 하고 실행하지 않는다.
- 어느 쪽이든 묶음 (3)이 정해지면 레포·체크·루브릭을 만들고 검증한 뒤 보고하고 멈춘다. 본 실행은 2026-10-27 이후.
- go·goreleaser·openjdk는 Stage 11이 끝날 때까지 남긴다. 끝나면 지울지 사용자에게 다시 묻는다.

### 3.1.3 결과 (2026-10-25)

- **openjdk**: 이미 설치돼 있었다(openjdk 27, openjdk@21, keg-only — PATH에 없어서 §3.1 조사 때 "JDK 없음"으로 잘못 셌다; `/usr/bin/java`는 macOS 스텁). `brew install openjdk`는 "already installed and up-to-date"로 끝났고 설치 전후 brew list 차이 0(`stage11-private/toolchain/*openjdk*`). Stage 11 전부터 있던 것이라 끝난 뒤 삭제 질문 대상은 go·goreleaser다. `~/go`(20K)는 체크 검증 중 Go 빌드가 만들었다(삭제 질문에 같이 넣는다).
- **t118 실행 전 확인**: 라벨 정의(v5-ss-b·run-c 등급 ≥2 없음) 만족. 2b 블라인드 채점 73행, 등급 ≥2 없음 → **넣음**($0.086). 실행 전 확인 합계 $0.49.
- **묶음 (3) 확정 = t160, t162, t118** (1순위). 반복 6회, 조건당 18세션 — §3 표·§8 비용 추정 그대로.
- **레포**(`e2e/repos/`, 작성자 `e2e <e2e@local>`, 커밋 1개 + 조건 브랜치): 요청 원문의 경로·이름에 맞춰 만들었다. 외부 의존성 없음(Go 표준 라이브러리, JDK만).

| 레포 | `s11-a` | `s11-r` (라우터 S-b′, "chore: add project skill") | 내용 |
|---|---|---|---|
| s11-t160 | `fa34592` | `cd4a016` | Go 모듈 `github.com/acme-fleet/tracker`, `cmd/{tracker-api,tracker-ingest,trackerctl}`, Makefile `release` = vet + test + API 이미지 docker build/push, README "Releasing" |
| s11-t162 | `8f25b30` | `f2ff41c` | Go `inventory-cli`(`cmd/inventory-cli`), `.goreleaser.yaml` v2(linux·darwin·windows × amd64·arm64, Homebrew 없음), GitHub Actions release 워크플로 |
| s11-t118 | `0872447` | `e462c4f` | Java 패키지 `com.acme.payments.reconciliation`, `PaymentReconciliationService.reconcileBatch`(checked 2개 선언, unchecked 3개 throw), 다른 클래스는 Javadoc 완비, Makefile(`javac --release 21`, 평범한 Java 테스트 main, `docs`는 `-Xdoclint:all,-missing`) |

- **루브릭**: `stage11/rubric-b3.md`(레포를 만들기 전에 고정).
- **숨긴 체크**(`stage11-private/b3/checks/<t>/check.py`, 참조 구현 `stage11-private/b3/ref/<t>.patch`, 레포 밖):
  - t160: go build·vet·test; `make release`를 실제로 돌리고(REGISTRY·VERSION 지정) `ko`·`docker`는 인자만 기록하는 PATH 심(`go run github.com/google/ko`도 심으로) — ko build/publish가 `cmd/tracker-ingest`를 push 끄지 않고 KO_DOCKER_REPO와 함께 부름, KO_DOCKER_REPO가 지정한 REGISTRY를 따름, 기존 API 이미지 단계·vet·test 그대로, ko 실패 시 `make release` 실패, Go 파일 불변.
  - t162: go build·vet·test; `goreleaser check` rc 0 또는 2(유효하지만 deprecated, 예: `brews`); 임시 사본에서 `goreleaser release --snapshot --clean`(게시 없음) → 바이너리가 정확히 darwin/arm64·linux/amd64; Homebrew formula/cask 생성·tap 저장소 owner/name·windows 없음; `skip_upload: true` 아님; Go 파일 불변.
  - t118: `make test`; `javadoc -Xdoclint:all -Werror` 통과; 주석 제외 Java 토큰 불변(새 파일은 `package-info.java`만); `reconcileBatch` Javadoc에 `@throws` 5종(CurrencyMismatch, UnmatchedAmount, DuplicateTransaction, IllegalArgument, IllegalState; NPE는 선택), 설명 있음.
- **검증**(`stage11-private/b3/verify_b3.py`, §6 하네스 경로 = 단일 브랜치 클론 → `main`으로 이름 변경 → `origin` 제거 → `--base <s11-r sha>`): 세 체크 모두 시작 상태 **실패**(t160 b·c·e, t162 c·d·e, t118 b·d), 참조 구현 **통과 3/3**, 클론에 보이는 ref는 `refs/heads/main`뿐. 체크 뒤 작업 트리 변경 없음.
  - 대안 풀이·결함 탐침: t160(`cd` 후 `ko build -B .`, `go run …/ko@v build` → 통과; 레지스트리 하드코딩 → c 실패; `-` 접두로 실패 무시 → e 실패; `--push=false` → b 실패), t162(`brews` + `ignore:` → 통과; `skip_upload: true` → e 실패; windows만 뺌 → c 실패), t118(checked 2개만 `@throws` → d 실패; 메시지 문자열 변경 → c 실패; `package-info.java` 추가 → 통과).
  - 검증 중 고친 것 2건: (1) t160 체크가 `/var`→`/private/var` 심볼릭 링크 때문에 임시 클론에서 ko 대상 경로를 못 맞춤 → 세 체크 모두 `realpath`로 비교. (2) 단일 브랜치 클론에도 `refs/remotes/origin/s11-r`와 원본 경로가 남음 → 하네스에서 클론 뒤 `origin` 제거(§6에 추가).
- 동결: `stage11-private/b3/FROZEN.sha256`(체크·참조 구현·검증 스크립트), 공개 파일은 `stage11/FROZEN.sha256`.

### 3.2 묶음 (4) 추가 후보

- Stage 10 §2.1 기준(staging-4에 등급 3 새 레코드, release에 등급 ≥2 없음)을 다시 확인했다(2026-10-25).

| 태스크 | 스택 | 등급 3 (staging-4) | release 등급 ≥2 | 객관 체크 안 |
|---|---|---|---|---|
| **t288** | Rust ratatui | domain-cli | 없음 | ratatui `TestBackend`로 선택 행 굵게·스크롤바 렌더 확인, 기존 테스트 |
| **t266** | Rust axum | m07-concurrency | 없음 | 리사이즈가 `spawn_blocking` 안에서 돌고, 동시 처리 수가 `Semaphore` 한도를 넘지 않음(계측 테스트), 다른 엔드포인트 응답 지연 상한, 기존 테스트 |
| t267 (예비) | Rust | m10-performance | 없음 | ahash 직접 의존, k-mer u64 패킹, 결과 동일 — 성능 자체는 재지 않음 |

- 제안: t288, t266. Stage 10과 같은 방식(요청 원문 그대로, 원문 경로·이름에 맞춘 레포, 레포 밖 숨긴 체크·참조 구현, 시작 커밋 실패·참조 구현 통과 3/3)으로 만든다.

### 3.2.1 묶음 (4) 추가 확인 결과 (2026-10-25)

- **사용자 결정**(실행 전 고정): Stage 10 §2.1과 같은 기준을 블라인드 채점으로 확인 — staging-4 top 50에 등급 ≥2 스킬이 있고, release index에는 없음. 하나라도 기준에 안 맞으면 빼고, 묶음 (4)는 Stage 10의 4개 × 6회(조건당 24세션)로 간다. 비용은 다시 추정만.
- **절차**: `scripts/s11_b4_precheck.py`(§3.1.1과 같은 R-c top-50 합집합 2b 블라인드 채점, 시드 `s11-b4pre-<task>`, Stage 3 원문 그대로, index 해시 확인 뒤). release 쪽은 "release top 50"이 아니라 "release index에 있는 스킬" 전체로 본다(합집합 안에서). $0.195.

| 태스크 | 채점 | staging-4 top 50 등급 ≥2 | release index 등급 ≥2 | 기준 |
|---|---:|---|---|---|
| t288 | 81 | domain-cli (3), uasl/anvil (2) | uasl/anvil (2) | **불충족** |
| t266 | 84 | m07-concurrency (3), domain-web (2), m10-performance (2), rust-patterns (2) | 없음 | 충족 |

  - t288: §3.2의 라벨 기준(v5-ss-b)으로는 release 등급 ≥2가 없었는데, 블라인드 채점에서 uasl/anvil이 2를 받았다.
- **결과**: t288이 불충족이므로 규칙대로 **묶음 (4) = Stage 10의 4개(t016, t263, t115, t198) × 6회**. t266은 기준을 충족했지만 규칙("하나라도 … 4개 × 6회")에 따라 넣지 않았고 레포·체크·루브릭 행을 만들지 않았다.
- **세션 수**: R0·R1 각 (12 + 12 + 18 + 24) = 66 → 132, A 24 → **156**. 비용은 §8.1.

### 3.2.2 정정 (2026-10-25, 실행 전, 사용자)

- **이전 지시의 뜻**은 "기준에 안 맞는 태스크만 뺀다"였다. 지시 문장("하나라도 기준에 안 맞으면 빼고, 묶음 (4)는 Stage 10의 4개 × 6회")이 두 가지로 읽혔고, §3.2.1은 문자 그대로(둘 다 빼기) 읽었다. 지시가 애매했음을 그대로 적는다.
- **정정 결과**: t288 제외, **t266 포함** → 묶음 (4) = Stage 10의 4개(t016, t263, t115, t198) + t266, 6회 → 조건당 30세션. §3.2.1의 "세션 수 156"과 §8.1은 §8.2로 대체한다.
- t266은 묶음 (3)과 같은 방식으로 만든다: 루브릭 행 먼저 고정·해시 → 레포(`s11-a`, `s11-r`) → 숨은 체크(시작 커밋 실패, 참조 구현 3/3, 다른 정답·일부러 넣은 오류 사례) → 하네스 dry-run(클론 점검, 전체 준비).
- **규칙(앞으로)**: 묶음 기준 확인(맞는 스킬 있음/없음)은 라벨이 아니라 **블라인드 채점**(R-c top 50 합집합 2b)으로 한다. 근거: t288은 라벨(v5-ss-b)로는 release에 등급 ≥2가 없었지만 블라인드 채점에서 uasl/anvil이 2를 받았다(§3.2.1).

### 3.2.3 t266 만들기와 검증 (2026-10-25)

- **루브릭 행**: `stage11/rubric-b4-add.md`(레포를 만들기 전에 고정·해시; 형식·척도는 `stage10/rubric-b4.md` 그대로, s11-t266 행만 더함).
- **레포** `repos/s11-t266`: `s11-a` `5c12e69`, `s11-r` `8ae69f5`(라우터 파일만, "chore: add project skill"). Rust crate `cms-api`(axum 0.8.9, tokio 1.54.1, image 0.25.10 png·jpeg, `[profile.dev.package.image]` 등 opt-level 3), `src/routes/media.rs`의 `POST /api/media/resize`가 `media::resize_to_fit`(동기 decode·Lanczos3·PNG encode)를 async 핸들러에서 바로 부른다. articles API·`/healthz`, 기존 테스트 5개. 의존성은 crates.io에서 받아 `~/.cargo` 캐시에 있다(체크는 `--offline`).
  - 만드는 중 <E2 plugin> 훅이 레포 안에 만든 `<E2 plugin>/`가 첫 커밋에 들어가서, 커밋을 고치고(`--amend`) reflog 만료·`gc --prune=now`로 떨어진 객체를 지웠다(남은 unreachable 0).
- **숨은 체크**(`stage11-private/b4/checks/t266/`: `check.py`, `probe.rs`, `zz_s11_probe.rs`; 참조 구현 `stage11-private/b4/ref/t266.patch`):
  - a: 작업 트리에서 `cargo test --offline`(기존·세션 테스트).
  - b–e는 작업 트리의 임시 사본에서: 라이브러리(src/, main.rs·src/bin 제외)의 `image::load_from_memory(…)` 호출을 프로브로 감싸고(`pub mod __s11_probe` 추가), 숨은 테스트를 넣는다. 프로브는 decode가 tokio async 워커 스레드(2워커 런타임, 시작 때 스레드와 일반 태스크가 돈 스레드)에서 도는지, 동시에 몇 개 도는지 기록하고, 48개가 찰 때까지 각 decode를 최대 300 ms 잡아 둔다(제한 없는 폭주는 48까지 보이고 크기 L의 세마포어는 L 이하).
  - b 워커 밖: decode ≥1, 워커에서 돈 decode 0. c 제한: 48개 동시 요청에서 최대 동시 decode 1–32, 응답은 200·429·503만, 200 ≥1. d 다른 API: 폭주 중 `/healthz`·`/api/articles` 모두 성공, 지연 < 200 ms, 타이머 지연 < 200 ms. e 출력: 1600×1200 → 400×400 요청이 400×300, 폭주 중 200 응답이 400×400 이하.
- **검증**: 시작 커밋 **실패**(b: 48개 decode가 워커에서, d: 타이머 지연 8.3 s), 참조 구현 **통과 3/3**(최대 동시 8, 48개 모두 200, 타이머 지연 ≤15 ms), 하네스 경로(`verify_b4.py`, `--no-local` 단일 브랜치 클론)에서 시작 실패·참조 통과.
  - 다른 정답: `try_acquire` → 503(최대 4, 200×4·503×44) 통과; 세마포어 + `spawn_blocking` 안에서 decode를 직접 쓴 풀이 통과.
  - 일부러 넣은 오류: 세마포어 없음 → c 실패(최대 48); `spawn_blocking` 없이 세마포어만 → b·d 실패; `let _ = sem.acquire().await`(허가를 바로 버림) → c 실패(최대 48).
  - 한계(→ §3.2.4에서 바꿈): decode가 `load_from_memory` 계열이 아니면(예: `ImageReader`) 프로브를 못 넣어 b–e가 "프로브 없음"으로 실패했다.

### 3.2.4 t266 체크 개정과 "판정 불가" 규칙 (2026-10-25, 파일럿 전, 사용자 결정)

- **프로브 위치를 바꿈**: 세션 코드의 호출 문자열을 감싸는 대신, 체크의 임시 사본이 쓰는 `image` crate를 패치한 사본으로 바꾼다(`[patch.crates-io] image = { path = … }`, 버전은 사본의 Cargo.lock 그대로, 소스는 `~/.cargo` 레지스트리 캐시). 프로브는 image 0.25의 비공개 `decoder_to_image` 맨 앞에서 불린다 — 공개 디코드 진입점 `load_from_memory`, `load_from_memory_with_format`, `load`, `open`, `ImageReader::decode`(옛 이름 `io::Reader`), `DynamicImage::from_decoder`가 모두 여기로 모인다(소스 확인). 체크 자신이 응답을 decode하는 부분은 `quiet`로 프로브에서 뺀다.
- **판정 불가(실행 전 규칙)**: 프로브를 넣을 수 없거나(image 버전이 캐시에 없음, 버전 여러 개, 주입 지점 없음) 200 응답이 있는데 프로브에 decode가 하나도 안 닿으면(예: `PngDecoder::read_image`로 직접 decode해 `decoder_to_image`를 건너뜀) b·c(프로브를 아예 못 넣으면 숨은 테스트를 안 돌리므로 d·e도)를 `pass: null`로 적고, 다른 항목이 실패하지 않았으면 체크 결과도 `pass: null`, `undecidable: [...]`로 둔다. 다른 항목이 실패했으면 불통과다. 보고서에서는 통과·불통과와 **따로** 센다(조건별 개수).
- **다시 확인**: 시작 커밋 실패(b·d), 참조 구현 통과 3/3(최대 동시 8, 타이머 지연 3 ms), 하네스 경로(`verify_b4.py`) 시작 실패·참조 통과.
  - 다른 정답 4개 통과: `try_acquire` → 503, decode를 `spawn_blocking` 안에 직접, **`ImageReader::new(..).with_guessed_format()?.decode()`**, `image::load(.., ImageFormat::Png)`.
  - 오류 3개: 세마포어 없음 → c 실패(최대 48); `spawn_blocking` 없음 → b·d 실패(워커에서 48, 타이머 지연 7.6 s); 허가를 바로 버림 → c 실패(최대 48).
  - 판정 불가 예: `PngDecoder` + `read_image` → b·c 판정 불가, 체크 결과 `pass: null`.
  - 개정 중 고친 것: 첫 개정판에서 숨은 테스트 자신의 decode(응답 크기 확인)까지 프로브에 잡혀 워커를 막았다 → `quiet`로 뺐다.

## 4. 게이트 (실행 전 고정)

넷을 **모두** 만족하면 staging-4 release. 하나라도 아니면 release하지 않는다.

- **(i)** 묶음 (4) 관련 스킬 로드 비율: R1 > R0. 비율 = 등급 ≥2 스킬을 1개 이상 로드한 세션 수 / 세션 수(조건별 36).
- **(ii)** 모든 묶음에서 R1 ≥ R0 − D. 판정자별로 따로(Claude, GPT).
  - Claude: 조건 점수 = (p1 + p2) / 2의 평균. D_claude(b) = max(max over c ∈ {R0, R1} |mean_p1(c, b) − mean_p2(c, b)|, **0.25**).
  - GPT: 조건 점수 = GPT 점수 평균. D_gpt(b) = max(max over 패스 쌍 x, y ∈ {p1, p2, gpt}, c ∈ {R0, R1} |mean_x(c, b) − mean_y(c, b)|, **0.25**).
  - A는 D 계산에 넣지 않는다.
  - **하한 0.25의 출처**(2026-10-25 추가, 실행 전 고정): 하한 0.25는 Stage 10 재평가 결과를 본 뒤 정한 값이다. 그 값이면 Stage 10에서 불통과한 칸((ii)-GPT 새 묶음 (3), R1 4.667 vs R0 4.889)이 하한 4.639로 통과하게 된다. 그래서 Stage 10 데이터에는 적용하지 않는다(Stage 10 판정 불통과 그대로).
  - **참고 줄**: Stage 11 보고서에는 하한 없는 D(위 식에서 0.25 항을 뺀 값)로 본 게이트 (ii)와 전체 결과도 참고 줄로 같이 쓴다. 판정은 하한 있는 쪽으로만 한다.
- **(iii)** 묶음 (3) 불필요 로드: R1 ≤ R0 + 2. 불필요 로드 = 스킬을 1개 이상 로드한 세션 수(등급과 상관없이, 조건별 18세션 중).
- **(iv)** 모든 묶음에서 중앙 턴: R1 ≤ R0 + 2.
- **보고만**(게이트 아님): 묶음 (4)에서 A 대비 R0·R1의 점수·턴·비용, 묶음 (3) 로드 스킬의 등급 분포, 판정자 간 일치(같은 점수, 차이 ≤1).

## 5. 지표

- 세션: 발화(첫 `search_skills` 턴), 로드한 스킬 id(`load_skills` 결과), 턴, 입력 토큰(캐시 포함), 비용, 벽시계, 객관 체크.
- 로드 등급: 묶음 (4)는 run-c 라벨, 묶음 (3)은 §3.1 실행 전 채점을 먼저 쓰고, 없는 (태스크, 스킬)과 묶음 (1)–(2)는 2b 블라인드 채점(격리 `claude -p`, 태스크마다 1회).
- 판정: Claude 두 패스(p1, p2: 새 하위 에이전트, 새 무작위 코드, 루브릭과 세트 폴더만), GPT 패키지(`stage11/judge-package/gpt/`). 세트 = 태스크 단위, 그 태스크의 모든 세션(묶음 (4)는 A 포함). 형식 검증 뒤 키를 읽는다.
- 루브릭: 묶음 (1) `stage6/6b/rubric-design.md`, (2) `stage2/rubrics.md`, (3) `stage11/rubric-b3.md`(레포 만들기 전에 고정), (4) `stage10/rubric-b4.md` + 추가 태스크 행(레포 만들기 전에 고정).

## 6. 하네스 (Stage 10에서 배운 것을 실행 전에 반영)

- **세션 격리**: 세션마다 `git clone --no-local --single-branch --branch <조건 브랜치>`로 독립 사본을 만들고 브랜치 이름을 `main`으로 바꾸고 `origin`을 지운다(원격 추적 ref·원본 경로가 남지 않게, §3.1.3).
- **툴체인 PATH**: 세션·체크 환경에서만 `/opt/homebrew/opt/openjdk/bin`을 PATH 앞에 넣는다(모든 Stage 11 세션 같게). 셸 프로필은 바꾸지 않는다. go·goreleaser는 `/opt/homebrew/bin`에 있다. 세션이 만든 브랜치가 다른 세션에 보이지 않고, 다른 조건 브랜치 이름도 보이지 않는다(Stage 10 §10의 공유 ref 문제).
- **경로·커밋 이름**: 세션 디렉터리는 무작위 id(조건 이름 없음). 라우터를 넣는 커밋 메시지는 중립("chore: add project skill").
- **메인 체크아웃**: 사전 확인 때 모든 레포가 라우터 없는 시작 커밋에 있는지 검사(Stage 10 nextjs·fastapi `e2e-baseline` 사례).
- **한도 중단**: 최종 답의 한도 문구로 하네스 실패를 판정(턴 수 무관). 끊긴 세션은 `runs/harness-fail/`로 옮기고 재실행. 누적 지출 상한에서 큐 정지.
- **판정 자료**: 체크 출력의 세션 경로 치환, 조건 토큰 감사(0건이어야 함). 묶음 (4)는 최종 답 포함, Stage 10 §4.6의 표시 없는 제거 + 감사 규칙을 그대로 쓴다.
- **체크**: 묶음 (4) 기존 4개는 Stage 10 최종 체크(t115 개정·결함 수정 반영)를 동결해서 쓴다. 새 체크는 레포 밖에 두고 시작 커밋 실패·참조 구현 통과 3/3을 확인한 뒤 동결한다.
- **비공개 파일**: `e2e/stage11-private/`(참조 구현, 숨긴 체크, 키, 세션 원자료). 판정 패키지는 `stage11/judge-package/`에만.

### 6.1 구현과 dry-run 확인 (2026-10-25, 세션 실행 없음)

- **파일**: `scripts/run_s11.py`(세션 1개, `--dry-run [--no-prep]`), `scripts/run_queue_s11.py`(4병렬 큐, `--dry-run`), `scripts/make_jobs_s11.py`(작업 목록), `mcp/mcp-{none,r0,r1}.json`(Stage 10과 같은 내용).
- **조건 브랜치**: 13개 레포 모두 `s11-r` = 시작 브랜치 + 커밋 1개("chore: add project skill", 라우터 파일만, blob sha256 `3efef1e0…f040`). 기존 10개 레포는 `s10-r`이 정확히 시작 + 라우터 파일인지 확인한 뒤 같은 tree로 `commit-tree`했다(작업 트리 안 건드림). A는 시작 브랜치(`s6b-a`/`s10-a`).
- **세션마다 사전 점검**(하나라도 걸리면 세션을 띄우지 않음): index 해시, `s11-r` 구조(부모·바뀐 파일·blob·커밋 메시지), 시작 커밋에 라우터 없음, 본 체크아웃 작업 트리에 라우터 없음, 도구(claude, uvx, go, goreleaser, JDK), 서버 worktree, Postgres(fastapi·6b 체크).
- **클론 상태 점검**: ref가 `refs/heads/main` 하나, remote 없음, status 깨끗, `.claude/skills` 항목 = 시작 커밋의 항목(+ R0·R1은 라우터 파일, sha 일치). 안 맞으면 세션을 띄우지 않는다.
- **세션 디렉터리**: `~/skillfetch-e2e-wt/s11/<무작위 12자리 hex>`(조건·태스크 이름 없음), 체크 뒤 삭제. 조건·태스크는 비공개 출력 경로(`stage11-private/runs/<cond>/<task>-<tag>.*`)와 meta에만 있다.
- **한도·끊김**: `harness_fail` = 결과 이벤트가 오류이고 최종 답에 한도 문구(Stage 10 실제 문구 "You've hit your org's monthly spend limit · run /usage-credits … resets …"로 확인한 표지어). `no_result` = 결과 이벤트 없음(시간 초과 제외). 둘 다 큐를 멈추고 다시 돈다(`runs/harness-fail/`로 옮기는 것은 Stage 10과 같이 손으로).
- **PATH**: 세션·체크 환경에서만 `/opt/homebrew/opt/openjdk/bin`을 앞에 넣는다.
- **dry-run 결과**(`stage11-private/dryrun/`):
  - 큐: 파일럿 6(b3 R0 3·R1 3), 본 실행 156(b1·b2 R0/R1 각 12, b3 각 18, b4 A·R0·R1 각 24), 중복 0. 예상 $73.07 + 쓴 것 $0.68.
  - 본 실행의 (태스크, 조건) 34쌍 전부 `--no-prep`(4병렬): 클론 점검 34/34, ref `refs/heads/main`만, remote 0, 라우터 R0·R1 30/30 있음·A 4/4 없음, 머리 커밋 메시지 R0·R1 모두 중립, MCP 파일 조건별 일치, PATH 맨 앞 JDK, 세션 디렉터리 34개 모두 다름·조건 이름 없음, index 해시 34/34, 끝난 뒤 남은 세션 디렉터리 0.
  - 레포마다 1개(13개) 준비 단계까지(npm ci, uv sync + alembic, cargo build, swift build, go build): 13/13 통과, 준비 뒤 status 깨끗, 남은 `s11_*` DB 0.
- **클론 방식 변경(2026-10-25, §3.2.3 작업 중 발견)**: `--local`은 원본의 objects 디렉터리를 통째로 하드링크해서, 단일 브랜치여도 도달할 수 없는 객체(이전 세션·작업의 커밋)가 클론에 따라온다(nextjs 530개, s2-tests 78개, s10-t016 66개 — `git fsck --unreachable`로 볼 수 있음). `--no-local`(git 전송, 그 브랜치에서 도달할 수 있는 객체만)로 바꿨고 14개 레포 모두 0개다. 클론 점검에 "unreachable 객체 0"을 더했다.
- **dry-run 다시(2026-10-25, `--no-local`·t266 반영)**: 큐 파일럿 9·본 실행 174(b1·b2 R0/R1 각 12, b3 각 18, b4 A·R0·R1 각 30), 중복 0, 예상 $79.60 + 쓴 것 $0.68. (태스크, 조건) 37쌍 `--no-prep`: 클론 점검 37/37, unreachable 객체 합 0, ref `refs/heads/main`만, remote 0, 라우터 R0·R1 32/32·A 0/5, MCP 파일 조건별 일치, PATH 맨 앞 JDK, 디렉터리 37개 모두 다름·조건 이름 없음, index 해시 37/37. 레포 14개 전체 준비: 14/14 통과(t266 cargo build 10.1 s), 준비 뒤 status 깨끗, 남은 세션 디렉터리·`s11_*` DB 0. 묶음 (3) 하네스 경로 검증(`verify_b3.py`)도 `--no-local`로 다시 통과.
- **dry-run에서 고친 것**: fastapi 시작 커밋에 템플릿의 프로젝트 스킬(`.claude/skills/library-skills/`, 심볼릭 링크 `fastapi`·`sqlmodel`)이 있어 처음 점검이 실패했다 → "시작 커밋의 항목 + 라우터"와 비교하도록 고침. 이 스킬은 Stage 10에서도 모든 조건에 있었다.
- **남은 프로세스(2026-10-25, 실행 전 규칙, 사용자 결정)**:
  - **정리**: Stage 10 감사에서 Stage 6b·1b 세션이 띄운 서버가 남아 다른 세션의 `lsof`/`ps`에 보인 것이 확인됐다. 조사(`ps`·`lsof` cwd, 조건: cwd나 인자에 e2e 워크스페이스·`~/skillfetch-e2e-wt`·단계 이름) 결과 Stage 1b 서버 2개(PID 87976 `uv run fastapi run app/main.py --port 18431`, 87981, cwd `s1b-fa-tags-plan-A-r1/backend`, 2026-10-22부터)를 SIGTERM으로 껐다(포트 18431 비움, 프로세스 그룹 비움). 남긴 것: 하네스 Postgres(cwd `e2e/infra/pgdata`, 포트 55432), 이 작업 중인 Claude 세션과 그 MCP·도구 프로세스. 사용자 앱으로 애매한 것 0. 기록 `stage11-private/procs/leftover-2026-10-25.json`.
  - **세션 전 점검**: 위 조건에 맞는 프로세스가 하나라도 있으면(리스닝 여부와 상관없이) 세션을 띄우지 않는다. 예외: 하네스 Postgres, 운영 프로세스의 자손(가장 가까운 `claude` 조상, 없으면 가장 바깥 `run_queue_s11`/`run_s11` 조상 — 큐의 동시 세션 포함).
  - **세션 뒤 정리**: `claude -p`를 자기 프로세스 그룹으로 띄우고(`start_new_session`), 세션이 끝난 뒤와 체크 뒤에 그 그룹이나 세션 디렉터리를 cwd·인자에 가진 프로세스를 SIGTERM → 5초 뒤 SIGKILL → 다시 확인한다. 남은 것은 `meta.leftover_procs`에 적고 큐를 멈춘다.
  - **dry-run 확인**: launchd로 넘어간 가짜 프로세스 (A) cwd `~/skillfetch-e2e-wt/zz-fake-leftover`, (B) cwd는 무관하고 인자에 `s6b-fake-leftover-A-r1`만 → 둘 다 "preflight failed: 1 leftover process"로 막힘. 지운 뒤 통과. (C) `--fake-server`로 세션 디렉터리 안에 분리된 프로세스를 띄움 → 정리가 죽이고 남은 것 0. 37쌍 `--no-prep` 4병렬 다시: 37/37 통과, 남은 프로세스 0(동시 dry-run끼리 막지 않음).
- **알려진 것(조건과 무관, Stage 10과 같음)**: s2-docs 시작 커밋 메시지 "remove README.md (stage 2 docs task)"; 세션이 `ps`를 보면 MCP 서버 인자(index 경로)가 보일 수 있다; 경로에 `skillfetch-e2e-wt`가 있다.
- **아직 확인 안 한 것**: 실제 `claude -p` 세션(스트림·결과 이벤트·비용 집계·체크 연결) — 파일럿 첫 세션(연기 테스트)에서 확인한다. 큐의 비용 정지는 dry-run 투영만 확인했다.

## 7. 순서

1. §3.1 결정(가·나·다) → 묶음 (3)·(4) 레포·체크·루브릭 → 실행 전 확인(묶음 (3) 2b 채점) → 동결.
2. 파일럿(2026-10-25 갱신, §3.2.2 반영): 새 태스크 × 1 = 9세션 — 묶음 (3) 3개 × {R0, R1}, s11-t266 × {A, R0, R1}(`stage11-private/runs/jobs-pilot.txt`, 태그 p1). 2026-10-27 이후. 첫 줄(s11-t118 R1)은 **세션 1개 연기 테스트**로 혼자 먼저 돌리고, 출력(스트림·결과 이벤트·비용·체크·클론 삭제·index 해시)을 확인한 뒤 나머지 5개를 큐로 돌린다.
3. 본 실행 → 채점 → Claude 두 패스 → GPT 패키지 → `report-11.md`(숫자만).

## 8. 비용 추정 (2026-10-25, Stage 10 E1 세션 평균 비용 기준)

| 항목 | 세션 | 세션 평균 (Stage 10) | 추정 |
|---|---:|---|---:|
| 묶음 (1) R0 · R1 | 12 · 12 | $0.708 · $0.745 | $17.4 |
| 묶음 (2) R0 · R1 | 12 · 12 | $0.708 · $0.682 | $16.7 |
| 묶음 (3) R0 · R1 | 18 · 18 | $0.371 · $0.344 (재측정 묶음 (3)) | $12.9 |
| 묶음 (4) R0 · R1 (6태스크) | 36 · 36 | $0.383 · $0.446 | $29.8 |
| 묶음 (4) A (참고) | 36 | $0.258 | $9.3 |
| **본 실행 소계** | **192** | | **$86.1** |
| 파일럿 | 10–12 | | ~$5 |
| 묶음 (3) 실행 전 채점 + 로드 스킬 채점 | – | | ~$1 |
| 하네스 실패 재실행 여유(10%) | – | | ~$9 |
| **합계** | | | **약 $100 (범위 $85–115)** |
| **상한**(사용자 결정) | | | **$115** — 넘을 것 같으면 멈춤 |

- 묶음 (4) 추가가 1개면 본 실행 $79.6, 0개면 $73.1.

### 8.1 다시 추정 (2026-10-25, 묶음 (4) 추가 0개, §3.2.1)

| 항목 | 세션 | 추정 |
|---|---:|---:|
| 묶음 (1) R0 · R1 | 12 · 12 | $17.4 |
| 묶음 (2) R0 · R1 | 12 · 12 | $16.7 |
| 묶음 (3) R0 · R1 | 18 · 18 | $12.9 |
| 묶음 (4) R0 · R1 (4태스크) | 24 · 24 | $19.9 |
| 묶음 (4) A (참고) | 24 | $6.2 |
| **본 실행 소계** | **156** | **$73.1** |
| 파일럿(연기 테스트 포함) | 6 | ~$2.2 |
| 로드 스킬 2b 채점 | – | ~$1 |
| 하네스 실패 재실행 여유(10%) | – | ~$7.3 |
| 지금까지 쓴 것(실행 전 확인 b3 $0.487 + b4 $0.195) | – | $0.68 |
| **합계** | | **약 $84 (범위 $75–100)** — 상한 $115 |

- 세션 평균은 §8과 같은 Stage 10 값이다. 묶음 (3)의 Go·Java 태스크는 Stage 10 묶음 (3)과 비용이 다를 수 있다(빌드·goreleaser 스냅샷·javadoc 실행). 파일럿 뒤 그 값으로 다시 본다.
### 8.2 다시 추정 (2026-10-25, §3.2.2 정정 뒤: 묶음 (4) = 4 + t266)

| 항목 | 세션 | 추정 |
|---|---:|---:|
| 묶음 (1) R0 · R1 | 12 · 12 | $17.4 |
| 묶음 (2) R0 · R1 | 12 · 12 | $16.7 |
| 묶음 (3) R0 · R1 | 18 · 18 | $12.9 |
| 묶음 (4) R0 · R1 (5태스크) | 30 · 30 | $24.9 |
| 묶음 (4) A (참고) | 30 | $7.7 |
| **본 실행 소계** | **174** | **$79.6** |
| 파일럿(연기 테스트 포함) | 9 | ~$3.2 |
| 로드 스킬 2b 채점 | – | ~$1 |
| 하네스 실패 재실행 여유(10%) | – | ~$8.0 |
| 지금까지 쓴 것(실행 전 확인) | – | $0.68 |
| **합계** | | **약 $93 (범위 $80–105)** — 상한 $115 |

- §8.1을 대체한다. t266 세션 평균은 Stage 10 묶음 (4) 값을 쓴다(파일럿 뒤 다시 본다).

- 큐(`run_queue_s11.py`)는 실행 전마다 "지금까지 쓴 것 + 남은 세션 × 세션 추정"이 $115를 넘으면 멈춘다(세션 추정 = 같은 묶음·조건의 Stage 11 세션이 3개 이상이면 그 평균, 아니면 위 Stage 10 값). 실행 전 확인·채점 지출은 `stage11-private/spend-other.json`에 적어 같이 센다.
- 묶음 (3)을 Go 태스크로 하면 세션 비용이 재측정 묶음 (3)과 다를 수 있다(빌드 시간·턴 수). 범위 상단에 넣었다.
- Claude 판정 두 패스는 하위 에이전트(플랜 사용)라 API 환산에 넣지 않는다. GPT 판정은 사용자가 맡는다.
- 시간: Stage 10 E1 세션 207개의 세션+준비 시간 평균 88초(중앙 79초, 체크 시간 제외) → 192세션 4병렬 약 1.2시간 + 체크 시간. 지출 한도로 끊기면 더 길어진다(Stage 10에서 2회).

## 11. 실행 기록

- **2026-10-26 시작**(사용자 지시): 문서의 "실행은 2026-10-27 이후"보다 하루 이르다. 사용자가 출시(2026-10-26) 뒤 결제 설정(추가 사용량 꺼짐)을 확인했다고 알리고 스모크 테스트부터 시작하라고 해서 시작했다. 이 밖의 설계·게이트·상한($115)은 바꾸지 않았다.
- **세션 전 상태**: index 해시 12/12, FROZEN 불일치 0(공개·b3·b4), Postgres 정상, 남은 프로세스 0, Claude Code 2.1.280.
- **스모크 테스트**: 파일럿 첫 줄 s11-t118 R1 p1을 혼자 돌린다(§7).
- **스모크 결과**(s11-t118 R1 p1):
  - **하네스**: 모두 정상.
    - 클론(unreachable 0, 무작위 디렉터리)
    - MCP `connected`, 라우터 발화 → `profile_repo` → `search_skills` → `resolve_and_load`
    - JDK PATH(`javadoc` = openjdk)
    - 결과 이벤트 성공, 13턴, $0.387, 39초
    - 세션 뒤 index 12/12, 프로세스 정리 대상 0, 남은 프로세스 0
  - **체크**: 불통과(b doclint: 생성자·`isClosed` 주석 없음; a·c·d 통과). 측정 결과이고 하네스 결함이 아니다.
  - **로드**: `uasl/receiving-code-review` 1개(묶음 (3) 불필요 로드).
  - **세션 밖 파일**: 세션이 `/tmp/jd`(javadoc 출력)에 썼다. 다음 세션에 보이지 않게 지웠다. 세션이 `/tmp` 같은 공용 경로에 남기는 파일은 하네스가 막지 않는다(기록만).
- **파일럿 결과**(나머지 8세션, 4병렬, 2026-10-26):
  - **하네스**: 하네스 실패 0, 결과 없음 0, index 불일치 0, 남은 프로세스 0, 정리 대상 0. 세션 밖 `/tmp`에 새 파일 0.
  - **체크**: s11-t118 R0는 스모크와 같이 b doclint 불통과. 나머지 7개는 통과했고, t266 판정 불가는 0.
  - **로드**:

    | 세션 | 로드한 스킬 |
    |---|---|
    | s11-t118 R0·R1 | `receiving-code-review` |
    | s11-t160·t162 R0·R1 | 없음(검색만) |
    | s11-t266 R0 | 없음 |
    | s11-t266 R1 | `domain-web`, `m07-concurrency` |
    | s11-t266 A | 검색 없음 |

  - **비용·턴**: 파일럿 세션 합계 $3.566(스모크 포함 9세션), 턴 6–24.
- **본 실행 시작 전 투영**: 쓴 것 $4.25 + 남은 174세션 추정 $80.18 = $84.4 < $115.
- **본 실행 중 하네스 수정**(2026-10-26 11:35경, 세션 14개 뒤):
  - **증상**: 세션 3개(R1 s2-tests-m1, R1 s2-docs-m1, R0 d3-dashboard-m1)가 끝난 뒤 "남은 프로세스" 2개씩을 기록했고, 큐가 규칙대로 새 세션을 멈췄다.
  - **원인**: 6건 모두 **동시에 돌던 다른 세션**의 디자인 체크(`check_6b.py`)가 띄운 `npm exec next start` / `next-server`였다.
    - 체크 서버가 분리돼 launchd 밑으로 가면서 "운영 프로세스의 자손" 예외에서 빠졌다.
    - 그 서버의 작업 디렉터리는 아직 살아 있는 다른 세션 디렉터리였다.
    - 서버는 그 세션의 체크가 스스로 껐다. 주인 세션의 정리 대상은 0, 남은 것도 0이었다.
  - **수정**: 아직 존재하는 세션 디렉터리를 cwd나 인자에 가진 프로세스를 예외로 둔다. 세션 디렉터리는 그 세션의 정리 뒤에만 지워지므로, 디렉터리가 남아 있으면 진행 중인 세션이다.
  - **영향**: 끝난 14세션의 데이터는 그대로 쓴다. `leftover_procs` 기록은 거짓 경보로 표시한다. 수정 뒤 남은 프로세스 0, 남은 세션 디렉터리 0을 확인하고 큐를 다시 시작했다(끝난 작업은 건너뜀).
- **본 실행 완료**(2026-10-26 12:40):
  - 174/174세션. 하네스 실패 0, 결과 없음 0, index 불일치 0. 남은 프로세스 기록은 위의 거짓 경보 3세션뿐이다.
  - 세션 비용 $88.92. 합계 $93.27(파일럿 $3.57 + 실행 전 확인 $0.68 + 로드 스킬 채점 $0.10 포함, 상한 $115).
  - t266 판정 불가 0.
- **판정 준비**:
  - 로드 스킬 39쌍: run-c 라벨 15, 2b 채점 24($0.10).
  - 묶음 (4) 최종 답 가림: R0 22세션, R1 11세션에서 문장을 통째로 지웠다(다듬기 0). A는 0이다.
  - 블라인드 세트 p1·p2·gpt: 각 174개, 16세트, 조건 토큰 감사 0건, 디자인 스크린샷 빠짐 0.
- **Claude 판정**: p1·p2를 새 하위 에이전트 8개(패스 × 묶음 무리)로 돌린다. 각 에이전트는 자기 패스 폴더와 rubrics만 본다. GPT 패키지는 `stage11/judge-package/gpt/`(README 포함)이고, 사용자가 GPT에 전달한다.
- **판정 중 중단**(2026-10-26 12:45경):
  - 조직 월 지출 한도로 Claude 판정 하위 에이전트 6개가 중간에 멈췄다. 그때 끝난 세트는 묶음 (3) p1·p2와 p2 디자인이다.
  - 나머지 5개 묶음은 사용자가 다른 계정으로 로그인한 뒤 같은 지시로 새 에이전트가 다시 판정했다. 멈춘 에이전트가 쓴 파일은 없었다.
  - 세션 실행은 12:40에 이미 끝나 있어 세션 데이터에는 영향이 없다.
- **판정 기록**: s2-docs R1 m1의 diff에 `AGENTS.md`가 있다. 세션이 띄운 `next dev`(Next.js 16)가 만든 파일을 세션이 그대로 남긴 것이다. 하네스 잡음이 아니라 결과물의 일부로 판정됐다. Stage 11 174개 중 1개이고, Stage 10 E1 diff에는 0개다.
- **Claude 판정 결과**(p1·p2 형식 검증 뒤 키 읽음, 각 174점):
  - (i) 묶음 (4) 관련 로드: R1 30/30, R0 0/30 → 예
  - (ii)-Claude(하한 0.25 적용): b1 4.167 vs 4.167, b2 4.750 vs 4.792, b3 4.333 vs 4.583, b4 4.950 vs 4.850 → 4/4 예
    - b3는 정확한 분수로 R1 13/3 = R0 55/12 − 1/4, 여유 0이다(경계에서 통과).
  - (iii) 묶음 (3) 불필요 로드: R1 4/18, R0 6/18 → 예
  - (iv) 중앙 턴: b1 25 vs 23, b2 15.5 vs 16, b3 15.5 vs 16, b4 14 vs 13 → 4/4 예
  - D_claude 원값: b1 1/6, b2 1/4, b3 2/9, b4 1/30
  - 참고 줄(하한 없는 D, 판정 아님): (ii)-Claude b3 아니오(4.333 < 4.583 − 0.222)
  - p1·p2 일치: 같은 점수 151/174, 차이 ≤1 174/174
  - 묶음 (3) 로드 스킬 등급: 모두 1(12개)
  - 판정은 (ii)-GPT를 기다린다(`judge-package/gpt/`, 사용자가 GPT에 전달).
- **조직 월 지출 한도 도달 기록**(2026-10-26, 사용자 요청으로 추가):
  - **시점**: Claude 판정 하위 에이전트 6개가 2026-10-26 12:45:07–12:45:15(KST)에 "You've hit your org's monthly spend limit … resets 1:50pm (Asia/Seoul)"로 멈췄다.
  - **그때까지 Stage 11 비용**(API 환산, 하네스 기록): $93.27.
    - 본 실행 174세션 $88.92(마지막 세션 종료 12:39:47)
    - 파일럿·스모크 9세션 $3.57
    - 실행 전 확인 $0.68
    - 로드 스킬 채점 $0.10
  - 하위 에이전트 판정과 이 작업 세션 자체의 사용량은 하네스가 재지 않아 이 합계에 없다.
  - 같은 달 앞선 기록: Stage 10 $202.43 + $9.51 + 채점 약 $0.5(2026-10-25).
  - 한도 도달 뒤 세션은 띄우지 않았다. 판정은 사용자가 다른 계정으로 로그인한 뒤 다시 돌렸다.
- **GPT 판정과 최종 판정**(2026-10-26):
  - GPT 결과 16세트(174개)를 `judge-package/gpt/`에서 `stage11-private/judge/gpt/`로 옮겼다. 형식 검증 통과 뒤 키를 읽었다.
  - (ii)-GPT(하한 0.25): b1 4.667 vs 4.500, b2 4.167 vs 4.167, b3 3.889 vs 4.056, b4 4.700 vs 4.667 → 4/4 예. D_gpt 원값은 모두 0.25 이상이다(0.583, 0.750, 0.611, 0.267).
  - **최종 판정: 통과**(§4 넷 모두 충족).
  - 참고 줄(하한 없는 D): (ii)-Claude b3만 아니오 → 이 기준이라면 불통과. 판정은 하한 적용 기준이다.
  - 보고서 `stage11/report-11.md`.
