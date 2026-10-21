# Constraints: extraction schema and conflict resolution

Status: v0 draft. This is the core of the project. `resolve_set` must follow
this document exactly; if the implementation needs to deviate, change the
document in the same commit.

## 0. Why not keywords

Keyword overlap tells you two skills talk about the same thing. It cannot tell
you whether they agree. "Use emoji in headers" and "never use emoji" share every
keyword. Conflict detection needs **polarity** and **scope**, so we extract
typed constraints, not keywords. Keywords are still extracted — for search and
for cheap candidate blocking — but never for judgement.

## 1. Constraint (claim) schema

One SKILL.md yields 0–30 constraints. Each:

```json
{
  "id": "anthropics-skills/pdf@3f9c…#c3",
  "subject": "emoji",
  "directive": "forbid",
  "object": "in headers",
  "scope": {
    "artifact": "markdown",
    "phase": "format",
    "condition": null
  },
  "strength": "must",
  "evidence": {"line_no": 42, "text": "Never put emoji in section headers."}
}
```

Fields:

- `subject` — a short noun phrase, lowercase, from a **controlled vocabulary when
  possible** (see §1.1), free text otherwise. The extractor must prefer vocabulary
  terms and must not invent synonyms for an existing term.
- `directive` — one of `require | forbid | prefer | avoid | order`.
  - `require`/`forbid`: hard (the skill says must / never).
  - `prefer`/`avoid`: soft (should / try to / by default).
  - `order`: a sequencing claim ("write tests before code"); `object` holds the
    thing it must precede/follow, `direction` holds `before|after`.
- `object` — what the directive is about, when `subject` alone is ambiguous.
  Optional.
- `direction` — `before | after`, `order` only (null otherwise): the subject
  comes before / after the object.
- `scope.artifact` — what the rule applies to: `code | tests | commit-message |
  pr-description | markdown | response | plan | any`. `any` when the skill does
  not narrow it.
- `scope.phase` — `plan | implement | test | review | format | any`.
- `scope.condition` — condition if the rule is conditional, else null. When
  possible a single language, framework or artifact name (`python`, `django`,
  `migrations`), lowercase; otherwise a short phrase. Applies to every
  directive, including `order` ("tests first *for bug fixes*").
- `strength` — `must | should`. Derived from directive (require/forbid → must,
  prefer/avoid → should) unless the text clearly says otherwise. `order` has no
  polarity; its strength defaults to `must` unless stated.
- `evidence` — the exact source line. **Required.** A constraint without a
  quotable line is dropped by the extractor. `line_no` is 1-based in the
  original `SKILL.md`, counting the frontmatter, so users can jump to it.

For `order`, `object` and `direction` are required; "A before B" and "B after
A" are the same constraint. (Until v0.1 the direction lived in
`scope.condition`, which left `order` without a real condition — issue #1.)

### 1.1 Controlled subject vocabulary (v0)

Start small; grow from extraction output, not from imagination.

```
formatting: emoji, headers, bullet-points, code-blocks, line-length, trailing-whitespace
language:   type-hints, docstrings, comments, naming-convention, error-handling, logging
process:    tests-first, commit-granularity, branch-naming, pr-size, review-before-merge
output:     response-length, preamble, summary-at-end, ask-before-acting, explain-reasoning
tooling:    package-manager*, linter, formatter*, test-runner*, build-tool*
```

The extractor is told: "If the constraint is about one of these, use that exact
term as `subject`." The machine-readable list is
`src/skillfetch/resolve/vocabulary.py`.

**Exclusive terms** (marked `*`, `exclusive: true`): the subject is a single
slot, so two different choices for it cannot both be followed — "always use
npm" and "always use pnpm" conflict even though neither skill forbids the
other. Choices only exclude each other within one ecosystem; across ecosystems
they coexist (a repo can use pnpm for the front end and uv for the back end). conda is
its own ecosystem: it manages environments across languages, and `pip install`
inside a conda environment is routine, so "use conda" never excludes pip or uv.
Each exclusive term therefore lists its known alternatives per ecosystem:

