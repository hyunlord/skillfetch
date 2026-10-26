---
name: skillfetch-router
description: Run this before your first tool call — before git status, Read, Grep, Glob or ls — whenever the user asks for a code change: a feature, a bug fix, a refactor, tests, docs, config, CI or deploy work, even if it looks small. Run it again each time a new task arrives in the same conversation; do not reuse the skill choice from an earlier task. It loads the skills for the task in four quick MCP calls. Skip it only for a one-line edit in one file, a rename, or a question with no edits.
---

# skillfetch router

Run this again each time a new task arrives in the same conversation; do not reuse the
skill choice from an earlier task. Use the skillfetch MCP tools to pick skills for this
task. Nothing gets installed.

## When

Run the steps first, before you grep, glob or read the codebase, for:

- a feature, even one that fits in a single file
- a bug fix, even when you expect the fix to be one line
- a refactor: splitting, moving or extracting code
- tests: adding, extending or repairing them
- documentation: README sections, guides, docstrings, comments across a file
- configuration: build, lint, CI, dependency or framework config
- a review, a migration, a new document

"It looks small" is not a reason to skip. Neither is a project skill that seems to fit
(for example one in `.claude/skills/`): run the steps and pin it (step 5).

Skip only: a one-line edit in a single file (a typo, a constant, an import), a rename
with no other change, or answering a question without editing files.

## Steps

1. **Restate the task in English**, whatever language the user wrote in, as three short
   sentences: (a) what it builds or fixes, in domain nouns ("Conditional GET with ETags
   for the product catalog API"); (b) the kind of work and how to do it: the approach the
   user asked for ("Test-driven: write failing tests first", "Minimal diff", "Security
   first"), or, if they did not say, the one that fits this task best ("Bug fix: find the
   root cause first"); (c) the stack and target files ("Go net/http, `internal/catalog/`").
   Add (d), the user's request copied word for word, as a fourth query. Do not explore
   the code first; the search needs the task, not the code.
2. If no `mcp__skillfetch__*` tool is listed yet, the server is starting: load them with
   ToolSearch (query `+skillfetch`), and search again if it says it is connecting.
3. Call `profile_repo` with the repository root once per session (it reads manifest files
   only) and pass the result as `profile` to `search_skills`. Search once per task.
4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best
   first: read all 50 and pick up to 3 that fit this task — the best fit is often not
   near the top. Do not pick a skill unless you can say in one sentence what its summary
   changes in this task; often none fits, and then you skip steps 6–7. Each result has a
   `token_estimate`: when two fit equally, take the smaller, and keep the set's total
   under `load_skills`' budget (8000 tokens by default).
5. If the user named a skill ("use the pdf skill"), call `search_skills` with that name,
   take the id of the result whose title matches, and put it in `pinned_ids`. A local
   skill folder (one the user named, or a project skill that fits) is pinned as
   `path:/absolute/path`. If nothing matches, say so.
6. Call `resolve_set` with your picks as `auto_ids` (in order of preference) and the
   pinned skills as `pinned_ids`. Respect `excluded`; read every warning's two quoted
   lines and decide whether they matter for this task.
7. Call `load_skills` with the `set_id` and follow the returned instructions.
8. Do the work. If `load_skills` lists a skill in `errors` (hash mismatch, fetch error,
   dropped for the token budget), continue without it and say so.

