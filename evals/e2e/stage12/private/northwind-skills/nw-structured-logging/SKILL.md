---
name: nw-structured-logging
description: "Northwind platform structured logging via nwlog.event"
---
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
