#!/usr/bin/env python3
"""Re-run the (fixed) s2-api check on every s2-api session's worktree after the queue: <name>.recheck/, and
meta["check"] := recheck (original kept as meta["check_original"]). See checks/VALIDATION.md."""
import json
import sys
from pathlib import Path

S2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import run_s2  # noqa: E402

for cond in ("A", "B", "C2"):
    for mp in sorted((S2 / "runs" / cond).glob("s2-api-r*.meta.json")):
        meta = json.loads(mp.read_text())
        out = Path(str(mp)[: -len(".meta.json")] + ".re")  # run_check writes <out>.check -> <name>.re.check
        res = run_s2.run_check(meta["task"], Path(meta["worktree"]), meta["base_commit"], out)
        Path(str(out) + ".check").rename(Path(str(mp)[: -len(".meta.json")] + ".recheck"))
        if "check_original" not in meta:
            meta["check_original"] = meta["check"]
        meta["check"] = res
        meta["rechecked"] = "api_contract.py lifespan fix"
        mp.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        print(cond, mp.name, meta["check_original"].get("pass"), "->", res.get("pass"), res["metrics"].get("contract_pass"))
