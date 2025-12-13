"""
OpenFGA Playground Auth Proxy Server

Protects OpenFGA Playground with:
- Keycloak JWT authentication
- OpenFGA authorization (user must have 'admin' on 'authz:playground')

This proxy intercepts all requests to /playground/* and:
1. Validates the JWT token via Keycloak JWKS
2. Checks if the user has 'admin' permission on 'authz:playground' via OpenFGA
3. If authorized, proxies the request to the OpenFGA Playground backend
4. If not authorized, returns 401 (no token) or 403 (no permission)

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from mcp_server_langgraph.auth.factory import create_auth_middleware
from mcp_server_langgraph.auth.middleware import get_current_user, set_global_auth_middleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import init_observability, logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Initializes:
    - Observability (OpenTelemetry)
    - Auth middleware (Keycloak + OpenFGA)
    - OpenFGA store_id lookup
    """
    global _openfga_store_id

    # Initialize observability for logging and tracing
    init_observability(settings)

    # Create and register auth middleware globally
    # This is required for get_current_user() dependency to work
    auth_middleware = create_auth_middleware(settings)
    set_global_auth_middleware(auth_middleware)

    # Fetch OpenFGA store_id at startup
    _openfga_store_id = await fetch_store_id()
    if _openfga_store_id:
        logger.info(f"OpenFGA store_id fetched: {_openfga_store_id}")
    else:
        logger.warning("Could not fetch OpenFGA store_id - permission checks may fail")

    logger.info(
        "authz-proxy initialized",
        extra={
            "auth_provider": settings.auth_provider,
            "keycloak_server_url": settings.keycloak_server_url,
            "openfga_store_id": _openfga_store_id,
        },
    )

    yield

    logger.info("authz-proxy shutting down")


# Create FastAPI app
app = FastAPI(
    title="OpenFGA Playground Auth Proxy",
    description="Protects OpenFGA Playground with Keycloak + OpenFGA authorization",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration
OPENFGA_PLAYGROUND_URL = os.getenv("OPENFGA_PLAYGROUND_URL", "http://openfga-test:3000")
OPENFGA_API_URL = os.getenv("OPENFGA_API_URL", "http://localhost:8080")
OPENFGA_PRESHARED_KEY = os.getenv("OPENFGA_PRESHARED_KEY")
OPENFGA_STORE_NAME = "mcp-server-langgraph-test"  # Must match seed script
AUTHZ_OBJECT = "authz:playground"

# Global store_id, fetched at startup
_openfga_store_id: str | None = None


async def fetch_store_id() -> str | None:
    """Fetch the OpenFGA store ID by looking up existing stores."""
    import httpx

    headers = {"Content-Type": "application/json"}
    if OPENFGA_PRESHARED_KEY:
        headers["Authorization"] = f"Bearer {OPENFGA_PRESHARED_KEY}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OPENFGA_API_URL}/stores", headers=headers)
            if response.status_code == 200:
                stores = response.json().get("stores", [])
                for store in stores:
                    if store.get("name") == OPENFGA_STORE_NAME:
                        store_id: str = str(store["id"])
                        return store_id
                # If no store with expected name, use first store
                if stores:
                    first_store_id: str = str(stores[0]["id"])
                    return first_store_id
    except Exception as e:
        logger.error(f"Failed to fetch OpenFGA store ID: {e}")

    return None


def get_openfga_client() -> OpenFGAClient:
    """Get OpenFGA client instance with preshared key authentication and store_id."""
    # Use store_id from environment or fetched at startup
    store_id = os.getenv("OPENFGA_STORE_ID") or _openfga_store_id

    config = OpenFGAConfig(
        api_url=OPENFGA_API_URL,
        store_id=store_id,
        preshared_key=OPENFGA_PRESHARED_KEY,
    )
    return OpenFGAClient(config=config)


async def require_admin_permission(
    current_user: dict[str, Any] = Depends(get_current_user),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> dict[str, Any]:
    """Require admin permission on authz:playground."""
    # get_current_user returns dict with 'username' (normalized from preferred_username or sub)
    # and 'user_id' (already in "user:username" format)
    user_id = current_user.get("user_id") or f"user:{current_user.get('username', 'unknown')}"

    try:
        allowed = await openfga.check_permission(
            user=user_id,
            relation="admin",
            object=AUTHZ_OBJECT,
        )
    finally:
        await openfga.close()

    if not allowed:
        logger.warning(
            "OpenFGA Playground access denied",
            extra={"user": user_id, "permission": "admin", "object": AUTHZ_OBJECT},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to OpenFGA Playground. Admin permission required.",
        )

    logger.info(
        "OpenFGA Playground access granted",
        extra={"user": user_id, "permission": "admin", "object": AUTHZ_OBJECT},
    )
    return current_user


@app.get("/api/authz-proxy/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint (public).

    Required for Kubernetes liveness/readiness probes.
    """
    return {"status": "healthy", "service": "authz-proxy"}


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy_to_openfga_playground(
    path: str,
    request: Request,
    current_user: dict[str, Any] = Depends(require_admin_permission),
) -> Response:
    """
    Proxy requests to OpenFGA Playground.

    All requests are authenticated via Keycloak JWT and authorized via OpenFGA.
    Only users with 'admin' permission on 'authz:playground' can access.
    """
    # Build target URL
    target_url = f"{OPENFGA_PLAYGROUND_URL}/{path}"

    # Get query string
    if request.query_params:
        target_url += f"?{request.query_params}"

    # Forward headers (excluding host and authorization - we're proxying internally)
    forward_headers = {
        key: value for key, value in request.headers.items() if key.lower() not in ("host", "authorization", "content-length")
    }

    # Add user info headers for audit trail
    forward_headers["X-Forwarded-User"] = current_user.get("preferred_username", "unknown")
    forward_headers["X-Forwarded-Email"] = current_user.get("email", "")

    try:
        # Get request body
        body = await request.body()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body if body else None,
            )

            # Return proxied response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")
                },
                media_type=response.headers.get("content-type"),
            )

    except httpx.TimeoutException:
        logger.error(f"Timeout proxying request to OpenFGA Playground: {target_url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout connecting to OpenFGA Playground",
        )
    except httpx.ConnectError as e:
        logger.error(f"Connection error proxying to OpenFGA Playground: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to OpenFGA Playground",
        )
    except Exception as e:
        logger.error(f"Error proxying to OpenFGA Playground: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proxy error: {e}",
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom exception handler for consistent error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )
