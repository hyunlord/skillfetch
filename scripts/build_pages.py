"""Build the GitHub Pages site (.github/workflows/pages.yml): the e2e galleries and an index.

    uv run python scripts/build_pages.py [--out _site]

Copies evals/e2e/<stage>/gallery/*.html to <out>/<stage>/ and writes <out>/index.html. Nothing
else is deployed. The galleries are self-contained (screenshots as data URIs).
"""

from __future__ import annotations

import argparse
import html
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E2E = ROOT / "evals" / "e2e"
REPO = "https://github.com/hyunlord/skillfetch"
SECTIONS = {  # stage folder -> what it is, and its numbers.md section
    "stage10": ("Stage 10: final stack in real sessions", "§21"),
    "stageQ": ("Stage Q: qualitative round", "§23"),
    "stage13": ("Stage 13: popular skills installed, the router, or neither", "§26"),
    "stage14": ("Stage 14: six consecutive requests in one session", "§28"),
}


def galleries(e2e: Path = E2E) -> list[Path]:
    return sorted(e2e.glob("*/gallery/*.html"))


def index_html(items: list[tuple[str, str, int]]) -> str:
    """items: (stage, file name, bytes)."""
    rows = []
    for stage, name, size in items:
        title, section = SECTIONS.get(stage, (stage, ""))
        where = f"{REPO}/blob/main/docs/writeup/numbers.md" if section else REPO
        rows.append(
            f'<li><a href="{html.escape(stage)}/{html.escape(name)}">{html.escape(title)}</a>'
            f" <span>({html.escape(name)}, {size / 1e6:.1f} MB"
            + (f', numbers <a href="{where}">{section}</a>' if section else "")
            + ")</span></li>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>skillfetch galleries</title>
<style>
body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 46rem; margin: 2rem auto;
  padding: 0 1rem; color: #222; }}
li {{ margin: .5rem 0; }} span {{ color: #666; font-size: .9em; }}
</style>
</head>
<body>
<h1>skillfetch: experiment galleries</h1>
<p>Every output of the end-to-end experiments side by side, as the blind judges saw them.
Code, data and the write-up: <a href="{REPO}">{REPO.removeprefix("https://")}</a>.</p>
<ul>
{chr(10).join(rows)}
</ul>
</body>
</html>
"""


def build(out: Path, e2e: Path = E2E) -> list[Path]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    items, written = [], []
    for g in galleries(e2e):
        stage = g.parent.parent.name
        dest = out / stage / g.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(g, dest)
        items.append((stage, g.name, g.stat().st_size))
        written.append(dest)
    (out / "index.html").write_text(index_html(items))
    written.append(out / "index.html")
    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", type=Path, default=ROOT / "_site")
    args = p.parse_args(argv)
    for path in build(args.out):
        print(path.relative_to(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
