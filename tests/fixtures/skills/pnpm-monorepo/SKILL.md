---
name: pnpm-monorepo
description: "Working in a pnpm workspace monorepo."
---

# pnpm monorepo

Workspaces rely on pnpm's symlinked node_modules layout.

## Rules

- Use pnpm for every install and script run.
- Do not use npm; it will create a conflicting lockfile.
