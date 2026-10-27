---
name: nw-payments-ids
description: "Payments team public ID format"
---
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
