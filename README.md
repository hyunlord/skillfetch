# skillfetch

**Zero-install skills for coding agents.** Install one MCP server. For every
task, your agent searches a vetted, pre-indexed corpus of `SKILL.md` files,
assembles a *conflict-free* set, uses it for that task, and moves on. Nothing
piles up in `~/.claude/skills`.

Measured: on design tasks the router matched an expert-installed skill; on process-style tasks (planning, brevity) it does not find the skill yet; it costs about seven extra turns per task. Details in the write-up, section 5.

> Status: v0.1 is done: `scan`, the public index and the write-up
> ([English](docs/writeup/post-en.md), [한국어](docs/writeup/post-ko.md)). v0.2:
> the MCP server works end to end and the index ships as a GitHub release
> (`skillfetch sync`). The index covers anthropics/skills and UASL: 1,724 of
> 1,831 discovered skills are indexed. Numbers: [`docs/writeup/numbers.md`](docs/writeup/numbers.md).

Check the skills you already have. `sync` downloads the index (metadata and
extracted constraints, no skill bodies; a 3 MB download); `scan` matches each installed
skill to the index by content hash, so it needs no model and no API key:

```console
$ uvx --from git+https://github.com/hyunlord/skillfetch skillfetch sync
installed: ~/.skillfetch/index from hyunlord/skillfetch@index-2026-10-22 (skillfetch-index-20261022T061543Z.tar.gz) · 1724 skills · built 2026-10-22T06:15:43Z · extraction openrouter/openai/gpt-6-luna
$ uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan .claude/skills
skillfetch scan .claude/skills
30 skills · lint: 30 ok, 0 failed · injection scan: 30 ok, 0 failed, 21 with warnings · scripts: 4
constraints: 30 analyzed (index 30), 0 skipped
index: ~/.skillfetch/index (1724 skills, extraction openrouter/openai/gpt-6-luna)

[… 2 LINT_WARNING, 21 SCAN_WARNING (bare URLs) and 4 HAS_SCRIPTS blocks …]

NEEDS_REVIEW  eval-harness ⟷ receiving-code-review
  subject: implementation   scope: code / implement
  eval-harness:127         "Write code to pass the defined evals."
  receiving-code-review:44 "STOP - do not implement anything yet"

summary: 0 conflict, 0 redundant, 0 tension, 1 needs_review, 0 duplicate, 0 lint_failed, 0 scan_failed
```

That is a real run (excerpt) over 30 public skills picked at random from UASL
and installed as a user has them. Every finding quotes the line from each
skill. The rules are tuned for precision: a pair is a `conflict` only when the
two instructions cannot both be followed; anything less certain is
`needs_review`, and pairs a judge model found independent are not shown.
Skills the index does not cover are listed as skipped; `--with-api --model
anthropic/<model>` extracts them (calls the API, cached once per skill).

The router, measured in real Claude Code sessions on five task types (landing page, test writing, backend API, documentation, data script): it loaded the skill an expert would pick in 23 of 24 runs. Only the design task came out differently with that skill; on the other four, no skill, the expert's skill and the router all passed every check. The router costs 1.7–2.1 times the input tokens of no skill ([numbers.md §11](docs/writeup/numbers.md#11-router-in-real-sessions-end-to-end-stages-1-1b-and-2)). Offline, on 380 synthetic tasks, the shipped router: top-50 recall 0.81 (0.75 on labels the search could not bias), up from 0.74 before this fix ([evals/retrieval](evals/retrieval/), [numbers.md §13](docs/writeup/numbers.md#13-retrieval-benchmark-380-synthetic-tasks)). scan and sync are unaffected.

```console
$ skillfetch scan path/to/skills --json                   # machine-readable
$ skillfetch scan path/to/skills --fail-on conflict,scan  # exit 1 for CI
$ skillfetch scan tests/fixtures/skills                   # the labelled fixture corpus
$ skillfetch serve                                        # MCP server over stdio
$ claude mcp add skillfetch -- uvx --from git+https://github.com/hyunlord/skillfetch skillfetch serve
```

The server loads the index once, at start. After `skillfetch sync` installs a new
index, restart the MCP server (in Claude Code: `/mcp`, or a new session) to use it.

Building the index yourself: `skillfetch ingest --sources sources.yaml --out
data/index --upstream-licenses`, then `skillfetch sync --pack data/index` for a
release tarball. Extraction (`--with-api`) defaults to the `claude-code/<model>`
backend, which queues each request under `~/.skillfetch/claude-code-queue/` for a
Claude Code session to answer; `--model openrouter/<vendor>/<model>`,
`anthropic/<model>` or `openai/<model>` call an API instead (`pip install
'skillfetch[ingest]'`). Every skill is extracted once and cached in
`~/.skillfetch/extract-cache/`.

## Other MCP clients

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
and replace step 2, which names Claude Code's `ToolSearch`.

Verified: one `search_skills` call from Codex; automatic firing not measured.

## The problem

Skills are great until you have thirty of them. Then two of them disagree —
one says "squash commits", another says "never squash" — and your agent quietly
picks one. Existing skill linters check frontmatter and broken links; none of
them check whether two skills contradict each other. Existing skill routers
hand you one skill, or a list; none of them build a set that is safe to load
together, scope it to one task, or tell you afterwards whether it helped.

## What skillfetch does

| | |
|---|---|
| **Vetted corpus** | Public skills are snapshotted, linted, scanned for prompt-injection patterns, and tiered. Ranking is by vetting, not install count. |
| **Pre-extracted constraints** | Each skill's instructions are extracted once, offline, into typed constraints with polarity and scope — "forbid emoji in headers", not a bag of keywords. |
| **Conflict-free sets** | `resolve_set` drops candidates that contradict or duplicate each other. Every exclusion comes with the two quoted source lines that caused it. Skills you name yourself are always kept. |
| **Per-task, no model at runtime** | BM25 over the index; your host model is the reranker. |

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
- The router loads something in 30 of the 95 benchmark tasks where nothing in the
  index fits (32%), and in 30% of the 40 trivial requests that need no skill
  ([numbers.md §13](docs/writeup/numbers.md#13-retrieval-benchmark-380-synthetic-tasks)).
- In real repositories the router fires on 40% of non-trivial tasks: 23 of 57
  sessions in a clean environment, 22 of 57 with 14 MCP servers, 134 skills and
  hooks (per-task difference +0.018 on these tasks), and on 0 of 30 and 1 of 30
  trivial ones. When
  it loads, the set holds a relevant skill in 8 of 14 and 10 of 17 sessions
  ([numbers.md §14](docs/writeup/numbers.md#14-stage-4-router-in-real-repos-clean-vs-authors-environment)).
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
