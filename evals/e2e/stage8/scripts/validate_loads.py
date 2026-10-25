#!/usr/bin/env python3
"""Stage 8 §2 검증: every body SS-load-kw / SS-load-full loaded (raw/load/<kind>/<task>/: SKILL.md + bundled files)
through skillfetch 38dcb69 lint_skill + scan_skill (injection rules, scripts) and skill_license. The repo-level license
(source_license) is read from the repo root LICENSE* via raw.githubusercontent (no token); none found -> "per-skill".
Run: uvx --from git+https://github.com/hyunlord/skillfetch@38dcb69 python scripts/validate_loads.py
Writes validate-loads.json (per load) and validate-summary.json."""
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from skillfetch.ingest.injection import load_rules, scan_skill
from skillfetch.ingest.licenses import LICENSE_FILES, classify_text, skill_license
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.skillfile import read_skill

S8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S8 / "scripts"))
from ss_parse import parse_load  # noqa: E402

main = {}
for l in (S8 / "raw" / "main.jsonl").open():
    r = json.loads(l)
    main[(r["task"], r["kind"])] = r
LC = S8 / "raw" / "repo-license"
LC.mkdir(exist_ok=True)


def repo_license(repo):
    f = LC / (re.sub(r"[^\w.-]", "_", repo) + ".json")
    if f.exists():
        return json.loads(f.read_text())["spdx"]
    spdx, src = "per-skill", None
    for br in ("main", "master"):
        for n in LICENSE_FILES:
            try:
                with urllib.request.urlopen(f"https://raw.githubusercontent.com/{repo}/{br}/{n}", timeout=20) as r:
                    t = r.read().decode("utf-8", "replace")
                c = classify_text(t)
                spdx, src = (c or "unknown"), f"{br}/{n}"
                break
            except Exception:
                continue
        if src:
            break
    f.write_text(json.dumps({"repo": repo, "spdx": spdx, "file": src}))
    return spdx


rows = []
for kind in ("SS-load-kw", "SS-load-full"):
    for (tid, k), r in sorted(main.items()):
        if k != kind:
            continue
        ld = parse_load(r["text"])
        if not ld:
            continue
        d = S8 / "raw" / "load" / kind / tid
        row = {"task": tid, "kind": kind, "name": ld["name"], "repo": ld["repo"], "copied": (d / "SKILL.md").exists()}
        if row["copied"]:
            files = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
            lint, scan = lint_skill(d), scan_skill(d)
            try:
                fm = read_skill(d).frontmatter
            except Exception:
                fm = None
            lic = skill_license(d, fm, repo_license(ld["repo"]))
            row.update({"files": files, "skill_md_sha256": hashlib.sha256((d / "SKILL.md").read_bytes()).hexdigest(),
                        "lint_errors": [i.model_dump() for i in lint.errors], "lint_warnings": len(lint.warnings),
                        "scan_failures": [h.model_dump() for h in scan.failures],
                        "scan_warnings": [h.model_dump() for h in scan.warnings], "scripts": scan.scripts,
                        "license": lic.license, "redistributable": lic.redistributable, "license_origin": lic.origin})
        rows.append(row)
(S8 / "validate-loads.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))


def summ(rs):
    c = [r for r in rs if r["copied"]]
    return {"loads": len(rs), "body_copied": len(c),
            "lint_error": sum(bool(r["lint_errors"]) for r in c), "scan_fail": sum(bool(r["scan_failures"]) for r in c),
            "scan_warn": sum(bool(r["scan_warnings"]) for r in c), "has_scripts": sum(bool(r["scripts"]) for r in c),
            "bundled_files_gt0": sum(len(r["files"]) > 1 for r in c),
            "license": dict(Counter(r["license"] for r in c).most_common()),
            "license_origin": dict(Counter(r["license_origin"] for r in c).most_common()),
            "redistributable": sum(r["redistributable"] for r in c),
            "scan_fail_rules": dict(Counter(h["rule_id"] for r in c for h in r["scan_failures"]).most_common()),
            "lint_error_rules": dict(Counter(i["rule"] for r in c for i in r["lint_errors"]).most_common())}


uniq = {}
for r in rows:
    if r["copied"]:
        uniq.setdefault(r["skill_md_sha256"], r)
out = {"scan_rules_version": load_rules().version, "per_kind": {k: summ([r for r in rows if r["kind"] == k]) for k in ("SS-load-kw", "SS-load-full")},
       "unique_bodies": summ(list(uniq.values()))}
(S8 / "validate-summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, ensure_ascii=False))
