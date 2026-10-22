"""Runtime latency on a real index: server start, search_skills, resolve_set.

    uv run python scripts/bench_runtime.py [--index ~/.skillfetch/index] [--sizes 3,10,20,50]

resolve_set sets are what the router would pass: the top N search_skills results for each
of the queries below (related skills, so they share subjects). Each size is timed once per
query (median and range). Sizes up to the session's auto_ids limit go through
Session.resolve_set; larger sizes call the resolver directly with the same Skill objects
(the session would refuse them). Server start: a fresh process importing the MCP server and
loading the index.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

QUERIES = [
    "Add pytest unit tests for a FastAPI backend utility module",
    "Build a landing page in a Next.js TypeScript app with hero, features and pricing",
    "Refactor a React component into smaller hooks",
    "Write a README with setup and usage for a Python CLI",
    "Squash commits before merging a pull request",
]


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.2f} s"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, default=Path("~/.skillfetch/index").expanduser())
    ap.add_argument("--sizes", default="3,10,20,50")
    args = ap.parse_args()

    code = (
        "import time; t=time.perf_counter(); "
        "from skillfetch.index.loader import Index; from skillfetch.mcp.session import Session; "
        "from skillfetch.mcp.server import build_server; "
        f"build_server(Session(Index.load(__import__('pathlib').Path({str(args.index)!r})))); "
        "print(time.perf_counter()-t)"
    )
    start = float(
        subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout
    )

    from skillfetch.index.loader import Index
    from skillfetch.mcp import session as session_mod
    from skillfetch.mcp.session import Session
    from skillfetch.resolve import resolve_set
    from skillfetch.resolve.relation import DEFAULT_CAP

    s = Session(Index.load(args.index))
    search = []
    for q in QUERIES:
        t = time.perf_counter()
        s.search_skills(q)
        search.append(time.perf_counter() - t)

    limit = getattr(session_mod, "MAX_AUTO_IDS", None)
    cap = s.index.manifest.get("conflict_cap") or DEFAULT_CAP
    rows = {}
    for size in (int(x) for x in args.sizes.split(",")):
        times = []
        for q in QUERIES:
            ids = [r["id"] for r in s.search_skills(q, k=size)["results"]]
            t = time.perf_counter()
            if limit is None or size <= limit:
                s.resolve_set(ids)
            else:
                resolve_set([s.index.skill(i) for i in ids], [], s.index.verdicts(), cap)
            times.append(time.perf_counter() - t)
        rows[size] = times
    out = {
        "server_start_s": round(start, 3),
        "search_ms": [round(x * 1000, 1) for x in search],
        "resolve_s": {k: [round(x, 4) for x in v] for k, v in rows.items()},
    }
    print(json.dumps(out))
    print(
        f"server start {_ms(start)}; search {_ms(min(search))}–{_ms(max(search))}", file=sys.stderr
    )
    for size, times in rows.items():
        print(
            f"resolve_set {size}: median {_ms(statistics.median(times))}, "
            f"{_ms(min(times))}–{_ms(max(times))}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
