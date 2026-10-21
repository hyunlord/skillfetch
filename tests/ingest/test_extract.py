"""Extraction through the API, replayed from recorded responses (no network)."""

import subprocess
import sys

import pytest
from conftest import SKILLS_DIR, FakeClient, recorded, write_skill

from skillfetch.ingest.backends import AnthropicBackend, anthropic_request, parse_model
from skillfetch.ingest.extract import (
    EXTRACT_VERSION,
    PROMPT_SHA256,
    Extractor,
    ExtractResult,
    Usage,
    cost_usd,
    numbered,
    prompt_fingerprint,
    response_schema,
    system_prompt,
)
from skillfetch.resolve.models import Constraint
from skillfetch.resolve.vocabulary import VOCABULARY


def run(skill, *responses, model="claude-sonnet-5"):
    client = FakeClient(*[recorded(r) if isinstance(r, str) else r for r in responses])
    backend = AnthropicBackend(client, model)
    record = Extractor(backend).extract(SKILLS_DIR / skill, skill, "0" * 64)
    return record, client


# --- prompt and schema ----------------------------------------------------------------------


def test_prompt_and_schema_are_pinned_to_the_extract_version():
    assert prompt_fingerprint() == PROMPT_SHA256, (
        "the extraction prompt or schema changed: bump EXTRACT_VERSION "
        f"(now {EXTRACT_VERSION}) and set PROMPT_SHA256 = {prompt_fingerprint()!r}"
    )


def test_system_prompt_carries_the_vocabulary():
    prompt = system_prompt()
    assert "{{" not in prompt
    for term in VOCABULARY:
        assert f"`{term.name}`" in prompt
        for eco in term.ecosystems:
            assert all(choice in prompt for choice in eco.choices)
    assert "no line, no constraint" in prompt.lower()


def _objects(schema):
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            yield schema
        for value in schema.values():
            yield from _objects(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _objects(value)


def test_schema_is_strict():
    for obj in _objects(response_schema()):
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])


def test_schema_mirrors_the_result_models():
    schema = response_schema()
    assert list(schema["properties"]) == list(ExtractResult.model_fields)
    constraint = schema["properties"]["constraints"]["items"]
    assert set(constraint["properties"]) == set(Constraint.model_fields) - {"id"}


def test_request_shape():
    messages = [{"role": "user", "content": "x"}]
    req = anthropic_request("claude-sonnet-5", system_prompt(), messages, response_schema())
    assert req["model"] == "claude-sonnet-5" and req["messages"] is messages
    assert "temperature" not in req  # rejected by current models
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert anthropic_request("claude-sonnet-4-6", "s", messages, {})["temperature"] == 0


def test_numbered_lines_match_file_line_numbers():
    assert numbered("a\nb\n") == "1| a\n2| b"
    assert numbered("\n".join("x" * 12)).splitlines()[9] == "10| x"


# --- extraction -------------------------------------------------------------------------------


def test_successful_extraction():
    record, client = run("commit-squash", "commit-squash.ok.json")
    assert record.status == "ok" and record.error is None
    assert record.model == "anthropic/claude-sonnet-5"
    assert len(client.requests) == 1
    assert (
        "12| - Squash every feature into a single commit"
        in client.requests[0]["messages"][0]["content"]
    )
    [squash, branch] = record.constraints()
    assert squash.id == "commit-squash#c1"
    assert (squash.subject, squash.directive, squash.object) == (
        "commit-granularity",
        "require",
        "squash",
    )
    assert record.result.tags.domain == ["git"]


def test_miscounted_line_is_repaired_and_invented_quote_dropped():
    record, _ = run("commit-squash", "commit-squash.evidence-issues.json")
    assert record.status == "ok"
    [kept] = record.constraints()
    assert kept.evidence.line_no == 12
    assert record.repaired == [
        "line 3 -> 12: 'Squash every feature into a single commit before opening a PR.'"
    ]
    [dropped] = record.dropped
    assert dropped.reason == "quote not found in SKILL.md"
    assert dropped.constraint["evidence"]["text"] == "Always rebase onto main before merging."


