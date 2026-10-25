#!/usr/bin/env python3
"""Step 1a: the 300 stratified cells (12 task types x 6 stacks x 5 phrasings = 360, at most one task per cell).
Design: 12 (type, stack) combos keep all 5 phrasings (one per type, two per stack); the other 60 drop one phrasing,
cycling so every phrasing is dropped 12 times. Result: 25 per type, 50 per stack, 60 per phrasing.
Also the 40 trivial (expect_none) slots and 20 direction pairs. Writes gen/cells.json."""
import json
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
TYPES = ["feature", "bugfix", "refactor", "tests", "docs", "ci_infra", "deploy", "data", "ml", "security_review",
         "performance", "ui_design"]
STACKS = ["python", "ts_react_next", "go", "rust", "java_kotlin", "mobile"]
PHRASINGS = ["terminal", "normal", "spec", "korean", "directive"]

keep_all = {(t, (i * 2 + i // 6) % 6) for i, t in enumerate(range(12))}  # one stack per type, two types per stack
cells, drop_i = [], 0
for t in range(12):
    for s in range(6):
        drop = None if (t, s) in keep_all else drop_i % 5
        if drop is not None:
            drop_i += 1
        for p in range(5):
            if p != drop:
                cells.append({"task_type": TYPES[t], "stack": STACKS[s], "phrasing": PHRASINGS[p]})
assert len(cells) == 300, len(cells)
for key, vals in (("task_type", TYPES), ("stack", STACKS), ("phrasing", PHRASINGS)):
    counts = {v: sum(c[key] == v for c in cells) for v in vals}
    print(key, counts)
trivial = [{"task_type": "trivial", "stack": STACKS[i % 6], "phrasing": PHRASINGS[i % 5], "kind": k}
           for i, k in enumerate(["one-line fix", "rename", "typo", "answer a question", "constant change",
                                  "import fix", "comment edit", "version bump"] * 5)]
DIRS = [("test-first (TDD)", "minimal diff"), ("security first", "performance first"), ("accessibility first", "visual polish first"),
        ("no new dependencies", "use a well-known library"), ("plan before coding", "just do it, small change"),
        ("backward compatible", "breaking change allowed")]
pairs = [{"pair_id": f"pair{n + 1:02d}", "task_type": TYPES[(n * 5) % 12], "stack": STACKS[n % 6], "directions": DIRS[n % 6]}
         for n in range(20)]
(S3 / "gen" / "cells.json").write_text(json.dumps({"cells": cells, "trivial": trivial, "pairs": pairs}, indent=1))
print(len(cells), len(trivial), len(pairs))
