"""Pairwise and skill-level relations (constraints.md §3, §4)."""

import pytest
from pydantic import ValidationError

from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.relation import (
    Relation,
    complementary,
    constraint_relation,
    normalize_term,
    skill_relation,
)

_line = iter(range(1, 10_000))


def k(
    subject,
    directive,
    obj=None,
    artifact="any",
    phase="any",
    condition=None,
    strength=None,
    text="quoted line",
    direction=None,
):
    data = {
        "subject": subject,
        "directive": directive,
        "object": obj,
        "direction": direction,
        "scope": {"artifact": artifact, "phase": phase, "condition": condition},
        "evidence": {"line_no": next(_line), "text": text},
    }
    if strength is not None:
        data["strength"] = strength
    return Constraint.model_validate(data)


def rel(a, b):
    """Relation must be symmetric; check both directions."""
    forward, backward = constraint_relation(a, b), constraint_relation(b, a)
    assert forward == backward, f"asymmetric: {forward} vs {backward}"
    return forward


# --- normalization ---------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Type-Hints ", "type-hint"),
        ("docstrings", "docstring"),
        ("tests-first", "test-first"),
        ("Policies", "policy"),
        ("process", "process"),
        ("status", "status"),
        ("analysis", "analysis"),
        ("public   functions", "public function"),
        ("is", "is"),
        ("In Headers.", "in header"),
    ],
)
def test_normalize_term(raw, expected):
    assert normalize_term(raw) == expected


# --- schema ------------------------------------------------------------------------


def test_strength_is_derived_from_directive():
    assert k("emoji", "require").strength == "must"
    assert k("emoji", "forbid").strength == "must"
    assert k("emoji", "prefer").strength == "should"
    assert k("emoji", "avoid").strength == "should"


def test_explicit_strength_is_kept():
    assert k("emoji", "require", strength="should").strength == "should"


def test_evidence_is_required():
    with pytest.raises(ValidationError):
        Constraint.model_validate({"subject": "emoji", "directive": "forbid"})


def test_evidence_text_must_not_be_blank():
    with pytest.raises(ValidationError):
        k("emoji", "forbid", text="   ")


def test_order_requires_object_and_direction():
    with pytest.raises(ValidationError):
        k("tests", "order", None, direction="before")
    with pytest.raises(ValidationError):
        k("tests", "order", "implementation")
    with pytest.raises(ValidationError):
        k("tests", "order", "implementation", direction="whenever")


def test_direction_only_on_order():
    with pytest.raises(ValidationError):
        k("tests", "require", direction="before")


def test_order_can_carry_a_real_condition():
    c = k("tests", "order", "implementation", direction="before", condition="bug fixes")
    assert (c.direction, c.scope.condition) == ("before", "bug fixes")


def test_unknown_directive_rejected():
    with pytest.raises(ValidationError):
        k("emoji", "maybe")


# --- polarity and strength --------------------------------------------------------


def test_hard_opposites_conflict():
    assert rel(k("emoji", "require"), k("emoji", "forbid")) == Relation.CONFLICT


@pytest.mark.parametrize(
    "pos, neg",
    [("prefer", "forbid"), ("require", "avoid"), ("prefer", "avoid")],
)
def test_soft_opposites_are_tension(pos, neg):
    assert rel(k("emoji", pos), k("emoji", neg)) == Relation.TENSION


def test_strength_override_downgrades_conflict_to_tension():
    a = k("emoji", "require", strength="should")
    assert rel(a, k("emoji", "forbid")) == Relation.TENSION


def test_same_polarity_is_redundant():
    assert rel(k("emoji", "forbid"), k("emoji", "avoid")) == Relation.REDUNDANT
    assert rel(k("emoji", "require"), k("emoji", "prefer")) == Relation.REDUNDANT


def test_different_subjects_are_independent():
    assert rel(k("emoji", "require"), k("headers", "forbid")) == Relation.INDEPENDENT


def test_subject_normalization_applies():
    assert rel(k("Type-Hints", "require"), k("type-hint", "forbid")) == Relation.CONFLICT


# --- scope -----------------------------------------------------------------------------


def test_disjoint_artifacts_are_independent():
    a = k("emoji", "require", artifact="commit-message")
    b = k("emoji", "forbid", artifact="markdown")
    assert rel(a, b) == Relation.INDEPENDENT


def test_disjoint_phases_are_independent():
    a = k("comments", "require", phase="implement")
    b = k("comments", "forbid", phase="review")
    assert rel(a, b) == Relation.INDEPENDENT


