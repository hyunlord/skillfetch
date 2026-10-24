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

Discovery walks the root recursively: any folder with a SKILL.md is a skill, and
folders inside a skill belong to it. Hidden folders (`.claude/`, `.agents/`, …),
`node_modules` and `__pycache__` are never entered. Two optional fields cover
repositories that keep skills in more than one place or ship skeletons:

```yaml
  roots: [skills/, plugins/git/skills/]   # instead of root
  exclude: [template, tests/fixtures]     # fnmatch on a folder name, or on the
                                          # snapshot-relative path when it has a "/"
```

Both default to empty, so a source without them is discovered exactly as before.

The source list lives in `sources.yaml` at the repo root (loaded by
`ingest/sources.py`). It has two sources: `anthropics/skills` (verified) and the
UASL corpus, `onfire7777/universal-ai-skills-library` (1812 skills, unknown
trust). UASL is an aggregation: 954 skills carry an `.openskills.json` naming
their upstream repo and path, recorded per skill as `upstream`. Its
`docs/THIRD_PARTY_SOURCE_REPOS.md` lists only external router sources (GStack,
GBrain) that are not copied into `skills/`; it is parsed into the source's
`third_party_upstreams`, not into skill records.

`license` records how a source licenses its skills: an SPDX id for the whole
source, or `per-skill` (the default) when each skill is licensed by its own
license file or frontmatter, and is `unknown` without either. Both sources are
per-skill; UASL's repository MIT license is not inherited because the
repository aggregates third-party skills. See §1.8 for what follows. skills.sh scraping is v0.2 (needs rate limiting
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
`__pycache__/`, symbolic links, and a top-level `constraints.json` sidecar (§5).

Git sources (`ingest/snapshot.py`) must have an `https://` URL (other git
transports run code paths of their own, `ext::` among them), every git call
puts `--` before the URL, and a ref may not start with `-`. Source ids name
directories, so they are `[A-Za-z0-9][A-Za-z0-9._-]*` without `..`. A skill
folder that cannot be read (a broken link, a non-object `.openskills.json`)
becomes a `lint_failed` record (`lint.unreadable`) and the build goes on.
Extraction errors stored in `skills.jsonl` are redacted (known keys and
anything key-shaped); a provider's AuthenticationError / PermissionDenied
stops the build instead of failing every skill.

### 1.3 Lint (static)

Reuse the agentskills.io spec rules; do not reimplement a full linter. Minimal
checks we own:

- `SKILL.md` exists, frontmatter parses, has `name` and `description`.
- Body ≤ 500 lines / ~5000 tokens (warn, not fail; tokens estimated as chars/4).
- No broken relative links to files inside the folder. Inline links, images and
  reference definitions are checked; links inside fenced or inline code, URLs
  with a scheme, and `#anchors` are not. A link that leaves the folder (`../`,
  or an absolute path) is an error too: the folder is materialized on its own.
  A placeholder target is a warning (`lint.placeholder-link`), not checked:
  template syntax (`{baseDir}/…`, `${VAR}`) or a stand-in word (`URL`, `link`,
  `path`, `href`, `TODO`, `...`; not file names such as `README`). A template line such as
  `[Title](URL) — one-sentence description` is not a broken link (it rejected
  anthropics' academy-guide in the first public build).

Rule ids: `lint.missing-skill-md`, `lint.frontmatter-{missing,unclosed,invalid}`,
`lint.missing-{name,description}`, `lint.broken-link`, `lint.link-outside-skill`
(errors); `lint.body-too-long`, `lint.body-too-many-tokens`,
`lint.placeholder-link` (warnings).

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

- Scanned: `SKILL.md` plus every other `.md` file in the folder, license texts
  excepted (`LICENSE`, `LICENCE`, `COPYING`, `NOTICE`, `OFL` stems: fonts ship
  the OFL). Rules v5 dropped `.markdown/.mdx/.txt`: `.txt` was mostly license
  texts. Script files are tagged, not regex-scanned (they are code, and the
  `scripts` tier cap already applies). A leading BOM is not an invisible
  character.
- Symbolic links are never followed, read, hashed or scanned, and a folder
  whose `SKILL.md` is a link is not a skill (`skillfile.py`): a snapshot of an
  untrusted repo must not make the build read a file outside it.
- Lines over 2000 characters are not matched; each is reported as a
  `scan.line-too-long` warning with its first characters as evidence (rules
  v5). A rule may set `within`, a second regex that must match inside the
  first match; `exfil.remote-script-untrusted-url` uses it (pipe-to-shell,
  then the untrusted URL inside it) instead of one regex that took 42 s on a
  20k-character line.
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
- `override.system-prompt` needs one of `ignore`, `disregard`, `bypass`,
  `reveal`, `print`, `repeat`, `leak` within 20 characters before "system
  prompt". `output` and `override` were dropped in rules v4: "… without test or
  build output, add to the system prompt" (anthropics claude-api) and "Direct:
  override system prompts" (an OWASP table describing attacks) are
  documentation.
- `override` rules set `allow_quoted` (rules v3): a match that lies inside
  quotation marks (`"…"`, `“…”`) is downgraded to a warning, marked
  `quoted: true`. Prompt-writing advice quotes the phrase it warns against
  ("avoid override-style language (\"disregard the previous instruction\")"),
  which rejected anthropics' claude-api in the first public build. It is a
  warning, not a skip: a quoted injection is still text the agent reads, so
  it stays visible and keeps an unknown publisher's skill in tier C. A line
  with any unquoted match still fails, and quotes never soften the other
  families.
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
- The cache holds the raw exchange only: `extract_version`, `model`,
  `content_hash`, `skill_id`, `status`, `error` and the `attempts` with the
  model's answers verbatim. Post-processing (validation, evidence check,
  polarity, implied artifacts, object vocabulary, condition clauses,
  sections, per-line merge) runs at every read against the skill's SKILL.md,
  so a rule change reaches every cached answer at the next build with no API
  call. `POSTPROCESS_FINGERPRINT` (sha256 over the source of those rules) is
  pinned by a test and recorded in the manifest as `postprocess`. A cache
  file whose own `extract_version`, `model` or `content_hash` disagrees with
  its path is a miss.
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

### 1.6 Dedup (static)

Two skills are a **duplicate group** when any of:

- identical `content_hash`;
- Jaccard(keywords) ≥ 0.8 **and** constraint-multiset equality after
  normalization, i.e. each is redundant with the other (constraints.md §4; a
  one-way subset is not a duplicate group, it is handled by `resolve_set`);
- same normalized `name` from the same publisher at different refs → keep newest
  (`build.dedup`: lowercased, runs of space, `_` and `-` as one `-`; at a
  different commit, so two folders of one snapshot are never merged by name).

Each group gets a `canonical_id` (prefer verified publisher, then newest). The
index keeps all members; `search_skills` returns only canonicals.

### 1.7 Tier (rules)

| tier | rule | default in search |
|---|---|---|
| A | `publisher_trust: verified` and passed lint + scan + extract (or too large to extract, below) | on |
| B | passed lint + scan + extract, no `has_scripts`, not a duplicate of an A skill | on |
| C | anything else that is not `*_failed` (has scripts, extract failed, unknown publisher with warnings) | off |

Tier is recomputed on every ingest; it is not stored in the source.

A skill over the extraction cost guard (§1.5, ~12k tokens) is not sent to the
model: it gets `status: not_extracted`, `not_extracted_reason: too_large`, no
constraints, and keeps the tier the other rules give it (anthropics'
claude-api is A). It can be searched and loaded but never takes part in a
conflict or duplicate check. `extract_failed` and `not_extracted` with reason
`no cache entry` (a build without `--with-api`) stay tier C.
A request that fails (connection, provider or SDK error, after the SDK's own
retries) does not stop the build: that skill gets `not_extracted_reason:
api_error`, is tier C for this build, is not cached, and is retried by the next
run; `ingest` exits 1 when any skill failed this way. (The first full UASL
build was stopped by a single `Connection error.` after ~270 extractions.)

`network.bare-url` warnings do not count as "warnings" for the tier: skills for
web APIs are full of documentation URLs, and in the first public build that one
rule alone put 129 of 185 UASL skills in tier C. The warning is still recorded
in the skill's `scan` field and in the build report.

### 1.8 License and redistribution

Each skill record carries `license` (an SPDX id, `proprietary`, or `unknown`)
and `redistributable` (bool). The license comes from, in order: a license file
in the skill folder (`LICENSE`, `LICENSE.txt`, `LICENSE.md`, `COPYING`),
classified by its text; the frontmatter `license:` field; the source's SPDX
license if it has one; else `unknown`.

**Upstream licenses and `license_source`.** An aggregated skill is licensed by
its upstream author, not by the aggregator. With `ingest --upstream-licenses`
the build reads each upstream repo named in `.openskills.json` once (GitHub git
trees API through `gh`, cached in `~/.skillfetch/upstream-licenses/`) and looks
for a license file on the skill's upstream path, from its folder up to the repo
root; the nearest one applies when the skill folder has none
(`license_origin: upstream:<repo>/<file>`). Every record carries
`license_source`, which keeps "no license stated" apart from "not
redistributable":

- `explicit`: a license is stated, in the skill folder or upstream;
- `upstream_no_license`: the upstream repo was read and states no license —
  all rights reserved by default, so not redistributable, but known;
- `upstream_unknown`: no upstream is recorded, or it could not be read.

The build report tabulates `license_source` × license class (permissive,
copyleft, proprietary, unrecognized, none).

`redistributable` is true only for permissive licenses: MIT, Apache-2.0,
BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, CC-BY-4.0, CC0-1.0, Unlicense.
Copyleft (GPL, AGPL), `proprietary` and `unknown` are not redistributable in
v0.1 — conservative on purpose, like the rest of the pipeline.

`redistributable` describes whether skillfetch *could* mirror the files; since
v0.2 the index mirrors none. Every skill — whatever its license — is indexed
with metadata, extracted constraints (with their short evidence quotes), tier
and a per-file manifest of sha256 hashes, and never with its body or files.

**Runtime fetch (v0.2, the default path).** `load_skills` fetches every file in a skill's manifest from its pinned source
— for a GitHub source
`https://raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>/<file>`,
for a `dir` source a `file://` path — verifies each file's sha256 against the
manifest, and caches the folder under `~/.skillfetch/cache/<content_hash>/`.
A cached folder is re-verified before use. Any mismatch, missing file or fetch
error refuses that skill with a structured error and no body; the other skills
of the set still load. The record itself is input and is checked before use:
`content_hash` must be a sha256 hex digest (it names the cache folder that is
replaced), `fetch_base` must start with `https://raw.githubusercontent.com/`
(`file://` only for skills of a source whose `manifest.sources[].kind` is
`dir`), redirects must stay on the same host, and each file is capped at 8 MB. This is the only network access at runtime (CLAUDE.md
non-goals): no other URL is ever requested, and nothing is executed.

## 2. Index layout

```
index/
  manifest.json
  skills.jsonl            one record per skill (see §3), with its file manifest
  constraints.jsonl       one line per constraint, keyed by skill id (denormalized for resolve/)
  dupgroups.json          {canonical_id: [member_ids]}
  rejected.jsonl          records that failed lint or the injection scan
  pairs.jsonl             optional: judge verdicts for pairs the rules left open (constraints.md §8)
```

No `bodies/`, `assets/` or `bm25/`: bodies are fetched at runtime (§1.8), and
BM25 is built in memory when the server loads the index (a few thousand short
documents; well under a second).

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

As built (`ingest/build.py`, `skillfetch ingest --sources sources.yaml
[--only ID] [--sample ID=N] [--seed N] --out DIR`):

- Ids are `<source_id>/<name>@<content_hash[:12]>`.
- Each record carries `files` — `{relpath: sha256}` for every file of the
  skill folder, `SKILL.md` included, hashed as raw bytes on disk — and
  `fetch_base`, the URL the files are fetched from (`<fetch_base>/<relpath>`):
  `https://raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>` for
  GitHub sources; for `dir` sources and other git hosts, `file://` to the
  skill folder in the local snapshot (loadable only on the machine that built
  the index).
- `rejected.jsonl` holds the records that failed lint or the injection scan
  (not in the index, kept for the data write-up).
- Extraction runs once per distinct `content_hash`.
- Manifest additions: `extract_model`, per source `url`, `ref`,
  `commit_date`, `discovered`, `sampled`, `sample_seed`,
  `third_party_upstreams`; `licenses` (count per license) and
  `redistributable`. `counts` also has `too_large` and `not_extracted`.
- Sampling: the source's skill folders sorted by path, then
  `random.Random(seed).sample`; the sample is recorded, so a build is
  reproducible from the manifest.
- The build is written next to `--out` and swapped in when complete.

`signature` is reserved; v0.1 verifies file hashes only. Releases are a tarball
of `index/` attached to a GitHub release; `skillfetch sync` downloads the
latest, verifies hashes, swaps `~/.skillfetch/index/` atomically.

As built (`index/sync.py`):

- `skillfetch sync --pack DIR --out dist/` writes
  `skillfetch-index-<built_at>.tar.gz` and `<name>.sha256`: manifest.json and
  the files it lists, under `index/`, reproducible (sorted members, zero mtimes
  and owners). Maintainers attach both to a release (`gh release create
  index-<date> dist/*`).
- `skillfetch sync [--repo hyunlord/skillfetch] [--tag T] [--index DIR]` takes
  release `T`, or the newest non-draft, non-pre-release with both assets;
  `--from FILE` installs a local tarball (checked against `FILE.sha256` when
  present). The tarball must match its `.sha256`; only regular files under
  `index/` are unpacked (no links, absolute paths or `..`); the unpacked index
  must pass `Index.load` (every file against the manifest) before it replaces
  the old one, which stays in place on any failure. Same manifest → "already
  up to date". `GITHUB_TOKEN`/`GH_TOKEN`, if set, is sent to api.github.com
  only (rate limit), never to the download host, never printed.
- Every read is capped (read(limit + 1)): the tarball and the sum of its
  unpacked members at 64 MB, release listings and `.sha256` files at 8 MB.
  Members are checked from their headers as the stream is read, before their
  data. Downloads and redirects go to GitHub hosts over https only.

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
  "files": {"SKILL.md": "<sha256>", "scripts/fill.py": "<sha256>"},
  "fetch_base": "https://raw.githubusercontent.com/anthropics/skills/a1b2c3d/skills/pdf",
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

- Document text for BM25 = `title + description + keywords×2 + synthetic_queries + summary`
  (no body: bodies are not in the index, §1.8).
  Keywords are repeated once to weight them; do not over-tune.
- Queries = the host model's restatement of the task as 1–4 short sentences (the router
  sends four: what it builds, how to work, the stack and files, the request word for
  word; `query` = one sentence).
  Each is ranked on its own (top k each) and the rankings are merged by reciprocal
  rank fusion, score Σ 1/(60 + rank), ties by id (`search.rrf`, `Searcher.search_many`).
  One query is plain BM25. On the 380-task benchmark (`skillfetch eval retrieval`,
  numbers.md §13) three sentences raise recall@50 from 0.775 to 0.835.
