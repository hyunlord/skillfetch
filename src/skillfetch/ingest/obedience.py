"""Obedience split test: when an agent gets two skills that the judge thinks disagree, which
one does it follow?

For each selected pair (judge verdict `conflict`, or `ambiguous_together`, ranked by the
judge's confidence): a model writes one short task that touches both instructions and says
what following A and following B would look like; then the agent model runs the task N
times with both full skill bodies in its system prompt, and a judge classifies each output
as following A, B, both or neither. Pairs whose runs mix A and B are non-deterministic.

Steps are separate so the task list can be reviewed before anything runs:
`generate_tasks` (cheap) and `run_trials` + `classify` (N agent runs per pair).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from skillfetch.ingest.extract import ExtractBackend
from skillfetch.ingest.judge_run import JudgePair

DEFAULT_CACHE = Path("~/.skillfetch/obedience-cache").expanduser()
DEFAULT_AGENT_MODEL = "claude-code/sonnet"  # subagent sessions, not an API
TRIALS = 10
Followed = Literal["a", "b", "both", "neither"]

TASK_PROMPT = """You design one test task for a coding agent. The agent will have both of the
skills below loaded at once. The highlighted instructions (lines marked `>`) may disagree.

Write one short, realistic task (one to three sentences; include any small code or text it
needs inline) that a user could give the agent and that makes both highlighted instructions
apply, so that following skill A's instruction gives a visibly different result from
following skill B's. Do not mention the skills, the instructions or the test in the task.
Then say, in one sentence each, what an output that follows A looks like and what an output
that follows B looks like, concretely enough that a reader can tell them apart."""

TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "follows_a": {"type": "string"},
        "follows_b": {"type": "string"},
    },
    "required": ["task", "follows_a", "follows_b"],
    "additionalProperties": False,
}

CLASSIFY_PROMPT = """An agent was given a task while two skills were loaded. Below are the task,
what an output that follows skill A looks like, what an output that follows skill B looks
like, and the agent's output. Decide which the output follows: `a`, `b`, `both` (it satisfies
both descriptions), or `neither`. Give a one-sentence reason."""

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "followed": {"type": "string", "enum": ["a", "b", "both", "neither"]},
        "reason": {"type": "string"},
    },
    "required": ["followed", "reason"],
    "additionalProperties": False,
}


class ObedienceTask(BaseModel):
    pair: str  # "a|b"
    verdict: str
    confidence: float
    ambiguous_together: bool
    judge_reason: str
    task: str
    follows_a: str
    follows_b: str
    cost_usd: float | None = None


def select_pairs(rows: list[dict], n: int = 30) -> list[dict]:
    """judgments.jsonl rows with verdict conflict or ambiguous_together, by confidence
    (conflict first on ties, then pair id)."""
    picked = [r for r in rows if r.get("verdict") == "conflict" or r.get("ambiguous_together")]
    picked.sort(key=lambda r: (-(r["confidence"] or 0), r["verdict"] != "conflict", r["pair"]))
    return picked[:n]


def _cached(cache_dir: Path, kind: str, payload: str, call):
    sha = hashlib.sha256(payload.encode()).hexdigest()
    path = cache_dir / kind / f"{sha}.json"
    if path.is_file():
        return json.loads(path.read_text())
    out = call()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def _json_call(backend: ExtractBackend, system: str, user: str, schema: dict) -> dict:
    reply = backend.complete(system, [{"role": "user", "content": user}], schema)
    data = json.loads(reply.text)
    data["_cost_usd"] = reply.usage.reported_cost_usd
    return data


def generate_tasks(
    rows: list[dict],
    pairs: dict[str, JudgePair],
    backend: ExtractBackend,
    cache_dir: Path = DEFAULT_CACHE,
    jobs: int = 6,
) -> list[ObedienceTask]:
    def one(row: dict) -> ObedienceTask:
        text = pairs[row["pair"]].item.text
        data = _cached(
            cache_dir,
            f"tasks/{backend.key}",
            TASK_PROMPT + "\0" + text,
            lambda: _json_call(backend, TASK_PROMPT, text, TASK_SCHEMA),
        )
        return ObedienceTask(
            pair=row["pair"],
            verdict=row["verdict"],
            confidence=row["confidence"],
            ambiguous_together=row["ambiguous_together"],
            judge_reason=row["reason"],
            task=data["task"],
            follows_a=data["follows_a"],
            follows_b=data["follows_b"],
            cost_usd=data.get("_cost_usd"),
        )

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return list(pool.map(one, rows))


def render_tasks(tasks: list[ObedienceTask]) -> str:
    out = ["# Obedience split test: tasks to review before running", ""]
    for i, t in enumerate(tasks, 1):
        a, b = t.pair.split("|")
        out += [
            f"## {i}. `{a}` ⟷ `{b}`",
            "",
            f"- judge: {t.verdict}, confidence {t.confidence:.2f}, ambiguous_together "
            f"{str(t.ambiguous_together).lower()} — {t.judge_reason}",
            f"- **task:** {t.task}",
            f"- follows A: {t.follows_a}",
            f"- follows B: {t.follows_b}",
            "",
        ]
    return "\n".join(out)


# --- trials (run only after the task list is approved) -------------------------------------


@dataclass
class Trial:
    pair: str
    run: int
    output: str
    followed: Followed | None
    reason: str


def system_prompt(body_a: str, body_b: str) -> str:
    return (
        "You are a coding agent. Follow the skills below while you work.\n\n"
        f'<skill name="A">\n{body_a}\n</skill>\n\n<skill name="B">\n{body_b}\n</skill>'
    )


def run_trials(
    task: ObedienceTask,
    bodies: tuple[str, str],
    agent: ExtractBackend,
    judge: ExtractBackend,
    trials: int = TRIALS,
    cache_dir: Path = DEFAULT_CACHE,
) -> list[Trial]:
    """`trials` agent runs (each cached under its run number) and their classification."""
    system = system_prompt(*bodies)
    out = []
    for n in range(trials):

        def answer() -> dict:
            # empty schema: free text at the default temperature, so runs can differ
            reply = agent.complete(system, [{"role": "user", "content": task.task}], {})
            return {"text": reply.text}

        text = _cached(cache_dir, f"runs/{agent.key}", f"{system}\0{task.task}\0{n}", answer)
        user = (
            f"Task:\n{task.task}\n\nFollows A: {task.follows_a}\nFollows B: {task.follows_b}"
            f"\n\nAgent output:\n{text['text']}"
        )
        verdict = _cached(
            cache_dir,
            f"classify/{judge.key}",
            CLASSIFY_PROMPT + "\0" + user,
            lambda user=user: _json_call(judge, CLASSIFY_PROMPT, user, CLASSIFY_SCHEMA),
        )
        out.append(Trial(task.pair, n, text["text"], verdict["followed"], verdict["reason"]))
    return out


def summarize(trials: list[Trial]) -> tuple[Counter, bool]:
    """(distribution of followed, non-deterministic: both A and B occur)."""
    dist = Counter(t.followed for t in trials)
    return dist, dist["a"] > 0 and dist["b"] > 0
