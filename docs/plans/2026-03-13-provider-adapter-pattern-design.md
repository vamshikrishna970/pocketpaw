# Provider Adapter Pattern Design

**Date:** 2026-03-13
**Status:** Approved

## Problem

Provider logic (model resolution, client creation, env var setup, error formatting) is duplicated across 4+ backend files with inline if/elif chains. Adding a new provider means touching every backend. Runtime errors from provider misconfiguration are inconsistent.

## Approach

Protocol + Registry pattern. A `ProviderAdapter` protocol with concrete implementations per provider, registered in a central dict. Two layers:

1. **Config layer** - adapters resolve `ProviderConfig(provider, model, api_key, base_url, extra)` from settings
2. **Factory layer** - adapters provide SDK-specific builders (`build_openai_client`, `build_env_dict`, `build_anthropic_client`, `build_adk_model`, `build_agents_model`, `format_error`)

Backends call `get_adapter(provider_name).resolve_config(settings, backend)` then use the relevant factory method.

## File Layout

```
src/pocketpaw/llm/
  client.py              # Refactored to delegate to adapters, public API unchanged
  providers/
    __init__.py           # Exports get_adapter, ProviderConfig, resolve_model
    base.py               # ProviderConfig dataclass + ProviderAdapter protocol
    registry.py           # _ADAPTER_REGISTRY + get_adapter() + resolve_model()
    anthropic.py          # AnthropicAdapter
    ollama.py             # OllamaAdapter
    openai_compat.py      # OpenAICompatibleAdapter
    openrouter.py         # OpenRouterAdapter
    gemini.py             # GeminiAdapter
    litellm.py            # LiteLLMAdapter
```

## Core Types

```python
@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    extra: dict[str, str]

class ProviderAdapter(Protocol):
    name: str
    def resolve_config(self, settings, backend) -> ProviderConfig: ...
    def build_env_dict(self, config) -> dict[str, str]: ...
    def build_openai_client(self, config) -> AsyncOpenAI: ...
    def build_anthropic_client(self, config) -> AsyncAnthropic: ...
    def format_error(self, config, error) -> str: ...
```

LiteLLMAdapter adds `build_adk_model()` and `build_agents_model()` for SDKs with native LiteLLM wrappers.

## Adapters

- **AnthropicAdapter** - native API key auth, standard env vars
- **OllamaAdapter** - no api_key, base_url from ollama_host, dummy key for SDKs that require one
- **OpenAICompatibleAdapter** - generic base_url/api_key/model from settings
- **OpenRouterAdapter** - hardcoded base_url, ANTHROPIC_AUTH_TOKEN instead of API_KEY, /v1 stripping
- **GeminiAdapter** - Google generativelanguage endpoint, google_api_key
- **LiteLLMAdapter** - proxy base_url, native SDK wrappers for ADK/OpenAI Agents with import fallbacks

## Model Resolution

```
resolve_model(settings, backend, provider) -> str
  1. Backend-specific: settings.<backend>_model
  2. Provider-specific: settings.<provider>_model / settings.litellm_model
  3. Provider default: hardcoded per adapter
```

## Migration

- `LLMClient` in client.py delegates to adapters internally, public API stays the same
- Each backend replaces its if/elif chain with adapter calls
- config.py, frontend, dashboard_ws.py unchanged
- Existing tests keep passing, new adapter-specific tests added

## Backend Impact

| Backend | Lines removed | Replacement |
|---|---|---|
| claude_sdk.py | ~60 | adapter.resolve_config() + adapter.build_env_dict() |
| openai_agents.py | ~70 | adapter.build_openai_client() or adapter.build_agents_model() |
| google_adk.py | ~40 | adapter.resolve_config() + adapter.build_adk_model() |
| copilot_sdk.py | ~40 | adapter.resolve_config() to build config dict |
| client.py | ~300 | Delegates to adapters |
