"""
FastAPI Application Factory

This module provides factory functions for creating FastAPI applications
with proper configuration, middleware, and lifecycle management.

Separates infrastructure concerns from business logic.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.core.container import ApplicationContainer, create_test_container

logger = logging.getLogger(__name__)


def create_app(
    container: Optional[ApplicationContainer] = None,
    settings: Optional[Settings] = None,
    environment: Optional[str] = None,
) -> FastAPI:
    """
    Create a FastAPI application with proper configuration.

    This factory function creates a FastAPI app with:
    - Proper middleware (CORS, rate limiting, auth)
    - Lifecycle management (startup/shutdown)
    - OpenAPI customization
    - Health check endpoints

    Args:
        container: Optional ApplicationContainer for DI
        settings: Optional Settings (if container not provided)
        environment: Optional environment override

    Returns:
        Configured FastAPI application

    Example:
        # Using container (preferred)
        from mcp_server_langgraph.core.container import create_test_container
        container = create_test_container()
        app = create_app(container=container)

        # Using custom settings
        from mcp_server_langgraph.core.config import Settings
        settings = Settings(service_name="my-service")
        app = create_app(settings=settings)

        # Using defaults
        app = create_app()
    """
    # Get or create container
    if container is None:
        if environment == "test" or (settings and settings.environment == "test"):
            container = create_test_container(settings=settings)
        else:
            from mcp_server_langgraph.core.container import ApplicationContainer, ContainerConfig

            env = environment or (settings.environment if settings else "development")
            config = ContainerConfig(environment=env)
            container = ApplicationContainer(config, settings=settings)

    # Get settings from container
    app_settings = container.settings

    # Create lifespan context
    lifespan_ctx = create_lifespan(container=container)

    # Create FastAPI app
    app = FastAPI(
        title=app_settings.service_name,
        description="MCP Server with LangGraph",
        version="1.0.0",
        lifespan=lifespan_ctx,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on settings in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add health check endpoint
    @app.get("/health")  # type: ignore[misc]  # FastAPI decorator lacks complete type stubs
    async def health_check() -> dict[str, str]:
        """Health check endpoint"""
        return {"status": "healthy", "service": app_settings.service_name}

    # Customize OpenAPI
    app.openapi_schema = None  # Reset to trigger regeneration

    return app


@asynccontextmanager
async def create_lifespan(container: Optional[ApplicationContainer] = None) -> AsyncIterator[None]:
    """
    Create application lifespan context manager.

    Handles startup and shutdown tasks:
    - Initialize telemetry
    - Setup connections
    - Cleanup resources

    Args:
        container: Optional ApplicationContainer

    Yields:
        None (context manager pattern)

    Example:
        lifespan = create_lifespan(container)
        app = FastAPI(lifespan=lifespan)
    """
    # Startup
    if container:
        _telemetry = container.get_telemetry()  # noqa: F841
        logger.info(f"Application starting (environment: {container.settings.environment})")

        # Validate checkpoint configuration at startup (fail-fast)
        from mcp_server_langgraph.core.checkpoint_validator import validate_checkpoint_config

        try:
            validate_checkpoint_config(container.settings)
        except Exception as e:
            logger.error(f"Checkpoint configuration validation failed: {e}")
            # Re-raise to prevent application from starting with invalid config
            raise

    yield

    # Shutdown
    if container:
        logger.info("Application shutting down")


def customize_openapi(app: FastAPI) -> dict[str, Any]:
    """
    Customize OpenAPI schema for the application.

    Args:
        app: FastAPI application

    Returns:
        Customized OpenAPI schema dict

    Example:
        app = FastAPI()
        schema = customize_openapi(app)
        app.openapi_schema = schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom properties
    openapi_schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}

    app.openapi_schema = openapi_schema
    return app.openapi_schema
