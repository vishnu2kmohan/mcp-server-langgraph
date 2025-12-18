"""
HTTP Bootstrap Module.

Initializes the shared HTTP client pool for external requests.
Uses httpx.AsyncClient with HTTP/2 and connection pooling.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING


logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.core.http_client import HttpClientManager


@dataclass
class HttpState:
    """
    HTTP state after client pool initialization.

    Holds reference to the HTTP client manager.
    """

    http_client_manager: "HttpClientManager | None" = None

    async def cleanup(self) -> None:
        """
        Cleanup HTTP resources.

        Closes the HTTP client pool to release connections.
        """
        if self.http_client_manager is not None:
            try:
                await self.http_client_manager.close()
            except Exception as e:
                logger.debug("Operation failed: %s", e)


async def init_http_client(settings: "Settings") -> HttpState:
    """
    Initialize the shared HTTP client pool.

    Creates a HttpClientManager with HTTP/2 and connection pooling
    for reuse across all auth modules and external requests.

    Args:
        settings: Application settings

    Returns:
        HttpState with initialized HTTP client manager

    Example:
        state = await init_http_client(settings)
        app.state.http_client_manager = state.http_client_manager
    """
    from mcp_server_langgraph.core.http_client import HttpClientManager
    from mcp_server_langgraph.observability.telemetry import logger

    http_client_manager = HttpClientManager()
    logger.info("HTTP client pool manager initialized")

    return HttpState(http_client_manager=http_client_manager)
