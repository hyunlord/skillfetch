"""Calibration: extracted constraints vs hand labels (constraints.md §2, §7)."""

from conftest import FIXTURES_DIR, load_corpus

from skillfetch.ingest.calibrate import GATE, calibrate, render_calibration
from skillfetch.ingest.extract import EXTRACT_VERSION, ExtractRecord, ExtractResult

PAIRS = 41 * 40 // 2


def _record(skill_id, constraints, status="ok"):
    result = None
    if status == "ok":
        result = ExtractResult(
            summary="s",
            keywords=[],
            tags={"languages": [], "frameworks": [], "phase": [], "domain": []},
            synthetic_queries=[],
            constraints=[c.model_copy(update={"id": ""}) for c in constraints],
            consumes=[],
            produces=[],
            requires_tools=[],
        )
    return ExtractRecord(
        extract_version=EXTRACT_VERSION,
        model="claude-sonnet-5",
        content_hash="0" * 64,
        skill_id=skill_id,
        status=status,
        result=result,
    )


def perfect_records():
    return {sid: _record(sid, skill.constraints) for sid, skill in load_corpus().items()}


def _edit(records, skill_id, index, **update):
    cs = list(records[skill_id].result.constraints)
    cs[index] = cs[index].model_copy(update=update)
    records[skill_id] = _record(skill_id, cs)


def test_perfect_extraction_scores_one():
    cal = calibrate(FIXTURES_DIR, perfect_records())
    assert cal.pairs.total == PAIRS and cal.pairs.correct == PAIRS
    assert cal.pairs.accuracy == 1.0 and cal.passed
    assert all(f.matches == f.total for f in cal.fields.per_field.values())
    assert cal.fields.missed == [] and cal.fields.extra == []
    text = render_calibration(cal)
    assert f"pair-relation accuracy, all pairs: 1.000 ({PAIRS}/{PAIRS})" in text
    assert "informative pairs: 1.000 (33/33)" in text
    assert (cal.pairs.recall, cal.pairs.false_positives) == (1.0, 0)
    assert "recall 1.000 (33/33), false positives 0" in text
    assert "PASS" in text.splitlines()[-1]


def test_field_disagreement_that_keeps_relations_costs_no_pair_accuracy():
    records = perfect_records()
    # branch-naming appears in no other skill, so a different object changes no relation
    _edit(records, "commit-squash", 1, object="feature branches")
    cal = calibrate(FIXTURES_DIR, records)
    assert cal.pairs.accuracy == 1.0
    assert cal.fields.per_field["object"].matches == cal.fields.per_field["object"].total - 1


def test_wrong_directive_shows_up_as_mismatched_pairs_with_evidence():
    records = perfect_records()
    _edit(records, "commit-squash", 0, directive="prefer", strength="should")
    cal = calibrate(FIXTURES_DIR, records)
    assert cal.pairs.correct == PAIRS - 2
    assert {(m.a, m.b, m.expected, m.got) for m in cal.pairs.mismatches} == {
        ("atomic-commits", "commit-squash", "conflict", "tension"),
        ("commit-squash", "small-commits", "conflict", "tension"),
    }
    assert cal.fields.per_field["directive"].matches == cal.fields.per_field["directive"].total - 1
    text = render_calibration(cal)
    assert "MISMATCH  atomic-commits ⟷ commit-squash  expected conflict, got tension" in text
    assert (
        'commit-squash:12  "Squash every feature into a single commit before opening a PR."' in text
    )
    assert "prefer commit-granularity [squash]" in text


def test_missed_constraint_is_reported_and_explained():
    records = perfect_records()
    cs = list(records["atomic-commits"].result.constraints)
    records["atomic-commits"] = _record("atomic-commits", cs[1:])  # lose the squash ban
    cal = calibrate(FIXTURES_DIR, records)
    assert [(s, c.evidence.line_no) for s, c in cal.fields.missed] == [("atomic-commits", 12)]
    got = {(m.a, m.b): m.got for m in cal.pairs.mismatches}
    assert got[("atomic-commits", "commit-squash")] == "independent"
    assert got[("atomic-commits", "small-commits")] == "subsumes:small-commits"
    text = render_calibration(cal)
    assert "atomic-commits:12  (nothing extracted on this line)" in text


def test_extra_constraint_is_reported():
    records = perfect_records()
    first = records["careful-agent"].result.constraints[0]
    records["careful-agent"] = _record(
        "careful-agent", [first, first.model_copy(update={"subject": "file edits"})]
    )
    cal = calibrate(FIXTURES_DIR, records)
    assert [(s, c.subject) for s, c in cal.fields.extra] == [("careful-agent", "file edits")]


def test_failed_and_missing_extractions_count_against_accuracy():
    records = perfect_records()
    records["commit-squash"] = _record("commit-squash", [], status="extract_failed")
    del records["tdd-strict"]
    cal = calibrate(FIXTURES_DIR, records)
    assert cal.failed == ["commit-squash"] and cal.missing == ["tdd-strict"]
    assert cal.pairs.correct < PAIRS


def test_an_empty_extractor_does_not_pass_the_gate():
    # 787 of 820 pairs are independent, so extracting nothing scores ~0.96 over all pairs.
    # The gate is on informative pairs (expected or got not independent), where it scores 0.
    records = {sid: _record(sid, []) for sid in load_corpus()}
    cal = calibrate(FIXTURES_DIR, records)
    assert cal.pairs.accuracy > GATE
    assert cal.pairs.informative_accuracy == 0.0 and not cal.passed
    assert (cal.pairs.recall, cal.pairs.false_positives) == (0.0, 0)
    assert "BELOW GATE" in render_calibration(cal).splitlines()[-1]


def test_false_conflicts_count_against_the_gate():
    records = perfect_records()
    # turn inline-comments' rule into the same object self-documenting bans: a conflict
    # on a pair labelled independent
    _edit(records, "inline-comments", 0, object="restating the code")
    cal = calibrate(FIXTURES_DIR, records)
    assert [(m.a, m.b, m.expected, m.got) for m in cal.pairs.mismatches] == [
        ("inline-comments", "self-documenting", "independent", "conflict")
    ]
    assert (cal.pairs.informative_correct, cal.pairs.informative_total) == (33, 34)
    assert (cal.pairs.recall, cal.pairs.false_positives) == (1.0, 1)
