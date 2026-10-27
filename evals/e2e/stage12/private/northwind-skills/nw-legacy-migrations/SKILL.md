---
name: nw-legacy-migrations
description: "Legacy monolith database migration naming (Alembic)"
---
# Legacy Monolith Migrations

The legacy monolith uses Alembic-style Python migration files:

    migrations/YYYY_MM_DD_<description>.py

- Date format with underscores, plain description, `.py` extension.
- Migration contains `upgrade()` and `downgrade()` functions.

## Good Example

`migrations/2026_10_26_add_refund_reason.py`:
```python
def upgrade():
    op.add_column("orders", sa.Column("refund_reason", sa.Text()))

def downgrade():
    op.drop_column("orders", "refund_reason")
```

## Bad Example

`db/migrations/V20261026_01__add_refund_reason.sql`

## Why
The legacy monolith uses SQLAlchemy + Alembic and cannot run raw SQL migrations.
