#!/usr/bin/env python3
"""P0 pilot: isolation checks and cost per session, from stage4/runs/<env>/<task>-p0.*"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

S4 = Path(__file__).resolve().parents[1]
HOME = str(Path.home())


def events(path):
    for line in path.read_text().splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            pass


def summarize(jsonl: Path) -> dict:
    ev = list(events(jsonl))
    init = next((e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(ev) if e.get("type") == "result"), {})
    hooks = [e for e in ev if e.get("type") == "system" and str(e.get("subtype", "")).startswith("hook")]
    tools = []
    for e in ev:
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    name = c["name"]
                    if name == "Skill":
                        name += f"({c['input'].get('skill') or c['input'].get('command')})"
                    tools.append(name)
    sf = [t for t in tools if t.startswith("mcp__skillfetch__")]
    dbg = jsonl.with_suffix("").with_suffix("")  # strip .jsonl
    debug = Path(str(jsonl)[: -len(".jsonl")] + ".debug.log")
    dtext = debug.read_text(errors="replace") if debug.is_file() else ""
    memory = sorted(set(re.findall(r"(/[^\s\"']*CLAUDE\.md)", dtext)))
    return {
        "mcp_servers": [(s.get("name"), s.get("status")) for s in init.get("mcp_servers", [])],
        "plugins": [p.get("name") if isinstance(p, dict) else p for p in init.get("plugins", [])],
        "skills": init.get("skills", []),
        "agents": init.get("agents", []),
        "slash_commands_n": len(init.get("slash_commands", []) or []),
        "tools_n": len(init.get("tools", []) or []),
        "model": init.get("model"),
        "hook_events": Counter((h.get("subtype"), h.get("hook_event") or h.get("hook_event_name"), h.get("hook_name")) for h in hooks),
        "memory_files_in_debug": [m.replace(HOME, "~") for m in memory],
        "result": {k: result.get(k) for k in ("subtype", "num_turns", "total_cost_usd", "duration_ms")},
        "input_tokens": sum((result.get("usage") or {}).get(k, 0) or 0 for k in
                            ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
        "first_tool": tools[0] if tools else None,
        "tools": tools,
        "skillfetch_calls": sf,
    }


def main():
    for env in ("E1", "E2"):
        for jsonl in sorted((S4 / "runs" / env).glob("*-p0.jsonl")):
            s = summarize(jsonl)
            meta_p = Path(str(jsonl)[: -len(".jsonl")] + ".meta.json")
            meta = json.loads(meta_p.read_text()) if meta_p.is_file() else {}
            print(f"=== {env} {jsonl.name} prep {meta.get('prep_s')}s wall {meta.get('wall_s')}s exit {meta.get('exit_code')}")
            print(json.dumps({k: (dict((str(kk), v) for kk, v in s[k].items()) if isinstance(s[k], Counter) else s[k])
                              for k in s}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
