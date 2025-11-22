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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server_langgraph.api import api_keys_router, gdpr_router, health_router, scim_router, service_principals_router
from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware
from mcp_server_langgraph.api.error_handlers import register_exception_handlers
from mcp_server_langgraph.api.health import run_startup_validation
from mcp_server_langgraph.auth.middleware import AuthMiddleware, set_global_auth_middleware
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.middleware.rate_limiter import setup_rate_limiting
from mcp_server_langgraph.observability.telemetry import init_observability, logger


def create_app(settings_override: Settings | None = None, skip_startup_validation: bool = False) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        settings_override: Optional settings to use instead of global settings.
                          Useful for testing with custom configurations.
        skip_startup_validation: If True, skip database connectivity and startup validation.
                                Useful for unit tests that don't have infrastructure running.
                                Default: False (validation runs in production).

    Returns:
        FastAPI: Configured application instance

    Usage:
        # Production (uses global settings, runs validation)
        app = create_app()

        # Testing (uses custom settings, skips validation)
        test_settings = Settings(environment="test", ...)
        test_app = create_app(settings_override=test_settings, skip_startup_validation=True)
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
        raise RuntimeError(
            "Observability initialization failed! Logger still raises RuntimeError. "
            f"Error: {e}. This is a critical bug - logging will fail throughout the app."
        )

    app = FastAPI(
        title="MCP Server LangGraph API",
        version="2.8.0",
        description="Production-ready MCP server with LangGraph, OpenFGA, and multi-LLM support",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
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
    auth_middleware = AuthMiddleware(secret_key=config.jwt_secret_key, settings=config)
    set_global_auth_middleware(auth_middleware)  # Set global instance for dependency injection
    app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)
    try:
        logger.info("Auth request middleware enabled")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    # Rate limiting - setup function registers middleware and exception handlers
    setup_rate_limiting(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Include API routers
    app.include_router(health_router)  # Health check first (doesn't require auth)
    app.include_router(api_keys_router)
    app.include_router(service_principals_router)
    app.include_router(gdpr_router)
    app.include_router(scim_router)

    try:
        logger.info("FastAPI application created with all routers mounted")
    except RuntimeError:
        pass  # Graceful degradation if observability not initialized

    # Run startup validation to ensure all critical systems initialized correctly
    # This prevents the app from starting if any of the OpenAI Codex findings recur
    # Skip validation in unit tests (skip_startup_validation=True) to avoid DB dependency
    if not skip_startup_validation:
        try:
            run_startup_validation()
        except Exception as e:
            try:
                logger.critical(f"Startup validation failed: {e}")
            except RuntimeError:
                pass  # Graceful degradation if observability not initialized
            raise
    else:
        try:
            logger.debug("Skipping startup validation (test mode)")
        except RuntimeError:
            pass  # Graceful degradation if observability not initialized

    return app


# Create the application instance
# Skip validation when running under pytest to avoid DB dependency in unit tests
# This is detected via PYTEST_CURRENT_TEST environment variable set by pytest
_is_pytest_session = os.getenv("PYTEST_CURRENT_TEST") is not None
app = create_app(skip_startup_validation=_is_pytest_session)


@app.get("/health")  # type: ignore[misc]  # FastAPI decorator lacks complete type stubs
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server-langgraph"}


@app.get("/")  # type: ignore[misc]  # FastAPI decorator lacks complete type stubs
async def root() -> dict[str, str]:
    """Root endpoint with API information"""
    return {
        "service": "MCP Server LangGraph",
        "version": "2.8.0",
        "docs": "/api/docs",
        "health": "/health",
    }
