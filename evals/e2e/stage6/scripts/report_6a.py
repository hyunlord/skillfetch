#!/usr/bin/env python3
"""report-6a.md from kind-agreement.json, eval-6a.json, pool-v4.json, cases-6a.json, select-cands/, logs/."""
import json
import subprocess
from pathlib import Path

S6 = Path(__file__).resolve().parents[1]
d = json.loads((S6 / "eval-6a.json").read_text())
ka = json.loads((S6 / "kind-agreement.json").read_text())
pv = json.loads((S6 / "pool-v4.json").read_text())
cases = json.loads((S6 / "cases-6a.json").read_text())
res = json.loads((S6 / "gen" / "results-rc.json").read_text())
C = ("S-0", "S-a", "S-b", "S-c")
logs = {c: (S6 / "logs" / f"select-{c}.log").read_text().strip().splitlines()[-1] for c in C}
cost = {c: float(logs[c].split("cost ")[1].split()[0]) for c in C}
redo = {c: int(logs[c].split("redone alone ")[1].split()[0]) for c in C}
chars = sum(len(json.dumps(v)) for v in res.values()) / len(res)
kchars = chars + 50 * len(', "kind": "tooling"')


def fmt_sel(xs, rank=True):
    return ", ".join(f"{a} ({k}, {g}" + (f", {r}위" if rank else "") + ")" for a, k, g, *rest in xs for r in (rest[0] if rest else None,)) or "없음"


def fmt_rel(xs):
    return ", ".join(f"{a} ({k}, {g}, " + (f"{r}위" if r else "50위 밖") + ")" for a, k, g, r in xs)


L = ["# 6a단계 — 선택 규칙 수정 (오프라인) (report)\n",
     "세션 실행은 없다. 모든 호출은 격리 `claude -p`(도구·MCP·사용자 설정 없음, 시스템 프롬프트 1h 캐시)이고, 외부 API 키는 쓰지 않았다. 스크립트는 `scripts/`, 해시는 `FROZEN.sha256`에 있다.\n",
     "## 0. 설정\n", "| 항목 | 값 |\n|---|---|",
     "| 라우터 | main `cc5d16c`의 `assets/router-skill/SKILL.md`(= 5단계 V1, 60줄) → `select-cands/S-0/SKILL.md` 그대로 |",
     "| 검색 | 380태스크의 R-c 쿼리(`stage3/followup/rc-R-c-380.jsonl`) → skillfetch `cc5d16c` `search_skills(queries=…)` 출력 그대로(compact 50, profile 없음). top-50은 3단계 R-c 순위와 380/380 같다 |",
     f"| 선택 프롬프트 | 시스템 프롬프트 = 후보 SKILL.md 전문 + 중립 래퍼(\"`resolve_set`에 넘길 `auto_ids`, 부르지 않으면 빈 목록\"). 사용자 프롬프트 = 요청 원문 + `queries` + 그 태스크의 search 결과. 10태스크/호출. 다른 태스크의 id를 고른 태스크는 한 태스크씩 다시 돌렸다(" + ", ".join(f"{c} {redo[c]}" for c in C) + ") |",
     "| 3단계와 다른 점 | 3단계 선택 래퍼에는 \"none when no result fits\"가 있었다. 이번 래퍼에는 없다. 그래서 S-0 수치는 3단계 표 2와 직접 비교하지 않는다 |",
     f"| oracle | **v4** = 3단계 v3 + 네 후보가 고른 스킬 중 풀 밖이던 {pv['added']}개(같은 2b 프롬프트, ${pv['cost_usd']}, 새 관련 {pv['added_relevant']}). 관련 쌍 {pv['relevant_v3']} → {pv['relevant_v4']}, 관련 없음 태스크 {pv['no_relevant_v3']} → {pv['no_relevant_v4']} |",
     "| 관련 없음 태스크 수 | 지시문의 95는 v2 기준이다(v2 95, v3 89, v4 85). 아래 none-정확도(관련 없음)는 v4의 85개 기준이다 |",
     "| expect_none | 40개(사소한 작업). v4에서 그중 33개는 관련 없음이다 |\n",
     "## 1. kind 라벨 (`kind.jsonl`)\n",
     f"index의 tier A/B canonical 1,489개 전부(3단계 카탈로그)에 라벨을 붙였다. 시스템 프롬프트는 정의와 카탈로그 전체(`gen/sys-kind.txt`)이고, 50개씩 카드(id, title, 전체 summary, tags)를 주었다. 30회, ${ka['cost_usd']}.\n",
     f"| kind | 개수 |\n|---|---|\n| domain | {ka['kinds']['domain']} |\n| process | {ka['kinds']['process']} |\n| tooling | {ka['kinds']['tooling']} |\n",
     "oracle v3의 process 표시와 비교했다(kind = process ⇔ process 표시):\n",
     "| 기준 | n | 일치율 | kappa | kind process · 표시 있음 | kind process · 표시 없음 | kind 다른 것 · 표시 있음 | kind 다른 것 · 표시 없음 |\n|---|---|---|---|---|---|---|---|"]
