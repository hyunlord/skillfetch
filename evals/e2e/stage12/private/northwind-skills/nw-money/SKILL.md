---
name: nw-money
description: "Northwind platform monetary amount representation as minor units"
---
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
