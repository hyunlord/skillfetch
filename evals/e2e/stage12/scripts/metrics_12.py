#!/usr/bin/env python3
"""Stage 12 numbers from the runs (stage12/DESIGN.md §4, §5): per session and per condition, the rule-check pass rate
(passed rule items / decided rule items; undecidable items are left out of the denominator and counted apart), the
functional items, turns, API-price equivalent, and for R the router firing (Skill `skillfetch-router` or any skillfetch
MCP call) and the skills it loaded (resolve_and_load / resolve_set + load_skills inputs). Northwind skills loaded are
split into required for the task, other platform rules, and distractors (DESIGN §1.3).
usage: metrics_12.py <tag-prefix> [...]   e.g. metrics_12.py p   (pilot) / metrics_12.py m   (main)"""
import json
import sys
from collections import defaultdict
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
PRIV = S12.parent / "stage12-private"
DISTRACT = {"nw-payments-errors", "nw-data-logging", "nw-legacy-migrations", "nw-mobile-strings",
            "nw-marketing-analytics", "nw-payments-ids", "nw-infra-runbooks", "nw-ml-experiments"}
TASKS = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "tasks.jsonl").open()}


def tool_uses(jsonl):
    for line in Path(jsonl).open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        for c in d.get("message", {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                yield c.get("name") or "", c.get("input") or {}


def session(meta_path):
    m = json.loads(meta_path.read_text())
    jsonl = Path(str(meta_path).replace(".meta.json", ".jsonl"))
    chk = m.get("check") or {}
    fired, loaded, sf_calls = False, [], 0
    if jsonl.exists():
        for name, inp in tool_uses(jsonl):
            if name == "Skill" and "skillfetch-router" in json.dumps(inp):
                fired = True
            if name.startswith("mcp__skillfetch__"):
                fired, sf_calls = True, sf_calls + 1
                if name.endswith(("resolve_and_load", "resolve_set")):
                    loaded += [i for i in inp.get("auto_ids") or [] if isinstance(i, str)]
    nw = sorted({i.split("/")[1].split("@")[0] for i in loaded if i.startswith("northwind/")})
    req = set(TASKS[m["task"]]["required_skills"])
    return {"task": m["task"], "cond": m["cond"], "tag": m["tag"],
            "rule_pass": chk.get("rule_pass"), "rule_total": chk.get("rule_total"),
            "rule_undecidable": chk.get("rule_undecidable"), "func_pass": chk.get("func_pass"),
            "func_total": chk.get("func_total"), "check_error": chk.get("error"),
            "turns": m.get("num_turns") or m.get("turns"), "cost_usd": m.get("cost_usd"),
            "harness_fail": m.get("harness_fail"), "fired": fired, "skillfetch_calls": sf_calls,
            "loaded_required": sorted(set(nw) & req), "loaded_distractor": sorted(set(nw) & DISTRACT),
            "loaded_other_nw": sorted(set(nw) - req - DISTRACT), "loaded_non_nw": len(set(loaded)) - len(nw)}


def main():
    prefixes = sys.argv[1:] or ["p"]
    rows = [session(p) for p in sorted((PRIV / "runs").glob("*/*.meta.json"))
            if any(p.name.split("-")[-1].startswith(x) for x in prefixes)]
    by = defaultdict(lambda: defaultdict(float))
    for r in rows:
        b = by[r["cond"]]
        b["sessions"] += 1
        b["rule_pass"] += r["rule_pass"] or 0
        b["rule_decided"] += (r["rule_total"] or 0) - (r["rule_undecidable"] or 0)
        b["rule_undecidable"] += r["rule_undecidable"] or 0
        b["func_pass"] += r["func_pass"] or 0
        b["func_total"] += r["func_total"] or 0
        b["cost_usd"] += r["cost_usd"] or 0
        b["fired"] += r["fired"]
    summary = {c: {**{k: round(v, 3) for k, v in b.items()},
                   "rule_rate": round(b["rule_pass"] / b["rule_decided"], 3) if b["rule_decided"] else None}
               for c, b in sorted(by.items())}
    out = {"prefixes": prefixes, "sessions": rows, "by_cond": summary}
    (PRIV / f"metrics-{'-'.join(prefixes)}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for r in rows:
        print(f"{r['task']:3} {r['cond']} {r['tag']:3} rule {r['rule_pass']}/{r['rule_total']} (undec {r['rule_undecidable']})"
              f" func {r['func_pass']}/{r['func_total']} turns {r['turns']} ${r['cost_usd']} fired {r['fired']}"
              f" req {r['loaded_required']} distr {r['loaded_distractor']} other {r['loaded_other_nw']}"
              + (f" ERR {r['check_error']}" if r["check_error"] else ""))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
