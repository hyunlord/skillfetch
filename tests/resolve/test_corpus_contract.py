"""The fixture corpus is the contract (CLAUDE.md, constraints.md §7).

Every unordered pair of fixture skills must resolve to exactly the relation
labelled in expected.yaml (unlisted pairs: independent). That implies
conflict precision = 1.0, which is the v0.1 gate.
"""

from itertools import combinations, permutations

from conftest import load_corpus, load_expected

from skillfetch.resolve.relation import Relation, pair_label, skill_relation


def _predicted() -> dict[frozenset[str], str]:
    corpus = load_corpus()
    return {
        frozenset((a, b)): pair_label(corpus[a], corpus[b])
        for a, b in combinations(sorted(corpus), 2)
    }


def _expected_full() -> dict[frozenset[str], str]:
    corpus = load_corpus()
    labelled = load_expected()
    return {
        frozenset((a, b)): labelled.get(frozenset((a, b)), Relation.INDEPENDENT.value)
        for a, b in combinations(sorted(corpus), 2)
    }


def test_conflict_precision_is_one():
    predicted, expected = _predicted(), _expected_full()
    flagged = {p for p, r in predicted.items() if r == "conflict"}
    false_positives = sorted(sorted(p) for p in flagged if expected[p] != "conflict")
    assert false_positives == []
    true_conflicts = {p for p, r in expected.items() if r == "conflict"}
    recall = len(flagged & true_conflicts) / len(true_conflicts)
    print(f"\nconflict precision=1.0 recall={recall:.2f} ({len(flagged)} flagged)")


def test_every_pair_matches_its_label():
    predicted, expected = _predicted(), _expected_full()
    mismatches = sorted(
        (sorted(p), expected[p], predicted[p]) for p in expected if predicted[p] != expected[p]
    )
    assert mismatches == [], "pair, expected, got"


def test_every_finding_has_evidence_from_both_skills():
    corpus = load_corpus()
    for a, b in permutations(sorted(corpus), 2):
        result = skill_relation(corpus[a], corpus[b])
        if result.relation == Relation.INDEPENDENT:
            continue
        assert result.pairs, f"{a} / {b}: {result.relation} without evidence"
        for pair in result.pairs:
            assert pair.a.evidence.text and pair.b.evidence.text
            assert pair.a in corpus[a].constraints and pair.b in corpus[b].constraints
