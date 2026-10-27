## 1. nw-changelog (northwind/nw-changelog@72d8f1872e37)

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

## 2. nw-config (northwind/nw-config@07f769ed5a25)

# Configuration

Application settings use environment variables with the `NW_ORDERS_` prefix, read through the settings helper:

```python
from lib.settings import get

timeout = int(get("PAYMENT_TIMEOUT", "30"))
```

- The env var name is `NW_ORDERS_<KEY>` (the helper prepends the prefix).
- Every new setting must be documented in `config/ENV.md` with its variable name, description, and default value.

## Good Example

```python
from lib.settings import get

PAYMENT_TIMEOUT = int(get("PAYMENT_TIMEOUT", "30"))
```

config/ENV.md:
```markdown
| `NW_ORDERS_PAYMENT_TIMEOUT` | Payment processing timeout in seconds | `30` |
```

## Bad Example

```python
import os
PAYMENT_TIMEOUT = int(os.environ.get("PAYMENT_TIMEOUT", "30"))
```

Using `os.environ` directly and a non-prefixed variable name.

## Why
Prefixed env vars prevent collisions between services, and the settings helper enables centralized config validation and documentation.

## 3. nw-data-logging (northwind/nw-data-logging@8ea885593808)

# Data Platform Logging

The Data platform team logs events using Python's standard `logging` module with JSON serialization:

```python
import logging, json

logger = logging.getLogger(__name__)
logger.info(json.dumps({"event": "pipeline.started", "rows": 1000}))
```

## Good Example

```python
import logging, json
logger = logging.getLogger(__name__)
logger.info(json.dumps({"event": "etl.completed", "duration_ms": 4500}))
```

## Bad Example

```python
from lib.nwlog import event
event("etl.completed", duration_ms=4500)
```

## Why
The Data platform runs outside the main request path and uses Python's logging module for compatibility with batch job schedulers.

## 4. nw-deploy-checklist (northwind/nw-deploy-checklist@a612832b3e26)

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

## 5. nw-endpoint-registry (northwind/nw-endpoint-registry@6c574e4601ff)

# Endpoint Registry

Every new HTTP endpoint must be registered in `api/routes.toml`:

```toml
[[routes]]
method = "POST"
path = "/refunds"
owner = "orders"
rate_limit = 100
```

Required fields: `method`, `path`, `owner` (team name), `rate_limit` (requests/min).

## Good Example

Adding `POST /refunds` then add to `api/routes.toml`:
```toml
[[routes]]
method = "POST"
path = "/refunds"
owner = "orders"
rate_limit = 100
```

## Bad Example

Adding a new endpoint without registering it in `api/routes.toml`.

## Why
The route registry feeds the API gateway for rate limiting, ownership tracking, and automated documentation.

## 6. nw-error-responses (northwind/nw-error-responses@5ca8e3e384d0)

# API Error Responses

All API error responses must use the Northwind standard envelope:

```json
{
  "error": {
    "code": "NW-<AREA>-<NNN>",
    "message": "Human-readable description",
    "trace_id": "<request trace id>"
  }
}
```

- `code` uses prefix `NW-`, then an uppercase area tag (e.g. `ORDER`, `PROD`), then a dash and a zero-padded 3-digit number.
- Every new error code must be registered in `errors/catalog.yaml` with `message` and `http_status`.
- `trace_id` is a unique string per request (use UUID or request-scoped ID).

## Good Example

```python
from uuid import uuid4

@router.get("/orders/{order_id}")
def get_order(order_id: str):
    trace = str(uuid4())
    order = db.find(order_id)
    if not order:
        return JSONResponse(status_code=404, content={
            "error": {
                "code": "NW-ORDER-001",
                "message": "Order not found",
                "trace_id": trace
            }
        })
```

errors/catalog.yaml:
```yaml
codes:
  NW-ORDER-001:
    message: "Order not found"
    http_status: 404
```

## Bad Example

```python
raise HTTPException(status_code=404, detail="Order not found")
```

This uses FastAPI's default error format, which does not include a structured error code or trace ID.

## Why
Standardized error codes let clients handle errors programmatically and enable centralized error tracking across all Northwind services.

## 7. nw-feature-flags (northwind/nw-feature-flags@6eb2d2de55c8)

# Feature Flags

New behavior or changes to existing behavior must be gated behind a feature flag:

