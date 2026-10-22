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
    ExtractRecord,
    ExtractResult,
    Usage,
    cost_usd,
    numbered,
    postprocess_fingerprint,
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


# Post-processing (validation, evidence, polarity, implied artifacts, object vocabulary,
# condition clauses, sections, per-line merge) runs on every cached answer at build time.
POSTPROCESS_SHA256 = "b3c40a2ca2ae646f8400a9fa58fcac6eb6b993a3913ac95b236b90f84006d603"


def test_post_processing_rules_are_pinned():
    assert postprocess_fingerprint() == POSTPROCESS_SHA256, (
        "a post-processing rule changed: cached answers will process differently, so "
        "rebuild the index and record what moved; then set "
        f"POSTPROCESS_SHA256 = {postprocess_fingerprint()!r}"
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
    assert set(constraint["properties"]) == set(Constraint.model_fields) - {
        "id",
        "section_heading",
        "fan_out",
    }


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


def test_object_raw_is_kept_and_never_compared():
    import json

    from skillfetch.resolve.relation import constraint_identity, constraint_relation

    response = recorded("commit-squash.ok.json")
    data = json.loads(response["content"][0]["text"])
    data["constraints"][0]["object_raw"] = "every feature into a single commit"
    response["content"][0]["text"] = json.dumps(data)
    record, _ = run("commit-squash", response)
    squash = record.constraints()[0]
    assert (squash.object, squash.object_raw) == ("squash", "every feature into a single commit")
    plain = squash.model_copy(update={"object_raw": None})
    assert constraint_identity(squash) == constraint_identity(plain)
    assert constraint_relation(squash, plain).value == "redundant"


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


@pytest.mark.parametrize(
    "subject, directive, text, want",
    [
        ("trailing-whitespace", "require", "Never strip trailing whitespace.", "require"),
        ("preamble", "require", "Do not remove the preamble.", "require"),
        ("preamble", "require", "Don't ever remove the preamble.", "require"),
        ("trailing-whitespace", "require", "Avoid stripping trailing whitespace.", "require"),
        ("trailing-whitespace", "prefer", "Commit without removing trailing spaces.", "prefer"),
        ("trailing-whitespace", "require", "Strip trailing whitespace.", "forbid"),
        ("preamble", "require", "Remove the preamble.", "forbid"),
        # avoid is not a removal verb: the model already says `avoid` for avoid-rules
        ("preamble", "prefer", "Avoid a preamble when the answer is short.", "prefer"),
    ],
)
def test_a_negated_removal_verb_keeps_the_directive(subject, directive, text, want):
    from skillfetch.ingest.extract import apply_vocabulary

    [c], _ = apply_vocabulary([_k(subject, directive, text)])
    assert c.directive == want


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


def test_a_clause_condition_is_removed_and_noted():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary([_kc("when they make the output friendlier", line=12)])
    assert c.scope.condition is None
    assert notes == [
        "line 12: condition 'when they make the output friendlier' -> null (reads like a clause)"
    ]


@pytest.mark.parametrize("condition", ["django migrations", "docx", "latex", "feature work"])
def test_other_conditions_are_kept(condition):
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary([_kc(condition)])
    assert c.scope.condition == condition and notes == []


def test_prompt_defines_conditions():
    prompt = " ".join(system_prompt().split())
    assert "language, framework, library or file type" in prompt
    assert "removed after extraction" in prompt


def test_prompt_reads_scope_from_the_evidence_line_only():
    prompt = " ".join(system_prompt().split())
    assert "from the evidence line only" in prompt
    assert '"wherever", "everywhere", "anywhere"' in prompt


# --- free-text subjects containing a vocabulary term --------------------------------------------


def _ks(subject, obj=None, artifact="any", phase="any", line=1):
    return Constraint.model_validate(
        {
            "subject": subject,
            "directive": "forbid",
            "object": obj,
            "scope": {"artifact": artifact, "phase": phase},
            "evidence": {"line_no": line, "text": "t"},
        }
    )


def test_subject_with_scope_words_is_normalized_to_the_term():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary([_ks("test logging", artifact="tests", phase="test", line=12)])
    assert c.subject == "logging"
    assert notes == [
        "line 12: subject 'test logging' -> `logging` (remaining words are in the scope)"
    ]


def test_commit_message_words_are_covered_by_the_artifact():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], _ = apply_vocabulary([_ks("commit message emoji", artifact="commit-message")])
    assert c.subject == "emoji"


def test_narrower_subject_keeps_its_free_text():
    # the escape hatch: "request body logging" must not become a blanket logging ban
    from skillfetch.ingest.extract import apply_vocabulary

    [c], notes = apply_vocabulary([_ks("request body logging")])
    assert c.subject == "request body logging" and notes == []


