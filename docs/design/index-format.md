# Index format and ingestion pipeline

Status: v0 draft. Owner: Kwan Hyeon. Everything here may change before v0.2;
after that, breaking changes bump `manifest.schema_version`.

## 1. Pipeline

```
sources ──► snapshot ──► lint ──► injection scan ──► extract ──► dedup ──► tier ──► index + manifest
            (git/HTTP)   (static) (static)           (Claude API) (static) (rules)
```

Stages 1–3 and 5–6 are pure Python, no network, no model. Stage 4 is the only
stage that calls the Claude API. Each stage writes its output next to the
skill so a failed run can resume.

### 1.1 Sources

A source is a YAML entry in `sources.yaml`:

```yaml
- id: anthropics-skills
  kind: git                 # git | dir | tarball
  url: https://github.com/anthropics/skills
  ref: main
  root: skills/             # subdir containing <name>/SKILL.md folders
  publisher: anthropics
  publisher_trust: verified # verified | known | unknown
```

v0.1 ships with: `anthropics/skills`, the UASL corpus, and a hand-picked list of
~20 well-known publisher repos. The list lives in `sources.yaml` at the repo
root (loaded by `ingest/sources.py`). As of 2026-10-21 it holds
`anthropics/skills`; the UASL corpus is not added because no public project by
that name could be identified.

`license` records how a source licenses its skills: an SPDX id for the whole
source, or `per-skill` when each skill folder has its own license file.
`anthropics/skills` is per-skill: Apache-2.0 for most skills, "All rights
reserved" for docx/pdf/pptx/xlsx, none for doc-coauthoring. The index
redistributes bodies and files (§2), so ingest must check each skill's license
and keep only metadata and a link for skills it may not redistribute; that rule
is to be implemented with the ingest stage. skills.sh scraping is v0.2 (needs rate limiting
and a stable listing API; do not hand-roll a crawler in v0.1).

### 1.2 Snapshot

Clone/download into `work/<source_id>/<commit>/`. Record the commit SHA. A skill's
identity is `source_id/<name>@<content_sha256[:12]>` — the hash is over the
normalized SKILL.md body + the sorted list of (relative path, sha256) of every
file in the skill folder. Same content under two sources → two records, same
`content_hash`, deduped at stage 5.

Normalization for the hash (`ingest/skillfile.py`): UTF-8, BOM stripped, line
endings `\n`, trailing whitespace stripped per line, leading/trailing blank
lines dropped. "Every file" excludes hidden files and folders, `node_modules/`,
`__pycache__/`, and a top-level `constraints.json` sidecar (§5).

### 1.3 Lint (static)

Reuse the agentskills.io spec rules; do not reimplement a full linter. Minimal
checks we own:

- `SKILL.md` exists, frontmatter parses, has `name` and `description`.
- Body ≤ 500 lines / ~5000 tokens (warn, not fail; tokens estimated as chars/4).
- No broken relative links to files inside the folder. Inline links, images and
  reference definitions are checked; links inside fenced or inline code, URLs
  with a scheme, and `#anchors` are not. A link that leaves the folder (`../`,
  or an absolute path) is an error too: the folder is materialized on its own.

Rule ids: `lint.missing-skill-md`, `lint.frontmatter-{missing,unclosed,invalid}`,
`lint.missing-{name,description}`, `lint.broken-link`, `lint.link-outside-skill`
(errors); `lint.body-too-long`, `lint.body-too-many-tokens` (warnings).

Fail → skill is recorded with `status: lint_failed` and excluded from the index.
Lint findings are stored so the data write-up can count them.

### 1.4 Injection scan (static)

Pattern families, each a list of regexes in `scan_rules.yaml`. A hit records
`{rule_id, line_no, line}`.

