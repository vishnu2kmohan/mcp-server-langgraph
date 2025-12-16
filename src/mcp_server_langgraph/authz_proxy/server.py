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
from mcp_server_langgraph.core.dependencies import get_openfga_client_from_request
from mcp_server_langgraph.observability.telemetry import (
    init_observability,
    instrument_fastapi_app,
    logger,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Initializes:
    - Observability (OpenTelemetry)
    - FastAPI OTEL instrumentation
    - Auth middleware (Keycloak + OpenFGA)

    NOTE: OpenFGA store_id and model_id are resolved dynamically by the
    centralized OpenFGA client (see core/dependencies.py).
    """
    # Initialize observability for logging and tracing
    init_observability(settings)

    # Instrument FastAPI app with OTEL tracing (best practice)
    try:
        instrument_fastapi_app(app)
        logger.info("FastAPI app instrumented with OTEL tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI app with OTEL: {e}")

    # Create and register auth middleware globally
    # This is required for get_current_user() dependency to work
    auth_middleware = create_auth_middleware(settings)
    set_global_auth_middleware(auth_middleware)

    # Initialize OpenFGA client (async initialization pattern)
    openfga_client: OpenFGAClient | None = None
    try:
        has_store_config = settings.openfga_store_id or settings.openfga_store_name
        if has_store_config:
            oidc_issuer = settings.openfga_oidc_issuer
            if not oidc_issuer and settings.openfga_oidc_client_id and settings.openfga_oidc_client_secret:
                oidc_issuer = f"{settings.keycloak_server_url.rstrip('/')}/realms/{settings.keycloak_realm}"

            openfga_config = OpenFGAConfig(
                api_url=settings.openfga_api_url,
                store_id=settings.openfga_store_id,
                store_name=settings.openfga_store_name,
                model_id=settings.openfga_model_id,
                oidc_client_id=settings.openfga_oidc_client_id,
                oidc_client_secret=settings.openfga_oidc_client_secret,
                oidc_issuer=oidc_issuer,
                preshared_key=settings.openfga_preshared_key,
            )
            openfga_client = OpenFGAClient(config=openfga_config)
            await openfga_client._ensure_initialized()
            logger.info(
                "OpenFGA client initialized for authz-proxy",
                extra={"store_id": openfga_client.store_id, "model_id": openfga_client.model_id},
            )
        else:
            logger.warning("OpenFGA not configured for authz-proxy")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenFGA for authz-proxy: {e}")
        openfga_client = None

    # Store in app.state for get_openfga_client_from_request dependency
    app.state.openfga_client = openfga_client

    logger.info(
        "authz-proxy initialized",
        extra={
            "auth_provider": settings.auth_provider,
            "keycloak_server_url": settings.keycloak_server_url,
        },
    )

    yield

    # Cleanup OpenFGA client
    if openfga_client is not None:
        try:
            await openfga_client.close()
            logger.info("OpenFGA client closed for authz-proxy")
        except Exception as e:
            logger.warning(f"Error closing OpenFGA client: {e}")

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
AUTHZ_OBJECT = "authz:playground"

# NOTE: OpenFGA client is initialized in lifespan and accessed via app.state
# The client handles OIDC authentication, store lookup by name, and model ID resolution automatically


async def require_admin_permission(
    current_user: dict[str, Any] = Depends(get_current_user),
    openfga: OpenFGAClient | None = Depends(get_openfga_client_from_request),
) -> dict[str, Any]:
    """Require admin permission on authz:playground."""
    # get_current_user returns dict with 'username' (normalized from preferred_username or sub)
    # and 'user_id' (already in "user:username" format)
    user_id = current_user.get("user_id") or f"user:{current_user.get('username', 'unknown')}"

    # Handle case where OpenFGA is not configured
    if openfga is None:
        logger.warning(
            "OpenFGA not configured - denying access (fail-closed)",
            extra={"user": user_id, "permission": "admin", "object": AUTHZ_OBJECT},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization service unavailable",
        )

    allowed = await openfga.check_permission(
        user=user_id,
        relation="admin",
        object=AUTHZ_OBJECT,
    )
    # Note: Don't close the client - it's managed by app lifespan

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


@app.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint (public).

    Required for Alloy/Prometheus scraping. Exposes OpenTelemetry metrics
    in Prometheus format via prometheus-client.
    """
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


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

    # Add user info headers for audit trail and authentication
    forward_headers["X-Forwarded-User"] = current_user.get("preferred_username", "unknown")
    forward_headers["X-Forwarded-Email"] = current_user.get("email", "")
    # Forward roles as comma-separated list for RBAC (persona detection)
    roles = current_user.get("roles", [])
    forward_headers["X-Forwarded-Groups"] = ",".join(roles) if roles else ""

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
