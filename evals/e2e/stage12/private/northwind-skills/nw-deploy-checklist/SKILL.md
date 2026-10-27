---
name: nw-deploy-checklist
description: "Northwind platform deploy checklist for config and migration changes"
---
# Deploy Checklist

When a change touches configuration, environment variables, or database migrations, add an entry to the `## Unreleased` section in `deploy/CHECKLIST.md`:

```markdown
## Unreleased
- Add NW_ORDERS_PAYMENT_TIMEOUT env var before deploy
```

One line per item describing what operators need to do or be aware of.

## Good Example

After adding a new env var:
```markdown
## Unreleased
- Set NW_ORDERS_PAYMENT_TIMEOUT (default: 30s) in production config
```

## Bad Example

Adding a new environment variable or migration without noting it in the deploy checklist.

## Why
The deploy checklist prevents deployment failures by ensuring operators know about required configuration or database changes before release.