def test_normalization_respects_the_term_objects():
    from skillfetch.ingest.extract import apply_vocabulary

    [c], _ = apply_vocabulary([_ks("test logging", obj="stack traces", artifact="tests")])
    assert c.subject == "test logging"  # `logging` does not allow that object


def test_prompt_keeps_situations_out_of_the_subject():
    # v4 dropped situations from the rule ("Once a team is selected, ... do not ask for
    # separate confirmation" -> blanket forbid ask-before-acting); v5 put them into long
    # free-text subjects, which hid real relations. v6: subject <= 3 words, situation in
    # object_raw.
    prompt = system_prompt()
    assert "## situations" in prompt
    assert "A subject has at\nmost three words" in prompt


# --- subject cap and clause split (v6) ------------------------------------------------------


def _with_subject(subject, index=1):
    import json

    response = recorded("commit-squash.ok.json")
    data = json.loads(response["content"][0]["text"])
    data["constraints"][index]["subject"] = subject
    response["content"][0]["text"] = json.dumps(data)
    return response


def test_a_clause_in_the_subject_is_split_off():
    record, client = run("commit-squash", _with_subject("branch name when the ticket exists"))
    assert len(client.requests) == 1
    branch = record.constraints()[1]
    assert branch.subject == "branch name"
    assert branch.object_raw == "when the ticket exists"
    assert record.adjusted[0] == (
        f"line {branch.evidence.line_no}: subject 'branch name when the ticket exists' -> "
        "'branch name', clause 'when the ticket exists' -> condition and object_raw"
    )


def test_vocabulary_and_order_subjects_are_not_split():
    from skillfetch.ingest.extract import split_subject_clause

    assert split_subject_clause({"subject": "review-before-merge", "directive": "require"}) is None
    order = {"subject": "tests before code", "directive": "order"}
    assert split_subject_clause(order) is None and order["subject"] == "tests before code"


def test_a_long_subject_is_sent_back_once():
    long = _with_subject("branch names for every new feature")
    record, client = run("commit-squash", long, "commit-squash.ok.json")
    assert record.status == "ok" and len(client.requests) == 2
    retry = client.requests[1]["messages"][-1]["content"]
    assert "subject 'branch names for every new feature' has 6 words" in retry


def test_a_long_subject_after_the_retry_drops_that_constraint_only():
    long = _with_subject("branch names for every new feature")
    record, _ = run("commit-squash", long, long)
    assert record.status == "ok"
    assert [c.subject for c in record.constraints()] == ["commit-granularity"]
    assert [d.reason for d in record.dropped] == ["subject over 3 words after the retry"]


def test_stored_records_load_without_the_extraction_checks():
    # the cap applies to model output, not to cache entries written by earlier versions
    long = {
        "subject": "table of contents headings",
        "directive": "forbid",
        "evidence": {"line_no": 3, "text": "x"},
    }
    data = {
        "summary": "",
        "keywords": [],
        "tags": {"languages": [], "frameworks": [], "phase": [], "domain": []},
        "synthetic_queries": [],
        "constraints": [long],
        "consumes": [],
        "produces": [],
        "requires_tools": [],
    }
    assert ExtractResult.model_validate(data).constraints[0].subject == long["subject"]


def test_a_vocabulary_violation_after_the_retry_drops_that_constraint_only():
    bad = "concise-responses.disallowed-object.json"
    record, client = run("concise-responses", bad, bad)
    assert record.status == "ok" and len(client.requests) == 2
    assert any("after the retry" in d.reason for d in record.dropped)
    assert all(c.object is None for c in record.constraints() if c.subject == "summary-at-end")


def test_postprocess_takes_the_last_attempt_as_a_last_attempt():
    from skillfetch.ingest.extract import postprocess

    failed = ExtractRecord(
        extract_version=EXTRACT_VERSION,
        model="anthropic/claude-sonnet-5",
        content_hash="0" * 64,
        skill_id="concise-responses",
        status="extract_failed",
        error="object not allowed",
        attempts=[
            {
                "stop_reason": "end_turn",
                "text": recorded("concise-responses.disallowed-object.json")["content"][0]["text"],
                "usage": {},
            }
        ],
    )
    text = (SKILLS_DIR / "concise-responses" / "SKILL.md").read_text()
    fixed = postprocess(failed, text)
    # one attempt, so it is the last: the disallowed object is dropped, the skill kept
    assert fixed.status == "ok" and fixed.error is None
    assert any("after the retry" in d.reason for d in fixed.dropped)
    assert postprocess(fixed, text) == fixed  # deterministic, idempotent
