#!/usr/bin/env python3
"""Staging bundle for #60's first application (offline; no network: urlopen is disabled).
Gap-56 tasks covered per repository = the 56 gap tasks (oracle v3 relevant 0, not expect_none, not trivial) on which a
v5-ss relevant, out-of-index Skillselion skill from that repository (current repo, as source_candidates.py) is relevant.
Gate: drop repositories whose lint-failure rate (survey30.json) is above 50%. Then greedy set cover: the repository that
adds the most new gap tasks first (ties: fewer extraction requests), while the requests sum stays <= 1000."""
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

def _no_net(*a, **k):
    raise RuntimeError("network disabled")
urllib.request.urlopen = _no_net

E2E = Path(__file__).resolve().parents[1]
S8 = E2E / "stage8"
sys.path.insert(0, str(S8 / "scripts"))
from ss_parse import fetch_skill_md, id_repo, index, parse_search, sha  # noqa: E402

recs, by_rp, by_name = index()
tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S8 / "oracle-v5-ss.jsonl").open()}
v3 = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "followup" / "oracle-v3.jsonl").open()}
ss_map = json.loads((S8 / "ss-map.json").read_text())
cands = json.loads((S8 / "cands.json").read_text())
main = {(r["task"], r["kind"]): r for r in map(json.loads, (S8 / "raw" / "main.jsonl").open())}
GAP = {t for t in tasks if not v3[t]["relevant"] and not tasks[t]["expect_none"] and tasks[t]["task_type"] != "trivial"}
R = {t: set(o["relevant"]) for t, o in orc.items()}
ss_rel = defaultdict(set)
for t in tasks:
    for k in R[t]:
        if k.startswith("ss:"):
            ss_rel[k].add(t)

def classify(k):
    e = next(cands[t][k] for t in ss_rel[k])
    sid = e["ss_ids"][0]
    if (ss_map.get(sid) or {}).get("why") in ("repo_name_match_hash_differs", "repo_name_match_body_unavailable"):
        return "other"
    same = by_name.get(e["title"].lower(), [])
    if not same:
        return "out_of_index"
    repo, slug = id_repo(sid)
    try:
        body = fetch_skill_md(repo, slug)
    except RuntimeError:
        return "other"
    if body is None:
        return "other"
    return "other" if any((recs[s].get("files") or {}).get("SKILL.md") == sha(body) for s in same) else "out_of_index"

cur = {}
for (t, kind), r in main.items():
    if r["tool"] == "search_skillselion":
        for x in parse_search(r["text"]):
            if x["id"]:
                cur[x["id"].lower()] = (x["repo_line"] or id_repo(x["id"])[0]).lower()
gap_by_repo = defaultdict(set)
for k in ss_rel:
    if classify(k) != "out_of_index":
        continue
    sid = next(cands[t][k]["ss_ids"][0] for t in ss_rel[k])
    gap_by_repo[cur.get(sid.lower(), id_repo(sid)[0].lower())] |= ss_rel[k] & GAP

survey = [r for r in json.load(open(E2E / "staging30" / "survey30.json")) if "error" not in r]
check = {r["repo"]: r["gap56"] for r in json.load(open(S8 / "source-candidates.json"))}
rows = []
for r in survey:
    g = gap_by_repo.get(r["repo"].lower(), set())
    assert len(g) == check[r["repo"]], (r["repo"], len(g), check[r["repo"]])  # same as source-candidates.json
    rate = r["lint_failed"] / r["discovered"] if r["discovered"] else 0.0
    rows.append({**r, "gap_set": sorted(g), "lint_fail_rate": round(rate, 3)})
gated = [r for r in rows if r["lint_fail_rate"] > 0.5]
pool = [r for r in rows if r["lint_fail_rate"] <= 0.5 and r["new"] > 0]
covered, total, picked = set(), 0, []
while True:
    options = [r for r in pool if r not in picked and total + r["new"] <= 1000]
    options = [r for r in options if set(r["gap_set"]) - covered]
    if not options:
        break
    best = min(options, key=lambda r: (-len(set(r["gap_set"]) - covered), r["new"], r["rank"]))
    gain = len(set(best["gap_set"]) - covered)
    covered |= set(best["gap_set"])
    total += best["new"]
    picked.append(best)
    best["gain"], best["cum_requests"], best["cum_gap"] = gain, total, len(covered)
out = {"gated": [{"repo": r["repo"], "lint_failed": r["lint_failed"], "discovered": r["discovered"], "rate": r["lint_fail_rate"]} for r in gated],
       "picked": [{"repo": r["repo"], "new": r["new"], "gain": r["gain"], "cum_requests": r["cum_requests"], "cum_gap": r["cum_gap"],
                   "commit": r["commit"]} for r in picked],
       "covered_gap": len(covered), "requests": total,
       "unpicked_with_gain": [{"repo": r["repo"], "new": r["new"], "adds": len(set(r["gap_set"]) - covered)} for r in pool if r not in picked and set(r["gap_set"]) - covered]}
(E2E / "staging30" / "bundle.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
