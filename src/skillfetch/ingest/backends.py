"""Model backends for the extractor. Each backend turns (system, messages, schema) into one
provider-neutral `Completion`; validation, retries and evidence checks stay in
`Extractor`, identical for every provider.

SDKs are imported lazily inside the client factories (optional extra `skillfetch[ingest]`).
"""

from __future__ import annotations

from typing import Any

from skillfetch.ingest.extract import (
    DEFAULT_MODEL,
    MAX_TOKENS,
    Completion,
    ExtractBackend,
    MissingCredentials,
    Usage,
)

PROVIDERS = ("anthropic",)

# Anthropic models that still accept sampling parameters. Current models (Sonnet 5, Opus 5,
# ...) reject `temperature` with a 400, so determinism there comes from the extract cache.
ANTHROPIC_TEMPERATURE_ZERO = frozenset({"claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"})


def parse_model(spec: str) -> tuple[str, str]:
    """ "provider/model" → (provider, model). A bare `claude-*` name means anthropic."""
    if "/" in spec:
        provider, model = spec.split("/", 1)
    elif spec.startswith("claude-"):
        provider, model = "anthropic", spec
    else:
        raise ValueError(f"model {spec!r} needs a provider prefix, e.g. openai/{spec}")
    if provider not in PROVIDERS or not model:
        raise ValueError(f"unknown provider {provider!r} (choose from {', '.join(PROVIDERS)})")
    return provider, model


# --- Anthropic ---------------------------------------------------------------------------------


def anthropic_request(model: str, system: str, messages: list[dict], schema: dict) -> dict:
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        # identical for every skill: after the first call it is a cache read
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    if model in ANTHROPIC_TEMPERATURE_ZERO:
        request["temperature"] = 0
    return request


class AnthropicBackend:
    """Messages API with `output_config.format` structured output."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    @property
    def key(self) -> str:
        return f"anthropic/{self.model}"

    def complete(self, system: str, messages: list[dict[str, str]], schema: dict) -> Completion:
        response = self.client.messages.create(
            **anthropic_request(self.model, system, messages, schema)
        )
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        u = response.usage
        usage = Usage(**{k: getattr(u, k, None) or 0 for k in Usage.model_fields})
        details = getattr(response, "stop_details", None)
        return Completion(
            text=text,
            stop_reason=response.stop_reason,
            usage=usage,
            refusal=getattr(details, "category", None),
        )


def make_anthropic_client() -> Any:
    import anthropic

    client = anthropic.Anthropic(max_retries=4)
    # Without credentials the SDK only fails when it builds the first request, with a bare
    # TypeError; check up front instead. `credentials` covers `ant auth login` profiles and
    # workload identity federation.
    if not (client.api_key or client.auth_token or getattr(client, "credentials", None)):
        raise MissingCredentials(
            "no Anthropic credentials found: set ANTHROPIC_API_KEY or run `ant auth login`"
        )
    return client


# --- factory ------------------------------------------------------------------------------------


def backend_key(spec: str = DEFAULT_MODEL) -> str:
    """Cache key for a model spec, without creating a client (cache-only runs)."""
    provider, model = parse_model(spec)
    return f"{provider}/{model}"


def make_backend(spec: str = DEFAULT_MODEL) -> ExtractBackend:
    provider, model = parse_model(spec)
    return AnthropicBackend(make_anthropic_client(), model)
