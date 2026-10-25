# 9단계 설계 — 스테이징 index 평가 (세션 실행 없음)

실행 전에 고정한다(2026-10-24). 판정 기준(§2)과 이전 규칙(§3)은 결과를 본 뒤 바꾸지 않는다.

## 0. 입력

- **기준 index**: `~/.skillfetch/index`(index-2026-10-22, 1,724 레코드). 코드는 skillfetch `38dcb69`이다. search 코드는 `cc5d16c` 이후 변경이 없다.
- **스테이징 index**: 레포 세션이 #60 상위 30개 저장소를 넣어 만든 index 디렉터리(경로는 레포 세션이 알려 준다)다. 같은 코드에서 `Index.load(<경로>)`로 읽는다.
- **라벨**:
  - oracle v3(`stage3/followup/oracle-v3.jsonl`)
  - oracle v5-ss-b(`stage8/oracle-v5-ss-b.jsonl`)
  - 매핑 `stage8/source-skill-map.jsonl`(592행; 해시는 `stage8/FROZEN.sha256`)
- **라우터**: 배포 R-c다. 질의는 `stage3/followup/rc-R-c-380.jsonl`의 4개이고, `search_skills(None, queries=…)`, k=50, profile 없음, 기본 tier(A/B)로 부른다.
- **선택**: S-b′(`stage6/select-cands/S-bp/SKILL.md`)를 `stage6/scripts/select_cands.py`와 같은 래퍼·시스템 프롬프트(`stage6/gen/sys-select-S-bp.txt`)·10태스크 묶음·범위 밖 id 재시도로 쓴다. 입력만 스테이징 검색 결과로 바꾼다.

## 1. 전제 확인 (먼저, 실패하면 멈추고 보고)

- 기준 index의 모든 레코드 id가 스테이징에 있고, `content_hash`와 `tier`가 같아야 한다. 라벨이 id로 매겨져 있기 때문이다.
- 다르면 다른 레코드 수와 사례를 보고하고 멈춘다.
- **새 레코드** = 스테이징에만 있는 id다. 저장소별·tier별·status별 수를 보고한다.
  - 기본 tier(A/B) 밖인 새 레코드는 검색에 나오지 않는다. 그 수를 따로 적는다.

## 2. 회귀 판정 (기각 기준)

- **측정**: R-c를 기준 index와 스테이징에서 같은 방식으로 돌리고, 다음 네 값을 잰다.
  - hit@50, recall@50 × {oracle v3, v5-ss-b의 index 스킬}
  - recall@50은 태스크별 |top-50 ∩ R| / |R|의 평균이다.
- **고정 라벨·고정 분모**:
  - 기준 index에서 정한 관련 세트와 분모를 그대로 쓴다(v3 284태스크, v5-ss-b 270태스크).
  - 새 레코드는 이 판정에서 관련으로 치지 않는다.
  - 판정의 질문은 새 스킬이 기존 관련 스킬을 top-50 밖으로 밀어내는가이다.
