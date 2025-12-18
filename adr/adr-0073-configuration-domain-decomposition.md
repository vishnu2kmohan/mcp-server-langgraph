# ADR-0073: Configuration Domain Decomposition

## Status

Accepted

## Date

2025-12-18

## Context

The `core/config.py` had grown to 500+ lines with 100+ settings in a flat structure. This monolithic configuration created several problems:

1. **Cognitive overload**: Developers had to navigate 100+ settings in one file
2. **Weak grouping**: Related settings scattered throughout (e.g., auth settings mixed with LLM settings)
3. **Testing friction**: Couldn't test domain-specific validation in isolation
4. **Merge conflicts**: Multiple feature branches touching the same file

Example of the flat structure:
```python
class Settings(BaseSettings):
    # 100+ fields in one class
    jwt_secret_key: str
    keycloak_realm: str
    llm_provider: str
    postgres_host: str
    enable_verification: bool
    # ... 95 more fields
```

## Decision

Decompose the monolithic `config.py` into domain-specific modules while maintaining full backwards compatibility.

### Package Structure

```
src/mcp_server_langgraph/core/config/
├── __init__.py          # Re-exports Settings, settings for backwards compat
├── base.py              # DomainSettings base class, shared utilities
├── auth.py              # AuthSettings (JWT, DPoP, Keycloak, OpenFGA)
├── llm.py               # LLMSettings (providers, models, fallback)
├── storage.py           # StorageSettings (Postgres, Redis, Qdrant)
├── observability.py     # ObservabilitySettings (OTEL, LangSmith, LGTM)
├── agent.py             # AgentSettings (feature flags, graph config)
└── compliance.py        # ComplianceSettings (GDPR, HIPAA, SOC2, audit)
```

### Domain Settings Pattern

```python
# base.py
class DomainSettings(BaseModel):
    """Base class for domain-specific settings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

# auth.py
class AuthSettings(DomainSettings):
    """Authentication and authorization settings."""
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Keycloak
    keycloak_server_url: str | None = None
    keycloak_realm: str = "mcp-server"

    # OpenFGA
    openfga_api_url: str = "http://localhost:8080"
    openfga_store_id: str | None = None
```

### Backwards Compatibility

The `__init__.py` re-exports everything for unchanged imports:

```python
# Existing code works unchanged
from mcp_server_langgraph.core.config import Settings, settings

# New granular imports also work
from mcp_server_langgraph.core.config.auth import AuthSettings
from mcp_server_langgraph.core.config.llm import LLMSettings
```

### Cross-Field Validation

Domain modules can contain focused validators:

```python
# auth.py
class AuthSettings(DomainSettings):
    @model_validator(mode="after")
    def validate_auth_config(self) -> Self:
        if self.auth_provider == "keycloak" and not self.keycloak_server_url:
            raise ValueError("keycloak_server_url required when auth_provider=keycloak")
        return self
```

## Consequences

### Positive

1. **Domain cohesion**: Related settings grouped together (~80 lines per module)
2. **Testability**: Domain-specific validation testable in isolation
3. **Discoverability**: IDE autocomplete shows relevant settings per domain
4. **Reduced merge conflicts**: Features touch different modules
5. **Backwards compatible**: Zero changes to existing imports

### Negative

1. **More files**: 8 files instead of 1 (acceptable tradeoff for maintainability)
2. **Potential circular imports**: Careful design required for cross-domain validation

### Neutral

1. **Legacy file preserved**: `config_legacy.py` contains the monolithic Settings class
2. **Gradual migration**: Teams can adopt domain-specific imports at their own pace

## Implementation

Files created:
- `src/mcp_server_langgraph/core/config/__init__.py`
- `src/mcp_server_langgraph/core/config/base.py`
- `src/mcp_server_langgraph/core/config/auth.py`
- `src/mcp_server_langgraph/core/config/llm.py`
- `src/mcp_server_langgraph/core/config/storage.py`
- `src/mcp_server_langgraph/core/config/observability.py`
- `src/mcp_server_langgraph/core/config/agent.py`
- `src/mcp_server_langgraph/core/config/compliance.py`

Files renamed:
- `src/mcp_server_langgraph/core/config.py` -> `config_legacy.py`

Tests:
- `tests/unit/core/config/test_auth_settings.py`
- `tests/unit/core/config/test_llm_settings.py`
- `tests/unit/core/config/test_storage_settings.py`
- `tests/unit/core/config/test_observability_settings.py`
- `tests/unit/core/config/test_agent_settings.py`
- `tests/unit/core/config/test_compliance_settings.py`

## References

- [Pydantic Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12-Factor App - Config](https://12factor.net/config)
- ADR-0007: Authentication Provider Pattern
- ADR-0017: Multi-Provider LLM Support