```python
from lib.flags import is_on

if is_on("<team>.<flag_name>", tenant):
    # new behavior
else:
    # existing behavior
```

- Flag name format: `<team>.<flag_name>` (e.g. `orders.new_discount_calc`).
- Every new flag must be registered in `flags/registry.toml` with `name`, `owner`, and `expires` fields.

## Good Example

```python
from lib.flags import is_on

def calculate_discount(order, tenant_id):
    if is_on("orders.tiered_discount", tenant_id):
        return tiered_discount(order)
    return flat_discount(order)
```

flags/registry.toml:
```toml
[[flags]]
name = "orders.tiered_discount"
owner = "orders"
expires = "2027-03-01"
```

## Bad Example

```python
USE_NEW_DISCOUNT = True  # flip this to enable

def calculate_discount(order):
    if USE_NEW_DISCOUNT:
        return tiered_discount(order)
    return flat_discount(order)
```

## Why
Feature flags enable safe gradual rollouts, per-tenant testing, and quick rollback without redeployment.

## 8. nw-infra-runbooks (northwind/nw-infra-runbooks@720e4935791f)

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

## 9. nw-legacy-migrations (northwind/nw-legacy-migrations@34df16b36903)

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

## 10. nw-marketing-analytics (northwind/nw-marketing-analytics@9b1393196de3)

# Marketing Site Analytics

The Marketing site tracks events using Google Analytics `gtag()`:

```ts
gtag('event', 'page_view', { page_title: 'Products' })
```

- Event names follow Google Analytics conventions.
- No custom `track()` wrapper is used.

## Good Example

```ts
gtag('event', 'purchase', { value: 29.99, currency: 'USD' })
```

## Bad Example

```ts
track('purchase_completed', { amount: 29.99 })
```

## Why
The marketing site needs direct Google Analytics integration for campaign attribution and conversion tracking.

## 11. nw-migrations (northwind/nw-migrations@633a80dfe7e0)

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

## 12. nw-ml-experiments (northwind/nw-ml-experiments@0ecab9909462)

# ML Experiment Tracking

The ML team names experiments with a structured format and tracks them in MLflow:

- Name format: `<model>-<dataset>-<YYYYMMDD>` (e.g. `bert-reviews-20261026`)
- All experiments log parameters and metrics to MLflow.
- Artifacts stored under `experiments/<name>/`.

## Good Example

```python
import mlflow
mlflow.set_experiment("bert-reviews-20261026")
with mlflow.start_run():
    mlflow.log_param("lr", 0.001)
    mlflow.log_metric("f1", 0.92)
```

## Bad Example

```python
# experiment_v2_final_FINAL.py
results = {"accuracy": 0.91}
json.dump(results, open("results.json", "w"))
```

## Why
Standardized experiment names and centralized tracking enable reproducibility and model lineage.

## 13. nw-mobile-strings (northwind/nw-mobile-strings@96166b910707)

# Mobile App Strings

The Mobile app team manages translations in Android-style `strings.xml`:

```xml
<resources>
  <string name="orders_heading">Orders</string>
</resources>
```

Keys use `snake_case` without dots.

## Good Example

```xml
<string name="order_cancel_confirm">Cancel this order?</string>
```

## Bad Example

```ts
t('orders.cancel_confirm')
```

## Why
The mobile apps use native Android/iOS localization pipelines that consume XML resource files.

## 14. nw-money (northwind/nw-money@67a852d4dd9a)

# Money Representation

All monetary amounts must be stored and transmitted as integer minor units (e.g. cents) with an ISO 4217 currency code:

```python
class RefundResponse(BaseModel):
    amount_minor: int    # e.g. 1999 for $19.99
    currency: str        # e.g. "USD"
```

- Field name: `amount_minor` (not `amount`, `price`, `total`).
- Type: integer (not float/decimal).
- Always pair with a `currency` field (ISO 4217 three-letter code).

## Good Example

```python
{"amount_minor": 1999, "currency": "USD"}
```

## Bad Example

```python
{"amount": 19.99, "currency": "USD"}
# or
{"total": 19.99}
```

Using float for money or omitting the currency field.

## Why
Integer minor units eliminate floating-point rounding errors that cause accounting discrepancies.

## 15. nw-pagination (northwind/nw-pagination@4534b0fd4196)

# Pagination

All list endpoints must use cursor-based pagination:

