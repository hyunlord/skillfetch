"""scripts/skill_count.py on a hand-written transcript (no model, no network)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("skill_count", ROOT / "scripts" / "skill_count.py")
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)


def _use(uid: str, tool: str, inp: dict) -> dict:
    block = {"type": "tool_use", "id": uid, "name": f"mcp__skillfetch__{tool}", "input": inp}
    return {"type": "assistant", "message": {"content": [block]}}


def _result(uid: str, payload: dict) -> dict:
    block = {"type": "tool_result", "tool_use_id": uid, "content": json.dumps(payload)}
    return {"type": "user", "message": {"content": [block]}}


def _transcript(tmp_path: Path, events: list[dict]) -> Path:
    path = tmp_path / "s.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


RESULTS = [
    {"id": "a", "token_estimate": 3000},
    {"id": "b", "token_estimate": 4000},
    {"id": "c", "token_estimate": 900},
    {"id": "d", "token_estimate": 500},
]


def test_picks_tokens_drops_and_unpicked(tmp_path):
    path = _transcript(
        tmp_path,
        [
            _use("1", "search_skills", {"queries": ["w", "x", "y", "z"]}),
            _result("1", {"results": RESULTS}),
            _use("2", "resolve_and_load", {"auto_ids": ["a", "b"], "pinned_ids": ["path:/x/y"]}),
            _result(
                "2",
                {
                    "content": "x" * 400,
                    "errors": [
                        {"id": "b", "error": "dropped: the set is over max_tokens=8000 (...)"},
                        {"id": "path:/x/y", "error": "SKILL.md: fetch failed (URLError)"},
                    ],
                },
            ),
        ],
    )
    row = sc.session_row(path, {"a": 3, "b": 1, "c": 2, "d": 0})
    assert row["n_picked"] == 2
    assert row["picked_tokens"] == 7000
    assert row["pinned"] == ["path:<local>"]
    assert row["budget_drops"] == ["b"]
    assert row["other_load_errors"] == 1
    assert row["loaded_tokens"] == 100
    assert row["max_tokens"] == [8000]
    assert row["labeled_results"] == 4
    assert row["picked_grades"] == [3, 1]
    assert row["unpicked_g2"] == [{"id": "c", "grade": 2, "token_estimate": 900}]


def test_no_search_is_no_row(tmp_path):
    path = _transcript(tmp_path, [_use("1", "profile_repo", {"path": "/r"})])
    assert sc.session_row(path, None) is None


def test_labels_count_on_the_task_search_not_the_name_search(tmp_path):
    path = _transcript(
        tmp_path,
        [
            _use("1", "search_skills", {"queries": ["w", "x", "y", "z"]}),
            _result("1", {"results": RESULTS}),
            _use("2", "search_skills", {"query": "rust-testing"}),
            _result("2", {"results": [{"id": "e", "token_estimate": 100}]}),
            _use("3", "resolve_set", {"auto_ids": ["a"], "pinned_ids": ["e"]}),
            _result("3", {"set_id": "s"}),
        ],
    )
    row = sc.session_row(path, {"c": 2})
    assert row["results"] == 4
    assert row["pinned_tokens"] == 100
    assert row["load_calls"] == 0
    assert row["unpicked_g2"] == [{"id": "c", "grade": 2, "token_estimate": 900}]
