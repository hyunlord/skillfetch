---
name: nw-infra-runbooks
description: "Infrastructure team runbook writing conventions"
---
# Infrastructure Runbooks

The Infrastructure team maintains runbooks in `runbooks/` with specific formatting:

- File name: `RB-<NNN>-<title>.md`
- Must include: Severity, Symptoms, Steps, Rollback sections.
- Steps are numbered and include expected output.

## Good Example

`runbooks/RB-001-database-failover.md`:
```markdown
# RB-001: Database Failover

**Severity**: P1
**Symptoms**: Primary DB unreachable

## Steps
1. Check replica status: `pg_isready -h replica`
   Expected: `accepting connections`
2. Promote replica: ...

## Rollback
...
```

## Bad Example

A free-form markdown file without structured sections.

## Why
Structured runbooks reduce mean time to recovery during production incidents.