for k, lab in (("graded_pairs", "채점된 (태스크, 스킬) 쌍 전체"), ("relevant_pairs", "관련 쌍(등급 ≥2)"), ("skills_majority_flag", "스킬 단위(그 스킬 표시의 다수결)")):
    a = ka[k]
    L.append(f"| {lab} | {a['n']} | {a['agree']} | {a['kappa']} | {a['kind_process&flag']} | {a['kind_process&no_flag']} | {a['kind_other&flag']} | {a['kind_other&no_flag']} |")
L += ["", "## 2. 후보 규칙\n",
      "세 후보는 같은 구조 편집을 공유한다. 선택 단계 밖의 편집이다.",
      "- `## Rules` 절을 없앴다.",
      "- \"Never load a skill that `resolve_set` excluded\"는 6단계 \"Respect `excluded`\"와 같은 말이라 지웠다.",
      "- \"Do not search again mid-task unless the task changes\"는 3단계 끝의 \"Search once per task.\"로 옮겼다.",
      "- 1단계(측정된 R-c 재진술)는 그대로다.",
      "- 4단계 문구만 후보마다 다르다.\n",
      "S-b와 S-c는 \"pick 1–3\"을 \"pick up to 3\"으로 바꿨다. 0개를 허용하는 새 문장과 어긋나지 않게 하려는 것이다.\n",
      "| 후보 | 줄 수 | 4단계 문구 |\n|---|---|---|"]
st4 = json.loads((S6 / "gen" / "step4-texts.json").read_text())
s0 = (S6 / "select-cands" / "S-0" / "SKILL.md").read_text()
L.append(f"| S-0 (main) | {len(s0.splitlines())} | {' '.join(s0[s0.index(chr(10) + '4. ') + 1:s0.index(chr(10) + '5. ')].split())} |")
for c in ("S-a", "S-b", "S-c"):
    L.append(f"| {c} | {len((S6 / 'select-cands' / c / 'SKILL.md').read_text().splitlines())} | {st4[c]} |")
L += ["\nS-a·S-b·S-c의 search 결과에는 각 항목의 `tier` 뒤에 `\"kind\"`가 들어간다. S-0의 결과는 서버 출력 그대로다.\n",
      "## 3. 표 — 선택 지표 (oracle v4; 괄호는 v3)\n", "| 지표 | " + " | ".join(C) + " |\n|---|" + "---|" * 4]
for lab, k in ((f"precision (고른 태스크; 관련 있는 태스크 n={d['v4']['S-0']['coverage_tasks']})", "precision"), ("recall", "recall"), ("hit (관련 1개 이상 고름)", "hit"),
               ("none-정확도 — 관련 없음 태스크 (v4 85 / v3 89)", "none_acc_oracle"), ("none-정확도 — expect_none 40", "none_acc_expect_none"),
               ("과잉 로드 태스크 (관련 없음인데 고름)", "over_load_tasks"), ("잘못 로드 수 (등급 <2, 380 전체)", "wrong_loads"),
               ("관련 있는 태스크에서 none", "none_cov"), ("태스크당 평균 로드 수", "mean_loaded"),
               ("방향 쌍: 세트가 바뀜 / 20", "pairs_changed"), ("방향 쌍: 방향대로 바뀜 / 20", "pairs_moved")):
    L.append(f"| {lab} | " + " | ".join(f"{d['v4'][c][k]} ({d['v3'][c][k]})" for c in C) + " |")
