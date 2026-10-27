---
name: nw-config
description: "Northwind platform configuration via NW_ORDERS_ prefixed environment variables"
---
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
