# 8단계 설계 — Skillselion 비교 (설계 → 파일럿 → 본 실행)

## 0. 이용 조건 확인 (2026-10-24, 실행 전)

- **Terms** (https://skillselion.com/terms, last updated 21 October 2026):
  - "You may browse, search and use the directory for your own building and research. You agree not to scrape it abusively, disrupt the service, misuse the accounts of others, or use Skillselion for anything unlawful."
  - 자동화된 질의를 금지하는 조항은 없다. 금지는 "abusive" 스크래핑과 서비스 방해다.
- **MCP 페이지** (https://skillselion.com/skillselion-mcp): "free & read-only", "No auth, no secrets"이다. 질의는 수요 신호로 전송되고 `DO_NOT_TRACK=1`(또는 `SK_NO_DEMAND=1`)로 끈다. 사용량 제한 문구는 없다.
- **판단**: 허용된다. 연구 목적이고, 질의는 순차로 보내며, 요청 간 ≥ 1초를 두고, 총량은 약 1,150회다. 수요 신호는 끈다.
- **실행 조건**:
  - `DO_NOT_TRACK=1`, `SK_NO_DEMAND=1`
  - 도구 호출 사이 ≥ 1초(순차, 동시 1)
  - `GITHUB_TOKEN`은 설정하지 않는다. 필요하면 읽기 전용 토큰만 쓴다. 미설정이면 `load_skill`의 GitHub tree API가 60회/시간 제한에 걸릴 수 있고, 클라이언트는 그때 SKILL.md 본문만 가져온다(index.js 주석).
  - 작업 디렉터리는 빈 폴더 `stage8/iso/`다. 클라이언트가 cwd의 저장소로 순위를 맞추는 기능(`repoCategories(process.cwd())`)이 우리 레포에 영향받지 않게 하려는 것이다.
- **클라이언트**: npm `skillselion-mcp@0.9.11` (gitHead `f0127de3274895fdae743215d8b71752287ff41a`; GitHub `skillselion/skillselion-mcp`). 서버 API는 `https://skillselion.com/api/upstream`.
- **클라이언트 동작 메모(소스 기준)**:
  - 200자 자르기(`scrubQuery`)는 수요 신호에만 적용된다. 검색 질의 자체는 자르지 않는다.
  - 키워드 경로는 120자를 넘는 변형을 건너뛰고 짧은 변형(유의어 묶음, 앞·뒤 두 단어, 가장 긴 단어)으로 찾는다. 의미 검색 풀은 질의 전체를 쓴다.
  - 그래서 SS-q1은 태스크 원문을 그대로 넘기고, 클라이언트가 하는 처리를 그대로 둔다.
  - `search_skillselion`의 `limit`는 최대 25다. 관련성 하한(`clearsFloor`)을 통과한 것만 돌려준다.

## 1. 파일럿 (10태스크, 2026-10-24) — `pilot-summary.json`, `raw/pilot.jsonl`

- 태스크: 시드 `s8-pilot`로 관련 있는 태스크 8개와 expect_none 2개를 골랐다. 호출 30회, 오류 0이다.
- 서버 `serverInfo.version`은 `0.9.10`이다(npm 패키지는 `0.9.11`; 클라이언트 상수 차이로 보이며 기록만 한다).
- **결과 수**(`type=skill`, `limit=25`; 관련성 하한을 통과한 것만 온다):
  - SS-q1: 18, 20, 17, 11, 17, 4, 1, 3, 7, 16
  - SS-q3: 17, 23, 9, 14, 19, 19, 7, 14, 16, 18
- **k 고정**: 검색은 `limit=25`(최댓값)로 부른다. hit@1/@5/@10은 돌아온 목록 안에서 센다. 목록이 k보다 짧으면 그만큼만 보고, 빈 목록은 적중 0이다.
- **load_skill**: 고른 스킬과 "Or switch to" 후보 2개, 로컬 임시 폴더의 SKILL.md와 번들 파일을 돌려준다(10회 중 9회에 번들 파일 목록이 있었다; 호출 시간 전체 중앙 1.45 s, p95 2.28 s, 최대 3.36 s). 본문은 호출 직후 그 폴더에서 `raw/load/<task>/`로 복사한다.
- **지연**: 클라이언트 쪽 도구 호출 시간이다. 한 호출이 서버 API를 여러 번 부른다(키워드 풀 2, 의미 풀 1, lessons 1). 그래서 "그쪽 서버 기준"은 도구 호출 단위의 왕복 시간으로 잰다.
- **우리 index 대응**: (저장소, 이름)이 같은 경우는 SS 검색 결과 270행 중 1행뿐이다. 우리 index는 같은 스킬을 다른 출처(예: 묶음 저장소)로 담은 경우가 많다. 그래서 거의 모든 SS 결과를 새로 채점한다.

## 2. 지표 (실행 전 고정)

- **라벨 oracle v5-ss**:
  - 태스크마다 후보 = SS-q1 결과 ∪ SS-q3 결과 ∪ SS-load 선택 ∪ SF R-c top-10 ∪ SF 선택(S-b′ 3회)이다.
  - 출처를 숨기고 섞어(고정 시드) 2b 프롬프트(`stage3/gen/sys-grade.txt`)로 채점한다. 태스크마다 격리 `claude -p` 1회다.
  - **카드는 모든 후보에 같은 형식**(이름 + 설명)으로 준다.
    - SS 결과는 검색 출력의 설명(클라이언트가 220자로 자른 것)을 쓴다.
    - 우리 index 스킬은 frontmatter `description`을 같은 규칙(220자, 넘으면 217자 + "...")으로 자른다. tags는 넣지 않는다(SS 쪽에 없어서 출처가 드러난다).
  - 같은 저장소·경로(+ 내용 해시 일치)인 SS 결과는 우리 index id로 합친다(한 후보로 채점).
  - 60태스크 표본(시드 `s8-gpt60`, 작업종류·표현 층화)을 같은 블라인드 행으로 `blind-ss-60.jsonl`에 내보낸다(GPT 교차 라벨용).
- **hit@1/@5/@10**:
  - 대상은 v5-ss에서 관련(등급 ≥2) 스킬이 있는, expect_none이 아닌 태스크다(분모는 새로 계산).
  - 비교는 SF(R-c top-50 순위) vs SS-q1 vs SS-q3.
  - 적중 = 그 순위의 상위 k 안에 관련 스킬이 1개 이상.
- **최종 로드**:
  - SF 선택 세트(S-b′ 3회 각각, 평균) vs SS-load 1개
  - 관련 적중률: 관련 있는 태스크에서 로드한 것 중 관련이 1개 이상
  - 관련 없는 태스크에서 1개 이상 로드한 비율(SF는 none을 고를 수 있고, SS-load는 항상 1개다)
- **index 밖 관련 스킬**:
  - SS가 찾았고 v5-ss 등급 ≥2이며 우리 index에 없는 스킬 수
  - "없음"은 (저장소, 이름) 대응도 없고, 이름이 같은 우리 스킬과 SKILL.md 본문 해시도 다른 경우다
  - 그중 56개 공백 태스크(3단계 oracle에서 관련 0인 사소하지 않은 태스크)에 해당하는 수
- **검증**: SS-load가 로드한 본문 전부(SKILL.md + 번들 파일)에 skillfetch `scan`(lint, injection scan, scripts)과 라이선스 확인을 돌린다. 걸린 비율과 사례(원문 인용)를 낸다.
- **지연**: 도구 호출당 시간의 중앙값과 p95. 종류별로(SS-q1, SS-q3, SS-load) 낸다.
- **보고**: "어느 쪽이 낫다"는 결론 문장은 쓰지 않는다. 지표별 숫자와 한계만 쓴다. 첫 단락에 우리 벤치마크·라벨·라우터 문구가 우리 시스템에 맞춰 만들어졌다는 점을 적는다.

## 3. 본 실행 전 결정이 필요한 것 (파일럿 보고 시 질문)

1. `load_skill`의 번들 파일은 GitHub tree API(인증 없이 60회/시간)로 받는다. 380회를 쓰려면 읽기 전용 `GITHUB_TOKEN`을 받거나, 60회를 넘은 뒤는 SKILL.md만 받는 폴백을 그대로 받아들여야 한다(검증 지표의 scripts 범위가 줄어든다).
2. SS-load의 질의: 지시대로 태스크 원문을 쓰면, 도구 설명("2–6 words, ONE topic")과 다르게 쓰는 셈이다. 파일럿에서 FastAPI 텔레메트리 태스크에 `feature-sliced-design`이 로드됐다. 원문 그대로 둘지, R-c 첫 문장 판본(SS-load-q3)을 함께 돌릴지 정해야 한다.

## 2-추가. 본 실행 결정 (2026-10-24, 본 실행 전에 기록; §2의 다른 규칙은 그대로)

1. **GitHub 토큰**: 사용자가 준 읽기 전용 fine-grained 토큰(`<credentials file>`의 `GITHUB_PAT_TOKEN`)을 쓴다.
   - `ss_client.py`가 실행 시 그 파일에서 값을 읽어 **MCP 서버 자식 프로세스의 env(`GITHUB_TOKEN`)에만** 넣는다.
   - 값은 출력·로그·보고서·파일 어디에도 쓰지 않는다. 실행 뒤 `raw/` 전체에 토큰 문자열이 없는지 검사하고, 그 결과(있음/없음)만 적는다.
   - 확인한 것: 접두사 `github_pat_`(fine-grained), `/rate_limit` 응답의 한도 5000. 토큰의 권한 목록은 API로 조회되지 않는다.
   - 클라이언트는 이 토큰을 GitHub tree/raw GET에만 쓴다(index.js `ghHeaders`). `load_skill`은 먼저 Skillselion 자체 저장소(`/api/skills/:id/files`)에서 받고, 실패할 때만 GitHub로 간다.
2. **질의 조건 5개** (태스크마다 이 순서로 순차 호출, 380태스크 × 5 = 1,900회; §0의 "약 1,150회"를 대체):
   - **SS-q1**: `search_skillselion(query=태스크 원문, type=skill, limit=25)` (파일럿과 같음)
   - **SS-q3**: `search_skillselion(query=R-c 첫 질의, type=skill, limit=25)` (파일럿과 같음)
   - **SS-kw**: `search_skillselion(query=kw 질의, type=skill, limit=25)`
   - **SS-load-kw (주)**: `load_skill(query=kw 질의, context=태스크 원문)`
   - **SS-load-full (보조)**: `load_skill(query=태스크 원문, context=태스크 원문)` (파일럿의 SS-load)
   - 검색 세 조건은 `context`를 넘기지 않는다. 두 load 조건은 `context`가 같고, 질의만 다르다.
3. **kw 질의 생성**:
   - 380태스크마다 격리 `claude -p` 1회(도구 없음, MCP 없음, project 설정만; stage6 `batch.py`와 같은 방식)를 쓴다.
   - 시스템 프롬프트 `sys-kw.txt`는 `tools/list`가 돌려준 `load_skill` 설명 원문 + `query`·`context` 인자 설명 원문(`raw/tools-list.json`)에, 출력 형식 한 줄("Reply with only the value you would pass as `query` for the task below — no quotes, no other text.")만 더한 것이다.
   - 사용자 프롬프트는 태스크 원문뿐이다.
   - 결과를 `kw-queries.jsonl`로 동결하고 해시를 `FROZEN.sha256`에 더한 **뒤에** SS 호출을 시작한다.
   - 2–6단어를 벗어난 질의도 고치지 않고 그대로 쓰며, 그 수만 보고한다.
4. **채점 카드**: SF 후보(우리 index)도 SS와 같은 형식으로 보여 준다.
   - 형식은 이름 + 220자 설명이다. SF는 frontmatter `description`을 220자로 자르고, 넘으면 217자 + "..."를 붙인다. tags·summary는 넣지 않는다.
   - 후보 합집합에 SS-kw 결과, SS-load-kw의 로드 스킬, SS-load-full의 로드 스킬을 더한다.
   - 로드 스킬은 검색 출력이 없으므로, SS 검색 결과에 같은 id가 있으면 그 설명을, 없으면 로드된 SKILL.md frontmatter `description`을 같은 규칙으로 자른 것을 쓴다.
5. **SF hit은 v5-ss 라벨만으로 다시 계산**한다.
   - v3·v4·v5 계열 라벨을 섞지 않는다. 분모(관련 있는 태스크, 관련 없는 태스크)도 v5-ss로 정한다.
   - `expect_none` 태스크는 관련 없는 쪽에 둔다(§2와 같음).
6. **빈 결과**: 조건별로 빈 결과로 돌아온 태스크 수를 보고한다.
   - 검색은 결과 0개("No Skillselion result" 또는 `### ` 행 0개)일 때 빈 결과로 센다.
   - load는 로드된 스킬이 없을 때 빈 결과로 센다.
   - 오류(`error`/`isError`)는 따로 센다.
   - SF는 R-c top-50이 0개인 태스크와 S-b′ 선택이 없음(none)인 태스크 수를 따로 낸다.
7. **load 본문 저장**: 각 load 직전에 클라이언트 임시 폴더(`$TMPDIR/skillselion`)를 비운다. 직후에 그 폴더를 `raw/load/<조건>/<태스크>/`로 복사한다.
8. **index 대응 판정**:
   - SS 결과가 우리 index 스킬과 같은지는 다음 순서로 본다. (저장소 owner/repo 대소문자 무시 일치) + (SS 이름 또는 `--skill` 경로의 마지막 부분 = 우리 `path`의 마지막 부분) → 후보.
   - 후보이면 SS 쪽 SKILL.md를 가져와 우리 `files["SKILL.md"]` sha256과 비교하고, 같으면 우리 id로 합친다.
   - SS 쪽 SKILL.md는 로드한 경우 그 본문을, 아니면 raw.githubusercontent GET(main/master, 클라이언트와 같은 경로 후보 순서)으로 가져온다.
   - "index 밖 관련 스킬"의 이름 같은 스킬 본문 비교도 같은 방식으로 가져온다.

## 4. 후속 (2026-10-24, 본 실행 보고 뒤·후속 결과를 보기 전에 기록; 세션 실행·외부 API 호출 없음)

0. **크리덴셜**: 크리덴셜 파일을 직접 읽지 않는다. 이번 후속은 SS 호출이 없어서 토큰이 필요 없다. `ss_client.py`는 동결본이라 고치지 않는다. 다음 SS 실행 전에는 환경변수만 읽도록 바꾼다.
1. **194태스크 최종 로드**: v5-ss에서 index 스킬이 하나 이상 관련(등급 ≥2)인 관련 태스크 194개로 비교한다. 대상은 SF S-b′ 3회 평균과 SS-load-kw(= SS-load-short)다.
   - 관련 로드 비율: 로드 세트에 관련이 1개 이상인 태스크 / 194
   - precision(태스크): 로드한 태스크 중 관련이 1개 이상인 비율
   - precision(스킬): 로드한 스킬 중 관련인 비율
2. **라벨 확장 v5-ss-b** (SF hit@25·@50과 실험 2에 필요):
   - v5-ss는 SF R-c를 top-10까지만 채점했다. 그래서 다음 합집합 중 v5-ss 풀에 없는 index 스킬을 새로 채점한다.
     - SF R-c top-50
     - 실험 2의 (a) kw 단독 top-50
     - 실험 2의 (b) R-c+kw top-50
   - 카드·프롬프트·격리 방식은 §2와 같다(title = 이름, summary = 220자 description, 2b 프롬프트 원문, 태스크마다 1회, 시드 `s8b-grade-<태스크>`로 섞고 `n01`… 라벨).
   - 기존 v5-ss 등급은 바꾸지 않는다. 결과는 `oracle-v5-ss-b.jsonl`이다.
   - 확장으로 관련 태스크 분모가 바뀌면 바뀐 값을 보고한다. v5-ss(미채점 = 무관 처리, 하한) 숫자도 함께 낸다.
3. **hit@25·@50**:
   - v5-ss-b로 SF R-c의 @10/@25/@50을 낸다. SS-q1·q3·kw의 @10/@25도 같은 라벨로 낸다(SS 결과는 최대 25개이고 전부 채점됨).
   - 분모는 v5-ss-b 관련 태스크 전체와 index 관련 태스크 두 가지다.
4. **후보 균형 민감도**: v5-ss의 SS 후보를 검색 조건(SS-q1·q3·kw)마다 상위 10개만 남긴다. 두 load 조건의 로드 스킬과 SF 후보는 그대로 둔다.
   - 그 풀에 있는 후보의 등급만으로 관련 세트와 분모를 다시 정하고 표 1(hit@1/5/10)을 다시 계산한다.
   - 다시 채점하지 않는다. 등급은 전체 풀 맥락에서 매겨진 것이다.
5. **짧은 쿼리 실험(오프라인)**: skillfetch `38dcb69` `search_skills(None, queries=…)`(k=50, profile 없음; R-c와 같은 호출)에 넣는다.
   - 조건: (a) `[kw]`, (b) `R-c 4개 + [kw]`(RRF는 search_skills 내부), 기준은 `R-c 4개`다(`results-rc.json`과 같은지 먼저 확인).
   - 지표: hit@10, hit@50, recall@50(태스크별 |top-50 ∩ R| / |R| 평균).
   - 라벨 두 가지:
     - **oracle v3**(`stage3/followup/oracle-v3.jsonl`): 관련 = v3 relevant, 미채점 = 무관. top-50 중 v3 풀 밖 비율을 함께 보고한다.
     - **v5-ss-b**: index 스킬만 관련 세트로 쓴다.
   - 분모는 expect_none이 아닌 관련 태스크다. 거절 문장 4태스크(t311, t317, t327, t330)는 표와 별도로 결과 목록을 보인다.
6. **소스 후보 목록**: v5-ss index 밖 관련 스킬 1,241개를 원본 GitHub 저장소로 묶는다.
   - **저장소**: SS 검색 출력의 `repo:` 줄(현재 저장소)을 쓰고, 없으면 id의 저장소를 쓴다.
   - **열**: 관련 스킬 수, 관련 (태스크, 스킬) 쌍 수, 공백 56 중 커버 수, 라이선스, 이름만 바뀐 사본 여부.
   - **라이선스**: 네트워크를 쓰지 않는다. 본 실행에서 이미 받은 루트 LICENSE 캐시(`raw/repo-license/`)만 쓰고, 없으면 "미확인"으로 둔다.
   - **사본**: 같은 owner의 다른 저장소가 같은 현재 저장소(`repo:` 줄)로 가리키거나, 관련·검색 결과의 스킬 이름 집합이 겹치면(공통 이름 ≥ 3이고 Jaccard ≥ 0.5) "사본 의심"으로 표시하고 상대 저장소를 적는다.
   - 상위 30개(관련 스킬 수 → 공백 커버 수 순)를 `source-candidates.md`로 쓴다.
7. **GPT 60**: `blind-ss-60.jsonl`은 그대로 둔다. 라벨(`gpt-ss-60.jsonl`; task_id, candidate_id, grade, process)이 오면 다음을 계산한다.
   - 완전 일치, ±1, 관련 여부 κ, process κ
   - 교집합(둘 다 ≥2) 기준 60태스크의 표 1과 최종 로드
   - **보충(실행 중 기록)**: `search_skills`는 질의를 4개까지만 받는다(`MAX_QUERIES = 4`). 그래서 (b) 5질의에서는 오류가 난다.
   - (b)는 session이 내부에서 부르는 `searcher.search_many`를 같은 인자로 직접 불렀다. 인자는 질의마다 `MAX_QUERY_CHARS` 자르기, profile 없음, k=50, `DEFAULT_TIERS`다. RRF 코드는 그대로다.
   - 같은 경로로 R-c 4질의를 부르면 380/380이 `search_skills` 결과와 같다(`search-kw.json`의 "R-c via search_many").

## 5. 운영 규칙과 #60 준비 (2026-10-24)

1. **지출**: 계획에 없던 지출이 $10을 넘을 것 같으면 실행 전에 사용자에게 묻는다(추정 근거와 함께).
2. **Skillselion 클라이언트**:
   - 동결본 `scripts/ss_client.py`(본 실행에 쓴 판본; 크리덴셜 파일을 읽음)는 그대로 둔다.
   - 다음 Skillselion 실행부터는 사본 `scripts/ss_client_env.py`를 쓴다. 사본은 환경변수 `GITHUB_TOKEN`만 읽고, 없으면 멈춘다. 그 밖의 코드는 동결본과 같다(diff는 `_gh_token`과 docstring뿐).
   - `main_run.py`처럼 `from ss_client import SS`를 쓰는 스크립트는 새 실행에서 `from ss_client_env import SS`로 바꾼 사본을 쓴다.
3. **`source-skill-map.jsonl`** (#60용):
   - **대상**: `source-candidates.md` 상위 30개 저장소의 SS 쪽 스킬(oracle key `ss:…`) 중 v5-ss-b에서 등급 ≥2를 한 번이라도 받은 것. 이름만 바뀐 id(`renamed_from`)도 현재 저장소로 묶는다.
   - **행**: 스킬 1개가 1행이다. 필드는 다음과 같다.
     - `oracle_key`, `ss_id`, `repo`(현재), `repo_url`, `id_repo`, `renamed_from`, `slug`, `name`
     - `install_skill_arg`: SS 검색 출력의 `npx skills add … --skill <arg>`
     - `path`/`branch`: 본 실행에서 raw.githubusercontent로 SKILL.md를 받은 경우만 있다.
     - `skill_md_sha256`과 그 출처: 로드 사본 또는 본 실행 fetch
     - `classification`, `summary`(채점 카드 그대로), `relevant_tasks`, `gap56_tasks`
     - `labels`: 그 스킬이 채점된 모든 태스크의 grade·process, 등급 0–1 포함
   - **레포 세션의 라벨 이전 절차(제안)**: 스테이징 index에 30개 저장소를 넣은 뒤 다음 순서로 맞춘다.
     1. `skill_md_sha256` = 새 레코드 `files["SKILL.md"]`
     2. 같은 저장소에서 `path`가 일치
     3. 같은 저장소에서 frontmatter `name` = `name` 또는 경로 마지막 부분 = `install_skill_arg`/`slug`의 마지막 부분
     - 맞은 새 id로 `labels`를 옮긴다. 같은 새 id에 여러 `oracle_key`가 맞으면(이름만 바뀐 사본 등) 태스크별 최고 등급을 쓴다. 이 규칙은 레포 세션이 확정한다.
     - 못 맞춘 행은 수와 목록을 보고한다.
   - 네트워크 없이 만들었다. 그래서 `path`는 일부만 있다.