def test_invalid_output_is_retried_once_with_the_error():
    record, client = run("tdd-strict", "tdd-strict.missing-direction.json", "tdd-strict.ok.json")
    assert record.status == "ok" and len(record.attempts) == 2
    assert "direction" in record.attempts[0].error
    retry = client.requests[1]["messages"]
    assert [m["role"] for m in retry] == ["user", "assistant", "user"]
    assert "failed validation" in retry[2]["content"] and "direction" in retry[2]["content"]
    [order, _] = record.constraints()
    assert (order.direction, order.object) == ("before", "implementation")


def test_second_failure_gives_up():
    record, client = run("commit-squash", "not-json.json", "max-tokens.json")
    assert record.status == "extract_failed" and record.result is None
    assert len(client.requests) == 2
    assert "not valid JSON" in record.error
    assert [a.stop_reason for a in record.attempts] == ["end_turn", "max_tokens"]


def test_refusal_is_not_retried():
    record, client = run("commit-squash", "refusal.json")
    assert record.status == "extract_failed" and len(client.requests) == 1
    assert record.error == "refused (cyber)"


def test_oversized_skill_is_not_sent(tmp_path):
    d = write_skill(tmp_path, "huge", "word " * 12000)
    client = FakeClient()
    record = Extractor(AnthropicBackend(client, "claude-sonnet-5")).extract(d, "huge", "0" * 64)
    assert record.status == "too_large" and client.requests == []


# --- cost ---------------------------------------------------------------------------------------


def test_cost_counts_cache_writes_and_reads():
    record, _ = run("tdd-strict", "tdd-strict.missing-direction.json", "tdd-strict.ok.json")
    assert record.usage == Usage(
        input_tokens=1190 + 1650,
        output_tokens=280 + 305,
        cache_creation_input_tokens=2400,
        cache_read_input_tokens=2400,
    )
    expected = (2840 * 2.00 + 2400 * 2.00 * 1.25 + 2400 * 2.00 * 0.1 + 585 * 10.00) / 1e6
    assert record.cost_usd == pytest.approx(expected)


def test_unknown_model_has_no_price():
    assert cost_usd("anthropic/claude-something-new", Usage(input_tokens=10)) is None


def test_model_specs_carry_a_provider():
    assert parse_model("anthropic/claude-sonnet-5") == ("anthropic", "claude-sonnet-5")
    assert parse_model("claude-haiku-4-5") == ("anthropic", "claude-haiku-4-5")
    for bad in ("gpt-x", "nope/model", "anthropic/"):
        with pytest.raises(ValueError):
            parse_model(bad)


