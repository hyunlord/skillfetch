#!/usr/bin/env python3
"""§9 (replaces §1): every release skills.jsonl / rejected.jsonl line present byte-identical in staging, no release id
with different bytes; constraints.jsonl of release skills equal except fan_out (multiset per skill); other files
(manifest, dupgroups, pairs) reported. usage: s9_precheck.py <staging_dir> -> precheck.json; exit 1 on failure."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from s9_common import OUT, BASE_INDEX, S9, repo_of

B, S = BASE_INDEX, Path(sys.argv[1]).expanduser()
lines = lambda p: p.read_bytes().splitlines()  # noqa: E731
out = {"release": str(B), "staging": str(S)}
ok = True
for f in ("skills.jsonl", "rejected.jsonl"):
    bl, sl = lines(B / f), lines(S / f)
    sset = Counter(sl)
    missing = [l for l in bl if not sset[l]]
    bid = {json.loads(l)["id"] for l in bl}
    sid_lines = defaultdict(list)
    for l in sl:
        sid_lines[json.loads(l)["id"]].append(l)
    rel_changed = [i for i in bid if any(l not in set(bl) for l in sid_lines.get(i, []))]
    dup_ids = [i for i, v in sid_lines.items() if len(v) > 1]
    out[f] = {"release_lines": len(bl), "staging_lines": len(sl), "release_lines_missing_in_staging": len(missing),
              "release_ids_with_other_bytes_in_staging": len(rel_changed), "duplicate_ids_in_staging": len(dup_ids),
              "new_lines": sum(1 for l in sl if json.loads(l)["id"] not in bid),
              "examples": [json.loads(l)["id"] for l in missing[:5]] + rel_changed[:5]}
    ok &= not missing and not rel_changed and not dup_ids
# constraints: per release skill, multiset of rows without fan_out
strip = lambda d: json.dumps({k: v for k, v in d.items() if k != "fan_out"}, sort_keys=True, ensure_ascii=False)  # noqa: E731
bc, sc = defaultdict(Counter), defaultdict(Counter)
bfan, sfan = {}, {}
for l in lines(B / "constraints.jsonl"):
    d = json.loads(l)
    bc[d["skill_id"]][strip(d)] += 1
    bfan[d["id"]] = d.get("fan_out")
release_skills = set(bc)
for l in lines(S / "constraints.jsonl"):
    d = json.loads(l)
    sc[d["skill_id"]][strip(d)] += 1
    sfan[d["id"]] = d.get("fan_out")
diff_skills = [s for s in release_skills if bc[s] != sc.get(s, Counter())]
flip = Counter((bfan[i], sfan.get(i)) for i in bfan if bfan[i] != sfan.get(i))
out["constraints.jsonl"] = {"release_rows": sum(sum(c.values()) for c in bc.values()), "staging_rows": sum(sum(c.values()) for c in sc.values()),
                            "release_skills": len(release_skills), "release_skills_differing_beyond_fan_out": len(diff_skills),
                            "examples": diff_skills[:5], "fan_out_changed": {f"{a}->{b}": n for (a, b), n in flip.items()},
                            "fan_out_changed_total": sum(flip.values()), "new_skill_rows": sum(sum(c.values()) for s, c in sc.items() if s not in release_skills)}
ok &= not diff_skills
# other files (reported, not part of the condition)
bm, sm = json.loads((B / "manifest.json").read_text()), json.loads((S / "manifest.json").read_text())
bd = json.loads((B / "dupgroups.json").read_text()) if (B / "dupgroups.json").exists() else {}
sd = json.loads((S / "dupgroups.json").read_text()) if (S / "dupgroups.json").exists() else {}
out["other_files"] = {
    "manifest_sources_release": [s["id"] for s in bm.get("sources", [])], "manifest_sources_staging": [s["id"] for s in sm.get("sources", [])],
    "manifest_keys_changed": sorted(k for k in set(bm) | set(sm) if bm.get(k) != sm.get(k)),
    "release_sources_same_in_staging": all(any(s == t for t in sm.get("sources", [])) for s in bm.get("sources", [])),
    "dupgroups_release": len(bd), "dupgroups_staging": len(sd), "release_dupgroups_kept": all(sd.get(k) == v for k, v in bd.items()),
    "pairs_release_lines": len(lines(B / "pairs.jsonl")) if (B / "pairs.jsonl").exists() else None,
    "pairs_staging_lines": len(lines(S / "pairs.jsonl")) if (S / "pairs.jsonl").exists() else None}
sk = [json.loads(l) for l in lines(S / "skills.jsonl")]
bid = {json.loads(l)["id"] for l in lines(B / "skills.jsonl")}
new = [r for r in sk if r["id"] not in bid]
out["new_records"] = {"n": len(new), "by_repo": dict(Counter(repo_of(r) for r in new).most_common()),
                      "by_tier": dict(Counter(r.get("tier") for r in new)), "by_status": dict(Counter(r.get("status") for r in new)),
                      "outside_default_tiers": sum(r.get("tier") not in ("A", "B") for r in new),
                      "non_canonical": sum(r.get("canonical_id", r["id"]) != r["id"] for r in new)}
out["precondition_ok"] = bool(ok)
(OUT / "precheck.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
sys.exit(0 if ok else 1)
