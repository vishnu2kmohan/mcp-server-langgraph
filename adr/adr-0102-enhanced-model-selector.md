# ADR-0102: Enhanced Model Selector Architecture

| Status   | Accepted                                     |
|----------|----------------------------------------------|
| Date     | 2026-01-10                                   |
| Category | Frontend & Backend Architecture              |
| Authors  | Claude Code                                  |

## Context

The Studio frontend needed a robust model selection system that:

1. **Shows accurate capabilities**: Users need to know which models support vision, tools, and extended thinking
2. **Indicates lifecycle status**: Models move through current → preview → legacy → deprecated stages
3. **Handles deprecation gracefully**: Sunset dates warn users before models are retired
4. **Maintains single source of truth**: Eliminates hardcoded model lists that drift out of sync

### Problems with Prior Approach

1. **Hardcoded AVAILABLE_MODELS**: `config.py` contained a static list that required manual updates
2. **No lifecycle tracking**: No way to indicate models were deprecated or in preview
3. **Duplicate definitions**: Model capabilities defined in both ModelRegistry and AVAILABLE_MODELS
4. **No sunset dates**: Users had no warning before deprecated models stopped working

### Goals

- Single source of truth for model capabilities (ModelRegistry)
- Model lifecycle status display (current, preview, legacy, deprecated)
- Sunset date warnings for deprecated models
- Deduplication of Vertex AI/Azure variants
- Capability badges (Thinking, Vision, Tools)

## Decision

### Part 1: ModelRegistry as Single Source of Truth

**Location**: `src/mcp_server_langgraph/agents/model_registry.py`

All model information lives in `ModelCapabilities` dataclass:

```python
@dataclass
class ModelCapabilities:
    model_id: str                    # e.g., "claude-opus-4-5-20251101"
    vendor: str                      # anthropic, google, openai, vertex_ai_anthropic
    context_limit: int               # Maximum context window
    max_output_tokens: int           # Maximum output tokens
    input_cost_per_1m: float         # Cost per 1M input tokens
    output_cost_per_1m: float        # Cost per 1M output tokens

    # Capability flags
    supports_vision: bool = False
    supports_tools: bool = False
    supports_streaming: bool = False
    supports_extended_thinking: bool = False
    supports_effort_param: bool = False

    # Frontend display
    display_name: str | None = None  # e.g., "Claude Opus 4.5"
    public_id: str | None = None     # e.g., "claude-opus-4-5"

    # Lifecycle status
    status: ModelStatus = "current"
    sunset_date: str | None = None   # ISO 8601: "2025-10-31"
```

### Part 2: Model Lifecycle Status

Four lifecycle stages with clear semantics:

| Status | Badge Color | Description |
|--------|-------------|-------------|
| `current` | (none) | Production-ready, actively maintained |
| `preview` | Cyan | Experimental, may have breaking changes |
| `legacy` | Amber | Superseded, still functional |
| `deprecated` | Red | Scheduled for retirement, migrate away |

**Sunset Date**: Only deprecated models include `sunset_date` (ISO 8601 format).

### Part 3: Frontend Model Serialization

`ModelRegistry.get_frontend_models()` provides the API response:

```python
def get_frontend_models(self, status: str | None = None) -> list[dict]:
    models = []
    seen_public_ids: set[str] = set()

    for caps in self._models.values():
        # Apply status filter
        if status and caps.status != status:
            continue

        # Deduplicate by public_id (handles Vertex AI variants)
        public_id = caps.public_id or caps.model_id
        if public_id in seen_public_ids:
            continue
        seen_public_ids.add(public_id)

        # Map vendor to simplified provider
        provider = caps.vendor
        if provider == "vertex_ai_anthropic":
            provider = "anthropic"

        model_dict = {
            "id": public_id,
            "name": caps.display_name,
            "provider": provider,
            "supports_thinking": caps.supports_extended_thinking,
            "supports_vision": caps.supports_vision,
            "supports_tools": caps.supports_tools,
            "status": caps.status,
        }

        # Include sunset_date only for deprecated models
        if caps.status == "deprecated" and caps.sunset_date:
            model_dict["sunset_date"] = caps.sunset_date

        models.append(model_dict)

    return models
```

