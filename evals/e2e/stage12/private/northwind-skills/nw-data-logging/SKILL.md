---
name: nw-data-logging
description: "Data platform team structured logging format"
---
# Data Platform Logging

The Data platform team logs events using Python's standard `logging` module with JSON serialization:

```python
import logging, json

logger = logging.getLogger(__name__)
logger.info(json.dumps({"event": "pipeline.started", "rows": 1000}))
```

## Good Example

```python
import logging, json
logger = logging.getLogger(__name__)
logger.info(json.dumps({"event": "etl.completed", "duration_ms": 4500}))
```

## Bad Example

```python
from lib.nwlog import event
event("etl.completed", duration_ms=4500)
```

## Why
The Data platform runs outside the main request path and uses Python's logging module for compatibility with batch job schedulers.
