#!/usr/bin/env python3
"""Stage Q judge material (DESIGN §0, §4): final replies with router traces removed by the Stage 10 §4.6 rule, as
stage11/scripts/redact_s11.py (same target terms, task-content audit and removal), applied to every Stage Q request
with a reply (all jobs, every condition alike). Trace terms: the tool names, "skill"/"스킬", "MCP", and every skill
loaded anywhere in this Stage Q run (id, name part, index title). Task-content audit: s10-t016 and s11-t266 as in Stage 11
(the other tasks have no task-content list, so a target sentence there is removed whole).
usage: redact_q.py <requests.jsonl>
  -> stageQ-private/redacted/<job>-<tag>[.pK].reply.md
  -> stageQ-private/redacted/audit.jsonl, stats.json"""
import json
import os
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
E2E = SQ.parent
PRIV = Path(os.environ.get("SQ_PRIV") or E2E / "stageQ-private")  # $SQ_PRIV: the Q1 extension
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
from redact_s11 import process, task_patterns, trace_patterns  # noqa: E402


def stem(r):
    s = f"{r['job'].replace(':', '-')}-{r['tag']}"
    return s + (f".p{r['k']}" if r["kind"] == "q2" else "")


def main():
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    loaded = sorted({i for r in rows for i in r.get("loaded") or []})
    tpats, terms = trace_patterns(loaded)
    cp = task_patterns()
    out_dir = PRIV / "redacted"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit, per = [], []
    for r in rows:
        src = PRIV / "runs" / f"{stem(r)}.reply.txt"
        if not src.exists():
            continue
        text = src.read_text()
        red, recs = process(text, tpats, cp.get(r["task"], ([], []))[0])
        (out_dir / f"{stem(r)}.reply.md").write_text(red)
        audit += [{"request": stem(r), **x} for x in recs]
        per.append({"request": stem(r), "removed": sum(x["action"] == "remove" for x in recs),
                    "trimmed": sum(x["action"] == "trim" for x in recs), "chars_before": len(text), "chars_after": len(red)})
    (out_dir / "audit.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in audit))
    (out_dir / "stats.json").write_text(json.dumps({"trace_terms": terms, "requests": per}, indent=1, ensure_ascii=False))
    print(f"{len(per)} replies, {sum(p['removed'] for p in per)} sentences removed, {sum(p['trimmed'] for p in per)} trimmed, "
          f"{sum(p['removed'] + p['trimmed'] > 0 for p in per)} replies touched")


if __name__ == "__main__":
    main()
