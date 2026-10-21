"""Per-skill license and provenance (index-format.md §1.1, §1.8)."""

import json

import pytest
from conftest import write_skill

from skillfetch.ingest.licenses import classify_field, classify_text, skill_license
from skillfetch.ingest.provenance import openskills_upstream, parse_third_party_doc

APACHE = "          Apache License\n          Version 2.0, January 2004\n"
MIT = "MIT License\n\nCopyright (c) 2025 X\n\nPermission is hereby granted, free of charge, to"
PROPRIETARY = (
    "© 2025 Anthropic, PBC. All rights reserved.\n\nLICENSE: Use of these materials is governed"
)


@pytest.mark.parametrize(
    "text, spdx",
    [
        (APACHE, "Apache-2.0"),
        (MIT, "MIT"),
        ("Permission is hereby granted, free of charge, to any person obtaining a copy", "MIT"),
        (
            "Redistribution and use in source and binary forms ... Neither the name of",
            "BSD-3-Clause",
        ),
        ("Redistribution and use in source and binary forms, with or without", "BSD-2-Clause"),
        ("Mozilla Public License Version 2.0", "MPL-2.0"),
        ("GNU GENERAL PUBLIC LICENSE\nVersion 3", "GPL-3.0"),
        ("GNU AFFERO GENERAL PUBLIC LICENSE", "AGPL-3.0"),
        ("This is free and unencumbered software released into the public domain.", "Unlicense"),
        (PROPRIETARY, "proprietary"),
        ("Some custom terms nobody recognizes.", None),
    ],
)
def test_classify_text(text, spdx):
    assert classify_text(text) == spdx


@pytest.mark.parametrize(
    "value, spdx",
    [
        ("MIT", "MIT"),
        ("Apache-2.0", "Apache-2.0"),
        ("apache 2.0", "Apache-2.0"),
        ("Proprietary. LICENSE.txt has complete terms", "proprietary"),
        ("Complete terms in LICENSE.txt", None),
    ],
)
def test_classify_frontmatter_field(value, spdx):
    assert classify_field(value) == spdx


def test_license_file_wins_over_frontmatter(tmp_path):
    fm = "---\nname: a\ndescription: d\nlicense: MIT\n---\n"
    d = write_skill(tmp_path, "a", frontmatter=fm, files={"LICENSE.txt": PROPRIETARY})
    lic = skill_license(d, {"license": "MIT"}, "per-skill")
    assert (lic.license, lic.redistributable, lic.origin) == ("proprietary", False, "LICENSE.txt")


def test_frontmatter_then_source_then_unknown(tmp_path):
    d = write_skill(tmp_path, "a")
    assert skill_license(d, {"license": "MIT"}, "per-skill").license == "MIT"
    assert skill_license(d, {}, "Apache-2.0").origin == "source"
    unknown = skill_license(d, {}, "per-skill")
    assert (unknown.license, unknown.redistributable, unknown.origin) == ("unknown", False, "none")


def test_copyleft_is_not_redistributable_in_v01(tmp_path):
    d = write_skill(tmp_path, "a", files={"LICENSE": "GNU GENERAL PUBLIC LICENSE\nVersion 3"})
    assert not skill_license(d, {}, "per-skill").redistributable


def test_openskills_upstream(tmp_path):
    meta = {
        "source": "https://github.com/ComposioHQ/awesome-claude-skills",
        "sourceType": "git",
        "repoUrl": "https://github.com/ComposioHQ/awesome-claude-skills",
        "subpath": "composio-skills\\\\-21risk-automation",
    }
    d = write_skill(tmp_path, "a", files={".openskills.json": json.dumps(meta)})
    up = openskills_upstream(d)
    assert up.repo == "https://github.com/ComposioHQ/awesome-claude-skills"
    assert up.path == "composio-skills/-21risk-automation"
    assert openskills_upstream(write_skill(tmp_path, "b")) is None


def test_broken_openskills_file_is_ignored(tmp_path):
    assert openskills_upstream(write_skill(tmp_path, "a", files={".openskills.json": "{"})) is None


def test_parse_third_party_doc():
    doc = (
        "# Third-Party Source Repos\n\nintro\n\n## GStack\n\n- Upstream: <https://github.com/garrytan/gstack>\n"
        "- Local source: `x`\n\n## GBrain\n\n- Upstream: <https://github.com/garrytan/gbrain>\n\n"
        "## Verification\n\n```\nskill-router\n```\n"
    )
    assert parse_third_party_doc(doc) == [
        {"name": "GStack", "url": "https://github.com/garrytan/gstack"},
        {"name": "GBrain", "url": "https://github.com/garrytan/gbrain"},
    ]