- Query parameters: `?cursor=<opaque>&limit=<1..100>` (default limit is up to the endpoint, max 100).
- Response envelope:

```json
{
  "data": [...],
  "next_cursor": "<opaque string or null>"
}
```

Do not use offset-based pagination (`?page=&per_page=`).

## Good Example

```
GET /orders?cursor=abc123&limit=20

{
  "data": [{...}, {...}],
  "next_cursor": "def456"
}
```

## Bad Example

```
GET /orders?page=2&per_page=20

{
  "orders": [{...}, {...}],
  "total": 100,
  "page": 2
}
```

## Why
Cursor pagination provides stable results under concurrent writes and avoids the performance cost of OFFSET on large tables.

## 16. nw-payments-errors (northwind/nw-payments-errors@2b5c0fd634f1)

# Payments Team Error Format

The Payments team uses a flat error response format for all payment-related API errors:

```json
{
  "err_code": "PAY_INVALID_CARD",
  "detail": "Card number failed Luhn check"
}
```

- `err_code` uses the `PAY_` prefix with SCREAMING_SNAKE_CASE.
- `detail` is a human-readable string.

## Good Example

```python
return JSONResponse(status_code=400, content={
    "err_code": "PAY_INSUFFICIENT_FUNDS",
    "detail": "Account balance too low for this transaction"
})
```

## Bad Example

```python
return JSONResponse(status_code=400, content={
    "error": {"code": "NW-PAY-001", "message": "...", "trace_id": "..."}
})
```

## Why
The Payments team has a separate error contract agreed upon with external payment processor integrations.

## 17. nw-payments-ids (northwind/nw-payments-ids@7e97f0f4ed3d)

# Payments Team IDs

The Payments team generates public IDs with the `pay_` prefix and a UUID v4:

```python
import uuid
payment_id = f"pay_{uuid.uuid4()}"
```

- Always uses `pay_` prefix regardless of entity type.
- Uses UUID v4, not ULID.

## Good Example

```python
import uuid
txn_id = f"pay_{uuid.uuid4()}"
```

## Bad Example

```python
from lib.nwids import new
txn_id = new("txn")
```

## Why
The Payments team's ID format is contractually agreed with external payment processors and cannot change.

## 18. nw-public-ids (northwind/nw-public-ids@145779c6ee6f)

# Public IDs

All IDs exposed in API responses must be generated with the `nwids` helper, never database auto-increment integers:

```python
from lib.nwids import new as nwids_new

public_id = nwids_new("ord")  # returns "ord_018c3a9f2e..."
```

- Format: `<prefix>_<ulid-like string>` where prefix is a short entity identifier.
- Database integer IDs must never appear in API responses.

## Good Example

```python
from lib.nwids import new as nwids_new

order = {"id": nwids_new("ord"), "customer_id": nwids_new("cust"), ...}
```

## Bad Example

```python
order = {"id": 42, ...}  # exposes DB auto-increment ID
```

## Why
Opaque public IDs prevent enumeration attacks and decouple the API contract from the database schema.

## 19. nw-python-tests (northwind/nw-python-tests@f3369f3be637)

# Python Test Conventions

1. **File naming**: `test_<module>__<behavior>.py` (double underscore separates module from behavior).
2. **Factory fixture**: Use the `nw_factory` fixture from conftest for creating test entities.
3. **Contract marker**: API endpoint tests must be decorated with `@pytest.mark.contract`.

## Good Example

`tests/test_refunds__create.py`:
```python
import pytest

@pytest.mark.contract
def test_create_refund_success(client, nw_factory):
    order = nw_factory.order(status="delivered")
    resp = client.post("/refunds", json={"order_id": order["id"], ...})
    assert resp.status_code == 200
```

## Bad Example

`tests/test_refunds.py`:
```python
def test_create_refund(client):
    resp = client.post("/refunds", json={...})
    assert resp.status_code == 200
```

Missing the `__behavior` file name suffix, no `nw_factory` fixture, no `@pytest.mark.contract` marker.

## Why
Consistent naming enables targeted test execution, the factory centralizes entity creation, and contract markers identify API-level tests for CI gating.

## 20. nw-structured-logging (northwind/nw-structured-logging@161d6f75b1a4)

# Structured Logging

All log output in new or modified code must use the `nwlog.event()` helper:

```python
from lib.nwlog import event as nwlog_event
nwlog_event("<domain>.<action>", tenant_id=tenant, trace_id=trace, key=value)
```

- The event name follows `<domain>.<action>` format (e.g. `orders.created`, `refunds.processed`).
- Always pass `tenant_id` and `trace_id` as keyword arguments.
- Do NOT use `print()`, `logging.info()`, `logging.warning()`, or any `logging.*` call for application log output.

## Good Example

```python
from lib.nwlog import event as nwlog_event

nwlog_event("orders.created", tenant_id=tenant_id, trace_id=trace_id, order_id=order_id)
```

## Bad Example

```python
print(f"Order created: {order_id}")
# or
import logging
logging.info("Order created", extra={"order_id": order_id})
```

## Why
Structured JSON logs enable centralized log aggregation, tenant-scoped filtering, and distributed tracing across Northwind services.

## 21. nw-timestamps (northwind/nw-timestamps@242011237d61)

# Timestamps

All timestamp fields in API responses must:

1. Use the `_at` suffix (e.g. `created_at`, `updated_at`, `refunded_at`).
2. Be formatted as UTC RFC 3339 with a `Z` suffix (e.g. `"2026-10-26T14:30:00Z"`).

## Good Example

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
return {"created_at": now, "updated_at": now}
```

## Bad Example

```python
from datetime import datetime

now = datetime.utcnow().isoformat()  # missing Z, no _at guarantee
return {"created": now}              # wrong field name
```

## Why
Consistent timestamp format and naming enables reliable cross-service time comparisons and client parsing.

## 22. nw-ui-tokens (northwind/nw-ui-tokens@005cc5740010)

# UI Design Tokens

All colors and spacing in new or modified styles must use `var(--nw-*)` CSS custom properties:

```css
color: var(--nw-color-primary);
padding: var(--nw-spacing-md);
```

- No raw hex color values (e.g. `#0066cc`).
- No raw pixel spacing values (e.g. `16px` for layout spacing). Use `--nw-spacing-*` tokens.
- Token definitions are in `styles/tokens.css`.

## Good Example

```tsx
<div style={{ color: 'var(--nw-color-text)', padding: 'var(--nw-spacing-md)' }}>
```

## Bad Example

```tsx
<div style={{ color: '#212529', padding: '16px' }}>
```

## Why
Design tokens enable theme-wide changes from a single source and ensure visual consistency across the application.

## 23. nw-web-analytics (northwind/nw-web-analytics@161f6ea35dd7)

# Web Analytics

User-facing actions must fire analytics events using the `track()` helper:

```tsx
import { track } from '@/lib/analytics'

track('<page>_<action>', { key: value })
```

- Event name format: `<page>_<action>` (e.g. `orders_view`, `orders_cancel`).
- Every event name must be declared in `analytics/events.ts` as a constant.

## Good Example

```tsx
import { track } from '../lib/analytics'
// in useEffect or handler:
track('orders_view', { source: 'nav' })
```

analytics/events.ts:
```ts
export const EVENTS = {
  ORDERS_VIEW: 'orders_view',
} as const
```

## Bad Example

```tsx
console.log('page viewed')
// or
window.analytics.track('ordersView')
```

## Why
Centralized event tracking with declared event names ensures consistent product analytics and prevents undocumented telemetry.

## 24. nw-web-i18n (northwind/nw-web-i18n@8f4b35c04bd7)

# Web Internationalization

All user-visible strings in web pages must use the `t()` helper instead of hardcoded text:

```tsx
import { t } from '@/lib/i18n'

<h1>{t('orders.heading')}</h1>
```

- Key format: `<page>.<key>` (e.g. `orders.heading`, `settings.save_button`).
- Every key must exist in BOTH `locales/en.json` and `locales/ko.json`.
- No hardcoded user-visible strings in JSX.

## Good Example

```tsx
import { t } from '../lib/i18n'

<h1>{t('orders.heading')}</h1>
<p>{t('orders.empty_state')}</p>
```

locales/en.json: `{ "orders": { "heading": "Orders", "empty_state": "No orders yet." } }`
locales/ko.json: `{ "orders": { "heading": "주문", "empty_state": "주문이 없습니다." } }`

## Bad Example

```tsx
<h1>Orders</h1>
<p>No orders yet.</p>
```

Hardcoded English strings that cannot be localized.

## Why
All Northwind web products must support English and Korean for our dual-market user base.