| term | ecosystem: alternatives |
|---|---|
| package-manager | javascript: npm, pnpm, yarn, bun · python: pip, uv, poetry, pipenv, pdm · conda: conda, mamba, micromamba |
| formatter | javascript: prettier, biome, dprint · python: black, ruff, yapf, autopep8 |
| test-runner | javascript: jest, vitest, mocha, ava · python: pytest, unittest, nose2 |
| build-tool | javascript: vite, webpack, esbuild, rollup, parcel, rspack · jvm: maven, gradle, sbt |

An object names a choice when exactly one alternative appears among its
normalized words ("pnpm workspaces" → pnpm; "npm or yarn" → no single choice).
`linter` is deliberately not exclusive (several linters routinely run together),
nor is `naming-convention` (conventions differ per language and the constraint
schema has no language field). Grow these lists from extraction output.

**Polarity and implied artifacts** (applied by extraction post-processing,
§2):

- `polarity: negative` marks a subject that rules usually remove:
  `trailing-whitespace`, `preamble`. "Strip/remove/delete/trim/avoid X" on a
  negative subject is a ban; an extracted `require`/`prefer` with such a verb
  on its evidence line becomes `forbid`/`avoid`. Without the verb the
  directive stands ("Always begin by restating the question" requires a
  preamble).
- `implied_artifact` is the only artifact a subject occurs in: type hints,
  docstrings, comments, formatter → `code`; preamble, summary-at-end,
  explain-reasoning → `response`; commit-granularity → `commit-message`; test
  runner → `tests`; headers → `markdown`. Per object: `emoji` "in headers" →
  `markdown` (emoji in general has none). It replaces an extracted `any`, never
  an explicit artifact. Without it, a requirement left at `any` against a ban
  on `markdown` reads as a scope carve-out (§3 row 12) and a real conflict
  becomes `needs_review`.

## 2. Extraction prompt (summary; full text in `src/skillfetch/ingest/prompts/extract.md`)

- Input: the whole SKILL.md with line numbers (`  12| text`), counted from the
  top of the file so `evidence.line_no` matches what users open.
- System prompt: the template plus the controlled vocabulary of §1.1, rendered
  from `resolve/vocabulary.py` (exclusive terms list their alternatives). It is
  identical for every skill and sent with `cache_control`, so after the first
  call it is a cache read.
- Instruction: list every instruction that would change how an agent behaves
  if followed. Skip background explanation, examples, and anything not
  actionable. One constraint per actionable instruction. Quote the line: **no
  quotable line, no constraint**. Conditions are, when possible, a single
  language, framework or artifact name. Scopes are narrowed only when the line
  names them or the subject only exists there (the §3 carve-out rules make a
  one-sided narrowing change the relation).
- Output: structured output (`output_config.format`, strict JSON schema in
  `ingest/extract.py`) for the whole extract object of `index-format.md` §1.5.
- Backends (`ingest/backends.py`, protocol `ExtractBackend` in `extract.py`):
  `anthropic/<model>` uses the Messages API with `output_config.format`;
  `openai/<model>` uses Chat Completions with `response_format: json_schema`
  (`strict: true`), and `--base-url` points the same backend at any
  OpenAI-compatible server (vLLM, Ollama). `openrouter/<vendor>/<model>` uses
  the same backend against OpenRouter with `provider.require_parameters` (so
  structured output is honoured), sends only parameters the model lists as
  supported, and records OpenRouter's billed `usage.cost`. All backends return
  one provider-neutral completion; parsing, the retry and the evidence check
  are shared.
- Temperature 0 is sent where the model accepts it. Anthropic current models
  reject it (not sent); on the OpenAI backend a 400 naming `temperature` drops
  it for that model. Reproducibility comes from the extract cache: a skill is
  extracted once per `(extract_version, provider/model, content_hash)`.
- Validate with pydantic; on failure retry once with the validation error
  appended; on second failure record `extract_failed`. A refusal is not retried.
