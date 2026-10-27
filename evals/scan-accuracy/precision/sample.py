"""Precision sample of the scan's warnings over the released index (README.md here).

    uv run python evals/scan-accuracy/precision/sample.py [--work ~/skillfetch-work/scan-accuracy]

Strata, canonical skills only, current scan rules:
- every (skill, rule) pair with an injection-scan warning (remote instructions included);
- 30 skills each with a size warning, bundled scripts, or a dated line (seed 30).
Each stratum is shuffled (seed 30) and split in half: dev (used to change rules) and eval.
Writes the full items (with the lines, for the judges) to <work>/items.jsonl and the derived
sample (no skill text) to sample.jsonl here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR
from skillfetch.ingest.injection import scan_skill
from skillfetch.ingest.skill_checks import dated_lines, skill_size
from skillfetch.ingest.skillfile import read_text
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR

HERE = Path(__file__).resolve().parent
PER_STRATUM = 30
SEED = 30
CONTEXT = 2  # lines before and after a hit
MAX_SCRIPT_LINES = 40


def _context(folder: Path, file: str, line_no: int) -> str:
    lines = read_text(folder / file).split("\n")
    lo, hi = max(1, line_no - CONTEXT), min(len(lines), line_no + CONTEXT)
    return "\n".join(
        f"{n:>5}{'>' if n == line_no else ' '} {lines[n - 1][:300]}" for n in range(lo, hi + 1)
    )


def items(index: Path, work: Path) -> list[dict]:
    records = [json.loads(x) for x in (index / "skills.jsonl").open()]
    canon = [r for r in records if r.get("canonical_id", r["id"]) == r["id"]]
    rng = random.Random(SEED)
    inj, size, scripts, dated = [], [], [], []
    for r in canon:
        folder = work / r["source_id"] / r["commit"] / r["path"]
        if not (folder / "SKILL.md").is_file():
            continue
        base = {"skill_id": r["id"], "description": r.get("description", "")[:300]}
        res = scan_skill(folder)
        by_rule: dict[str, list] = {}
        for h in res.warnings:
            by_rule.setdefault(h.rule_id, []).append(h)
        for rule, hits in sorted(by_rule.items()):
            inj.append(
                {
                    **base,
                    "stratum": rule,
                    "hits": [
                        {
                            "file": h.file,
                            "line_no": h.line_no,
                            "context": _context(folder, h.file, h.line_no),
                        }
                        for h in hits[:5]
                    ],
                }
            )
        sz = skill_size(folder)
        if sz.warnings:
            size.append(
                {
                    **base,
                    "stratum": "size",
                    "warnings": sz.warnings,
                    "files": sz.files,
                    "total_bytes": sz.total_bytes,
                    "skill_md_tokens": sz.skill_md_tokens,
                }
            )
        if res.scripts:
            heads = []
            for rel in res.scripts[:3]:
                text = read_text(folder / rel).split("\n")[:MAX_SCRIPT_LINES]
                heads.append({"file": rel, "head": "\n".join(x[:200] for x in text)})
            scripts.append(
                {**base, "stratum": "scripts", "scripts": res.scripts[:20], "heads": heads}
            )
        dl = dated_lines(folder)
        if dl:
            dated.append(
                {
                    **base,
                    "stratum": "dated",
                    "hits": [
                        {
                            "file": d.file,
                            "line_no": d.line_no,
                            "matches": d.matches,
                            "context": _context(folder, d.file, d.line_no),
                        }
                        for d in dl[:5]
                    ],
                }
            )
    out = list(inj)
    for group in (size, scripts, dated):
        out += rng.sample(group, min(PER_STRATUM, len(group)))
    # split each stratum in half after a seeded shuffle
    strata: dict[str, list] = {}
    for it in out:
        strata.setdefault(it["stratum"], []).append(it)
    final = []
    for name in sorted(strata):
        group = sorted(strata[name], key=lambda x: x["skill_id"])
        rng.shuffle(group)
        for i, it in enumerate(group):
            it["split"] = "dev" if i % 2 == 0 else "eval"
            it["item_id"] = hashlib.sha256(f"{name}|{it['skill_id']}".encode()).hexdigest()[:12]
            final.append(it)
    return final


def derived(it: dict) -> dict:
    row = {k: it[k] for k in ("item_id", "stratum", "split", "skill_id")}
    if "hits" in it:
        row["locations"] = [f"{h['file']}:{h['line_no']}" for h in it["hits"]]
    if it["stratum"] == "size":
        row.update({k: it[k] for k in ("warnings", "files", "total_bytes", "skill_md_tokens")})
    if it["stratum"] == "scripts":
        row["scripts"] = len(it["scripts"])
    return row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--index", type=Path, default=DEFAULT_INDEX_DIR)
    p.add_argument("--snapshots", type=Path, default=DEFAULT_WORK_DIR)
    p.add_argument(
        "--work", type=Path, default=Path("~/skillfetch-work/scan-accuracy").expanduser()
    )
    args = p.parse_args(argv)
    found = items(args.index, args.snapshots)
    args.work.mkdir(parents=True, exist_ok=True)
    (args.work / "items.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in found)
    )
    (HERE / "sample.jsonl").write_text("".join(json.dumps(derived(x)) + "\n" for x in found))
    counts: dict[str, list[int]] = {}
    for x in found:
        c = counts.setdefault(x["stratum"], [0, 0])
        c[x["split"] == "eval"] += 1
    print(json.dumps({k: {"dev": v[0], "eval": v[1]} for k, v in sorted(counts.items())}))
    print("items", len(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
