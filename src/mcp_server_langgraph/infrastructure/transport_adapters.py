"""
Transport Adapter Utilities

Provides utilities for different transport mechanisms (STDIO, HTTP, etc.)
"""

from __future__ import annotations

from typing import Any


def create_stdio_adapter() -> Any:
    """
    Create STDIO transport adapter.

    Returns:
        STDIO adapter instance

    Example:
        adapter = create_stdio_adapter()
    """

    # Mock implementation for now
    class StdioAdapter:
        """STDIO transport adapter"""

        def __init__(self) -> None:
            self.transport_type = "stdio"

    return StdioAdapter()


def create_http_adapter() -> Any:
    """
    Create HTTP transport adapter.

    Returns:
        HTTP adapter instance

    Example:
        adapter = create_http_adapter()
    """

    # Mock implementation for now
    class HttpAdapter:
        """HTTP transport adapter"""

        def __init__(self) -> None:
            self.transport_type = "http"

    return HttpAdapter()
