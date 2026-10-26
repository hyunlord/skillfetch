#!/usr/bin/env python3
"""Stage 11 bundle (4) judge material (DESIGN §6): final replies with router traces removed by the Stage 10 §4.6 rule
(stage10/scripts/redact_replies.py), unchanged except: runs are stage11-private/runs/<cond>/ (E1), the trace terms use
the skills loaded anywhere in this Stage 11 run, and the task-content audit also covers s11-t266 (repo s11-t266 at
s11-a, its row in stage11/rubric-b4-add.md). The same rule applies to every condition (A, R0, R1).

A sentence is a TARGET when it contains any of:
  - "skill" (any case, any word containing it: skills, skillfetch, SKILL.md) or "스킬"
  - "MCP" (any case, as a word or before "_", e.g. mcp__…)
  - a tool name: search_skills, resolve_set, load_skills, resolve_and_load, profile_repo
  - any skill loaded anywhere in this Stage 11 run (all bundles, all conditions): its full id, the name part of the id
    (between "/" and "@"), and its index title, matched case-insensitively as whole tokens (hyphens kept literally)
Audit (before removal): a target sentence has TASK CONTENT when it contains, case-sensitively as a whole token,
  - a file of the task repo at its start commit (s10-a; s11-a for s11-t266) (path or basename), or a fn/struct/enum/trait/type/const/func/class/protocol name
    defined there (generic words in STOP excluded), or a backticked name from the task's rubric row
  - for t115 also the unsound-flag terms of the check (unsound, not sound, …n't sound, undefined behaviour, out of bounds, UB)
Removal (no marker): a target sentence without task content is removed whole; in one with task content only the
matched trace spans (with an enclosing pair of backticks/parentheses when the span fills it) are removed and the rest
is kept as is. A line left with only a list/heading marker is dropped.
Sentences: each line is split after ". ", "! ", "? " when the next character starts a new sentence; a leading list,
heading or quote marker is kept; a line inside a code fence is one sentence.

usage: redact_replies.py <sessions.jsonl> [<sessions.jsonl> ...]
  -> stage11-private/redacted/<cond>/<task>-<tag>.reply.md   (bundle (4) sessions)
  -> stage11-private/redacted/audit.jsonl   one row per target sentence: session, sentence, task_content, matched, action
  -> stage11-private/redacted/stats.json    per condition: removed whole, trimmed, sessions touched, chars after"""
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
E2E = S11.parent
S10 = E2E / "stage10"
PRIV = E2E / "stage11-private"
TOOLS = ("search_skills", "resolve_set", "load_skills", "resolve_and_load", "profile_repo")
MARKER = re.compile(r"^(\s*(?:[-*+]|\d+[.)]|#{1,6}|>)\s+)?(.*)$")
SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`*\[(\"'가-힣])")
DEFN = re.compile(r"\b(?:fn|struct|enum|trait|type|const|func|class|protocol)\s+([A-Za-z_][A-Za-z0-9_]*)")
STOP = {"new", "run", "main", "start", "join", "leave", "handle", "len", "last", "fill", "bytes", "frames", "average",
        "errors", "helpers", "depth", "attr", "u8", "u16", "u32", "is_empty", "checksum", "broadcast", "empty"}
FLAG_T115 = r"(?i:unsound|not sound|(?:is|are|was|were)n['’]?t sound|undefined behaviou?r|out[- ]of[- ]bounds)|\bUB\b"


def final_reply(jsonl):  # sessions run before run_s10 saved <out>.reply.txt (pilot)
    r = ""
    for line in jsonl.open():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "result":
            r = d.get("result") or ""
    return r


def titles():
    t = {}
    for idx in ("release", "staging-4"):
        for line in (S10 / "index" / idx / "skills.jsonl").open():
            r = json.loads(line)
            t[r["id"]] = r.get("title") or r.get("name")
    return t


def trace_patterns(loaded_ids):
    tt = titles()
    terms = set(TOOLS)
    for i in loaded_ids:
        terms.add(i)
        terms.add(i.split("/", 1)[-1].split("@", 1)[0])
        if tt.get(i):
            terms.add(tt[i])
    alts = "|".join(re.escape(x) for x in sorted(terms, key=len, reverse=True) if x)
    return [re.compile(r"(?i)[\w./-]*skill[\w./-]*|스킬"), re.compile(r"(?i)\bmcp(?:\b|_)\w*"),
            re.compile(rf"(?i)(?<![\w-])(?:{alts})(?![\w-])")], sorted(terms)


def task_patterns():
    rubric = {}
    for rf in (S10 / "rubric-b4.md", S11 / "rubric-b4-add.md"):
        for line in rf.read_text().splitlines():
            m = re.match(r"\|\s*(s1[01]-t\d+)\s*\|", line)
            if m:
                rubric[m.group(1)] = {x.strip("&") for x in re.findall(r"`([^`]+)`", line)}
    out = {}
    for tid, base in (("s10-t016", "s10-a"), ("s10-t263", "s10-a"), ("s10-t115", "s10-a"), ("s10-t198", "s10-a"), ("s11-t266", "s11-a")):
        repo = E2E / "repos" / tid
        files = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", base], capture_output=True,
                               text=True, check=True).stdout.split()
        names = set()
        for f in files:
            if f.endswith((".rs", ".swift")):
                src = subprocess.run(["git", "-C", str(repo), "show", f"{base}:{f}"], capture_output=True, text=True).stdout
                names |= set(DEFN.findall(src))
        words = {n for n in names if n not in STOP} | {f for f in files if not f.startswith(".")} \
            | {Path(f).name for f in files if not f.startswith(".") and Path(f).suffix} | rubric.get(tid, set())
        words = {w for w in words if len(w) > 2}
        alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        pats = [re.compile(rf"(?<![\w./-])(?:{alt})(?![\w-])")]
        if tid == "s10-t115":
            pats.append(re.compile(FLAG_T115))
        out[tid] = (pats, sorted(words))
    return out


def trim(sentence, tpats):
    s = sentence
    for p in tpats:
        s = p.sub(lambda m: "\0", s)
    s = re.sub(r"`\0`|\(\0\)|\0", "", s)
    return re.sub(r"  +", " ", s).strip()


def process(text, tpats, cpats):
    out, recs, fence = [], [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if fence:
            lead, parts = "", [line]
        else:
            lead, body = MARKER.match(line).groups()
            parts = SPLIT.split(body)
        kept, n0 = [], len(recs)
        for s in parts:
            hit = [m.group(0) for p in tpats for m in p.finditer(s)]
            if not hit:
                kept.append(s)
                continue
            content = sorted({m.group(0) for p in cpats for m in p.finditer(s)})
            if content:
                new = trim(s, tpats)
                kept.append(new)
                recs.append({"sentence": s, "task_content": True, "content_terms": content, "trace": hit, "action": "trim", "after": new})
            else:
                recs.append({"sentence": s, "task_content": False, "content_terms": [], "trace": hit, "action": "remove"})
        if len(recs) == n0:  # nothing removed on this line
            out.append(line)
            continue
        rest = " ".join(x for x in kept if x)
        if rest:  # a line left with only its marker is dropped
            out.append((lead or "") + rest)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n", recs


def main():
    rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
    loaded = sorted({i for r in rows for i in r.get("loaded") or []})
    tpats, terms = trace_patterns(loaded)
    cpats = task_patterns()
    per, audit = [], []
    for r in rows:
        if r["bundle"] != 4 or r.get("harness_fail"):
            continue
        src = PRIV / "runs" / r["cond"] / f"{r['task']}-{r['tag']}.reply.txt"
        text = src.read_text() if src.exists() else final_reply(src.with_name(src.name.replace(".reply.txt", ".jsonl")))
        red, recs = process(text, tpats, cpats[r["task"]][0])
        dst = PRIV / "redacted" / r["cond"] / f"{r['task']}-{r['tag']}.reply.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(red)
        for x in recs:
            audit.append({"task": r["task"], "env": r["env"], "cond": r["cond"], "tag": r["tag"], **x})
        per.append({"task": r["task"], "env": r["env"], "cond": r["cond"], "tag": r["tag"],
                    "removed": sum(x["action"] == "remove" for x in recs), "trimmed": sum(x["action"] == "trim" for x in recs),
                    "chars_before": len(text), "chars_after": len(red)})
    stats = {}
    for key in sorted({(p["env"], p["cond"], p["tag"][0]) for p in per}):
        g = [p for p in per if (p["env"], p["cond"], p["tag"][0]) == key]
        ch = [p["chars_after"] for p in g]
        stats[f"{key[0]} {key[1]} {'main' if key[2] == 'm' else 'pilot'}"] = {
            "sessions": len(g), "removed_whole": sum(p["removed"] for p in g), "trimmed": sum(p["trimmed"] for p in g),
            "sessions_touched": sum(p["removed"] + p["trimmed"] > 0 for p in g),
            "chars_after": {"min": min(ch), "median": statistics.median(ch), "mean": round(statistics.mean(ch)), "max": max(ch)}}
    (PRIV / "redacted").mkdir(parents=True, exist_ok=True)
    (PRIV / "redacted" / "audit.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in audit))
    (PRIV / "redacted" / "stats.json").write_text(json.dumps({"trace_terms": terms, "task_terms": {k: v[1] for k, v in cpats.items()},
                                                              "by_condition": stats, "sessions": per}, indent=1, ensure_ascii=False))
    for k, v in stats.items():
        print(k, json.dumps(v, ensure_ascii=False))


if __name__ == "__main__":
    main()
