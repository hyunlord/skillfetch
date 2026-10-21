"""Where a skill came from (index-format.md §1.1).

Aggregated sources such as UASL keep an `.openskills.json` per installed skill (the
openskills installer's record: upstream repo and path). A source may also document its
third-party upstreams in a markdown file (`third_party_doc` in sources.yaml).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

OPENSKILLS_FILE = ".openskills.json"
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_UPSTREAM = re.compile(r"^\s*-\s*Upstream:\s*<?(https?://[^>\s]+)>?", re.I)


@dataclass(frozen=True)
class Upstream:
    repo: str
    path: str | None
    kind: str | None


def openskills_upstream(skill_dir: Path) -> Upstream | None:
    path = skill_dir / OPENSKILLS_FILE
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    repo = data.get("repoUrl") or data.get("source")
    if not isinstance(repo, str) or not repo:
        return None
    subpath = data.get("subpath")
    if isinstance(subpath, str):
        subpath = re.sub(r"[\\/]+", "/", subpath).strip("/")  # written on Windows
    return Upstream(repo=repo, path=subpath or None, kind=data.get("sourceType"))


def parse_third_party_doc(text: str) -> list[dict[str, str]]:
    """[{name, url}] for each `## Name` section that has an `- Upstream: <url>` line."""
    found, current = [], None
    for line in text.splitlines():
        if m := _HEADING.match(line):
            current = m.group(1)
        elif current and (m := _UPSTREAM.match(line)):
            found.append({"name": current, "url": m.group(1)})
            current = None
    return found
