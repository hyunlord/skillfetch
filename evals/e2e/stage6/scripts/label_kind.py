#!/usr/bin/env python3
"""Step 1: kind label (domain / process / tooling) for the 1,489 tier A/B canonical skills of the catalog
(gen/catalog.md = stage3/gen/catalog.md). System prompt gen/sys-kind.txt = definitions + the whole catalog (cached);
user prompt = 50 skill cards (cards.card: id, title, full summary, tags) in a seeded order. Writes kind.jsonl
{id, kind} and kind-agreement.json: agreement of kind == process with the stage-3 oracle v3 process flag
(stage3/followup/oracle-v3.jsonl), per graded (task, skill) pair, per relevant pair, and per skill (majority flag)."""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S6, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

ids = [l.split(" | ")[0] for l in (S6 / "gen" / "catalog.md").read_text().splitlines()]
order = ids[:]
random.Random("kind-1489").shuffle(order)
chunks = [order[i: i + 50] for i in range(0, len(order), 50)]
res = run_all([(f"kind-{n + 1:02d}", S6 / "gen" / "sys-kind.txt", "SKILLS\n\n" + "\n".join(card(s) for s in c))
               for n, c in enumerate(chunks)], workers=6)
kind, problems = {}, []
for c, r in zip(chunks, res):
    assert not r["is_error"], r["name"]
    for x in parse_json_last(r["text"]):
        got, _ = resolve_ids([x["id"]], set(c))
        if got and x.get("kind") in ("domain", "process", "tooling"):
            kind[got[0]] = x["kind"]
    problems += [s for s in c if s not in kind]
if problems:  # missing ids: one more call with only those
    r = run_all([("kind-missing", S6 / "gen" / "sys-kind.txt", "SKILLS\n\n" + "\n".join(card(s) for s in problems))], workers=1)[0]
    for x in parse_json_last(r["text"]):
        got, _ = resolve_ids([x["id"]], set(problems))
        if got and x.get("kind") in ("domain", "process", "tooling"):
            kind[got[0]] = x["kind"]
assert set(kind) == set(ids), len(set(ids) - set(kind))
(S6 / "kind.jsonl").write_text("".join(json.dumps({"id": s, "kind": kind[s]}) + "\n" for s in ids))


def kappa(x, y):
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in set(x) | set(y))
    return round((po - pe) / (1 - pe), 3)


orc = [json.loads(l) for l in (S6.parent / "stage3" / "followup" / "oracle-v3.jsonl").open()]
pairs = [(kind[x["skill"]] == "process", x["process"], x["grade"]) for o in orc for x in o["pool"] if x["skill"] in kind]
per = {}
for o in orc:
    for x in o["pool"]:
        if x["skill"] in kind:
            per.setdefault(x["skill"], []).append(x["process"])
skill_maj = [(kind[s] == "process", sum(v) * 2 > len(v)) for s, v in per.items()]


def agree(rows):
    a, b = [r[0] for r in rows], [r[1] for r in rows]
    return {"n": len(rows), "agree": round(sum(x == y for x, y in zip(a, b)) / len(rows), 3), "kappa": kappa(a, b),
            "kind_process&flag": sum(x and y for x, y in zip(a, b)), "kind_process&no_flag": sum(x and not y for x, y in zip(a, b)),
            "kind_other&flag": sum((not x) and y for x, y in zip(a, b)), "kind_other&no_flag": sum((not x) and (not y) for x, y in zip(a, b))}


out = {"kinds": dict(Counter(kind.values())), "graded_pairs": agree(pairs), "relevant_pairs": agree([p for p in pairs if p[2] >= 2]),
       "skills_majority_flag": agree(skill_maj), "missing_first_pass": len(problems),
       "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2)}
(S6 / "kind-agreement.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