def test_extract_module_does_not_need_the_sdk():
    code = (
        "import sys, skillfetch.ingest.extract, skillfetch.ingest.backends, skillfetch.cli; "
        "assert not {'anthropic', 'openai'} & set(sys.modules)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


# --- object vocabulary ---------------------------------------------------------------------------


def test_object_outside_the_vocabulary_is_retried_with_the_allowed_list():
    record, client = run(
        "concise-responses",
        "concise-responses.disallowed-object.json",
        "concise-responses.ok.json",
    )
    assert record.status == "ok" and len(record.attempts) == 2
    retry = client.requests[1]["messages"][2]["content"]
    assert "'of what you did' is not allowed for subject `summary-at-end`" in retry
    assert "Allowed objects: (none), or null" in retry
    assert "more specific free-text subject" in retry


def test_free_text_subjects_keep_free_objects():
    from skillfetch.ingest.extract import vocabulary_errors

    result = ExtractResult.model_validate_json(
        recorded("commit-squash.ok.json")["content"][0]["text"]
    )
    assert vocabulary_errors(result) == []  # branch-naming is open, squash is listed


def test_hand_labels_follow_the_object_vocabulary():
    from conftest import load_corpus

    from skillfetch.ingest.extract import constraint_vocabulary_errors

    for sid, skill in load_corpus().items():
        assert constraint_vocabulary_errors(skill.constraints) == [], sid


def test_prompt_lists_allowed_objects():
    prompt = system_prompt()
    assert '`emoji` (objects: "in headers")' in prompt
    assert "`summary-at-end` (no object)" in prompt


# --- one constraint per line ---------------------------------------------------------------------


def test_extra_constraints_on_a_line_are_merged_into_the_vocabulary_one():
    record, _ = run("atomic-commits", "atomic-commits.two-per-line.json")
    assert record.status == "ok"
    kept = [(c.evidence.line_no, c.subject) for c in record.constraints()]
    assert kept == [(12, "commit-granularity"), (13, "review-before-merge")]
    reasons = sorted(d.reason for d in record.dropped)
    assert reasons == [
        "merged: duplicate of the constraint kept on line 13",
        "merged: one constraint per line; kept `commit-granularity` on line 12",
    ]


def test_merge_keeps_the_first_when_no_subject_is_in_the_vocabulary():
    from skillfetch.ingest.extract import merge_per_line

    def c(subject, line):
        return Constraint.model_validate(
            {"subject": subject, "directive": "require", "evidence": {"line_no": line, "text": "t"}}
        )

    kept, dropped = merge_per_line([c("alpha", 3), c("beta", 3), c("gamma", 4)])
    assert [(k.subject, k.evidence.line_no) for k in kept] == [("alpha", 3), ("gamma", 4)]
    assert [d.constraint["subject"] for d in dropped] == ["beta"]


def test_prompt_asks_for_one_constraint_per_line():
    assert "at most one constraint per line" in system_prompt()


# --- condition vs target --------------------------------------------------------------------


def test_prompt_separates_conditions_from_targets():
    prompt = system_prompt()
    # the calibration counterexample, reworded (the original is a fixture line)
    assert '"Run black on every Python file" has condition\nnull' in prompt
    assert "Python is what gets formatted" in prompt


def test_prompt_examples_do_not_quote_fixture_lines():
    # examples copied from the calibration set would inflate calibration scores
    from conftest import fixture_skill_dirs

    prompt = system_prompt()
    for d in fixture_skill_dirs():
        for line in (d / "SKILL.md").read_text().splitlines():
            rule = line.removeprefix("- ").strip()
            if line.startswith("- ") and len(rule) > 25:
                assert rule not in prompt, (d.name, rule)


def test_prompt_shares_no_five_word_run_with_a_fixture_rule():
    import re

    from conftest import fixture_skill_dirs

    def words(text):
        return re.findall(r"[a-z0-9']+", text.lower())

    prompt = words(system_prompt())
    shingles = {tuple(prompt[i : i + 5]) for i in range(len(prompt) - 4)}
    for d in fixture_skill_dirs():
        for line in (d / "SKILL.md").read_text().splitlines():
            if not line.startswith("- "):
                continue
            w = words(line)
            hits = [
                " ".join(w[i : i + 5]) for i in range(len(w) - 4) if tuple(w[i : i + 5]) in shingles
            ]
            assert not hits, (d.name, hits)


def test_prompt_covers_the_patterns_all_models_missed():
    prompt = system_prompt()
    for marker in (
        "ask-before-acting",
        "summary-at-end",
        "preamble",
        "type-hints",
        "commit-granularity",
    ):
        assert prompt.count(f'"subject": "{marker}"') >= 1, marker


# --- vocabulary post-processing (polarity, implied artifact) -------------------------------------


def _k(subject, directive, text, obj=None, artifact="any", line=1):
    return Constraint.model_validate(
        {
            "subject": subject,
            "directive": directive,
            "object": obj,
            "scope": {"artifact": artifact},
            "evidence": {"line_no": line, "text": text},
        }
    )


def test_removal_verb_on_a_negative_subject_flips_to_a_ban():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary(
        [
            _k(
                "trailing-whitespace",
                "require",
                "Strip trailing whitespace from every line.",
                line=13,
            )
        ]
    )
    assert (c.directive, c.strength) == ("forbid", "must")
    assert notes == ["line 13: require -> forbid (`trailing-whitespace` is negative; 'strip')"]


def test_soft_positive_flips_to_avoid():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], _ = apply_vocabulary([_k("preamble", "prefer", "Try to remove filler intros.")])
    assert (c.directive, c.strength) == ("avoid", "should")


