# skillfetch — project instructions for Claude Code

Read this file fully before touching code. It is the spec. Design details live in
`docs/design/` — read those before implementing the module they describe.

## What this is

**Skill vetting before you install, plus a measured study of what skills do for coding
agents.** Per-task routing is an experimental feature (below).

`skillfetch setup` puts three features into Claude Code (`src/skillfetch/setup.py`): it
registers the MCP server, installs the vet skill and syncs the index, after showing every change
and asking; `--remove` undoes it.

| feature | default | how |
|---|---|---|
| check before install | on | the vet skill (`assets/vet-skill`) calls `scan_skill` before a skill is installed or written into `.claude/skills`, shows the advice and license lines, and asks |
| find on request | on | the vet skill calls `find_skills` when the user asks for a skill, then scans the pick |
| auto-apply (per-task routing) | off | `setup --auto`: the router skill and the routing tools (`serve` without `--vet`) |

- **`skillfetch scan <dir | GitHub URL>`** checks skills before they are installed: lint,
  injection scan (including remote instructions), size, bundled scripts, dated claims, the
  license, duplicates and contradictions between skills, each with the line it comes from. A
  GitHub URL is shallow-cloned into a temporary folder and deleted; nothing is installed or
  run. The report opens with one line of advice (RECOMMENDED / CAUTION / NOT RECOMMENDED, from
  safety and quality only) and, under it, the license with where it was found
  (`docs/design/index-format.md` §5, §5.1). The same check runs as the MCP tool `scan_skill`
  and in CI (`.github/actions/skillfetch-scan`, `scan --markdown`). No model and no API key,
  except contradiction extraction for skills the index does not cover (`--claude-code`,
  `--with-api`).
- **`skillfetch find "<what you want>"`** / `find_skills`: index matches for a request the
  user made, with an advice from the index record and the URL to scan (§5.2).
- **The measurement study** is everything under `evals/` and `docs/writeup/numbers.md`: real
  Claude Code sessions, blind judging, the index scanned with the scan rules. Every number in
  README or the posts comes from numbers.md.
- **Per-task routing** (an MCP server plus one router skill that searches, resolves and
  loads skills for each task) is kept as an experimental feature; its spec is in
  "Experimental: per-task routing".

The product has two halves that must stay decoupled:

- **Offline ingestion** (runs on CI / cron, uses the Claude API): snapshot public
  skill sources → lint → injection scan → extract constraints, keywords,
  synthetic queries → assign trust tier → emit a versioned index.
