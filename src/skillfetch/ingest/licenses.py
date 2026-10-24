"""Per-skill license and redistribution (index-format.md §1.8)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from skillfetch.ingest.skillfile import read_text

LICENSE_FILES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt", "COPYING")
# Conservative on purpose: permissive licenses only. Copyleft, proprietary and unknown
# skills are indexed without their body and files.
REDISTRIBUTABLE = frozenset(
    {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "MPL-2.0",
        "CC-BY-4.0",
        "CC0-1.0",
        "Unlicense",
    }
)

# (pattern, SPDX id), first match wins; specific licenses before the generic "all rights
# reserved", which also appears in permissive copyright lines.
_TEXT_RULES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(p, re.I | re.S), spdx)
    for p, spdx in (
        (r"apache license.{0,80}version 2\.0", "Apache-2.0"),
        (r"gnu affero general public license", "AGPL-3.0"),
        (r"gnu lesser general public license", "LGPL-3.0"),
        (r"gnu general public license", "GPL-3.0"),
        (r"mozilla public license", "MPL-2.0"),
        (r"\bmit license\b|permission is hereby granted, free of charge", "MIT"),
        (r"redistribution and use in source and binary forms.*neither the name", "BSD-3-Clause"),
        (r"redistribution and use in source and binary forms", "BSD-2-Clause"),
        (
            r"\bisc license\b|permission to use, copy, modify, and/?or distribute this software",
            "ISC",
        ),
        (r"creative commons attribution 4\.0|\bcc[- ]by[- ]4\.0\b", "CC-BY-4.0"),
        (r"\bcc0\b|creative commons zero", "CC0-1.0"),
        (r"free and unencumbered software released into the public domain", "Unlicense"),
        (r"all rights reserved|\bproprietary\b", "proprietary"),
    )
)
_FIELD_IDS = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "isc": "ISC",
    "mpl-2.0": "MPL-2.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc0-1.0": "CC0-1.0",
    "unlicense": "Unlicense",
    "gpl-3.0": "GPL-3.0",
    "agpl-3.0": "AGPL-3.0",
}


@dataclass(frozen=True)
class SkillLicense:
    license: str  # SPDX id, "proprietary" or "unknown"
    redistributable: bool
    origin: str  # license file name, "frontmatter", "source" or "none"


def classify_text(text: str) -> str | None:
    head = text[:4000]
    return next((spdx for pattern, spdx in _TEXT_RULES if pattern.search(head)), None)


def classify_field(value: str) -> str | None:
    """Frontmatter `license:`. A pointer ("Complete terms in LICENSE.txt") returns None."""
    v = value.strip().rstrip(".").lower()
    if v in _FIELD_IDS:
        return _FIELD_IDS[v]
    if "proprietary" in v or "all rights reserved" in v:
        return "proprietary"
    return None


def _make(spdx: str, origin: str) -> SkillLicense:
    return SkillLicense(spdx, spdx in REDISTRIBUTABLE, origin)


def skill_license(skill_dir: Path, frontmatter: dict | None, source_license: str) -> SkillLicense:
    for name in LICENSE_FILES:
        path = skill_dir / name
        if path.is_file() and (spdx := classify_text(read_text(path))):
            return _make(spdx, name)
    value = (frontmatter or {}).get("license")
    if isinstance(value, str) and (spdx := classify_field(value)):
        return _make(spdx, "frontmatter")
    if source_license != "per-skill":
        return _make(source_license, "source")
    return SkillLicense("unknown", False, "none")


def root_license(snapshot: Path) -> str:
    """The license of a snapshot's root license file: an SPDX id, "unrecognised" when the
    file matches no rule, "none" without one. Recorded as repo_license; it never decides a
    skill's own `license` (per-skill sources do not inherit it)."""
    for name in LICENSE_FILES:
        path = snapshot / name
        if path.is_file() and not path.is_symlink():
            return classify_text(path.read_text(errors="replace")) or "unrecognised"
    return "none"