L.append("| directive 100개 중 process 스킬을 고른 태스크 (그중 관련) | " + " | ".join(f"{d['v4'][c]['directive_with_process_pick']} ({d['v4'][c]['directive_process_pick_relevant']})" for c in C) + " |")
L.append("| directive 아닌 240개 중 process 스킬을 고른 태스크 | " + " | ".join(str(d['v4'][c]['nondirective_with_process_pick']) for c in C) + " |")
L.append("| 고른 스킬의 kind (domain / process / tooling) | " + " | ".join(f"{d['v4'][c]['picked_kinds'].get('domain', 0)} / {d['v4'][c]['picked_kinds'].get('process', 0)} / {d['v4'][c]['picked_kinds'].get('tooling', 0)}" for c in C) + " |")
L.append("| 비용 ($, 단독 재실행 포함) | " + " | ".join(f"{cost[c]:.2f}" for c in C) + " |")
L += ["\n방향 쌍 기준의 상한: 20쌍 중 두 쪽의 oracle 관련 세트가 다른 쌍은 16개다(process 관련 세트가 다른 쌍 13). \"방향대로 바뀜\"은 세트가 바뀌고, 각 쪽에 더한 스킬이 그쪽에만 관련이어야 센다(3단계 `eval_selection.py` 정의). 그래서 15/20은 16개 중 15개를 맞혀야 한다.\n",
      "## 판정 (기준: none-정확도 ≥ 0.85, hit 하락 ≤ 0.05, 방향 쌍 ≥ 15/20; v4)\n",
      "| 후보 | none-정확도 (관련 없음 85) | none-정확도 (expect_none 40) | hit 하락 (S-0 대비) | 방향 쌍 | 통과 |\n|---|---|---|---|---|---|"]
for c in ("S-a", "S-b", "S-c"):
    v, m = d["verdict"][c], d["v4"][c]
    ok = v["none_acc_oracle>=0.85"] and v["hit_drop<=0.05"] and v["pairs>=15"]
    mark = lambda b: "✓" if b else "✗"  # noqa: E731
    L.append(f"| {c} | {m['none_acc_oracle']} {mark(v['none_acc_oracle>=0.85'])} | {m['none_acc_expect_none']} {mark(v['none_acc_expect_none>=0.85'])} | {v['hit_drop']:+.3f} {mark(v['hit_drop<=0.05'])} | {m['pairs_moved']}/20 {mark(v['pairs>=15'])} | {'예' if ok else '아니오'} |")
L += ["\n**세 기준을 모두 넘은 후보는 없다. 승자 없음.** none-정확도 기준만 넘은 것은 S-b다(관련 없음 0.894, expect_none 0.85). S-b의 hit 하락은 0.090, 방향 쌍은 12/20이다.\n",
      "## 실패 사례 (S-b, 시드 `6a-cases`로 5개씩)\n",
      "S-b의 과잉 로드는 9건이다. 9건 모두 process 스킬만 골랐고, 모두 등급 1이다(7건은 1개, 2건은 2개). S-0이 맞혔는데 S-b가 놓친 태스크는 28개이고, 그중 21개에서 S-b는 아무것도 고르지 않았다. 표기는 (스킬, kind, 등급, search 순위).\n",
      "### 과잉 로드 5\n"]
for c in cases["over"]:
    L.append(f"**{c['id']}** ({c['type']} · {c['phrasing']}{' · expect_none' if c['expect_none'] else ''}) — S-b: {fmt_sel(c['S-b'])}; S-0: {fmt_sel(c['S-0'], rank=False)}; 관련 없음\n")
    L.append("> " + c["text"].replace("\n", "\n> ") + "\n")
L.append("### 놓침 5 (S-0은 관련 스킬을 골랐고 S-b는 못 골랐다)\n")
for c in cases["miss"]:
    more = " …" if len(c["relevant"]) > 5 else ""
    L.append(f"**{c['id']}** ({c['type']} · {c['phrasing']}) — S-b: {fmt_sel(c['S-b'])}; S-0: {fmt_sel(c['S-0'])}; 관련 {len(c['relevant'])}개: {fmt_rel(c['relevant'][:5])}{more}\n")
    L.append("> " + c["text"].replace("\n", "\n> ") + "\n")
L += ["## 후보 전문\n", "승자가 없으므로 전문은 파일로 둔다: `select-cands/S-a/SKILL.md`(57줄), `S-b`(59줄), `S-c`(60줄). 모두 60줄 제한 안이다. S-0 대비 diff:\n"]
for c in ("S-a", "S-b", "S-c"):
    df = subprocess.run(["diff", "-u", str(S6 / "select-cands/S-0/SKILL.md"), str(S6 / f"select-cands/{c}/SKILL.md")], capture_output=True, text=True).stdout.split("\n", 2)[2]
    L.append(f"<details><summary>{c}</summary>\n\n```diff\n{df}```\n</details>\n")
