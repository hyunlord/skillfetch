# Stage 13 — 인기 스킬 묶음(P) 대 skillfetch(R) (설계, 실행 전 고정)

작성 2026-10-27, 승인 2026-10-27(상한 $42 = P $35 + Q1 6개 A·R 3회차 $6.6). 보고에는 숫자와 인용만 쓴다. 비용은 구독 사용량을 API 단가로 환산한 값이다.

사용자 지시(원문):
> 대신 Stage 13 설계만 한다(실행 X):
> - 조건 P(인기 스킬 묶음): skills.sh 순위와 Anthropic 공식 스킬 기준으로 보통 사용자가 깔아 둘 인기 스킬 8개 안팎을 .claude/skills에 설치, 라우터·MCP 없음. 선정 기준과 목록을 먼저 고정한다.
> - 태스크: Q1 확장의 18개 태스크 × 3회. A(끔)와 R(켬)은 Q1 확장 결과를 재사용하고 P만 새로 돌린다.
> - 보고: 태스크별 A / P / R 점수, 체크, 턴, 비용, P에서 실제로 쓴 스킬. 블라인드 판정은 같은 루브릭.
> - 세션 수와 환산 비용을 추정한다.

배경: Stage 12c는 취소했다. 사용자 이유는 "skillfetch의 사용자는 스킬이 없거나 몇 개뿐인 사람이라, 수백 개를 설치한 N과의 비교는 현실과 맞지 않는다"이다(`stage12c/DESIGN.md` §8). Stage 13은 "스킬을 몇 개 깔아 둔 보통 사용자"(P)를 재는 실험이다.

## 1. 조건 P: 선정 기준과 목록 (고정)

### 1.1 출처

- **skills.sh All Time 순위**: 2026-10-27에 받은 스냅샷 `stage13/skillssh-alltime-2026-10-27.json`(932행)이다. 순위·이름·출판자·설치 수가 있다.
- **Anthropic 공식 스킬**: `anthropics/skills`의 `skills/` 폴더다(2026-10-27). academy-guide, algorithmic-art, brand-guidelines, canvas-design, claude-api, discernment-nudge, doc-coauthoring, docx, frontend-design, internal-comms, mcp-builder, pdf, pptx, skill-creator, slack-gif-creator, theme-factory, web-artifacts-builder, webapp-testing, xlsx가 있다.

### 1.2 기준 (순위 순서대로 적용)

1. 대상은 skills.sh 순위 상위 200위 안이거나 Anthropic 공식 스킬이다.
2. **뺀다**:
   - (a) 영상·이미지·오디오 생성·편집(hyperframes, ai-video-generation, media-use, remotion 등)
   - (b) 문서·협업 도구 전용(lark-*, docx, pptx, xlsx, pdf, doc-coauthoring, internal-comms)
   - (c) 특정 클라우드·DB 벤더 전용(azure-*, google-agents-cli-*, prisma-*, supabase-*, claude-api, mcp-builder)
   - (d) 마케팅·소셜 자동화(reddit-automation 등)
   - (e) 메타·설정·세션 관리·출력 문체(find-skills, setup-*, handoff, claude-handoff, skill-creator, writing-for-agents, caveman*)
   - (f) 외부 바이너리·계정이 있어야 하는 것(agent-browser, webapp-testing의 Playwright)
   - (g) 주된 동작이 사용자 인터뷰인 것(grill-me, grill-with-docs, grilling, wait-what, to-questionnaire, ask-matt, brainstorming, teach)
   - (h) 이슈·PR 워크플로 전용(triage, to-tickets, to-spec)
   - (i) 버리는 산출물(prototype)
   - (j) 설명에 "이름으로 부를 때만 동작(opt-in)" 또는 "Retired"라고 적힌 것(high-end-visual-design, minimalist-ui, redesign-existing-projects 등)
