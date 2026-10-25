# Expert-pinned skills per stage-1 task (DRAFT)

Assumptions
- Source: `~/.skillfetch/index/skills.jsonl` as on disk 2026-10-22 (manifest `built_at` 2026-10-22T06:15:43Z,
  1724 records). `token_estimate` values are from this index; a few differ from the stage-0 report
  (e.g. python-testing-patterns 6281 here vs 6213 at load time in stage 0) because the index was rebuilt
  after stage 0.
- Bodies were read only where they are already on disk (`~/.skillfetch/cache/<content_hash>/` or
  `runs/loaded/`). Picks marked **summary-only** were judged from the index summary/description/tags
  alone. Nothing was fetched from the network.
- Budget: each task's set stays under 8000 tokens (`load_skills` default).
- Fit: **good** = the body covers what the task needs; **partial** = useful general rules, gaps or
  mismatches noted; **none fits** = nothing in the index I would pin. I did not force a pick.
- Not in the index but present in the fastapi repo for all conditions: `.claude/skills/fastapi` and
  `.claude/skills/sqlmodel` (symlinks into `.venv`, active after `uv sync`). Stage 0 fa-02 pinned them via
  `path:`. For the fastapi tasks they fit better than anything in the index; see open question in README.

## Per task

| task | pick (exact id) | title | tokens | fit | reason (quote from index summary/description) |
|---|---|---|---|---|---|
| s1-fa-01 sort items | `uasl/api-design@bba608f8c974` | api-design | 3267 | partial | "covering resource URLs, HTTP behavior, response formats, pagination" — body has "Filtering, Sorting, and Search" and "BAD: 500 for validation errors / GOOD: 400 or 422". Its sort convention is `?sort=-created_at`, which differs from the `order_by`/`order` names the prompt asks for. |
| s1-fa-02 is_done + migration | `uasl/postgresql-table-design@59d09e948243` | postgresql-table-design | 4004 | partial, summary-only | "choosing data types and constraints ... It also covers ... safe schema evolution" (NOT NULL boolean with a default on a table that has rows). No skill in the index mentions Alembic or SQLModel. |
| s1-fa-03 dashboard card | `uasl/shadcn@fb196fe88c66` | shadcn | 4103 | good, summary-only | "Guides agents working in shadcn/ui projects to use project context, documentation, registries, and existing components before building or updating UI" (frontend has `components.json` and `src/components/ui/card.tsx`). Nothing in the index covers TanStack Query + the generated client. |
| s1-fa-04 items permission helper | `uasl/refactoring-patterns@7283bad3e86e` | refactoring-patterns | 5244 | good | "Use named, incremental refactorings to improve code structure while preserving observable behavior. Check tests around changes" — body: "Rule of Three ... Third copy of same logic → Extract the shared logic". |
| s1-fa-05 pagination dependency | `uasl/python-design-patterns@5c0fbe0d4633` | python-design-patterns | 3093 | partial | "clear separation of concerns, composition, and dependency injection. It also recommends delaying abstractions". Its DI pattern is constructor injection with Protocols, not FastAPI `Depends`. |
| s1-fa-06 owner-filter tests | `uasl/integration-testing@62b51275be50` | integration-testing | 5792 | good, summary-only | "write integration tests that exercise multiple components together, using real dependencies ... API testing patterns, database cleanup" (repo tests use TestClient + real Postgres). |
| s1-fa-07 auth dependency tests | `uasl/python-testing-patterns@e62d0f1ca316` | python-testing-patterns | 6281 | good | "pytest patterns, fixtures, mocks ... meaningful coverage of failure behavior" — body has "Testing Exceptions", "Monkeypatch", "Test Error Paths" (expired token, deleted/inactive user). |
| s1-fa-08 title null → 422 | `uasl/defense-in-depth@e9a7d1415325` | defense-in-depth | 975 | good, summary-only | "prevent invalid data from causing failures deeper in execution. Trace data flow, add checks at each layer" (null passes the Pydantic model and fails at the DB). |
|  | `uasl/api-design@bba608f8c974` | api-design | 3267 | partial | "BAD: 500 for validation errors / GOOD: 400 or 422 with field-level details" (body). Set total 4242. |
| s1-fa-09 case-insensitive email | none fits | | 0 | none | Considered `uasl/auth-implementation-patterns@7a99b395d548` (4031; "JWTs, sessions, OAuth2, RBAC ... passwords, tokens") — tags express/passport.js, nothing on identifier normalisation; `uasl/security-review@fcc354bc486e` (3055) — TypeScript/Next/Supabase checklist. |
| s1-fa-10 env var table in README | `uasl/quill@336ba74b0e79` | quill | 3199 | partial | "improve codebase documentation, type clarity, and README/API materials while preserving runtime behavior" — body READ phase lists "undocumented `.env`". About a third of the body is AUTORUN/Nexus hand-off protocol (same issue as radar in stage 0); `references/` files are not loaded. |
| s1-nx-01 prev/next links | none fits | | 0 | none | Nothing for the Pages Router. `uasl/next-best-practices@ee058f89acea` (1008) is App Router material (`generateStaticParams`, async `params`) and mostly links to sub-files. |
| s1-nx-02 /api/users/[id] | `uasl/backend-patterns@3d87ff489f3e` | backend-patterns | 3456 | partial, summary-only | description: "server-side best practices for Node.js, Express, and Next.js API routes"; summary "API design, data access ... error handling". |
|  | `uasl/api-design@bba608f8c974` | api-design | 3267 | good | "HTTP behavior, response formats" — status code table (400 / 404) and error response shape. Set total 6723. |
| s1-nx-03 custom 404 page | none fits | | 0 | none | `next-best-practices` error-handling.md describes App Router `not-found.tsx`; following it in this Pages Router repo would create a file Next ignores (`pages/404.tsx` is needed). |
| s1-nx-04 about card grid | `uasl/responsive-design@2cf7927ef938` | responsive-design | 3110 | partial, summary-only | "mobile-first styling, content-based breakpoints, fluid sizing, and container queries" (one card per row on narrow screens). Tags include tailwind css; the repo has no CSS framework. Rejected `uasl/web-component-design@af6d16dc78dc` (1873): its quick start is Tailwind + `class-variance-authority`, which would pull new deps into a plain-CSS repo. |
| s1-nx-05 nav array + aria-current | none fits | | 0 | none | `uasl/accessibility-compliance@696d2b4119ed` (2962; "semantic HTML, keyboard access, screen-reader support") — body has no `aria-current` or navigation-landmark guidance (checked on disk). |
| s1-nx-06 lib/users.ts refactor | `uasl/refactoring-patterns@7283bad3e86e` | refactoring-patterns | 5244 | good | "preserving observable behavior" — body section "Moving Features Between Objects" and the test → refactor → test cycle. The repo has no tests, so its "wrap in tests" rule can only be met by build + output comparison. |
| s1-nx-07 Vitest + RTL setup | `uasl/tdd-workflow@6eadb0bf0ea8` | tdd-workflow | 2411 | partial | tags "jest, vitest, playwright, react testing library, next.js"; body has a `@testing-library/react` render/screen example. Its core rule "Tests BEFORE Code" and 80% coverage target do not fit adding tests to existing code. |
| s1-nx-08 getStaticPaths/Props tests | `uasl/unit-testing@6c5fbb821103` | unit-testing | 6067 | partial | "write and improve isolated unit tests ... Emphasizes focused, deterministic tests" — the two functions are plain async functions. Most of the 6067 tokens are C#/Java/Go; its sample `vitest.config.ts` uses `include: ['src/**/*.test.ts']` and 80% thresholds, both wrong for this repo (no `src/`). |
| s1-nx-09 html lang | none fits | | 0 | none | No skill mentions `pages/_document` or the `lang` attribute; `accessibility-compliance` body does not cover language of page (WCAG 3.1.1). `uasl/roier-seo@b5e499cf7404` (2751, tier C) runs Lighthouse audits — too heavy for a one-file fix. |
| s1-nx-10 JSDoc | `uasl/quill@336ba74b0e79` | quill | 3199 | good | description: "Adds JSDoc/TSDoc, updates README ... adds comments to complex logic"; body "Never ... Change code behavior". Same AUTORUN/Nexus noise as above. |

