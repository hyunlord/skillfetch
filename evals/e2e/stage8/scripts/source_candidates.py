#!/usr/bin/env python3
"""Stage 8 §4-6: group the v5-ss out-of-index relevant SS skills (metrics-8 classification "out_of_index") by their
current GitHub repo (the search output `repo:` line; else the id repo), with relevant skill counts, (task, skill)
pairs, gap-56 coverage, license from the main-run root-LICENSE cache only (no network), and copy flags:
 - renamed: two or more id repos point to the same current repo (same skill listed under an old and a new repo name)
 - copy suspect: another repo of the same owner shares >= 3 skill names with Jaccard >= 0.5 (names from all SS search
   results of the main run). Writes source-candidates.json and source-candidates.md (top 30)."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import metrics_8 as m  # noqa: E402
from ss_parse import id_repo, parse_load, parse_search  # noqa: E402

S8 = m.S8
cur, names_by_repo, ids_by_repo = {}, defaultdict(set), defaultdict(set)
for (t, k), r in m.main.items():
    if r["tool"] == "search_skillselion":
        for x in parse_search(r["text"]):
            if x["id"]:
                rp = id_repo(x["id"])[0]
                c = (x["repo_line"] or rp).lower()
                cur[x["id"].lower()] = (x["repo_line"] or rp)
                names_by_repo[c].add(x["name"].lower())
                ids_by_repo[c].add(rp.lower())
    else:
        ld = parse_load(r["text"])
        if ld:
            names_by_repo[ld["repo"].lower()].add(ld["name"].lower())
lic = {}
for f in (S8 / "raw" / "repo-license").glob("*.json"):
    j = json.loads(f.read_text())
    lic[j["repo"].lower()] = j
ooi = [k for k in m.ss_rel if m.cls[k] == "out_of_index"]
grp = defaultdict(lambda: {"skills": set(), "names": set(), "pairs": 0, "gap": set(), "tasks": set(), "id_repos": set()})
for k in ooi:
    sid = next(m.cands[t][k]["ss_ids"][0] for t in m.ss_rel[k])
    rp = id_repo(sid)[0]
    c = cur.get(sid.lower(), rp)
    g = grp[c.lower()]
    g["display"] = c
    g["skills"].add(k)
    g["names"].add(next(m.cands[t][k]["title"] for t in m.ss_rel[k]).lower())
    g["pairs"] += len(m.ss_rel[k])
    g["tasks"] |= m.ss_rel[k]
    g["gap"] |= m.ss_rel[k] & set(m.GAP)
    g["id_repos"].add(rp.lower())
rows = []
for c, g in grp.items():
    aliases = sorted(ids_by_repo.get(c, set()) | g["id_repos"])
    renamed = [a for a in aliases if a != c]
    owner = c.split("/")[0]
    sus = []
    for o, ns in names_by_repo.items():
        if o != c and o.split("/")[0] == owner and o not in aliases:
            a, b = names_by_repo.get(c, set()), ns
            inter = len(a & b)
            if inter >= 3 and inter / len(a | b) >= 0.5:
                sus.append(f"{o} ({inter} 공통, J={inter / len(a | b):.2f})")
    L = None
    for a in [c] + aliases:
        if a in lic:
            L = lic[a]
            break
    rows.append({"repo": g["display"], "relevant_skills_ids": len(g["skills"]), "relevant_skill_names": len(g["names"]),
                 "pairs": g["pairs"], "tasks": len(g["tasks"]), "gap56": len(g["gap"]),
                 "license": (L["spdx"] if L["spdx"] != "per-skill" else "루트 LICENSE 없음") if L else "미확인",
                 "license_file": (L or {}).get("file"), "renamed_aliases": renamed, "copy_suspect": sus})
rows.sort(key=lambda r: (-r["relevant_skill_names"], -r["gap56"], -r["pairs"], r["repo"].lower()))
(S8 / "source-candidates.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
gap_cover_all = len(set().union(*[g["gap"] for g in grp.values()]))
top = rows[:30]
gap_top = len(set().union(*[grp[r["repo"].lower()]["gap"] for r in top]))
md = ["# 소스 후보 — v5-ss index 밖 관련 스킬의 원본 저장소 (상위 30)", "",
      f"- 대상: v5-ss 등급 ≥2를 받은 SS 쪽 스킬 중 index 밖으로 분류된 {len(ooi):,}개(`metrics-8.json`). 저장소 {len(rows)}개로 묶인다.",
      "- 저장소: SS 검색 출력의 `repo:` 줄(현재 저장소). 없으면 id의 저장소를 쓴다.",
      "- 관련 스킬 수: 고유 이름 수(괄호 안은 SS id 수 — 옛 저장소명 id와 새 저장소명 id가 둘 다 있으면 2로 센다).",
      "- 쌍: 그 저장소 스킬이 등급 ≥2를 받은 (태스크, 스킬) 수. 태스크: 그런 태스크 수.",
      "- 공백 56: v3 oracle 관련 0·expect_none 아님·trivial 아님 태스크 56개 중 이 저장소의 index 밖 관련 스킬이 있는 태스크 수.",
      "- 라이선스: 본 실행에서 받은 루트 LICENSE 캐시(`raw/repo-license/`, 로드된 스킬의 저장소만)를 skillfetch `classify_text`로 분류한 것이다. 이번에는 네트워크를 쓰지 않았다. 캐시에 없으면 \"미확인\", 루트에 LICENSE 파일이 없으면 \"루트 LICENSE 없음\", 파일은 있는데 분류 규칙에 안 걸리면 \"unknown\"이다. 스킬 폴더·frontmatter 라이선스는 이 표에 넣지 않았다.",
      "- 이름만 바뀐 사본: 같은 현재 저장소를 가리키는 다른 id 저장소명. 사본 의심: 같은 owner의 다른 저장소와 검색 결과 스킬 이름이 3개 이상 겹치고 Jaccard ≥ 0.5.",
      f"- 상위 30개가 커버하는 공백 태스크: {gap_top}/56 (전체 {len(rows)}개 저장소: {gap_cover_all}/56).", "",
      "| # | 저장소 | 관련 스킬 (id) | 쌍 | 태스크 | 공백 56 | 라이선스 | 이름만 바뀐 사본 | 사본 의심 |",
      "|---:|---|---:|---:|---:|---:|---|---|---|"]
for i, r in enumerate(top, 1):
    md.append(f"| {i} | [{r['repo']}](https://github.com/{r['repo']}) | {r['relevant_skill_names']} ({r['relevant_skills_ids']}) | {r['pairs']} | {r['tasks']} | {r['gap56']} | "
              f"{r['license']} | {', '.join(r['renamed_aliases']) or '–'} | {'; '.join(r['copy_suspect']) or '–'} |")
lic_cnt = defaultdict(int)
for r in rows:
    lic_cnt[r["license"]] += 1
md += ["", f"전체 {len(rows)}개 저장소의 라이선스: " + ", ".join(f"{k} {v}" for k, v in sorted(lic_cnt.items(), key=lambda x: -x[1])) + ".",
       f"이름만 바뀐 사본이 있는 저장소 {sum(bool(r['renamed_aliases']) for r in rows)}개, 사본 의심 {sum(bool(r['copy_suspect']) for r in rows)}개(전체 기준).", "",
       "전체 목록: `source-candidates.json`. 스크립트: `scripts/source_candidates.py`."]
(S8 / "source-candidates.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
