---
name: skillfetch-router
description: Use at the start of any coding task that adds or changes code, tests, docs or config (more than a one-line edit in one file), fixes a bug, or starts a feature — before reading the codebase. Skip only a one-line edit in a single file, a rename, or answering a question.
---

# skillfetch router

Use the skillfetch MCP tools to pick skills for the task at hand. Nothing gets installed;
the next task searches again.

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

1. **Restate the task in one English sentence**, whatever language the user wrote in,
   naming the stack and the target files when you know them: "Refactor the React
   `UserCard` component in `src/components/` into smaller presentational components".
   Do not explore the code first; the search needs the task, not the code.
2. If no `mcp__skillfetch__*` tool is in your tool list yet, the server is still
   starting: load them with ToolSearch (query `+skillfetch`), and search again if it
   says the server is connecting.
3. Call `profile_repo` with the repository root once per session (it reads manifest files
   only) and pass the result as `profile` to `search_skills`.
4. Call `search_skills` with that sentence. It returns 50 one-line summaries, best BM25
   match first: read all 50 and pick 1–3 that fit this task — the best fit is often not
   near the top. Each result has a `token_estimate`: when two fit equally, take the
   smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default).
5. If the user named a skill ("use the pdf skill"), call `search_skills` with that name,
   take the id of the result whose title matches, and put it in `pinned_ids`. A local
   skill folder (one the user named, or a project skill that fits) is pinned as
   `path:/absolute/path`. If nothing matches, say so.
6. Call `resolve_set` with your picks as `auto_ids` (in order of preference) and the
   pinned skills as `pinned_ids`. Respect `excluded`; read every warning's two quoted
   lines and decide whether they matter for this task.
7. Call `load_skills` with the `set_id` and follow the returned instructions. When two of
   them disagree, the earlier skill wins (the precedence header says so).
8. Do the work. If `load_skills` lists a skill in `errors` (hash mismatch, fetch error,
   dropped for the token budget), continue without it and say so.

## Rules

- Search with the task, not with the user's literal wording or a list of keywords.
- Never load a skill that `resolve_set` excluded.
- Do not search again mid-task unless the task changes.
