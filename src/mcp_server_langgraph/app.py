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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server_langgraph.api import api_keys_router, gdpr_router, scim_router, service_principals_router
from mcp_server_langgraph.api.error_handlers import register_exception_handlers
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.middleware.rate_limiter import setup_rate_limiting
from mcp_server_langgraph.observability.telemetry import init_observability, logger


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    # Initialize observability FIRST before any logging (OpenAI Codex Finding #2)
    # This prevents RuntimeError: "Observability not initialized" when logger is used
    init_observability(settings)

    app = FastAPI(
        title="MCP Server LangGraph API",
        version="2.8.0",
        description="Production-ready MCP server with LangGraph, OpenFGA, and multi-LLM support",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware - use settings configuration with environment-aware defaults
    # get_cors_origins() provides localhost origins in dev, empty list in production
    cors_origins = settings.get_cors_origins()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {cors_origins}")
    else:
        logger.info("CORS disabled (no allowed origins configured)")

    # Rate limiting - setup function registers middleware and exception handlers
    setup_rate_limiting(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Include API routers
    app.include_router(api_keys_router)
    app.include_router(service_principals_router)
    app.include_router(gdpr_router)
    app.include_router(scim_router)

    logger.info("FastAPI application created with all routers mounted")

    return app


# Create the application instance
app = create_app()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server-langgraph"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information"""
    return {
        "service": "MCP Server LangGraph",
        "version": "2.8.0",
        "docs": "/api/docs",
        "health": "/health",
    }
