#!/usr/bin/env python3
"""Stage Q per-request rows from stageQ-private/runs/<job>-<tag>[.pK].* -> stageQ-private/requests-<tags>.jsonl.

One row per request (Q2 has 4 per job, the others 1). Fields as stage11/scripts/extract_s11.py where they exist:
turns, tokens (input = input + cache read + cache creation; uncached = input + cache creation; cache read), output,
cost, wall, fired (any skillfetch call), first skillfetch turn, skillfetch calls by name, queries, auto_ids / pinned_ids,
loaded ids (load_skills results; resolve_and_load content headers among the asked ids), load errors (Q6), API calls
(distinct assistant message ids, router_cost.py's count), check pass and failed items, and for Q2 the canary facts:
  canary_read      a Read or Bash call on the canary path in this request (sessions read it with Read or `cat`)
  canary_pinned    the canary path / name was passed as pinned_ids (skillfetch) in this request
  F_hit / F_new / R / other   markers as run_queue_q.markers() (task 1 too: the premise check, DESIGN §2)
Visibility (Q6 b, on runs): reply mentions of loaded skill names or ids, and of the words "skill"/"스킬" (unredacted).
usage: extract_q.py <tag> [<tag> ...]"""
import json
import os
import re
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
PRIV = Path(os.environ.get("SQ_PRIV") or SQ.parent / "stageQ-private")  # $SQ_PRIV: the re-fire check
RUNS = PRIV / "runs"
SF = "mcp__skillfetch__"
TOKEN = "cnry-q7"


def events(f):
    out = []
    for line in Path(f).open(errors="replace"):
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def tool_text(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def payload(t):
    try:
        return json.loads(t)
    except ValueError:
        return None


def parse(f):
    ev = events(f)
    result = next((e for e in reversed(ev) if e.get("type") == "result"), {})
    calls, results, msg_ids, turn = [], {}, set(), 0
    for e in ev:
        if e.get("parent_tool_use_id"):
            continue
        if e.get("type") == "assistant":
            turn += 1
            msg_ids.add(e["message"].get("id"))
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    calls.append({"id": c["id"], "name": c["name"], "input": c.get("input") or {}, "turn": turn})
        elif e.get("type") == "user" and isinstance(e.get("message", {}).get("content"), list):
            for c in e["message"]["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    results[c.get("tool_use_id")] = tool_text(c.get("content"))
    return result, calls, results, len(msg_ids - {None})


def name_of(sid):
    return sid.split("/")[-1].split("@")[0]


def row(meta, step, f, base):
    result, calls, results, api_calls = parse(f)
    sf = [c for c in calls if c["name"].startswith(SF)]
    loaded, errors, queries, auto, pinned = [], [], [], [], []
    for c in sf:
        n = c["name"].removeprefix(SF)
        if n == "search_skills":
            queries += c["input"].get("queries") or ([c["input"]["query"]] if c["input"].get("query") else [])
        auto += c["input"].get("auto_ids") or []
        pinned += c["input"].get("pinned_ids") or []
        p = payload(results.get(c["id"], "")) or {}
        if n == "load_skills":
            loaded += [s["id"] for s in p.get("skills", []) if isinstance(s, dict) and "id" in s]
        elif n == "resolve_and_load":
            asked = set(c["input"].get("auto_ids") or []) | set(c["input"].get("pinned_ids") or [])
            heads = re.findall(r"^## \d+\. .*\(([^()\s]+)\)$", p.get("content") or "", re.M)
            loaded += [i for i in heads if i in asked]
        if n in ("load_skills", "resolve_and_load"):
            errors += [x.get("error", "")[:160] for x in p.get("errors") or [] if isinstance(x, dict)]
    canary = meta.get("canary")
    u = result.get("usage") or {}
    reply = Path(base + ".reply.txt").read_text() if Path(base + ".reply.txt").exists() else ""
    diff = Path(base + ".diff").read_text(errors="replace") if Path(base + ".diff").exists() else ""
    names = sorted({name_of(i) for i in loaded})
    r = {"job": meta["job"], "tag": meta["tag"], "kind": meta["kind"], "task": meta["task"], "mcp": meta["mcp"],
         "k": step.get("k", 1), "session_id": step.get("session_id"), "subtype": result.get("subtype"),
         "turns": result.get("num_turns"), "api_calls": api_calls,
         "input_tokens": sum(u.get(x, 0) or 0 for x in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
         "uncached_input": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0),
         "cache_read": u.get("cache_read_input_tokens") or 0, "output_tokens": u.get("output_tokens"),
         "cost_usd": result.get("total_cost_usd"), "wall_s": step.get("wall_s"), "timed_out": step.get("timed_out"),
         "harness_fail": step.get("harness_fail"), "no_result": step.get("no_result"),
         "fired": bool(sf), "router_skill": any(c["name"] == "Skill" and "skillfetch-router" in json.dumps(c["input"]) for c in calls),
         "first_sf_turn": sf[0]["turn"] if sf else None, "sf_calls": [c["name"].removeprefix(SF) for c in sf],
         "queries": queries, "auto_ids": auto, "pinned_ids": pinned, "loaded": list(dict.fromkeys(loaded)), "load_errors": errors,
         "load_attempts": sum(c["name"] in (SF + "load_skills", SF + "resolve_and_load") for c in sf),
         "new_files": step.get("new_files", []),
         "reply_mentions_loaded": [n for n in names if n in reply] + [i for i in dict.fromkeys(loaded) if i in reply],
         "reply_word_skill": len(re.findall(r"skill|스킬", reply, re.I)), "reply_chars": len(reply)}
    if canary:
        r["canary_read"] = any(c["name"] in ("Read", "Bash") and canary in json.dumps(c["input"]) for c in calls)
        r["canary_pinned"] = any(canary in json.dumps(c["input"]) or "canary" in json.dumps(c["input"].get("pinned_ids") or [])
                                 for c in sf)
        f_hit = f_new = 0
        for chunk in diff.split("diff --git ")[1:]:
            if "\nnew file mode" not in chunk.split("@@")[0]:
                continue
            nm = chunk.split("\n", 1)[0].split(" b/")[-1]
            if nm.endswith((".json", ".lock")):
                continue
            f_new += 1
            first = next((l[1:] for l in chunk.split("\n") if l.startswith("+") and not l.startswith("+++")), "")
            f_hit += TOKEN in first
        last = next((l.strip() for l in reversed(reply.splitlines()) if l.strip()), "")
        r.update({"F_hit": f_hit, "F_new": f_new, "R": last == TOKEN,
                  "other": diff.count(TOKEN) + reply.count(TOKEN) - f_hit - (last == TOKEN)})
    chk = meta.get("check") or {}
    r["check_pass"] = chk.get("pass") if chk else None
    r["check_failed"] = [i["name"] for i in chk.get("items", []) if i.get("pass") is False] if chk else []
    return r


def main():
    tags = set(sys.argv[1:])
    rows = []
    for m_path in sorted(RUNS.glob("*.meta.json")):
        meta = json.loads(m_path.read_text())
        if meta["tag"] not in tags:
            continue
        stem = str(m_path)[: -len(".meta.json")]
        for step in meta["steps"]:
            base = f"{stem}.p{step['k']}" if len(meta["steps"]) > 1 or meta["kind"] == "q2" else stem
            rows.append(row(meta, step, base + ".jsonl", base))
    out = PRIV / f"requests-{'-'.join(sorted(tags))}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(len(rows), "rows ->", out.name)


if __name__ == "__main__":
    main()
