"""Section headings (constraints.md §2 post-processing): recorded, never applied."""

import json

from conftest import FakeClient, write_skill

from skillfetch.ingest.backends import AnthropicBackend
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.sections import record_sections, section_headings
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


def _k(directive, line_no, text, subject="error messages"):
    return Constraint.model_validate(
        {
            "subject": subject,
            "directive": directive,
            "evidence": {"line_no": line_no, "text": text},
        }
    )


def test_headings_are_recorded_and_never_change_a_directive():
    constraints = [
        _k("require", 6, "Ignore error messages"),  # the model already read the list as bans
        _k("require", 4, "Read error messages completely"),
    ]
    out = record_sections(constraints, lines())
    assert [(c.directive, c.section_heading) for c in out] == [
        ("require", "❌ Don't"),
        ("require", "✅ Do"),
    ]


def test_extractor_records_headings(tmp_path):
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
    assert (c.directive, c.section_heading) == ("forbid", "❌ Don't")
    assert record.adjusted == []
