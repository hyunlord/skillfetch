---
name: nw-python-tests
description: "Northwind platform Python test naming, fixtures, and contract markers"
---
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
