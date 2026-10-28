"""Re-check the sampled warnings under the current scan rules, and list warnings the current
rules add that the sample did not have (README.md here).

    uv run python evals/scan-accuracy/precision/rescore.py [--work DIR]

Writes flagged-now.jsonl here (item_id, still flagged under the current rules) and the new
(skill, rule) warnings to <work>/items-new.jsonl (with lines, for judge.py --items) and
new.jsonl here (derived). An item is still flagged when the current rules flag at least one of
its judged lines (injection rules, dated) or the skill as a whole (size, risky scripts).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from sample import CONTEXT, _context  # noqa: F401  (same context lines as the sample)

from skillfetch.index.loader import DEFAULT_INDEX_DIR
from skillfetch.ingest.injection import scan_skill
from skillfetch.ingest.skill_checks import dated_lines, skill_size
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR

HERE = Path(__file__).resolve().parent
MAX_NEW_PER_RULE = 30


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--index", type=Path, default=DEFAULT_INDEX_DIR)
    p.add_argument("--snapshots", type=Path, default=DEFAULT_WORK_DIR)
    work = Path("~/skillfetch-work/scan-accuracy").expanduser()
    p.add_argument("--work", type=Path, default=work)
    args = p.parse_args(argv)
    items = [json.loads(x) for x in (args.work / "items.jsonl").open()]
    records = {}
    for line in (args.index / "skills.jsonl").open():
        r = json.loads(line)
        records[r["id"]] = r
    sampled = {(it["skill_id"], it["stratum"]) for it in items}
    folder = lambda r: args.snapshots / r["source_id"] / r["commit"] / r["path"]  # noqa: E731
    flagged = []
    for it in items:
        d = folder(records[it["skill_id"]])
        s = it["stratum"]
        if s == "size":
            now = bool(skill_size(d).warnings)
        elif s == "scripts":
            now = bool(scan_skill(d).risky_scripts)
        elif s == "dated":
            lines = {(x.file, x.line_no) for x in dated_lines(d)}
            now = any((h["file"], h["line_no"]) in lines for h in it["hits"])
        else:
            hits = {(h.file, h.line_no) for h in scan_skill(d).warnings if h.rule_id == s}
            now = any((h["file"], h["line_no"]) in hits for h in it["hits"])
        flagged.append({"item_id": it["item_id"], "stratum": s, "split": it["split"], "now": now})
    (HERE / "flagged-now.jsonl").write_text("".join(json.dumps(x) + "\n" for x in flagged))
    # warnings of the current rules that the sample does not hold (canonical skills)
    new: dict[str, list[dict]] = {}
    for r in records.values():
        if r.get("canonical_id", r["id"]) != r["id"]:
            continue
        d = folder(r)
        if not (d / "SKILL.md").is_file():
            continue
        res = scan_skill(d)
        by_rule: dict[str, list] = {}
        for h in res.failures + res.warnings:
            by_rule.setdefault(h.rule_id, []).append(h)
        for rule, hits in by_rule.items():
            if (r["id"], rule) in sampled:
                continue
            new.setdefault(rule, []).append(
                {
                    "skill_id": r["id"],
                    "description": r.get("description", "")[:300],
                    "stratum": rule,
                    "hits": [
                        {
                            "file": h.file,
                            "line_no": h.line_no,
                            "context": _context(d, h.file, h.line_no),
                        }
                        for h in hits[:5]
                    ],
                }
            )
    out = []
    for rule, group in sorted(new.items()):
        group.sort(key=lambda x: hashlib.sha256(x["skill_id"].encode()).hexdigest())
        for i, it in enumerate(group[:MAX_NEW_PER_RULE]):
            it["split"] = "dev" if i % 2 == 0 else "eval"
            it["item_id"] = hashlib.sha256(f"{rule}|{it['skill_id']}".encode()).hexdigest()[:12]
            out.append(it)
    full = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out)
    (args.work / "items-new.jsonl").write_text(full)
    rows = []
    for x in out:
        row = {k: x[k] for k in ("item_id", "stratum", "split", "skill_id")}
        row["locations"] = [f"{h['file']}:{h['line_no']}" for h in x["hits"]]
        rows.append(json.dumps(row) + "\n")
    (HERE / "new.jsonl").write_text("".join(rows))
    counts = {rule: len(g) for rule, g in sorted(new.items())}
    print(json.dumps({"new_warnings_by_rule": counts, "to_judge": len(out)}))
    still = {}
    for x in flagged:
        c = still.setdefault(x["stratum"], [0, 0])
        c[0] += x["now"]
        c[1] += 1
    print(json.dumps({"still_flagged": still}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
