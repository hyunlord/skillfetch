---
name: nw-error-responses
description: "Northwind platform API error response format and error code catalog"
---
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
