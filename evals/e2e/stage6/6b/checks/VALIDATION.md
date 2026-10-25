# 6b check validation (on the upstream branch s6b-a, before any session)

Each bundle (1)/(3) check ran on an untouched `s6b-a` worktree (2026-10-24). Expected: checks run to completion, the
worktree is restored, items for work the task asks for fail, items that guard existing behaviour pass. Outputs:
`checks/validation/<task>/check.json`.

| task | pass on upstream | failed items on upstream | note |
|---|---|---|---|
| d1-landing | False | /landing 404 at both widths | expected (new route) |
| d2-redesign | True | — | expected: redesign of an existing page; the check guards build, render and the /users/[id] links |
| d3-dashboard | False | /dashboard 404 at both widths | expected (new route) |
| d4-email | True | — | expected: redesign of an existing email; the check guards build, export, render, prop names. `npm run build` 25 s, `export` 1.4 s |
| s6b-t004 | False | celery dep, tasks.py schedule, Item fields, new revision, template | expected; alembic check and backend suite (58) pass on upstream |
| s6b-t133 | False | Dockerfile and .dockerignore items | expected; next build passes. `docker build` is not checked (no Docker daemon on the harness machine) |
| s6b-t179 | False | dedupe_items.py missing | expected; seed SQL tested separately on an upstream DB (6 rows inserted) |
| s6b-t354 | False | new function, call in init(), unknown-revision abort | expected. A first version used `alembic downgrade -1`, which passed on upstream (the downgrade drops `created_at` and initial_data crashes anyway); replaced before freezing by "schema at head, alembic_version set to an unknown id" |

Dockerfile parsing (t133) joins `\` continuation lines; tested on a sample multi-line `RUN --mount=... \ npm ci`.
