# Fixture corpus

The contract for `resolve/` (see `docs/design/constraints.md` §7).

- `skills/<name>/SKILL.md` — a small hand-written skill. `name` in the frontmatter
  equals the directory name, which is also the skill id in tests.
- `skills/<name>/constraints.json` — hand-labelled constraints for that skill,
  in the schema of `constraints.md` §1 (without `id`; the loader assigns
  `<name>#c<n>`). `evidence.line_no` is the 1-based line in `SKILL.md`,
  counting the frontmatter; `evidence.text` must appear verbatim on that line.
- `expected.yaml` — hand-labelled skill-level relations. Every unordered pair not
  listed there must resolve to `independent`, so the tests check the full
  pairwise matrix, not just the positives. `subsumes: [superset, subset]` is
  the one directional label: the subset is redundant given the superset.

When you add a skill, label its constraints by hand and re-check every pair it
forms with the existing skills. Prefer adding near misses (same subject,
compatible instructions) — they are what protect conflict precision.
