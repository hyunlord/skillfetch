"""OpenAI-compatible backend and credential handling (no network)."""

import json
import os
from pathlib import Path

import pytest
from conftest import SKILLS_DIR, FakeBadRequest, FakeOpenAIClient, write_skill

import skillfetch.ingest.backends as backends_mod
from skillfetch.cli import main
from skillfetch.ingest.backends import OpenAICompatBackend, backend_key, parse_model
from skillfetch.ingest.credentials import openai_api_key, redact
from skillfetch.ingest.extract import Extractor, MissingCredentials, Usage

RESP = Path(__file__).parent.parent / "fixtures" / "extract" / "responses" / "openai"


def rec(name):
    return json.loads((RESP / name).read_text())


def run(*responses, official=True):
    client = FakeOpenAIClient(*[rec(r) if isinstance(r, str) else r for r in responses])
    backend = OpenAICompatBackend(client, "gpt-test", official=official)
    record = Extractor(backend).extract(SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64)
    return record, client


# --- requests and responses -------------------------------------------------------------------


def test_request_uses_strict_json_schema_and_a_system_message():
    record, client = run("commit-squash.ok.json")
    [req] = client.requests
    assert req["model"] == "gpt-test"
    assert [m["role"] for m in req["messages"]] == ["system", "user"]
    fmt = req["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["additionalProperties"] is False
    assert req["temperature"] == 0 and "max_completion_tokens" in req
    assert record.status == "ok" and record.model == "openai/gpt-test"


def test_compat_servers_get_max_tokens():
    _, client = run("commit-squash.ok.json", official=False)
    assert "max_tokens" in client.requests[0] and "max_completion_tokens" not in client.requests[0]


def test_usage_separates_cached_prompt_tokens():
    record, _ = run("commit-squash.ok.json")
    assert record.usage == Usage(
        input_tokens=3610 - 2304, output_tokens=412, cache_read_input_tokens=2304
    )


def test_refusal_is_not_retried():
    record, client = run("refusal.json")
    assert record.status == "extract_failed" and len(client.requests) == 1
    assert record.error == "refused (I can't help with that.)"


def test_truncated_output_goes_through_the_same_retry_path():
    record, client = run("length.json", "commit-squash.ok.json")
    assert record.status == "ok"
    assert [a.stop_reason for a in record.attempts] == ["max_tokens", "end_turn"]
    assert [m["role"] for m in client.requests[1]["messages"]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]


def test_unsupported_temperature_is_dropped_and_remembered():
    ok = rec("commit-squash.ok.json")
    client = FakeOpenAIClient(FakeBadRequest("temperature"), ok, ok)
    backend = OpenAICompatBackend(client, "gpt-reasoner")
    for _ in range(2):
        Extractor(backend).extract(SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64)
    assert ["temperature" in r for r in client.requests] == [True, False, False]


def test_unsupported_max_completion_tokens_falls_back():
    client = FakeOpenAIClient(FakeBadRequest("max_completion_tokens"), rec("commit-squash.ok.json"))
    Extractor(OpenAICompatBackend(client, "m")).extract(
        SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64
    )
    assert "max_tokens" in client.requests[1] and "max_completion_tokens" not in client.requests[1]


def test_other_bad_requests_propagate():
    client = FakeOpenAIClient(FakeBadRequest("response_format"))
    with pytest.raises(FakeBadRequest):
        Extractor(OpenAICompatBackend(client, "m")).extract(
            SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64
        )


# --- model specs and keys -----------------------------------------------------------------------


def test_keys_carry_the_provider_and_compat_host():
    assert parse_model("openai/gpt-test") == ("openai", "gpt-test")
    assert backend_key("openai/gpt-test") == "openai/gpt-test"
    assert backend_key("openai/llama3", "http://localhost:8000/v1") == (
        "openai-compat+localhost:8000/llama3"
    )
    with pytest.raises(ValueError):
        backend_key("anthropic/claude-sonnet-5", "http://localhost:8000/v1")


# --- credentials ----------------------------------------------------------------------------------

SECRET = "sk-proj-THISisNOTaREALkey0123456789"


def _creds(tmp_path, body):
    path = tmp_path / ".rnd_creds.env"
    path.write_text(body)
    return path


def test_key_from_env_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    assert openai_api_key(_creds(tmp_path, f"OPEN_API_KEY={SECRET}\n")) == "from-env"


def test_key_from_creds_file_reads_only_that_variable(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = _creds(tmp_path, f"OTHER_SECRET=hunter2\nexport OPEN_API_KEY={SECRET}\n")
    before = dict(os.environ)
    assert openai_api_key(path) == SECRET
    assert dict(os.environ) == before  # nothing loaded into the process environment


def test_no_key_anywhere(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert openai_api_key(_creds(tmp_path, "OTHER=x\n")) is None
    assert openai_api_key(tmp_path / "missing.env") is None


def test_redact_masks_the_key_and_key_shaped_strings():
    msg = f"Incorrect API key provided: {SECRET[:8]}****6789. Key {SECRET} rejected"
    out = redact(msg, SECRET)
    assert SECRET not in out and "sk-proj-" not in out and "6789" not in out


def test_openai_without_a_key_fails_before_any_request(tmp_path, monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingCredentials, match="OPEN_API_KEY"):
        backends_mod.make_backend("openai/gpt-test", creds_file=tmp_path / "none.env")


def test_cli_error_output_never_contains_the_key(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)

    class AuthenticationError(Exception):
        __module__ = "openai._exceptions"

    class Leaky:
        key = "openai/gpt-test"

        def complete(self, system, messages, schema):
            raise AuthenticationError(f"Incorrect API key provided: {SECRET}")

    monkeypatch.setattr(backends_mod, "make_backend", lambda spec, **kw: Leaky())
    write_skill(tmp_path / "skills", "one")
    args = ["ingest", str(tmp_path / "skills"), "--with-api", "--model", "openai/gpt-test"]
    assert main(args + ["--cache-dir", str(tmp_path / "c")]) == 1
    captured = capsys.readouterr()
    assert SECRET not in captured.err + captured.out
    assert "Claude API error" not in captured.err and "API error" in captured.err


# --- OpenRouter -------------------------------------------------------------------------------


class FakeOpenRouterClient(FakeOpenAIClient):
    def __init__(self, catalog, *responses):
        from types import SimpleNamespace

        super().__init__(*responses)
        self.models = SimpleNamespace(
            list=lambda: [SimpleNamespace(id=mid, supported_parameters=p) for mid, p in catalog]
        )


CATALOG = [
    ("openai/gpt-6-luna", ["structured_outputs", "response_format", "max_tokens"]),
    ("openai/gpt-oss-20b", ["structured_outputs", "response_format", "temperature", "max_tokens"]),
    ("some/plain-model", ["max_tokens", "temperature"]),
]


def test_openrouter_specs_and_keys():
    assert parse_model("openrouter/openai/gpt-6-luna") == ("openrouter", "openai/gpt-6-luna")
    assert backend_key("openrouter/openai/gpt-6-luna") == "openrouter/openai/gpt-6-luna"
    # the same server reached through --base-url gets the same cache key
    assert backend_key("openai/openai/gpt-6-luna", "https://openrouter.ai/api/v1") == (
        "openrouter/openai/gpt-6-luna"
    )


def test_openrouter_requires_parameter_support_and_reports_cost():
    client = FakeOpenRouterClient(CATALOG, rec("openrouter.commit-squash.ok.json"))
    backend = backends_mod.openrouter_backend(client, "openai/gpt-oss-20b")
    record = Extractor(backend).extract(SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64)
    [req] = client.requests
    assert req["extra_body"] == {"provider": {"require_parameters": True}}
    assert "max_tokens" in req and req["temperature"] == 0
    assert record.model == "openrouter/openai/gpt-oss-20b"
    assert record.cost_usd == pytest.approx(0.000231)  # billed amount, not the price table


def test_openrouter_omits_unsupported_temperature():
    client = FakeOpenRouterClient(CATALOG, rec("openrouter.commit-squash.ok.json"))
    backend = backends_mod.openrouter_backend(client, "openai/gpt-6-luna")
    Extractor(backend).extract(SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64)
    assert "temperature" not in client.requests[0]


def test_openrouter_rejects_unknown_or_unstructured_models():
    with pytest.raises(ValueError, match="not on OpenRouter"):
        backends_mod.openrouter_backend(FakeOpenRouterClient(CATALOG), "openai/nope")
    with pytest.raises(ValueError, match="structured outputs"):
        backends_mod.openrouter_backend(FakeOpenRouterClient(CATALOG), "some/plain-model")


def test_openrouter_key_from_env_or_creds_file(tmp_path, monkeypatch):
    from skillfetch.ingest.credentials import api_key

    path = _creds(tmp_path, f"OPEN_API_KEY={SECRET}\n")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert api_key("openrouter", path) == SECRET
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    assert api_key("openrouter", path) == "from-env"


# --- defaults ---------------------------------------------------------------------------------


def test_default_model_needs_no_api():
    # "no external API" rule: Claude Code answers; the API backends stay opt-in
    from skillfetch.ingest.extract import DEFAULT_MODEL
    from skillfetch.ingest.judge import DEFAULT_JUDGE_MODEL

    assert DEFAULT_MODEL == DEFAULT_JUDGE_MODEL == "claude-code/opus-5.5"
    assert backend_key() == "claude-code/opus-5.5"
    assert backend_key("openrouter/openai/gpt-6-luna") == "openrouter/openai/gpt-6-luna"


def test_clients_use_a_120_second_request_timeout(tmp_path, monkeypatch):
    openai = pytest.importorskip("openai")
    anthropic = pytest.importorskip("anthropic")
    seen = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            seen["openai"] = kwargs
            from types import SimpleNamespace

            self.models = SimpleNamespace(
                list=lambda: [
                    SimpleNamespace(
                        id="openai/gpt-6-luna", supported_parameters=["structured_outputs"]
                    )
                ]
            )

    class FakeAnthropic:
        def __init__(self, **kwargs):
            seen["anthropic"] = kwargs
            self.api_key, self.auth_token, self.credentials = "k", None, None

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    backends_mod.make_backend("openrouter/openai/gpt-6-luna")
    backends_mod.make_backend("anthropic/claude-sonnet-5")
    assert seen["openai"]["timeout"] == 120 and seen["anthropic"]["timeout"] == 120


def test_a_response_without_usage_counts_zero_tokens():
    response = rec("commit-squash.ok.json")
    response.pop("usage", None)
    response["usage"] = None
    record, _ = run(response)
    assert record.status == "ok"
    assert record.usage == Usage() and record.usage.reported_cost_usd is None


def test_an_empty_schema_asks_for_free_text_at_default_temperature():
    client = FakeOpenAIClient(rec("commit-squash.ok.json"))
    backend = OpenAICompatBackend(client, "gpt-test")
    backend.complete("sys", [{"role": "user", "content": "hi"}], {})
    [req] = client.requests
    assert "response_format" not in req and "temperature" not in req
