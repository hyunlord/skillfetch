"""`scan --claude-code`: extraction through an isolated `claude -p` (the user's Claude Code
login). A fake `claude` stands in; no network, no API."""

import json
import shutil

import pytest
from conftest import SKILLS_DIR, oracle

from skillfetch.cli import main
from skillfetch.ingest.claude_code import ClaudeCliBackend, first_json
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.local_scan import Lookup, render_report, scan_dir
from skillfetch.ingest.skillfile import CONSTRAINTS_FILE


class FakeClaude:
    """`claude -p ... --output-format json`: answers with the oracle extraction for the
    fixture skill named in the prompt, inside a ```json fence as a model would."""

    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if self.error:
            out = {"type": "result", "is_error": True, "result": self.error}
        else:
            text = oracle({"messages": [{"content": cmd[2]}]})["content"][0]["text"]
            out = {"type": "result", "is_error": False, "result": f"```json\n{text}\n```"}

        class Proc:
            returncode = 0
            stdout = json.dumps(out)
            stderr = ""

        return Proc()


def _copy(tmp_path, names=("atomic-commits", "commit-squash")):
    root = tmp_path / "skills"
    for name in names:
        shutil.copytree(SKILLS_DIR / name, root / name)
        (root / name / CONSTRAINTS_FILE).unlink()
    return root


def test_unknown_skills_are_extracted_through_claude_p(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    fake = FakeClaude()
    backend = ClaudeCliBackend("opus-5.5", queue=tmp_path / "queue", run=fake)
    extractor = Extractor(backend)
    lookup = Lookup(
        cache=ExtractCache(tmp_path / "cache"), model=extractor.model, extractor=extractor
    )
    report = scan_dir(_copy(tmp_path), lookup)
    assert {s.constraints_source for s in report.skills} == {"extracted"}
    assert any(f.kind == "conflict" for f in report.findings)
    cmd, kw = fake.calls[0]
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--tools") + 1] == "" and "--strict-mcp-config" in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert "--no-session-persistence" in cmd
    assert "CLAUDECODE" not in kw["env"]  # not seen as a nested session
    assert kw["cwd"] != tmp_path  # a scratch directory
    assert len(list((tmp_path / "queue" / "answers").glob("*.json"))) == 2
    assert not list((tmp_path / "queue" / "pending").glob("*.json"))
    # a second run with an empty cache reads the stored answers; claude is not called again
    again = FakeClaude(error="should not be called")
    extractor2 = Extractor(ClaudeCliBackend("opus-5.5", queue=tmp_path / "queue", run=again))
    lookup2 = Lookup(
        cache=ExtractCache(tmp_path / "cache2"), model=extractor2.model, extractor=extractor2
    )
    rerun = scan_dir(tmp_path / "skills", lookup2)
    assert {s.constraints_source for s in rerun.skills} == {"extracted"}
    assert len(fake.calls) == 2 and not again.calls


def test_a_failed_claude_call_is_reported_per_skill(tmp_path):
    extractor = Extractor(
        ClaudeCliBackend("opus-5.5", queue=tmp_path / "q", run=FakeClaude(error="not logged in"))
    )
    lookup = Lookup(
        cache=ExtractCache(tmp_path / "cache"), model=extractor.model, extractor=extractor
    )
    report = scan_dir(_copy(tmp_path), lookup)
    assert report.analyzed == []
    notes = {s.constraints_note for s in report.skills}
    assert all("not logged in" in (n or "") for n in notes)


def test_first_json():
    assert first_json('text ```json\n{"a": 1}\n``` more') == {"a": 1}
    assert first_json('{"b": [1, 2]} trailing') == {"b": [1, 2]}
    with pytest.raises(ValueError):
        first_json("no object")


def test_cli_without_the_claude_binary_says_the_check_was_skipped(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    root = _copy(tmp_path)
    args = ["scan", str(root), "--claude-code", "--index", str(tmp_path / "no-index")]
    assert main(args + ["--cache-dir", str(tmp_path / "c")]) == 0
    out = capsys.readouterr().out
    assert "skipped: --claude-code needs the `claude` CLI on PATH" in out
    assert "contradiction check skipped for 2 skills" in out


def test_cli_claude_code_and_with_api_exclude_each_other(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["scan", str(tmp_path), "--claude-code", "--with-api"])
    assert "not allowed with" in capsys.readouterr().err


def test_render_mentions_claude_code_when_skills_were_skipped(tmp_path):
    text = render_report(scan_dir(_copy(tmp_path)))
    assert "add `--claude-code`" in text and "no API key" in text
