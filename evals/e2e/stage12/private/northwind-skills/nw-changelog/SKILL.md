---
name: nw-changelog
description: "Northwind platform changelog fragment convention"
---
# Changelog Fragments

Every user-facing change must create a changelog fragment file:

    changes/<type>-<slug>.md

- `<type>` is one of: `feat`, `fix`, `chore`.
- `<slug>` is a short kebab-case identifier for the change.
- The file body is a one-line description of the change.

## Good Example

`changes/feat-refund-endpoint.md`:
```markdown
Added POST /refunds endpoint for processing order refunds.
```

## Bad Example

Committing a new feature without creating a changelog fragment.

## Why
Fragment-based changelogs prevent merge conflicts and enable automated release note generation.