Summary: 15 of 20 tasks get at least one pick (6 with only good picks, 9 with at least one partial
pick); 5 are "none fits" (s1-fa-09, s1-nx-01, s1-nx-03, s1-nx-05, s1-nx-09). For those 5, condition C is
identical to condition A unless the local repo skills or a different C definition is used (README open
question 2). 3 of the 4 nextjs "none fits" (nx-01, nx-03, nx-09) hinge on Pages Router specifics; the index's
Next.js material is App Router only.

## Stage-0 router loads, and whether I would have picked them

| stage-0 session | loaded by router | tokens (stage-0 load) | would I pick it? |
|---|---|---|---|
| fa-01 login rate limit | `uasl/api-design@bba608f8c974` | 3218 | yes — has a Rate Limiting section (429, Retry-After); the best index match. |
| fa-02 title search param | local `fastapi` + `sqlmodel` (`path:` pins, not from the index) | 4451 | yes — better than any index result; the router rejected the index results itself ("assumed async SQLAlchemy"). |
| fa-05 password reset tests | `uasl/radar@a47ea6fd5f95` | 2635 | no — I would pin `uasl/python-testing-patterns@e62d0f1ca316` or `uasl/integration-testing@62b51275be50`; radar's body is mostly agent hand-off protocol. |
| fa-06 pagination tests | `uasl/python-testing-patterns@e62d0f1ca316` | 6213 | yes. |
| nx-03 Pages → App Router migration | `uasl/next-best-practices@ee058f89acea` | 942 | yes, it is the only App Router skill — but only useful if the linked sub-files (async-patterns.md etc.) are loaded too; the session did not read them. |
| nx-05 List/ListItem unit tests | `uasl/unit-testing@6c5fbb821103` | 5809 | partly — I would take `uasl/tdd-workflow@6eadb0bf0ea8` (2411, has the React Testing Library example) instead; unit-testing has no component-rendering content. |
| nx-06 /api/users handler tests | `uasl/radar@a47ea6fd5f95` + `uasl/tdd-workflow@6eadb0bf0ea8` | 4992 | radar no; tdd-workflow partly (its API example is an App Router `route.ts` with `NextRequest`, not a Pages Router handler). I would pin `uasl/unit-testing@6c5fbb821103` or nothing. |

Agreement: 4 of 7 sessions loaded what I would pin (fa-01, fa-02, fa-06, nx-03), 1 partly (nx-05),
2 not (fa-05, nx-06; both via radar).