- Evidence check after validation: a quote found on its cited line is kept; a
  quote found on exactly one other line is kept with the line corrected (a
  miscount, reported as `repaired`); anything else is dropped (`dropped`, with
  the reason).
- Vocabulary post-processing (`apply_vocabulary`, after the evidence check and
  before the per-line merge): the polarity flip and the implied artifact of
  §1.1. Every change is recorded in the record's `adjusted` list. The hand
  labels are a fixed point (a test checks it).
- `EXTRACT_VERSION` must be bumped whenever the prompt, the schema or the
  post-processing changes (it keys the cache); a test pins the prompt+schema
  fingerprint so a prompt change cannot slip through.

Calibration set: `tests/fixtures/skills/` has ≥ 15 skills with hand-labelled
constraints. `skillfetch ingest tests/fixtures --with-api --calibrate`
(`ingest/calibrate.py`) extracts every fixture skill and prints:

- **Field agreement.** Extracted constraints are aligned to labelled ones by
  evidence line (per skill, best field match on the same line), then compared
  per field: subject, directive, object, scope (artifact + phase + condition,
  also broken out), strength, direction. Labelled constraints with no
  extracted constraint on their line are `MISSED`; leftovers are `EXTRA`.
- **Pair-relation accuracy** — the real metric. The §3–§4 rules run on the
  extracted constraints for every pair of fixture skills, and each pair's
  label (as in `expected.yaml`, `subsumes` direction included) is compared
  with the hand label. Every mismatched pair is printed with the hand-labelled
  evidence lines and what was extracted on those lines.

**Gates.**

- **Hard: conflict precision = 1.0.** Every pair the extracted constraints
  call `conflict` must be labelled `conflict`. One false conflict fails
  calibration (`--calibrate` exits 1). This is the §7 policy applied to the
  extractor: a false "these skills contradict" costs more trust than any miss.
- **Soft: informative-pair accuracy ≥ 0.85.** Informative pairs are those
  where the hand label or the extracted relation is not `independent`. Most
  fixture pairs are independent (787 of 820), so accuracy over all pairs is
  ~0.96 for an extractor that extracts nothing; over informative pairs it
  scores 0, and every false relation on an independent pair enlarges the
  denominator. Missing the target is reported (`MISSED`) but does not fail the
  run; it means fix the prompt before building on the extractor.

Conflict precision is vacuously 1.0 when no conflict is flagged, so an
extractor that finds nothing passes the hard gate; the soft target is what
catches it. Accuracy over all pairs, labelled-pair recall and the number of
false positives are printed as well.

## 3. Pairwise relation

Given constraint `a` from skill A and `b` from skill B:

```
norm(x)        = lowercase, collapse whitespace, naive per-word singular, strip edge punctuation
same_subject   = norm(a.subject) == norm(b.subject)
scopes_overlap = (a.artifact == b.artifact or either is "any")
             and (a.phase == b.phase or either is "any")
opposite       = {require,prefer} vs {forbid,avoid}  (directive polarity differs)
same_polarity  = both in {require,prefer} or both in {forbid,avoid}
opposed(a, b)  = conflict if both `must`, else tension
```

Relation of the pair (a, b) — evaluated top to bottom, first match wins
(implemented in `src/skillfetch/resolve/relation.py`):