def test_negative_subject_without_a_removal_verb_is_kept():
    # a real requirement: this preamble rule is one side of a fixture conflict
    from skillfetch.ingest.extract import apply_vocabulary

    text = "Always begin by restating the user's question in your own words."
    [c], notes = apply_vocabulary([_k("preamble", "require", text, artifact="response")])
    assert c.directive == "require" and notes == []


def test_implied_artifact_fills_any_but_never_overrides():
    from skillfetch.ingest.extract import apply_vocabulary

    out, notes = apply_vocabulary(
        [
            _k("emoji", "require", "Lead every heading with an emoji.", "in headers", line=5),
            _k("type-hints", "require", "Annotate everything.", artifact="markdown", line=6),
        ]
    )
    assert [c.scope.artifact for c in out] == ["markdown", "markdown"]
    assert notes == ["line 5: artifact any -> markdown (implied by `emoji` in headers)"]


def test_post_processing_leaves_the_hand_labels_unchanged():
    from conftest import load_corpus

    from skillfetch.ingest.extract import apply_vocabulary

    for sid, skill in load_corpus().items():
        out, notes = apply_vocabulary(skill.constraints)
        assert notes == [] and out == skill.constraints, sid


def test_extractor_applies_the_vocabulary_and_records_it():
    record, _ = run("no-emoji-docs", "no-emoji-docs.strip-as-require.json")
    assert [(c.subject, c.directive, c.scope.artifact) for c in record.constraints()] == [
        ("emoji", "forbid", "markdown"),
        ("trailing-whitespace", "forbid", "any"),
    ]
    assert record.adjusted == [
        "line 13: require -> forbid (`trailing-whitespace` is negative; 'strip')"
    ]


def test_prompt_maps_removal_verbs_to_bans():
    prompt = " ".join(system_prompt().split())  # independent of line wrapping
    assert "remove / strip / delete X → `forbid` X" in prompt
    assert "avoid X → `avoid` X (the soft ban); never `require` or `prefer`" in prompt


# --- closed conditions ------------------------------------------------------------------------


def _kc(condition, line=1):
    return Constraint.model_validate(
        {
            "subject": "commit-granularity",
            "directive": "require",
            "object": "squash",
            "scope": {"artifact": "commit-message", "condition": condition},
            "evidence": {"line_no": line, "text": "Squash each feature branch."},
        }
    )


def test_condition_outside_the_closed_set_is_removed_and_noted():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary([_kc("feature work", line=12)])
    assert c.scope.condition is None
    assert notes == [
        "line 12: condition 'feature work' -> null (not a language, framework or file type)"
    ]


def test_condition_inside_the_closed_set_is_kept():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary([_kc("django migrations")])
    assert c.scope.condition == "django migrations" and notes == []


def test_prompt_defines_closed_conditions():
    prompt = " ".join(system_prompt().split())
    assert "language, framework or file type" in prompt
    assert "removed after extraction" in prompt


def test_prompt_reads_scope_from_the_evidence_line_only():
    prompt = " ".join(system_prompt().split())
    assert "from the evidence line only" in prompt
    assert '"wherever", "everywhere", "anywhere"' in prompt
