# 재발화 검증 보고

실행 2026-10-26. 설계와 기준은 `stageRF/DESIGN.md`(실행 전 고정, §6에 사용자 결정에 따른 변경)에 있다. 이 보고에는 숫자와 인용만 적는다. 비용은 API 단가 환산이다.

- **방식**: Q2 S와 같다. 레포 `sq-mono`에서 한 세션에 작업 4개를 보내고(작업 2–4는 `--resume`), canary는 없다(작업 1의 로컬 스킬 지정 문장을 뺐다).
- **범위**: 사용자 결정(§6)에 따라 지금 라우터(cur)는 5회 돌렸다. 변형 (a)·(b)는 본 실행 1회씩(+ 파일럿 1회씩)에서 멈췄고, canary 재측정은 하지 않았다.

## 지금 라우터 (S-b′, 5세션)

| 작업 | 발화(Skill `skillfetch-router` 또는 skillfetch MCP) | 로드한 스킬(합) | 앞 작업 스킬 언급(로드 없이) | 중앙 턴 | 평균 API 단가 환산 |
|---|---:|---|---:|---:|---:|
| 1 디자인(후기 섹션) | 5/5 | web-design ×3, design-system ×2 | – | 12 | $0.348 |
| 2 Rust(`duration.rs`) | **5/5** | m06-error-handling ×5, rust-testing ×5, coding-guidelines ×2 | 0 | 8 | $0.735 |
| 3 README 오타 | **0/5**(미발화 5/5) | – | 0 | 4 | $0.812 |
| 4 Python(`export_csv.py`) | **5/5** | python-testing ×4, python-error-handling ×2 | 0 | 9 | $1.185 |

- **기준**: 사소하지 않은 작업 2·4 발화 **10/10**, 사소한 작업 3 미발화 **5/5**다.
- **발화 방식**: 작업 1은 5/5 Skill 도구로 `skillfetch-router`를 불렀다. 작업 2·4의 10개는 모두 Skill을 다시 부르지 않고 skillfetch MCP(`search_skills` → `resolve_and_load` 등)를 곧바로 불렀다.
- **세션당 평균 API 단가 환산**: $3.08다(Q2 S는 $1.54, 작업 4의 입력 토큰 52–63만 대 29만).

## 변형 (기록만)

| 갈래 | 세션 | 작업 1 | 작업 2 | 작업 3 | 작업 4 | 세션 API 단가 환산 |
|---|---|---|---|---|---|---:|
| (a) refire.md | 본 실행 m4 | 발화 | 발화(MCP만) | 미발화 | 발화(MCP만) | $3.24 |
| (a) refire.md | 파일럿 p1 | 발화 | 발화(MCP만) | 미발화 | 발화(MCP만) | $3.21 |
| (b) refire.md + CLAUDE.md | 본 실행 m1 | 발화 | 발화(Skill) | 미발화 | 발화(Skill) | $3.08 |
| (b) refire.md + CLAUDE.md | 파일럿 p1 | 발화 | 발화(Skill) | 미발화 | 발화(Skill) | $3.25 |

- 표의 "MCP만"은 Skill 도구로 라우터를 다시 부르지 않고 `search_skills`·`resolve_and_load`를 곧바로 부른 경우다. "Skill"은 Skill 도구로 `skillfetch-router`를 다시 부른 경우다.
- 작업 2·4에서 Skill을 다시 부른 요청 수: cur 0/10, (a) 0/4, (b) 4/4.

## Stage Q Q2의 0/20

- Q2 S(작업 1에 "For this task, use my local skill at `<path>`."가 있음)는 20개 요청 모두 skillfetch 호출이 0이었다.
- 같은 4작업에서 그 문장만 뺀 이번 cur 5회는 작업 1·2·4에서 15/15 발화했다.
- 사용자 결정에 따라 이것을 "1번 작업에서 로컬 스킬을 이름으로 지정하면 그 세션 전체에서 라우터가 돌지 않는" 현상으로 기록한다(`stageQ/report-Q.md` §3).
- 이 경우를 다른 레포에서 확인하는 작업 2개는 Q1 확장(`stageQ/DESIGN-Q1x.md` §2.1)에서 돌린다.

## 비용

API 단가 환산 합계는 **$28.18**이다. 파일럿 2($6.46), 본 실행 a 1·b 1·cur 5 = 7세션($21.72)이다. 처음 상한은 $50, 추정은 $44였다. 세션당 실측 $3.1(추정 $1.8)로 큐가 투영 규칙에서 멈춘 뒤, 사용자 결정으로 cur 3세션만 더 돌렸다.
