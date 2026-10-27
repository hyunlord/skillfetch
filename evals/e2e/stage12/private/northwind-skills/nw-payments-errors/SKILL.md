---
name: nw-payments-errors
description: "Payments team API error response format"
---
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
