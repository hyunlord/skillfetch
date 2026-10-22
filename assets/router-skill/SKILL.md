---
name: skillfetch-router
description: Before non-trivial coding work, find, de-conflict and load task-specific skills through the skillfetch MCP server. Skip it for trivial edits.
---

# skillfetch router

Use the skillfetch MCP tools to pick skills for the task at hand. Nothing gets installed;
the next task searches again.

## When

- Before non-trivial work: a feature, a refactor, a review, a migration, a new document.
- Not for trivial edits: typos, renames, one-line fixes, answering a question.

## Steps

1. **Restate the task in one English sentence**, whatever language the user wrote in,
   naming the stack and the target files: "Refactor the React `UserCard` component in
   `src/components/` into smaller presentational components". The index is English; a
   query in another language matches only the words it shares with English (a Korean
   request about React matches "react" and nothing else).
2. Call `profile_repo` with the repository root once per session (it reads manifest files
   only) and pass the result as `profile` to `search_skills`.
3. Call `search_skills` with that sentence. Read the summaries and pick 1–3 candidates
   that fit this task. If the user named a skill, pass it as pinned instead.
4. Call `resolve_set` with your picks as `auto_ids` (in order of preference) and the
   user's skills as `pinned_ids`. Respect `excluded`; read every warning's two quoted
   lines and decide whether they matter for this task.
5. Call `load_skills` with the `set_id` and follow the returned instructions. When two of
   them disagree, the earlier skill wins (the precedence header says so).
6. Do the work. If `load_skills` refuses a skill (hash mismatch, fetch error), continue
   without it and say so.

## Rules

- Search with the task, not with the user's literal wording or a list of keywords.
- Never load a skill that `resolve_set` excluded.
- Do not search again mid-task unless the task changes.
