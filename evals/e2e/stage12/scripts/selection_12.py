#!/usr/bin/env python3
"""Stage 12 R selection analysis (added 2026-10-27 at the user's request, after the main run started; reads finished
runs only, changes nothing in the run). For each R session:
  required  = the task's required Northwind skills (tasks.jsonl, the answer set)
  found     = Northwind skills in any search_skills result of the session (each call returns the top 50 by default)
  loaded    = ids in `included` of the session's resolve_and_load / resolve_set results
and per required skill: loaded / found but not chosen / not in the search results / no search (router did not fire).
Each rule item has one skill (tasks.jsonl rule_items); a failed rule item is put in one class by its skill:
  no_search      the session made no search_skills call
  not_found      the skill was in no search result of the session      ("못 찾음")
  not_chosen     in a search result, not loaded                        ("안 고름")
  loaded_failed  loaded, and the rule item still failed                ("골랐는데 안 지킴")
Passed items get the same classes (for reference); undecidable items are counted apart.
usage: selection_12.py <tag-prefix> [...]   (e.g. p, m)  -> stage12-private/selection-<prefixes>.json"""
import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
PRIV = S12.parent / "stage12-private"
TASKS = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "tasks.jsonl").open()}
DISTRACT = {"nw-payments-errors", "nw-data-logging", "nw-legacy-migrations", "nw-mobile-strings",
            "nw-marketing-analytics", "nw-payments-ids", "nw-infra-runbooks", "nw-ml-experiments"}


def short(i):
    return i.split("/", 1)[1].split("@")[0] if i.startswith("northwind/") else None


def rule_items(task):
    ri = task["rule_items"]
    return ri if isinstance(ri, list) else ast.literal_eval(ri)


def calls(jsonl):
    """(name, input, result-json-or-None) for each skillfetch MCP call, in order."""
    uses, out = {}, []
    for line in Path(jsonl).open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        for c in (d.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if d.get("type") == "assistant" and c.get("type") == "tool_use" and "skillfetch" in (c.get("name") or ""):
                uses[c["id"]] = len(out)
                out.append([c["name"].split("__")[-1], c.get("input") or {}, None])
            elif d.get("type") == "user" and c.get("type") == "tool_result" and c.get("tool_use_id") in uses:
                cc = c.get("content")
                txt = cc if isinstance(cc, str) else "".join(x.get("text", "") for x in cc or [] if isinstance(x, dict))
                try:
                    out[uses[c["tool_use_id"]]][2] = json.loads(txt)
                except ValueError:
                    out[uses[c["tool_use_id"]]][2] = {"_raw": txt[:200]}
    return out


def session(meta_path):
    m = json.loads(meta_path.read_text())
    task = TASKS[m["task"]]
    cs = calls(str(meta_path).replace(".meta.json", ".jsonl"))
    searches = [c for c in cs if c[0] == "search_skills"]
    found, ranks = set(), {}
    for n, (_, _, res) in enumerate(searches):
        for r, x in enumerate((res or {}).get("results") or [], 1):
            s = short(x.get("id", ""))
            if s:
                found.add(s)
                ranks.setdefault(s, []).append((n + 1, r))
    loaded = set()
    for name, inp, res in cs:
        if name in ("resolve_and_load", "resolve_set") and isinstance(res, dict):
            loaded |= {short(i) for i in res.get("included") or [] if isinstance(i, str) and short(i)}
    req = list(task["required_skills"])

    def cls(s):
        if not searches:
            return "no_search"
        if s in loaded:
            return "loaded"
        return "not_chosen" if s in found else "not_found"

    req_cls = {s: cls(s) for s in req}
    chk = m.get("check") or {}
    items = []
    by_id = {i["id"]: i["pass"] for i in chk.get("rule_items") or []}
    for it in rule_items(task):
        p = by_id.get(it["id"])
        c = cls(it["skill"])
        items.append({"id": it["id"], "skill": it["skill"], "pass": p,
                      "class": "undecidable" if p is None else ("loaded_failed" if c == "loaded" and p is False else c)})
    return {"task": m["task"], "tag": m["tag"], "required": req, "loaded": sorted(loaded),
            "loaded_required": sorted(loaded & set(req)), "loaded_distractor": sorted(loaded & DISTRACT),
            "loaded_other_nw": sorted(loaded - set(req) - DISTRACT), "searches": len(searches),
            "required_class": req_cls, "required_ranks": {s: ranks.get(s) for s in req}, "rule_items": items}


def main():
    prefixes = sys.argv[1:] or ["m"]
    rows = [session(p) for p in sorted((PRIV / "runs" / "R").glob("*.meta.json"))
            if any(p.name.split("-")[-1].startswith(x) for x in prefixes)]
    req_c = Counter(c for r in rows for c in r["required_class"].values())
    fail_c = Counter(i["class"] for r in rows for i in r["rule_items"] if i["pass"] is False)
    pass_c = Counter(i["class"] for r in rows for i in r["rule_items"] if i["pass"] is True)
    per_item = defaultdict(Counter)
    for r in rows:
        for i in r["rule_items"]:
            per_item[i["id"]]["pass" if i["pass"] else ("undecidable" if i["pass"] is None else i["class"])] += 1
    summary = {"sessions": len(rows),
               "required_total": sum(len(r["required"]) for r in rows),
               "required_by_class": dict(req_c),
               "loaded_required_rate": round(req_c["loaded"] / max(1, sum(req_c.values())), 3),
               "failed_rule_items_by_class": dict(fail_c), "passed_rule_items_by_class": dict(pass_c),
               "per_rule_item": {k: dict(v) for k, v in sorted(per_item.items())},
               "distractor_loads": sum(len(r["loaded_distractor"]) for r in rows)}
    (PRIV / f"selection-{'-'.join(prefixes)}.json").write_text(
        json.dumps({"prefixes": prefixes, "summary": summary, "sessions": rows}, indent=1, ensure_ascii=False))
    for r in rows:
        print(f"{r['task']:3} {r['tag']:3} required {len(r['required'])} loaded-req {len(r['loaded_required'])}"
              f" | {r['required_class']} | distr {r['loaded_distractor']} other {r['loaded_other_nw']}")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
