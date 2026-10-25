# skillfetch e2e — stage 1 materials (DRAFT)

Prepared 2026-10-22 for the stage-1 "3-condition comparison". Nothing here has been run with `claude`;
these are inputs for the user to edit before the design is fixed.

## Files

| path | what |
|---|---|
| `tasks-stage1.yaml` | 20 draft tasks (10 fastapi, 10 nextjs; en 10 / ko 10; feature 7, refactor 4, test 4, bugfix 3, docs 2; 5 UI tasks). Same top-level shape as `../tasks.yaml` (`repos` + `tasks`) plus `check`, `screens` (UI tasks), `expert_skills`, and `verified` on bugfix tasks. |
| `expert-skills.md` | Per task: the 0–2 index skills an expert would pin (exact id, title, token_estimate, fit, quoted reason), "none fits" where nothing fits, and a comparison with what the stage-0 router loaded. |
| `scripts/screenshot.py` | Build + start an app from a worktree, full-page PNG per route, `screens.json` manifest, always stops what it started. Kinds: `nextjs`, `fastapi-frontend`. |
| `screens-smoke/` | Smoke run on a fresh `repos/nextjs` worktree at `e2e-baseline`: `index.png`, `about.png`, `users.png`, `users-101.png`, `screens.json`, `logs/`. |
| `screens-smoke/fastapi-frontend/` | Smoke run on a fresh `repos/fastapi` worktree at `e2e-baseline`: `login.png` (anonymous), `index.png`, `items.png`, `admin.png`, `settings.png` (logged in as superuser, 3 seeded items). |
| `wt/` | Empty; temporary worktrees used for verification were created here and removed. |

## Assumptions

- Conditions: **A** no skillfetch (router skill and `.mcp.json` removed), **B** skillfetch router
  (+ optional prompt hook), **C** the `expert_skills` of the task pinned. Same prompt, model, max turns
  and baseline commit in all three.
- Outcome is judged by the `check` of each task, run by the harness after the session on the session's
  worktree. Hidden tests and mutants are *described* in `check`; the files are not written yet.
- fastapi checks run with `FASTAPI_ENV=development` in the process env (without it `app.main` fails
  to import: `backend/app/frontend` does not exist in a source checkout) and a per-run `DATABASE_URL`.
- Bugs in bugfix tasks were reproduced on the baseline (TestClient script against a private Postgres for
  fastapi; `next build` output + screenshot manifest for nextjs). The `verified:` field says how.
  Mutants in the two fastapi test tasks were applied one at a time to the baseline: the existing 58 tests
  still pass under each of them, so they only fail if the session's new tests catch them.
- `token_estimate` values come from the current index (rebuilt after stage 0; a few differ by up to ~70
  tokens from the stage-0 load numbers).

## Screenshot pipeline

```bash
cd <e2e>/stage1
# nextjs: npm ci only if node_modules is missing -> next build -> next start
uv run scripts/screenshot.py --worktree <wt> --kind nextjs --out <dir> --routes / /about /users /users/101
# fastapi-frontend: private Postgres (initdb in a temp dir) -> alembic + initial_data -> `fastapi run`;
# bun install only if node_modules is missing -> tsc + vite build into a temp dir -> vite preview.
# Routes are visited logged in as FIRST_SUPERUSER from the worktree's .env; append @anon to skip login.
uv run scripts/screenshot.py --worktree <wt> --kind fastapi-frontend --out <dir> \
    --routes /login@anon / /items /admin /settings [--seed-items 3]
```

