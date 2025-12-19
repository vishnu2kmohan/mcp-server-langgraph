"""
Configuration Package - Modular Domain-Specific Configuration.

This package decomposes the monolithic config.py into domain-specific modules
while maintaining full backwards compatibility. All existing imports continue
to work unchanged.

Structure:
    core/config/
    ├── __init__.py          # This file - re-exports for backwards compatibility
    ├── base.py              # BaseSettings, SettingsConfigDict, shared utilities
    ├── auth.py              # AuthSettings (JWT, DPoP, Keycloak, OpenFGA)
    ├── llm.py               # LLMSettings (providers, models, fallback)
    ├── storage.py           # StorageSettings (Postgres, Redis, Qdrant)
    ├── observability.py     # ObservabilitySettings (OTEL, LangSmith, LGTM)
    ├── agent.py             # AgentSettings (feature flags, graph config)
    └── compliance.py        # ComplianceSettings (GDPR, HIPAA, SOC2, audit)

Usage (unchanged):
    from mcp_server_langgraph.core.config import Settings, settings

    # Individual settings still accessible
    settings.jwt_secret_key
    settings.llm_provider
    settings.enable_verification

Migration Path:
    The decomposed modules allow granular imports for better testability:

    from mcp_server_langgraph.core.config.auth import AuthSettings
    from mcp_server_langgraph.core.config.llm import LLMSettings
"""

# Import the main Settings class (moved from config_legacy.py)
# This ensures all existing imports work unchanged
# Note: _settings.py is named with underscore to avoid module/variable name collision
# which confused mypy when the module and instance shared the name "settings"
from mcp_server_langgraph.core.config._settings import Settings, settings

# Import domain-specific settings for granular use
from mcp_server_langgraph.core.config.base import DomainSettings
from mcp_server_langgraph.core.config.auth import AuthSettings
from mcp_server_langgraph.core.config.llm import LLMSettings
from mcp_server_langgraph.core.config.storage import StorageSettings
from mcp_server_langgraph.core.config.observability import ObservabilitySettings
from mcp_server_langgraph.core.config.agent import AgentSettings
from mcp_server_langgraph.core.config.compliance import ComplianceSettings
from mcp_server_langgraph.core.config.streaming import StreamingSettings

# Re-export for backwards compatibility and domain-specific access
__all__ = [
    # Backwards compatibility (monolithic)
    "Settings",
    "settings",
    # Domain-specific settings (modular)
    "DomainSettings",
    "AuthSettings",
    "LLMSettings",
    "StorageSettings",
    "ObservabilitySettings",
    "AgentSettings",
    "ComplianceSettings",
    "StreamingSettings",
]