def test_positive_broader_on_artifact_is_a_carve_out():
    # "use emoji (anywhere)" + "never in markdown": followable together elsewhere.
    a = k("emoji", "require", artifact="any")
    b = k("emoji", "forbid", artifact="markdown")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_positive_broader_on_phase_is_a_carve_out():
    a = k("ask-before-acting", "require", phase="any")
    b = k("ask-before-acting", "forbid", phase="implement")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_negative_broader_is_a_blanket_ban():
    a = k("emoji", "require", artifact="commit-message")
    b = k("emoji", "forbid", artifact="any")
    assert rel(a, b) == Relation.CONFLICT
    soft = k("bullet-points", "avoid", artifact="any")
    narrow = k("bullet-points", "require", artifact="pr-description")
    assert rel(soft, narrow) == Relation.TENSION


def test_mixed_breadth_needs_review():
    a = k("emoji", "require", artifact="any", phase="format")
    b = k("emoji", "forbid", artifact="markdown", phase="any")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_any_overlaps_everything():
    a = k("emoji", "require", artifact="markdown", phase="format")
    b = k("emoji", "forbid", artifact="any", phase="any")
    assert rel(a, b) == Relation.CONFLICT


# --- objects ---------------------------------------------------------------------------


def test_blanket_ban_vs_specific_requirement_conflicts():
    a = k("emoji", "require", "in headers")
    b = k("emoji", "forbid", None)
    assert rel(a, b) == Relation.CONFLICT


def test_general_requirement_vs_specific_ban_needs_review():
    # "use emoji" vs "never in headers": a carve-out, probably compatible.
    a = k("emoji", "require", None)
    b = k("emoji", "forbid", "in headers")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_equal_objects_after_normalization_conflict():
    a = k("docstrings", "require", "Public Functions")
    b = k("docstrings", "forbid", "public function")
    assert rel(a, b) == Relation.CONFLICT


def test_different_objects_are_independent():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "forbid", "npm")
    assert rel(a, b) == Relation.INDEPENDENT


def test_same_polarity_different_objects_are_independent():
    # naming-convention is not exclusive: snake_case in Python and camelCase in JS coexist.
    a = k("naming-convention", "require", "snake_case")
    b = k("naming-convention", "require", "camelCase")
    assert rel(a, b) == Relation.INDEPENDENT


# --- exclusive subjects (§1.1) ---------------------------------------------------------


def test_exclusive_choices_in_same_ecosystem_conflict():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "require", "npm")
    assert rel(a, b) == Relation.CONFLICT


def test_exclusive_soft_choice_is_tension():
    a = k("package-manager", "prefer", "pnpm")
    b = k("package-manager", "require", "npm")
    assert rel(a, b) == Relation.TENSION


def test_exclusive_choice_matches_on_a_word_of_the_object():
    a = k("formatter", "require", "ruff format", artifact="code")
    b = k("formatter", "require", "Black", artifact="code")
    assert rel(a, b) == Relation.CONFLICT


def test_exclusive_choices_across_ecosystems_are_independent():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "require", "pip")
    assert rel(a, b) == Relation.INDEPENDENT
    c = k("test-runner", "require", "jest", artifact="tests")
    d = k("test-runner", "require", "pytest", artifact="tests")
    assert rel(c, d) == Relation.INDEPENDENT


def test_conda_coexists_with_python_package_managers():
    # conda manages environments across languages; `pip install` inside a conda
    # env is routine, so conda is its own ecosystem, not a python alternative.
    conda = k("package-manager", "require", "conda")
    for other in ("pip", "uv", "poetry"):
        assert rel(conda, k("package-manager", "require", other)) == Relation.INDEPENDENT


def test_exclusive_same_choice_is_not_a_conflict():
    a = k("formatter", "require", "ruff")
    b = k("formatter", "require", "ruff format")
    assert rel(a, b) == Relation.INDEPENDENT


def test_exclusive_unknown_choice_needs_review():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "require", "our in-house installer")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_exclusive_ambiguous_object_needs_review():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "require", "npm or yarn")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_exclusive_with_different_conditions_needs_review():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "require", "npm", condition="in the legacy app")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_exclusive_bans_on_different_choices_are_independent():
    a = k("package-manager", "forbid", "npm")
    b = k("package-manager", "forbid", "yarn")
    assert rel(a, b) == Relation.INDEPENDENT


