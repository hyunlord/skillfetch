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

from skillfetch.ingest.claude_code import PendingAnswer
from skillfetch.ingest.extract import Completion, ExtractBackend, Usage
from skillfetch.ingest.judge_run import JudgePair

DEFAULT_CACHE = Path("~/.skillfetch/obedience-cache").expanduser()
DEFAULT_AGENT_MODEL = "claude-code/sonnet"  # subagent sessions, not an API
TRIALS = 5
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


PRECEDENCE = ("none", "ab", "ba")


@dataclass
class Trial:
    pair: str
    run: int
    order: str  # "ab": skill A loaded first; "ba": B first
    output: str
    followed: Followed | None
    reason: str
    precedence: str = "none"  # none: no rule; ab / ba: the load_skills header, that order


def system_prompt(skills: list[tuple[str, str]], header: str | None = None) -> str:
    """Both skills, as (name, body), in the given order. Without `header` there is no
    precedence rule: the test asks which one the agent follows on its own. With it (the
    precedence header load_skills sends), the header goes first, as in a loaded set."""
    blocks = "\n\n".join(f'<skill name="{name}">\n{body}\n</skill>' for name, body in skills)
    top = f"{header}\n\n" if header else ""
    return (
        f"{top}The following skills are loaded for this task. Follow them while you work.\n\n"
        f"{blocks}\n\n{NO_TOOLS}"
    )


# The runs have no tools. Without a note most runs (51 of the first 90) wrote a tool call as
# text ("Let me find the file") and ended there. A first wording ("do the task in this one
# reply") pushed runs away from stopping to ask, which biased every pair whose rule is "ask
# first"; this one leaves both open.
NO_TOOLS = (
    "This session has no tools: no shell, no file access, no network. Everything available is "
    "in the user's message; treat any code or files it quotes as what you would have read. "
    "Reply as you would after reading them: with your result, or with your questions if you "
    "would stop and ask before going on."
)


class ClaudeSessionAgent:
    """The agent under test: one isolated headless Claude Code session per run
    (`claude -p --safe-mode`: no CLAUDE.md, plugins, hooks or MCP; no tools), with the skills
    appended to its system prompt. Not an API call from skillfetch."""

    def __init__(self, model: str = "sonnet", workdir: Path | None = None):
        self.model = model
        self.workdir = workdir or Path("/tmp")

    @property
    def key(self) -> str:
        return f"claude-code/{self.model}-session"

    def complete(self, system: str, messages: list[dict[str, str]], schema: dict) -> Completion:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(system)
        cmd = [
            "claude",
            "-p",
            "--safe-mode",
            "--tools",
            "",
            "--no-session-persistence",
            "--model",
            self.model,
            "--output-format",
            "json",
            "--append-system-prompt-file",
            f.name,
            messages[-1]["content"],
        ]
        # stdin closed: `claude -p` appends piped stdin to the prompt
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.workdir, stdin=subprocess.DEVNULL
        )
        Path(f.name).unlink(missing_ok=True)
        data = json.loads(proc.stdout)
        if data.get("is_error") or data.get("terminal_reason") not in (None, "completed"):
            raise RuntimeError(f"claude session failed: {data.get('terminal_reason')}")
        return Completion(
            text=data.get("result") or "",
            stop_reason="end_turn",
            # what the session would have cost at API prices (Claude Code reports it)
            usage=Usage(reported_cost_usd=data.get("total_cost_usd")),
        )


def run_trials(
    task: ObedienceTask,
    skills: tuple[tuple[str, str], tuple[str, str]],
    agent: ExtractBackend,
    judge: ExtractBackend,
    trials: int = TRIALS,
    cache_dir: Path = DEFAULT_CACHE,
    precedence: str = "none",
) -> list[Trial]:
    """`trials` agent runs (each cached under its run number) and their classification.
    precedence "none": even runs load A first, odd runs B first, so a position bias shows
    up, and there is no precedence rule. "ab" / "ba": every run puts the load_skills
    precedence header on top and loads the skills in that order."""
    from skillfetch.mcp.session import PRECEDENCE_HEADER

    if precedence not in PRECEDENCE:
        raise ValueError(f"precedence {precedence!r}: one of {', '.join(PRECEDENCE)}")
    header = None if precedence == "none" else PRECEDENCE_HEADER
    out = []
    for n in range(trials):
        order = precedence if header else ("ab" if n % 2 == 0 else "ba")
        ordered = list(skills) if order == "ab" else list(skills)[::-1]
        system = system_prompt(ordered, header)

        def answer(system=system) -> dict:
            # empty schema: free text at the default temperature, so runs can differ
            reply = agent.complete(system, [{"role": "user", "content": task.task}], {})
            return {"text": reply.text, "cost_usd": reply.usage.reported_cost_usd}

        text = _cached(cache_dir, f"runs/{agent.key}", f"{system}\0{task.task}\0{n}", answer)
        user = (
            f"Task:\n{task.task}\n\nFollows A: {task.follows_a}\nFollows B: {task.follows_b}"
            f"\n\nAgent output:\n{text['text']}"
        )
        try:
            verdict = _cached(
                cache_dir,
                f"classify/{judge.key}",
                CLASSIFY_PROMPT + "\0" + user,
                lambda user=user: _json_call(judge, CLASSIFY_PROMPT, user, CLASSIFY_SCHEMA),
            )
        except PendingAnswer:  # queued for Claude Code; a rerun picks the answer up
            verdict = {"followed": None, "reason": "pending"}
        out.append(
            Trial(
                task.pair,
                n,
                order,
                text["text"],
                verdict["followed"],
                verdict["reason"],
                precedence,
            )
        )
    return out


