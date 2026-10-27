---
name: nw-timestamps
description: "Northwind platform timestamp field naming and format"
---
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
