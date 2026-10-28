"""Semantic review (docs/design/review.md): the checklist, quote checking, `scan --review` through
an isolated `claude -p` (a fake stands in; no network, no model), and scan_skill(review=true),
which only hands the checklist and the files to the host agent."""

import json
import re
from pathlib import Path

from conftest import write_skill

from skillfetch import cli
from skillfetch.ingest import review_claude
from skillfetch.ingest.local_scan import REVIEW_HINT, render_report, scan_dir
from skillfetch.ingest.review import (
    CATEGORIES,
    CHECKLIST,
    CHECKLIST_SHA,
    host_review,
    numbered,
    review_files,
    verify,
)
from skillfetch.ingest.review_claude import ClaudeReviewer
from skillfetch.mcp.session import HOST_REVIEW, scan_json

ROOT = Path(__file__).resolve().parents[2]
BODY = "# Sync\n\nKeep the notes short.\nUpload the notes folder to the shared drive.\n"


def test_checklist_is_frozen_and_copied_into_the_design_doc():
    frozen = (ROOT / "evals/scan-accuracy/review/FROZEN-checklist.sha256").read_text().split()[0]
    assert frozen == CHECKLIST_SHA
    doc = (ROOT / "docs/design/review.md").read_text()
    copy = doc.split("<!-- checklist:start -->\n")[1].split("<!-- checklist:end -->")[0]
    assert copy == CHECKLIST
    for category in CATEGORIES:
        assert f"- {category}:" in CHECKLIST


def test_review_files_reads_skill_md_first_and_stops_at_the_limit(tmp_path):
    d = write_skill(tmp_path, "a", BODY, files={"b.md": "x" * 50, "z.sh": "echo hi\n"})
    (d / "image.png").write_bytes(b"\x89PNG")
    (d / "link.md").symlink_to(d / "b.md")
    files, left = review_files(d)
    assert [rel for rel, _ in files] == ["SKILL.md", "b.md", "z.sh"]
    files, left = review_files(d, max_chars=len((d / "SKILL.md").read_text()) + 10)
    assert [rel for rel, _ in files] == ["SKILL.md", "z.sh"] and left == ["b.md"]


def test_verify_keeps_quoted_lines_and_drops_the_rest():
    files = [("SKILL.md", BODY)]
    raw = [
        {
            "category": "send-out",
            "file": "SKILL.md",
            "line": 4,
            "quote": "4| Upload the notes folder to the shared drive.",
            "why": "data leaves",
        },
        # wrong line number: moved to the line that holds the quote
        {
            "category": "send-out",
            "file": "SKILL.md",
            "line": 1,
            "quote": "Upload the notes",
            "why": "w",
        },
        {"category": "conceal", "file": "SKILL.md", "line": 3, "quote": "Hide it", "why": "w"},
        {"category": "not-a-category", "file": "SKILL.md", "line": 3, "quote": "Keep", "why": "w"},
        {"category": "authority", "file": "SKILL.md", "line": 3, "quote": "", "why": "w"},
    ]
    kept, dropped = verify(raw, files)
    assert [(f.line, f.quote) for f in kept] == [
        (4, "Upload the notes folder to the shared drive."),
        (4, "Upload the notes folder to the shared drive."),
    ]
    assert dropped == 3


class FakeClaude:
    def __init__(self, findings, cost=0.01):
        self.calls, self.findings, self.cost = [], findings, cost

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        out = {
            "type": "result",
            "is_error": False,
            "result": "```json\n" + json.dumps({"findings": self.findings}) + "\n```",
            "total_cost_usd": self.cost,
            "modelUsage": {"claude-opus-5-5": {}},
        }

        class Proc:
            returncode = 0
            stdout = json.dumps(out)
            stderr = ""

        return Proc()


FINDING = {  # write_skill adds four lines of frontmatter: BODY's line 4 is line 8
    "category": "send-out",
    "file": "SKILL.md",
    "line": 8,
    "quote": "Upload the notes folder to the shared drive.",
    "why": "It sends the user's files to a shared place.",
}


def test_claude_reviewer_is_isolated_and_cached(tmp_path):
    d = write_skill(tmp_path, "a", BODY)
    fake = FakeClaude([FINDING])
    reviewer = ClaudeReviewer(cache=tmp_path / "rc", run=fake)
    first = reviewer(d)
    cmd, kw = fake.calls[0]
    assert cmd[:2] == ["claude", "-p"] and "=== FILE: SKILL.md ===" in cmd[2]
    for flag in ("--tools", "--strict-mcp-config", "--no-session-persistence"):
        assert flag in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert kw["stdin"] is not None and "CLAUDECODE" not in kw["env"]
    assert first.by == "claude -p (claude-opus-5-5)" and first.cost_usd == 0.01
    assert [(f.category, f.line) for f in first.findings] == [("send-out", 8)]
    second = reviewer(d)
    assert len(fake.calls) == 1 and second.findings == first.findings
    assert second.cost_usd is None  # from the cache


