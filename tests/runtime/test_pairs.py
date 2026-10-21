"""Judge verdicts stored with the index (pairs.jsonl) and used by resolve_set."""

import json

from indexkit import make_index, skill_id

from skillfetch.index.loader import Index
from skillfetch.ingest.build import write_pairs
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.judge_run import import_judgments
from skillfetch.mcp.session import Session

NAMES = ("verbose-logging", "quiet-tests", "commit-squash", "atomic-commits")


def _judgments(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def _row(a, b, verdict):
    return {
        "pair": f"{a}|{b}",
        "rules": "needs_review",
        "row": "12 scope carve-out",
        "verdict": verdict,
        "reason": "r",
        "ambiguous_together": False,
        "confidence": 0.9,
        "error": None,
        "evidence": [],
    }


def test_imported_verdicts_suppress_independent_warnings(tmp_path):
    root = make_index(tmp_path, NAMES)
    verbose, quiet = skill_id(root, "verbose-logging"), skill_id(root, "quiet-tests")
    session = Session(Index.load(root), extract_cache=ExtractCache(tmp_path / "xc"))
    assert len(session.resolve_set([verbose, quiet])["warnings"]) == 1

    report = _judgments(tmp_path / "judgments.jsonl", [_row(verbose, quiet, "independent")])
    rows = import_judgments(report, "openrouter/anthropic/claude-sonnet-5.5", 1)
    write_pairs(root, rows)
    index = Index.load(root)  # the manifest covers pairs.jsonl
    assert index.manifest["judged_pairs"] == 1 and "pairs.jsonl" in index.manifest["files"]
    out = Session(index, extract_cache=ExtractCache(tmp_path / "xc")).resolve_set([verbose, quiet])
    assert out["warnings"] == [] and out["suppressed_by_judge"] == 1


def test_a_rebuild_keeps_verdicts_whose_skills_are_unchanged(tmp_path):
    root = make_index(tmp_path, NAMES)
    verbose, quiet = skill_id(root, "verbose-logging"), skill_id(root, "quiet-tests")
    squash = skill_id(root, "commit-squash")
    write_pairs(
        root,
        import_judgments(
            _judgments(
                tmp_path / "j.jsonl",
                [
                    _row(verbose, quiet, "independent"),
                    _row(squash, "fx/gone@000000000000", "situational"),
                ],
            ),
            "judge/x",
            1,
        ),
    )
    root = make_index(tmp_path, NAMES)  # same content, rebuilt into the same out dir
    pairs = Index.load(root).pairs
    assert list(pairs) == [frozenset((verbose, quiet))]
