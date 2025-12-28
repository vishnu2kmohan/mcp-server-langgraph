"""
Streaming Configuration Module.

Settings for MCP WebSocket streaming, metrics cleanup, and chunk handling.
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class StreamingSettings(DomainSettings):
    """
    Streaming and WebSocket configuration settings.

    Covers:
    - Stream metrics cleanup intervals
    - Idle connection timeouts
    - Chunk size limits
    - Feature toggles
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # Metrics cleanup configuration
    streaming_metrics_cleanup_interval: int = Field(
        default=300,  # 5 minutes
        description="Interval in seconds between stream metrics cleanup runs",
    )

    streaming_max_age_seconds: int = Field(
        default=3600,  # 1 hour
        description="Maximum age in seconds for completed streams before cleanup",
    )

    # Connection cleanup
    streaming_idle_cleanup_interval: int = Field(
        default=60,  # 1 minute
        description="Interval in seconds between idle connection cleanup runs",
    )

    # Chunk configuration
    streaming_max_chunk_size: int = Field(
        default=65536,  # 64KB
        description="Maximum size in bytes for a single streaming chunk",
    )

    # Feature toggle
    streaming_enabled: bool = Field(
        default=True,
        description="Enable or disable streaming support globally",
    )

    # Rate limiting
    streaming_max_notifications_per_second: int = Field(
        default=100,
        description="Maximum streaming notifications per second to prevent overwhelming clients",
    )

    # Security limits (previously hardcoded in mcp_websocket.py)
    streaming_max_connections_per_user: int = Field(
        default=5,
        description="Maximum WebSocket connections allowed per user",
    )

    streaming_max_message_size: int = Field(
        default=1_000_000,  # 1MB
        description="Maximum size in bytes for incoming WebSocket messages",
    )

    streaming_max_messages_per_minute: int = Field(
        default=600,
        description="Maximum messages allowed per user per minute",
    )

    streaming_idle_timeout_seconds: int = Field(
        default=1800,  # 30 minutes
        description="Idle connection timeout in seconds before automatic disconnect",
    )

    # Token validation
    streaming_token_validation_interval: int = Field(
        default=300,  # 5 minutes
        description="Interval in seconds for JWT token validation during active connections",
    )


__all__ = ["StreamingSettings"]
