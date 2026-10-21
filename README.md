# skillfetch

**Zero-install skills for coding agents.** Install one MCP server. For every
task, your agent searches a vetted, pre-indexed corpus of `SKILL.md` files,
assembles a *conflict-free* set, uses it for that task, and moves on. Nothing
piles up in `~/.claude/skills`.

> Status: early v0.1. `skillfetch scan` runs on a local skills directory
> (lint, injection scan, duplicate and conflict report). Constraint extraction
> through the API, the public corpus and the MCP server are not built yet.

```console
$ uv run skillfetch scan path/to/skills          # human-readable report
$ uv run skillfetch scan path/to/skills --json   # machine-readable
$ uv run skillfetch scan path/to/skills --fail-on conflict,scan   # exit 1 for CI
$ uv run skillfetch scan tests/fixtures/skills   # the labelled fixture corpus
```

Conflict analysis currently needs pre-extracted constraints in a
`constraints.json` next to each `SKILL.md` (see `tests/fixtures/`); skills
without one are linted and scanned, and listed as skipped.

Constraint extraction through the Claude API (needs `pip install
'skillfetch[ingest]'` and `ANTHROPIC_API_KEY` or `ant auth login`; results are
cached in `~/.skillfetch/extract-cache/`, each skill is extracted once):

```console
$ uv run skillfetch ingest tests/fixtures --with-api --calibrate   # measure the extractor
$ uv run skillfetch ingest path/to/skills --with-api               # extract + cost log
$ uv run skillfetch ingest tests/fixtures --with-api --calibrate --model openai/<model>
$ uv run skillfetch ingest dir --with-api --model openai/<model> --base-url http://localhost:8000/v1
```

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
| **Per-task, no model at runtime** | BM25 over the index; your host model is the reranker. Optional isolation mode runs the task in a fresh subagent with only the chosen skills. |

## Roadmap

- [ ] **v0.1** `skillfetch scan <dir>` — conflict/duplicate report for a local
      skills directory, with evidence; first public corpus index.
  - [x] fixture corpus with labelled conflicts and duplicates; `resolve/` rules
        and `resolve_set`, conflict precision 1.0 on fixtures
  - [x] lint, injection scan, dedup by content hash, `skillfetch scan` with
        `--json` and `--fail-on`
  - [x] constraint extraction through the API (`ingest --with-api`, extract
        cache, cost log) and `--calibrate` against the fixtures
  - [ ] pass calibration with a real model run (conflict precision 1.0 hard,
        informative-pair accuracy ≥ 0.85 soft); then let `scan` use cached extractions instead of
        `constraints.json`
  - [ ] public corpus ingest (`skillfetch ingest <source>`, `sources.yaml`,
        snapshots) and the top-N public skills scan + write-up
  - [ ] keyword-Jaccard dedup groups, tiers A/B/C, index layout and manifest
        (index-format §1.6–§2)
- [ ] **v0.2** `skillfetch serve` — MCP server (`search_skills`, `resolve_set`,
      `load_skills`, …) + the one router skill you install.
  - [ ] surface the `complementary` hint in `resolve_set` output
- [ ] **v0.3** isolation runner, outcome log, and an honest on/off comparison on
      a verified task set.

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
  requires the subagent runner (v0.3).
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

## License

MIT
