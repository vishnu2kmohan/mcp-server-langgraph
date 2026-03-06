"""
FastAPI Application Factory

This module provides factory functions for creating FastAPI applications
with proper configuration, middleware, and lifecycle management.

Separates infrastructure concerns from business logic.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.core.container import ApplicationContainer, create_test_container
from mcp_server_langgraph.llm.otel_integration import configure_litellm_cost_tracking

logger = logging.getLogger(__name__)


def create_app(
    container: ApplicationContainer | None = None,
    settings: Settings | None = None,
    environment: str | None = None,
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

    # Create lifespan wrapper to inject container
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with create_lifespan(container=container):
            yield

    # Create FastAPI app
    app = FastAPI(
        title=app_settings.service_name,
        description="MCP Server with LangGraph",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on settings in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add DevTools network event middleware for real-time debugging
    from mcp_server_langgraph.middleware.devtools_emitter import DevToolsNetworkMiddleware

    app.add_middleware(DevToolsNetworkMiddleware)

    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint"""
        return {"status": "healthy", "service": app_settings.service_name}

    # Customize OpenAPI
    app.openapi_schema = None  # Reset to trigger regeneration

    return app


@asynccontextmanager
async def create_lifespan(container: ApplicationContainer | None = None) -> AsyncIterator[None]:
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

    # Configure LiteLLM cost tracking callback (idempotent, safe to call multiple times)
    # This enables automatic cost recording on every LLM call via LiteLLM's callback system
    configure_litellm_cost_tracking()
    logger.info("LiteLLM cost tracking callback registered")

    if container:
        _telemetry = container.get_telemetry()
        logger.info(f"Application starting (environment: {container.settings.environment})")

        # Validate checkpoint configuration at startup (fail-fast)
        from mcp_server_langgraph.core.checkpoint_validator import validate_checkpoint_config

        try:
            validate_checkpoint_config(container.settings)
        except Exception as e:
            logger.exception(f"Checkpoint configuration validation failed: {e}")
            # Re-raise to prevent application from starting with invalid config
            raise

        # Initialize compliance storage at startup (fail-fast)
        # Supports GDPR, HIPAA, SOC2, and FedRAMP compliance frameworks
        from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage

        try:
            logger.info(f"Initializing compliance storage (backend: {container.settings.compliance_storage_backend})")
            await initialize_gdpr_storage(
                backend=container.settings.compliance_storage_backend,  # type: ignore[arg-type]
                postgres_url=container.settings.compliance_postgres_url,
            )
            logger.info("Compliance storage initialized successfully")
        except Exception as e:
            logger.exception(f"Compliance storage initialization failed: {e}")
            # Re-raise to prevent application from starting without compliance storage
            raise

        # Initialize Push Notification Sender (optional, only if VAPID keys configured)
        # ADR-0026: Web Push API for critical alerts
        vapid_keys_configured = (
            container.settings.vapid_public_key
            and container.settings.vapid_private_key
            and container.settings.vapid_claims_email  # Also require email for valid VAPID claims
        )
        if vapid_keys_configured:
            from mcp_server_langgraph.websocket.registry import get_alert_broadcaster
            from mcp_server_langgraph.api.v1.notifications import set_push_subscription_store
            from mcp_server_langgraph.notifications.push_sender import PushNotificationSender
            from mcp_server_langgraph.notifications.push_store import (
                InMemoryPushSubscriptionStore,
                PostgresPushSubscriptionStore,
                PushSubscriptionStore,
            )

            try:
                # Create push subscription store - use PostgreSQL in production/staging
                push_store: PushSubscriptionStore
                is_production = container.settings.environment in ("production", "staging")
                has_database = bool(container.settings.database_url)

                if is_production and has_database:
                    from mcp_server_langgraph.database.session import get_session_maker

                    session_maker = get_session_maker(container.settings.database_url)
                    push_store = PostgresPushSubscriptionStore(session_maker)
                    logger.info("Using PostgreSQL push subscription store (production)")
                else:
                    push_store = InMemoryPushSubscriptionStore()
                    logger.info("Using in-memory push subscription store (development/test)")

                # Wire the push store to the notifications API for DI
                set_push_subscription_store(push_store)

                # Create push notification sender with VAPID credentials
                push_sender = PushNotificationSender(
                    vapid_private_key=container.settings.vapid_private_key,
                    vapid_public_key=container.settings.vapid_public_key,
                    vapid_claims={"sub": f"mailto:{container.settings.vapid_claims_email}"},
                    subscription_store=push_store,
                )

                # Wire push sender to alert broadcaster
                broadcaster = get_alert_broadcaster()
                broadcaster._push_sender = push_sender

                logger.info("Push notification sender initialized successfully")
            except Exception as e:
                logger.warning(f"Push notification sender initialization failed: {e}")
                # Non-fatal: alerts will still work via WebSocket without push notifications
        else:
            logger.debug("VAPID keys not configured, push notifications disabled")

        # Initialize Feedback Store for AI Model Tuning (Phase 8)
        # ADR-0026: Few-shot learning and constraint learning from remediation feedback
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            PostgresFeedbackStore,
            FeedbackStore,
        )
        from mcp_server_langgraph.api.v1.remediation_approvals import set_feedback_store

        try:
            feedback_store: FeedbackStore
            is_production = container.settings.environment in ("production", "staging")
            has_database = bool(container.settings.database_url)

            if is_production and has_database:
                from mcp_server_langgraph.database.session import get_session_maker

                session_maker = get_session_maker(container.settings.database_url)
                feedback_store = PostgresFeedbackStore(session_maker)
                logger.info("Using PostgreSQL feedback store (production)")
            else:
                feedback_store = InMemoryFeedbackStore()
                logger.info("Using in-memory feedback store (development/test)")

            # Wire the feedback store to the remediation approvals API for DI
            set_feedback_store(feedback_store)
            logger.info("Feedback store initialized successfully")
        except Exception as e:
            logger.warning(f"Feedback store initialization failed: {e}")
            # Non-fatal: remediations will work but AI learning will be disabled

        # Initialize Budget Storage for cost management
        # Uses PostgreSQL in production/staging, in-memory for development/test
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            PostgresBudgetStorage,
            set_budget_storage,
        )

        try:
            is_production = container.settings.environment in ("production", "staging")
            has_database = bool(container.settings.database_url)

            if is_production and has_database:
                from mcp_server_langgraph.database.session import get_session_maker

                session_maker = get_session_maker(container.settings.database_url)
                budget_store = PostgresBudgetStorage(session_maker)
                logger.info("Using PostgreSQL budget storage (production)")
            else:
                budget_store = MemoryBudgetStorage()
                logger.info("Using in-memory budget storage (development/test)")

            set_budget_storage(budget_store)
            logger.info("Budget storage initialized successfully")
        except Exception as e:
            logger.warning(f"Budget storage initialization failed: {e}")
            # Non-fatal: budget endpoints will use default in-memory storage

        # Initialize Artifacts Service (optional, feature-flagged)
        # ADR: Multi-layer storage for Canvas artifacts (PostgreSQL + Redis + Cloud + Qdrant)
        from mcp_server_langgraph.core.feature_flags import get_feature_flags

        feature_flags = get_feature_flags()
        if feature_flags.enable_interactive_artifacts:
            from mcp_server_langgraph.api.v1.artifacts import set_artifacts_service
            from mcp_server_langgraph.storage.artifacts import create_artifacts_service

            try:
                has_database = bool(container.settings.database_url)
                has_redis = bool(container.settings.redis_url)

                if has_database and has_redis:
                    from redis.asyncio import Redis
                    from mcp_server_langgraph.database.session import get_session_maker

                    session_maker = get_session_maker(container.settings.database_url)
                    redis_client = Redis.from_url(container.settings.redis_url)

                    artifacts_service = create_artifacts_service(
                        db_session_factory=session_maker,
                        redis_client=redis_client,
                        cloud_provider=getattr(container.settings, "artifacts_cloud_provider", "s3"),
                        content_size_threshold=getattr(container.settings, "artifacts_content_size_threshold", 100_000),
                        qdrant_enabled=bool(container.settings.qdrant_url),
                        qdrant_url=container.settings.qdrant_url if container.settings.qdrant_url != "localhost" else None,
                    )

                    set_artifacts_service(artifacts_service)  # type: ignore[arg-type]
                    logger.info("Artifacts service initialized (PostgreSQL + Redis + Cloud + Qdrant)")
                else:
                    # Use in-memory service for development/testing
                    logger.info("Using in-memory artifacts service (database/redis not configured)")
            except Exception as e:
                logger.warning(f"Artifacts service initialization failed: {e}")
                # Non-fatal: will fall back to in-memory service
        else:
            logger.debug("Interactive artifacts feature flag disabled, using in-memory service")

        # Initialize observability query clients (Grafana, Tempo, Loki, Prometheus)
        # Required for /api/v1/observability/* endpoints
        from mcp_server_langgraph.observability.query.factory import init_query_clients

        try:
            await init_query_clients()
            logger.info("Observability query clients initialized successfully")
        except Exception as e:
            logger.warning(f"Observability query clients initialization failed: {e}")
            # Non-fatal: observability endpoints will fail gracefully

        # Wire MCP aggregated broadcaster to cached unified registry
        # Enables real-time capability change notifications via WebSocket
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            get_cached_unified_registry,
        )
        from mcp_server_langgraph.websocket.registry import get_mcp_aggregated_broadcaster

        try:
            cached_registry = get_cached_unified_registry()
            mcp_broadcaster = get_mcp_aggregated_broadcaster()
            cached_registry.set_broadcaster(mcp_broadcaster)
            logger.info("MCP aggregated broadcaster wired to cached registry")
        except Exception as e:
            logger.warning(f"MCP aggregated broadcaster wiring failed: {e}")
            # Non-fatal: capability changes won't be broadcast to WebSocket clients

        # Configure LiteLLM OTEL callback (cost tracking already configured above)
        # Uses LiteLLM's response_cost as authoritative source for cost calculation
        from mcp_server_langgraph.llm.otel_integration import configure_litellm_otel

        try:
            configure_litellm_otel()
            logger.info("LiteLLM OTEL callback configured")
        except Exception as e:
            logger.warning(f"LiteLLM OTEL callback configuration failed: {e}")
            # Non-fatal: tracing will be disabled

        # NOTE: MCP sync + semantic indexing moved to app.py lifespan (v26)
        # See: sync_mcp_tools() + index_all_tools() in app.py

        # Initialize Plan Repositories (Phase 6: pgvector Pool at App Startup)
        # Supports PostgreSQL with pgvector for semantic search or in-memory for testing
        from mcp_server_langgraph.repositories.execution_plan import (
            InMemoryExecutionPlanRepository,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )
        from mcp_server_langgraph.api.v1.execution_plans import (
            set_plan_repo,
            set_template_repo,
        )

        try:
            use_postgres = container.settings.plan_storage_backend == "postgres"
            has_database = bool(container.settings.database_url)

            if use_postgres and has_database:
                from mcp_server_langgraph.database.session import get_session_maker
                from mcp_server_langgraph.repositories.postgres_execution_plan import (
                    PostgresExecutionPlanRepository,
                )
                from mcp_server_langgraph.repositories.postgres_plan_template import (
                    PostgresPlanTemplateRepository,
                )

                session_maker = get_session_maker(container.settings.database_url)

                # Create a context manager factory for session
                @asynccontextmanager
                async def session_factory():
                    async with session_maker() as session:
                        yield session

                execution_plan_repo = PostgresExecutionPlanRepository(session_factory)
                plan_template_repo = PostgresPlanTemplateRepository(session_factory)
                logger.info("Using PostgreSQL plan repositories with pgvector (production)")
            else:
                execution_plan_repo = InMemoryExecutionPlanRepository()
                plan_template_repo = InMemoryPlanTemplateRepository()
                logger.info("Using in-memory plan repositories (development/test)")

            # Wire repositories to DI
            set_plan_repo(execution_plan_repo)
            set_template_repo(plan_template_repo)
            logger.info("Plan repositories initialized successfully")

            # Initialize embedding service for background processing (Phase 7)
            try:
                import asyncio
                from mcp_server_langgraph.services.plan_embedding_service import (
                    PlanEmbeddingService,
                    set_embedding_service_instance,
                )

                embedding_service = PlanEmbeddingService(
                    execution_plan_repo=execution_plan_repo,
                    plan_template_repo=plan_template_repo,
                )
                set_embedding_service_instance(embedding_service)
                # Start background processing task (stored in service for shutdown)
                embedding_service._task = asyncio.create_task(
                    embedding_service.start_background_processing(),
                    name="plan_embedding_bg",
                )
                logger.info("Plan embedding service initialized and background processing started")
            except Exception as e:
                logger.warning(f"Plan embedding service initialization failed: {e}")
                # Non-fatal: embeddings will be skipped but core functionality works
        except Exception as e:
            logger.warning(f"Plan repository initialization failed: {e}")
            # Fallback to in-memory
            set_plan_repo(InMemoryExecutionPlanRepository())
            set_template_repo(InMemoryPlanTemplateRepository())
            logger.info("Falling back to in-memory plan repositories")

    yield

    # Shutdown
    if container:
        logger.info("Application shutting down")

        # Reset stores on shutdown to ensure clean state for testing
        from mcp_server_langgraph.api.v1.artifacts import set_artifacts_service
        from mcp_server_langgraph.api.v1.notifications import set_push_subscription_store
        from mcp_server_langgraph.api.v1.remediation_approvals import set_feedback_store
        from mcp_server_langgraph.api.v1.execution_plans import reset_plan_repo, reset_template_repo
        from mcp_server_langgraph.compliance.gdpr.factory import reset_gdpr_storage
        from mcp_server_langgraph.monitoring.budget_storage import set_budget_storage

        set_push_subscription_store(None)
        set_feedback_store(None)
        set_artifacts_service(None)
        set_budget_storage(None)
        reset_gdpr_storage()
        reset_plan_repo()
        reset_template_repo()

        # Stop embedding service background task
        from mcp_server_langgraph.services.plan_embedding_service import (
            get_embedding_service_instance,
            set_embedding_service_instance,
        )

        embedding_service = get_embedding_service_instance()
        if embedding_service:
            embedding_service.stop_background_processing()
            set_embedding_service_instance(None)

        # Reset MCP aggregated broadcaster
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            reset_cached_unified_registry,
        )
        from mcp_server_langgraph.websocket.registry import set_mcp_aggregated_broadcaster

        set_mcp_aggregated_broadcaster(None)
        reset_cached_unified_registry()

        # Reset unified tool registry (v7)
        from mcp_server_langgraph.tools.unified_registry import invalidate_registry

        invalidate_registry()

        # Close observability query clients
        from mcp_server_langgraph.observability.query.factory import close_query_clients

        try:
            await close_query_clients()
            logger.info("Observability query clients closed")
        except Exception as e:
            logger.warning(f"Error closing observability query clients: {e}")

        # Cleanup all centralized service clients (PostgreSQL registry, CacheService, Qdrant)
        # This handles the URL-keyed engine registry and shared clients
        try:
            from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

            await cleanup_all_clients()
        except Exception as e:
            logger.warning(f"Error in centralized client cleanup: {e}")

        # Reset LiteLLM callbacks
        from mcp_server_langgraph.llm.otel_integration import (
            reset_cost_tracking_configuration,
            reset_otel_configuration,
        )

        reset_cost_tracking_configuration()
        reset_otel_configuration()

        logger.info(
            "Stores reset (push subscriptions, feedback, artifacts, budget, GDPR, observability, MCP broadcaster, LiteLLM callbacks)"
        )


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
    from typing import cast

    if app.openapi_schema:
        return cast(dict[str, Any], app.openapi_schema)  # type: ignore[redundant-cast]

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
    return cast(dict[str, Any], app.openapi_schema)  # type: ignore[redundant-cast]