| family | examples | effect |
|---|---|---|
| `override` | "ignore previous/all instructions", "disregard the system prompt", "you are now" | hard fail |
| `exfil` | reads of `~/.ssh`, `~/.aws`, `.env`, tokens/keys, "send to <url>"; remote script execution from an untrusted URL (`http://`, raw IP, URL shortener) | hard fail |
| `exfil` (warn rules) | remote script execution from an `https://` URL: `curl … \| sh`, `sh -c "$(curl …)"`, `sh <(curl …)` | warn |
| `privilege` | remote script execution combined with sudo, "run as root", "disable sandbox", "--dangerously" | hard fail |
| `privilege` (warn rules) | `sudo <command>` on its own (`sudo apt-get install …`) | warn |
| `network` | any absolute `http(s)://` in an instruction (not in a docs link) | warn |
| `scripts` | folder contains executable files or `scripts/` | tag `has_scripts`; tier cap B→C unless publisher verified |
| `hidden` | zero-width chars, HTML comments with instructions, base64 blobs > 200 chars | hard fail |

Hard fail → `status: scan_failed`, excluded. This is a blocklist, not a proof of
safety; say so in README.

Why `curl … | sh` and bare `sudo` only warn (rules v2): they are the standard
install form of uv, rustup, Homebrew and nvm and of most setup steps. Failing
them would drop a large share of legitimate setup skills, and anyone opening
the "rejected because" list in the data write-up would stop trusting it. They
fail only in the combinations above.

Implementation notes (`ingest/injection.py`, rules in `ingest/scan_rules.yaml`):

- Scanned: `SKILL.md` plus every `.md/.markdown/.mdx/.txt` file in the folder.
  Script files are tagged, not regex-scanned (they are code, and the `scripts`
  tier cap already applies). A leading BOM is not an invisible character.
- `scripts` = any file under `scripts/`, any file with a script extension
  (`.sh .py .js .ts …`), or any executable file. The list is recorded as
  evidence for the tag.
- `network` ignores markdown link targets, `<autolinks>` and reference
  definitions; a URL anywhere else (prose, inline code, code blocks) warns.
- A rule may set `effect` to override its family's effect; that is how the warn
  rules above live in the `exfil` and `privilege` families. Hits record their
  effective `effect`.
- HTML comments fail only for directive wording aimed at the agent (`ignore`,
  `disregard`, `you must/should/are/will`, `assistant`, `claude`, `system
  prompt`, `execute`, `upload`, `run the following`). Maintainer notes such as
  "always keep this table sorted" or "do not remove" pass (rules v2).
- Rules may set `allow_negated`: a match is skipped when a negation (`not`,
  `never`, `n't`, `no`, `without`) appears at most two words before it. "Never
  run sudo …" is advice; "Do not hesitate to run sudo …" still fails. Used only
  where benign negated phrasing is common (sudo, root, sandbox,
  `--dangerously-*`, reading key/credential paths, system prompt).
- Evidence lines show invisible characters as `<U+200B>` and are cut at 160
  characters.

### 1.5 Extract (Claude API)

One call per skill, structured output (temperature 0 where the model accepts
it; see constraints.md §2). Produces:

```json
{
  "summary": "one or two sentences, what the skill makes the agent do differently",
  "keywords": ["5-15 lowercase terms, domain + action words"],
  "tags": {
    "languages": ["python"],
    "frameworks": ["django"],
    "phase": ["implement", "review"],
    "domain": ["backend", "testing"]
  },
  "synthetic_queries": ["8-12 user-style task sentences this skill should match, varied register, some vague"],
  "constraints": [ ... see constraints.md ... ],
  "consumes": ["artifacts this skill expects, e.g. 'failing test', 'design mockup'"],
  "produces": ["artifacts it yields, e.g. 'PR description', 'migration file'"],
  "requires_tools": ["Bash", "WebFetch"]
}
```

The prompt lives in `src/skillfetch/ingest/prompts/extract.md`. Changing it
bumps `extract_version`; records with an older version are re-extracted on the
next run. Extraction failures (schema invalid after one retry) → `status:
extract_failed`, excluded from `B`, can still be `C`.

Cost guard: skip bodies > 12k tokens (record `status: too_large`). Each
record keeps the token usage of every attempt, so cost per skill is known
(prices in `ingest/extract.py`, list prices; cache writes 1.25x, reads 0.1x).

