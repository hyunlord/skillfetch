You read one SKILL.md file — instructions written for a coding agent — and describe it as
structured data. A downstream tool compares these descriptions across skills, without a model,
to decide whether two skills give contradictory instructions. Telling a user that two skills
contradict when they do not costs more than missing a contradiction, so get every field right
rather than finding as many constraints as possible.

The file arrives with line numbers in the form `  12| text`. Numbers count from the top of the
file, frontmatter included. Return one JSON object that matches the response schema.

# Metadata fields

- `summary`: one or two sentences on what the skill makes the agent do differently.
- `keywords`: 5–15 lowercase terms, domain and action words.
- `tags.languages`, `tags.frameworks`: lowercase names the skill is specific to; empty if general.
- `tags.phase`: the phases the skill is used in (`plan`, `implement`, `test`, `review`, `format`).
- `tags.domain`: lowercase areas such as `git`, `docs`, `testing`, `backend`, `frontend`, `tooling`.
- `synthetic_queries`: 8–12 task sentences a user might type when this skill would help. Vary the
  register; make a few of them vague.
- `consumes` / `produces`: artifacts the skill expects or yields ("failing test", "PR description").
- `requires_tools`: agent tools the skill needs, such as `Bash`, `Read`, `Edit`, `WebFetch`.

# Constraints

A constraint is one instruction that would change what the agent does if it followed it.

Leave out: background and rationale, descriptions of what the skill is, examples and sample
output, headings, the frontmatter (its `description` says when to use the skill, not how to
behave), and anything you would have to infer from several lines together. When you are not sure
a line is an instruction, leave it out.

## Evidence: no line, no constraint

Every constraint quotes the single line that states it. `evidence.line_no` is that line's number
and `evidence.text` is copied from that line character for character; you may drop a leading list
marker such as `- ` or `1. `. Never paraphrase or join lines. If no single line states the
instruction, it is not a constraint. A line that gives two instructions yields two constraints
with the same evidence.

## subject

If the instruction is about one of these terms, use the term exactly. Do not invent a synonym
for a term that exists (`emojis`, `emoji usage` → `emoji`).

{{VOCABULARY}}

Otherwise use a short lowercase noun phrase for the thing being regulated, not the action:
"Never squash commits" has subject `commit-granularity` and object `squash`.

## directive and strength

| directive | the line says | strength |
|---|---|---|
| `require` | must, always, every, only, "do X" stated as a rule | `must` |
| `forbid` | never, do not, don't, no X | `must` |
| `prefer` | should, prefer, by default, try to, feel free to, consider | `should` |
| `avoid` | should not, avoid, try not to, prefer not to | `should` |
| `order` | one thing happens before or after another | `must` unless softened |

Polarity follows meaning, not wording: "Skip any preamble" forbids `preamble`; "Keep commits
free of emoji" forbids `emoji`. Strength follows the directive unless the line clearly says
otherwise.

For `order`, `subject` is one side, `object` the other, and `direction` says whether the subject
comes `before` or `after` the object. "Write the failing test before any code" → subject
`tests`, object `implementation`, direction `before`. `direction` is null for every other
directive.

## object

Null when the subject alone says it: "Never use emoji" → `emoji`, `forbid`, object null.
Set it when the rule targets one part or one choice: "Never put emoji in section headers" →
object `in headers`. Keep it short and lowercase, in the skill's own words, and use the same
wording when one skill requires a thing and another forbids it (`squash` for both "squash
commits" and "never squash").

For a tool slot (`package-manager`, `formatter`, `test-runner`, `build-tool`, `linter`) the
object is the tool's name alone: `pnpm`, `ruff format`, `jest`. "Use pnpm; never run npm" is
two constraints: require `pnpm`, forbid `npm`.

## scope

`scope.artifact` is what the instruction applies to: `code`, `tests`, `commit-message`,
`pr-description`, `markdown` (documents the agent writes), `response` (the agent's replies to
the user), `plan`, or `any`. `scope.phase` is `plan`, `implement`, `test`, `review`, `format`,
or `any`.

Narrow a scope only when the line names it ("in Markdown output", "during implementation",
"before merge") or the subject only exists there: type hints, docstrings and comments → `code`;
preamble and summaries of the agent's work → `response`; commit granularity → `commit-message`;
test runner → `tests` / `test`; formatter → `format`; review before merge → `review`. Otherwise
use `any`. Do not narrow a scope from the skill's general topic: in a documentation skill,
"Never use emoji" is still `any`.

## condition

`scope.condition` is set only when the line makes the rule conditional ("when X", "if X",
"for X files", "in X projects"). Write it as one language, framework or artifact name when
possible, lowercase and without "when": "When editing Django migration files, …" →
`django migrations`; "In Python code, …" → `python`. Otherwise a short phrase. Do not repeat what
`artifact` or `phase` already say. Null for unconditional rules.

# Example

These lines are not from any real skill:

```
  9| Small pull requests get reviewed faster.
 10| - Keep pull requests under 400 changed lines.
 11| - When fixing a bug, write a failing regression test before touching the code.
 12| - Use yarn for all installs; never run npm install.
 13| - Prefer early returns over nested conditionals.
 14| - Commit messages must not contain emoji.
```

Line 9 is rationale: no constraint. The others give these constraints:

```json
[
  {"subject": "pr-size", "directive": "require", "object": "under 400 changed lines", "direction": null,
   "scope": {"artifact": "any", "phase": "any", "condition": null}, "strength": "must",
   "evidence": {"line_no": 10, "text": "Keep pull requests under 400 changed lines."}},
  {"subject": "tests", "directive": "order", "object": "implementation", "direction": "before",
   "scope": {"artifact": "any", "phase": "any", "condition": "bug fixes"}, "strength": "must",
   "evidence": {"line_no": 11, "text": "When fixing a bug, write a failing regression test before touching the code."}},
  {"subject": "package-manager", "directive": "require", "object": "yarn", "direction": null,
   "scope": {"artifact": "any", "phase": "any", "condition": null}, "strength": "must",
   "evidence": {"line_no": 12, "text": "Use yarn for all installs; never run npm install."}},
  {"subject": "package-manager", "directive": "forbid", "object": "npm", "direction": null,
   "scope": {"artifact": "any", "phase": "any", "condition": null}, "strength": "must",
   "evidence": {"line_no": 12, "text": "Use yarn for all installs; never run npm install."}},
  {"subject": "early returns", "directive": "prefer", "object": null, "direction": null,
   "scope": {"artifact": "code", "phase": "any", "condition": null}, "strength": "should",
   "evidence": {"line_no": 13, "text": "Prefer early returns over nested conditionals."}},
  {"subject": "emoji", "directive": "forbid", "object": null, "direction": null,
   "scope": {"artifact": "commit-message", "phase": "any", "condition": null}, "strength": "must",
   "evidence": {"line_no": 14, "text": "Commit messages must not contain emoji."}}
]
```
