"""Settings helper."""
import os


def get(key: str, default: str | None = None) -> str | None:
    return os.environ.get(f"NW_ORDERS_{key}", default)
