"""Section headings and "don't" lists (constraints.md §2 post-processing)."""

import json

import pytest
from conftest import FakeClient, write_skill

from skillfetch.ingest.backends import AnthropicBackend
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.sections import apply_sections, negative_section, section_headings
from skillfetch.resolve.models import Constraint

DOC = """\
# Validation
Validate early.
### ✅ Do
- Read error messages completely
### ❌ Don't
- Ignore error messages
- Don't skip validation
```
# a comment in a code block, not a heading
```
**Never:**

- Deploy on Fridays

Back under the Don't heading.
"""


def lines():
    return DOC.split("\n")


def test_each_line_gets_its_heading():
    got = dict(zip(lines(), section_headings(lines()), strict=True))
    assert got["Validate early."] == "Validation"
    assert got["- Read error messages completely"] == "✅ Do"
    assert got["- Ignore error messages"] == "❌ Don't"
    assert got["# a comment in a code block, not a heading"] == "❌ Don't"
    assert got["- Deploy on Fridays"] == "Never"  # a bold label opens a block
    assert got["Back under the Don't heading."] == "❌ Don't"


@pytest.mark.parametrize(
    "heading, negative",
    [
        ("❌ Don't", True),
        ("Don'ts", True),
        ("Don’t", True),
        ("Avoid", True),
        ("Common Anti-Patterns", True),
        ("Mistakes to avoid", True),
        ("Never", True),
        ("❌ Bad", True),
        ("Do's and Don'ts", False),  # mixed list
        ("✅ Do", False),
        ("Never hardcode secrets", False),  # an instruction, with explanation below
        ("What goes wrong", False),
        ("Best practices", False),
        (None, False),
    ],
)
def test_negative_sections(heading, negative):
    assert negative_section(heading) is negative


def _k(directive, line_no, text, subject="error messages"):
    return Constraint.model_validate(
        {
            "subject": subject,
            "directive": directive,
            "evidence": {"line_no": line_no, "text": text},
        }
    )


def test_a_dont_list_is_inverted_and_noted():
    constraints = [
        _k("forbid", 6, "Ignore error messages"),
        _k("require", 4, "Read error messages completely"),
    ]
    out, notes = apply_sections(constraints, lines())
    assert [(c.directive, c.strength, c.section_heading) for c in out] == [
        ("require", "must", "❌ Don't"),
        ("require", "must", "✅ Do"),
    ]
    assert notes == [
        'line 6: under heading "❌ Don\'t": forbid -> require (the list names what not to do)'
    ]


def test_a_line_that_negates_itself_is_left_alone():
    out, notes = apply_sections([_k("forbid", 7, "Don't skip validation", "validation")], lines())
    assert out[0].directive == "forbid" and notes == []


def test_soft_directives_invert_to_soft():
    out, _ = apply_sections([_k("prefer", 13, "Deploy on Fridays", "friday deploys")], lines())
    assert (out[0].directive, out[0].strength) == ("avoid", "should")


def test_extractor_records_headings_and_inversions(tmp_path):
    d = write_skill(tmp_path, "n8n", body=DOC)
    offset = 4  # frontmatter lines
    result = {
        "summary": "s",
        "keywords": [],
        "tags": {"languages": [], "frameworks": [], "phase": [], "domain": []},
        "synthetic_queries": [],
        "constraints": [
            {
                "subject": "error messages",
                "directive": "forbid",
                "object": None,
                "object_raw": None,
                "direction": None,
                "scope": {"artifact": "any", "phase": "any", "condition": None},
                "strength": "must",
                "evidence": {"line_no": 6 + offset, "text": "Ignore error messages"},
            }
        ],
        "consumes": [],
        "produces": [],
        "requires_tools": [],
    }
    response = {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": json.dumps(result)}],
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    backend = AnthropicBackend(FakeClient(response), "claude-sonnet-5")
    record = Extractor(backend).extract(d, "n8n", "0" * 64)
    [c] = record.constraints()
    assert (c.directive, c.section_heading) == ("require", "❌ Don't")
    assert record.adjusted == [
        'line 10: under heading "❌ Don\'t": forbid -> require (the list names what not to do)'
    ]


def test_no_fixture_hand_label_is_inverted():
    from conftest import SKILLS_DIR, load_corpus

    for sid, skill in load_corpus().items():
        text = (SKILLS_DIR / sid / "SKILL.md").read_text()
        out, notes = apply_sections(skill.constraints, text.split("\n"))
        assert notes == [], sid
        assert [c.directive for c in out] == [c.directive for c in skill.constraints]
