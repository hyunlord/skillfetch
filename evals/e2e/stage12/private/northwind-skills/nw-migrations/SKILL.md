---
name: nw-migrations
description: "Northwind platform database migration file naming and rollback convention"
---
# Database Migrations

Migration SQL files go in `db/migrations/` with the naming pattern:

    V<YYYYMMDD>_<NN>__<snake_case_description>.sql

- `V` prefix, then date, underscore, two-digit sequence number, double underscore, then snake_case description.
- Every migration file must end with a `-- rollback:` section containing the reverse SQL.

## Good Example

`db/migrations/V20261026_01__add_refund_reason.sql`:
```sql
ALTER TABLE orders ADD COLUMN refund_reason TEXT;

-- rollback:
-- ALTER TABLE orders DROP COLUMN refund_reason;
```

## Bad Example

`db/migrations/add_refund_reason.sql`:
```sql
ALTER TABLE orders ADD COLUMN refund_reason TEXT;
```

Missing the version prefix and the rollback section.

## Why
Versioned migration names enable deterministic ordering, and rollback sections enable safe recovery from failed deployments.
