"""CLI entry point."""

import json
import subprocess
import sys

from conftest import SKILLS_DIR

from skillfetch.cli import main


def test_scan_prints_text_report(capsys):
    assert main(["scan", str(SKILLS_DIR)]) == 0
    out = capsys.readouterr().out
    assert "CONFLICT  atomic-commits ⟷ commit-squash" in out
    assert out.rstrip().splitlines()[-1].startswith("summary: 19 conflict")


def test_scan_json(capsys):
    assert main(["scan", str(SKILLS_DIR), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"root", "skills", "duplicates", "findings", "analyzed", "skipped"} <= set(data)
    assert sum(f["kind"] == "conflict" for f in data["findings"]) == 19


def test_scan_missing_dir(tmp_path, capsys):
    assert main(["scan", str(tmp_path / "nope")]) == 2
    assert "not a directory" in capsys.readouterr().err


def test_module_entry_point():
    proc = subprocess.run(
        [sys.executable, "-m", "skillfetch.cli", "scan", str(SKILLS_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "summary:" in proc.stdout