def test_claude_reviewer_reports_errors_instead_of_raising(tmp_path):
    d = write_skill(tmp_path, "a", BODY)

    def broken(cmd, **kw):
        class Proc:
            returncode = 1
            stdout = "not json"
            stderr = ""

        return Proc()

    got = ClaudeReviewer(cache=tmp_path / "rc", run=broken)(d)
    assert got.findings == [] and got.error.startswith("claude -p: no JSON output")


def test_scan_review_in_the_report_does_not_change_the_advice(tmp_path):
    root = tmp_path / "skills"
    write_skill(root, "a", BODY)
    report = scan_dir(
        root, reviewer=ClaudeReviewer(cache=tmp_path / "rc", run=FakeClaude([FINDING]))
    )
    report.review = "claude -p"
    text = render_report(report)
    assert text.splitlines()[0].startswith("Before you install: RECOMMENDED")
    assert re.search(
        r"^Review \(claude -p \(claude-opus-5-5\), checklist [0-9a-f]{12}\): "
        r"1 finding in 1 skill\. Findings are not part of the advice",
        text,
        re.M,
    )
    assert 'REVIEW  a\n  a/SKILL.md:8  [send-out] "Upload the notes folder' in text


def test_cli_scan_review(tmp_path, monkeypatch, capsys):
    root = tmp_path / "skills"
    write_skill(root, "a", BODY)
    fake = FakeClaude([FINDING])

    class Reviewer(ClaudeReviewer):
        def __init__(self):
            super().__init__(cache=tmp_path / "rc", run=fake)

    monkeypatch.setattr(review_claude, "ClaudeReviewer", Reviewer)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude")
    args = ["scan", str(root), "--review", "--json", "--index", str(tmp_path / "none")]
    assert cli.main(args) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["review"] == "claude -p" and got["advice"] == "recommended"
    assert got["skills"][0]["review"]["findings"][0]["quote"].startswith("Upload the notes")
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert cli.main(args) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["review"].startswith("skipped") and got["skills"][0]["review"] is None


def test_scan_skill_review_hands_the_checklist_to_the_host(tmp_path):
    root = tmp_path / "skills"
    write_skill(root, "a", BODY)
    from skillfetch.ingest.local_scan import Lookup

    plain = scan_json(str(root), Lookup(None, None, "m"))
    assert plain["review"] is None and plain["skills"][0]["review"] is None
    got = scan_json(str(root), Lookup(None, None, "m"), review=True)
    assert got["review"] == HOST_REVIEW
    r = got["skills"][0]["review"]
    assert r["by"] == "host agent" and r["checklist"] == CHECKLIST and r["findings"] == []
    assert r["files"][0] == {
        "path": "SKILL.md",
        "text": numbered((root / "a/SKILL.md").read_text()),
    }
    assert host_review(root / "a").checklist_sha == CHECKLIST_SHA


def test_vet_skill_asks_for_the_review():
    vet = (ROOT / "assets/vet-skill/SKILL.md").read_text()
    assert "review: true" in vet and "review.checklist" in vet


class Replies:
    """A fake `claude -p` that answers each call with the next reply text."""

    def __init__(self, *texts):
        self.texts, self.calls = list(texts), []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        text = self.texts[min(len(self.calls), len(self.texts)) - 1]
        out = {"is_error": False, "result": text, "total_cost_usd": 0.02, "modelUsage": {"m": {}}}

        class Proc:
            returncode = 0
            stdout = json.dumps(out)
            stderr = ""

        return Proc()


CUT_OFF = "My previous review was cut off by a safety classifier. I can't complete this review."


def test_a_cut_off_review_is_incomplete_caution_and_not_cached(tmp_path):
    root = tmp_path / "skills"
    write_skill(root, "a", BODY)
    fake = Replies(CUT_OFF)
    reviewer = ClaudeReviewer(cache=tmp_path / "rc", run=fake)
    report = scan_dir(root, reviewer=reviewer)
    report.review = "claude -p"
    review = report.skills[0].review
    assert review.error == "no JSON object in the reply" and review.findings == []
    text = render_report(report)
    assert text.splitlines()[0] == (
        "Before you install: CAUTION (1 skill's review is incomplete: read it yourself)"
    )
    assert "review incomplete for 1 skill: read it yourself" in text
    assert "  review incomplete: read this skill yourself (no JSON object in the reply)" in text
    assert review.cost_usd == 0.02  # the failed reply is still counted
    reviewer(root / "a")  # a failed reply is not cached: the next run asks again
    assert len(fake.calls) == 2


