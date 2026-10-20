# skillfetch

**Zero-install skills for coding agents.** Install one MCP server. For every
task, your agent searches a vetted, pre-indexed corpus of `SKILL.md` files,
assembles a *conflict-free* set, uses it for that task, and moves on. Nothing
piles up in `~/.claude/skills`.

> Status: design phase. Nothing runs yet. See the roadmap below.

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
- [ ] **v0.2** `skillfetch serve` — MCP server (`search_skills`, `resolve_set`,
      `load_skills`, …) + the one router skill you install.
- [ ] **v0.3** isolation runner, outcome log, and an honest on/off comparison on
      a verified task set.

## Design docs

- [`CLAUDE.md`](CLAUDE.md) — scope, tool surface, non-goals, working rules
- [`docs/design/index-format.md`](docs/design/index-format.md) — ingestion pipeline, tiers, index layout
- [`docs/design/constraints.md`](docs/design/constraints.md) — constraint schema, conflict rules, `resolve_set`

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

## License

MIT
