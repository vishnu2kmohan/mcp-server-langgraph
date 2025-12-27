"""
Lightweight Dependencies for Authz-Proxy

This module provides lightweight dependency injection functions specifically
for the authz-proxy container. It avoids importing heavy modules like
repositories, storage, and database which are not needed for the proxy.

For the full dependencies module, see: mcp_server_langgraph.core.dependencies
"""

from fastapi import Request

from mcp_server_langgraph.auth.openfga import OpenFGAClient


def get_openfga_client_from_request(request: Request) -> OpenFGAClient | None:
    """
    Get OpenFGA client from FastAPI request state (async-initialized pattern).

    This is the preferred way to access OpenFGA client in FastAPI routes.
    The client is initialized once during app lifespan startup and stored
    in app.state.openfga_client.

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        OpenFGAClient if configured and initialized, None otherwise
    """
    return getattr(request.app.state, "openfga_client", None)
