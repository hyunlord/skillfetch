#!/usr/bin/env python3
"""Stage 12 judge material (DESIGN §7): final replies with skill/router traces removed by the Stage 10 §4.6 rule, using
the sentence splitting, task-content audit and removal of stage11/scripts/redact_s11.py (process, trim) unchanged.
The same rule applies to every condition (A, R, O). Stage 12 settings:
  trace terms  "skill"/"스킬", "MCP", the skillfetch tool names, and every Northwind skill (all 24: full id,
               the name, its index title), matched case-insensitively as whole tokens
  task content files of the task repo at its start commit (path or basename) and names defined there
               (def/class in .py; function/const/type/interface/export in .ts/.tsx), generic words excluded
usage: redact_12.py   -> stage12-private/redacted/<cond>/<task>-<tag>.reply.md, audit.jsonl, stats.json (main runs m*)"""
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
E2E = S12.parent
PRIV = E2E / "stage12-private"
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
from redact_s11 import TOOLS, final_reply, process  # noqa: E402

TASKS = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "tasks.jsonl").open()}
DEF_PY = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_]\w*)", re.M)
DEF_TS = re.compile(r"\b(?:function|const|let|type|interface|class)\s+([A-Za-z_$][\w$]*)")
STOP = {"app", "main", "get", "new", "event", "data", "test", "index", "init", "run", "client", "config", "settings",
        "Layout", "props", "error", "page", "db", "api"}


def trace_patterns():
    terms = set(TOOLS) | {"skillfetch-router"}
    for line in (PRIV / "index-nw" / "skills.jsonl").open():
        r = json.loads(line)
        if r["id"].startswith("northwind/"):
            terms |= {r["id"], r["id"].split("/", 1)[1].split("@")[0], r.get("title") or "", r.get("name") or ""}
    alts = "|".join(re.escape(x) for x in sorted(terms, key=len, reverse=True) if x)
    return [re.compile(r"(?i)[\w./-]*skill[\w./-]*|스킬"), re.compile(r"(?i)\bmcp(?:\b|_)\w*"),
            re.compile(rf"(?i)(?<![\w-])(?:{alts})(?![\w-])")], sorted(t for t in terms if t)


def task_patterns():
    out = {}
    for repo, br in {(t["repo"], t["base_branch"]) for t in TASKS.values()}:
        g = E2E / "repos" / repo
        files = [f for f in subprocess.run(["git", "-C", str(g), "ls-tree", "-r", "--name-only", br], capture_output=True,
                                           text=True, check=True).stdout.split() if not f.startswith(".")]
        names = set()
        for f in files:
            if f.endswith((".py", ".ts", ".tsx")):
                src = subprocess.run(["git", "-C", str(g), "show", f"{br}:{f}"], capture_output=True, text=True).stdout
                names |= set((DEF_PY if f.endswith(".py") else DEF_TS).findall(src))
        words = {n for n in names if n not in STOP} | set(files) | {Path(f).name for f in files if Path(f).suffix}
        words = {w for w in words if len(w) > 2}
        alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        out[(repo, br)] = ([re.compile(rf"(?<![\w./-])(?:{alt})(?![\w-])")], sorted(words))
    return out


def main():
    tpats, terms = trace_patterns()
    cpats = task_patterns()
    per, audit = [], []
    for meta in sorted((PRIV / "runs").glob("*/*-m[0-9].meta.json")):
        m = json.loads(meta.read_text())
        t = TASKS[m["task"]]
        src = Path(str(meta).replace(".meta.json", ".reply.txt"))
        text = src.read_text() if src.exists() else final_reply(Path(str(meta).replace(".meta.json", ".jsonl")))
        red, recs = process(text, tpats, cpats[(t["repo"], t["base_branch"])][0])
        dst = PRIV / "redacted" / m["cond"] / f"{m['task']}-{m['tag']}.reply.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(red)
        audit += [{"task": m["task"], "cond": m["cond"], "tag": m["tag"], **x} for x in recs]
        per.append({"task": m["task"], "cond": m["cond"], "tag": m["tag"], "removed": sum(x["action"] == "remove" for x in recs),
                    "trimmed": sum(x["action"] == "trim" for x in recs), "chars_before": len(text), "chars_after": len(red)})
    stats = {}
    for c in sorted({p["cond"] for p in per}):
        g = [p for p in per if p["cond"] == c]
        ch = [p["chars_after"] for p in g]
        stats[c] = {"sessions": len(g), "removed_whole": sum(p["removed"] for p in g), "trimmed": sum(p["trimmed"] for p in g),
                    "sessions_touched": sum(p["removed"] + p["trimmed"] > 0 for p in g),
                    "chars_after": {"min": min(ch), "median": statistics.median(ch), "max": max(ch)}}
    (PRIV / "redacted" / "audit.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in audit))
    (PRIV / "redacted" / "stats.json").write_text(json.dumps({"trace_terms": terms, "by_condition": stats, "sessions": per},
                                                             indent=1, ensure_ascii=False))
    for k, v in stats.items():
        print(k, json.dumps(v, ensure_ascii=False))


if __name__ == "__main__":
    main()
