"""Human-readable findings (constraints.md §6)."""

from conftest import load_corpus

from skillfetch.resolve import render_finding, resolve_set


def test_excluded_conflict_renders_with_both_evidence_lines():
    corpus = load_corpus()
    res = resolve_set([corpus["atomic-commits"]], [corpus["commit-squash"]])
    [ex] = res.excluded
    assert render_finding(ex.to_finding()) == (
        "CONFLICT  commit-squash ⟷ atomic-commits\n"
        "  subject: commit-granularity   scope: commit-message / any\n"
        '  commit-squash:12  "Squash every feature into a single commit before opening a PR."\n'
        '  atomic-commits:12 "Never squash; one logical change per commit, always."'
    )


def test_scope_shows_the_overlap():
    corpus = load_corpus()
    res = resolve_set([corpus["friendly-tone"]], [corpus["plain-markdown"]])
    [w] = res.warnings
    text = render_finding(w)
    assert text.splitlines()[0] == "TENSION  plain-markdown ⟷ friendly-tone"
    assert "scope: markdown / any" in text


def test_redundant_renders_every_matched_pair():
    corpus = load_corpus()
    res = resolve_set([corpus["concise-responses"], corpus["terse-mode"]], [])
    [ex] = res.excluded
    lines = render_finding(ex.to_finding()).splitlines()
    assert lines[0] == "REDUNDANT  concise-responses ⟷ terse-mode"
    assert sum(line.startswith("  subject:") for line in lines) == 2
    assert len(lines) == 1 + 2 * 3


def test_order_conflict_names_both_sides_of_the_order():
    corpus = load_corpus()
    res = resolve_set([corpus["tdd-strict"], corpus["prototype-first"]], [])
    [ex] = res.excluded
    text = render_finding(ex.to_finding())
    assert "subject: order: tests before implementation" in text


def test_needs_review_label():
    corpus = load_corpus()
    res = resolve_set([corpus["type-hints-strict"], corpus["django-migrations"]], [])
    [w] = res.warnings
    assert render_finding(w).startswith("NEEDS_REVIEW  type-hints-strict ⟷ django-migrations")