| # | condition | relation |
|---|---|---|
| 1 | exactly one is `order` | `independent` |
| 2 | both `order`, ¬scopes_overlap | `independent` |
| 3 | both `order`, same edge (A before B, after normalizing "B after A") | `redundant` |
| 4 | both `order`, reversed edge | `needs_review` if norm(conditions) differ, else opposed(a, b) |
| 5 | both `order`, otherwise | `independent` |
| 6 | ¬same_subject ∨ ¬scopes_overlap | `independent` |
| 7 | same_polarity ∧ norm(objects) equal (both null counts as equal) | `redundant` |
| 8 | both positive ∧ both objects non-null ∧ subject is exclusive (§1.1) | see 8a–8d |
| 8a | … either object names no single known alternative | `needs_review` |
| 8b | … choices from different ecosystems, or the same choice reworded | `independent` |
| 8c | … different choices, same ecosystem, norm(conditions) differ | `needs_review` |
| 8d | … different choices, same ecosystem, conditions equal | opposed(a, b) |
| 9 | same_polarity, objects differ (otherwise) | `independent` |
| 10 | opposite ∧ both objects non-null ∧ differ ("require pnpm" vs "forbid npm") | `independent` |
| 11 | opposite ∧ positive side has no object, negative side has one ("use emoji" vs "never in headers": a carve-out) | `needs_review` |
| 12 | opposite ∧ the positive side's scope is broader on artifact or phase (positive `any`, negative specific; "use emoji" vs "never in Markdown": a carve-out by scope) | `needs_review` |
| 13 | opposite ∧ norm(conditions) differ (incl. one null) | `needs_review` |
| 14 | opposite (objects and scopes equal, or a blanket ban — broader object or scope on the negative side — vs a specific requirement; conditions equal) | opposed(a, b) |

Rows 11 and 12 are the same asymmetry, once by object and once by scope. A ban
that is narrower than the requirement reads as an exception to it, so the pair
is probably compatible: `needs_review`. A ban that is broader than (or equal
to) the requirement cannot be followed together with it: opposed. When the
positive side is broader on one dimension and the negative on the other, row 12
applies (unsure → `needs_review`).

Rows 8a, 8c and 10–13 are v0.1 precision choices: an object, scope or
condition mismatch means the rules cannot tell whether both instructions can be
followed at once, so they never produce `conflict`. Consequences accepted for
v0.1: "always ask before editing" (any phase) vs "never ask during
implementation" is `needs_review`, although most edits happen during
implementation; mutually exclusive choices are only caught for exclusive vocabulary subjects
and listed alternatives (row 8); two bans on different choices ("never npm",
"never yarn") are compatible; and the same text under identical conditions is
treated as unconditional.

`needs_review` is a first-class outcome. v0.1 never upgrades it to `conflict`
automatically; it is shown to the user with both evidence lines.

## 4. Skill-level relation

`relation(A, B)` is the relation of B given A (A is already in the set). For
skills A, B, compute all constraint pairs (|A|×|B| ≤ 900, trivial). Then:

- `conflict` if any pair is `conflict`.
- else `redundant` if **B ⊆ A**: B's constraint multiset, after normalization,
  is a sub-multiset of A's. Dropping B then loses no constraint — the
  "lossless" criterion. B must be non-empty: a skill with no constraints is
  never redundant (the empty set is a subset of everything, but there is no
  evidence line to show). Partial overlap (neither side contained) is **not**
  redundancy.
- else `tension` if any pair is `tension`.
- else `needs_review` if any pair is `needs_review`.
- else `independent`.

Every relation is symmetric except `redundant`, which is directional: if B ⊊ A,
then `relation(A, B) = redundant` but `relation(B, A)` is not (A adds
constraints B lacks). Equal multisets are redundant in both directions; that
two-way case is what dedup uses (index-format.md §1.6).

Redundant ranks above tension: if B's constraints all appear in A, any tension
between them is internal to A, and loading B adds nothing.

Lossless is measured on extracted constraints only. Body text that yields no
constraint (examples, background, scripts) is not compared; a subsumed skill
can still carry useful examples. v0.1 accepts that: the set stays smaller and
the superset's instructions are all present.

Normalized identity of a constraint for multiset containment: `(norm(subject),
directive, norm(object), artifact, phase, norm(condition), strength)`; for
`order`, `(edge, artifact, phase, norm(condition), strength)`. Evidence is not
part of identity.
Containment is exact on identity: a `should` is not subsumed by a `must`.

The result carries the constraint pairs at the winning relation (all
conflicting pairs; for `redundant`, each of B's constraints paired with its
match in A). These are the evidence lines of §6.

