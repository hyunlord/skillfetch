#!/usr/bin/env python3
"""Re-run the frozen check, with .omc/ env noise stripped first, for sessions whose check ran before the
runner learned to strip it (meta.check has no `env_noise_removed`). Keeps the original result as
meta.check_original and the new one as meta.check (+ meta.rechecked_at)."""
import json
import sys
import time
from pathlib import Path

import yaml

S1 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S1 / "scripts"))
import run_stage1 as rs  # noqa: E402


def main():
    tasks = {t["id"]: t for t in yaml.safe_load((S1 / "tasks-stage1.yaml").read_text())["tasks"]}
    for meta_path in sorted((S1 / "runs").glob("*/*.meta.json")):
        meta = json.loads(meta_path.read_text())
        if "env_noise_removed" in meta["check"]:
            continue
        out = Path(str(meta_path)[: -len(".meta.json")])
        new = rs.run_check(tasks[meta["task"]["id"]], Path(meta["worktree"]), meta["base_commit"], out, recheck=True)
        meta["check_original"] = meta["check"]
        meta["check"] = new
        meta["rechecked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        print(meta_path.name, "original", meta["check_original"].get("pass"), "-> recheck", new.get("pass"), "noise", new["env_noise_removed"])


if __name__ == "__main__":
    main()
