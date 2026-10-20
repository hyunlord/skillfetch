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
~20 well-known publisher repos. skills.sh scraping is v0.2 (needs rate limiting
and a stable listing API; do not hand-roll a crawler in v0.1).

### 1.2 Snapshot

Clone/download into `work/<source_id>/<commit>/`. Record the commit SHA. A skill's
identity is `source_id/<name>@<content_sha256[:12]>` — the hash is over the
normalized SKILL.md body + the sorted list of (relative path, sha256) of every
file in the skill folder. Same content under two sources → two records, same
`content_hash`, deduped at stage 5.

### 1.3 Lint (static)

Reuse the agentskills.io spec rules; do not reimplement a full linter. Minimal
checks we own:

- `SKILL.md` exists, frontmatter parses, has `name` and `description`.
- Body ≤ 500 lines / ~5000 tokens (warn, not fail).
- No broken relative links to files inside the folder.

Fail → skill is recorded with `status: lint_failed` and excluded from the index.
Lint findings are stored so the data write-up can count them.

### 1.4 Injection scan (static)

Pattern families, each a list of regexes in `scan_rules.yaml`. A hit records
`{rule_id, line_no, line}`.

| family | examples | effect |
|---|---|---|
| `override` | "ignore previous/all instructions", "disregard the system prompt", "you are now" | hard fail |
| `exfil` | reads of `~/.ssh`, `~/.aws`, `.env`, tokens/keys, "send to <url>", `curl ... \| sh` | hard fail |
| `privilege` | "run with sudo", "disable sandbox", "--dangerously" | hard fail |
| `network` | any absolute `http(s)://` in an instruction (not in a docs link) | warn |
| `scripts` | folder contains executable files or `scripts/` | tag `has_scripts`; tier cap B→C unless publisher verified |
| `hidden` | zero-width chars, HTML comments with instructions, base64 blobs > 200 chars | hard fail |

Hard fail → `status: scan_failed`, excluded. This is a blocklist, not a proof of
safety; say so in README.

### 1.5 Extract (Claude API)

One call per skill, structured output, temperature 0. Produces:

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

Cost guard: skip bodies > 12k tokens (record `status: too_large`).

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