- Each query is lowercased, tokenized
  into Unicode words (`_` separates), each run of Han, Kana or Hangul as
  overlapping 2-grams ("리팩토링" → 리팩, 팩토, 토링), stopwords removed, no
  stemming in v0.1 (measure first). Documents are tokenized the same way.
- Profile boost: for each tag in `profile.tags` that appears in the skill's
  `tags.*`, multiply score by 1.3. Skills whose `tags.languages` is non-empty
  and disjoint from `profile.languages` are multiplied by 0.5 (soft filter, never
  dropped — a Rust skill may still be what the user wants).
- Return the top k (default 50) canonicals. By default each result is compact —
  id, title, the summary's first sentence (≤160 chars), tier, token_estimate — so
  50 fit in about 4k tokens and the host model reads them all and picks 1–3 (the
  expert's pick was in the BM25 top 3 for 7 of 34 real queries, top 50 for 24).
  `verbose=true` adds the full summary, tags and `match_reasons`: which query
  tokens hit which field, and which profile tags boosted. This is what makes the
  result explainable; keep it.

## 5. Local scan mode

`skillfetch scan <dir>` runs stages 1.3–1.6 on a local directory and then
`resolve_set` over **all** pairs in it (N is small locally). Output is a
human-readable report plus `--json`. Constraints come from the index first (an
installed copy of a public skill has the same content hash as its index record),
so no model is needed for skills the index covers; only the rest need extraction.

As built (`ingest/local_scan.py`, `cli.py`):

- Skills are folders containing `SKILL.md`, found recursively (hidden folders
  and `node_modules/` skipped; folders inside a skill belong to it). The id is
  the folder path relative to `<dir>`.
- Constraints come from, in order:
  1. a `constraints.json` sidecar next to `SKILL.md` (the schema of
     constraints.md §1; this is also the fixture format). Sidecars are a
     local-scan input only; corpus ingest never trusts them;
  2. the index (`--index`, default `~/.skillfetch/index` from `skillfetch
     sync`; skipped if absent, refused if it fails its manifest check): the
     record with the same `content_hash`. Constraints keep the corpus's
     fan-out flags (§3 row 14a), which a few local skills could not show;
  3. the extract cache under `--model` (default: the index's
     `extract_model`);
  4. with `--with-api`, a fresh extraction with `--model` (cached; skills
     that fail lint or the injection scan are never sent).
  Whatever the source, every evidence quote must appear on its line of the
  local `SKILL.md`, or the skill is reported as `INVALID_CONSTRAINTS` and
  skipped. Skipped skills are listed with the reason when one is known (in
  the index but not extracted, cached extraction failed, fails the injection
  scan, queued for Claude Code).
- A tension / needs_review finding between two skills whose constraints came
  from the index is not shown when the index's judge verdict for that pair is
  `independent` (constraints.md §8, as in `resolve_set`); the report counts
  them (`suppressed_by_judge`). Conflicts are never hidden.
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
