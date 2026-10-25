#!/usr/bin/env python3
"""§3: move source-skill-map.jsonl labels onto staging new ids. Order: SKILL.md hash -> path -> name/install arg;
ties -> canonical only, else ambiguous; several rows -> one id: per-task max grade (process of that row; ties -> any).
usage: s9_migrate.py <staging_dir>  -> migration.json, oracle-v5-ss-b-s9.jsonl"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from s9_common import OUT, BASE_INDEX, S8, S9, jl, records, repo_of, vb

base, stg = records(BASE_INDEX), records(sys.argv[1])
new = {i: r for i, r in stg.items() if i not in base}
base_hash = {(r.get("files") or {}).get("SKILL.md"): i for i, r in base.items()}
rej = jl(Path(sys.argv[1]) / "rejected.jsonl") if (Path(sys.argv[1]) / "rejected.jsonl").exists() else []
by_repo = defaultdict(list)
for i, r in new.items():
    by_repo[repo_of(r)].append(i)
last = lambda p: (p or "").rstrip("/").split("/")[-1].lower()  # noqa: E731


def pick(c):
    c = sorted(set(c))
    if len(c) > 1:
        c = [i for i in c if new[i].get("canonical_id", i) == i] or c
    return c


rows = jl(S8 / "source-skill-map.jsonl")
res = []
for row in rows:
    repos = {x.lower() for x in (row["repo"], row.get("renamed_from"), row.get("id_repo")) if x}
    cand_ids = [i for rp in repos for i in by_repo.get(rp, [])]
    out = {"oracle_key": row["oracle_key"], "repo": row["repo"], "name": row["name"], "new_id": None, "step": None, "reason": None}
    h = row.get("skill_md_sha256")
    if h and h in base_hash:
        out.update(reason="already_in_baseline", baseline_id=base_hash[h])
        res.append(out)
        continue
    steps = [("hash", [i for i, r in new.items() if h and (r.get("files") or {}).get("SKILL.md") == h]),
             ("path", [i for i in cand_ids if row.get("path") and (new[i].get("path") or "").rstrip("/") == row["path"].rsplit("/SKILL.md", 1)[0].rstrip("/")]),
             ("name", [i for i in cand_ids if (new[i].get("name") or "").lower() == row["name"].lower()
                       or last(new[i].get("path")) in {last(row.get("install_skill_arg")), last(row.get("slug"))} - {""}])]
    for step, c in steps:
        c = pick(c)
        if len(c) == 1:
            out.update(new_id=c[0], step=step)
            break
        if len(c) > 1:
            out.update(reason="ambiguous", step=step, candidates=c[:10])
            break
    if not out["new_id"] and not out["reason"]:
        rp_path = (row.get("path") or "").rsplit("/SKILL.md", 1)[0].rstrip("/")
        hit = [r for r in rej if (h and (r.get("files") or {}).get("SKILL.md") == h)
               or (repo_of(r) in repos and ((rp_path and (r.get("path") or "").rstrip("/") == rp_path)
                                            or (r.get("name") or "").lower() == row["name"].lower()
                                            or last(r.get("path")) in {last(row.get("install_skill_arg")), last(row.get("slug"))} - {""}))]
        if hit:
            out.update(reason="rejected", rejected_id=hit[0].get("id"), rejected_status=hit[0].get("status"),
                       rejected_detail={"lint_errors": [e.get("rule") for e in (hit[0].get("lint") or {}).get("errors", [])],
                                        "scan_failures": [f.get("rule_id") for f in (hit[0].get("scan") or {}).get("failures", [])],
                                        "license": hit[0].get("license"), "not_extracted_reason": hit[0].get("not_extracted_reason")})
        elif not cand_ids:
            out["reason"] = "repo_not_ingested"
        else:
            out["reason"] = "not_found"
    res.append(out)
mp = {r["oracle_key"]: r["new_id"] for r in res if r["new_id"]}
rows_out = []
for t, o in vb.items():
    pool = {}
    for x in o["pool"]:
        k = mp.get(x["skill"], x["skill"])
        y = {**x, "skill": k, **({"migrated_from": x["skill"]} if k != x["skill"] else {})}
        if k in pool:
            a = pool[k]
            if y["grade"] > a["grade"] or (y["grade"] == a["grade"] and y["process"] and not a["process"]):
                pool[k] = {**y, "merged_from": a.get("merged_from", [a.get("migrated_from", a["skill"])]) + [y.get("migrated_from", k)]}
            else:
                pool[k] = {**a, "merged_from": a.get("merged_from", [a.get("migrated_from", a["skill"])]) + [y.get("migrated_from", k)]}
        else:
            pool[k] = y
    pl = list(pool.values())
    rows_out.append({**o, "pool": pl, "relevant": [x["skill"] for x in pl if x["grade"] >= 2]})
(OUT / "oracle-v5-ss-b-s9.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in rows_out))
summ = {"rows": len(res), "matched": sum(bool(r["new_id"]) for r in res), "by_step": dict(Counter(r["step"] for r in res if r["new_id"])),
        "unmatched_by_reason": dict(Counter(r["reason"] for r in res if not r["new_id"])),
        "distinct_new_ids": len(set(mp.values())), "rows_sharing_a_new_id": sum(c for c in Counter(mp.values()).values() if c > 1),
        "unmatched_by_repo": dict(Counter(r["repo"] for r in res if not r["new_id"]).most_common())}
(OUT / "migration.json").write_text(json.dumps({"summary": summ, "rows": res}, indent=1, ensure_ascii=False))
print(json.dumps(summ, ensure_ascii=False))
