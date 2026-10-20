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
    thing it must precede/follow, `scope.condition` holds `before|after`.
- `object` — what the directive is about, when `subject` alone is ambiguous.
  Optional.
- `scope.artifact` — what the rule applies to: `code | tests | commit-message |
  pr-description | markdown | response | plan | any`. `any` when the skill does
  not narrow it.
- `scope.phase` — `plan | implement | test | review | format | any`.
- `scope.condition` — free-text condition if the rule is conditional ("when
  writing Python"), else null.
- `strength` — `must | should`. Derived from directive (require/forbid → must,
  prefer/avoid → should) unless the text clearly says otherwise. `order` has no
  polarity; its strength defaults to `must` unless stated.
- `evidence` — the exact source line. **Required.** A constraint without a
  quotable line is dropped by the extractor. `line_no` is 1-based in the
  original `SKILL.md`, counting the frontmatter, so users can jump to it.

For `order`, `object` and `scope.condition` (`before|after`) are required;
"A before B" and "B after A" are the same constraint.

### 1.1 Controlled subject vocabulary (v0)

Start small; grow from extraction output, not from imagination.

```
formatting: emoji, headers, bullet-points, code-blocks, line-length, trailing-whitespace
language:   type-hints, docstrings, comments, naming-convention, error-handling, logging
process:    tests-first, commit-granularity, branch-naming, pr-size, review-before-merge
output:     response-length, preamble, summary-at-end, ask-before-acting, explain-reasoning
tooling:    package-manager, linter, formatter, test-runner, build-tool
```

The extractor is told: "If the constraint is about one of these, use that exact
term as `subject`."

## 2. Extraction prompt (summary; full text in `src/skillfetch/ingest/prompts/extract.md`)

- Input: SKILL.md body with line numbers.
- Instruction: list every instruction that would change how an agent behaves
  if followed. Skip background explanation, examples, and anything not
  actionable. One constraint per actionable instruction. Quote the line.
- Output: JSON array matching §1, inside the larger extract object from
  `index-format.md` §1.5.
- Temperature 0. Validate with pydantic; on failure retry once with the
  validation error appended; on second failure record `extract_failed`.

Calibration set: `tests/fixtures/skills/` has ≥ 15 skills with hand-labelled
constraints. `skillfetch ingest --with-api --calibrate` prints per-field
agreement so prompt changes can be measured, not eyeballed.

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
| 4 | both `order`, reversed edge | opposed(a, b) |
| 5 | both `order`, otherwise | `independent` |
| 6 | ¬same_subject ∨ ¬scopes_overlap | `independent` |
| 7 | same_polarity ∧ norm(objects) equal (both null counts as equal) | `redundant` |
| 8 | same_polarity, objects differ | `independent` |
| 9 | opposite ∧ both objects non-null ∧ differ ("require pnpm" vs "forbid npm") | `independent` |
| 10 | opposite ∧ positive side has no object, negative side has one ("use emoji" vs "never in headers": a carve-out) | `needs_review` |
| 11 | opposite ∧ norm(conditions) differ (incl. one null) | `needs_review` |
| 12 | opposite (objects equal, or a blanket ban vs a specific requirement; conditions equal) | opposed(a, b) |

Rows 9–11 are v0.1 precision choices: an object or condition mismatch means the
rules cannot tell whether both instructions can be followed at once, so they
never produce `conflict`. Two consequences, both accepted for v0.1:
mutually exclusive choices stated only positively ("always npm" vs "always
pnpm") are missed unless one skill also forbids the other's choice; and the
same text under identical conditions is treated as unconditional.

`needs_review` is a first-class outcome. v0.1 never upgrades it to `conflict`
automatically; it is shown to the user with both evidence lines.

## 4. Skill-level relation

For skills A, B, compute all constraint pairs (|A|×|B| ≤ 900, trivial). Then:

- `conflict` if any pair is `conflict`.
- else `redundant` if the constraint multisets are equal after normalization
  (used by dedup, §index-format 1.6) — partial overlap alone is **not**
  redundancy, and two skills with no constraints are **not** redundant (there
  is no evidence line to show).
- else `tension` if any pair is `tension`.
- else `needs_review` if any pair is `needs_review`.
- else `independent`.

Redundant ranks above tension: if two skills carry the same constraints, any
tension between them is internal to each, and loading both adds nothing.

Normalized identity of a constraint for multiset equality: `(norm(subject),
directive, norm(object), artifact, phase, norm(condition), strength)`; for
`order`, `(edge, artifact, phase, strength)`. Evidence is not part of identity.

The result carries the constraint pairs at the winning relation (all
conflicting pairs; for `redundant`, the one-to-one matching). These are the
evidence lines of §6.

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
     else any redundant → excluded (reason=redundant_with, conflicts_with=first such s, evidence=matched lines)
     else           → included; one warning per s with tension or needs_review
   "first" = earliest in precedence order.
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
