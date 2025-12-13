"""
Feature Flag Management System

Enables gradual rollouts, A/B testing, and safe feature deployment.
All flags are configurable via environment variables for different environments.
"""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    """
    Feature flags for controlling system behavior

    All flags can be overridden via environment variables with FF_ prefix.
    Example: FF_ENABLE_PYDANTIC_AI_ROUTING=false
    """

    # Pydantic AI Features
    enable_pydantic_ai_routing: bool = Field(
        default=True,
        description="Use Pydantic AI for type-safe routing decisions with confidence scoring",
    )

    enable_pydantic_ai_responses: bool = Field(
        default=True,
        description="Use Pydantic AI for structured response generation with validation",
    )

    pydantic_ai_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to trust Pydantic AI routing (0.0-1.0)",
    )

    # LLM Features
    enable_llm_fallback: bool = Field(
        default=True,
        description="Enable automatic fallback to alternative models on failure",
    )

    enable_streaming_responses: bool = Field(
        default=True,
        description="Enable streaming responses for real-time output",
    )

    llm_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Maximum time to wait for LLM responses (10-300 seconds)",
    )

    # Authorization Features
    enable_openfga: bool = Field(
        default=True,
        description="Enable OpenFGA for fine-grained authorization checks",
    )

    openfga_strict_mode: bool = Field(
        default=False,
        description="Fail-closed on OpenFGA errors (strict) vs fail-open (permissive)",
    )

    openfga_cache_ttl_seconds: int = Field(
        default=60,
        ge=0,
        le=3600,
        description="Cache authorization check results for N seconds (0=disabled)",
    )

    # Keycloak Features
    enable_keycloak: bool = Field(
        default=True,
        description="Enable Keycloak integration for authentication",
    )

    enable_token_refresh: bool = Field(
        default=True,
        description="Enable automatic token refresh for Keycloak tokens",
    )

    keycloak_role_sync: bool = Field(
        default=True,
        description="Sync Keycloak roles/groups to OpenFGA on authentication",
    )

    openfga_sync_on_login: bool = Field(
        default=True,
        description="Synchronize user roles to OpenFGA on every login",
    )

    # Observability Features
    enable_langsmith: bool = Field(
        default=False,
        description="Enable LangSmith tracing for LLM-specific observability",
    )

    enable_detailed_logging: bool = Field(
        default=True,
        description="Include detailed context in logs (may increase log volume)",
    )

    enable_trace_sampling: bool = Field(
        default=False,
        description="Sample traces rather than capturing all (reduces overhead)",
    )

    trace_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Percentage of traces to sample when sampling enabled (0.0-1.0)",
    )

    # Performance Optimizations
    enable_response_caching: bool = Field(
        default=False,
        description="Cache LLM responses for identical inputs (experimental)",
    )

    cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=86400,
        description="How long to cache responses (60s-24h)",
    )

    enable_request_batching: bool = Field(
        default=False,
        description="Batch multiple requests to reduce LLM API calls (experimental)",
    )

    max_batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of requests to batch together",
    )

    # Agent Behavior
    max_agent_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum iterations for agent loops before stopping",
    )

    enable_agent_memory: bool = Field(
        default=True,
        description="Enable conversation memory/checkpointing for stateful agents",
    )

    memory_max_messages: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum messages to retain in conversation history",
    )

    # Security Features
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting to prevent abuse",
    )

    rate_limit_requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum requests per minute per user",
    )

    enable_input_validation: bool = Field(
        default=True,
        description="Validate and sanitize all user inputs",
    )

    max_input_length: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum input length in characters",
    )

    # UI Features (Unified Studio/BFF)
    enable_workflows_feature: bool = Field(
        default=True,
        description="Enable workflow builder UI feature",
    )

    enable_sessions_feature: bool = Field(
        default=True,
        description="Enable chat sessions UI feature",
    )

    enable_cost_dashboard: bool = Field(
        default=True,
        description="Enable cost dashboard for admins",
    )

    enable_cost_dashboard_users: bool = Field(
        default=False,
        description="Enable cost dashboard for regular users (not just admins)",
    )

    enable_observability_ui: bool = Field(
        default=True,
        description="Enable observability/trace UI feature",
    )

    enable_code_export: bool = Field(
        default=True,
        description="Enable code export feature in workflow builder",
    )

    enable_ai_suggestions: bool = Field(
        default=True,
        description="Enable AI-powered suggestions in UI",
    )

    enable_mcp_websocket: bool = Field(
        default=False,
        description="Enable MCP 2025-11-25 WebSocket protocol (experimental)",
    )

    # Experimental Features
    enable_experimental_features: bool = Field(
        default=False,
        description="Master switch for all experimental features",
    )

    enable_multi_agent_collaboration: bool = Field(
        default=False,
        description="Enable multiple agents working together (experimental)",
    )

    enable_tool_reflection: bool = Field(
        default=False,
        description="Enable agents to reflect on tool usage effectiveness (experimental)",
    )

    model_config = SettingsConfigDict(
        env_prefix="FF_",  # All flags use FF_ prefix in environment
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from environment
    )

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled

        Args:
            feature_name: Name of the feature flag (e.g., 'enable_pydantic_ai_routing')

        Returns:
            True if feature is enabled, False otherwise
        """
        return getattr(self, feature_name, False)

    def get_feature_value(self, feature_name: str, default: Any | None = None) -> Any:
        """
        Get feature flag value with fallback

        Args:
            feature_name: Name of the feature flag
            default: Default value if flag not found

        Returns:
            Feature flag value or default
        """
        return getattr(self, feature_name, default)

    def should_use_experimental(self, feature_name: str) -> bool:
        """
        Check if experimental feature should be enabled

        Requires both the master experimental switch and individual feature flag.

        Args:
            feature_name: Name of the experimental feature

        Returns:
            True if both master switch and feature are enabled
        """
        if not self.enable_experimental_features:
            return False

        return self.is_feature_enabled(feature_name)

    def get_ui_features_for_role(self, role: str) -> dict[str, bool]:
        """
        Get UI feature availability based on user role.

        Admins get access to all features. Regular users get filtered access
        based on feature flags (e.g., cost_dashboard_users controls whether
        non-admins can see the cost dashboard).

        Args:
            role: User role (e.g., 'admin', 'user', 'viewer')

        Returns:
            Dictionary mapping feature names to their enabled status for this role.

        Example:
            >>> flags.get_ui_features_for_role('admin')
            {'workflows': True, 'sessions': True, 'cost_dashboard': True, ...}

            >>> flags.get_ui_features_for_role('user')
            {'workflows': True, 'sessions': True, 'cost_dashboard': False, ...}
        """
        is_admin = role.lower() == "admin"

        return {
            "workflows": self.enable_workflows_feature,
            "sessions": self.enable_sessions_feature,
            # Cost dashboard: admins always see it; users only if enable_cost_dashboard_users
            "cost_dashboard": (
                self.enable_cost_dashboard if is_admin else (self.enable_cost_dashboard and self.enable_cost_dashboard_users)
            ),
            "observability": self.enable_observability_ui,
            "code_export": self.enable_code_export,
            "ai_suggestions": self.enable_ai_suggestions,
            "mcp_websocket": self.enable_mcp_websocket,
        }


# Global feature flags instance
feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance"""
    return feature_flags


def is_enabled(feature_name: str) -> bool:
    """
    Convenience function to check if a feature is enabled

    Args:
        feature_name: Name of the feature flag

    Returns:
        True if enabled, False otherwise

    Example:
        if is_enabled('enable_pydantic_ai_routing'):
            # Use Pydantic AI routing
    """
    return feature_flags.is_feature_enabled(feature_name)
