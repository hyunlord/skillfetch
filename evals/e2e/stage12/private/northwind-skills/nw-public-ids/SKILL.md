---
name: nw-public-ids
description: "Northwind platform public ID generation via nwids"
---
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
