# 소스 후보 — v5-ss index 밖 관련 스킬의 원본 저장소 (상위 30)

- 대상: v5-ss 등급 ≥2를 받은 SS 쪽 스킬 중 index 밖으로 분류된 1,241개(`metrics-8.json`). 저장소 353개로 묶인다.
- 저장소: SS 검색 출력의 `repo:` 줄(현재 저장소). 없으면 id의 저장소를 쓴다.
- 관련 스킬 수: 고유 이름 수(괄호 안은 SS id 수 — 옛 저장소명 id와 새 저장소명 id가 둘 다 있으면 2로 센다).
- 쌍: 그 저장소 스킬이 등급 ≥2를 받은 (태스크, 스킬) 수. 태스크: 그런 태스크 수.
- 공백 56: v3 oracle 관련 0·expect_none 아님·trivial 아님 태스크 56개 중 이 저장소의 index 밖 관련 스킬이 있는 태스크 수.
- 라이선스: 본 실행에서 받은 루트 LICENSE 캐시(`raw/repo-license/`, 로드된 스킬의 저장소만)를 skillfetch `classify_text`로 분류한 것이다. 이번에는 네트워크를 쓰지 않았다. 캐시에 없으면 "미확인", 루트에 LICENSE 파일이 없으면 "루트 LICENSE 없음", 파일은 있는데 분류 규칙에 안 걸리면 "unknown"이다. 스킬 폴더·frontmatter 라이선스는 이 표에 넣지 않았다.
- 이름만 바뀐 사본: 같은 현재 저장소를 가리키는 다른 id 저장소명. 사본 의심: 같은 owner의 다른 저장소와 검색 결과 스킬 이름이 3개 이상 겹치고 Jaccard ≥ 0.5.
- 상위 30개가 커버하는 공백 태스크: 36/56 (전체 353개 저장소: 45/56).

