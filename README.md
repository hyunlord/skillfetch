# skillfetch

**Check a skill before you install it.** `skillfetch scan` reads a skills folder, or a GitHub
repository without installing anything, and tells you in one line whether to install it.
It checks:
- injection patterns and remote instructions;
- size;
- bundled scripts;
- the license;
- lines that state a version or a year;
- skills that contradict each other.

No model and no API key. The rest of this repository is the measurement study behind it:
what skills do for coding agents in real sessions ([numbers.md](docs/writeup/numbers.md)).

## Before you install a skill, scan it

```console
$ uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan https://github.com/<owner>/<repo>
$ uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills
```

- **A GitHub URL** (optionally `/tree/<ref>/<path>`):
  - It is cloned at depth 1 into a temporary folder, scanned there, and deleted.
  - Nothing is installed or run: no hooks, submodules or LFS, and symbolic links become plain
    files.
  - The report names the URL and the commit.
- **The first line** is the advice:
  - **NOT RECOMMENDED** when a skill fails the injection scan or lint, or two skills give
    opposite instructions;
  - **CAUTION** when a skill has injection-scan warnings, is over a size limit, bundles scripts,
    states no license, or covers another skill;
  - **RECOMMENDED** otherwise.

  The rule is in [index-format.md §5.1](docs/design/index-format.md).
- **Then** a summary by severity, then the details, each with the line it comes from.

| check | what it reports |
|---|---|
| injection scan | failures (instruction overrides, exfiltration, privilege, hidden text) and warnings (`sudo`, piping a download into a shell, a URL named as instructions to follow) |
| size | `SKILL.md` over 8,000 tokens, more than 20 files, or more than 1 MB |
| scripts | files a skill bundles to run |
| license | the skill's LICENSE file or frontmatter, else none (all rights reserved) |
| dated claims | prose lines that state a year or a version: they may have changed since the model was trained, or be wrong; check the official docs |
| lint | frontmatter, links, length |
| duplicates and contradictions | identical copies; pairs of skills whose extracted instructions conflict, quoting both lines |

A real run (2026-10-27, excerpt) on design-taste-frontend, a popular design skill that one
of our measured conditions installed:

```console
$ skillfetch scan https://github.com/leonxlnx/taste-skill/tree/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill
Before you install: CAUTION (1 skill is over a size limit; 1 skill bundles scripts; 1 skill states no license)

skillfetch scan https://github.com/leonxlnx/taste-skill/tree/12af471f…/skills/taste-skill@12af471f627f
1 skill · index: ~/.skillfetch/index (2785 skills, extraction openrouter/openai/gpt-6-luna)

  severity  count  problem
  medium        1  SIZE_WARNING         skills over a size limit (SKILL.md tokens, files or MB)
  low           1  LINT_WARNING         skills with lint warnings only
  low           1  NO_LICENSE           skills that state no license
  info          1  HAS_SCRIPTS          skills that bundle scripts
  info          1  SCAN_INFO            skills with injection-scan notes (links, quoted phrases)
  info          1  DATED                skills with lines that state a year or version (check them)

[…]

SIZE_WARNING  taste-skill
  SKILL.md is ~9,874 tokens (over 8,000); 39 files (over 20); 2.4 MB in total (over 1 MB)
```

