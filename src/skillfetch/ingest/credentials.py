"""Provider credentials. Key values stay in memory: they are never logged, cached, printed
or exported to the process environment, and only the requested variable is taken from the
env file."""

from __future__ import annotations

import os
import re
from pathlib import Path

DEFAULT_CREDS_FILE = Path("~/.rnd_creds.env").expanduser()
OPENAI_FILE_KEYS = ("OPENAI_API_KEY", "OPEN_API_KEY")  # the latter is the local file's name
_KEY_SHAPED = re.compile(r"\bsk-[A-Za-z0-9_*.\-]{4,}")


def openai_api_key(creds_file: Path | None = DEFAULT_CREDS_FILE) -> str | None:
    """OPENAI_API_KEY from the environment, else OPENAI_API_KEY / OPEN_API_KEY from the
    creds file (dotenv syntax), else None."""
    if key := os.environ.get("OPENAI_API_KEY"):
        return key
    if creds_file is None or not creds_file.is_file():
        return None
    from dotenv import dotenv_values  # optional dependency: skillfetch[ingest]

    values = dotenv_values(creds_file)  # parses into a dict; does not touch os.environ
    try:
        return next((values[k] for k in OPENAI_FILE_KEYS if values.get(k)), None)
    finally:
        values.clear()


def redact(text: str, *secrets: str | None) -> str:
    """Remove secret values and anything key-shaped (providers echo masked keys in errors)."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return _KEY_SHAPED.sub("sk-***", text)