def test_exclusive_in_disjoint_scope_is_independent():
    a = k("build-tool", "require", "vite", phase="implement")
    b = k("build-tool", "require", "webpack", phase="review")
    assert rel(a, b) == Relation.INDEPENDENT


def test_exclusive_without_object_is_not_a_choice():
    a = k("package-manager", "require", None)
    b = k("package-manager", "require", "npm")
    assert rel(a, b) == Relation.INDEPENDENT


# --- conditions ------------------------------------------------------------------------


def test_condition_on_one_side_needs_review():
    a = k("type-hints", "require")
    b = k("type-hints", "forbid", condition="when editing migrations")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_different_conditions_need_review():
    a = k("type-hints", "require", condition="in library code")
    b = k("type-hints", "forbid", condition="in scripts")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_identical_conditions_behave_like_no_condition():
    a = k("type-hints", "require", condition="When writing Python")
    b = k("type-hints", "forbid", condition="when writing python.")
    assert rel(a, b) == Relation.CONFLICT


def test_condition_does_not_rescue_disjoint_scope():
    a = k("type-hints", "require", artifact="code")
    b = k("type-hints", "forbid", artifact="markdown", condition="in examples")
    assert rel(a, b) == Relation.INDEPENDENT


def test_condition_with_different_objects_stays_independent():
    a = k("package-manager", "require", "pnpm")
    b = k("package-manager", "forbid", "npm", condition="in ci")
    assert rel(a, b) == Relation.INDEPENDENT


# --- order -----------------------------------------------------------------------------


def test_reversed_order_conflicts():
    a = k("tests", "order", "implementation", direction="before", strength="must")
    b = k("implementation", "order", "tests", direction="before", strength="must")
    assert rel(a, b) == Relation.CONFLICT


def test_before_vs_after_on_same_subject_conflicts():
    a = k("tests", "order", "implementation", direction="before", strength="must")
    b = k("tests", "order", "implementation", direction="after", strength="must")
    assert rel(a, b) == Relation.CONFLICT


def test_same_order_written_two_ways_is_redundant():
    a = k("tests", "order", "implementation", direction="before", strength="must")
    b = k("implementation", "order", "tests", direction="after", strength="must")
    assert rel(a, b) == Relation.REDUNDANT


def test_reversed_soft_order_is_tension():
    a = k("tests", "order", "implementation", direction="before", strength="should")
    b = k("implementation", "order", "tests", direction="before", strength="must")
    assert rel(a, b) == Relation.TENSION


def test_reversed_order_under_different_conditions_needs_review():
    a = k("tests", "order", "implementation", direction="before", condition="bug fixes")
    b = k("implementation", "order", "tests", direction="before")
    assert rel(a, b) == Relation.NEEDS_REVIEW


def test_reversed_order_under_the_same_condition_conflicts():
    a = k("tests", "order", "implementation", direction="before", condition="Bug fixes")
    b = k("implementation", "order", "tests", direction="before", condition="bug fixes.")
    assert rel(a, b) == Relation.CONFLICT


def test_order_condition_is_part_of_identity():
    a = S("a", k("tests", "order", "implementation", direction="before", condition="bug fixes"))
    b = S("b", k("tests", "order", "implementation", direction="before"))
    assert skill_relation(a, b).relation == Relation.INDEPENDENT


def test_order_on_unrelated_objects_is_independent():
    a = k("tests", "order", "implementation", direction="before", strength="must")
    b = k("docs", "order", "release", direction="before", strength="must")
    assert rel(a, b) == Relation.INDEPENDENT


def test_order_vs_non_order_is_independent():
    a = k("tests", "order", "implementation", direction="before", strength="must")
    b = k("tests", "forbid")
    assert rel(a, b) == Relation.INDEPENDENT


def test_reversed_order_in_disjoint_scope_is_independent():
    a = k("tests", "order", "code", artifact="code", direction="before", strength="must")
    b = k("code", "order", "tests", artifact="markdown", direction="before", strength="must")
    assert rel(a, b) == Relation.INDEPENDENT


# --- skill level -----------------------------------------------------------------------


def S(sid, *constraints, **kw):
    return Skill(id=sid, constraints=list(constraints), **kw)


def test_skill_conflict_wins_and_carries_evidence():
    bad_a = k("emoji", "require", text="Always use emoji.")
    bad_b = k("emoji", "forbid", text="Never use emoji.")
    a = S("a", k("comments", "prefer"), bad_a)
    b = S("b", k("comments", "avoid"), bad_b)
    result = skill_relation(a, b)
    assert result.relation == Relation.CONFLICT
    assert [(p.a.evidence.text, p.b.evidence.text) for p in result.pairs] == [
        ("Always use emoji.", "Never use emoji.")
    ]


