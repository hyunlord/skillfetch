"""Two independent judges per sampled warning: is it worth a human look before installing,
or a false positive? Each call is an isolated `claude -p` (no tools, no MCP servers, project-
only settings, a neutral working folder), the knowledge-gap probe's setup (numbers.md §24).

    uv run python evals/scan-accuracy/precision/judge.py [--work DIR] [--only N] [--items FILE]

Reads <work>/items.jsonl (sample.py), caches each reply under <work>/raw/, and writes
verdicts.jsonl here: item_id, judge (1 or 2), verdict, kind (no skill text, no reasons).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = (
    "real risk",
    "needs a check",
    "documentation or example",
    "ordinary setup step",
    "pattern match only",
    "other",
)
SYSTEM = f"""You review warnings from a scanner that checks agent skills (SKILL.md folders that a
coding agent loads as instructions) before a user installs them. For one warning you get the
skill's description and what the scanner flagged, with the surrounding lines.

Decide whether this warning is worth a human reviewer's look before installing the skill:
- "worth_a_look": a careful reviewer would want to read it before installing (it could make the
  agent do something risky, depend on content that can change, or it is large or outdated enough
  to matter), even if it turns out fine.
- "false_positive": nothing here a reviewer needs to check; the scanner matched a harmless line.

Reply with only one JSON object:
{{"verdict": "worth_a_look" | "false_positive", "kind": one of {json.dumps(list(KINDS))}, "reason": "<one sentence>"}}"""

RULES = {
    "privilege.sudo": "a command run with sudo",
    "exfil.pipe-to-shell": "a downloaded script piped into a shell",
    "network.remote-instructions": "instructions fetched from a URL at use time",
    "scan.line-too-long": "a line over 2,000 characters that the scanner cannot read",
    "size": "the skill is large: SKILL.md over 8,000 tokens, more than 20 files, or over 1 MB",
    "scripts": "the skill bundles scripts the agent may run",
    "dated": "lines that state a year or a version, which may be out of date",
}


def prompt(it: dict) -> str:
    head = (
        f"Skill: {it['skill_id']}\nDescription: {it['description']}\n"
        f"Warning: {it['stratum']} ({RULES.get(it['stratum'], it['stratum'])})\n\n"
    )
    if "hits" in it:
        body = "\n\n".join(f"{h['file']} line {h['line_no']}:\n{h['context']}" for h in it["hits"])
    elif it["stratum"] == "size":
        body = (
            f"{'; '.join(it['warnings'])}\nSKILL.md ~{it['skill_md_tokens']} tokens, "
            f"{it['files']} files, {it['total_bytes']} bytes"
        )
    else:
        body = f"Scripts: {', '.join(it['scripts'])}\n\n" + "\n\n".join(
            f"--- {h['file']} (first lines)\n{h['head']}" for h in it["heads"]
        )
    return head + body


def _env() -> dict:
    e = dict(os.environ)
    for k in list(e):
        if k in ("CLAUDECODE", "VIRTUAL_ENV", "UV") or k.startswith("CLAUDE_CODE_"):
            e.pop(k)
    return e


def call(work: Path, iso: Path, sysfile: Path, it: dict, judge: int) -> dict:
    out = work / "raw" / f"{it['item_id']}-j{judge}.json"
    if out.exists():
        return json.loads(out.read_text())
    cmd = [
        "claude",
        "-p",
        prompt(it),
        "--system-prompt-file",
        str(sysfile),
        "--tools",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        str(iso / "mcp.json"),
        "--setting-sources",
        "project",
        "--output-format",
        "json",
        "--no-session-persistence",
    ]
    j: dict = {}
    for attempt in range(3):
        p = subprocess.run(
            cmd,
            cwd=iso,
            env=_env(),
            capture_output=True,
            text=True,
            timeout=600,
            stdin=subprocess.DEVNULL,
        )
        try:
            j = json.loads(p.stdout)
        except json.JSONDecodeError:
            j = {"is_error": True, "result": (p.stdout + p.stderr)[-300:]}
        if not j.get("is_error"):
            break
        time.sleep(10 * (attempt + 1))
    rec = {
        "item_id": it["item_id"],
        "judge": judge,
        "text": j.get("result") or "",
        "cost_usd": j.get("total_cost_usd"),
        "is_error": bool(j.get("is_error")),
        "model": next(iter((j.get("modelUsage") or {}).keys()), None),
    }
    if not rec["is_error"]:
        out.write_text(json.dumps(rec, ensure_ascii=False))
    return rec


def parse(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    try:
        d = json.loads(text[start : end + 1])
    except ValueError:
        return {"verdict": None, "kind": None}
    v = d.get("verdict") if d.get("verdict") in ("worth_a_look", "false_positive") else None
    k = d.get("kind") if d.get("kind") in KINDS else "other"
    return {"verdict": v, "kind": k}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--work", type=Path, default=Path("~/skillfetch-work/scan-accuracy").expanduser()
    )
    p.add_argument("--items", type=Path, default=None)
    p.add_argument("--only", type=int, default=None, help="first N calls (a pilot)")
    p.add_argument("--out", type=Path, default=HERE / "verdicts.jsonl")
    args = p.parse_args(argv)
    (args.work / "raw").mkdir(parents=True, exist_ok=True)
    iso = Path(tempfile.gettempdir()) / "scan-accuracy-iso"
    iso.mkdir(exist_ok=True)
    (iso / "mcp.json").write_text('{"mcpServers":{}}')
    sysfile = args.work / "system.txt"
    sysfile.write_text(SYSTEM)
    items = [json.loads(x) for x in (args.items or args.work / "items.jsonl").open()]
    jobs = [(it, j) for it in items for j in (1, 2)]
    if args.only:
        jobs = jobs[: args.only]
    with ThreadPoolExecutor(6) as ex:
        recs = list(ex.map(lambda job: call(args.work, iso, sysfile, *job), jobs))
    rows = [
        {"item_id": r["item_id"], "judge": r["judge"], **parse(r["text"])}
        for r in recs
        if not r["is_error"]
    ]
    if not args.only:
        args.out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(
        json.dumps(
            {
                "calls": len(recs),
                "errors": sum(r["is_error"] for r in recs),
                "cost": round(sum(r["cost_usd"] or 0 for r in recs), 3),
                "model": recs[0]["model"] if recs else None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
