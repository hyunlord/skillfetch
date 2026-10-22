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
    skills = (("skill-a", "body a"), ("skill-b", "body b"))
    trials = run_trials(task, skills, agent, judge, trials=4, cache_dir=tmp_path)
    dist, mixed = summarize(trials)
    assert dist == {"a": 2, "b": 1, "neither": 1} and mixed
    assert agent.calls[0][2] == {}  # free text, default temperature
    first, second = agent.calls[0][0], agent.calls[1][0]
    assert first.index("skill-a") < first.index("skill-b")  # run 0: A first
    assert second.index("skill-b") < second.index("skill-a")  # run 1: B first
    assert [t.order for t in trials] == ["ab", "ba", "ab", "ba"]


def _task(tmp_path):
    pair = fixture_pairs(FIXTURES)[0]
    writer = Fake("w", [{"task": "T", "follows_a": "A", "follows_b": "B"}])
    [task] = generate_tasks([_row(pair.key)], {pair.key: pair}, writer, tmp_path)
    return task


def test_precedence_puts_the_load_skills_header_on_top_in_that_order(tmp_path):
    from skillfetch.ingest.obedience import PRECEDENCE_HEADER

    task = _task(tmp_path)
    skills = (("skill-a", "body a"), ("skill-b", "body b"))
    judge = Fake("judge", [{"followed": "a", "reason": "r"}])
    for cond, first, second in (("ab", "skill-a", "skill-b"), ("ba", "skill-b", "skill-a")):
        agent = Fake(f"agent-{cond}", [f"out {i}" for i in range(3)])
        trials = run_trials(task, skills, agent, judge, 3, tmp_path, precedence=cond)
        assert [t.order for t in trials] == [cond] * 3
        assert {t.precedence for t in trials} == {cond}
        for system, _, _ in agent.calls:
            assert system.startswith(PRECEDENCE_HEADER)
            assert system.index(first) < system.index(second)
    none = Fake("agent-none", ["x"])
    run_trials(task, skills, none, judge, 1, tmp_path)
    assert PRECEDENCE_HEADER not in none.calls[0][0]


def test_precedence_report_counts_control_and_turned_winners():
    from skillfetch.ingest.obedience import ObedienceTask, Trial, render_precedence

    def runs(pair, cond, followed):
        return [
            Trial(pair, i, cond or "ab", "", f, "", cond or "none") for i, f in enumerate(followed)
        ]

    tasks = [
        ObedienceTask(
            pair=p,
            verdict="conflict",
            confidence=1,
            ambiguous_together=True,
            judge_reason="",
            task="",
            follows_a="",
            follows_b="",
        )
        for p in ("s/x@1|s/y@1", "s/u@1|s/v@1")
    ]
    baseline = [runs(tasks[0].pair, None, "aaaab"), runs(tasks[1].pair, None, "bbbbb")]
    by_cond = {
        "ab": [runs(tasks[0].pair, "ab", "aaaaa"), runs(tasks[1].pair, "ab", "aabbb")],
        "ba": [runs(tasks[0].pair, "ba", "bbbba"), runs(tasks[1].pair, "ba", "bbbbb")],
    }
    text = render_precedence(tasks, by_cond, baseline)
    # controlled: 5 + 4 (pair 1), 2 + 5 (pair 2) = 16 of 20
    assert "**16/20** of all runs" in text
    # pair 1: winner a, ranked second under ba, b won -> turned; pair 2: winner b, ranked
    # second under ab, b still won -> kept
    assert "turned around (winner ranked second, other skill won the majority): **1**" in text
    assert "winner kept although ranked second: 1" in text


