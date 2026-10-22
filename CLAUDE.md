# skillfetch — project instructions for Claude Code

Read this file fully before touching code. It is the spec. Design details live in
`docs/design/` — read those before implementing the module they describe.

## What this is

**Zero-install skills for coding agents.** The user installs nothing but this MCP
server. For each task, the agent:

1. describes the task (what it is, which stack, which files) and searches a
   curated, pre-indexed corpus of SKILL.md files,
2. picks candidate skills, then asks `resolve_set` to drop the ones that
   contradict or duplicate each other (and always keep the ones the user pinned),
3. loads the resulting set — into the main context (default) or into a fresh
   subagent (isolation mode) — and does the work,
4. moves on. The next task searches again. Nothing accumulates in
   `~/.claude/skills`.

The product has two halves that must stay decoupled:

- **Offline ingestion** (runs on CI / cron, uses the Claude API): snapshot public
  skill sources → lint → injection scan → extract constraints, keywords,
  synthetic queries → assign trust tier → emit a versioned index.
- **Runtime MCP server** (runs on the user's machine, uses **no model**): BM25
  over the index, conflict resolution over pre-extracted constraints, body
  fetch. The index holds metadata, constraints and content hashes only; bodies
  are fetched by `load_skills` from each skill's source repo at the pinned
  commit, verified against the per-file sha256 in the index, and cached under
  `~/.skillfetch/cache/`. Claude is the reranker. Runtime latency budget:
  < 200 ms per tool call excluding the host model (a first `load_skills` of an
  uncached skill also waits for the fetch).

## Positioning (why this exists — keep README consistent with this)

- Existing `skill-lint`-style tools check frontmatter, links, token counts.
  **They do not check whether two skills give opposite instructions.** We do.
- Existing routers (UASL, skill-search) load one skill, or hand Claude a list.
  **They do not build a conflict-free *set*, scope it to one task, or record
  whether it helped.** We do.
- Existing registries rank by install count. **We gate by automated vetting.**
- We do NOT claim to be the first per-prompt skill router. We are not.

## Non-goals for v0.1 (do not build these, even if they seem small)

- No embedding model, no vector DB, no local LLM at runtime.
- No automatic UserPromptSubmit hook. Routing is model-initiated via MCP tools.
- No skill "fusion" (merging two SKILL.md into one). Sets are concatenations with
  precedence, nothing more.
- No skill self-generation from task history.
- No GUI, no web service. CLI + MCP only.
- Runtime network access is limited to fetching skill bodies from their pinned
  source; a hash mismatch is refused. Search and `resolve_set` read the local
  index only.

## Repository layout (target)

```
skillfetch/
  CLAUDE.md                     this file
  README.md
  docs/design/
    index-format.md             ingestion pipeline, skill record schema, manifest, tiers
    constraints.md              claim schema, extraction prompt, conflict rules, resolve_set
  src/skillfetch/
    ingest/                     offline: sources, lint, scan, extract, index build
    index/                      index loading, BM25 search, tag filters
    resolve/                    conflict/redundancy resolution
    mcp/                        MCP server exposing the tool surface below
    cli.py                      `skillfetch scan|ingest|judge|obedience|sync|serve`
  assets/
    router-skill/SKILL.md       the one always-on skill the user installs
    runner-agent.md             the one subagent definition for isolation mode
  tests/
    fixtures/skills/            small hand-written SKILL.md corpus with known conflicts
  data/                         gitignored; local mirror lives in ~/.skillfetch/
```

Python 3.11+, `uv` for env, `ruff` for lint, `pytest`. Single package, no
monorepo. Keep dependencies minimal: `mcp`, `pyyaml`, `rank-bm25` (or a tiny
hand-rolled BM25), `anthropic` (ingest only, optional extra), `pydantic`.

## MCP tool surface

Built (v0.2): `profile_repo`, `search_skills`, `resolve_set`, `load_skills`.
Planned for v0.3, not built: `prepare_set`, `report_outcome`.

| tool | input | output |
|---|---|---|
| `profile_repo(path)` | repo root | `{languages, frameworks, package_managers, tags[]}` from manifest files only (package.json, pyproject.toml, go.mod, Cargo.toml, framework config files). Never scans source. Cached per session. |
| `search_skills(query, profile?, k=50, tiers=["A","B"], verbose=false)` | task description written by the host model + optional profile | ranked candidates, compact: `{id, title, summary (first sentence, ≤160 chars), tier, token_estimate}` (50 fit in ~4k tokens); `verbose` adds the full summary, `tags` and `match_reasons[]` |
| `resolve_set(auto_ids[], pinned_ids[])` | candidate ids chosen by the host model, plus user-pinned ids | `{set_id, included[], excluded[{id, reason, conflicts_with}], warnings[], precedence[]}` |
| `load_skills(set_id, max_tokens=8000)` | | bodies concatenated with a precedence header, for injection into the current context. Each body is fetched from the skill's pinned source (unless cached), verified against the index hashes, and cached under `~/.skillfetch/cache/<content_hash>/`; a mismatch or fetch failure refuses that skill with a structured error and the others still load. Over `max_tokens` the lowest-precedence skills are dropped (listed in `errors`). |
| `prepare_set(set_id)` (v0.3) | | `{prompt_block, materialized_paths{}}` for the isolation runner; the folder is fetched and verified like `load_skills` and materialized under `~/.skillfetch/cache/<content_hash>/` |
| `report_outcome(set_id, ok: bool, note?)` (v0.3) | | ack. Only appends to a local JSONL log; nothing reads it yet. |

Rules:

- `search_skills` does BM25 over `title + description + keywords + synthetic_queries +
  summary` (bodies are not in the index); tokens are Unicode words, CJK runs as
  2-grams. Profile tags are a boost/filter, never part of the query string.
- `resolve_set` follows `docs/design/constraints.md` exactly. Pinned beats auto.
  Pinned-vs-pinned conflicts are reported, never auto-resolved.
- Pinned ids may be local paths (`path:/abs/path/to/skill`). Those are linted and
  injection-scanned at resolve time (a failure refuses them); their constraints come
  from the extract cache when it has them (`skillfetch ingest <dir> --with-api` puts
  them there). The server never extracts: without a cache entry the skill is included
  with a note and no constraints, so it is not conflict-checked.
- `resolve_set` uses the conflict cap the index was built with (`manifest.conflict_cap`).
- Every tool returns JSON. No prose in tool results.

## Router skill (`assets/router-skill/SKILL.md`)

The only skill a user installs. Short (< 60 lines). It tells the host model:

1. Before non-trivial work, restate the task in one sentence including stack and
   target files, then call `search_skills` with that sentence.
2. Pick 1–3 candidates by reading all 50 summaries, weighing `token_estimate` against
   `load_skills`' budget. If the user named a skill, find its id with
   `search_skills` (the result whose title matches) and pass it as pinned.
3. Call `resolve_set`, then `load_skills` (default). From v0.3: `prepare_set` +
   delegate to the `skillfetch-runner` subagent when the task is self-contained and
   the user asked for isolation (or the project config sets `isolate: true`).
4. From v0.3, after the task, call `report_outcome`.
5. Skip the search only for trivial edits: a one-line edit in a single file, a rename,
   or answering a question. Bug fixes, docs and config changes are not trivial.

## Runner agent (`assets/runner-agent.md`)

One static subagent definition, installed once into `~/.claude/agents/`. No
`skills:` field. System prompt: follow the skill instructions passed in the
prompt, do the task, report back concisely. Isolation = fresh context per
invocation; the host passes task + skill block + explicit context (file paths,
decisions). Document plainly in README that true context isolation requires
this mode; default injection mode leaves skill text in the transcript.

## Roadmap (build in this order; each step must ship and be demoable alone)

**v0.1 — `scan` + corpus v0** (target: 1 week)
- `skillfetch ingest <source>`: sources = local dir, git repo URL, UASL/skills.sh
  snapshot. Output: index dir + manifest.
- `skillfetch scan <dir>`: run the same pipeline on a local skills dir and print
  a conflict/duplicate report **with quoted evidence lines from both skills**.
- Fixture corpus with ≥ 10 known conflicts and ≥ 5 known duplicates; tests assert
  precision = 1.0 on fixtures (we optimize precision over recall in v0.1).
- Deliverable for launch: a scan of the top-N public skills + a short write-up.

**v0.2 — `serve`** (+1 week)
- MCP server with the six tools, router skill, `sync` command for the index.
- End-to-end demo in Claude Code: search → resolve → load → work.

**v0.3 — isolation + feedback** (+1 week)
- Runner agent, `prepare_set`, outcome log, and a first on/off comparison on a
  small verified task set. This is where we find out whether auto-loaded unknown
  skills actually help on average. Report it honestly either way.

## Working rules for Claude Code in this repo

- Read `docs/design/*.md` before implementing the matching module. If a design
  doc is wrong or incomplete, update the doc in the same commit as the code.
- Precision over recall everywhere in v0.1. A false "conflict" costs more trust
  than a missed one. When unsure, emit `needs_review`, not `conflict`.
- Every judgement the tool makes must be explainable with quoted source lines.
  No score without evidence.
- Tests first for `resolve/`. The fixture corpus is the contract.
- No network calls in tests. Ingestion against the API is behind `--with-api`.
- Keep the two halves decoupled: nothing under `src/skillfetch/index/`,
  `resolve/`, or `mcp/` may import `anthropic` or any model client.
- Commit small. One feature per commit. Conventional commit prefixes
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- When you finish a roadmap item, update the checklist in README.
