#!/usr/bin/env python3
"""Stage 8 §2 / §2-추가 4, 8: per task, candidate union = SS-q1 ∪ SS-q3 ∪ SS-kw results ∪ SS-load-kw / SS-load-full
loaded skill ∪ SF R-c top-10 ∪ SF S-b' selections (3 runs). SS results that are the same skill as an index skill
((owner/repo, name) match + SKILL.md sha256 equal) are merged into the index id. Cards: title = name,
summary = 220-char description. Writes cands.json {task: {key: {title, summary, sources, ss_ids}}} and ss-map.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ss_parse import desc220, fetch_skill_md, frontmatter_desc, id_repo, index, parse_load, parse_search, sha  # noqa: E402

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
recs, by_rp, by_name = index()
tasks = [json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()]
rc = json.loads((E2E / "stage6" / "gen" / "results-rc.json").read_text())
sel = [{json.loads(l)["id"]: json.loads(l)["skills"] for l in (E2E / "stage6" / f).open()}
       for f in ("select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl")]
main = {}
for l in (S8 / "raw" / "main.jsonl").open():
    r = json.loads(l)
    main[(r["task"], r["kind"])] = r  # last record wins (resume)

# every SS search result seen anywhere: (repo lower, name lower) -> (id, desc)
seen = {}
for (t, k), r in main.items():
    if r["tool"] == "search_skillselion":
        for x in parse_search(r["text"]):
            if x["id"]:
                rp, _ = id_repo(x["id"])
                for repo in {rp.lower(), x["repo_line"].lower()} - {""}:
                    seen.setdefault((repo, x["name"].lower()), (x["id"], x["desc"]))


def ss_body(sid, task=None, kind=None):
    """SS-side SKILL.md bytes: the loaded copy when this candidate was loaded in (task, kind), else raw GitHub."""
    if task and kind:
        p = S8 / "raw" / "load" / kind / task / "SKILL.md"
        if p.exists():
            return p.read_bytes()
    repo, slug = id_repo(sid)
    return fetch_skill_md(repo, slug) if repo else None


merge_cache = {}


def merged_id(sid, name, repo_line, task=None, kind=None):
    """index id if this SS result is the same skill (repo+name match and SKILL.md hash equal), else None."""
    repo, slug = id_repo(sid)
    names = {name.lower(), slug.split("/")[-1].lower()} - {""}
    cands = []
    for rp in {repo.lower(), (repo_line or "").lower()} - {""}:
        for n in names:
            cands += by_rp.get((rp, n), [])
    if not cands:
        return None, "no_repo_name_match"
    if sid in merge_cache:
        return merge_cache[sid]
    body = ss_body(sid, task, kind)
    if body is None:
        res = (None, "repo_name_match_body_unavailable")
    else:
        h = sha(body)
        hit = [c for c in cands if (recs[c].get("files") or {}).get("SKILL.md") == h]
        res = (hit[0], "merged") if hit else (None, "repo_name_match_hash_differs")
    merge_cache[sid] = res
    return res


out, ss_map, stats = {}, {}, {"merge": {}}
for t in tasks:
    tid = t["id"]
    c = {}

    def add(key, title, summary, src, ss_id=None):
        e = c.setdefault(key, {"title": title, "summary": summary, "sources": [], "ss_ids": []})
        if src not in e["sources"]:
            e["sources"].append(src)
        if ss_id and ss_id not in e["ss_ids"]:
            e["ss_ids"].append(ss_id)

    def add_ss(sid, name, repo_line, desc, src, kind=None):
        mid, why = merged_id(sid, name, repo_line, tid, kind)
        stats["merge"][why] = stats["merge"].get(why, 0) + 1
        ss_map[sid] = {"merged_into": mid, "why": why}
        if mid:
            r = recs[mid]
            add(mid, r["name"], desc220(r.get("description")), src, sid)
        else:
            add("ss:" + sid.lower(), name, desc220(desc), src, sid)

    for k in ("SS-q1", "SS-q3", "SS-kw"):
        for x in parse_search(main[(tid, k)]["text"]):
            if x["id"]:
                add_ss(x["id"], x["name"], x["repo_line"], x["desc"], k)
    for k in ("SS-load-kw", "SS-load-full"):
        ld = parse_load(main[(tid, k)]["text"])
        if not ld:
            continue
        hit = seen.get((ld["repo"].lower(), ld["name"].lower()))
        if hit:
            sid, desc = hit
        else:
            sid = f"skill:{ld['repo']}#{ld['name']}"
            p = S8 / "raw" / "load" / k / tid / "SKILL.md"
            desc = frontmatter_desc(p.read_text(errors="replace")) if p.exists() else ""
        add_ss(sid, ld["name"], ld["repo"], desc, k, kind=k)
    for x in rc[tid]["results"][:10]:
        r = recs[x["id"]]
        add(x["id"], r["name"], desc220(r.get("description")), "SF-top10")
    for i, s in enumerate(sel):
        for sid in s.get(tid, []):
            r = recs[sid]
            add(sid, r["name"], desc220(r.get("description")), f"SF-sel-r{i + 1}")
    out[tid] = c
(S8 / "cands.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
(S8 / "ss-map.json").write_text(json.dumps(ss_map, ensure_ascii=False, indent=0))
n = [len(v) for v in out.values()]
stats.update({"tasks": len(out), "candidates": sum(n), "per_task_min": min(n), "per_task_max": max(n),
              "per_task_mean": round(sum(n) / len(n), 1),
              "empty_desc": sum(1 for v in out.values() for e in v.values() if not e["summary"])})
(S8 / "cands-summary.json").write_text(json.dumps(stats, indent=1))
print(json.dumps(stats))