Also compute `complementary` as a separate boolean (does not affect inclusion):
`A.produces ∩ B.consumes ≠ ∅` in either direction, or (`A.tags.domain ∩
B.tags.domain ≠ ∅` and both have phase tags and `A.tags.phase ∩ B.tags.phase =
∅`). Surfaced as a hint only; v0.1 computes it but does not put it in the
`resolve_set` output.

## 5. `resolve_set(auto_ids, pinned_ids)`

```
input:  auto   = candidates chosen by the host model (ordered by its preference)
        pinned = user-named skills (ordered as given)
output: included, excluded[{id, reason, conflicts_with, evidence}], warnings, precedence

0. repeated ids are collapsed (first occurrence wins); an auto id that is also
   pinned is treated as pinned only.
1. included = pinned (all of them, always)
2. for each pair within pinned:
     if conflict → warnings += finding(kind=conflict, a=X, b=Y, evidence=both lines)
     (never exclude a pinned skill; only conflicts are warned for pinned pairs)
3. for each a in auto, in order, compare against every s currently in included
   (skills excluded earlier never block later candidates):
     any conflict   → excluded (reason=conflict, conflicts_with=first such s, evidence=both lines)
     else any s with a ⊆ s → excluded (reason=redundant_with, conflicts_with=first such s, evidence=matched lines)
     else           → included; one warning per s with tension or needs_review
   "first" = earliest in precedence order. A candidate that is a strict
   superset of an included skill is included (it adds constraints); the
   earlier skill stays, since resolve_set never removes what it already chose.
4. precedence = pinned in given order, then auto in given order (included only).
   load_skills emits a header:
     "Skills are listed in precedence order. If two instructions disagree,
      follow the earlier one."
5. set_id = sha256("\n".join(sorted included ids))[:12]; cache the resolution for the session.
```

In every finding and exclusion, `a` is the skill already in the set (the
winner) and `b` the later one. Warnings and exclusions are structured JSON
(`Finding`, `Excluded` in `resolve/models.py`); §6 is their text rendering.

Rationale for step 3 ordering: the host model ranked `auto`; earlier picks
win ties. We do not re-rank. We only remove.

## 6. Report format (`scan` and `resolve_set` excluded entries)

Every exclusion and warning must render like this, no exceptions:

```
CONFLICT  commit-style@a1b2 ⟷ conventional-commits@c3d4
  subject: commit-granularity   scope: commit-message / any
  commit-style@a1b2:42        "Squash every feature into a single commit before opening a PR."
  conventional-commits@c3d4:17 "Never squash; one logical change per commit, always."
```

Labels: `CONFLICT`, `TENSION`, `NEEDS_REVIEW`, `REDUNDANT`. One `subject:` line
plus two evidence lines per constraint pair; `scope` shows the overlap (the
narrower of each side). Order pairs render as `subject: order: A before B`.

If there is no evidence line to print, the finding does not exist. This is a
hard rule: it is what keeps false positives from destroying trust.

## 7. Precision policy for v0.1

- Extraction quality is gated separately (§2: conflict precision 1.0 hard,
  informative-pair accuracy ≥ 0.85 soft);
  this section is about the rules given correct constraints.
- Measured on `tests/fixtures/skills/`: `conflict` precision must be 1.0;
  recall is reported but not gated. Because fixture constraints are
  hand-labelled, `tests/resolve/test_corpus_contract.py` additionally asserts
  the exact relation of every pair (labels in `tests/fixtures/expected.yaml`),
  which tests the rules in isolation from extraction quality.
- Anything the rules are unsure about goes to `needs_review`. A reviewer (human
  or, in v0.3, an LLM judge behind a flag) resolves it. We ship the conservative
  rules, not the clever ones.
- Known blind spots, documented in README: semantic conflicts without shared
  subject ("minimal design" vs "rich visual hierarchy"), script-level behaviour,
  conflicts that only manifest on a specific task. These are v0.3+ problems and
  need the outcome log, not better regexes.
