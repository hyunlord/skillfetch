#!/usr/bin/env python3
"""Step 1c: generated.json (+ rewrites.json) -> tasks.jsonl; title-token leak check against every index title.
A token is a lowercase run [a-z0-9] joined by - _ . +; a task leaks when one of its tokens equals a skill title."""
import json
import re
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
TOK = re.compile(r"[a-z0-9]+(?:[-_.+][a-z0-9]+)*")
titles = {(json.loads(l).get("title") or json.loads(l)["name"]).lower() for l in (Path.home() / ".skillfetch/index/skills.jsonl").open()}


def leaks(text):
    toks = set(TOK.findall(text.lower()))
    # also the parts of a joined token ("auth-service" -> auth, service)
    toks |= {p for t in toks for p in re.split(r"[-_.+]", t)}
    return sorted(t for t in toks if t in titles)


def build():
    g = json.loads((S3 / "gen" / "generated.json").read_text())
    rw = json.loads((S3 / "gen" / "rewrites.json").read_text()) if (S3 / "gen" / "rewrites.json").exists() else {}
    tasks = []
    for name, b in g.items():
        if name == "gen-pairs":
            continue
        for it, m in zip(sorted(b["items"], key=lambda x: x["i"]), b["meta"]):
            trivial = name == "gen-trivial"
            tasks.append({"task_type": m["task_type"], "stack": m["stack"], "phrasing": m["phrasing"], "text": it["text"],
                          "pair_id": None, "expect_none": trivial, **({"trivial_kind": m["kind"]} if trivial else {})})
    for it, m in zip(sorted(g["gen-pairs"]["items"], key=lambda x: x["i"]), g["gen-pairs"]["meta"]):
        for side, direction in zip("ab", m["directions"]):
            tasks.append({"task_type": m["task_type"], "stack": m["stack"], "phrasing": "directive", "text": it[side],
                          "pair_id": m["pair_id"], "pair_side": side, "direction": direction, "expect_none": False})
    for n, t in enumerate(tasks, 1):
        t["id"] = f"t{n:03d}"
        if t["id"] in rw:
            t["text"], t["rewritten"] = rw[t["id"]], True
        t["title_leaks"] = leaks(t["text"])
    return tasks


if __name__ == "__main__":
    tasks = build()
    bad = [t for t in tasks if t["title_leaks"]]
    print(len(tasks), "tasks;", len(bad), "with title tokens")
    from collections import Counter
    print(Counter(w for t in bad for w in t["title_leaks"]).most_common(40))
    (S3 / "gen" / "tasks-draft.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks))
