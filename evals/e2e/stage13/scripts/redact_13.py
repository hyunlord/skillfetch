#!/usr/bin/env python3
"""Stage 13 judge material for bundle (4) (stage13/DESIGN.md §3): the final replies of A, P and R with skill/router traces
removed by the Stage 10 §4.6 rule, using stage11/scripts/redact_s11.py (process, trace_patterns, task_patterns)
unchanged. One rule for all three conditions. Trace terms: the skillfetch tool names, "skill"/"스킬", "MCP", every skill
R loaded in these sessions (id, name part, index title), and the 8 P skill names. Task-content audit: redact_s11's lists
(s10-t016, s10-t263, s10-t115, s10-t198, s11-t266).
usage: redact_13.py   -> stage13-private/redacted/<A|P|R>-<task>-<tag>.reply.md, audit.jsonl, stats.json"""
import json
import sys
from pathlib import Path

S13 = Path(__file__).resolve().parents[1]
E2E = S13.parent
PRIV = E2E / "stage13-private"
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
sys.path.insert(0, str(S13 / "scripts"))
from redact_s11 import process, task_patterns, trace_patterns  # noqa: E402
from build_blind_13 import P_NAMES, source  # noqa: E402
import usage_13  # noqa: E402

B4 = ("s10-t016", "s10-t263", "s10-t115", "s10-t198", "s11-t266")


def main():
    sess = [(t, c, f"m{k}") for t in B4 for c in ("A", "P", "R") for k in (1, 2, 3)]
    loaded = set()
    for t, c, g in sess:
        if c == "R":
            loaded |= {f"x/{n}@0" for n in usage_13.r_session(Path(str(source(t, c, g)) + ".jsonl"))}
    loaded |= {f"p/{n}@0" for n in P_NAMES}
    tpats, terms = trace_patterns(sorted(loaded))
    cp = task_patterns()
    out = PRIV / "redacted"
    out.mkdir(parents=True, exist_ok=True)
    audit, per = [], []
    for t, c, g in sess:
        src = Path(str(source(t, c, g)) + ".reply.txt")
        text = src.read_text()
        red, recs = process(text, tpats, cp[t][0])
        (out / f"{c}-{t}-{g}.reply.md").write_text(red)
        audit += [{"task": t, "cond": c, "tag": g, **x} for x in recs]
        per.append({"task": t, "cond": c, "tag": g, "removed": sum(x["action"] == "remove" for x in recs),
                    "trimmed": sum(x["action"] == "trim" for x in recs)})
    (out / "audit.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in audit))
    (out / "stats.json").write_text(json.dumps({"trace_terms": terms, "sessions": per}, indent=1, ensure_ascii=False))
    for c in ("A", "P", "R"):
        g = [p for p in per if p["cond"] == c]
        print(c, "removed", sum(p["removed"] for p in g), "trimmed", sum(p["trimmed"] for p in g),
              "touched", sum(p["removed"] + p["trimmed"] > 0 for p in g))


if __name__ == "__main__":
    main()
