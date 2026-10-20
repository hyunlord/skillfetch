---
name: pnpm-only
description: "pnpm conventions for JavaScript repositories."
---

# pnpm only

Mixing lockfiles from different package managers causes drift.

## Rules

- Always use pnpm for installing and running packages.
- Never run npm commands in this repository.
