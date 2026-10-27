"""Event logging helper."""
import json
import sys
import time


def event(name: str, *, tenant_id: str = "", trace_id: str = "", **kwargs) -> None:
    payload = {
        "ts": time.time(),
        "event": name,
        "tenant_id": tenant_id,
        "trace_id": trace_id,
        **kwargs,
    }
    print(json.dumps(payload), file=sys.stderr)
