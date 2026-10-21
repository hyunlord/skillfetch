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