def test_resolved_block_names_the_winner_above_a_then_b(tmp_path):
    from skillfetch.ingest.obedience import PRECEDENCE_HEADER, RESOLVED_TITLE, Conflict

    task = _task(tmp_path)
    skills = (("skill-a", "body a"), ("skill-b", "body b"))
    conflict = Conflict("emoji", ((3, "Use emoji."),), ((7, "Never emoji."),))
    judge = Fake("judge", [{"followed": "b", "reason": "r"}])
    for cond, winner in (("resolved-a", "skill-a"), ("resolved-b", "skill-b")):
        agent = Fake(f"agent-{cond}", ["o1", "o2"])
        trials = run_trials(task, skills, agent, judge, 2, tmp_path, cond, conflict)
        assert [t.order for t in trials] == ["ab", "ab"]
        system = agent.calls[0][0]
        assert system.startswith(RESOLVED_TITLE) and PRECEDENCE_HEADER not in system
        assert f'Winner: "{winner}"' in system
        assert 'skill-a, line 3: "Use emoji."' in system
        assert 'skill-b, line 7: "Never emoji."' in system
        assert system.index('<skill name="skill-a">') < system.index('<skill name="skill-b">')


def test_pair_conflicts_take_judged_lines_else_a_shared_subject(tmp_path):
    from skillfetch.ingest.obedience import pair_conflicts

    idx = tmp_path / "index"
    idx.mkdir()
    rows = [
        {"skill_id": "s/a@1", "subject": "emoji", "evidence": {"line_no": 3, "text": "Use emoji."}},
        {"skill_id": "s/b@1", "subject": "Emoji", "evidence": {"line_no": 7, "text": "No emoji."}},
        {"skill_id": "s/c@1", "subject": " EMOJI", "evidence": {"line_no": 2, "text": "Emoji!"}},
    ]
    (idx / "constraints.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    judged = tmp_path / "j.jsonl"
    ev = [["s/a@1", 3, "Use emoji."], ["s/b@1", 7, "No emoji."]]
    judged.write_text(json.dumps({"pair": "s/a@1|s/b@1", "evidence": ev}) + "\n")
    out = pair_conflicts(idx, judged, ["s/a@1|s/b@1", "s/a@1|s/c@1"])
    assert out["s/a@1|s/b@1"].subject == "emoji"
    assert out["s/a@1|s/b@1"].lines_b == ((7, "No emoji."),)
    assert out["s/a@1|s/c@1"].lines_b == ((2, "Emoji!"),)  # from constraints.jsonl


def test_strip_lines_replaces_the_losers_evidence_with_a_comment():
    from skillfetch.ingest.obedience import strip_lines

    body = ["# Rules", "", "- Never use emoji.", "- Keep lines short."]
    # SKILL.md line numbers: frontmatter takes lines 1-4, the body starts on line 5
    out, done = strip_lines(body, 5, ((7, "Never use emoji."),), "emoji-skill")
    assert done == 1
    assert out.split("\n")[2] == '<!-- overridden by emoji-skill: "- Never use emoji." -->'
    assert "- Keep lines short." in out  # replaced, nothing else removed
    # a wrong line number falls back to the first body line that contains the text
    out2, done2 = strip_lines(body, 5, ((99, "Keep lines short."),), "w")
    assert done2 == 1 and '<!-- overridden by w: "- Keep lines short." -->' in out2
    assert strip_lines(body, 5, ((7, "not in the body"),), "w") == ("\n".join(body).strip(), 0)


def test_strip_conditions_have_no_header_or_block_and_load_a_then_b(tmp_path):
    from skillfetch.ingest.obedience import PRECEDENCE_HEADER, RESOLVED_TITLE, ranked_first

    task = _task(tmp_path)
    skills = (("skill-a", "body a"), ("skill-b", '<!-- overridden by skill-a: "x" -->'))
    agent = Fake("agent-strip", ["o1"])
    judge = Fake("judge", [{"followed": "a", "reason": "r"}])
    [trial] = run_trials(task, skills, agent, judge, 1, tmp_path, "strip-a")
    system = agent.calls[0][0]
    assert PRECEDENCE_HEADER not in system and RESOLVED_TITLE not in system
    assert system.index('<skill name="skill-a">') < system.index('<skill name="skill-b">')
    assert trial.order == "ab" and ranked_first("strip-b") == "b"
