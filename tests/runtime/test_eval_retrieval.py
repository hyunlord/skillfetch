"""`skillfetch eval retrieval` on the fixture index and a three-task eval set (no network)."""

import json

from indexkit import make_index, skill_id

from skillfetch.cli import main


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _evals(tmp_path, root):
    squash, typed = skill_id(root, "commit-squash"), skill_id(root, "typed-python")
    d = tmp_path / "evals"
    d.mkdir()
    _write(
        d / "tasks.jsonl",
        [
            {"id": "t1", "expect_none": False},
            {"id": "t2", "expect_none": False},
            {"id": "t3", "expect_none": True},
        ],
    )
    _write(
        d / "oracle.jsonl",
        [
            {"id": "t1", "relevant": [squash], "relevant_2a": [squash], "relevant_process": []},
            {"id": "t2", "relevant": [typed], "relevant_2a": [], "relevant_process": [typed]},
            {"id": "t3", "relevant": [], "relevant_2a": [], "relevant_process": []},
        ],
    )
    q3 = {"domain": "commit history", "method": "squash commits", "stack": "git"}
    _write(
        d / "queries.jsonl",
        [
            {"id": "t1", "q1": "squash my commits", "q2": "Squash the commits", "q3": q3},
            {
                "id": "t2",
                "q1": "add type hints",
                "q2": "Add type hints to the Python code",
                "q3": {"domain": "type hints", "method": "strict typing", "stack": "Python"},
            },
            {"id": "t3", "q1": "fix a typo", "q2": "Fix a typo", "q3": q3},
        ],
    )
    return d


def test_eval_retrieval_prints_the_recall_table(tmp_path, capsys):
    root = make_index(tmp_path / "idx")
    evals = _evals(tmp_path, root)
    assert main(["eval", "retrieval", "--index", str(root), "--evals", str(evals)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Tasks scored: all 2, 2a 1, process 1.")
    rows = [line for line in out.splitlines() if line.startswith(("| q1", "| q2", "| q3"))]
    assert [r.split(" | ")[0] for r in rows] == [
        "| q1 as typed",
        "| q2 restatement",
        "| q3 three queries, RRF",
    ]
    for row in rows:
        cells = [float(c) for c in row.strip("| ").split(" | ")[2:]]
        assert len(cells) == 6 and all(0 <= c <= 1 for c in cells)
    # the index is small: both relevant skills are in every top 50
    assert all(row.split(" | ")[3] == "1.000" for row in rows)


def test_eval_retrieval_needs_an_eval_set(tmp_path, capsys):
    root = make_index(tmp_path / "idx")
    assert main(["eval", "retrieval", "--index", str(root), "--evals", str(tmp_path)]) == 2
    assert "no tasks.jsonl" in capsys.readouterr().err
