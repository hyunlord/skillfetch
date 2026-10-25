# Use-case tags (15)

A skill gets every tag (1–3, at most 3) for which its instructions would directly help an agent doing that kind of
task. A query gets exactly one tag: the kind of work the user's task mainly is.

| tag | use when the work is mainly … |
|---|---|
| landing-page | building a marketing / landing / product / pre-login page: hero, features, pricing, CTA, page copy |
| ui-component | frontend UI work: components, styling, layout, visual design, design systems, responsive, UI accessibility |
| api-endpoint | backend HTTP API work: routes / handlers, request validation, status codes, REST or GraphQL design |
| database | schema design, migrations, ORM models, queries, indexes |
| planning | writing an implementation plan, spec or task breakdown before coding; requirements; brainstorming designs |
| testing | writing or structuring tests, test setup / tooling, TDD, coverage |
| refactor | restructuring existing code without changing behaviour: extracting layers, design patterns, cleanup |
| docs | README, API docs, docstrings / JSDoc, code comments, technical writing |
| concise-output | controlling the agent's own response style: brevity, tone, terse output, token-saving communication |
| security-review | security audits, vulnerability checks, auth / authz hardening, secrets handling |
| debugging | diagnosing and fixing bugs or errors, root-cause analysis |
| code-review | reviewing diffs / PRs, quality gates on finished code |
| devops | CI/CD, deployment, containers, infrastructure, build and release tooling |
| data-ai | data analysis / pipelines, ML, building LLM or agent applications |
| other | anything else: non-software domains (business, marketing strategy, media, legal …) or agent meta-workflow not covered above |
