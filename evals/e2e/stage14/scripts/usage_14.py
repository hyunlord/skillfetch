#!/usr/bin/env python3
"""Stage 14 per-request records (stage14/DESIGN.md §4 items 3, 4(a)(b), 5, 6), from the session files only (no model calls).
For every request p<k> of every session under stage14-private/runs (<cond>-<order>-<tag>):
  task, area, position k, after_domain_change (DESIGN §2: the previous request is in another area; the API-test request
  right after the API request is not), turns, result subtype (error_max_turns = 40-turn limit), API-price equivalent,
  tokens (input + cache read + cache creation; output apart), context_start = the first assistant event's input + cache
  read + cache creation tokens.
  skills: P = the P skills used (stage13/scripts/usage_13.py p_session: Skill tool call or files read under
  .claude/skills/<name>/); R = skills the router loaded (usage_13.r_session: `included` of resolve results); all
  conditions: every Skill tool call name; R also: router via the Skill tool ("skill") or skillfetch MCP only ("mcp") or not.
  trace (a) names: skills applied/loaded in requests 1..k-1 of the same session (P skills used, R loaded, other Skill
  calls; not the router) whose name appears in request k's final reply or diff (new files included), case-insensitive,
  word-bounded; trace_names_not_reloaded = the same without skills that request k also used or loaded itself
  (added after the main run, 2026-10-27: a skill re-loaded by request k explains its own mention).
  trace (b) out_of_area: files changed by request k outside its area (web/, api/, media/, data/; for the README task:
  files that are not .md/.mdx/.txt).
Writes stage14-private/usage-14.json and prints a table.
usage: usage_14.py [tag-prefix]   (default: m = main runs; p = pilot)"""
import json
import re
import sys
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
E2E = S14.parent
PRIV = E2E / "stage14-private"
sys.path.insert(0, str(E2E / "stage13" / "scripts"))
import usage_13 as u13  # noqa: E402

AREA = {"landing": "web", "api": "api", "apitests": "api", "rust": "media", "docs": "(root)", "data": "data"}
P_NAMES = set(u13.P_NAMES)


def events(p):
    for line in Path(p).open(errors="replace"):
        try:
            yield json.loads(line)
        except ValueError:
            continue


def request_record(jsonl):
    first, res, skills, router = None, {}, [], None
    for d in events(jsonl):
        if d.get("type") == "assistant":
            if first is None:
                u = (d.get("message") or {}).get("usage") or {}
                first = sum(u.get(x) or 0 for x in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            for c in (d.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    if c.get("name") == "Skill":
                        s = (c.get("input") or {}).get("skill") or ""
                        skills.append(s)
                        if "skillfetch-router" in s:
                            router = "skill"
                    elif str(c.get("name", "")).startswith("mcp__skillfetch__") and router is None:
                        router = "mcp"
        elif d.get("type") == "result":
            res = d
    u = res.get("usage") or {}
    return {"turns": res.get("num_turns"), "result": res.get("subtype"), "cost": res.get("total_cost_usd"),
            "tokens_in": sum(u.get(x) or 0 for x in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
            "tokens_out": u.get("output_tokens"), "context_start": first, "skill_calls": skills, "router": router}


def out_of_area(task, diff):
    files = re.findall(r"^diff --git a/(.*?) b/", diff, re.M)
    a = AREA[task]
    if a == "(root)":
        return sorted(f for f in files if not f.lower().endswith((".md", ".mdx", ".txt")))
    return sorted(f for f in files if not f.startswith(a + "/"))


def main():
    pre = sys.argv[1] if len(sys.argv) > 1 else "m"
    rows = []
    for meta_f in sorted((PRIV / "runs").glob(f"*-*-{pre}*.meta.json")):
        meta = json.loads(meta_f.read_text())
        base = str(meta_f)[: -len(".meta.json")]
        prior, prev_area = set(), None
        for s in meta["steps"]:
            k, task = s["k"], s["task"]
            p = Path(f"{base}.p{k}.jsonl")
            r = request_record(p)
            if meta["cond"] == "P":
                pu = u13.p_session(p)
                used = sorted(n for n in pu["used"] if n in P_NAMES)
            elif meta["cond"] == "R":
                used = sorted(u13.r_session(p))
            else:
                used = []
            others = sorted({x for x in r["skill_calls"] if x and "skillfetch-router" not in x and x not in used})
            reply = Path(f"{base}.p{k}.reply.txt").read_text(errors="replace") if Path(f"{base}.p{k}.reply.txt").exists() else ""
            diff = Path(f"{base}.p{k}.diff").read_text(errors="replace") if Path(f"{base}.p{k}.diff").exists() else ""
            hay = (reply + "\n" + diff).lower()
            named = sorted(n for n in prior if re.search(r"(?<![\w-])" + re.escape(n.lower().split("/")[-1].split("@")[0]) + r"(?![\w-])", hay))
            area = AREA[task]
            chk = (meta.get("checks") or {}).get(task) or {}
            rows.append({"session": meta_f.name[: -len(".meta.json")], "cond": meta["cond"], "order": meta["order"], "tag": meta["tag"],
                         "k": k, "task": task, "area": area,
                         "after_domain_change": k > 1 and area != prev_area,
                         **{x: r[x] for x in ("turns", "result", "cost", "tokens_in", "tokens_out", "context_start", "skill_calls", "router")},
                         "skills": used, "other_skill_calls": others, "prior_skills": sorted(prior),
                         "trace_names": named, "trace_names_not_reloaded": sorted(set(named) - set(used) - set(others)),
                         "out_of_area": out_of_area(task, diff),
                         "check": chk.get("pass"), "undecidable": chk.get("undecidable"),
                         "mutants_killed": (chk.get("metrics") or {}).get("mutants_killed") if task == "apitests" else None})
            prior |= set(used) | set(others)
            prev_area = area
    (PRIV / f"usage-14{'' if pre == 'm' else '-' + pre}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for r in rows:
        print(f"{r['session']:<10} p{r['k']} {r['task']:<9} chk={str(r['check']):<5} t={r['turns']} {r['result'] or '':<16} "
              f"${(r['cost'] or 0):.2f} ctx={r['context_start']} skills={','.join(r['skills']) or '-'} other={','.join(r['other_skill_calls']) or '-'} "
              f"router={r['router']} trace={','.join(r['trace_names']) or '-'} ooa={len(r['out_of_area'])}")


if __name__ == "__main__":
    main()
