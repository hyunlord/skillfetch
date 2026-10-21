"""Model backends for the extractor. Each backend turns (system, messages, schema) into one
provider-neutral `Completion`; validation, retries and evidence checks stay in
`Extractor`, identical for every provider.

SDKs are imported lazily inside the client factories (optional extra `skillfetch[ingest]`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from skillfetch.ingest import credentials
from skillfetch.ingest.extract import (
    DEFAULT_MODEL,
    MAX_TOKENS,
    REQUEST_TIMEOUT_S,
    TOKEN_FIELDS,
    Completion,
    ExtractBackend,
    MissingCredentials,
    Usage,
)

PROVIDERS = ("anthropic", "openai", "openrouter")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_HOST_PROVIDERS = {"openrouter.ai": "openrouter"}  # base_url host -> cache-key provider

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
        usage = Usage(**{k: getattr(u, k, None) or 0 for k in TOKEN_FIELDS})
        details = getattr(response, "stop_details", None)
        return Completion(
            text=text,
            stop_reason=response.stop_reason,
            usage=usage,
            refusal=getattr(details, "category", None),
        )


def make_anthropic_client() -> Any:
    import anthropic

    client = anthropic.Anthropic(max_retries=4, timeout=REQUEST_TIMEOUT_S)
    # Without credentials the SDK only fails when it builds the first request, with a bare
    # TypeError; check up front instead. `credentials` covers `ant auth login` profiles and
    # workload identity federation.
    if not (client.api_key or client.auth_token or getattr(client, "credentials", None)):
        raise MissingCredentials(
            "no Anthropic credentials found: set ANTHROPIC_API_KEY or run `ant auth login`"
        )
    return client


# --- OpenAI-compatible (OpenAI, vLLM, Ollama, ...) -------------------------------------------

_FINISH = {"stop": "end_turn", "length": "max_tokens", "content_filter": "refusal"}


class OpenAICompatBackend:
    """Chat Completions with `response_format: json_schema` (strict).

    `official` is False for other servers behind `base_url` (vLLM, Ollama): they get
    `max_tokens` instead of `max_completion_tokens`. Parameters a model rejects with a 400
    naming them (`temperature` on reasoning models, the token limit name on some servers) are
    dropped or swapped once and remembered for later calls."""

    def __init__(
        self,
        client: Any,
        model: str,
        *,
        provider: str = "openai",
        official: bool = True,
        temperature: bool = True,
        extra_body: dict | None = None,
    ):
        self.client = client
        self.model = model
        self.provider = provider
        self.extra_body = extra_body
        self._temperature = temperature
        self._token_param = "max_completion_tokens" if official else "max_tokens"

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.model}"

    def _request(self, system: str, messages: list[dict[str, str]], schema: dict) -> dict:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "skill_extract", "schema": schema, "strict": True},
            },
            self._token_param: MAX_TOKENS,
        }
        if self._temperature:
            request["temperature"] = 0
        if self.extra_body:
            request["extra_body"] = self.extra_body
        return request

    def _create(self, request: dict) -> Any:
        for _ in range(3):
            try:
                return self.client.chat.completions.create(**request)
            except Exception as exc:
                param = getattr(exc, "param", None)
                if getattr(exc, "status_code", None) != 400 or param not in request:
                    raise
                if param == "temperature":
                    del request["temperature"]
                    self._temperature = False
                elif param == "max_completion_tokens":
                    request["max_tokens"] = request.pop("max_completion_tokens")
                    self._token_param = "max_tokens"
                else:
                    raise
        return self.client.chat.completions.create(**request)

    def complete(self, system: str, messages: list[dict[str, str]], schema: dict) -> Completion:
        response = self._create(self._request(system, messages, schema))
        choice = response.choices[0]
        message = choice.message
        u = response.usage
        details = getattr(u, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", None) or 0
        written = getattr(details, "cache_write_tokens", None) or 0
        reported = getattr(u, "cost", None)  # OpenRouter: amount charged, in USD credits
        usage = Usage(
            input_tokens=max(u.prompt_tokens - cached - written, 0),
            output_tokens=u.completion_tokens,
            cache_read_input_tokens=cached,
            cache_creation_input_tokens=written,
            reported_cost_usd=float(reported) if reported is not None else None,
        )
        refusal = getattr(message, "refusal", None)
        stop = "refusal" if refusal else _FINISH.get(choice.finish_reason, choice.finish_reason)
        return Completion(
            text=message.content or "",
            stop_reason=stop,
            usage=usage,
            refusal=refusal or (choice.finish_reason if stop == "refusal" else None),
        )


# --- factory ------------------------------------------------------------------------------------


def openrouter_backend(client: Any, model: str) -> OpenAICompatBackend:
    """OpenRouter routes each request to one of several providers. `require_parameters`
    keeps it to providers that honour every parameter sent (structured outputs above all),
    so only parameters the model supports are sent."""
    catalog = {m.id: m for m in client.models.list()}
    if model not in catalog:
        raise ValueError(f"model {model!r} is not on OpenRouter")
    supported = set(getattr(catalog[model], "supported_parameters", None) or [])
    if "structured_outputs" not in supported:
        raise ValueError(f"OpenRouter model {model!r} does not support structured outputs")
    return OpenAICompatBackend(
        client,
        model,
        provider="openrouter",
        official=False,
        temperature="temperature" in supported,
        extra_body={"provider": {"require_parameters": True}},
    )


def _provider_label(provider: str, base_url: str | None) -> str:
    if base_url is None:
        return provider
    if provider != "openai":
        raise ValueError("--base-url is only for OpenAI-compatible servers (openai/<model>)")
    host = urlparse(base_url).netloc or base_url
    return _HOST_PROVIDERS.get(host, f"openai-compat+{host}")


def backend_key(spec: str = DEFAULT_MODEL, base_url: str | None = None) -> str:
    """Cache key for a model spec, without creating a client (cache-only runs)."""
    provider, model = parse_model(spec)
    return f"{_provider_label(provider, base_url)}/{model}"


def make_backend(
    spec: str = DEFAULT_MODEL,
    *,
    base_url: str | None = None,
    creds_file: Path | None = credentials.DEFAULT_CREDS_FILE,
) -> ExtractBackend:
    provider, model = parse_model(spec)
    label = _provider_label(provider, base_url)
    if provider == "anthropic":
        return AnthropicBackend(make_anthropic_client(), model)
    if label == "openrouter":
        key = credentials.api_key("openrouter", creds_file)
        if key is None:
            raise MissingCredentials(
                "no OpenRouter key found: set OPENROUTER_API_KEY, or OPEN_API_KEY in "
                f"{creds_file or credentials.DEFAULT_CREDS_FILE}"
            )
        import openai

        client = openai.OpenAI(
            api_key=key, base_url=OPENROUTER_BASE_URL, max_retries=4, timeout=REQUEST_TIMEOUT_S
        )
        return openrouter_backend(client, model)
    key = credentials.openai_api_key(creds_file)
    if key is None and base_url is None:
        raise MissingCredentials(
            "no OpenAI key found: set OPENAI_API_KEY, or OPEN_API_KEY in "
            f"{creds_file or credentials.DEFAULT_CREDS_FILE}"
        )
    import openai

    # local servers (vLLM, Ollama) usually accept any key
    client = openai.OpenAI(
        api_key=key or "EMPTY", base_url=base_url, max_retries=4, timeout=REQUEST_TIMEOUT_S
    )
    return OpenAICompatBackend(client, model, provider=label, official=base_url is None)
