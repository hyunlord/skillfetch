#!/usr/bin/env python3
"""Extract per-session facts from runs/<id>.jsonl (+ meta) into runs/_extract.json."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
SF = "mcp__skillfetch__"


def tool_result_text(content):
    if isinstance(content, str):
        return content
    out = []
    for c in content or []:
        if isinstance(c, dict):
            if c.get("type") == "text":
                out.append(c.get("text", ""))
            elif c.get("type") == "tool_reference":
                out.append(f"<tool_reference {c.get('tool_name')}>")
            else:
                out.append(json.dumps(c, ensure_ascii=False))
    return "\n".join(out)


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def load_events(path):
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def extract(task):
    tid = task["id"]
    path = RUNS / f"{tid}.jsonl"
    meta = json.loads((RUNS / f"{tid}.meta.json").read_text()) if (RUNS / f"{tid}.meta.json").exists() else {}
    events = load_events(path)
    calls = []          # ordered tool calls with results
    by_id = {}
    turns = []          # assistant messages (main thread only), in order
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    for e in events:
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            msg = e["message"]
            items = []
            for c in msg.get("content", []):
                if c["type"] == "tool_use":
                    call = {"id": c["id"], "name": c["name"], "input": c["input"], "result": None, "is_error": None}
                    calls.append(call)
                    by_id[c["id"]] = call
                    items.append({"tool_use": c["name"], "input": c["input"]})
                elif c["type"] == "text" and c["text"].strip():
                    items.append({"text": c["text"]})
            if items:
                # stream-json emits one event per content block of the same message id; merge them
                if turns and turns[-1]["msg_id"] == msg.get("id"):
                    turns[-1]["items"].extend(items)
                else:
                    turns.append({"msg_id": msg.get("id"), "items": items})
        elif e.get("type") == "user":
            content = e.get("message", {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in by_id:
                        by_id[c["tool_use_id"]]["result"] = tool_result_text(c.get("content"))
                        by_id[c["tool_use_id"]]["is_error"] = bool(c.get("is_error"))

    sf_calls = [c for c in calls if c["name"].startswith(SF)]
    def named(n):
        return [c for c in sf_calls if c["name"] == SF + n]
    searches, resolves, loads, profiles = named("search_skills"), named("resolve_set"), named("load_skills"), named("profile_repo")
    toolsearch = [c for c in calls if c["name"] == "ToolSearch"]
    skill_tool = [c for c in calls if c["name"] == "Skill"]
    router_reads = [c for c in calls if c["name"] == "Read" and "skillfetch-router" in json.dumps(c["input"])]

    loaded_ids, load_errors, load_tokens, load_chars = [], [], None, 0
    for c in loads:
        load_chars += len(c["result"] or "")
        j = parse_json(c["result"] or "")
        if isinstance(j, dict):
            for s in j.get("skills") or []:
                if isinstance(s, dict):
                    loaded_ids.append(s.get("id"))
                    load_tokens = (load_tokens or 0) + (s.get("token_estimate") or 0)
            load_errors.extend(j.get("errors") or [])

    usage = result.get("usage") or {}
    inp = sum(usage.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    model_usage = result.get("modelUsage") or {}

    chain = "none"
    if searches:
        chain = "search"
        if resolves:
            chain = "search+resolve"
            if loads:
                chain = "search+resolve+load"

    return {
        "id": tid, "repo": task["repo"], "kind": task["kind"], "lang": task["lang"], "prompt": task["prompt"],
        "init_model": init.get("model"),
        "init_skillfetch_status": next((m["status"] for m in init.get("mcp_servers", []) if m["name"] == "skillfetch"), None),
        "router_skill_listed": "skillfetch-router" in (init.get("skills") or []),
        "result_subtype": result.get("subtype"), "num_turns": result.get("num_turns"),
        "duration_ms": result.get("duration_ms"), "total_cost_usd": result.get("total_cost_usd"),
        "input_tokens_total": inp, "input_tokens_uncached": usage.get("input_tokens"),
        "cache_creation": usage.get("cache_creation_input_tokens"), "cache_read": usage.get("cache_read_input_tokens"),
        "output_tokens": usage.get("output_tokens"), "model_usage": model_usage,
        "permission_denials": result.get("permission_denials"),
        "toolsearch_calls": [{"input": c["input"], "result": (c["result"] or "")[:300]} for c in toolsearch],
        "skill_tool_calls": [{"input": c["input"], "result": (c["result"] or "")[:300], "is_error": c["is_error"]} for c in skill_tool],
        "router_skill_reads": len(router_reads),
        "profile_calls": [{"input": c["input"], "result": (c["result"] or "")[:500], "is_error": c["is_error"]} for c in profiles],
        "search_calls": [{"input": c["input"], "result": c["result"], "is_error": c["is_error"]} for c in searches],
        "resolve_calls": [{"input": c["input"], "result": c["result"], "is_error": c["is_error"]} for c in resolves],
        "load_calls": [{"input": c["input"], "result": c["result"], "is_error": c["is_error"]} for c in loads],
        "loaded_ids": loaded_ids, "load_errors": load_errors, "load_tokens_reported": load_tokens,
        "load_result_chars": load_chars,
        "chain": chain,
        "first3_turns": turns[:3],
        "all_tool_names": [c["name"] for c in calls],
        "subagent_events": sum(1 for e in events if e.get("parent_tool_use_id")),
        "final_text": result.get("result"),
        "meta": meta,
    }


def junit_summary(path, baseline_ids):
    if not path or not Path(path).exists():
        return None
    root = ET.parse(path).getroot()
    out = {"existing": {"pass": 0, "fail": 0, "skipped": 0, "missing": 0}, "new": {"pass": 0, "fail": 0, "skipped": 0}, "failed": []}
    seen = set()
    for tc in root.iter("testcase"):
        cls, name = tc.get("classname", ""), tc.get("name", "")
        file = "tests/" + "/".join(cls.split(".")[1:]) + ".py" if cls.startswith("tests.") else cls
        nodeid = f"{file}::{name}"
        failed = any(ch.tag in ("failure", "error") for ch in tc)
        skipped = any(ch.tag == "skipped" for ch in tc)
        bucket = "existing" if nodeid in baseline_ids else "new"
        if bucket == "existing":
            seen.add(nodeid)
        out[bucket]["fail" if failed else "skipped" if skipped else "pass"] += 1
        if failed:
            out["failed"].append(nodeid)
    out["existing"]["missing"] = len(baseline_ids - seen)
    return out


def main():
    cfg = yaml.safe_load((ROOT / "tasks.yaml").read_text())
    baseline = set((RUNS / "baseline_fastapi_tests.txt").read_text().split())
    rows = []
    for t in cfg["tasks"]:
        if not (RUNS / f"{t['id']}.jsonl").exists():
            continue
        r = extract(t)
        if t["repo"] == "fastapi":
            r["junit"] = junit_summary(r["meta"].get("tests", {}).get("junit"), baseline)
        rows.append(r)
    (RUNS / "_extract.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for r in rows:
        print(r["id"], r["chain"], r["num_turns"], r["result_subtype"], "loaded=", r["loaded_ids"],
              "q=", [c["input"].get("query") for c in r["search_calls"]])


if __name__ == "__main__":
    sys.exit(main())
