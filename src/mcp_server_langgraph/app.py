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
from mcp_server_langgraph.middleware.audit import (
    AuditMiddleware,
    get_audit_service,
    set_audit_service,
)
from mcp_server_langgraph.audit.factory import create_audit_scheduler
from mcp_server_langgraph.audit.service import UnifiedAuditService
from mcp_server_langgraph.audit.compliance_service import ComplianceService
from mcp_server_langgraph.audit.repository import create_audit_repository
from mcp_server_langgraph.audit.retention_scheduler import create_retention_scheduler
from mcp_server_langgraph.audit.alerts import AuditAlertDetector
from mcp_server_langgraph.audit.config import load_alerting_config, create_notifiers_from_config
from mcp_server_langgraph.audit.notifications import NotificationRouter, create_notification_callback
from mcp_server_langgraph.api.v1.compliance_reports import set_compliance_service
from mcp_server_langgraph.api.v1.audit_websocket import set_audit_event_broadcaster
from mcp_server_langgraph.api.v1.notification_websocket import set_notification_broadcaster
from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster
from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
from mcp_server_langgraph.observability.telemetry import init_observability, logger


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
        # Run startup validation to ensure all critical systems initialized correctly
        # This prevents the app from starting if any of the OpenAI Codex findings recur
        # Skip validation in unit tests (skip_startup_validation=True) to avoid DB dependency
        if not skip_startup_validation:
            try:
                await run_startup_validation_async()
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

        # Initialize audit service (required for middleware and scheduler)
        # Uses PostgresUnifiedAuditRepository if database_url is configured (production)
        # Falls back to InMemoryUnifiedAuditRepository if not (development/testing)
        try:
            audit_repository = create_audit_repository(database_url=config.database_url)
            # Create broadcaster for real-time WebSocket streaming
            audit_broadcaster = AuditEventBroadcaster()

            # Create alert notification system (Slack/PagerDuty integration)
            alert_detector = None
            try:
                alerting_config = load_alerting_config()
                notifiers = create_notifiers_from_config(alerting_config)
                if notifiers:
                    notification_router = NotificationRouter(notifiers=notifiers)
                    notification_callback = create_notification_callback(notification_router)

                    # Create alert detector with configured thresholds
                    alert_detector = AuditAlertDetector(
                        failed_login_threshold=alerting_config.detection.failed_login.threshold,
                        failed_login_window_minutes=alerting_config.detection.failed_login.window_minutes,
                        business_hours_start=alerting_config.detection.after_hours_admin.end_hour,
                        business_hours_end=alerting_config.detection.after_hours_admin.start_hour,
                        bulk_export_threshold_records=alerting_config.detection.bulk_export.threshold_records,
                        alert_callback=notification_callback,
                    )
                    logger.info(f"Alert notification system initialized with {len(notifiers)} notifier(s)")
                else:
                    logger.info("No alert notifiers configured (Slack/PagerDuty webhooks not set)")
            except Exception as alert_config_error:
                logger.warning(f"Failed to initialize alert notifications: {alert_config_error}")

            audit_service_instance = UnifiedAuditService(
                repository=audit_repository,
                integrity_secret=config.audit_integrity_secret,
                broadcaster=audit_broadcaster,
                alert_detector=alert_detector,
            )
            set_audit_service(audit_service_instance)
            # Make broadcaster available to WebSocket endpoint
            set_audit_event_broadcaster(audit_broadcaster)
            logger.info("Audit service initialized successfully with WebSocket streaming")

            # Initialize notification broadcaster for real-time user notifications
            notification_broadcaster = NotificationBroadcaster()
            set_notification_broadcaster(notification_broadcaster)
            logger.info("Notification WebSocket broadcaster initialized")

            # Initialize compliance service (depends on audit service)
            compliance_service_instance = ComplianceService(
                audit_service=audit_service_instance,
            )
            set_compliance_service(compliance_service_instance)
            logger.info("Compliance service initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize audit service: {e}")

        # Start audit integrity scheduler if enabled (FedRAMP AU-9 compliance)
        audit_scheduler = None
        if config.audit_scheduler_enabled:
            audit_service = get_audit_service()
            if audit_service is not None:
                try:
                    audit_scheduler = create_audit_scheduler(
                        audit_service=audit_service,
                        schedule_hours=config.audit_scheduler_hours,
                    )
                    await audit_scheduler.start()
                    logger.info(f"Audit integrity scheduler started (every {config.audit_scheduler_hours} hours)")
                except Exception as e:
                    logger.warning(f"Failed to start audit scheduler: {e}")
            else:
                logger.warning("Audit scheduler enabled but no audit service configured - skipping")

        # Start partition retention scheduler if enabled (FedRAMP AU-11 compliance)
        retention_scheduler = None
        if config.partition_retention_enabled:
            try:
                retention_scheduler = create_retention_scheduler(
                    retention_months=config.partition_retention_months,
                    schedule_hours=config.partition_retention_hours,
                )
                await retention_scheduler.start()
                logger.info(
                    f"Partition retention scheduler started "
                    f"(retention={config.partition_retention_months} months, "
                    f"interval={config.partition_retention_hours} hours)"
                )
            except Exception as e:
                logger.warning(f"Failed to start retention scheduler: {e}")

        yield

        # Stop retention scheduler gracefully on shutdown
        if retention_scheduler is not None:
            try:
                await retention_scheduler.stop()
                logger.info("Partition retention scheduler stopped")
            except Exception as e:
                logger.warning(f"Error stopping retention scheduler: {e}")

        # Stop audit scheduler gracefully on shutdown
        if audit_scheduler is not None:
            try:
                audit_scheduler.stop()  # sync method, no await needed
                logger.info("Audit integrity scheduler stopped")
            except Exception as e:
                logger.warning(f"Error stopping audit scheduler: {e}")

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
    set_global_auth_middleware(auth_middleware)  # Set global instance for dependency injection
    app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)
    try:
        logger.info("Auth request middleware enabled")
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
