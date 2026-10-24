"""LLM judge (needs_review / tension pairs). A fake backend; no network."""

import json
from pathlib import Path

from skillfetch.ingest.extract import Completion, Usage
from skillfetch.ingest.judge import Judge, Side, agrees, excerpt, run_judge
from skillfetch.ingest.judge_run import calibration_report, cross_table, fixture_pairs

FIXTURES = Path(__file__).parents[1] / "fixtures"


class FakeBackend:
    key = "openrouter/test/judge"

    def __init__(self, verdict="conflict", fail_on=None):
        self.verdict, self.fail_on, self.calls = verdict, fail_on, []

    def complete(self, system, messages, schema):
        text = messages[0]["content"]
        self.calls.append(text)
        if self.fail_on and self.fail_on in text:
            raise ConnectionError("Connection error.")
        out = {
            "verdict": self.verdict,
            "reason": "r",
            "ambiguous_together": True,
            "confidence": 0.9,
        }
        return Completion(json.dumps(out), "end_turn", Usage(reported_cost_usd=0.001))


def test_excerpt_marks_evidence_lines_with_context_and_heading():
    text = "\n".join(["---", "name: s", "---", "# Rules", *[f"line {i}" for i in range(5, 30)]])
    out = excerpt(Side("s", "s", "desc", text, (12,)))
    assert "section heading of line 12: Rules" in out
    assert ">   12| line 12" in out
    assert "    7| line 7" in out and "   17| line 17" in out
    assert "line 18" not in out and "line 6\n" not in out


def test_the_judge_never_sees_extracted_constraints():
    pairs = fixture_pairs(FIXTURES)
    assert len(pairs) == 42
    for p in pairs:
        assert '"directive"' not in p.item.text and "forbid" not in p.item.text.split("|")[0]


def test_judgments_are_cached_and_failures_isolated(tmp_path):
    pairs = fixture_pairs(FIXTURES)[:3]
    backend = FakeBackend(fail_on="careful-agent")
    judge = Judge(backend, tmp_path)
    outcomes = run_judge([p.item for p in pairs], judge, jobs=2)
    failed = [o for o in outcomes if o.record is None]
    assert len(failed) == 1 and "Connection error." in failed[0].error
    again = run_judge([p.item for p in pairs], Judge(FakeBackend(), tmp_path), jobs=2)
    assert sum(o.fresh for o in again) == 1  # only the failed pair is asked again


def test_calibration_agreement_and_cross_table(tmp_path):
    pairs = fixture_pairs(FIXTURES)
    outcomes = run_judge([p.item for p in pairs], Judge(FakeBackend("conflict"), tmp_path))
    rate, text = calibration_report(pairs, outcomes)
    assert rate == 21 / 42  # 20 conflicts + 1 tension agree with "conflict"
    assert "judge agreement with hand labels: 0.500 (21/42)" in text
    table = cross_table(pairs, outcomes)
    assert "| tension | 15 opposed | 1 | 0 | 0 | 0 | 0 | 0 | 1 |" in table
    assert "| **total** | | 42 | 0 | 0 | 0 | 0 | 0 | 42 |" in table


def test_agreement_mapping():
    assert agrees("needs_review", "carve_out") and agrees("needs_review", "situational")
    assert agrees("subsumes:a", "independent") and not agrees("conflict", "carve_out")
