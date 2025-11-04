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
from mcp_server_langgraph.api.error_handlers import register_error_handlers
from mcp_server_langgraph.middleware.rate_limiter import RateLimiter
from mcp_server_langgraph.observability.telemetry import logger


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="MCP Server LangGraph API",
        version="2.8.0",
        description="Production-ready MCP server with LangGraph, OpenFGA, and multi-LLM support",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware (configure allowed origins in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    app.add_middleware(RateLimiter)

    # Register error handlers
    register_error_handlers(app)

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
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server-langgraph"}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "MCP Server LangGraph",
        "version": "2.8.0",
        "docs": "/api/docs",
        "health": "/health",
    }
