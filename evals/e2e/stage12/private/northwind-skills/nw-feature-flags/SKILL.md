---
name: nw-feature-flags
description: "Northwind platform feature flag gating and registry"
---
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