**Extract cache and CLI** (`ingest/extract_cache.py`, `ingest/ingest.py`):

- Every record is cached at
  `~/.skillfetch/extract-cache/v<extract_version>/<provider>/<model>/<content_hash>.json`
  (`--cache-dir` to move it). The key adds `provider/model` to `content_hash`
  + `extract_version`, so `--model` never reuses another model's output;
  OpenRouter is `openrouter/<vendor>/<model>`; other OpenAI-compatible
  servers get the provider `openai-compat+<host>`. Cost per record is the
  provider-reported charge when there is one (OpenRouter), else list prices.
- Credentials: Anthropic via the SDK's usual sources; OpenAI via
  `OPENAI_API_KEY`, else `OPEN_API_KEY` / `OPENAI_API_KEY` read from
  `~/.rnd_creds.env` (`--creds-file`). Only that one variable is read from the
  file, it is passed to the client directly (never exported to the
  environment), and error output is redacted. A
  skill is never extracted twice for the same key.
- Model-output failures (`extract_failed`, `too_large`) are cached like
  successes. API errors are not: finished skills stay cached and a rerun
  resumes.
- Skills failing lint or the injection scan are never sent to the API.
- `skillfetch ingest <dir>` uses the cache only; `--with-api` calls the API for
  cache misses (`--jobs` parallel requests). Credentials are checked before
  the first request. Output is a cost log: per skill, status, tokens (input,
  cache reads/writes, output), dollars, dropped/repaired evidence; then the
  totals for this run.
- `--calibrate` takes a fixtures dir (`skills/` + `expected.yaml`) and prints
  the calibration of constraints.md §2; it refuses to run (exit 2) while
  fixture skills are missing from the cache, and exits 1 below the gate.
- Index building (§1.6–§2) is not implemented yet; extraction results live in
  the cache.

### 1.6 Dedup (static)

Two skills are a **duplicate group** when any of:

- identical `content_hash`;
- Jaccard(keywords) ≥ 0.8 **and** constraint-multiset equality after
  normalization, i.e. each is redundant with the other (constraints.md §4; a
  one-way subset is not a duplicate group, it is handled by `resolve_set`);
- same normalized `name` from the same publisher at different refs → keep newest.

Each group gets a `canonical_id` (prefer verified publisher, then newest). The
index keeps all members but `search_skills` returns only canonicals unless
`include_duplicates=true`.

### 1.7 Tier (rules)

| tier | rule | default in search |
|---|---|---|
| A | `publisher_trust: verified` and passed lint + scan + extract | on |
| B | passed lint + scan + extract, no `has_scripts`, not a duplicate of an A skill | on |
| C | anything else that is not `*_failed` (has scripts, extract failed, unknown publisher with warnings) | off |

Tier is recomputed on every ingest; it is not stored in the source.

## 2. Index layout

```
index/
  manifest.json
  skills.jsonl            one record per skill (see §3)
  bm25/                   serialized BM25 state (tokens, idf, doc lengths)
  bodies/<id>.md          normalized SKILL.md body
  assets/<id>/            other files in the skill folder (only for has_scripts or references)
  constraints.jsonl       one line per constraint, keyed by skill id (denormalized for resolve/)
  dupgroups.json          {canonical_id: [member_ids]}
```

`manifest.json`:

```json
{
  "schema_version": 1,
  "built_at": "2026-10-20T08:00:00Z",
  "extract_version": 1,
  "scan_rules_version": 1,
  "sources": [{"id": "...", "commit": "...", "skills": 123}],
  "counts": {"A": 40, "B": 310, "C": 120, "lint_failed": 15, "scan_failed": 4, "extract_failed": 7},
  "files": {"skills.jsonl": "<sha256>", "constraints.jsonl": "<sha256>", "...": "..."},
  "signature": null
}
```