| # | 저장소 | 관련 스킬 (id) | 쌍 | 태스크 | 공백 56 | 라이선스 | 이름만 바뀐 사본 | 사본 의심 |
|---:|---|---:|---:|---:|---:|---|---|---|
| 1 | [claude-dev-suite/claude-dev-suite](https://github.com/claude-dev-suite/claude-dev-suite) | 40 (40) | 63 | 56 | 2 | MIT | – | – |
| 2 | [bobmatnyc/claude-mpm-skills](https://github.com/bobmatnyc/claude-mpm-skills) | 38 (38) | 69 | 54 | 2 | MIT | – | – |
| 3 | [affaan-m/ECC](https://github.com/affaan-m/ECC) | 35 (59) | 120 | 69 | 9 | MIT | affaan-m/everything-claude-code | – |
| 4 | [aj-geddes/useful-ai-prompts](https://github.com/aj-geddes/useful-ai-prompts) | 29 (29) | 43 | 39 | 4 | MIT | – | – |
| 5 | [CharlesWiltgen/Axiom](https://github.com/CharlesWiltgen/Axiom) | 23 (23) | 25 | 13 | 5 | MIT | – | – |
| 6 | [giuseppe-trisciuoglio/developer-kit](https://github.com/giuseppe-trisciuoglio/developer-kit) | 23 (26) | 37 | 29 | 1 | MIT | giuseppe-trisciuoglio/developer-kit-claude-code | – |
| 7 | [Mindrally/skills](https://github.com/Mindrally/skills) | 22 (22) | 31 | 28 | 1 | Apache-2.0 | – | – |
| 8 | [davidcastagnetoa/skills](https://github.com/davidcastagnetoa/skills) | 20 (20) | 28 | 22 | 5 | 루트 LICENSE 없음 | – | – |
| 9 | [secondsky/claude-skills](https://github.com/secondsky/claude-skills) | 20 (31) | 48 | 34 | 3 | MIT | – | – |
| 10 | [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | 20 (24) | 34 | 26 | 2 | MIT | sickn33/antigravity-awesome-skills | – |
| 11 | [alphaonedev/openclaw-graph](https://github.com/alphaonedev/openclaw-graph) | 17 (17) | 27 | 26 | 5 | 루트 LICENSE 없음 | – | – |
| 12 | [dpearson2699/swift-ios-skills](https://github.com/dpearson2699/swift-ios-skills) | 16 (16) | 18 | 13 | 4 | unknown | – | – |
| 13 | [jeremylongshore/tons-of-skills-marketplace](https://github.com/jeremylongshore/tons-of-skills-marketplace) | 15 (15) | 18 | 18 | 0 | MIT | jeremylongshore/claude-code-plugins-plus-skills | – |
| 14 | [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) | 15 (15) | 16 | 12 | 0 | Apache-2.0 | – | – |
| 15 | [rshankras/claude-code-apple-skills](https://github.com/rshankras/claude-code-apple-skills) | 14 (14) | 17 | 14 | 5 | MIT | – | – |
| 16 | [wshobson/agents](https://github.com/wshobson/agents) | 14 (14) | 19 | 19 | 3 | MIT | – | – |
| 17 | [github/awesome-copilot](https://github.com/github/awesome-copilot) | 14 (14) | 33 | 33 | 2 | MIT | – | – |
| 18 | [agents-inc/skills](https://github.com/agents-inc/skills) | 14 (14) | 18 | 18 | 1 | MIT | – | – |
| 19 | [TheBushidoCollective/han](https://github.com/TheBushidoCollective/han) | 14 (14) | 14 | 13 | 0 | Apache-2.0 | – | – |
| 20 | [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | 13 (13) | 20 | 16 | 2 | MIT | – | – |
| 21 | [mohitmishra786/low-level-dev-skills](https://github.com/mohitmishra786/low-level-dev-skills) | 13 (13) | 19 | 11 | 2 | MIT | – | – |
| 22 | [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills) | 13 (13) | 21 | 20 | 1 | MIT | – | – |
| 23 | [ahmed3elshaer/everything-claude-code-mobile](https://github.com/ahmed3elshaer/everything-claude-code-mobile) | 12 (12) | 19 | 18 | 6 | MIT | – | – |
| 24 | [yaklang/hack-skills](https://github.com/yaklang/hack-skills) | 12 (12) | 13 | 10 | 1 | MIT | – | – |
| 25 | [JetBrains/skills](https://github.com/JetBrains/skills) | 11 (11) | 12 | 11 | 2 | 루트 LICENSE 없음 | – | – |
| 26 | [flutter/agent-plugins](https://github.com/flutter/agent-plugins) | 11 (12) | 18 | 6 | 1 | BSD-3-Clause | flutter/skills | – |
| 27 | [manutej/luxor-claude-marketplace](https://github.com/manutej/luxor-claude-marketplace) | 11 (11) | 22 | 20 | 0 | 루트 LICENSE 없음 | – | – |
| 28 | [pproenca/dot-skills](https://github.com/pproenca/dot-skills) | 11 (11) | 15 | 13 | 0 | MIT | – | – |
| 29 | [actionbook/rust-skills](https://github.com/actionbook/rust-skills) | 10 (14) | 18 | 11 | 3 | 루트 LICENSE 없음 | zhanghandong/rust-skills | – |
| 30 | [curiositech/some_claude_skills](https://github.com/curiositech/some_claude_skills) | 10 (10) | 15 | 15 | 0 | MIT | erichowens/some_claude_skills | – |

전체 353개 저장소의 라이선스: 미확인 211, MIT 79, 루트 LICENSE 없음 32, Apache-2.0 20, unknown 3, BSD-3-Clause 2, proprietary 2, GPL-3.0 2, Unlicense 1, AGPL-3.0 1.
이름만 바뀐 사본이 있는 저장소 43개, 사본 의심 0개(전체 기준).

전체 목록: `source-candidates.json`. 스크립트: `scripts/source_candidates.py`.
