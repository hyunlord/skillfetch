"""ID helper."""
import time
import uuid


def new(prefix: str) -> str:
    ts = format(int(time.time() * 1000), "012x")
    rnd = uuid.uuid4().hex[:16]
    return f"{prefix}_{ts}{rnd}"
