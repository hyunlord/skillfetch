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


PRECEDENCE = ("none", "ab", "ba", "resolved-a", "resolved-b", "strip-a", "strip-b")
NAMED = ("resolved-", "strip-")  # conditions that name a winner: resolved-a, strip-b, ...
RESOLVED_TITLE = "Resolved rule conflicts"


@dataclass(frozen=True)
class Conflict:
    """A pair's disagreement as the index records it: the subject and the evidence lines
    (line number, text) on each side."""

    subject: str
    lines_a: tuple[tuple[int, str], ...]
    lines_b: tuple[tuple[int, str], ...]


def resolved_block(conflict: Conflict, name_a: str, name_b: str, winner: str) -> str:
    """The block that names a pair's winner, with both sides' evidence lines."""
    win = name_a if winner == "a" else name_b
    out = [
        RESOLVED_TITLE,
        "",
        "These skills were checked against each other before this task. Where they "
        "disagree, follow the winner named here, whatever order the skills appear in.",
        "",
        f'- {conflict.subject}: "{name_a}" vs "{name_b}". Winner: "{win}".',
    ]
    for name, lines in ((name_a, conflict.lines_a), (name_b, conflict.lines_b)):
        out += [f'  - {name}, line {n}: "{text}"' for n, text in lines]
    return "\n".join(out)


def ranked_first(precedence: str) -> str:
    """The skill a condition tells the agent to follow: ab -> a, resolved-b -> b,
    strip-a -> a."""
    return precedence[-1] if precedence.startswith(NAMED) else precedence[0]


