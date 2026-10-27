"""Check the frozen hashes of the published e2e artifacts (evals/e2e/**/FROZEN*.sha256).

Each FROZEN file was written in the experiment workspace before a run, over the original bytes.
A published file passes when its sha256 matches, or, for a file changed before publishing, when
evals/e2e/sanitized.tsv gives the frozen hash as its original and the file still has the listed
published hash. A file that was edited in the workspace after it was frozen is reported as
superseded (a later FROZEN file of the stage lists its hash, e.g. stage 2's FROZEN.after-fix) or
as changed after freezing; publishing did not change those bytes. Files in the release asset
count once scripts/fetch_e2e_assets.sh has unpacked them; files that were not published are
listed as such.

    uv run python scripts/verify_e2e_frozen.py
    # exit 1 only if a published file differs from the bytes publishing recorded
"""

from __future__ import annotations

import hashlib
import sys
from collections import Counter
from pathlib import Path

E2E = Path(__file__).resolve().parents[1] / "evals" / "e2e"
# workspace folders published under another path
MOVED = {"../stage10-private/": "private/", "../stage11-private/": "private/"}
# FROZEN files from Stage 12 on list paths from the workspace root; where those folders went
ROOT_MOVED = {
    "stage12-private/": "stage12/private/",
    "stage12b/": "stage12/12b/",
    "stage12c/": "stage12/12c/",
    "stage13-private/": "stage13/private/",
    "stage14-private/": "stage14/private/",
    "stageRF/": "stageQ/refire/",
    "stageRF-private/": "stageQ/refire/private/",
}


def _rows(name: str) -> list[list[str]]:
    lines = (E2E / name).read_text().splitlines()
    return [x.split("\t") for x in lines if x and not x.startswith("#")][1:]


def main() -> int:
    sanitized = {r[0]: (r[1], r[2]) for r in _rows("sanitized.tsv")}
    assets = {r[0] for r in _rows("ASSETS.tsv")}
    totals: Counter[str] = Counter()
    bad, later = [], []
    listed: dict[str, set[str]] = {}  # stage -> every hash some FROZEN file of it lists
    for frozen in E2E.rglob("FROZEN*.sha256"):
        stage = frozen.relative_to(E2E).parts[0]
        listed.setdefault(stage, set()).update(
            x.split()[0] for x in frozen.read_text().splitlines() if x.strip()
        )
    for frozen in sorted(E2E.rglob("FROZEN*.sha256")):
        stage = frozen.relative_to(E2E).parts[0]
        for line in frozen.read_text().splitlines():
            if not line.strip():
                continue
            digest, rel = line.split(maxsplit=1)
            rel = rel.lstrip("*")
            for old, new in MOVED.items():
                rel = rel.replace(old, new) if rel.startswith(old) else rel
            from_root = next(
                (
                    new + rel.removeprefix(old)
                    for old, new in ROOT_MOVED.items()
                    if rel.startswith(old)
                ),
                rel,
            )
            candidates = [
                (frozen.parent / rel).resolve(),
                (E2E / stage / rel).resolve(),
                (E2E / from_root).resolve(),
            ]
            path = next((p for p in candidates if p.is_file()), None)
            key = next((str(p.relative_to(E2E)) for p in candidates if p.is_relative_to(E2E)), rel)
            if path is None:
                status = "in release asset, not unpacked" if key in assets else "not published"
            else:
                key = str(path.relative_to(E2E))
                now = hashlib.sha256(path.read_bytes()).hexdigest()
                original, published = sanitized.get(key, (None, None))
                if now == digest:
                    status = "ok"
                elif original == digest and published == now:
                    status = "ok (sanitized; original hash in sanitized.tsv)"
                elif published is not None and published != now:
                    status = "MISMATCH (differs from the published bytes)"
                    bad.append(f"{frozen.relative_to(E2E)}: {rel}")
                elif (original or now) in listed[stage]:
                    status = "superseded (a later FROZEN file lists the current hash)"
                else:
                    status = "changed in the workspace after freezing (not by publishing)"
                    later.append(f"{frozen.relative_to(E2E)}: {rel}")
            totals[status] += 1
    for status, n in sorted(totals.items()):
        print(f"{n:5}  {status}")
    for x in later:
        print("changed after freezing:", x)
    for b in bad:
        print("mismatch:", b, file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