- **기준선 값**(기준 index, `stage8/followup-8.json`): v3 hit@50 0.930 · recall@50 0.808, v5-ss-b hit@50 0.941 · recall@50 0.822. 스테이징 실행 때 같은 스크립트로 다시 계산해 이 값과 같은지 먼저 확인한다.
- **기각**: 네 값 중 **하나라도** 기준선보다 0.01 넘게 떨어지면 기각한다(#60 "may drop by at most 0.01"을 v3·v5-ss-b 각각에 적용).
- 이전된 라벨로 계산한 같은 네 값도 함께 보고한다. 이 값은 판정에 쓰지 않는다.

## 3. 라벨 이전 (`source-skill-map.jsonl` → 스테이징 새 id)

- **대상 레코드**: 매핑 행마다 스테이징의 **새 레코드** 중 같은 저장소의 것. 저장소가 같다는 것은 레코드 `source_url`의 owner/repo(대소문자 무시)가 행의 `repo`, `renamed_from`, `id_repo` 중 하나와 같다는 뜻이다.
- **매칭 순서**: 먼저 맞는 단계에서 끝낸다.
  1. **SKILL.md 해시**: 행 `skill_md_sha256` = 레코드 `files["SKILL.md"]`. 해시가 같은 레코드는 저장소와 무관하게 찾는다. 기준 index 레코드와 같으면 "이미 index에 있음"으로 따로 센다.
  2. **경로**: 행 `path` = 레코드 `path`(같은 저장소).
  3. **이름/설치 인자**(같은 저장소): 레코드 frontmatter `name` = 행 `name`이거나, 레코드 `path`의 마지막 부분 = `install_skill_arg` 또는 `slug`의 마지막 부분.
- **동률**: 한 단계에서 후보가 여럿이면 canonical 레코드(`canonical_id == id`)만 남긴다. 그래도 여럿이면 "모호"로 두고 이전하지 않는다.
- **여러 행 → 같은 새 id**: 태스크별 최고 등급을 쓴다. `process`는 최고 등급 행의 값이고, 동률이면 하나라도 true면 true다.
- **매칭 안 된 행**: 이유별로 수와 목록을 보고한다.
  - `repo_not_ingested`: 그 저장소의 새 레코드가 0
  - `rejected`: 스테이징 `rejected.jsonl`에 같은 저장소의 경로나 이름이 있음. 거절 이유를 인용한다.
  - `not_found`: 저장소는 들어왔지만 맞는 레코드가 없음
  - `ambiguous`
  - `already_in_baseline`: 해시가 기준 index 레코드와 같음
- **결과 라벨 v5-ss-b-s9**: v5-ss-b에서 이전된 `ss:` 키를 새 id로 바꾼다. 같은 태스크에서 키가 합쳐지면 최고 등급을 쓴다. 이전되지 않은 `ss:` 키는 index 밖으로 남는다.

## 4. 지표 (기준 index 대 스테이징; 판정 아님)

1. **index 관련 태스크 수**: 관련 있는 태스크(expect_none 아님, 관련 ≥1; v5-ss-b에서 331) 중 index 스킬이 관련인 태스크 수다. 기준은 270/331이다.
2. **공백 56 회복**: v3 관련 0·expect_none 아님·trivial 아님 56태스크 중 index 스킬이 관련인 태스크 수를 기준과 스테이징에서 센다. 늘어난 수가 회복이다.
3. **R-c hit@10/@50(·recall@50)**:
   - v5-ss-b-s9 + §5 새 등급의 index 스킬 기준이다.
   - 분모는 두 가지다. (a) 각 index에서 index 관련 태스크, (b) 기준의 270 고정.
4. **S-b′ 오프라인 선택 1회**(스테이징 검색 결과):
   - **관련 로드 비율**: index 관련 태스크 중 로드 세트에 관련 ≥1인 비율
   - **precision**: 태스크 단위와 스킬 단위
   - **불필요 로드**(핵심): 맞는 게 없는 태스크에서 1개 이상 로드한 비율. "맞는 게 없는 태스크" = expect_none이거나, 그 index에서 index 관련 스킬이 0인 태스크다. 다음 셋으로 나눠 낸다.
     - expect_none 40
     - 그 밖의 맞는 것 없는 태스크
     - 스테이징 기준 맞는 것 없는 태스크를 기준 index와 스테이징에 똑같이 적용한 고정 집합
   - **등급 ≤1 로드**: 관련 태스크에서 등급 ≤1 스킬만 로드한 태스크 수
   - **비교**: 기준 index의 S-b′ 3회(`stage6/select-S-bp*.jsonl`)를 같은 라벨로 다시 계산한 값과 그 범위다. 스테이징은 1회라 3회 범위 밖인지를 적는다.
   - 새로 로드된 스킬이 새 레코드인지 기존 레코드인지도 센다.

## 5. 새 후보 채점

- **대상**: 스테이징 R-c top-50과 S-b′ 선택 중 v5-ss-b-s9에 등급이 없는 (태스크, 스킬)이다.
- **방식**: v5-ss-b와 같다. 카드는 title = 이름, summary = 220자 description이다. 프롬프트는 2b 원문(`stage3/gen/sys-grade.txt`)이고, 태스크마다 격리 `claude -p` 1회, 시드 `s9-grade-<태스크>`, 라벨 `m01`…을 쓴다.
- **비용**: 채점 전에 후보 수 × $0.00117을 예상 비용으로 낸다. 이 단가는 v5-ss-b 확장의 실측값($29.37 / 25,020)이다. **$10을 넘으면 채점하지 않고 먼저 보고한다.**
- **S-b′ 선택 1회 비용**(요청된 작업): 6a 반복 실측으로 $6–19다(rep1 $18.65, rep2 $18.40, rep3 $6.05).
- **순서**: 전제 확인 → R-c 검색(두 index) → 회귀 판정 → 라벨 이전 → S-b′ 선택 1회 → 새 후보 수·비용 보고(> $10이면 멈춤) → 채점 → 지표.
- 회귀에서 기각되어도 지표는 계산해 함께 보고한다.

## 6. 산출물

- `stage9/report-9.md`
- `stage9/oracle-v5-ss-b-s9.jsonl`, `stage9/migration.json`(행별 매칭 단계와 이유)
- `stage9/results-rc-staging.json`, `stage9/select-S-bp-staging.jsonl`
- `stage9/FROZEN.sha256`

## 7. 실행 전 점검 (2026-10-24, 스테이징 index 없이 기준 index로 dry run)

- 기준 index로 R-c를 돌리면 `stage6/gen/results-rc.json`과 380/380 같다(`dry/results-rc-baseline.json`).
- 기준 index를 스테이징 자리에 넣으면:
  - 전제 확인 통과, 새 레코드 0
  - 회귀 Δ 0. 기준선 v3 hit@50 0.9296 · recall@50 0.8082, v5-ss-b 0.9407 · 0.8222로 Stage 8 값과 같다.
  - 라벨 이전 592행 모두 `repo_not_ingested`
  - 채점 대상 0
- **기준선 지표**(v5-ss-b):
  - index 관련 태스크 270/331
  - 공백 56 중 index 관련 17
  - R-c hit@10 0.556 · hit@50 0.941 · recall@50 0.822
  - S-b′ r1–r3 (맞는 것 없는 태스크 110개 = expect_none 40 + 그 밖 70):
    - 관련 로드 0.630–0.637
    - precision(태스크) 0.742–0.758
    - 불필요 로드 0.264–0.300 (r1: expect_none 7/40, 그 밖 22/70)
- **합성 스테이징 테스트**: 기준 index에 매핑 행에서 만든 가짜 레코드 6개와 거절 레코드 1개를 더했다.
  - 해시·경로·이름 단계가 각각 맞았다.
  - 같은 저장소의 동명 2개는 `ambiguous`, 거절 레코드는 `rejected`(scan_failed, exfil.secret-env)로 분류됐다.
  - 이름만 바뀐 두 id(affaan-m/ecc, affaan-m/everything-claude-code)는 한 새 id로 합쳐져 태스크별 최고 등급이 남았다.
  - 그 뒤 출력은 지웠다.
- **실행 명령**(스테이징 경로 `<S>`):
  1. `scripts/s9_precheck.py <S>`
  2. `uvx … s9_search.py <S> results-rc-staging.json`
  3. `s9_regress.py dry/results-rc-baseline.json results-rc-staging.json`
  4. `s9_migrate.py <S>`
  5. `s9_select.py results-rc-staging.json select-S-bp-staging.jsonl --run` (예상 $6–19)
  6. `s9_grade.py <S> results-rc-staging.json select-S-bp-staging.jsonl` (비용 확인; $10 이하면 `--run`, 넘으면 보고)
  7. `s9_metrics.py <S> dry/results-rc-baseline.json results-rc-staging.json select-S-bp-staging.jsonl`

## 8. 승인 (2026-10-24)

- 사용자가 §1–§4의 네 결정을 모두 승인했다.
  - 기각: 네 값 중 하나라도 0.01 초과 하락
  - 고정 라벨·고정 분모 회귀
  - 전제 확인
  - 라벨 이전 규칙
- 스테이징 index 경로는 레포 세션이 만든 뒤 사용자가 알려 준다. 그때 §7 순서대로 진행한다.
- S-b′ 선택 1회($6–19)는 요청된 작업이다. 새 후보 채점은 예상이 $10을 넘으면 먼저 보고한다.

## 9. 선행 조건 수정 (2026-10-24, 실행 전; §1을 대체)

- **스테이징 경로**: `~/github/skillfetch/data/index-staging`(레포 세션 보고 `data/index-staging-reports/report.md`, 2026-10-24T11:32:16Z 빌드).
  - 새 소스는 affaan-m/ECC, ahmed3elshaer/everything-claude-code-mobile, rshankras/claude-code-apple-skills, actionbook/rust-skills, dpearson2699/swift-ios-skills 5개다.
- **release**: `~/.skillfetch/index`(index-2026-10-22)다. 레포 `data/index`와 파일이 같은지 먼저 확인한다.
- **조건**(사용자 지시):
  1. **skills.jsonl·rejected.jsonl**: release와 바이트 단위로 같아야 한다.
     - 스테이징은 새 레코드를 더하므로 파일 전체는 같을 수 없다. 그래서 다음 뜻으로 적용한다.
       - release 파일의 **모든 줄이 스테이징 파일에 바이트 단위로 그대로** 있다.
       - 스테이징의 나머지 줄은 release에 없는 id의 새 레코드다. 같은 id가 다른 바이트로 있으면 안 된다.
  2. **constraints.jsonl**: release 스킬의 제약은 `fan_out` 표시만 다를 수 있다.
     - 이유: 새 스킬이 추가되면 constraints.md §3 row 14a(fan-out cap) 기준을 넘는 제약이 생긴다.
     - 비교 방법: 스킬마다 release 제약 줄과 스테이징 제약 줄을 `fan_out`을 뺀 JSON으로 비교한다(다중집합 비교, 개수 포함).
     - `fan_out` 값이 바뀐 수를 보고한다.
  3. 위 세 파일에서 그 밖의 차이가 있으면 멈추고 보고한다.
- **나머지 파일**: `manifest.json`, `dupgroups.json`, `pairs.jsonl`은 새 소스를 넣으면 바뀌는 파일이고 조건 대상이 아니다. 차이를 보고한다.
  - manifest: 소스 목록과 파일 해시
  - dupgroups: release 그룹이 스테이징에 그대로 있는지
  - pairs: 있는지와 줄 수
- **검색·오프라인 선택이 constraints를 쓰지 않는 근거**(skillfetch `38dcb69` 소스):
  - `index/search.py` `Searcher.__init__`는 `index.canonical()`(skills.jsonl 레코드 중 `canonical_id == id`)만 BM25에 넣는다. 필드는 title, description, keywords, synthetic_queries, summary다.
  - `Searcher.search`는 `index.records`의 `tier`·`tags`·`summary`·`token_estimate`만 읽는다. `search_many`는 그 결과를 RRF로 합칠 뿐이다.
  - `Index.constraints`·`dupgroups`·`pairs`는 `Index.skill()`과 `verdicts()`(resolve_set·충돌 판정)에서만 쓰인다.
  - `index/loader.py` `Index.load`는 constraints.jsonl을 파싱한다(필수 파일, manifest 해시 검사). 검색 결과에는 영향이 없다.
  - 오프라인 선택(`s9_select.py`)의 입력은 `search_skills` 출력(id, title, summary, tier, token_estimate)과 요청·질의뿐이다. `resolve_set`을 부르지 않는다.
  - 따라서 fan_out 차이는 검색·선택 지표에 영향이 없다.
  - 단, BM25의 IDF·평균 문서 길이는 전체 canonical 레코드로 계산된다. 그래서 새 레코드가 기존 스킬의 점수와 순위를 바꿀 수 있다. 이것은 §2 회귀 판정이 재는 대상이다.
- `scripts/s9_precheck.py`를 이 조건으로 바꾼 뒤 실행한다(§7 1단계).

## 10. 재실행 run-b (2026-10-24, 실행 전 기록; §2 판정 기준·§3 이전 규칙·§5 비용 규칙·§9 선행 조건은 그대로)

- **스테이징**: `~/github/skillfetch/data/index-staging-2`(레포 세션 재빌드, 2026-10-24T12:13:33Z; 보고 `data/index-staging-2-reports/report.md`).
  - 소스는 첫 스테이징과 같은 5개다. rshankras는 하위 스킬까지 183개를 넣었다. `dupgroups.json`은 760 B에서 49.5 KB로 커졌다.
- **출력**: 첫 실행(`index-staging`)의 파일과 `report-9.md`는 그대로 둔다. run-b 출력은 `stage9/run-b/`에 쓰고, 보고서는 `report-9b.md`다.
- **스크립트 변경**(출력 위치만): `s9_common.py`에 `S9_RUN` 환경변수를 더했다.
  - 기본 ""는 `stage9/`(첫 실행과 같은 위치)이고, `run-b`는 `stage9/run-b/`다.
  - 다섯 스크립트의 결과 파일 경로를 `OUT`으로 바꿨다.
  - `s9_grade.py`의 캐시 이름에 run 이름을 넣었다(`s9run-b-grade-<태스크>`). 채점 셔플 시드(`s9-grade-<태스크>`)는 그대로다.
  - 선택 출력 파일 이름은 `run-b/select-S-bp-staging-2.jsonl`이다. 선택 캐시 이름이 파일 이름(stem)에서 나오므로, 첫 실행 캐시(`s9-select-S-bp-staging-*`)와 겹치지 않는다.
  - 첫 실행 때의 스크립트 해시는 `FROZEN-run1.sha256`에 남긴다.
- **기준선**: 같은 기준 결과 `dry/results-rc-baseline.json`과 같은 기준 S-b′ 3회를 쓴다.

## 11. run-c 판정 규칙 (2026-10-24, run-b §5 채점 전에 기록; run-b 판정은 바꾸지 않음 — run-b는 기각)

**통과 = (A) 또는 ((B) 그리고 (C)). 둘 다 아니면 기각.**

- **(A) 기존 대체 검사**: §2를 그대로 쓴다. 고정 라벨·고정 분모에서 R-c hit@50·recall@50 × {v3, v5-ss-b} 네 값 중 0.01 넘게 떨어진 것이 없다.
- **(B) 전체 라벨 기준 R-c hit@50**: v3와 v5-ss-b 두 라벨 모두에서 기준선보다 0.01 넘게 떨어지지 않는다.
  - **전체 라벨**:
    - 기준 라벨의 관련 세트(v3 relevant, v5-ss-b의 기준 index 스킬 등급 ≥2)
    - ∪ 스테이징 새 레코드 중 등급 ≥2. 새 레코드 등급은 §3 이전 라벨과 §5 새 채점(`oracle-v5-ss-b-s9g.jsonl`)에서 온다.
    - 새 레코드 등급은 두 라벨에 같이 쓴다. v3에는 새 레코드 라벨이 없기 때문이다.
  - **분모**: 기준 index의 분모를 그대로 쓴다(v3 284태스크, v5-ss-b 270태스크). 같은 태스크에서 새 관련 스킬이 top-50에 들면 적중으로 센다.
  - **기준선**: 기준 index의 hit@50(v3 0.930, v5-ss-b 0.941)이다. 기준 index에는 새 레코드가 없으므로 전체 라벨로 계산해도 값이 같다.
  - 각자 분모(스테이징에서 관련 ≥1인 태스크) 값도 보고한다. 판정에는 쓰지 않는다.
- **(C) S-b′ 불필요 로드**: 스테이징 S-b′ 선택 1회의 불필요 로드율이 0.300 이하다. 0.300은 기준 index S-b′ 3회 범위 0.264–0.300의 상단이다.
  - 맞는 것 없는 태스크(§4-4 정의)는 expect_none이거나, 전체 라벨에서 스테이징 index 관련 스킬이 0인 태스크다.
  - 비율은 그 태스크 중 1개 이상 로드한 비율이다.
- **(B)·(C) 계산에는 §5 채점이 끝나야 한다.** 채점 비용이 $10을 넘으면 §5 규칙대로 먼저 보고한다.
- 구현: `scripts/s9_verdict_c.py`(아래 run-b 채점 뒤 참고 계산에도 같은 코드를 쓴다).

## 12. run-b 후속 (2026-10-24, 결과를 보기 전에 기록; run-b 판정 기각은 그대로)

1. **배치 효과 검사**(`scripts/s9_batch_check.py`):
   - **표본**: run-b 라벨(`run-b/oracle-v5-ss-b-s9g.jsonl`)에서 고른다.
     - 새 레코드 행: §5 채점 행. 출처 `s9-grade`, 스테이징 새 레코드, 10,546행.
     - 기존 후보 행: 기준 index 스킬 행. v5-ss 본채점 4,031행 + v5-ss-b 확장 25,020행.
   - **추출**: 각 종류가 5행 이상 있는 태스크에서 시드 `s9b-batch`로 60태스크를 고른다. 태스크마다 새 레코드 5행 + 기존 후보 5행을 무작위로 뽑는다. 합계는 새 300 + 기존 300이다.
   - **채점**: 태스크마다 10행을 섞은(시드 `s9b-batch-<태스크>`) 한 목록으로 같은 2b 프롬프트(`stage3/gen/sys-grade.txt`)·같은 카드(title = 이름, summary = 220자 description)·격리 `claude -p`(Opus) 1회로 다시 채점한다. 출처와 이전 등급은 넣지 않는다.
   - **보고**: 원래 등급과의 완전 일치, ±1 일치, 관련 여부(≥2) κ, 평균 등급 차(재채점 − 원래)를 새 레코드 / 기존 후보로 나눠 낸다. 기존 후보는 출처(v5-ss 본채점 / v5-ss-b 확장)별로도 낸다.
   - **해석 규칙**(미리 고정): 새 레코드 쪽만 평균 등급이 내려가면(재채점 − 원래 < 0) 배치 효과로 본다. 기존 후보 쪽 변화와 비교해 "새 레코드만 내려감"을 판단한다. 두 쪽 차이가 표본 오차보다 큰지는 행 단위 부트스트랩 95% 구간(2,000회)으로 함께 보인다.
2. **GPT 교차 라벨 파일** `blind-run-b-60.jsonl`(`scripts/s9_make_blind_60.py`):
   - **태스크 추출**: 스테이징(run-b) R-c top-10에 새 레코드가 1개 이상인 태스크 중 60개다. 시드 `s9b-gpt60`, 작업종류 비례(최대 잔여), 작업종류 안에서는 표현(phrasing) 순환으로 고른다.
   - **행**: 태스크마다 스테이징 top-10의 새 레코드 행 전부(n개)와 기존 레코드 행 n개다.
     - 기존 레코드 행은 스테이징 top-10의 기존 레코드에서 순위순으로 먼저 채운다. 모자라면 기준 index R-c top-10(밀려난 자리)에서 순위순으로 채운다.
     - 그래도 모자라면 있는 만큼만 넣고 수를 보고한다.
   - **필드**: task_id, task_text, candidate_id(불투명 `g01`…), title, summary. 출처·이전 등급은 넣지 않는다.
   - 행 순서는 태스크 안에서 시드로 섞는다. 대응표는 `blind-run-b-60-key.json`에 따로 둔다.
   - **GPT 결과**(`gpt-run-b-60.jsonl`: task_id, candidate_id, grade, process)가 오면 다음을 계산한다(`scripts/s9_gpt_run_b.py`).
     - 일치: 완전 일치, ±1, 관련 여부 κ, process κ. 새 레코드 / 기존으로 나눠서도 낸다.
     - **교집합 라벨**: 60태스크에서 GPT가 본 행은 Opus ≥2 그리고 GPT ≥2일 때만 관련이다. GPT가 보지 않은 행은 Opus 등급을 그대로 쓴다.
     - 교집합 라벨로 60태스크의 R-c hit@10(v5-ss-b 전체 라벨, 기준 index 대 스테이징)과 S-b′ 관련 로드(기준 3회 대 스테이징 1회)를 다시 계산한다. GPT가 덮은 행의 비율(top-10 자리, 선택)도 보고한다.
3. **run-c 예상치**(`scripts/s9_search_excl.py`):
   - `index-staging-2`를 읽은 뒤 `dpearson2699-swift-ios-skills/` 레코드를 `index.records`에서 지우고 Searcher를 만든다. 그 위에서 R-c(같은 질의·k=50)를 돌린다.
     - dpearson 레코드 86개는 모두 canonical이고 어떤 dupgroup에도 없다. 그래서 그 소스를 빼고 다시 빌드한 index와 검색 입력이 같다(다른 레코드가 바이트 단위로 같다는 전제).
   - **계산**: 전체 라벨(run-b 라벨) 기준 R-c hit@10/@50(v3·v5-ss-b, 기준 분모)과 §11 (A) 값이다.
   - 새로 top-50에 들어온 미채점 행은 수를 보고한다. 채점하지 않고 무관으로 처리한 하한이다.
   - S-b′ 선택이 없으므로 §11 (C)는 계산하지 않는다. 이 값은 run-c 판정이 아니라 예상치다.
4. **비용**: 실행 전에 추정한다. $10을 넘으면 먼저 보고한다.

## 13. run-c (2026-10-24, 실행 전 기록; 판정은 §11, 선행 조건은 §9, 이전 규칙은 §3)

- **스테이징**: `~/github/skillfetch/data/index-staging-3`(빌드 2026-10-24T14:38:55Z). 소스는 run-b에서 dpearson2699를 뺀 5개다.
  - 빌드 보고상 rshankras가 이번에는 tier B 175 / C 5다(run-b: B 23 / C 157). §12-3 오프라인 예상치의 전제("dpearson 밖 레코드가 run-b와 같다")는 rshankras에서 맞지 않을 수 있다. 실제 차이는 아래 검사에서 센다.
- **출력**: `stage9/run-c/`(`S9_RUN=run-c`), 보고서 `report-9c.md`. 선택 파일은 `run-c/select-S-bp-staging-3.jsonl`이고, 캐시 이름이 run-b와 겹치지 않는다.
- **선행 조건**: §9와 같다. 더해서, 사용자 지시로 release 대비 `fan_out`이 바뀐 constraints 줄을 직접 확인한다.
  - 그 줄들을 release와 스테이징에서 원문 그대로 꺼내 `"fan_out": false`↔`true`만 바꿨을 때 바이트 단위로 같은지 본다. 원문 쌍도 보고서에 싣는다.
- **run-b 대비 레코드 비교**(보고용): 스테이징-3의 새 레코드 중 run-b(스테이징-2)에 같은 id가 있는 수, 줄이 바이트 단위로 같은 수, run-b에 없는 id 수를 저장소별로 센다.
- **라벨**: 다음 순서로 만든다.
  1. §3 이전(`source-skill-map.jsonl` → 스테이징-3 새 id) 결과 `run-c/oracle-v5-ss-b-s9.jsonl`
  2. **run-b 채점 이월**: run-b §5 채점 행(`run-b/oracle-v5-ss-b-s9g.jsonl`, 출처 `s9-grade`) 중 다음을 모두 만족하는 행만 그대로 옮긴다(`scripts/s9_carry.py`, 결과는 같은 파일을 덮어씀).
     - id가 스테이징-3에 있다(id에는 내용 해시가 들어 있다).
     - 채점 카드(이름, 220자 description)가 run-b 때와 같다.
     - 그 태스크에서 아직 등급이 없다(이전 라벨이 우선).
  3. §5 채점: 스테이징-3 top-50 ∪ S-b′ 선택 중 아직 등급이 없는 행만 채점한다.
- **승인된 지출**(사용자, 2026-10-24): S-b′ 선택 1회(약 $20), 새로 top-50에 든 미채점 행 채점(약 $3–4).
  - 채점 예상이 $10을 넘으면 §5 규칙대로 멈추고 보고한다.
  - $10 이하이지만 $4를 크게 넘으면 실행하고, 그 사실을 보고한다.
- **판정**: `scripts/s9_verdict_c.py`(§11)를 쓴다. (B)는 미채점이 0인 확정치여야 한다. 미채점이 남으면 그 수를 보고하고 "하한"으로 표시한다.
- **실행 전 발견(2026-10-24, run-c 결과를 보기 전)**: `index-staging-2`는 run-b 도중에 같은 경로에서 다시 빌드됐다.
  - run-b가 평가한 빌드: 12:13:33Z. precheck·검색·이전·선택이 이 빌드를 읽었다(21:20–21:23).
  - 같은 경로의 새 빌드: 12:27:18Z, 21:27 생성. rshankras가 추출되어 tier B 175 / C 5가 됐다. id 2,871개는 같다.
  - run-b의 §5 채점 카드, `metrics-9.json`, `verdict-11.json`은 23:27에 새 빌드의 레코드를 읽었다.
  - 그래서 run-b의 순위·선택은 12:13Z 빌드의 것이고, 그 빌드는 디스크에 남아 있지 않다.
  - 스테이징-3의 새 레코드 1,061개는 **현재** `index-staging-2`(12:27Z)와 바이트 단위로 같다(`run-c/vs-run-b.json`). run-b가 평가한 12:13Z 빌드와는 rshankras 레코드가 다르다(tier).
  - 이월 규칙은 그대로 둔다. id에 내용 해시가 들어 있고, 카드(이름·description)는 12:27Z 빌드 기준으로 같은지 확인한다.
