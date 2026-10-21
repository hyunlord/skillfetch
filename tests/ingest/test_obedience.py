"""Obedience split test (fake backends; no network)."""

import json
from pathlib import Path

from skillfetch.ingest.extract import Completion, Usage
from skillfetch.ingest.judge_run import fixture_pairs
from skillfetch.ingest.obedience import (
    generate_tasks,
    render_tasks,
    run_trials,
    select_pairs,
    summarize,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


class Fake:
    def __init__(self, key, answers):
        self.key, self.answers, self.calls = key, list(answers), []

    def complete(self, system, messages, schema):
        self.calls.append((system, messages, schema))
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        text = answer if isinstance(answer, str) else json.dumps(answer)
        return Completion(text, "end_turn", Usage(reported_cost_usd=0.01))


def _row(pair, verdict="conflict", conf=0.9, amb=True):
    return {
        "pair": pair,
        "verdict": verdict,
        "confidence": conf,
        "ambiguous_together": amb,
        "reason": "they disagree",
    }


def test_select_pairs_ranks_by_confidence_conflicts_first():
    rows = [
        _row("a|b", "situational", 0.95, True),
        _row("c|d", "conflict", 0.95, False),
        _row("e|f", "independent", 0.99, False),
        _row("g|h", "conflict", 0.7),
    ]
    assert [r["pair"] for r in select_pairs(rows, 3)] == ["c|d", "a|b", "g|h"]


def test_tasks_are_generated_cached_and_rendered(tmp_path):
    pair = fixture_pairs(FIXTURES)[0]
    writer = Fake("w", [{"task": "Edit config.py.", "follows_a": "asks", "follows_b": "edits"}])
    rows = [_row(pair.key)]
    [task] = generate_tasks(rows, {pair.key: pair}, writer, tmp_path)
    assert task.task == "Edit config.py." and task.cost_usd == 0.01
    generate_tasks(rows, {pair.key: pair}, writer, tmp_path)
    assert len(writer.calls) == 1  # cached
    assert "**task:** Edit config.py." in render_tasks([task])


def test_trials_count_a_and_b_and_flag_non_determinism(tmp_path):
    pair = fixture_pairs(FIXTURES)[0]
    writer = Fake("w", [{"task": "T", "follows_a": "A", "follows_b": "B"}])
    [task] = generate_tasks([_row(pair.key)], {pair.key: pair}, writer, tmp_path)
    agent = Fake("agent", ["o1", "o2", "o3", "o4"])  # equal outputs share one verdict
    verdicts = [{"followed": f, "reason": "r"} for f in ["a", "b", "a", "neither"]]
    judge = Fake("judge", verdicts)
    trials = run_trials(task, ("body a", "body b"), agent, judge, trials=4, cache_dir=tmp_path)
    dist, mixed = summarize(trials)
    assert dist == {"a": 2, "b": 1, "neither": 1} and mixed
    assert agent.calls[0][2] == {}  # free text, default temperature
    assert '<skill name="A">\nbody a' in agent.calls[0][0]