3. 출판자당 최대 3개다.
4. 남은 것을 순위 순서로 **8개**까지 고른다. Anthropic 공식은 같은 기준을 통과하면 skills.sh 순위로 들어간다(frontend-design #14).

### 1.3 목록 (8개)

| # | 스킬 | 출판자 | skills.sh 순위 | 설치(All Time) | 설명(skills.sh) |
|---|---|---|---:|---:|---|
| 1 | improve-codebase-architecture | mattpocock/skills | 7 | 1.2M | "Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick." |
| 2 | tdd | mattpocock/skills | 8 | 1.2M | "Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests." |
| 3 | frontend-design | anthropics/skills | 14 | 1.0M | Anthropic 공식 |
| 4 | domain-modeling | mattpocock/skills | 22 | 889.1K | "Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing a GLOSSARY.md, or recording or editing an ADR." |
| 5 | vercel-react-best-practices | vercel-labs/agent-skills | 30 | 842.0K | "React and Next.js performance optimization guidelines from Vercel Engineering. …" |
| 6 | web-design-guidelines | vercel-labs/agent-skills | 55 | 788.3K | "Review UI code for Web Interface Guidelines compliance. …" |
| 7 | design-taste-frontend | leonxlnx/taste-skill | 72 | 683.0K | "tasteskill v2, the anti-slop frontend skill. Art direction for websites, …" |
| 8 | vercel-composition-patterns | vercel-labs/agent-skills | 175 | 420.1K | (준비 때 SKILL.md에서 기록) |

- **출판자 한도로 빠진 것**: mattpocock의 codebase-design(#28), diagnosing-bugs(#29), code-review(#53), implement(#56) 등. 4번째 mattpocock부터 빠졌다.
- **구성**: 8개 중 5개가 웹·프론트엔드 스킬(3, 5, 6, 7, 8)이고, 3개가 언어 무관 개발 방법(1, 2, 4)이다. Rust·Swift·Go·Java·Python 전용 스킬은 기준을 통과한 것 중 상위 200위 안에 없다. 이 편중은 인기 순위를 그대로 반영한 결과다.
- **본문**: 준비 때 각 스킬의 GitHub 저장소 기본 브랜치 커밋 SHA를 고정하고, 스킬 폴더 전체(SKILL.md와 딸린 파일)를 그 커밋에서 받아 해시로 고정한다. 모델 호출은 없다.

## 2. 태스크와 반복

- **태스크**: Q1 확장 보고(`stageQ/report-Q1x.md`)와 갤러리 v2의 18개다.
  - Stage Q Q1의 6개: d1-landing, d4-email, s10-t016, s11-t266, s2-api, s2-data
  - Q1 확장의 12개: d2-redesign, d3-dashboard, s10-t263, s10-t115, s10-t198, s11-t160, s11-t118, s2-docs, s10-t033, s2-tests, s10-t001, s6b-t179
  - 프롬프트, 시작 커밋, 체크는 원래 그대로다.
- **P**: 18 × 3회(m1–m3) = **54세션**이다.
- **A(끔)·R(켬) 재사용**: Q1 확장 12개는 3회씩이다. Q1 6개는 Stage Q 때 **2회씩**이다(m1–m2).
  - 기본안은 그대로 재사용하는 것이다(Q1 6개는 A·R 2회, P 3회).
  - 선택안은 Q1 6개의 A·R m3을 더 돌려 3회로 맞추는 것이다(+12세션, 약 $6.6). 사용자가 정한다.
- **환경**: E1, 하네스 `stageQ/scripts/run_q.py`다.
  - P는 레포마다 브랜치 `s13-p-<시작 브랜치>`를 쓴다. 시작 커밋 위 커밋 하나("chore: add project skills")로 `.claude/skills/<이름>/`에 8개를 더한다. 라우터·MCP는 없다(`mcp-none`).
  - 시작 커밋에 이미 있는 프로젝트 스킬(fastapi 템플릿의 `.claude/skills/library-skills`)은 A·R과 같이 그대로 둔다.
- **파일럿**: d2-redesign, s10-t263, s2-api × P × 1 = **3세션**이다(집계 밖). 유효성 점검: init `skills`에 8개가 보인다.

## 3. 보고 항목 (게이트 없음, 숫자만)

태스크별, 그리고 묶음(디자인, Rust, Swift, Go, Java, TS, Python)별로 낸다.

- **점수**: 블라인드 판정 A / P / R, Claude p1·p2 평균. 루브릭은 Q1·Q1 확장과 같다(묶음별 `rubric-design.md`, `rubrics-s2.md`, `rubric-b4.md`, `rubric-b3*.md`).
  - 판정 세트는 태스크마다 A·P·R 결과물을 함께 넣는다. 새 무작위 코드, 새 판정자 하위 에이전트다.
  - A·R도 이 세트에서 다시 점수를 받는다. Q1·Q1 확장 점수는 옆에 참고로 둔다.
- **체크 통과**(태스크 원래 체크), **추가 테스트 수**, **중앙 턴**, **입력 토큰**, **평균 API 단가 환산**
- **P에서 실제로 쓴 스킬**:
  - 세션마다 Skill 도구 호출, SKILL.md·딸린 파일 읽기(Read/Bash 경로)를 센다(12b N과 같은 방식, 이름 없는 반복 포함).
  - 태스크별로 "쓴 스킬 / 안 씀"을 낸다. R이 같은 태스크에서 로드한 스킬(Q1·Q1 확장 기록)과 나란히 둔다.
- **P의 스킬 목록 토큰**: 8개 이름·설명 글자 수다. 필요하면 짧은 요청 1회(A 브랜치 대 P 브랜치)로 입력 토큰 차이도 잰다.

## 4. 세션과 비용 추정 (API 단가 환산)

| 항목 | 계산 | 추정 |
|---|---|---:|
| 파일럿 | 3 × 약 $0.45 | $1.4 |
| P 본 실행 | 54 × 약 $0.45 | $24.3 |
| 목록 토큰 측정(선택) | 2 × 약 $0.05 | $0.1 |
| 다시 돌림 여유 10% | | $2.6 |
| **합계** | **세션 57(+2)** | **약 $28** |

- **P 세션당 $0.45의 근거**: Q1 확장 끔 평균 $0.347, 켬 $0.547이고, Q1 끔 $0.408, 켬 $0.692다. P는 끔에 스킬 목록(8개, 약 1k 토큰 미만)과 불러온 본문을 더한 것으로 잡았다. 디자인 태스크에서는 frontend-design·design-taste-frontend 같은 큰 본문을 불러올 수 있다.
- **상한 제안: $35.** 선택안(Q1 6개 A·R m3)을 더하면 +$6.6이다.
- 판정(Claude 하위 에이전트)은 환산에 넣지 않는다.

## 5. 준비 순서 (사용자 확인 뒤)

1. 8개 스킬의 저장소·커밋 SHA 고정 → 스킬 폴더 받기(GitHub raw, 고정 커밋) → 해시 고정
2. 레포마다 `s13-p-*` 브랜치(plumbing), `run_q.py`에 조건 P(브랜치, mcp-none), 사전 점검(바뀐 파일 = 8개 스킬 폴더만)
3. dry run(18개 태스크 × P), 파일럿 3세션, 유효성 점검
4. 본 실행 54세션(seed "s13"로 섞고 4병렬) → 쓴 스킬 분석 → 블라인드 판정(A·P·R) → `report-13.md`

## 6. 한계 (미리 적어 둠)

- "보통 사용자가 깔아 둘 스킬"을 skills.sh 설치 수로 근사했다. 설치 수에는 묶음 설치(한 저장소 전체 설치)가 섞여 있을 수 있다.
- 8개는 웹·프론트엔드 쪽으로 기울었다(§1.3). 그래서 Rust·Swift·Go·Java 태스크에서 P는 쓸 스킬이 거의 없을 수 있다. 이것은 인기 묶음의 실제 모습이다.
- A·R은 다른 날짜의 실행(Stage Q, Q1 확장)을 재사용한다. 같은 하네스·환경·체크다.
- web-design-guidelines는 실행 중 지침을 URL에서 가져온다(WebFetch). E1의 허용 도구에 따라 실패할 수 있다. 그대로 기록한다.

## 7. 기록

- 2026-10-27 설계 작성(실행 X).
  - skills.sh 스냅샷을 받았다.
  - 후보 설명은 skills.sh 페이지에서 확인했다: tdd, improve-codebase-architecture, grill-me, diagnosing-bugs, code-review, vercel-react-best-practices, triage, prototype, design-taste-frontend, domain-modeling, codebase-design, high-end-visual-design, redesign-existing-projects, web-design-guidelines, minimalist-ui.
  - ui-taste(uizze.sh)는 페이지가 404였다.
- 2026-10-27 사용자 승인. 원문: "Stage 13 승인(상한 $35 + 원래 Q1 6개 태스크의 A·R 3회차 추가 $6.6, 합계 상한 $42). P 목록 8개와 선정 규칙은 그대로 고정한다(웹 편중은 한계로 기록). 판정은 A·P·R을 같은 세트에 섞어서 새로 한다. 끝나면 태스크별 A/P/R 표와 P가 실제로 쓴 스킬, R이 같은 태스크에서 로드한 스킬을 나란히 보고한다."
  - **선택안 채택**: Q1 6개(d1-landing, d4-email, s10-t016, s11-t266, s2-api, s2-data)의 A·R m3을 돌려 모든 태스크를 3회로 맞춘다(+12세션). 하네스·서버·index는 Stage Q Q1과 같다.
  - **세션**: P 54 + 파일럿 3 + A·R m3 12 = 69세션이다. 상한은 $42다.
- 2026-10-27 파일럿 3세션(API 단가 환산 $2.12): 세 세션 모두 init `skills`에 P 8개가 있다(유효성 점검 맞음).
  - d2-redesign: $1.30, 24턴, design-taste-frontend 사용, 체크 통과
  - s10-t263: $0.29, 14턴, 스킬 사용 없음, 체크 통과
  - s2-api: $0.53, 10턴, 스킬 사용 없음, 체크 실패
  - 큐 비용 투영용 P 추정을 파일럿 실측으로 바꿨다. 디자인 4개(d1–d4)는 끔 + $0.90, 나머지는 끔 + $0.05다(파일럿 두 세션이 끔 대비 +$0.04, +$0.05). 투영은 쓴 것 $2.12 + 남은 것 약 $39.3 = 약 $41.4다(상한 $42). 실제가 추정보다 크면 큐가 상한을 넘기 전에 멈추고, 그때 사용자에게 묻는다.
- 2026-10-27 본 실행 첫 12 job 뒤에 큐가 비용 투영($42.05 > $42)으로 멈췄다.
  - 원인: P d1-landing m1이 $3.23, 41턴, 974초였다(design-taste-frontend 사용). 추정은 $1.24였다.
  - 사용자 결정(선택지 답): "Raise cap to $48". 상한을 **$48**로 올리고, d1-landing P 추정을 $3.2로 바꿔 재개했다.
- 2026-10-27 본 실행 66/66 완료(API 단가 환산 합계 $43.79). 판정(새 판정자 8명, A·P·R 한 세트)은 162쌍 중 같은 점수 137이다. 보고는 `stage13/report-13.md`다.
  - P d1-landing 세 세션은 모두 40턴 한도(`error_max_turns`)에서 끝났다. 페이지 섹션은 스크롤 등장(`opacity: 0` + `IntersectionObserver`)이라 정지 화면 캡처에서 빈칸이었다.
  - 판정 패키지 감사어에서 "canary"를 뺐다(Q1 확장과 같은 이유).
- 2026-10-27 실험 단계 종료(사용자): Stage 13으로 마무리한다. 공개 정리 때 P 스킬 본문(`stage13-private/p-skills/`, 제3자)은 공개하지 않고, 고정 커밋·경로·해시(`p-skills-manifest.json`)만 간다.
