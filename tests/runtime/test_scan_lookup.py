"""`skillfetch scan` takes constraints from the index, the extract cache or a fresh extraction
when a skill has no constraints.json (an installed copy of a public skill has none)."""

import json
import shutil

from conftest import OracleClient
from indexkit import make_index, skill_id

from skillfetch.cli import main
from skillfetch.index.loader import Index
from skillfetch.ingest.backends import AnthropicBackend
from skillfetch.ingest.build import write_pairs
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.judge_run import import_judgments
from skillfetch.ingest.local_scan import Lookup, render_report, scan_dir
from skillfetch.ingest.skillfile import CONSTRAINTS_FILE

NAMES = ("commit-squash", "atomic-commits", "verbose-logging", "quiet-tests")


def _installed(tmp_path, names=NAMES):
    """The indexed skill folders as a user would have them: no constraints.json."""
    root = tmp_path / "installed"
    for name in names:
        shutil.copytree(tmp_path / "src" / "skills" / name, root / name)
        (root / name / CONSTRAINTS_FILE).unlink()
    return root


def _by_id(report):
    return {s.id: s for s in report.skills}


def test_without_a_lookup_installed_skills_are_skipped(tmp_path):
    make_index(tmp_path, NAMES)
    report = scan_dir(_installed(tmp_path))
    assert report.analyzed == [] and len(report.skipped) == 4


def test_constraints_come_from_the_index_by_content_hash(tmp_path):
    index_dir = make_index(tmp_path, NAMES)
    report = scan_dir(_installed(tmp_path), Lookup(index=Index.load(index_dir)))
    by_id = _by_id(report)
    assert {s.constraints_source for s in report.skills} == {"index"}
    assert by_id["commit-squash"].index_id == skill_id(index_dir, "commit-squash")
    assert ("atomic-commits", "commit-squash") in {
        (f.a, f.b) for f in report.findings if f.kind == "conflict"
    }
    # evidence is quoted from the local files, under the local ids
    for f in report.findings:
        assert f.a in by_id and f.b in by_id
    text = render_report(report)
    assert text.startswith("Before you install: NOT RECOMMENDED (1 pair of skills gives opposite")
    assert f"\n\nskillfetch scan {tmp_path / 'installed'}\n" in text
    assert "Contradiction check: 4 of 4 skills analyzed (index 4)." in text
    assert f"index: {index_dir} (4 skills" in text


def test_index_evidence_must_match_the_local_lines(tmp_path):
    index = Index.load(make_index(tmp_path, NAMES))
    sid = skill_id(index.root, "commit-squash")
    c = index.constraints[sid][0]
    index.constraints[sid][0] = c.model_copy(
        update={"evidence": c.evidence.model_copy(update={"text": "not in the file"})}
    )
    report = scan_dir(_installed(tmp_path), Lookup(index=index))
    record = _by_id(report)["commit-squash"]
    assert record.constraints_source == "invalid" and "not in the file" in record.constraints_error
    assert "commit-squash" in report.skipped


def test_constraints_come_from_the_extract_cache(tmp_path):
    index_dir = make_index(tmp_path, NAMES)
    model = Index.load(index_dir).manifest["extract_model"]
    lookup = Lookup(cache=ExtractCache(tmp_path / "cache"), model=model)
    report = scan_dir(_installed(tmp_path), lookup)
    assert {s.constraints_source for s in report.skills} == {"cache"}
    assert report.index is None


def test_unknown_skills_are_extracted_with_an_extractor(tmp_path):
    make_index(tmp_path, NAMES)
    extractor = Extractor(AnthropicBackend(OracleClient(), "claude-sonnet-5"))
    cache = ExtractCache(tmp_path / "fresh-cache")
    report = scan_dir(
        _installed(tmp_path), Lookup(cache=cache, model=extractor.model, extractor=extractor)
    )
    assert {s.constraints_source for s in report.skills} == {"extracted"}
    rerun = scan_dir(tmp_path / "installed", Lookup(cache=cache, model=extractor.model))
    assert {s.constraints_source for s in rerun.skills} == {"cache"}


def test_independent_verdicts_hide_index_warnings(tmp_path):
    index_dir = make_index(tmp_path, NAMES)
    installed = _installed(tmp_path)
    before = scan_dir(installed, Lookup(index=Index.load(index_dir)))
    assert ("quiet-tests", "verbose-logging") in {
        tuple(sorted((f.a, f.b))) for f in before.findings if f.kind in ("tension", "needs_review")
    }
    verbose, quiet = skill_id(index_dir, "verbose-logging"), skill_id(index_dir, "quiet-tests")
    row = {
        "pair": f"{verbose}|{quiet}",
        "rules": "needs_review",
        "row": "12 scope carve-out",
        "verdict": "independent",
        "reason": "r",
        "ambiguous_together": False,
        "confidence": 0.9,
        "error": None,
        "evidence": [],
    }
    judgments = tmp_path / "j.jsonl"
    judgments.write_text(json.dumps(row) + "\n")
    write_pairs(index_dir, import_judgments(judgments, "judge/x", 1))
    after = scan_dir(installed, Lookup(index=Index.load(index_dir)))
    assert len(after.findings) == len(before.findings) - 1
    assert after.suppressed_by_judge == 1
    assert "judge verdict for the pair is `independent`" in render_report(after)


def test_cli_scan_reads_the_index(tmp_path, capsys):
    index_dir = make_index(tmp_path, NAMES)
    installed = _installed(tmp_path)
    args = ["scan", str(installed), "--cache-dir", str(tmp_path / "empty")]
    assert main([*args, "--index", str(index_dir)]) == 0
    out = capsys.readouterr().out
    assert "CONFLICT  atomic-commits ⟷ commit-squash" in out

    assert main([*args, "--index", str(tmp_path / "no-index")]) == 0
    out = capsys.readouterr().out
    assert "index: none (run `skillfetch sync`" in out
    assert "contradiction check skipped for 4 skills" in out
    assert "add `--claude-code`" in out
    assert "skillfetch sync" in out


def test_cli_scan_refuses_a_tampered_index(tmp_path, capsys):
    index_dir = make_index(tmp_path, NAMES)
    with (index_dir / "constraints.jsonl").open("a") as f:
        f.write("\n")
    assert main(["scan", str(_installed(tmp_path)), "--index", str(index_dir)]) == 2
    assert "does not match its manifest hash" in capsys.readouterr().err