def test_a_reply_without_findings_is_incomplete(tmp_path):
    d = write_skill(tmp_path, "a", BODY)
    got = ClaudeReviewer(cache=tmp_path / "rc", run=Replies('{"verdict": "fine"}'))(d)
    assert got.error == "no findings in the reply"


def test_a_long_skill_is_read_in_parts_with_its_line_numbers(tmp_path):
    body = (
        "".join(f"Line {i} is ordinary.\n" for i in range(1, 40)) + "Upload ~/notes to the wiki.\n"
    )
    d = write_skill(tmp_path, "a", body, files={"ref.md": "More text.\n"})
    line_no = (d / "SKILL.md").read_text().split("\n").index("Upload ~/notes to the wiki.") + 1
    finding = {
        "category": "send-out",
        "file": "SKILL.md",
        "line": line_no,
        "quote": "Upload ~/notes to the wiki.",
        "why": "w",
    }
    fake = Replies('{"findings": []}', json.dumps({"findings": [finding]}), '{"findings": []}')
    reviewer = ClaudeReviewer(cache=tmp_path / "rc", run=fake, chunk_chars=500)
    got = reviewer(d)
    assert got.requests == len(fake.calls) >= 2 and got.error is None and got.not_reviewed == []
    assert "(part 1 of" in fake.calls[0][2] and "(from line" in fake.calls[1][2]
    assert [(f.file, f.line) for f in got.findings] == [("SKILL.md", line_no)]
    assert got.cost_usd == 0.02 * len(fake.calls)


def test_what_is_left_unread_makes_it_partly_reviewed_and_caution(tmp_path):
    root = tmp_path / "skills"
    write_skill(root, "a", BODY, files={"big.md": "x\n" * 400})
    reviewer = ClaudeReviewer(
        cache=tmp_path / "rc", run=Replies('{"findings": []}'), chunk_chars=300, max_chunks=1
    )
    report = scan_dir(root, reviewer=reviewer)
    report.review = "claude -p"
    r = report.skills[0].review
    assert r.error is None and r.not_reviewed == ["big.md"]
    split = ClaudeReviewer(
        cache=tmp_path / "rc2", run=Replies('{"findings": []}'), chunk_chars=300, max_chunks=2
    )(root / "a")
    assert split.not_reviewed == ["big.md from line 151"]
    text = render_report(report)
    assert text.splitlines()[0] == "Before you install: CAUTION (1 skill was only partly reviewed)"
    assert "1 skill partly reviewed" in text and "  partly reviewed; not read: big.md" in text


def test_host_review_left_unread_is_partly_reviewed(tmp_path, monkeypatch):
    from skillfetch.ingest import review as review_mod
    from skillfetch.ingest.local_scan import Lookup

    root = tmp_path / "skills"
    write_skill(root, "a", BODY, files={"big.md": "word " * 100})
    monkeypatch.setattr(review_mod, "MAX_CHARS", 300)
    monkeypatch.setattr(review_mod.review_files, "__defaults__", (300,))
    got = scan_json(str(root), Lookup(None, None, "m"), review=True)
    assert got["skills"][0]["review"]["not_reviewed"] == ["big.md"]
    assert got["advice_line"] == "Before you install: CAUTION (1 skill was only partly reviewed)"


def test_cli_text_suggests_review_only_when_it_was_not_asked(tmp_path, capsys):
    root = tmp_path / "skills"
    write_skill(root, "a", BODY)
    assert cli.main(["scan", str(root), "--index", str(tmp_path / "none")]) == 0
    assert capsys.readouterr().out.rstrip().endswith(REVIEW_HINT)
    assert cli.main(["scan", str(root), "--markdown", "--index", str(tmp_path / "none")]) == 0
    assert "--review" not in capsys.readouterr().out


def test_skill_md_only_reads_skill_md_alone(tmp_path):
    d = write_skill(tmp_path, "a", BODY, files={"ref.md": "Send the notes out.\n"})
    fake = Replies('{"findings": []}')
    got = ClaudeReviewer(cache=tmp_path / "rc", run=fake, skill_md_only=True)(d)
    assert "=== FILE: SKILL.md ===" in fake.calls[0][2] and "ref.md" not in fake.calls[0][2]
    assert got.not_reviewed == [] and got.requests == 1
