"""API failures during extraction: errors that reach skills.jsonl are redacted, and
rejected credentials stop the build instead of failing every skill one by one."""

import pytest
from conftest import write_skill

from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.ingest import run_extractions

KEY = "sk-ant-api03-REALLOOKINGkeyMaterial0123456789"


class _Raising:
    model = "anthropic/test"

    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def extract(self, skill_dir, skill_id, digest):
        self.calls += 1
        raise self.exc


class AuthenticationError(Exception):  # the SDKs' class name is what counts
    pass


def _items(tmp_path, n=3):
    return [(write_skill(tmp_path, f"s{i}"), f"s{i}", f"{i:064x}") for i in range(n)]


def test_per_skill_errors_are_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    errors = {}
    extractor = _Raising(RuntimeError(f"upstream said: bad request for key {KEY}"))
    out = run_extractions(_items(tmp_path), ExtractCache(tmp_path / "c"), extractor, 2, errors)
    assert out == {} and len(errors) == 3
    for text in errors.values():
        assert KEY not in text and "***" in text


def test_key_shaped_strings_are_redacted_even_when_unknown(tmp_path):
    errors = {}
    extractor = _Raising(RuntimeError("Incorrect API key provided: sk-proj-abcd****wxyz"))
    run_extractions(_items(tmp_path, 1), ExtractCache(tmp_path / "c"), extractor, 1, errors)
    [text] = errors.values()
    assert "abcd" not in text and "sk-***" in text


def test_rejected_credentials_stop_the_run(tmp_path):
    errors = {}
    extractor = _Raising(AuthenticationError("invalid x-api-key"))
    with pytest.raises(AuthenticationError):
        run_extractions(_items(tmp_path), ExtractCache(tmp_path / "c"), extractor, 1, errors)
    assert errors == {}