**Why size matters.** In Stage 13, eight popular skills (this one among them) were
installed in `.claude/skills`. All three sessions on the landing-page task ended at the
40-turn limit with an empty final answer, at $3.09–$3.28 each. In one of them, 26 tool calls
read files of this skill (39 files, 2.4 MB). Details:
[numbers.md §26](docs/writeup/numbers.md#26-stage-13-popular-skills-installed-the-router-or-neither).

**The released index, scanned** (2,785 skills, 2,281 canonical;
[numbers.md §25](docs/writeup/numbers.md#25-index-scan-the-scan-rules-over-the-released-index)).
The index admitted only skills that pass lint and its injection scan; its build rejected
143 more (lint 110, injection scan 33).

| check | all indexed | canonical |
|---|---:|---:|
| injection-scan warning | 1.9% | 2.1% |
| of which remote instructions | 0.4% | 0.5% |
| size warning | 2.4% | 2.9% |
| bundles scripts | 9.0% | 11.0% |
| no license | 86.5% | 84.1% |
| states a year or version | 32.0% | 33.6% |

**Contradictions.**
- **Public copies:** the check runs once the index is installed (`skillfetch sync`: metadata
  and extracted constraints, no skill bodies). `scan` then matches each installed skill to
  the index by content hash, so it needs no model.
- **Other skills:** `--claude-code` extracts their instructions with your own Claude Code
  login (one isolated `claude -p` per skill); `--with-api --model anthropic/<model>` uses
  the API (paid). Without either, that part is skipped and the report says so.
- **Precision:** a pair is a `conflict` only when the two instructions cannot both be
  followed. Anything less certain is `needs_review`, and pairs a judge model found
  independent are not shown.

```console
$ skillfetch scan path/to/skills --json                   # machine-readable, with the advice
$ skillfetch scan path/to/skills --fail-on conflict,scan  # exit 1 for CI
$ skillfetch scan tests/fixtures/skills                   # the labelled fixture corpus
```

> Status: `scan` and the measurements are the product. v0.1 shipped `scan`, the public
> index and the write-up ([English](docs/writeup/post-en.md), [한국어](docs/writeup/post-ko.md)).
> The index covers anthropics/skills, UASL and four more repositories: 2,785 skills indexed
> (1,724 from the first two, as in the write-up, plus 1,061). Index update (Stage 11): this
> index, built as index-staging-4, passed the release gate fixed before Stage 11
> ([numbers.md §20](docs/writeup/numbers.md#20-stage-9-index-expansion-after-the-post-freeze),
> [§22](docs/writeup/numbers.md#22-stage-11-index-staging-4-release-gate-remeasured-after-the-post-freeze)).
> The per-task router below is experimental. Numbers: [`docs/writeup/numbers.md`](docs/writeup/numbers.md).

## Experimental: per-task routing

skillfetch can also serve skills per task. You install one MCP server and one router
skill. For every task, the agent:
1. searches the pre-indexed corpus;
2. assembles a conflict-free set;
3. uses it for that task;
4. moves on.

Nothing piles up in `~/.claude/skills`.

**Measured** in Stage 13: 18 tasks × 3 runs, judged blind
([numbers.md §26](docs/writeup/numbers.md#26-stage-13-popular-skills-installed-the-router-or-neither)).
- **Overall:** the router's results were the same as no skill: mean score 4.627 vs 4.618
  without the landing page, checks passed 52/54 vs 53/54.
- **Cost:** 62% more per session ($0.599 vs $0.370).
- **Where it was clearly better:** only on the landing-page design task (4.67 vs 3.00).
- **Popular skills installed:** with eight popular skills installed instead, the mean was
  4.725 without the landing page, and 1.33 on it.

```console
$ skillfetch serve                                        # MCP server over stdio
$ claude mcp add skillfetch -- uvx --from git+https://github.com/hyunlord/skillfetch skillfetch serve
```

The server loads the index once, at start. After `skillfetch sync` installs a new
index, restart the MCP server (in Claude Code: `/mcp`, or a new session) to use it.

Earlier measurements:
- **Stages 1–2, five task types** (landing page, test writing, backend API, documentation,
  data script): the router loaded the skill an expert would pick in 23 of 24 runs.
  - Only the design task came out differently with that skill. On the other four, no skill,
    the expert's skill and the router all passed every check.
  - The router cost 1.7–2.1 times the input tokens of no skill
    ([numbers.md §11](docs/writeup/numbers.md#11-router-in-real-sessions-end-to-end-stages-1-1b-and-2)).
- **Offline, 380 synthetic tasks:** top-50 recall 0.81 for the shipped router (0.75 on
  labels the search could not bias), up from 0.74 before this fix
  ([evals/retrieval](evals/retrieval/), [numbers.md §13](docs/writeup/numbers.md#13-retrieval-benchmark-380-synthetic-tasks)).
- **Firing:** with its current description it fired in 55 of 57 non-trivial sessions in a
  clean environment (39 of 57 with the previous one) and in 1 of 30 trivial ones
  ([numbers.md §15](docs/writeup/numbers.md#15-stage-5-what-makes-the-router-fire)).
- **Selection:** it picks a skill only when it can say in one sentence what the skill
  changes in the task. Offline, that raised none-accuracy on tasks no skill fits from 0.55
  to 0.85, and lowered the share of tasks with a relevant pick from 0.88 to 0.80
  ([numbers.md §17](docs/writeup/numbers.md#17-stage-6-choosing-none-after-the-post-freeze)).

Building the index yourself: `skillfetch ingest --sources sources.yaml --out
data/index --upstream-licenses`, then `skillfetch sync --pack data/index` for a
release tarball. Extraction (`--with-api`) defaults to the `claude-code/<model>`
backend, which queues each request under `~/.skillfetch/claude-code-queue/` for a
Claude Code session to answer; `--model openrouter/<vendor>/<model>`,
`anthropic/<model>` or `openai/<model>` call an API instead (`pip install
'skillfetch[ingest]'`). Every skill is extracted once and cached in
`~/.skillfetch/extract-cache/`.

### Always fire

In a repository you control, one line in the project's `CLAUDE.md` made the router fire
in 57 of 57 non-trivial sessions (39 of 57 without it, mean session cost $0.533 vs $0.396).
That was measured with the router's previous description; together with the current one
it is not measured ([numbers.md §15](docs/writeup/numbers.md#15-stage-5-what-makes-the-router-fire)).

```markdown
Before your first tool call on any coding task in this repository (anything beyond a one-line edit, a rename or a question), run the `skillfetch-router` skill and follow its steps.
```

### Other MCP clients

`skillfetch serve` is a stdio MCP server. In Codex, register the command and its
arguments (`codex mcp add`, or `~/.codex/config.toml`):

```console
$ codex mcp add skillfetch -- /path/to/skillfetch serve --index ~/.skillfetch/index
```

```toml
[mcp_servers.skillfetch]
command = "/path/to/skillfetch"
args = ["serve", "--index", "/path/to/.skillfetch/index"]
```

For the router, put the When, Steps and Rules of `assets/router-skill/SKILL.md` into the
project's `AGENTS.md` as plain instructions (merged into an existing one, not over it),
and replace step 2, which names Claude Code's `ToolSearch`. With `approval_policy =
"never"`, Codex refuses the MCP calls; let it run skillfetch's tools with
`default_tools_approval_mode = "approve"` under `[mcp_servers.skillfetch]`.

Measured ([numbers.md §16](docs/writeup/numbers.md#16-codex-after-the-post-freeze)): in 19
of 19 Codex sessions with router steps 1–4 in AGENTS.md, the agent searched and loaded
skills. With the whole router in AGENTS.md, 57 of 57 sessions searched and a relevant skill
was loaded in 26 of 51 sessions on the 17 tasks that have one (Claude Code on the same tasks
and labels: 37 of 51). With the shipped S-b′ router, Codex loaded nothing in 4 of the 6
sessions on the two tasks no skill fits (6 of 6 before) and a relevant skill in 22 of 51.

### How routing works

| | |
|---|---|
| **Vetted corpus** | Public skills are snapshotted, linted, scanned for prompt-injection patterns, and tiered. Ranking is by vetting, not install count. |
| **Pre-extracted constraints** | Each skill's instructions are extracted once, offline, into typed constraints with polarity and scope — "forbid emoji in headers", not a bag of keywords. |
| **Conflict-free sets** | `resolve_set` drops candidates that contradict or duplicate each other. Every exclusion comes with the two quoted source lines that caused it. Skills you name yourself are always kept. |
| **Per-task, no model at runtime** | BM25 over the index; your host model is the reranker. |

## The problem

Skills are great until you have thirty of them. Then two of them disagree —
one says "squash commits", another says "never squash" — and your agent quietly
picks one. Existing skill linters check frontmatter and broken links; none of
them check whether two skills contradict each other. Existing skill routers
(UASL, skill-search) hand you one skill, or a list. Searching and loading skills
mid-task without installing them is not unique to skillfetch:
[Skillselion](https://skillselion.com) is an MCP server that does it, ranking skills
by skills.sh install counts (a measured comparison is in
[numbers.md §19](docs/writeup/numbers.md#19-stage-8-skillselion-comparison-after-the-post-freeze)). What skillfetch adds is what admits a skill to the
index (automated vetting: lint, injection scan, license, not install counts), a
conflict check on the set it loads, and published measurements of whether loading
helped.

## Roadmap

- [x] **v0.1** `skillfetch scan <dir>` — conflict/duplicate report for a local
      skills directory, with evidence; first public corpus index.
  - [x] fixture corpus with labelled conflicts and duplicates; `resolve/` rules
        and `resolve_set`, conflict precision 1.0 on fixtures
  - [x] lint, injection scan, dedup by content hash, `skillfetch scan` with
        `--json` and `--fail-on`
  - [x] constraint extraction through the API (`ingest --with-api`, extract
        cache, cost log) and `--calibrate` against the fixtures
  - [x] pass calibration with a real model run (conflict precision 1.0 hard,
        informative-pair accuracy ≥ 0.85 soft: 0.912 with extraction v6), plus a
        hand-labelled holdout from public skills (`ingest --holdout`)
  - [x] let `scan` use the index and cached extractions instead of `constraints.json`
  - [x] public corpus ingest (`skillfetch ingest --sources sources.yaml`,
        snapshots, licenses, upstreams): anthropics/skills + all 1812 UASL skills
  - [x] write-up of the public-corpus scan ([`docs/writeup/post-en.md`](docs/writeup/post-en.md),
        [`post-ko.md`](docs/writeup/post-ko.md))
  - [x] keyword-Jaccard dedup groups, tiers A/B/C, index layout and manifest
        (index-format §1.6–§2)
- [ ] **v0.2** `skillfetch serve` — MCP server (`search_skills`, `resolve_set`,
      `load_skills`, …) + the one router skill you install.
  - [x] index without bodies: per-file sha256 manifest + pinned fetch base
  - [x] index loader (manifest-verified) and BM25 `search_skills` with profile boosts
  - [x] `resolve_set` over index constraints (pinned `path:` skills linted and scanned)
  - [x] `load_skills`: fetch from the pinned source, verify every hash, cache under
        `~/.skillfetch/cache/`, refuse mismatches
  - [x] MCP server (`skillfetch serve`) with `profile_repo`, `search_skills`,
        `resolve_set`, `load_skills`
  - [x] router skill (`assets/router-skill/SKILL.md`; restates the task in English)
  - [x] end-to-end run in Claude Code: search_skills → resolve_set → load_skills
  - [x] judge verdicts stored in the index (`pairs.jsonl`); `resolve_set` drops
        warnings judged independent (`suppressed_by_judge`)
  - [x] `sync` command: the index as a GitHub release tarball, sha256- and
        manifest-verified into `~/.skillfetch/index`
  - [ ] surface the `complementary` hint in `resolve_set` output
- [ ] **v0.3** process-skill retrieval: a domain query and a how-to-work query,
      searched separately ([#25](https://github.com/hyunlord/skillfetch/issues/25));
      a shorter chain: search, resolve and load in fewer calls
      ([#26](https://github.com/hyunlord/skillfetch/issues/26)); `report_outcome`.

## Experiment artifacts (`evals/e2e/`)

The end-to-end experiments behind [numbers.md](docs/writeup/numbers.md) §11–§20, stages 0–9
(Stage 10 follows when its judging is done). Each stage folder holds what was fixed before the
run and what came out of it:

- **Before the run:** `DESIGN.md`, `FROZEN*.sha256`, task definitions (`tasks*.jsonl`,
  `tasks*.yaml`) and rubrics.
- **Results:** `report*.md`, `metrics*.json`, unblinded scores and keys, and label files (`oracle*`,
  `gpt-*`).
- **Scripts:** `scripts/`.
- **Sessions:** `derived/sessions.jsonl`, one row per session.

| folder | what | numbers.md |
|---|---|---|
| `stage0`, `stage0.5` | first end-to-end runs | – |
| `stage1`, `stage1b`, `stage2` | router in real Claude Code sessions | §11 |
| `retrieval` | embedding check, retrieval set-up | §12, §13 |
| `stage3` | retrieval benchmark (380 tasks), shipped router rule, cross-model labels | §13 |
| `stage4`, `stage5` | clean vs author's environment; what makes the router fire | §14, §15 |
| `codex` | Codex sessions, Codex as third judge for stage 6b | §16, §17 |
| `stage6`, `stage7`, `stage8` | choosing none; working direction; Skillselion comparison | §17–§19 |
| `stage9`, `staging` | index expansion | §20 |
| `router-e2e.json` | the export numbers.md §11–§12 read | §11, §12 |

**Not here, and why.**

- **Third-party skill bodies.** The index does not redistribute skill bodies; `load_skills`
  fetches them from each skill's source. Session transcripts, judge packages, raw MCP
  results and Codex observation files contain the loaded `SKILL.md` text, so they are not
  published. Each session is a row in `derived/sessions.jsonl` instead, with:
  - model and Claude Code version, turns, cost and tokens;
  - how many tools, MCP servers, plugins and skills the environment had;
  - the sequence of tool calls (tools other than built-ins and skillfetch are generalised);
  - the skillfetch queries and the skill ids that were resolved and loaded.
- **Transcript text.** For the same reason, and because transcripts carry the environment below.
- **The author's environment.** Some sessions ran in the author's own Claude Code setup ("E2").
  Its MCP servers, plugins, connectors, hook output, file paths and account details are not
  published:
  - name lists became counts or `<E2 plugin>` / `<E2 MCP server>` / `<E2 hook text>`;
  - paths became `<e2e>`, `<home>`, `<worktrees>`, `<tmp>`;
  - the credentials file became `<credentials file>`.

  `evals/e2e/sanitized.tsv` lists each changed file with its original and published sha256 and
  what changed. The scripts' code that skips `.omc/` and `graft/` folders is kept as written.
- Also left out: session workspaces, logs, screenshots, raw model replies and the task repositories.

Before publishing, every file was scanned:
- credential-shaped strings: none;
- the author's paths, user name and environment names in documents and scripts: none;
- body text of the 28,856 `SKILL.md` files seen in the experiments: no file with three or
  more prose lines.

**Release asset.** Label and result files over 1 MB and the judge-package diffs (316 files)
are in the release asset `e2e-artifacts-2026-10-25`. `evals/e2e/ASSETS.tsv` lists each one
with its sha256. For a diff it also names the repository it was made in and that repository's
license:
- `fastapi/full-stack-fastapi-template`, MIT;
- `vercel/next.js` `examples/with-typescript`, MIT;
- the stage 2 repositories written for this experiment, MIT as this repository.

`scripts/fetch_e2e_assets.sh` downloads the tarball, checks its sha256 and each file's, and
unpacks the files in place (`evals/e2e/.gitignore` keeps them out of git).

**Checking the frozen hashes.** Each `FROZEN*.sha256` was written over the original files
before a run. `uv run python scripts/verify_e2e_frozen.py` compares them:
- a published file matches its frozen hash, or, if it was changed before publishing, its
  original hash in `sanitized.tsv`;
- files edited in the workspace after freezing are reported as superseded when a later
  `FROZEN` file of the stage lists them (stage 2's `FROZEN.after-fix`, stage 9's run-1 list).

With the asset unpacked: 410 ok, 17 ok through `sanitized.tsv`, 9 superseded, 51 not
published (logs, screenshots), 0 mismatches.

**Reproducing.**
- The scripts ran from the stage folder in the experiment workspace. In the published copy,
  `<e2e>` stands for `evals/e2e/` and `<worktrees>` for the folder of per-session git
  worktrees.
- Sessions need:
  - the Claude Code CLI (its version is in each `derived/sessions.jsonl` row);
  - for the `codex` stages, the Codex CLI;
  - `uv` and Node;
  - Postgres for the fastapi tasks;
  - the task repositories at the commits named in each stage's report.
- Model calls are isolated `claude -p` runs on a Claude Code plan; numbers.md §7 gives their
  API-price equivalent.

| variable | read by | purpose |
|---|---|---|
| `GITHUB_TOKEN` | `stage8/scripts/ss_client_env.py` | read-only fine-grained token, passed only to the Skillselion MCP server's process (the frozen `ss_client.py` read it from a local file) |
| `PGBIN` | `stage1/checks/run_check.py`, `stage1/scripts/screenshot.py` | Postgres binaries for the fastapi task databases |
| `BOOKMARKS_DB` | `stage2/reference/api/app/main.py` | SQLite file of the stage 2 API reference |
| `S4_ROUND`, `READAPT_PASS` | `stage4/scripts/adapt_tasks.py`, `prep_oracle.py`, `readapt_missing.py` | which preparation round or pass to run |
| `REP` | `stage6/scripts/select_cands.py` | repetition number of an offline selection run |
| `S9_RUN` | `stage9/scripts/s9_common.py` | output folder: `""` (run 1), `run-b`, `run-c` |

## Design docs

- [`CLAUDE.md`](CLAUDE.md) — scope, tool surface, non-goals, working rules
- [`docs/design/index-format.md`](docs/design/index-format.md) — ingestion pipeline, tiers, index layout
- [`docs/design/constraints.md`](docs/design/constraints.md) — constraint schema, conflict rules, `resolve_set`

## Conflict cap

A conflict is reported only when the rules are sure. By default
(`--conflict-cap all`) a pair where either rule has no object ("never use
emoji" vs "always use emoji") is `needs_review`, not `conflict`: on public
skills such blanket rules are mostly misreadings of narrower lines, and every
false conflict we found was one. `--conflict-cap vocabulary` (on `scan` and
`ingest`) lets a blanket rule about a controlled-vocabulary term conflict. It
finds 19 instead of 11 of the hand-labelled fixture conflicts, and in our
measurements it produced one false conflict on 200 public skills, where the
default produced none. Use it when recall matters more than precision.

## Honest limits

- The index is small. On our 380-task benchmark, 129 of the 323 tasks that have a
  relevant skill had one only outside the index, measured against Skillselion's
  catalog; 61 of 331 once our own top 50 was graded too
  ([numbers.md §19](docs/writeup/numbers.md#19-stage-8-skillselion-comparison-after-the-post-freeze)).
- The injection scan is a blocklist, not a proof of safety.
- Automated vetting rejects bad skills; it does not prove a skill is good.
- Default mode injects skill text into the current context; true isolation
  requires a subagent runner, which is not built.
- `sync` verifies the tarball against a sha256 published in the same GitHub release;
  it trusts whoever can write this repo's releases. The index is not signed yet
  ([#32](https://github.com/hyunlord/skillfetch/issues/32)).
- `load_skills` no longer puts a precedence header before the skills: it had no
  effect on which skill the agent follows when two disagree (measured: 112 of 260
  runs followed the skill it ranked first; [numbers.md §8](docs/writeup/numbers.md)).
- Embeddings (all-MiniLM-L6-v2) were evaluated against BM25 and not adopted: no
  gain (top-50 recall 0.74 with BM25 + embedding fusion, 0.71 with BM25 alone, on 34
  router queries; [numbers.md §12](docs/writeup/numbers.md#12-embedding-retrieval-not-adopted)).
  Re-evaluated on the 380-task benchmark: +0.026 recall@50 (§13).
- When nothing in the index fits the task, the router can still load something. With the
  shipped selection rule: offline none-accuracy 0.85 on the 85 such tasks (0.825 on the 40
  trivial requests), nothing loaded in 9 of 9 Stage 6 sessions on such tasks, and
  something loaded in 2 of 6 Codex sessions (before: 0.55 and 0.65 offline, 30 of 95
  such tasks in the earlier benchmark, 4 of 24 Stage 4 sessions in each environment,
  every searching Stage 5 session but one, 5 of 9 in Stage 6, 6 of 6 in Codex;
  §13–§17). The rule also picks a relevant skill less often (hit 0.88 → 0.80 offline).
- In real repositories the router with its previous description fired on 40% of
  non-trivial tasks: 23 of 57 sessions in a clean environment, 22 of 57 with 14 MCP
  servers, 134 skills and hooks (per-task difference +0.018 on these tasks), and on 0
  of 30 and 1 of 30 trivial ones (the current description: 55 of 57 and 1 of 30 in the
  clean environment, §15; the author's environment not measured). When
  it loads, the set holds a relevant skill in 8 of 14 and 10 of 17 sessions
  ([numbers.md §14](docs/writeup/numbers.md#14-stage-4-router-in-real-repos-clean-vs-authors-environment)).
- Long requests (800+ chars) are summarised, not copied, into the fourth query: 0 of
  40 sessions copied them word for word, against 100 of 120 under 400 characters
  ([numbers.md §15](docs/writeup/numbers.md#15-stage-5-what-makes-the-router-fire),
  #48).
- On four of five task types we measured, the expert skill changed nothing the
  checks could see; load a skill when the base model is weak at the domain, not by
  default.
- Semantic conflicts without a shared subject are not detected in v0.1.
- Mutually exclusive choices ("always use npm" vs "always use pnpm") are caught
  only for the tooling slots marked exclusive (package manager, formatter, test
  runner, build tool) and only between known alternatives of the same
  ecosystem. An unknown tool in one of those slots is `needs_review`; other
  subjects, such as naming conventions, are never treated as exclusive.
- When the rules are unsure, they report `needs_review`, never `conflict`.
- A conflict is only reported when both rules are clear. It is downgraded to
  `needs_review` when one rule conflicts with three or more skills (more likely
  a misread than a real contradiction), when its line is a double negative
  under a "Don't" heading, when its line names something narrower than its
  subject, or when it is a blanket rule about a subject outside the controlled
  vocabulary.

### Cases we get wrong

The two `conflict` findings left in the full public-corpus build (anthropics/skills
+ all 1812 UASL skills at `2a76bf42ce5c`, extraction v6, default cap) are both false.
We record them instead of tuning the rules to them:

- **caveman-review ⟷ saga**, subject `response-length`.
  - caveman-review, SKILL.md:51: "Drop terse mode for: security findings (CVE-class
    bugs need full explanation + reference), architectural disagreements …, and
    onboarding contexts …"
  - saga, SKILL.md:394: "Skip verbose explanations, focus on deliverables"
  - Why it is wrong: both rules are situational — detail for security findings in a
    code review, brevity in saga's autonomous (AUTORUN) mode. Extraction kept the
    situation only in `object_raw`, which the rules do not compare, so the two read as
    "require detailed" vs "forbid detailed".
- **darwin ⟷ thinking-ooda**, order `observation` before / after `action`.
  - darwin, SKILL.md:37: "**Principles:** Observe before acting · …"
  - thinking-ooda, SKILL.md:108: "Immediately return to OBSERVE" (and :219, "Mandate
    observe after act")
  - Why it is wrong: OODA is a loop: observing after acting is the next cycle's
    observing before acting. Order constraints have no notion of a cycle, so "observe
    after act" reads as the reverse of "observe before act".

## License

skillfetch is MIT ([`LICENSE`](LICENSE)). The skills it indexes belong to their
authors and keep their own licenses: the index holds their metadata, extracted
constraints with short evidence quotes and file hashes, never their files;
`load_skills` fetches each body from its pinned source.