### Part 4: Deduplication Strategy

Multiple model variants exist for the same logical model:

| Variant | model_id | public_id |
|---------|----------|-----------|
| Native Anthropic | `claude-opus-4-5-20251101` | `claude-opus-4-5` |
| Vertex AI Anthropic | `claude-opus-4-5@20251101` | `claude-opus-4-5` |
| Native Google | `gemini-2.5-flash` | `gemini-2.5-flash` |
| Vertex AI Google | `gemini-2.5-flash-preview-05-20` | `gemini-2.5-flash` |

Deduplication uses `public_id` to ensure frontend receives one entry per logical model.

### Part 5: Feature Flag Migration

```python
# core/feature_flags.py
use_model_registry_for_frontend: bool = Field(
    default=True,
    description="Use ModelRegistry.get_frontend_models() instead of AVAILABLE_MODELS"
)
```

When `False`, emits `DeprecationWarning` to guide migration.

### Part 6: Three-Tier Model Selection

Backend uses `ModelSelector` for task-based model selection:

```
Tier        │ Google           │ Anthropic         │ OpenAI
────────────┼──────────────────┼───────────────────┼──────────────
simple      │ gemini-3-flash   │ claude-haiku-4-5  │ gpt-4.1-nano
complicated │ gemini-2.5-flash │ claude-sonnet-4-5 │ gpt-4.1-mini
complex     │ gemini-2.5-pro   │ claude-opus-4-5   │ o3
```

Fallback chain: Primary vendor → Other available vendors → Google (default)

## Consequences

### Positive

1. **Single source of truth**: All model data in ModelRegistry
2. **Accurate capabilities**: Frontend shows real model features
3. **Lifecycle visibility**: Users see model status at a glance
4. **Sunset warnings**: 30+ days notice before model retirement
5. **Vendor abstraction**: Vertex AI variants transparent to users
6. **Cost tracking**: Centralized cost data for usage tracking

### Negative

1. **Migration burden**: Existing code using AVAILABLE_MODELS must migrate
2. **Startup overhead**: ModelRegistry initialization registers ~40 models
3. **Version coupling**: Model version updates require code changes

### Risks

1. **Stale data**: Model capabilities may change without registry updates
2. **Missing models**: New models need manual registration

## Implementation Files

| Component | Files |
|-----------|-------|
| Model Registry | `agents/model_registry.py` |
| Model Selector | `agents/model_selector.py` |
| Config API | `api/v1/config.py` |
| Feature Flag | `core/feature_flags.py` |
| Frontend Types | `studio/frontend/src/types/api.ts` |
| MSW Handlers | `studio/frontend/src/mocks/handlers.ts` |
| E2E Tests | `studio/frontend/e2e/model-selector.spec.ts` |

## API Response Format

`GET /api/v1/config/models` returns:

```json
[
  {
    "id": "claude-opus-4-5",
    "name": "Claude Opus 4.5",
    "provider": "anthropic",
    "supports_thinking": true,
    "supports_vision": true,
    "supports_tools": true,
    "status": "current"
  },
  {
    "id": "claude-3-5-sonnet",
    "name": "Claude 3.5 Sonnet",
    "provider": "anthropic",
    "supports_thinking": true,
    "supports_vision": true,
    "supports_tools": true,
    "status": "deprecated",
    "sunset_date": "2025-10-31"
  }
]
```

## Related ADRs

- **ADR-0001**: LLM Multi-Provider Strategy
- **ADR-0009**: Feature Flag System
- **ADR-0100**: Frontend AI-Native Integration

## References

- `docs/guides/model-lifecycle.mdx` - User-facing documentation
- `docs-internal/frontend/DESIGN_SYSTEM.md` - Badge component specs
- Sprint 2 - Enhanced Model Selector implementation