def strip_lines(
    body_lines: list[str], body_start: int, lines: tuple[tuple[int, str], ...], winner: str
) -> tuple[str, int]:
    """The losing skill's body with each evidence line replaced (not deleted) by
    `<!-- overridden by <winner>: "<line>" -->`; (body, lines replaced). A line is found by
    its SKILL.md line number, else by the first body line that contains its text."""
    out = list(body_lines)
    done = 0
    for n, text in lines:
        i = n - body_start
        if not (0 <= i < len(out) and text in out[i]):
            i = next((k for k, line in enumerate(out) if text in line), -1)
        if i < 0 or out[i].startswith("<!-- overridden by "):
            continue
        original = out[i].strip().replace("-->", "-- >")
        out[i] = f'<!-- overridden by {winner}: "{original}" -->'
        done += 1
    return "\n".join(out).strip(), done


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
    conflict: Conflict | None = None,
) -> list[Trial]:
    """`trials` agent runs (each cached under its run number) and their classification.
    precedence "none": even runs load A first, odd runs B first, so a position bias shows
    up, and there is no precedence rule. "ab" / "ba": every run puts the load_skills
    precedence header on top and loads the skills in that order. "resolved-a" /
    "resolved-b": every run puts the Resolved rule conflicts block (naming A or B the
    winner of `conflict`) on top, and loads A then B."""
    from skillfetch.mcp.session import PRECEDENCE_HEADER

    if precedence not in PRECEDENCE:
        raise ValueError(f"precedence {precedence!r}: one of {', '.join(PRECEDENCE)}")
    if precedence.startswith("strip-"):
        header = None  # the caller passes the loser's body already stripped
    elif precedence.startswith("resolved-"):
        if conflict is None:
            raise ValueError(f"precedence {precedence} needs the pair's conflict")
        header = resolved_block(conflict, skills[0][0], skills[1][0], ranked_first(precedence))
    else:
        header = None if precedence == "none" else PRECEDENCE_HEADER
    out = []
    for n in range(trials):
        if precedence.startswith(NAMED):
            order = "ab"
        else:
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
            first = ranked_first(cond)
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
            # the condition that ranks the content winner second
            against = [c for c in by_condition if ranked_first(c) == other]
            if against:
                won = _winner(by_condition[against[0]][i])
                flipped += won == other
                held += won == base
        rows.append(f"| {a} ⟷ {b} | {base or 'tie'} | " + " | ".join(cells) + " |")
    conds = list(by_condition)
    named = any(c.startswith(NAMED) for c in conds)
    stripped = any(c.startswith("strip-") for c in conds)
    lines += [
        f"{len(tasks)} pairs × {len(conds)} orders ({', '.join(conds)}) × "
        f"{len(next(iter(by_condition.values()))[0]) if tasks else 0} runs = {total} runs. "
        + (
            "No header and no block: in the losing skill's body each evidence line is "
            'replaced by `<!-- overridden by <winner>: "<line>" -->` (strip-a: A wins, B\'s '
            "lines replaced; strip-b: the reverse); the skills follow in the order A, B."
            if stripped
            else f'Each run starts with a "{RESOLVED_TITLE}" block that names the winner '
            "(resolved-a: A, resolved-b: B) with both sides' evidence lines; the skills follow "
            "in the order A, B."
            if named
            else "The header is the one load_skills sends: "
            '"Skills are listed in precedence order. If two instructions disagree, follow the '
            'earlier one."'
        ),
        "",
        f"Control rate (followed the skill ranked or named first): **{controlled}/{total}** of "
        "all runs; "
        f"{controlled}/{decided} of runs that followed exactly one skill.",
        "",
        *(
            f"- {c}: {v['controlled']}/{v['runs']} of all runs, {v['controlled']}/{v['ab']} "
            "of one-skill runs"
            for c, v in cond_tot.items()
        ),
        "",
        f"Pairs with a no-header winner whose winner the "
        f"{'stripping' if stripped else 'block' if named else 'header'} "
        "turned around (winner ranked "
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


def render_comparison(tasks: list[ObedienceTask], *groups: dict[str, list[list[Trial]]]) -> str:
    """Control per pair under each condition, side by side (the precedence header ab / ba,
    the resolved block, stripped lines, ...): runs that followed the skill ranked or named
    first."""
    cols = {c: r for g in groups for c, r in g.items()}
    conds = list(cols)
    lines = [
        "| pair (A ⟷ B) | " + " | ".join(conds) + " |",
        "|---|" + "---|" * len(conds),
    ]
    totals = {c: [0, 0] for c in conds}
    for i, t in enumerate(tasks):
        a, b = (x.split("/")[1].split("@")[0] for x in t.pair.split("|"))
        cells = []
        for c in conds:
            trials = cols[c][i]
            hit = sum(tr.followed == ranked_first(c) for tr in trials)
            totals[c][0] += hit
            totals[c][1] += len(trials)
            cells.append(f"{hit}/{len(trials)}")
        lines.append(f"| {a} ⟷ {b} | " + " | ".join(cells) + " |")
    lines.append(
        "| **all pairs** | "
        + " | ".join(f"**{h}/{n}** ({h / n:.2f})" if n else "0/0" for h, n in totals.values())
        + " |"
    )
    return "\n".join(lines)


def pair_conflicts(index_dir: Path, judgments: Path, pairs: list[str]) -> dict[str, Conflict]:
    """Each pair's Conflict: the evidence lines the judge saw (judgments.jsonl) and the
    subject of the indexed constraint on side A's first such line. A pair without judged
    evidence takes the first two constraints with the same subject from constraints.jsonl."""
    from skillfetch.resolve.terms import normalize_term

    by_skill: dict[str, list[dict]] = {}
    for line in (index_dir / "constraints.jsonl").open():
        row = json.loads(line)
        by_skill.setdefault(row["skill_id"], []).append(row)
    evidence = {}
    if judgments.is_file():
        for line in judgments.open():
            row = json.loads(line)
            evidence[row["pair"]] = row.get("evidence") or []
    out = {}
    for pair in pairs:
        a, b = pair.split("|")
        ev = evidence.get(pair) or []
        lines_a = tuple((n, t) for sid, n, t in ev if sid == a)[:2]
        lines_b = tuple((n, t) for sid, n, t in ev if sid == b)[:2]
        at = {c["evidence"]["line_no"]: c for c in by_skill.get(a, [])}
        subject = next((at[n]["subject"] for n, _ in lines_a if n in at), None)
        if not (lines_a and lines_b and subject):
            match = next(
                (
                    (ca, cb)
                    for ca in by_skill.get(a, [])
                    for cb in by_skill.get(b, [])
                    if normalize_term(ca["subject"]) == normalize_term(cb["subject"])
                ),
                None,
            )
            if match is None:
                raise ValueError(f"{pair}: no evidence lines and no shared subject")
            ca, cb = match
            subject = ca["subject"]
            lines_a = ((ca["evidence"]["line_no"], ca["evidence"]["text"]),)
            lines_b = ((cb["evidence"]["line_no"], cb["evidence"]["text"]),)
        out[pair] = Conflict(subject, lines_a, lines_b)
    return out