def test_skill_tension_and_review_ranking():
    a = S("a", k("emoji", "prefer"), k("type-hints", "require"))
    b = S("b", k("emoji", "forbid"), k("type-hints", "forbid", condition="in scripts"))
    assert skill_relation(a, b).relation == Relation.TENSION
    a2 = S("a2", k("type-hints", "require"))
    assert skill_relation(a2, b).relation == Relation.NEEDS_REVIEW


def test_equal_multisets_are_redundant_both_ways():
    a = S("a", k("emoji", "forbid", text="No emoji."), k("Docstrings", "require"))
    b = S("b", k("docstring", "require", text="Docs!"), k("emoji", "forbid", text="Never emoji."))
    for kept, cand in ((a, b), (b, a)):
        result = skill_relation(kept, cand)
        assert result.relation == Relation.REDUNDANT
        assert len(result.pairs) == 2
        assert all(p.relation == Relation.REDUNDANT for p in result.pairs)


def test_subset_is_redundant_only_in_the_lossless_direction():
    # b ⊆ a: dropping b loses nothing; dropping a would lose the docstring rule.
    a = S("a", k("emoji", "forbid"), k("docstrings", "require"))
    b = S("b", k("emoji", "forbid", text="the only rule in b"))
    result = skill_relation(a, b)
    assert result.relation == Relation.REDUNDANT
    assert [p.b.evidence.text for p in result.pairs] == ["the only rule in b"]
    assert skill_relation(b, a).relation == Relation.INDEPENDENT


def test_partial_overlap_is_not_redundant():
    a = S("a", k("emoji", "forbid"), k("docstrings", "require"))
    b = S("b", k("emoji", "forbid"), k("headers", "require"))
    assert skill_relation(a, b).relation == Relation.INDEPENDENT
    assert skill_relation(b, a).relation == Relation.INDEPENDENT


def test_multiset_counts_matter():
    a = S("a", k("emoji", "forbid"), k("emoji", "forbid"))
    b = S("b", k("emoji", "forbid"))
    assert skill_relation(a, b).relation == Relation.REDUNDANT
    assert skill_relation(b, a).relation == Relation.INDEPENDENT


def test_strength_is_part_of_multiset_identity():
    a = S("a", k("emoji", "forbid"))
    b = S("b", k("emoji", "forbid", strength="should"))
    assert skill_relation(a, b).relation == Relation.INDEPENDENT
    assert skill_relation(b, a).relation == Relation.INDEPENDENT


def test_skills_without_constraints_are_never_redundant():
    assert skill_relation(S("a"), S("b")).relation == Relation.INDEPENDENT
    # The empty set is a subset of everything, but there is no evidence line to show.
    assert skill_relation(S("a", k("emoji", "forbid")), S("b")).relation == Relation.INDEPENDENT


def test_independent_skill_relation_has_no_pairs():
    result = skill_relation(S("a", k("emoji", "forbid")), S("b", k("headers", "forbid")))
    assert result.relation == Relation.INDEPENDENT
    assert result.pairs == []


def test_skill_relation_is_symmetric_in_kind():
    a = S("a", k("emoji", "require", "in headers"))
    b = S("b", k("emoji", "forbid"))
    assert skill_relation(a, b).relation == skill_relation(b, a).relation


# --- complementary ---------------------------------------------------------------------


def test_complementary_via_produces_consumes_either_direction():
    a = S("a", produces=["failing test"])
    b = S("b", consumes=["Failing Tests"])
    assert complementary(a, b)
    assert complementary(b, a)


def test_complementary_via_same_domain_different_phase():
    a = S("a", tags={"domain": ["backend"], "phase": ["plan"]})
    b = S("b", tags={"domain": ["backend"], "phase": ["implement"]})
    assert complementary(a, b)


def test_not_complementary_when_phases_overlap():
    a = S("a", tags={"domain": ["backend"], "phase": ["implement"]})
    b = S("b", tags={"domain": ["backend"], "phase": ["implement", "review"]})
    assert not complementary(a, b)


def test_not_complementary_without_shared_domain():
    a = S("a", tags={"domain": ["backend"], "phase": ["plan"]})
    b = S("b", tags={"domain": ["frontend"], "phase": ["implement"]})
    assert not complementary(a, b)
