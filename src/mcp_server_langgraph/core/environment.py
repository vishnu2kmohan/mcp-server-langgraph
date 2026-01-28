"""Environment utility functions.

Provides environment detection and mode checking utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings


def is_developer_mode(settings: Settings | None = None) -> bool:
    """Check if application is in developer mode.

    ONLY 'development' environment bypasses auth checks.
    All other environments (test, staging, production, unknown) are fail-closed.

    Args:
        settings: Optional Settings instance. Uses get_settings() if None.

    Returns:
        True ONLY if environment == "development" (case-insensitive)

    Examples:
        >>> from mcp_server_langgraph.core.environment import is_developer_mode
        >>> # With explicit settings
        >>> is_developer_mode(settings=mock_settings)
        >>> # Without settings (uses get_settings())
        >>> is_developer_mode()
    """
    if settings is None:
        # Lazy import to avoid circular dependencies
        from mcp_server_langgraph.api.deps import get_settings

        settings = get_settings()

    # Handle None environment value safely
    environment = settings.environment
    if environment is None:
        return False

    return environment.lower() == "development"
