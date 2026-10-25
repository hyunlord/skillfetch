#!/usr/bin/env python3
"""Each check must fail on the untouched repo (s2-a) and pass on s2-a + the reference files in stage2/reference/.
Writes stage2/checks/VALIDATION.md."""
import json
import shutil
import sys
from pathlib import Path

import yaml

S2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import run_s2  # noqa: E402
from run_task import sh  # noqa: E402

REF = {"s2-tests": {"tests/test_rules_ref.py": "tests/test_rules_ref.py"},
       "s2-api": {"api/app/main.py": "app/main.py", "api/tests/test_api.py": "tests/test_api.py", "api/conftest.py": "conftest.py"},
       "s2-docs": {"docs/README.md": "README.md"},
       "s2-data": {"data/scripts/clean_orders.py": "scripts/clean_orders.py"}}
root = Path.home() / "skillfetch-e2e-wt" / "s2-validate"
lines = ["# Stage 2 check validation", "", "| task | tree | check pass | items |", "|---|---|---|---|"]
for t in yaml.safe_load((S2 / "tasks-stage2.yaml").read_text())["tasks"]:
    base = sh(["git", "-C", str(S2.parent / "repos" / t["repo"]), "rev-parse", "s2-a"], check=True).stdout.strip()
    for kind in ("base", "reference"):
        wt = root / f"{t['id']}-{kind}"
        run_s2.prepare(t, wt, base)
        if kind == "reference":
            for src, dst in REF[t["id"]].items():
                (wt / dst).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(S2 / "reference" / src, wt / dst)
        out = root / f"{t['id']}-{kind}"  # run_check writes <out>.check/
        if Path(str(out) + ".check").exists():
            shutil.rmtree(str(out) + ".check")
        res = run_s2.run_check(t, wt, base, out)
        items = "; ".join(f"{i['name']}: {'ok' if i['pass'] else 'FAIL'}" for i in res.get("items", []))
        mx = {k: v for k, v in res.get("metrics", {}).items() if k in ("rules_line_pct", "rules_branch_pct", "contract_pass", "readme_words", "outputs", "junit")}
        lines.append(f"| {t['id']} | {kind} | {res.get('pass')} | {items} {json.dumps(mx)} |")
        print(lines[-1])
(S2 / "checks" / "VALIDATION.md").write_text("\n".join(lines) + "\n")
