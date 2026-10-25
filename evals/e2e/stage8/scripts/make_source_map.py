#!/usr/bin/env python3
"""#60 prep: for the top-30 repos of source-candidates.md, every SS-side skill (key "ss:...") graded >= 2 in oracle
v5-ss-b, with what a repo session needs to find it in a staging index after ingesting those repos, and all its v5-ss-b
label rows (every task where it was graded, any grade) so the labels can be moved to the new index id.
Offline: in-repo paths are only known where the main run fetched the SKILL.md (raw/skillmd-fetch); otherwise
path = null and match on skill_md_sha256 (when the body is known) or on name / install_skill_arg / slug.
Writes source-skill-map.jsonl and source-skill-map-summary.json."""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ss_parse import id_repo, parse_search  # noqa: E402

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
v3 = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "followup" / "oracle-v3.jsonl").open()}
vb = {json.loads(l)["id"]: json.loads(l) for l in (S8 / "oracle-v5-ss-b.jsonl").open()}
cands = json.loads((S8 / "cands.json").read_text())
metrics = json.loads((S8 / "metrics-8.json").read_text())
top30 = json.loads((S8 / "source-candidates.json").read_text())[:30]
GAP = {t for t in tasks if not v3[t]["relevant"] and not tasks[t]["expect_none"] and tasks[t]["task_type"] != "trivial"}
top = {r["repo"].lower(): r for r in top30}
alias = {a: r["repo"].lower() for r in top30 for a in r["renamed_aliases"]}

# per SS id: current repo line, install --skill arg (from search output), name
info = {}
for l in (S8 / "raw" / "main.jsonl").open():
    r = json.loads(l)
    if r["tool"] != "search_skillselion":
        continue
    for blk in re.split(r"^### ", r["text"], flags=re.M)[1:]:
        x = parse_search("### " + blk)
        if not x or not x[0]["id"]:
            continue
        x = x[0]
        inst = re.search(r"install: `npx skills add (\S+) --skill ([^`]+)`", blk)
        info.setdefault(x["id"].lower(), {"repo_line": x["repo_line"], "name": x["name"],
                                          "install_url": inst.group(1) if inst else None, "install_skill_arg": inst.group(2).strip() if inst else None})
fetched = {}
for f in (S8 / "raw" / "skillmd-fetch").glob("*.json"):
    j = json.loads(f.read_text())
    fetched[(j["repo"].lower(), j["slug"])] = j

rows, per_repo = [], defaultdict(int)
seen = set()
for t, o in vb.items():
    for x in o["pool"]:
        k = x["skill"]
        if not k.startswith("ss:") or x["grade"] < 2 or k in seen:
            continue
        sid = next(e for tt in tasks if k in cands.get(tt, {}) for e in cands[tt][k]["ss_ids"])
        rp, slug = id_repo(sid)
        inf = info.get(sid.lower(), {})
        cur = (inf.get("repo_line") or rp).lower()
        cur = alias.get(cur, cur)
        if cur not in top:
            continue
        seen.add(k)
        # body: loaded copy (any task / load condition where this key was loaded) or the main run's raw fetch
        sha, body_src, path = None, None, None
        for tt in tasks:
            e = cands[tt].get(k)
            if e:
                for kind in ("SS-load-kw", "SS-load-full"):
                    p = S8 / "raw" / "load" / kind / tt / "SKILL.md"
                    if kind in e["sources"] and p.exists():
                        sha, body_src = hashlib.sha256(p.read_bytes()).hexdigest(), f"raw/load/{kind}/{tt}/SKILL.md"
                        break
            if sha:
                break
        fj = fetched.get((rp.lower(), slug))
        if fj and fj["content"] is not None:
            path = fj["path"]
            if not sha:
                sha, body_src = hashlib.sha256(fj["content"].encode()).hexdigest(), "raw/skillmd-fetch (raw.githubusercontent, decoded text)"
        labels = [{"task": tt, "grade": y["grade"], "process": y["process"], "label_set": "v5-ss" if y["label"].startswith("c") else "v5-ss-b"}
                  for tt, oo in vb.items() for y in oo["pool"] if y["skill"] == k]
        rel_tasks = sorted(l["task"] for l in labels if l["grade"] >= 2)
        title = next(cands[tt][k]["title"] for tt in tasks if k in cands.get(tt, {}))
        rows.append({"oracle_key": k, "ss_id": sid, "repo": top[cur]["repo"], "repo_url": f"https://github.com/{top[cur]['repo']}",
                     "id_repo": rp, "renamed_from": rp if rp.lower() != cur else None, "slug": slug or None,
                     "name": title, "install_skill_arg": inf.get("install_skill_arg"),
                     "path": (path.split("/", 1)[1] if path else None), "branch": (path.split("/", 1)[0] if path else None),
                     "path_source": "raw.githubusercontent fetch (main run)" if path else None,
                     "skill_md_sha256": sha, "skill_md_sha256_source": body_src,
                     "classification": None,  # filled below from metrics_8
                     "summary": next(cands[tt][k]["summary"] for tt in tasks if k in cands.get(tt, {})),
                     "relevant_tasks": rel_tasks, "gap56_tasks": sorted(set(rel_tasks) & GAP), "labels": sorted(labels, key=lambda l: l["task"])})
        per_repo[top[cur]["repo"]] += 1
# out-of-index classification from metrics_8 (recomputed there; here only names it per key)
sys.argv = [sys.argv[0]]
import metrics_8 as m  # noqa: E402
for r in rows:
    r["classification"] = m.cls.get(r["oracle_key"], "relevant only in v5-ss-b rows")
rows.sort(key=lambda r: (r["repo"].lower(), r["name"].lower(), r["ss_id"]))
(S8 / "source-skill-map.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
summ = {"repos": len(per_repo), "skills": len(rows), "per_repo": dict(sorted(per_repo.items(), key=lambda x: -x[1])),
        "with_path": sum(bool(r["path"]) for r in rows), "with_skill_md_sha256": sum(bool(r["skill_md_sha256"]) for r in rows),
        "with_install_skill_arg": sum(bool(r["install_skill_arg"]) for r in rows),
        "renamed_id": sum(bool(r["renamed_from"]) for r in rows),
        "label_rows": sum(len(r["labels"]) for r in rows), "relevant_pairs": sum(len(r["relevant_tasks"]) for r in rows),
        "gap56_covered": len({t for r in rows for t in r["gap56_tasks"]}),
        "classification": dict(__import__("collections").Counter(r["classification"] for r in rows))}
(S8 / "source-skill-map-summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
print(json.dumps(summ, ensure_ascii=False))