def summarize(trials: list[Trial]) -> tuple[Counter, bool]:
    """(distribution of followed, non-deterministic: both A and B occur)."""
    dist = Counter(t.followed for t in trials)
    return dist, dist["a"] > 0 and dist["b"] > 0


def render_results(tasks: list[ObedienceTask], results: list[list[Trial]]) -> str:
    """Per-pair distribution, the non-deterministic count, and a position-bias check."""
    lines = ["# Obedience split test: results", ""]
    mixed = 0
    total: Counter = Counter()
    first: Counter = Counter()  # followed the skill loaded first / second
    rows = []
    for t, trials in zip(tasks, results, strict=True):
        dist, nondet = summarize(trials)
        mixed += nondet
        total.update(dist)
        for tr in trials:
            if tr.followed in ("a", "b"):
                first["first" if tr.followed == tr.order[0] else "second"] += 1
        a, b = (x.split("/")[1].split("@")[0] for x in t.pair.split("|"))
        cells = " | ".join(str(dist.get(k, 0)) for k in ("a", "b", "both", "neither"))
        rows.append(f"| {a} ⟷ {b} | {cells} | {dist.get(None, 0)} | {'yes' if nondet else ''} |")
    n = sum(len(tr) for tr in results)
    lines += [
        f"{len(tasks)} pairs × {len(results[0]) if results else 0} runs = {n} runs. "
        f"Non-deterministic pairs (both A and B followed across runs): **{mixed}**.",
        "",
        "Overall: "
        + ", ".join(f"{k} {total.get(k, 0)}" for k in ("a", "b", "both", "neither"))
        + (f", pending {total[None]}" if total.get(None) else ""),
        "",
        f"When exactly one skill was followed, it was the one loaded first {first['first']} "
        f"times and the one loaded second {first['second']} times.",
        "",
        "## Per pair",
        "",
        "| pair (A ⟷ B) | A | B | both | neither | pending | non-deterministic |",
        "|---|---|---|---|---|---|---|",
        *rows,
    ]
    return "\n".join(lines)


def _winner(trials: list[Trial]) -> str | None:
    """The skill followed in more runs (a or b), or None on a tie or no a/b run."""
    dist = Counter(t.followed for t in trials)
    if dist["a"] == dist["b"]:
        return None
    return "a" if dist["a"] > dist["b"] else "b"


def render_precedence(
    tasks: list[ObedienceTask],
    by_condition: dict[str, list[list[Trial]]],
    baseline: list[list[Trial]],
) -> str:
    """Control rate per pair and overall: a run is controlled when the skill it followed
    is the one the header ranks first. Compared with the no-header winner of each pair:
    how many pairs the header turned around (the content winner loaded second, and the
    other skill won)."""
    lines = ["# Obedience split test: precedence header", ""]
    rows, flipped, held, total, controlled, decided = [], 0, 0, 0, 0, 0
    cond_tot: dict[str, Counter] = {c: Counter() for c in by_condition}
    for i, t in enumerate(tasks):
        a, b = (x.split("/")[1].split("@")[0] for x in t.pair.split("|"))
        base = _winner(baseline[i])
        cells = []
        for cond, results in by_condition.items():
            trials = results[i]
            first = cond[0]
            dist = Counter(tr.followed for tr in trials)
            hit = sum(tr.followed == first for tr in trials)
            ab_runs = dist["a"] + dist["b"]
            total += len(trials)
            controlled += hit
            decided += ab_runs
            cond_tot[cond].update({"runs": len(trials), "controlled": hit, "ab": ab_runs})
            cells.append(
                f"{hit}/{len(trials)} ({dist['a']}a {dist['b']}b {dist['both']}both "
                f"{dist['neither']}neither)"
            )
        if base is not None:
            other = "b" if base == "a" else "a"
            reversed_cond = f"{other}{base}"  # the content winner loaded second
            if reversed_cond in by_condition:
                won = _winner(by_condition[reversed_cond][i])
                flipped += won == other
                held += won == base
        rows.append(f"| {a} ⟷ {b} | {base or 'tie'} | " + " | ".join(cells) + " |")
    conds = list(by_condition)
    lines += [
        f"{len(tasks)} pairs × {len(conds)} orders ({', '.join(conds)}) × "
        f"{len(next(iter(by_condition.values()))[0]) if tasks else 0} runs = {total} runs. "
        "The header is the one load_skills sends: "
        '"Skills are listed in precedence order. If two instructions disagree, follow the '
        'earlier one."',
        "",
        f"Control rate (followed the skill ranked first): **{controlled}/{total}** of all runs; "
        f"{controlled}/{decided} of runs that followed exactly one skill.",
        "",
        *(
            f"- {c}: {v['controlled']}/{v['runs']} of all runs, {v['controlled']}/{v['ab']} "
            "of one-skill runs"
            for c, v in cond_tot.items()
        ),
        "",
        "Pairs with a no-header winner whose winner the header turned around (winner ranked "
        f"second, other skill won the majority): **{flipped}**; winner kept although ranked "
        f"second: {held}; pairs without a no-header winner: "
        f"{sum(_winner(r) is None for r in baseline)}.",
        "",
        "## Per pair",
        "",
        "| pair (A ⟷ B) | no-header winner | "
        + " | ".join(f"{c}: controlled/runs" for c in conds)
        + " |",
        "|---|---|" + "---|" * len(conds),
        *rows,
    ]
    return "\n".join(lines)
