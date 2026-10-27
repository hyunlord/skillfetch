#!/usr/bin/env python3
"""Stage 13 skill use (stage13/DESIGN.md §3). Per session:
  P   skills used = Skill tool calls (`input.skill`) and files read under .claude/skills/<name>/ (Read/Grep/Glob path, or a
      Bash command that mentions .claude/skills or SKILL.md: every P skill name in it, and bare-loop names `$s` as in
      stage12/scripts/selection_12b.py); reported apart (via_skill_tool, via_file_read)
  R   skills loaded = `included` of resolve_set / resolve_and_load results (Stage Q / Q1 extension / Stage 13 m3 runs)
Also the P init event's skill list (names Claude Code showed). Output: stage13-private/usage.json and a per-task table.
usage: usage_13.py [tag-prefix, default m]"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

S13 = Path(__file__).resolve().parents[1]
E2E = S13.parent
PRIV = E2E / "stage13-private"
P_NAMES = [m["name"] for m in json.loads((PRIV / "p-skills-manifest.json").read_text())]
TASKS = json.loads((PRIV / "tasks13.json").read_text())["tasks"]
NAME_RE = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, sorted(P_NAMES, key=len, reverse=True))) + r")(?![\w-])")


def events(jsonl):
    for line in Path(jsonl).open(errors="replace"):
        try:
            yield json.loads(line)
        except ValueError:
            continue


def p_session(jsonl):
    tool, read, init = set(), set(), []
    for d in events(jsonl):
        if d.get("type") == "system" and d.get("subtype") == "init":
            init = [str(s) for s in d.get("skills") or []]
        if d.get("type") != "assistant":
            continue
        for c in (d.get("message") or {}).get("content") or []:
            if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                continue
            inp = c.get("input") or {}
            name = c.get("name")
            if name == "Skill":
                s = str(inp.get("skill") or "").split(":")[-1]
                if s:
                    tool.add(s)
            elif name == "Bash":
                cmd = str(inp.get("command") or "")
                if ".claude/skills" in cmd or "SKILL.md" in cmd:
                    read |= set(NAME_RE.findall(cmd))
            elif name in ("Read", "Grep", "Glob"):
                path = str(inp.get("file_path") or inp.get("path") or inp.get("pattern") or "")
                m = re.search(r"\.claude/skills/([\w-]+)/", path)
                if m and m.group(1) in P_NAMES:
                    read.add(m.group(1))
    return {"via_skill_tool": sorted(tool), "via_file_read": sorted(read), "used": sorted(tool | read),
            "init_p_skills": sorted(s for s in init if s.split(":")[-1] in P_NAMES)}


def r_session(jsonl):
    uses, loaded = {}, set()
    for d in events(jsonl):
        for c in (d.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if d.get("type") == "assistant" and c.get("type") == "tool_use" and "skillfetch" in (c.get("name") or ""):
                uses[c["id"]] = c["name"].split("__")[-1]
            elif d.get("type") == "user" and c.get("type") == "tool_result" and uses.get(c.get("tool_use_id")) in ("resolve_set", "resolve_and_load"):
                cc = c.get("content")
                txt = cc if isinstance(cc, str) else "".join(x.get("text", "") for x in cc or [] if isinstance(x, dict))
                try:
                    loaded |= {i.split("/", 1)[-1].split("@")[0] for i in json.loads(txt).get("included") or []}
                except (ValueError, AttributeError):
                    pass
    return sorted(loaded)


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "m"
    out = {}
    for t in TASKS:
        ps = sorted((PRIV / "runs").glob(f"p-{t}-{prefix}[0-9].jsonl"))
        rs = sorted(f for d in ("stageQ-private", "stageQ1x-private") for f in (E2E / d / "runs").glob(f"q1-{t}-on-{prefix}[0-9].jsonl"))
        out[t] = {"P": {f.name: p_session(f) for f in ps}, "R": {f.name: r_session(f) for f in rs}}
    (PRIV / "usage.json").write_text(json.dumps(out, indent=1))
    for t, v in out.items():
        pc = Counter(s for x in v["P"].values() for s in x["used"])
        rc = Counter(s for x in v["R"].values() for s in x)
        print(f"{t:14} P[{len(v['P'])}] used: {dict(pc) or '-'} | R[{len(v['R'])}] loaded: {dict(rc) or '-'}")


if __name__ == "__main__":
    main()