`signature` is reserved; v0.1 verifies file hashes only. Releases are a tarball
of `index/` attached to a GitHub release; `skillfetch sync` downloads the
latest, verifies hashes, swaps `~/.skillfetch/index/` atomically.

## 3. Skill record (`skills.jsonl`)

```json
{
  "id": "anthropics-skills/pdf@3f9c2a1b7e0d",
  "canonical_id": "anthropics-skills/pdf@3f9c2a1b7e0d",
  "name": "pdf",
  "title": "PDF processing",
  "description": "<frontmatter description verbatim>",
  "summary": "<extracted>",
  "source_id": "anthropics-skills",
  "publisher": "anthropics",
  "publisher_trust": "verified",
  "commit": "a1b2c3d",
  "content_hash": "3f9c2a1b7e0d…",
  "tier": "A",
  "status": "ok",
  "tags": {"languages": [], "frameworks": [], "phase": ["implement"], "domain": ["documents"]},
  "keywords": ["pdf", "extract", "form", "merge"],
  "synthetic_queries": ["pull the tables out of this pdf", "…"],
  "consumes": ["pdf file"],
  "produces": ["extracted text", "filled form"],
  "requires_tools": ["Bash"],
  "has_scripts": true,
  "token_estimate": 2100,
  "lint": {"warnings": []},
  "scan": {"hits": [], "warnings": []},
  "extract_version": 1,
  "constraint_count": 7
}
```

## 4. Search (runtime, `src/skillfetch/index/`)

- Document text for BM25 = `title + description + keywords×2 + synthetic_queries + summary + body`.
  Keywords are repeated once to weight them; do not over-tune.
- Query = the host model's one-sentence task restatement, lowercased, tokenized
  on non-alphanumerics, stopwords removed, no stemming in v0.1 (measure first).
- Profile boost: for each tag in `profile.tags` that appears in the skill's
  `tags.*`, multiply score by 1.3. Skills whose `tags.languages` is non-empty
  and disjoint from `profile.languages` are multiplied by 0.5 (soft filter, never
  dropped — a Rust skill may still be what the user wants).
- Return top-k canonicals with `match_reasons`: which query tokens hit which
  field, and which profile tags boosted. This is what makes the result
  explainable; keep it.

## 5. Local scan mode

`skillfetch scan <dir>` runs stages 1.3–1.6 on a local directory and then
`resolve_set` over **all** pairs in it (N is small locally). Output is a
human-readable report plus `--json`. Constraint extraction needs the API; without
a key, scan still runs lint + scan + dedup-by-hash and prints
"constraint analysis skipped (no ANTHROPIC_API_KEY)".

As built (`ingest/local_scan.py`, `cli.py`):

- Skills are folders containing `SKILL.md`, found recursively (hidden folders
  and `node_modules/` skipped; folders inside a skill belong to it). The id is
  the folder path relative to `<dir>`.
- Constraints come from a `constraints.json` sidecar next to `SKILL.md` (the
  schema of constraints.md §1; this is also the fixture format). Every
  evidence quote must appear on its line of `SKILL.md`, or the sidecar is
  reported as `INVALID_CONSTRAINTS` and the skill is skipped. Sidecars are a
  local-scan input only; corpus ingest never trusts them. Until `--with-api`
  extraction exists, skills without a sidecar are listed as skipped.
- Skills that fail lint are not analyzed. Skills that fail the injection scan
  are still analyzed, so the user sees their conflicts too.
- Identical `content_hash` → `DUPLICATE`; those pairs are not re-reported as
  constraint findings. Every other pair of analyzed skills gets at most one
  finding: conflict, else redundant (directional; `a` is the superset), else
  tension, else needs_review.
- Exit code 0 when the scan ran, 2 on usage errors. `--fail-on
  {conflict,scan,lint}` (repeatable or comma-separated) exits 1 when the scan
  finds any conflict finding, injection-scan failure or lint failure; the
  reason goes to stderr so `--json` output stays parseable. Warnings,
  `tension`, `needs_review` and `redundant` never fail the run. Stage counts
  are per stage: a skill failing both lint and the scan counts for both.
