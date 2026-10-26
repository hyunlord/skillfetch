#!/usr/bin/env python3
"""Stage Q, Q4 blind rule-compliance package (DESIGN §4): stageQ/judge-package/q4-<pass>/.

Items: one per (request, loaded skill) for every Stage Q main-run request that loaded skills (Q1 on, Q2 S/C tasks 1–4,
Q5), the canary excluded (its two rules are counted mechanically, Q2 markers). Baseline: each Q1 on item is repeated on
the off run with the same task and tag (same rule bundle; the off session loaded nothing). Rules: stageQ-private/q4/
rules.json (pre-extracted) or rules-post.json (post-hoc, extracted before any output was read; marked "post").
Each item folder <code>/: TASK.md (the request, verbatim), RULES.md ("Rule bundle", 3 rules with kept / broken /
not-applicable criteria; no skill name), diff.patch (that request's diff, cleaned as Q1), reply.md (redacted reply).
Items are shuffled and split into parts of at most 20 (part-1/, part-2/, …) so each judge agent gets one part.
Key: stageQ-private/keys/q4-key-<pass>.jsonl {code, request, job, tag, k, task, skill, cond (on/off), rules_source}.
usage: build_q4.py <pass> <requests.jsonl>"""
import json
import os
import random
import re
import secrets
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
E2E = SQ.parent
PRIV = E2E / "stageQ-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
sys.path.insert(0, str(SQ / "scripts"))
from build_blind_s2 import clean_diff  # noqa: E402
from build_blind_q import AUDIT, WT, scrub  # noqa: E402
from redact_q import stem  # noqa: E402

PART = 20


def rules_md(rules):
    L = ["# Rule bundle", "", "Judge each rule against this request's diff and final reply only.", ""]
    for n, r in enumerate(rules, 1):
        L += [f"## Rule {n}", "", r["rule"], "", f"- kept: {r['kept']}", f"- broken: {r['broken']}",
              f"- not applicable: {r['not_applicable']}", ""]
    return "\n".join(L)


def prompt_of(r):
    """The request as sent (run_q.job_spec); the canary path is shown as <local skill path>."""
    import run_q
    ps = run_q.job_spec(r["job"])["prompts"]
    return ps[r["k"] - 1].replace("{CANARY_PATH}", "<local skill path>")


def main():
    pas, req_file = sys.argv[1], sys.argv[2]
    rows = [json.loads(l) for l in open(req_file) if l.strip()]
    rows = [r for r in rows if r["tag"].startswith("m")]
    pre = json.loads((PRIV / "q4" / "rules.json").read_text())["rules"]
    postf = PRIV / "q4" / "rules-post.json"
    post = json.loads(postf.read_text())["rules"] if postf.exists() else {}
    items, missing = [], set()
    for r in rows:
        for s in r["loaded"]:
            src = "pre" if s in pre else ("post" if s in post else None)
            if not src:
                missing.add(s)
                continue
            items.append((r, s, src, "on" if r["mcp"] != "off" else "off"))
            if r["kind"] == "q1":
                off = next(x for x in rows if x["job"] == r["job"].replace(":on", ":off") and x["tag"] == r["tag"])
                items.append((off, s, src, "off"))
    if missing:
        sys.exit(f"rules missing for {len(missing)} loaded skills (run q4_post.py first): {sorted(missing)}")
    root, keyf = SQ / "judge-package" / f"q4-{pas}", PRIV / "keys" / f"q4-key-{pas}.jsonl"
    assert not root.exists(), f"{root} already built"
    random.SystemRandom().shuffle(items)
    keys = []
    for n, (r, s, src, cond) in enumerate(items):
        code = secrets.token_hex(4)
        d = root / f"part-{n // PART + 1}" / code
        d.mkdir(parents=True)
        (d / "TASK.md").write_text("# Request (verbatim)\n\n" + prompt_of(r) + "\n")
        (d / "RULES.md").write_text(rules_md((pre if src == "pre" else post)[s]))
        diff, _ = scrub(clean_diff(PRIV / "runs" / f"{stem(r)}.diff"))
        (d / "diff.patch").write_text(diff)
        rp = PRIV / "redacted" / f"{stem(r)}.reply.md"
        (d / "reply.md").write_text(WT.sub("<worktree>", rp.read_text()) if rp.exists() else "")
        keys.append({"code": code, "part": n // PART + 1, "request": stem(r), "job": r["job"], "tag": r["tag"], "k": r["k"],
                     "task": r["task"], "skill": s, "cond": cond, "rules_source": src})
    keyf.parent.mkdir(parents=True, exist_ok=True)
    keyf.write_text("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: k["code"])))
    hits = [f"{p.relative_to(root)}: {m.group(0)}" for p in root.rglob("*.md") for m in AUDIT.finditer(p.read_text())
            if p.name != "RULES.md"]
    hits += [f"{p.relative_to(root)}: {m.group(0)}" for p in root.rglob("*.patch") for m in AUDIT.finditer(p.read_text())]
    ts = 1792656000
    for p in sorted(root.rglob("*"), reverse=True):
        os.utime(p, (ts, ts))
    print(f"q4-{pas}: {len(items)} items in {len(items) // PART + (len(items) % PART > 0)} parts "
          f"(on {sum(i[3] == 'on' for i in items)}, off baseline {sum(i[3] == 'off' for i in items)}), audit hits {len(hits)}")
    if hits:
        sys.exit("audit hits:\n" + "\n".join(hits[:40]))


if __name__ == "__main__":
    main()