Options: `--mode dev` (next dev / vite dev instead of build+serve), `--viewport 375x800`,
`--timeout 300` (build/readiness), `--nav-timeout 30`, `--settle-ms 500`, `--pgbin` (default
`/opt/homebrew/opt/postgresql@16/bin`). Playwright comes from the script's inline metadata
(`uv run` installs it into uv's cache); Chromium is installed with `playwright install chromium` only if
launching fails.

Behaviour:
- Ports: first free ports in 4100–4199 (1 for nextjs; 3 for fastapi-frontend: Postgres, API, web).
  Postgres runs with the Unix socket disabled (`unix_socket_directories=''`; macOS caps socket paths at
  103 bytes). It never touches the stage-0 Postgres on 55432.
- Worktree guard: before starting, the script snapshots all tracked files and the list of untracked
  non-ignored files; at the end it restores any tracked file the build/servers changed and deletes new
  untracked files (e.g. `AGENTS.md` written by `next dev` — seen in the dev-mode test). Restored paths are
  listed in `screens.json` → `worktree_restored`. Ignored paths (`node_modules`, `.next`, `.venv`) stay.
- Cleanup: servers run in their own process groups and are killed (TERM, then KILL) in a `finally`
  block; SIGTERM/SIGHUP to the script go through the same path; Postgres is stopped with
  `pg_ctl -m fast` and its temp dir removed.
- Output: `<out>/<route-slug>.png` (`/` → `index.png`, `/users/101` → `users-101.png`), `<out>/screens.json`
  (per route: status, final_url, title, html_lang, text = body innerText (first 20k chars), links
  (href / text / aria-current), console_errors, page_errors, http_errors ≥ 400, file; plus build
  timings, ports, git HEAD/status, start_error), `<out>/logs/*.log`.
- Exit code: 0 all routes captured, 1 some route failed or returned ≥ 500, 2 build/start failed
  (manifest still written, no PNGs).

What was run (2026-10-22):
- nextjs build mode, `/ /about /users /users/101` → all 200, no console errors; build 6.5 s; the four
  PNGs show the expected pages (nav + "Hello Next.js 👋"; About; Users List with 101–104; "Detail for
  Alice / ID: 101"). Output in `screens-smoke/`.
- fastapi-frontend build mode, `/login@anon / /items /admin /settings` → all 200, no console/page
  errors; login form, dashboard greeting, items table with 3 seeded rows, admin users table, settings
  page. Output in `screens-smoke/fastapi-frontend/`.
- nextjs dev mode (`/ /users/102 /nope /api/users`) → 200/200/404/200; `next dev` created `AGENTS.md`,
  which the guard removed.
- Failure path: a syntax error injected into `pages/about.tsx` → exit 2, `start_error: next build
  failed`, no server left. SIGTERM 5 s into a fastapi-frontend run → exit 2 (`SystemExit: 143`),
  Postgres/API/web stopped, temp dir removed, ports free.

Known limits: no lock around port selection, so two parallel runs can race for the same port (run them
serially or retry on exit 2). A port in TIME_WAIT counts as busy. `next build` writes `.next/` into the
worktree (ignored by git; the stage-0 harness builds there anyway).

## Open questions for the user

1. **Condition C mechanism.** Pin via `resolve_set(pinned_ids=…)` + `load_skills` in the prompt, copy the
   skill bodies into `.claude/skills/`, or prepend them to the prompt? Each changes what "pinned" means
   and how many tokens the session sees.
2. **"None fits" tasks** (s1-fa-09, s1-nx-01, s1-nx-03, s1-nx-05, s1-nx-09). Under C they are identical
   to A. Keep them (measures B's cost when nothing fits), drop them from C, or allow `path:` pins of the
   repo-local skills?
3. **Repo-local skills in fastapi.** `.claude/skills/fastapi` and `sqlmodel` ship with the upstream repo
   and are active in all conditions after `uv sync`. Keep them in A (realistic) or remove them (clean A)?
4. **B variants.** Router only, router + prompt hook, or both as separate conditions? Stage 0 fired on
   7/17 non-trivial tasks without a hook.
5. **Repetitions.** Stage 0 ran each task once. How many runs per task × condition (cost: 20 × 3 × n
   sessions; stage-0 sessions were 0.6–1.6 USD API-equivalent each)?
6. **Hidden tests and mutants.** Write them now (before any session) and freeze them? If a session edits
   the file a mutant targets, does a non-applying mutant count as "not caught"?
7. **UI judging.** Who rates the screenshots (user, LLM judge with a rubric), and blind to condition?
   The DOM facts in `screens.json` cover the objective part; layout quality is left to the judge.
8. **Max turns.** Stage 0 used `--max-turns 25`; fa-05 ended with `error_max_turns`. Same limit for all
   conditions, or raise it so B's extra tool calls do not cost it the task?
9. **Prompt specificity.** Some prompts name files and exact labels (needed for automatic checks, e.g.
   "Previous"/"Next"), others do not. Is that acceptable, or should every prompt be equally specific?
10. **Environment.** Stage 0 inherited the user's global `~/.claude` (CLAUDE.md, 12 plugins, hooks).
    Keep that for stage 1 or run with an isolated config dir?
11. **Negative controls.** Stage 1 has no trivial tasks. Add 2–3 trivial ones again to measure false
    firing under B (and under the prompt hook)?
