"""The claude-code backend: requests queued for Claude Code, answers cached as usual."""

import json

import pytest
from conftest import SKILLS_DIR, recorded

from skillfetch.ingest.backends import make_backend
from skillfetch.ingest.claude_code import ClaudeCodeBackend, PendingAnswer, request_sha
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.ingest import run_extractions


def test_factory_makes_a_claude_code_backend_without_credentials(tmp_path):
    backend = make_backend("claude-code/opus-5.5", creds_file=tmp_path / "none.env")
    assert isinstance(backend, ClaudeCodeBackend) and backend.key == "claude-code/opus-5.5"


def test_a_request_is_queued_then_answered(tmp_path):
    backend = ClaudeCodeBackend("opus-5.5", tmp_path)
    messages = [{"role": "user", "content": "hi"}]
    with pytest.raises(PendingAnswer):
        backend.complete("system text", messages, {"type": "object"})
    sha = request_sha("system text", messages, {"type": "object"})
    pending = json.loads((tmp_path / "pending" / f"{sha}.json").read_text())
    assert pending["messages"] == messages and pending["model"] == "claude-code/opus-5.5"
    assert (tmp_path / "systems" / f"{pending['system_sha256']}.txt").read_text() == "system text"
    (tmp_path / "answers" / f"{sha}.json").parent.mkdir()
    (tmp_path / "answers" / f"{sha}.json").write_text(json.dumps({"text": '{"ok": true}'}))
    reply = backend.complete("system text", messages, {"type": "object"})
    assert reply.text == '{"ok": true}' and reply.usage.reported_cost_usd == 0.0


def test_extraction_through_the_queue_lands_in_the_usual_cache(tmp_path):
    queue, cache = tmp_path / "q", ExtractCache(tmp_path / "cache")
    extractor = Extractor(ClaudeCodeBackend("opus-5.5", queue))
    items = [(SKILLS_DIR / "commit-squash", "commit-squash", "0" * 64)]
    errors: dict[str, str] = {}
    assert run_extractions(items, cache, extractor, errors=errors) == {}
    assert errors["0" * 64].startswith("PendingAnswer")
    [pending] = (queue / "pending").glob("*.json")
    answer = recorded("commit-squash.ok.json")["content"][0]["text"]
    (queue / "answers").mkdir()
    (queue / "answers" / pending.name).write_text(json.dumps({"text": answer}))
    done = run_extractions(items, cache, extractor, errors={})
    record = done["0" * 64]
    assert record.status == "ok" and record.model == "claude-code/opus-5.5"
    assert cache.get("0" * 64, "claude-code/opus-5.5", SKILLS_DIR / "commit-squash") is not None