L += ["## 레포 세션용: compact 결과에 kind를 넣는 데 필요한 변경\n",
      "S-a·S-b·S-c 문구는 결과의 `kind` 필드를 전제한다. 어느 후보를 쓰든 다음이 먼저 필요하다.\n",
      "1. **`skills.jsonl` 필드.** `kind`를 추가한다. 값은 `\"domain\" | \"process\" | \"tooling\"`, 없으면 `null`.",
      "   - `docs/design/index-format.md` §3 레코드 예시에 `\"kind\": \"process\"`를 넣고, 정의 세 줄을 쓴다(`stage6/gen/sys-kind.txt`의 정의 문단).",
      "2. **값 채우기 — 둘 중 하나.**",
      "   - (a) 오버레이: `stage6/kind.jsonl`(1,489행, `{id, kind}`, id는 `source/name@hash`)을 레포 데이터 파일로 넣는다(예: `data/kind.jsonl`). `ingest/build.py`에서 레코드에 병합한다. id가 바뀐 스킬은 같은 `canonical_id`의 라벨을 쓰고, 없으면 `null`이다.",
      "   - (b) extract 필드: `ingest/prompts/extract.md`와 `extract.py`의 `response_schema()`에 `kind`(enum)를 추가한다. prompt fingerprint가 바뀌므로 전체 재추출(Claude API)이 따른다.",
      "   - 이 평가는 (a)의 라벨로 쟀다.",
      "3. **`src/skillfetch/index/search.py` `search()`.**",
      "   - compact 분기(`else:`)의 dict에서 `\"tier\"` 다음에 `\"kind\": record.get(\"kind\")`를 넣는다. verbose 분기에도 같은 위치에 넣는다.",
      "   - 모듈 docstring과 index-format §4의 \"id, title, one-line summary, tier, token_estimate\" 목록에 kind를 더한다.",
      f"   - 크기: 쿼리 하나의 compact 결과가 평균 {chars:,.0f}자에서 kind 포함 약 {kchars:,.0f}자가 된다(+{kchars - chars:,.0f}자, 이 380태스크 기준). \"쿼리당 4k 토큰\" 예산 안이다.",
      "4. **테스트.**",
      "   - compact·verbose 결과에 `kind` 키가 있는지(값이 `null`이어도).",
      "   - 픽스처 index 레코드에 kind가 있을 때 그대로 나오는지.",
      "   - 오버레이 병합(a)의 id·canonical_id 대응.",
      "5. **라우터 SKILL.md.** 이 보고서의 판정으로는 바꿀 후보가 없다. kind 필드만 먼저 넣으면 S-0 문구에서는 필드가 설명 없이 보이게 된다. 문구 변경은 다음 규칙 후보가 기준을 넘은 뒤에 한다.\n",
      "## 비용 (API 환산)\n", f"| 항목 | $ |\n|---|---|\n| kind 라벨 (30회) | {ka['cost_usd']} |"]
for c in C:
    L.append(f"| 선택 {c} | {cost[c]:.2f} |")
L += [f"| v4 채점 ({pv['tasks_graded']}회) | {pv['cost_usd']} |", f"| 합 | {round(ka['cost_usd'] + sum(cost.values()) + pv['cost_usd'], 2)} |\n",
      "## 알려진 한계\n",
      "- 후보마다 1회만 생성했다. 같은 후보를 다시 돌릴 때의 변동은 재지 않았다.",
      "- 선택 모델, oracle, kind 라벨러가 모두 Opus 5.5다. 3단계 GPT 교차 라벨의 관련 여부 kappa는 0.482였다.",
      "- v4는 후보들이 고른 스킬만 추가 채점했다. 그래서 고르지 않은 쪽(none)의 정확도에는 유리할 수도, 불리할 수도 있다. 관련 없음 태스크는 89개에서 85개로 줄었다.",
      "- 배치(10태스크/호출) 선택이라 세션 안의 선택과 조건이 같지 않다. 5단계 e2e는 오프라인 선택과 세션 선택이 다르다는 것을 이미 보였다."]
(S6 / "report-6a.md").write_text("\n".join(L) + "\n")
