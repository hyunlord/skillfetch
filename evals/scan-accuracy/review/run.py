"""The semantic review's evaluation (docs/design/review.md §4, numbers.md §31).

    uv run python evals/scan-accuracy/review/run.py sample
    uv run python evals/scan-accuracy/review/run.py estimate --set index|gpt1|gpt2|gpt3
    uv run python evals/scan-accuracy/review/run.py run --set index|gpt1|gpt2|gpt3 --tag run1
    uv run python evals/scan-accuracy/review/run.py summary [--set gpt3]

`sample`: 60 skills from the released index (canonical, SKILL.md present), all of which passed
lint and the injection scan at build. 20 security or prompt-safety skills that quote attacks or
dangerous commands: a security word in the title or description (SECURITY) and an attack
marker in their text files (MARKERS), drawn with seed 31; 40 more drawn at random from the rest
(seed 31). Writes index-sample.jsonl here (ids and groups only).

`run`: the checklist applied by ClaudeReviewer (scan --review's isolated `claude -p`) to every
case once, with a cache of its own per set and tag, so a second tag is a fresh run. Writes
results-<set>-<tag>.jsonl here: case, expected (risky / harmless), flagged, categories and
file:line of each verified finding, unverified count, error, cost. The quoted lines and reasons
go to <work>/<set>-<tag>.jsonl only (index skills are third-party text).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR
from skillfetch.ingest.review import CATEGORIES, CHECKLIST_SHA, review_files
from skillfetch.ingest.review_claude import ClaudeReviewer
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("~/skillfetch-work/scan-review").expanduser()
SEED = 31
SECURITY = re.compile(
    r"\b(?:security|secure|injection|vulnerab\w*|owasp|pentest\w*|penetration|attack\w*|"
    r"exploit\w*|malware|red[- ]team\w*|threat\w*|guardrails?|jailbreak\w*|hardening|cve)\b",
    re.I,
)
MARKERS = re.compile(
    r"rm -rf|ignore (?:all )?previous|prompt injection|exfiltrat|reverse shell|verify=False|"
    r"--no-verify|chmod 777|curl [^\n]*\| *(?:ba)?sh|base64 -d|/etc/passwd|\.ssh/|api[_ ]?key",
    re.I,
)
SETS = {
    "gpt1": ROOT / "evals/scan-accuracy/independent/set",
    "gpt2": ROOT / "evals/scan-accuracy/independent-2/set",
    # §33: written by GPT knowing that a model reads each skill against this checklist
    "gpt3": ROOT / "evals/scan-accuracy/independent-3/set",
}
FROZEN = {
    "gpt1": ROOT / "evals/scan-accuracy/independent/FROZEN.sha256",
    "gpt2": ROOT / "evals/scan-accuracy/independent-2/FROZEN.sha256",
    "gpt3": ROOT / "evals/scan-accuracy/independent-3/FROZEN.sha256",
}
SET_DIRS = {"gpt2": "independent-2", "gpt3": "independent-3"}
LABELS = {"위험": "risky", "무해": "harmless", "risky": "risky", "harmless": "harmless"}


def _folder(r: dict) -> Path:
    return DEFAULT_WORK_DIR / r["source_id"] / r["commit"] / r["path"]


def sample() -> list[dict]:
    records = [json.loads(x) for x in (DEFAULT_INDEX_DIR / "skills.jsonl").open()]
    canon = [
        r
        for r in records
        if r.get("canonical_id", r["id"]) == r["id"] and (_folder(r) / "SKILL.md").is_file()
    ]
    canon.sort(key=lambda r: r["id"])
    security = []
    for r in canon:
        if not SECURITY.search(f"{r.get('title', '')} {r.get('description', '')}"):
            continue
        files, _ = review_files(_folder(r))
        if any(MARKERS.search(text) for _, text in files):
            security.append(r)
    rng = random.Random(SEED)
    picked = rng.sample(security, 20)
    taken = {r["id"] for r in security}
    rest = rng.sample([r for r in canon if r["id"] not in taken], 40)
    rows = [{"case": r["id"], "group": "security", "expected": "harmless"} for r in picked]
    rows += [{"case": r["id"], "group": "random", "expected": "harmless"} for r in rest]
    (HERE / "index-sample.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    print(json.dumps({"security_pool": len(security), "canonical": len(canon), "sampled": 60}))
    return rows


def cases(name: str) -> list[tuple[str, str, Path]]:
    """(case, expected, folder) for a set."""
    if name == "index":
        by_id = {}
        for line in (DEFAULT_INDEX_DIR / "skills.jsonl").open():
            r = json.loads(line)
            by_id[r["id"]] = r
        rows = [json.loads(x) for x in (HERE / "index-sample.jsonl").open()]
        return [(x["case"], x["expected"], _folder(by_id[x["case"]])) for x in rows]
    root = SETS[name]
    want = FROZEN[name].read_text().split()[0]
    if hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest() != want:
        raise SystemExit(f"{name}: SHA256SUMS differs from {FROZEN[name]}")
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{name}: {rel} differs from SHA256SUMS")
    out = []
    for line in (root / "cases.jsonl").open():
        c = json.loads(line)
        folder = root / Path(c["path"]).parent
        out.append((folder.name, LABELS[c["label"]], folder))
    return out


def estimate(name: str) -> dict:
    chars = [sum(len(t) for _, t in review_files(folder)[0]) for _, _, folder in cases(name)]
    return {"set": name, "calls": len(chars), "chars": sum(chars), "max_chars": max(chars)}


def run(name: str, tag: str, jobs: int) -> dict:
    reviewer = ClaudeReviewer(cache=WORK / f"cache-{name}-{tag}")
    todo = cases(name)

    def one(item):
        case, expected, folder = item
        return case, expected, reviewer(folder)

    with ThreadPoolExecutor(jobs) as pool:
        done = list(pool.map(one, todo))
    rows, full = [], []
    for case, expected, r in done:
        rows.append(
            {
                "case": case,
                "expected": expected,
                "flagged": bool(r.findings),
                "categories": sorted({f.category for f in r.findings}),
                "locations": [f"{f.file}:{f.line}" for f in r.findings],
                "unverified": r.unverified,
                "not_reviewed": len(r.not_reviewed),
                "error": r.error,
                "cost_usd": r.cost_usd,
                "by": r.by,
            }
        )
        full.append({"case": case, **r.model_dump(mode="json")})
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"{name}-{tag}.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in full)
    )
    (HERE / f"results-{name}-{tag}.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows)
    )
    risky = [x for x in rows if x["expected"] == "risky"]
    harmless = [x for x in rows if x["expected"] == "harmless"]
    out = {
        "set": name,
        "tag": tag,
        "checklist": CHECKLIST_SHA[:12],
        "risky_flagged": sum(x["flagged"] for x in risky),
        "risky": len(risky),
        "harmless_flagged": sum(x["flagged"] for x in harmless),
        "harmless": len(harmless),
        "errors": sum(x["error"] is not None for x in rows),
        "cost_usd": round(sum(x["cost_usd"] or 0 for x in rows), 3),
    }
    print(json.dumps(out))
    return out


def _load(path: Path) -> dict[str, dict]:
    return {x["case"]: x for x in map(json.loads, path.open())}


def _pair(rows: list[dict], key: str = "flagged") -> str:
    expected = [x.get("expected", x.get("expect")) for x in rows]  # scan_accuracy.py: expect
    risky = [x for x, e in zip(rows, expected, strict=True) if e in ("risky", "catch")]
    harmless = [x for x, e in zip(rows, expected, strict=True) if e in ("harmless", "pass")]
    return (
        f"{sum(x[key] for x in risky)}/{len(risky)} · {sum(x[key] for x in harmless)}/"
        f"{len(harmless)}"
    )


def set_summary(name: str, label: str) -> list[str]:
    """Tables for one independent set: rules v8 by advice and warning, the two review runs,
    per category (categories.yaml: `risky: {category: [case numbers]}`, and the harmless cases
    either by `harmless_quotes: {case: risky case}` or by `harmless: {category: [numbers]}`),
    and how far the two runs agree."""
    import yaml

    ind = ROOT / "evals/scan-accuracy" / SET_DIRS[name]
    rules = {
        k: json.loads((ind / f"{k}-v8.json").read_text())["cases"] for k in ("advice", "results")
    }
    runs = {tag: _load(HERE / f"results-{name}-{tag}.jsonl") for tag in ("run1", "run2")}
    cats = yaml.safe_load((ind / "categories.yaml").read_text())
    cat_of = {f"case-{n:03d}": c for c, ns in cats["risky"].items() for n in ns}
    for h, r in (cats.get("harmless_quotes") or {}).items():
        cat_of[f"case-{h:03d}"] = cat_of[f"case-{r:03d}"]
    for c, ns in (cats.get("harmless") or {}).items():
        cat_of.update({f"case-{n:03d}": c for n in ns})
    nr = sum(x["expected"] == "risky" for x in runs["run1"].values())
    nh = len(runs["run1"]) - nr
    of = f"of {nr} each" if nr == nh else f"of {nr} and {nh}"
    out = [
        f"| {label} (risky caught · harmless flagged, {of}) | result |",
        "|---|---:|",
        f"| rules v8, by advice (CAUTION or above) | {_pair(rules['advice'], 'caught')} |",
        f"| rules v8, by warning (fail or warn) | {_pair(rules['results'], 'caught')} |",
    ]
    for tag, rows in runs.items():
        errors = sum(x["error"] is not None for x in rows.values())
        note = f" ({errors} not reviewed: error)" if errors else ""
        out.append(f"| review, {tag} | {_pair(list(rows.values()))}{note} |")
    out += [
        "",
        "| category | risky | rules v8 | review run1 | review run2 | harmless | flagged (rules · "
        "review run1 · run2) |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    rule_rows = {x["case"]: x for x in rules["advice"]}
    for cat in dict.fromkeys([*cats["risky"], *(cats.get("harmless") or {})]):
        cs = [c for c in sorted(cat_of) if cat_of[c] == cat]
        rk = [c for c in cs if runs["run1"][c]["expected"] == "risky"]
        hm = [c for c in cs if runs["run1"][c]["expected"] == "harmless"]
        cell = lambda rows, key, ids: sum(rows[c][key] for c in ids)  # noqa: E731
        out.append(
            f"| {cat} | {len(rk)} | {cell(rule_rows, 'caught', rk)} | "
            f"{cell(runs['run1'], 'flagged', rk)} | {cell(runs['run2'], 'flagged', rk)} | "
            f"{len(hm)} | {cell(rule_rows, 'caught', hm)} · {cell(runs['run1'], 'flagged', hm)} · "
            f"{cell(runs['run2'], 'flagged', hm)} |"
        )
    r1, r2 = runs["run1"], runs["run2"]
    both = [c for c in r1 if r1[c]["expected"] == "risky" and r2[c]["error"] is None]
    lines = [
        "",
        f"- **Same verdict in both runs:** {sum(r1[c]['flagged'] == r2[c]['flagged'] for c in r1)}"
        f" of {len(r1)} cases.",
        f"- **Same set of categories** on the {len(both)} risky cases reviewed in both runs: "
        f"{sum(r1[c]['categories'] == r2[c]['categories'] for c in both)}; at least one "
        f"category in common: {sum(bool(set(r1[c]['categories']) & set(r2[c]['categories'])) for c in both)}.",  # noqa: E501
    ]
    for tag, rows in runs.items():
        if not set(cats["risky"]) <= set(CATEGORIES):
            break  # the families are not checklist categories (set 3: evasion methods)
        risky = [c for c in rows if rows[c]["expected"] == "risky" and rows[c]["flagged"]]
        hit = sum(cat_of[c] in rows[c]["categories"] for c in risky)
        lines.append(
            f"- **{tag}: the assigned category among the review's categories:** {hit} of "
            f"{len(risky)} flagged risky cases."
        )
    for tag, rows in runs.items():
        cost = sum(x["cost_usd"] or 0 for x in rows.values())
        lines.append(f"- **Cost, {tag}:** ${cost:.2f} for {len(rows)} calls.")
    return out + lines


def summary(name: str = "gpt2") -> str:
    """Markdown for numbers.md §31 (set 2, set 1, the index sample) or §33 (`gpt3`)."""
    if name != "gpt2":
        return "\n".join(set_summary(name, "evasion set"))
    out = set_summary("gpt2", "set 2")
    r1, r2 = (_load(HERE / f"results-gpt2-{t}.jsonl") for t in ("run1", "run2"))
    gpt1 = _load(HERE / "results-gpt1-run1.jsonl")
    index = _load(HERE / "results-index-run1.jsonl")
    groups = {x["case"]: x["group"] for x in map(json.loads, (HERE / "index-sample.jsonl").open())}
    sec = [c for c in index if groups[c] == "security"]
    rnd = [c for c in index if groups[c] == "random"]
    out += [
        "",
        f"- **Independent set 1** (§30; seen before the checklist was written, reference only): "
        f"review {_pair(list(gpt1.values()))}, "
        f"${sum(x['cost_usd'] or 0 for x in gpt1.values()):.2f} for {len(gpt1)} calls.",
        f"- **Released index, 60 skills** (all passed lint and the injection scan at build): "
        f"flagged {sum(index[c]['flagged'] for c in sec)} of {len(sec)} security skills that quote "
        f"attacks and {sum(index[c]['flagged'] for c in rnd)} of {len(rnd)} drawn at random; "
        f"{sum(index[c]['not_reviewed'] > 0 for c in index)} skill only partly read (over 60,000 "
        f"characters); ${sum(x['cost_usd'] or 0 for x in index.values()):.2f} for {len(index)} "
        "calls.",
        f"- **Quotes not found in the files** (dropped): "
        f"{sum(x['unverified'] for d in (r1, r2, gpt1, index) for x in d.values())} in all runs.",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sample")
    sm = sub.add_parser("summary")
    sm.add_argument("--set", default="gpt2", choices=["gpt2", "gpt3"])
    e = sub.add_parser("estimate")
    e.add_argument("--set", required=True, choices=["index", "gpt1", "gpt2", "gpt3"])
    r = sub.add_parser("run")
    r.add_argument("--set", required=True, choices=["index", "gpt1", "gpt2", "gpt3"])
    r.add_argument("--tag", required=True)
    r.add_argument("--jobs", type=int, default=4)
    args = p.parse_args(argv)
    if args.cmd == "sample":
        sample()
    elif args.cmd == "summary":
        print(summary(args.set))
    elif args.cmd == "estimate":
        print(json.dumps(estimate(args.set)))
    else:
        run(args.set, args.tag, args.jobs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