- **Runtime** (`scan` and the MCP server, on the user's machine, **no model**): the checks
  above, BM25 over the index, conflict resolution over pre-extracted constraints, body
  fetch. The index holds metadata, constraints and content hashes only; bodies
  are fetched by `load_skills` from each skill's source repo at the pinned
  commit, verified against the per-file sha256 in the index, and cached under
  `~/.skillfetch/cache/`. Claude is the reranker. Runtime latency budget:
  < 200 ms per tool call excluding the host model (a first `load_skills` of an
  uncached skill also waits for the fetch).

## Positioning (why this exists — keep README consistent with this)

- Existing `skill-lint`-style tools check frontmatter, links, token counts.
  **They do not check whether two skills give opposite instructions.** We do. `scan` also
  flags remote instructions, size, bundled scripts and dated claims, and checks a GitHub
  repository without installing it.
- Existing registries rank by install count. **We gate by automated vetting.**
- **What the measurements say about routing** (numbers.md §26, Stage 13: 18 tasks × 3 runs,
  judged blind):
  - the router's results were the same as no skill: mean 4.627 vs 4.618 without the
    landing-page task, checks 52/54 vs 53/54;
  - it cost 62% more per session ($0.599 vs $0.370);
  - it was clearly better only on the landing-page design task (4.67 vs 3.00);
  - with eight popular skills installed instead, the mean was 4.725 without the landing page
    and 1.33 on it.

  So we do not claim that routing improves results. It stays experimental.
- **What the measurements say about knowledge in skills** (numbers.md §24): without any
  skill, the model answered 173 of 180 short factual questions taken from 30 skills that
  promise knowledge it may lack. It did not know the Opus 5.5 price, and one skill
  (`uasl/ai-dpia`) cites an EDPB document that was not found in the EDPB's list of
  guidelines. A skill's facts can be out of date or wrong, which is why `scan` marks dated
  claims.
- Existing routers (UASL, skill-search, Skillselion) load one skill, or hand Claude a list.
  The experimental router builds a conflict-free *set* per task. We do NOT claim to be the
  first per-prompt skill router. We are not.

## Non-goals for v0.1 (do not build these, even if they seem small)

- No embedding model, no vector DB, no local LLM at runtime (all-MiniLM-L6-v2 re-evaluated on 380 tasks: +0.026 recall@50, not adopted).
- No automatic UserPromptSubmit hook. Routing is model-initiated via MCP tools.
- No skill "fusion" (merging two SKILL.md into one). Sets are concatenations with
  precedence, nothing more.
- No skill self-generation from task history.
- No GUI, no web service. CLI + MCP only.
- Runtime network access is limited to fetching skill bodies from their pinned
  source (a hash mismatch is refused) and to the shallow clone of a GitHub URL the user
  asks `scan` / `scan_skill` to check. Search and `resolve_set` read the local index only.

## Repository layout (target)

```
skillfetch/
  CLAUDE.md                     this file
  README.md
  docs/design/
    index-format.md             ingestion pipeline, skill record schema, manifest, tiers
    constraints.md              claim schema, extraction prompt, conflict rules, resolve_set
  src/skillfetch/
    ingest/                     offline: sources, lint, scan, extract, index build;
                                also scan's checks (local_scan, skill_checks, remote,
                                repo_license)
    index/                      index loading, BM25 search, tag filters
    resolve/                    conflict/redundancy resolution
    mcp/                        MCP server exposing the tool surface below
    cli.py                      `skillfetch scan|ingest|judge|obedience|sync|serve|eval|discover`
                                (`scan` takes a folder or a GitHub URL)
    evals.py                    `skillfetch eval retrieval` over evals/retrieval/
  assets/
    router-skill/SKILL.md       the one always-on skill the user installs
    runner-agent.md             the subagent definition for isolation mode (not built, not planned for v0.3)
  evals/retrieval/              380 synthetic tasks, oracle labels, frozen queries
  evals/e2e/                    published end-to-end experiments (stages 0–13, Q)
  evals/index-scan/             the scan rules over the released index (numbers.md §25)
  evals/knowledge-gap/          what the model answers without the skill (§24)
  tests/
    fixtures/skills/            small hand-written SKILL.md corpus with known conflicts
  data/                         gitignored; local mirror lives in ~/.skillfetch/
```

Python 3.11+, `uv` for env, `ruff` for lint, `pytest`. Single package, no
monorepo. Keep dependencies minimal: `mcp`, `pyyaml`, `rank-bm25` (or a tiny
hand-rolled BM25), `anthropic` (ingest only, optional extra), `pydantic`.

## Experimental: per-task routing

Kept as an experimental feature (see Positioning for the Stage 13 result). The user installs
nothing but the MCP server and the router skill. For each task, the agent:

1. describes the task (what it is, which stack, which files) and searches a
   curated, pre-indexed corpus of SKILL.md files,
2. picks candidate skills, then asks `resolve_set` to drop the ones that
   contradict or duplicate each other (and always keep the ones the user pinned),
3. loads the resulting set into the main context and does the work (isolation
   mode, a fresh subagent per task: not built, not planned for v0.3),
4. moves on. The next task searches again. Nothing accumulates in
   `~/.claude/skills`.

### MCP tool surface

Built (v0.2): `profile_repo`, `search_skills`, `resolve_set`, `load_skills`. Built after v0.2
(#26): `resolve_and_load`, both steps in one call; the router skill does not use it yet. Also
for #26, off by default: `serve --auto-profile` (a search without `profile` uses the server's
working directory) and `serve --summary-chars N` (docs/design/router-cost.md).
Planned for v0.3, not built: `report_outcome`. `prepare_set`: not built, not planned for v0.3.
Not part of routing: `scan_skill(target)` (a local folder or GitHub URL; the same JSON as
`skillfetch scan --json`, no model) and `find_skills(want, k=10)` (index matches for a request
the user made, with an advice from the record; index-format.md §5.2). Both are served with the
router tools and, without routing, by `serve --vet`, for the vet skill
`assets/vet-skill/SKILL.md` (install it without the router: it scans before a skill is
installed and asks, and finds skills when the user asks).

| tool | input | output |
|---|---|---|
| `profile_repo(path)` | repo root | `{languages, frameworks, package_managers, tags[]}` from manifest files only (package.json, pyproject.toml, go.mod, Cargo.toml, framework config files). Never scans source. Cached per session. |
| `search_skills(queries[1–4] \| query, profile?, k=50, tiers=["A","B"], verbose=false)` | the task restated by the host model as 1–4 short sentences (the router sends four: what it builds, how to work, stack and files, the request word for word; each searched with BM25, rankings merged by RRF k=60), or one `query`; `queries` wins + optional profile | ranked candidates, compact: `{id, title, summary (first sentence, ≤160 chars), tier, token_estimate}` (50 fit in ~4k tokens); `verbose` adds the full summary, `tags` and `match_reasons[]` |
| `resolve_set(auto_ids[], pinned_ids[])` | candidate ids chosen by the host model (at most 20; `path:` ids only as pinned), plus user-pinned ids | `{set_id, included[], excluded[{id, reason, conflicts_with}], warnings[], precedence[], suppressed_by_judge, notes[], errors[]}`; `suppressed_by_judge` counts the tension / needs_review warnings dropped because the judge called the pair independent |
| `load_skills(set_id, max_tokens=8000)` | | bodies concatenated in precedence order, with no precedence header (it did not change which skill the agent follows; numbers.md §8), for injection into the current context. Each body is fetched from the skill's pinned source (unless cached), verified against the index hashes, and cached under `~/.skillfetch/cache/<content_hash>/`; a mismatch or fetch failure refuses that skill with a structured error and the others still load. Over `max_tokens` the lowest-precedence skills are dropped (listed in `errors`). |
| `resolve_and_load(auto_ids[], pinned_ids[], max_tokens=8000)` | as `resolve_set`, plus `load_skills`' budget | `resolve_set` then `load_skills` in one call, same rules (constraints.md §5): `{set_id, included[], excluded[], warnings[], notes[], content, errors[]}`; excluded skills are not loaded; `errors` lists resolve's then load's. `resolve_set` and `load_skills` stay as they are |
| `prepare_set(set_id)` (not built, not planned for v0.3) | | `{prompt_block, materialized_paths{}}` for the isolation runner; the folder is fetched and verified like `load_skills` and materialized under `~/.skillfetch/cache/<content_hash>/` |
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

### Router skill (`assets/router-skill/SKILL.md`)

The only skill a user installs. Short (≤ 60 lines). It tells the host model:

1. Before non-trivial work, restate the task in three English sentences: what it builds
   (domain nouns), the kind of work and how to do it (the approach the user asked for,
   such as TDD, minimal diff or security first; when they did not say, the one that fits
   the task best), and the stack and target files. Add the user's request word for word
   as a fourth. Pass all four to `search_skills` as `queries`.
2. Pick up to 3 candidates by reading all 50 summaries, weighing `token_estimate` against
   `load_skills`' budget. Pick a skill only when you can say in one sentence what its
   summary changes in this task; often none fits, and then resolve and load are skipped.
   If the user named a skill, find its id with
   `search_skills` (the result whose title matches) and pass it as pinned.
3. Call `resolve_set`, then `load_skills`. (`prepare_set` + delegating to the
   `skillfetch-runner` subagent when the user asks for isolation: not built, not planned for v0.3.)
4. From v0.3, after the task, call `report_outcome`.
5. Skip the search only for trivial edits: a one-line edit in a single file, a rename,
   or answering a question. Bug fixes, docs and config changes are not trivial.

### Runner agent (`assets/runner-agent.md`) — not built, not planned for v0.3

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

**v0.2 — `serve`** (+1 week; per-task routing, now experimental)
- MCP server with the four tools, router skill, `sync` command for the index.
- End-to-end demo in Claude Code: search → resolve → load → work.

**v0.3 — process-skill retrieval, shorter chain, outcome log** (experimental routing)
- Process-skill retrieval: a domain query and a how-to-work query, searched
  separately (#25).
- A shorter chain: search, resolve and load in fewer calls (#26).
- `report_outcome`.

**v0.4 — scan before you install** (shipped 2026-10-27, PRs #99–#101)
- Size warning: `SKILL.md` over 8,000 tokens, more than 20 files, more than 1 MB.
- Dated claims (info): prose lines that state a year or a version, marked "check the
  official docs".
- `scan https://github.com/<owner>/<repo>[/tree/<ref>[/<path>]]`: shallow clone, nothing
  installed or run.
- One-line advice from safety and quality checks only; the license on its own line with its
  source, by discover's rule (nearest license file up to the repository root, outside an
  aggregator).
- The scan rules over the released index (numbers.md §25), and README led by `scan`.

**v0.5 — one setup, three features** (2026-10-27, PRs #105–#108)
- `scan_skill` MCP tool and the vet skill (`assets/vet-skill`): check before install.
- `skillfetch find` / `find_skills`: find on request, with an advice from the index record.
- GitHub Action and `scan --markdown`: the check in CI, one PR comment, fail on NOT RECOMMENDED.
- `skillfetch setup [--auto] [--project | --user] [--remove]`: MCP server, vet skill and index
  in one command; auto-apply (the router) off by default.

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
- A staging index directory is written once: a rebuild always goes to a new path
  (`data/index-staging-N`), never over an existing one; Stage 9's run-b read
  `index-staging-2` after it had been rebuilt in place.
