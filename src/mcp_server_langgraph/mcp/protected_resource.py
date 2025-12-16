"""
OAuth 2.0 Protected Resource Metadata Endpoint (RFC 9728)

Per MCP 2025-11-25, servers MUST expose this endpoint to enable
clients to discover the authorization servers for OAuth authentication.

Reference:
- RFC 9728: https://www.rfc-editor.org/rfc/rfc9728
- MCP 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProtectedResourceMetadataResponse(BaseModel):
    """OAuth 2.0 Protected Resource Metadata (RFC 9728)."""

    resource: str = Field(description="Protected resource identifier URL")
    authorization_servers: list[str] = Field(description="List of authorization server issuer URLs")
    scopes_supported: list[str] = Field(
        default_factory=list,
        description="OAuth scopes supported by this resource",
    )
    bearer_methods_supported: list[str] = Field(
        default_factory=lambda: ["header"],
        description="Methods for sending bearer tokens",
    )


def create_protected_resource_router(
    resource_url: str,
    authorization_servers: list[str],
    scopes_supported: list[str] | None = None,
    bearer_methods_supported: list[str] | None = None,
    path_prefix: str | None = None,
    cache_max_age: int = 3600,
) -> APIRouter:
    """
    Create a FastAPI router for Protected Resource Metadata.

    Per RFC 9728 Section 3.1, the metadata is served at:
    - /.well-known/oauth-protected-resource (for root resources)
    - /.well-known/oauth-protected-resource/{path} (for path-based resources)

    Args:
        resource_url: The protected resource URL (e.g., https://mcp.example.com)
        authorization_servers: List of authorization server issuer URLs
        scopes_supported: OAuth scopes supported by this resource
        bearer_methods_supported: Methods for sending bearer tokens (default: ["header"])
        path_prefix: Optional path prefix for path-based discovery
        cache_max_age: Cache-Control max-age in seconds (default: 1 hour)

    Returns:
        FastAPI router with the well-known endpoint
    """
    router = APIRouter()

    # Build the metadata response
    metadata = ProtectedResourceMetadataResponse(
        resource=resource_url,
        authorization_servers=authorization_servers,
        scopes_supported=scopes_supported or [],
        bearer_methods_supported=bearer_methods_supported or ["header"],
    )

    # Build the endpoint path
    if path_prefix:
        endpoint_path = f"/.well-known/oauth-protected-resource{path_prefix}"
    else:
        endpoint_path = "/.well-known/oauth-protected-resource"

    @router.get(
        endpoint_path,
        response_model=ProtectedResourceMetadataResponse,
        summary="Protected Resource Metadata",
        description="OAuth 2.0 Protected Resource Metadata per RFC 9728",
        tags=["OAuth 2.0"],
    )
    async def get_protected_resource_metadata() -> JSONResponse:
        """
        Return Protected Resource Metadata per RFC 9728.

        This endpoint enables OAuth clients to discover:
        - The authorization server(s) to use for authentication
        - The scopes supported by this resource
        - The methods for sending bearer tokens

        Per MCP 2025-11-25, clients MUST check this endpoint or
        parse the WWW-Authenticate header to discover authorization.
        """
        return JSONResponse(
            content=metadata.model_dump(),
            headers={
                "Cache-Control": f"max-age={cache_max_age}",
                "Content-Type": "application/json",
            },
        )

    # Add OPTIONS handler for CORS preflight
    @router.options(endpoint_path)
    async def options_protected_resource_metadata() -> JSONResponse:
        """Handle CORS preflight requests."""
        return JSONResponse(
            content={},
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "86400",
            },
        )

    return router


def get_default_mcp_scopes() -> list[str]:
    """
    Get default MCP scopes per MCP 2025-11-25.

    These are common scopes that MCP servers might support.
    """
    return [
        # Tool operations
        "tools:read",
        "tools:execute",
        # Resource operations
        "resources:read",
        "resources:write",
        "resources:subscribe",
        # Prompt operations
        "prompts:read",
        "prompts:execute",
        # Sampling operations
        "sampling:create",
        # Logging
        "logging:write",
        # Roots (filesystem access)
        "roots:read",
    ]
