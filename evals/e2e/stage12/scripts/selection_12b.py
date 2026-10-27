#!/usr/bin/env python3
"""Stage 12b selection analysis (stage12b/DESIGN.md §4; fixed before the 12b runs). Same classes and output as
selection_12.py, extended:
  Rp (R′)  loaded skills split into pinned (in a resolve_set/resolve_and_load `pinned_ids` input and in `included`) and
           auto (the rest of `included`); per required skill: pinned / loaded (auto) / not_chosen / not_found / no_search
  N        loaded = skills named in Skill tool calls (`input.skill`) OR read as files: a Read/Grep/Glob path under
           .claude/skills/<name>/, or a Bash command that mentions .claude/skills or SKILL.md, counting every Northwind
           skill name in that command (the pilot sessions ran `for s in nw-…; do cat .claude/skills/$s/SKILL.md; done`,
           no Skill tool call; definition widened 2026-10-27 before the main run). Reported apart: via_skill_tool,
           via_file_read. All 24 are listed by Claude Code, so per required skill: loaded / not_chosen
Failed rule items: not_found / not_chosen / loaded_failed (auto or N), pinned_failed (Rp, pinned and failed),
no_search. Distractor loads and non-required platform loads are counted per session.
usage: selection_12b.py <Rp|N|R> <tag-prefix>   -> stage12-private/selection12b-<cond>-<prefix>.json"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import selection_12 as s12

PRIV = s12.PRIV


NAMES = re.compile(r"(?<![\w-])(nw-[a-z0-9-]+)(?![\w-])")
NW24 = sorted(d.name for d in (PRIV / "northwind-skills").iterdir() if (d / "SKILL.md").exists())
# a loop over bare names (`for s in money config …; cat .claude/skills/nw-$s/SKILL.md`): fixed 2026-10-27 after the
# main run (N T1 m3 read 12 skills this way and was counted as 0); applies to every session alike
BARE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(n[3:]) for n in sorted(NW24, key=len, reverse=True)) + r")(?![\w-])")


def skill_reads(jsonl):
    """Northwind skill names read as files (Read/Grep/Glob path under .claude/skills/<name>/, or a Bash command that
    mentions .claude/skills or SKILL.md)."""
    out = set()
    for line in Path(jsonl).open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        for c in (d.get("message") or {}).get("content") or []:
            if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                continue
            inp = c.get("input") or {}
            if c.get("name") == "Bash":
                cmd = str(inp.get("command") or "")
                if ".claude/skills" in cmd or "SKILL.md" in cmd:
                    out |= set(NAMES.findall(cmd)) & set(NW24)
                    if re.search(r"nw-\$\{?\w+", cmd):
                        out |= {"nw-" + b for b in BARE.findall(cmd)}
            elif c.get("name") in ("Read", "Grep", "Glob"):
                path = str(inp.get("file_path") or inp.get("path") or inp.get("pattern") or "")
                m = re.search(r"\.claude/skills/(nw-[a-z0-9-]+)/", path)
                if m:
                    out.add(m.group(1))
    return out


def skill_calls(jsonl):
    out = []
    for line in Path(jsonl).open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        for c in (d.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                out.append(str((c.get("input") or {}).get("skill") or ""))
    return out


def nw_name(x):
    x = x.split(":")[-1]
    return s12.short(x) if x.startswith("northwind/") else (x if x.startswith("nw-") else None)


def session(cond, meta_path):
    m = json.loads(meta_path.read_text())
    task = s12.TASKS[m["task"]]
    jsonl = str(meta_path).replace(".meta.json", ".jsonl")
    req = list(task["required_skills"])
    if cond == "N":
        calls = skill_calls(jsonl)
        via_tool = {n for n in map(nw_name, calls) if n}
        via_read = skill_reads(jsonl)
        loaded, pinned, searches, found = via_tool | via_read, set(), None, None
    else:
        cs = s12.calls(jsonl)
        searches = [c for c in cs if c[0] == "search_skills"]
        found = {s12.short(x.get("id", "")) for _, _, res in searches for x in (res or {}).get("results") or []} - {None}
        loaded, pinned = set(), set()
        for name, inp, res in cs:
            if name in ("resolve_and_load", "resolve_set") and isinstance(res, dict):
                inc = {s12.short(i) for i in res.get("included") or [] if isinstance(i, str) and s12.short(i)}
                loaded |= inc
                pinned |= inc & {s12.short(i) for i in inp.get("pinned_ids") or [] if isinstance(i, str) and s12.short(i)}
        calls = None

    def cls(s):
        if cond == "N":
            return "loaded" if s in loaded else "not_chosen"
        if not searches and not pinned:
            return "no_search"
        if s in pinned:
            return "pinned"
        if s in loaded:
            return "loaded"
        return "not_chosen" if s in found else "not_found"

    by_id = {i["id"]: i["pass"] for i in (m.get("check") or {}).get("rule_items") or []}
    items = []
    for it in s12.rule_items(task):
        p, c = by_id.get(it["id"]), cls(it["skill"])
        k = ("undecidable" if p is None else "pinned_failed" if c == "pinned" and p is False
             else "loaded_failed" if c == "loaded" and p is False else c)
        items.append({"id": it["id"], "skill": it["skill"], "pass": p, "class": k})
    return {"task": m["task"], "tag": m["tag"], "required": req, "loaded": sorted(loaded), "pinned": sorted(pinned),
            "skill_calls": calls, "via_skill_tool": sorted(via_tool) if cond == "N" else None,
            "via_file_read": sorted(via_read) if cond == "N" else None, "searches": None if searches is None else len(searches),
            "required_class": {s: cls(s) for s in req}, "loaded_distractor": sorted(loaded & s12.DISTRACT),
            "loaded_other_nw": sorted(loaded - set(req) - s12.DISTRACT - pinned), "rule_items": items}


def main():
    cond, prefix = sys.argv[1], sys.argv[2]
    rows = [session(cond, p) for p in sorted((PRIV / "runs" / cond).glob("*.meta.json"))
            if p.name.split("-")[-1].startswith(prefix)]
    T = [r for r in rows if r["task"].startswith("T")]
    per_item = defaultdict(Counter)
    for r in rows:
        for i in r["rule_items"]:
            per_item[i["id"]]["pass" if i["pass"] else i["class"]] += 1
    summ = {"sessions": len(rows),
            "required_by_class_T": dict(Counter(c for r in T for c in r["required_class"].values())),
            "required_by_class_all": dict(Counter(c for r in rows for c in r["required_class"].values())),
            "failed_T_by_class": dict(Counter(i["class"] for r in T for i in r["rule_items"] if i["pass"] is False)),
            "passed_T_by_class": dict(Counter(i["class"] for r in T for i in r["rule_items"] if i["pass"] is True)),
            "distractor_loads": sum(len(r["loaded_distractor"]) for r in rows),
            "sessions_with_distractor": sum(bool(r["loaded_distractor"]) for r in rows),
            "other_platform_loads": sum(len(r["loaded_other_nw"]) for r in rows),
            "N_sessions_with_skill_tool": sum(bool(r["via_skill_tool"]) for r in rows) if cond == "N" else None,
            "N_sessions_with_file_read": sum(bool(r["via_file_read"]) for r in rows) if cond == "N" else None,
            "per_rule_item": {k: dict(v) for k, v in sorted(per_item.items())}}
    (PRIV / f"selection12b-{cond}-{prefix}.json").write_text(json.dumps({"summary": summ, "sessions": rows}, indent=1,
                                                                        ensure_ascii=False))
    print(json.dumps({k: v for k, v in summ.items() if k != "per_rule_item"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
