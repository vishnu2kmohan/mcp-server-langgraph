"""
Main FastAPI Application

Centralized FastAPI app that mounts all HTTP API routers for:
- API Key management
- Service Principal management
- GDPR compliance endpoints
- SCIM 2.0 provisioning

This app can be run standalone via uvicorn or integrated into the MCP server.

Usage:
    uvicorn mcp_server_langgraph.app:app --host 0.0.0.0 --port 8000
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware
from mcp_server_langgraph.api.router_registry import get_router_registry, reset_router_registry
from mcp_server_langgraph.api.v1.auth import AuthSecurityHeadersMiddleware
from mcp_server_langgraph.api.routers import register_default_routers
from mcp_server_langgraph.api.error_handlers import register_exception_handlers
from mcp_server_langgraph.api.health import run_startup_validation_async
from mcp_server_langgraph.auth.factory import create_user_provider
from mcp_server_langgraph.auth.middleware import AuthMiddleware, set_global_auth_middleware
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.middleware.rate_limiter import setup_rate_limiting
from mcp_server_langgraph.middleware.audit import AuditMiddleware
from mcp_server_langgraph.middleware.user_context import UserContextMiddleware
from mcp_server_langgraph.bootstrap import bootstrap_all, init_observability, AppState
from mcp_server_langgraph.observability.telemetry import logger


def create_app(settings_override: Settings | None = None, skip_startup_validation: bool = False) -> FastAPI:
    """
    Create and configure the FastAPI application.
    ...
    """
    # Use override settings if provided, otherwise use global settings
    config = settings_override if settings_override is not None else settings

    # Initialize observability FIRST before any logging (OpenAI Codex Finding #3)
    # This prevents RuntimeError: "Observability not initialized" when logger is used
    init_observability(config)

    # Validation: Verify logger is now usable (prevent regression)
    try:
        logger.debug("Observability initialized successfully")
    except RuntimeError as e:
        msg = (
            "Observability initialization failed! Logger still raises RuntimeError. "
            f"Error: {e}. This is a critical bug - logging will fail throughout the app."
        )
        raise RuntimeError(msg)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """
        Application lifespan handler using modular bootstrap.

        Uses bootstrap package for testable, isolated initialization phases:
        1. Security (OpenFGA, auth middleware)
        2. Storage (audit, compliance, schedulers)
        3. HTTP (connection pool)

        Reduced from ~160 lines to ~40 lines via P0.1 refactor.
        """
        # Run startup validation (skip in tests to avoid DB dependency)
        if not skip_startup_validation:
            try:
                await run_startup_validation_async()
            except Exception as e:
                logger.critical(f"Startup validation failed: {e}")
                raise
        else:
            logger.debug("Skipping startup validation (test mode)")

        # Bootstrap all components using modular initialization
        state: AppState = await bootstrap_all(config)

        # Store in app.state for request-scoped access via api/deps.py
        app.state.openfga_client = state.security.openfga_client if state.security else None
        app.state.http_client_manager = state.http.http_client_manager if state.http else None
        app.state.audit_service = state.storage.audit_service if state.storage else None
        app.state.websocket_lifecycle = state.websocket.mcp_lifecycle_manager if state.websocket else None

        # Context graph decision emitter for decision trace capture (ADR-0101)
        app.state.decision_emitter = state.context_graph.emitter if state.context_graph else None

        # Register marketplace admin router if available
        if state.skills and state.skills.marketplace_router:
            app.include_router(
                state.skills.marketplace_router,
                prefix="/api/v1/admin",
                tags=["marketplace-admin"],
            )
            logger.info("Marketplace admin router registered at /api/v1/admin/marketplaces")

        # Global setters are now called within bootstrap/storage.py:init_storage()
        # This consolidates initialization logic in bootstrap modules.
        # See: set_audit_service, set_audit_event_broadcaster,
        #      set_notification_broadcaster, set_compliance_service

        yield

        # Cleanup all components (reverse initialization order)
        await state.cleanup()
        logger.info("Application shutdown complete")

    app = FastAPI(
        title="MCP Server LangGraph API",
        version="2.8.0",
        description="Production-ready MCP server with LangGraph, OpenFGA, and multi-LLM support",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware - use config (settings or override) for environment-aware defaults
    # get_cors_origins() provides localhost origins in dev, empty list in production
    cors_origins = config.get_cors_origins()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            # Expose rate limit and pagination headers to browser clients
            expose_headers=[
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Retry-After",
                "Link",  # RFC 5988 pagination links
                "X-Total-Count",
                "X-Request-ID",
            ],
        )
        try:
            logger.info(f"CORS enabled for origins: {cors_origins}")
        except RuntimeError:
            pass  # Graceful degradation if observability not initialized
    else:
        try:
            logger.info("CORS disabled (no allowed origins configured)")
        except RuntimeError:
            pass  # Graceful degradation if observability not initialized

    # Authentication middleware - intercepts requests and verifies JWT tokens
    # Sets request.state.user for authenticated requests
    # Use factory to create the correct user provider based on AUTH_PROVIDER setting
    user_provider = create_user_provider(config)
    auth_middleware = AuthMiddleware(secret_key=config.jwt_secret_key, settings=config, user_provider=user_provider)

    # Store in app.state for DI-based access (recommended pattern)
    app.state.auth_middleware = auth_middleware

    # Also set global for backward compatibility with code using get_auth_middleware()
    set_global_auth_middleware(auth_middleware)

    app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)
    try:
        logger.info("Auth request middleware enabled")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    # User context middleware - sets contextvar for user-scoped session storage
    # Must be after AuthRequestMiddleware to access request.state.user
    # v8: Enables user_id for session ownership enforcement (Plan Finding 49)
    app.add_middleware(UserContextMiddleware)
    try:
        logger.info("User context middleware enabled (session ownership enforcement)")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    # Audit middleware - captures HTTP requests for compliance logging
    # Must be after AuthRequestMiddleware to access request.state.user
    # Supports: FedRAMP AU-2/3, HIPAA 164.312(b), GDPR Art. 30, SOC 2 CC6/CC7
    app.add_middleware(AuditMiddleware)
    try:
        logger.info("Audit middleware enabled (FedRAMP/HIPAA/GDPR/SOC2 compliance)")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    # Security headers middleware - adds OWASP-recommended security headers to auth endpoints
    # Headers: X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy, HSTS (in production)
    app.add_middleware(AuthSecurityHeadersMiddleware)
    try:
        logger.info("Auth security headers middleware enabled (OWASP best practices)")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    # Rate limiting - setup function registers middleware and exception handlers
    setup_rate_limiting(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Register root endpoint BEFORE routers (so it's not overridden)
    @app.get("/")
    async def root() -> RedirectResponse:
        """Root endpoint redirects to Studio UI"""
        return RedirectResponse(url="/studio", status_code=307)

    # Include API routers via RouterRegistry (OCP pattern)
    # Reset registry for clean state (important for tests with multiple app creations)
    reset_router_registry()
    registry = get_router_registry()
    register_default_routers(registry)
    registry.mount_all(app)

    try:
        logger.info("FastAPI application created with all routers mounted")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    return app


# Create the application instance
# Skip validation when running under pytest to avoid DB dependency in unit tests
# This is detected via PYTEST_CURRENT_TEST environment variable set by pytest
# Also skip if TESTING env var is set (used by integration tests)
_is_pytest_session = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("TESTING") == "true"
app = create_app(skip_startup_validation=_is_pytest_session)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server-langgraph"}
