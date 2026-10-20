"""resolve_set (constraints.md §5), exercised on the fixture corpus."""

import hashlib
import json

from conftest import load_corpus

from skillfetch.resolve import resolve_set


def skills(*names):
    corpus = load_corpus()
    return [corpus[n] for n in names]


def run(auto=(), pinned=()):
    return resolve_set(skills(*auto), skills(*pinned))


def test_empty_input():
    res = run()
    assert res.included == [] and res.excluded == [] and res.warnings == []
    assert res.set_id == hashlib.sha256(b"").hexdigest()[:12]


def test_pinned_are_always_included_and_conflicts_warned():
    res = run(pinned=["commit-squash", "atomic-commits"])
    assert res.included == ["commit-squash", "atomic-commits"]
    assert res.excluded == []
    [warning] = res.warnings
    assert (warning.kind, warning.a, warning.b) == ("conflict", "commit-squash", "atomic-commits")
    [ev] = warning.evidence
    assert ev.subject == "commit-granularity"
    assert (ev.a.skill_id, ev.a.line_no) == ("commit-squash", 12)
    assert ev.a.text == "Squash every feature into a single commit before opening a PR."
    assert (ev.b.skill_id, ev.b.text) == (
        "atomic-commits",
        "Never squash; one logical change per commit, always.",
    )


def test_auto_conflicting_with_pinned_is_excluded_with_evidence():
    res = run(auto=["emoji-headers"], pinned=["plain-markdown"])
    assert res.included == ["plain-markdown"]
    [ex] = res.excluded
    assert (ex.id, ex.reason, ex.conflicts_with) == ("emoji-headers", "conflict", "plain-markdown")
    [ev] = ex.evidence
    assert ev.a.text == "Never use emoji anywhere in Markdown output."
    assert ev.b.text == "Always start every section header with an emoji."
    assert ev.b.skill_id == "emoji-headers"


def test_earlier_auto_pick_wins():
    res = run(auto=["tdd-strict", "prototype-first"])
    assert res.included == ["tdd-strict"]
    assert [(e.id, e.conflicts_with) for e in res.excluded] == [("prototype-first", "tdd-strict")]

    res = run(auto=["prototype-first", "tdd-strict"])
    assert res.included == ["prototype-first"]
    assert [(e.id, e.conflicts_with) for e in res.excluded] == [("tdd-strict", "prototype-first")]


def test_redundant_auto_is_excluded():
    res = run(auto=["atomic-commits", "small-commits"])
    assert res.included == ["atomic-commits"]
    [ex] = res.excluded
    assert (ex.id, ex.reason, ex.conflicts_with) == (
        "small-commits",
        "redundant_with",
        "atomic-commits",
    )
    assert len(ex.evidence) == 2


def test_conflict_takes_priority_over_redundancy():
    res = run(auto=["small-commits"], pinned=["atomic-commits", "commit-squash"])
    [ex] = res.excluded
    assert (ex.reason, ex.conflicts_with) == ("conflict", "commit-squash")


def test_redundant_wins_over_tension_and_suppresses_warnings():
    res = run(auto=["no-emoji-docs"], pinned=["friendly-tone", "plain-markdown"])
    [ex] = res.excluded
    assert (ex.id, ex.reason, ex.conflicts_with) == (
        "no-emoji-docs",
        "redundant_with",
        "plain-markdown",
    )
    # friendly-tone vs plain-markdown is tension between pinned skills: not warned (§5 step 2).
    assert res.warnings == []


def test_excluded_skills_do_not_block_later_candidates():
    # clean-headings conflicts with emoji-headers, but emoji-headers was already excluded.
    res = run(auto=["plain-markdown", "emoji-headers", "clean-headings"])
    assert res.included == ["plain-markdown", "clean-headings"]
    assert [e.id for e in res.excluded] == ["emoji-headers"]


def test_tension_is_included_with_warning():
    res = run(auto=["plain-markdown", "friendly-tone"])
    assert res.included == ["plain-markdown", "friendly-tone"]
    [w] = res.warnings
    assert (w.kind, w.a, w.b) == ("tension", "plain-markdown", "friendly-tone")
    assert w.evidence


def test_tension_warned_once_per_included_skill():
    res = run(auto=["friendly-tone"], pinned=["plain-markdown", "no-emoji-docs"])
    assert "friendly-tone" in res.included
    assert [(w.kind, w.a) for w in res.warnings] == [
        ("tension", "plain-markdown"),
        ("tension", "no-emoji-docs"),
    ]


def test_needs_review_is_included_with_warning():
    res = run(auto=["type-hints-strict", "django-migrations"])
    assert res.included == ["type-hints-strict", "django-migrations"]
    [w] = res.warnings
    assert (w.kind, w.a, w.b) == ("needs_review", "type-hints-strict", "django-migrations")
    assert w.evidence[0].b.text == "When editing Django migration files, do not add type hints."


def test_auto_that_is_also_pinned_is_not_duplicated():
    res = run(auto=["plain-markdown", "gitmoji-commits"], pinned=["plain-markdown"])
    assert res.included == ["plain-markdown", "gitmoji-commits"]
    assert res.excluded == []


def test_repeated_ids_are_collapsed():
    res = run(
        auto=["gitmoji-commits", "gitmoji-commits"], pinned=["careful-agent", "careful-agent"]
    )
    assert res.included == ["careful-agent", "gitmoji-commits"]
    assert res.excluded == []


def test_precedence_is_pinned_then_auto_in_given_order():
    res = run(
        auto=["type-hints-strict", "gitmoji-commits", "minimal-scripts"],
        pinned=["pnpm-only", "careful-agent"],
    )
    assert res.precedence == ["pnpm-only", "careful-agent", "type-hints-strict", "gitmoji-commits"]
    assert res.included == res.precedence


def test_set_id_depends_only_on_included_set():
    a = run(auto=["gitmoji-commits"], pinned=["careful-agent"])
    b = run(auto=["careful-agent", "gitmoji-commits"])
    c = run(auto=["gitmoji-commits", "careful-agent", "act-autonomously"])
    expected = hashlib.sha256(b"careful-agent\ngitmoji-commits").hexdigest()[:12]
    assert a.set_id == b.set_id == expected
    assert c.set_id == hashlib.sha256(b"careful-agent\ngitmoji-commits").hexdigest()[:12]
    assert run(auto=["gitmoji-commits"]).set_id != expected


def test_result_is_plain_json():
    res = run(auto=["emoji-headers", "friendly-tone"], pinned=["plain-markdown"])
    data = json.loads(json.dumps(res.model_dump(mode="json")))
    assert set(data) == {"set_id", "included", "excluded", "warnings", "precedence"}
    assert data["excluded"][0]["evidence"][0]["a"]["line_no"] >= 1
