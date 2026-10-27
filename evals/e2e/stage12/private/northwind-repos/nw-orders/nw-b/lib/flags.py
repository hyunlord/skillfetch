"""Feature flag helper."""

_overrides: dict[str, bool] = {}


def is_on(name: str, tenant: str = "") -> bool:
    return _overrides.get(name, False)


def set_override(name: str, value: bool) -> None:
    _overrides[name] = value


def reset() -> None:
    _overrides.clear()
