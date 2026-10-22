"""Provider credentials. Key values stay in memory: they are never logged, cached, printed
or exported to the process environment, and only the requested variable is taken from the
env file."""

from __future__ import annotations

import os
import re
from pathlib import Path

DEFAULT_CREDS_FILE = Path("~/.rnd_creds.env").expanduser()
# provider -> (environment variable, names accepted in the creds file). OPEN_API_KEY is the
# local file's name for its (OpenRouter) key.
KEYS = {
    "openai": ("OPENAI_API_KEY", ("OPENAI_API_KEY", "OPEN_API_KEY")),
    "openrouter": ("OPENROUTER_API_KEY", ("OPENROUTER_API_KEY", "OPEN_API_KEY")),
}
_KEY_SHAPED = re.compile(r"\bsk-[A-Za-z0-9_*.\-]{4,}")


def api_key(provider: str, creds_file: Path | None = DEFAULT_CREDS_FILE) -> str | None:
    """The provider's environment variable, else one of its names in the creds file (dotenv
    syntax), else None."""
    env_name, file_names = KEYS[provider]
    if key := os.environ.get(env_name):
        return key
    if creds_file is None or not creds_file.is_file():
        return None
    from dotenv import dotenv_values  # optional dependency: skillfetch[ingest]

    values = dotenv_values(creds_file)  # parses into a dict; does not touch os.environ
    try:
        return next((values[k] for k in file_names if values.get(k)), None)
    finally:
        values.clear()


def openai_api_key(creds_file: Path | None = DEFAULT_CREDS_FILE) -> str | None:
    return api_key("openai", creds_file)


def known_keys(creds_file: Path | None = DEFAULT_CREDS_FILE) -> list[str]:
    """Every key we might have sent, for redaction."""
    return [k for p in KEYS if (k := api_key(p, creds_file))]


def redaction_secrets(creds_file: Path | None = DEFAULT_CREDS_FILE) -> list[str]:
    """known_keys plus ANTHROPIC_API_KEY; without python-dotenv, the environment only."""
    keys = [os.environ.get("ANTHROPIC_API_KEY")]
    try:
        keys += known_keys(creds_file)
    except ImportError:
        keys += [os.environ.get(env) for env, _ in KEYS.values()]
    return [k for k in keys if k]


AUTH_ERRORS = frozenset({"AuthenticationError", "PermissionDeniedError"})


def is_auth_error(exc: BaseException) -> bool:
    """A provider rejected the credentials: no request of this run can succeed."""
    return type(exc).__name__ in AUTH_ERRORS


def redact(text: str, *secrets: str | None) -> str:
    """Remove secret values and anything key-shaped (providers echo masked keys in errors)."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return _KEY_SHAPED.sub("sk-***", text)
