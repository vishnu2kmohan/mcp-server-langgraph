"""
FastAPI Dependencies

Provides dependency injection for commonly used services.
"""

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.langgraph_execution_trace import (
        LangGraphExecutionTraceRepositoryBase,
    )
    from mcp_server_langgraph.repositories.session_goal import SessionGoalRepository

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.auth.api_keys import APIKeyManager
from mcp_server_langgraph.auth.keycloak import KeycloakClient, TokenValidator
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager
from mcp_server_langgraph.auth.token_denylist import TokenDenylist, create_token_denylist
from mcp_server_langgraph.auth.user_provider import UserProvider
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.repositories.audit_log import AuditLogRepository
from mcp_server_langgraph.repositories.connections import (
    ConnectionRepository,
    PostgresConnectionRepository,
)
from mcp_server_langgraph.repositories.projects import PostgresProjectRepository
from mcp_server_langgraph.storage.base import ProjectRepository

# HTTP client for connection pooling
import httpx

from mcp_server_langgraph.core.http_client import HttpClientManager

logger = logging.getLogger(__name__)

# Singleton instances (will be initialized on first use)
_keycloak_client: KeycloakClient | None = None
_openfga_client: OpenFGAClient | None = None
_token_validator: TokenValidator | None = None
_service_principal_manager: ServicePrincipalManager | None = None
_api_key_manager: APIKeyManager | None = None
_user_provider: UserProvider | None = None
_token_denylist: TokenDenylist | None = None
_semantic_index_manager: Any = None  # SemanticIndexManager | None


def get_keycloak_client() -> KeycloakClient:
    """Get Keycloak client instance (singleton)"""
    global _keycloak_client

    if _keycloak_client is None:
        from mcp_server_langgraph.auth.keycloak import KeycloakConfig

        keycloak_config = KeycloakConfig(
            server_url=settings.keycloak_server_url,
            realm=settings.keycloak_realm,
            admin_realm=settings.keycloak_admin_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            admin_username=settings.keycloak_admin_username,
            admin_password=settings.keycloak_admin_password,
        )
        _keycloak_client = KeycloakClient(config=keycloak_config)

    return _keycloak_client


def get_token_validator() -> TokenValidator | None:
    """
    Get Keycloak TokenValidator instance (singleton).

    Returns None if Keycloak is not configured (auth_provider != 'keycloak').
    This allows graceful degradation for non-Keycloak deployments.

    Returns:
        TokenValidator instance for JWT validation, or None if not configured.
    """
    global _token_validator

    if _token_validator is None:
        # Only create validator for Keycloak auth
        if settings.auth_provider.lower() != "keycloak":
            logger.debug(f"Token validator not created: auth_provider is '{settings.auth_provider}', not 'keycloak'")
            return None

        from mcp_server_langgraph.auth.keycloak import KeycloakConfig

        keycloak_config = KeycloakConfig(
            server_url=settings.keycloak_server_url,
            public_url=settings.keycloak_public_url,
            realm=settings.keycloak_realm,
            admin_realm=settings.keycloak_admin_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            admin_username=settings.keycloak_admin_username,
            admin_password=settings.keycloak_admin_password,
        )
        _token_validator = TokenValidator(config=keycloak_config)
        logger.info("Keycloak TokenValidator initialized for JWT validation")

    return _token_validator


def get_openfga_client() -> OpenFGAClient | None:
    """
    Get OpenFGA client instance (singleton)

    Returns None if OpenFGA is not fully configured:
    - Either store_id or store_name must be set (store_name enables dynamic lookup)
    - model_id is optional (can be fetched from latest model)

    This allows graceful degradation when OpenFGA is intentionally disabled.
    """
    global _openfga_client

    if _openfga_client is None:
        from mcp_server_langgraph.auth.openfga import OpenFGAConfig
        from mcp_server_langgraph.observability.telemetry import logger

        # Validate that required configuration is present
        # Either store_id or store_name must be set (store_name enables dynamic lookup)
        has_store_config = settings.openfga_store_id or settings.openfga_store_name
        if not has_store_config:
            logger.warning(
                "OpenFGA configuration incomplete - authorization will be degraded. "
                f"store_id: {settings.openfga_store_id}, store_name: {settings.openfga_store_name}. "
                "Set OPENFGA_STORE_ID or OPENFGA_STORE_NAME environment variable to enable OpenFGA."
            )
            return None

        # Construct OIDC issuer URL from settings if not explicitly provided
        # Use openfga_oidc_issuer if set (required in Docker for gateway routing)
        # Otherwise, construct from keycloak_server_url (works for local development)
        oidc_issuer = settings.openfga_oidc_issuer
        if not oidc_issuer and settings.openfga_oidc_client_id and settings.openfga_oidc_client_secret:
            oidc_issuer = f"{settings.keycloak_server_url.rstrip('/')}/realms/{settings.keycloak_realm}"

        openfga_config = OpenFGAConfig(
            api_url=settings.openfga_api_url,
            store_id=settings.openfga_store_id,
            store_name=settings.openfga_store_name,
            model_id=settings.openfga_model_id,
            # OIDC authentication (recommended for production)
            oidc_client_id=settings.openfga_oidc_client_id,
            oidc_client_secret=settings.openfga_oidc_client_secret,
            oidc_issuer=oidc_issuer,
            # Legacy preshared key (deprecated, fallback if OIDC not configured)
            preshared_key=settings.openfga_preshared_key,
        )
        _openfga_client = OpenFGAClient(config=openfga_config)

    return _openfga_client


def get_openfga_client_from_request(request: Request) -> OpenFGAClient | None:
    """
    Get OpenFGA client from FastAPI request state (async-initialized pattern).

    This is the preferred way to access OpenFGA client in FastAPI routes.
    The client is initialized once during app lifespan startup and stored
    in app.state.openfga_client.

    Benefits over the sync singleton pattern:
    - Cold start latency eliminated (init at startup, not first request)
    - Proper async initialization (uses await, no event loop issues)
    - Fail-fast behavior (errors at startup, not runtime)
    - Request-scoped access pattern (proper FastAPI idiom)

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        OpenFGAClient if configured and initialized, None otherwise

    Example:
        @router.get("/resource")
        async def get_resource(
            openfga: OpenFGAClient = Depends(get_openfga_client_from_request),
        ):
            if openfga:
                allowed = await openfga.check_permission(...)
    """
    return getattr(request.app.state, "openfga_client", None)


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Get shared HTTP client from FastAPI request state.

    This provides access to the shared httpx.AsyncClient with HTTP/2 and
    connection pooling initialized at app startup. Use this for making
    HTTP requests in FastAPI routes instead of creating new clients.

    Benefits:
    - Connection reuse (HTTP/2 multiplexing, keep-alive)
    - Reduced connection overhead (~100ms saved per request)
    - Centralized connection pool limits and configuration
    - Proper cleanup on app shutdown

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        Shared httpx.AsyncClient instance

    Raises:
        RuntimeError: If HTTP client manager not initialized

    Example:
        @router.get("/external-data")
        async def fetch_external_data(
            http_client: httpx.AsyncClient = Depends(get_http_client),
        ):
            response = await http_client.get("https://api.example.com/data")
            return response.json()
    """
    http_client_manager: HttpClientManager | None = getattr(request.app.state, "http_client_manager", None)
    if http_client_manager is None:
        msg = "HTTP client manager not initialized. Ensure app lifespan is configured."
        raise RuntimeError(msg)

    return await http_client_manager.get_client()


def validate_production_auth_config(settings_obj: Settings) -> None:
    """
    Validate that production deployments have proper authorization configured.

    SECURITY: This function prevents production deployments from running with degraded
    authorization when OpenFGA is not configured and fallback is disabled.

    Implements remediation for OpenAI Codex Finding #1: Authorization Degradation

    Args:
        settings_obj: Settings object to validate

    Raises:
        RuntimeError: If production environment lacks required authorization infrastructure

    References:
        - tests/security/test_authorization_fallback_controls.py
        - CWE-862: Missing Authorization
    """
    if settings_obj.environment != "production":
        # Only enforce for production environment
        return

    # Check if OpenFGA is configured
    openfga_configured = bool(settings_obj.openfga_store_id and settings_obj.openfga_model_id)

    # Check if fallback is allowed
    allow_fallback = getattr(settings_obj, "allow_auth_fallback", False)

    # Production MUST have either:
    # 1. OpenFGA properly configured, OR
    # 2. Fallback explicitly disabled (fail-closed)
    if not openfga_configured and not allow_fallback:
        # This is the secure configuration - production with no OpenFGA will deny all auth requests
        # This is intentional fail-closed behavior
        from mcp_server_langgraph.observability.telemetry import logger

        logger.warning(
            "Production deployment without OpenFGA will deny all authorization requests. "
            "This is secure fail-closed behavior. Configure OpenFGA for production use.",
            extra={
                "environment": settings_obj.environment,
                "openfga_configured": openfga_configured,
                "allow_auth_fallback": allow_fallback,
            },
        )
        # This is actually a valid secure configuration, so we'll allow it
        # The authorization will just deny everything, which is secure
        return

    if not openfga_configured and allow_fallback:
        # SECURITY ERROR: Production with fallback enabled but no OpenFGA
        msg = (
            "SECURITY ERROR: Production deployment requires OpenFGA authorization infrastructure. "
            f"OpenFGA is not configured (store_id: {settings_obj.openfga_store_id}, "
            f"model_id: {settings_obj.openfga_model_id}) but ALLOW_AUTH_FALLBACK=true. "
            "This configuration would allow degraded role-based authorization in production. "
            "Either: (1) Configure OpenFGA properly, or (2) Set ALLOW_AUTH_FALLBACK=false to fail-closed."
        )
        raise RuntimeError(msg)


def get_service_principal_manager(
    keycloak: KeycloakClient = Depends(get_keycloak_client),
    openfga: OpenFGAClient | None = Depends(get_openfga_client_from_request),
) -> ServicePrincipalManager:
    """
    Get ServicePrincipalManager instance

    Args:
        keycloak: Keycloak client (injected)
        openfga: OpenFGA client from request state (injected)

    Returns:
        ServicePrincipalManager instance
    """
    global _service_principal_manager

    if _service_principal_manager is None:
        _service_principal_manager = ServicePrincipalManager(
            keycloak_client=keycloak,
            openfga_client=openfga,
        )

    return _service_principal_manager


def get_api_key_manager(
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> APIKeyManager:
    """
    Get APIKeyManager instance with Redis caching if enabled

    Args:
        keycloak: Keycloak client (injected)

    Returns:
        APIKeyManager instance configured with Redis cache if settings.api_key_cache_enabled=True
    """
    global _api_key_manager

    if _api_key_manager is None:
        # Wire Redis client for API key caching if enabled (OpenAI Codex Finding #5)
        # IMPORTANT: This Redis client must be passed to APIKeyManager or caching will be disabled
        # Settings used:
        #   - api_key_cache_enabled: Enable/disable caching
        #   - api_key_cache_db: Redis database number (default: 2)
        #   - api_key_cache_ttl: Cache TTL in seconds (default: 3600)
        #   - redis_url: Redis connection URL
        #   - redis_password: Redis password (optional)
        #   - redis_ssl: Use SSL for Redis connection (default: False)
        redis_client: Any | None = None
        if settings.api_key_cache_enabled and settings.redis_url:
            try:
                from urllib.parse import urlparse, urlunparse

                import redis.asyncio as redis

                # Build Redis URL with correct database number
                # Parse the URL to handle existing database numbers, trailing slashes, query params
                parsed = urlparse(settings.redis_url)

                # Remove existing database number from path (if present)
                # Redis URL path is typically empty or /db_number
                # We'll replace it with the configured database number
                new_path = f"/{settings.api_key_cache_db}"

                # Reconstruct URL with new database number
                redis_url_with_db = urlunparse(
                    (
                        parsed.scheme,  # redis:// or rediss://
                        parsed.netloc,  # host:port
                        new_path,  # /db_number
                        parsed.params,  # unused in Redis URLs
                        parsed.query,  # query parameters (if any)
                        parsed.fragment,  # fragment (if any)
                    )
                )

                # Create Redis client with configured credentials
                redis_client = redis.from_url(  # type: ignore[no-untyped-call]
                    redis_url_with_db,
                    password=settings.redis_password,
                    ssl=settings.redis_ssl,
                    decode_responses=True,
                )
            except ImportError:
                # Redis not installed, disable caching gracefully
                redis_client = None

        _api_key_manager = APIKeyManager(
            keycloak_client=keycloak,
            redis_client=redis_client,
            cache_ttl=settings.api_key_cache_ttl,
            cache_enabled=settings.api_key_cache_enabled,
        )

        # Validation: Ensure cache is actually enabled if requested (prevent regression)
        if settings.api_key_cache_enabled and settings.redis_url and not _api_key_manager.cache_enabled:
            msg = (
                "API key caching configuration error! "
                f"settings.api_key_cache_enabled=True but APIKeyManager.cache_enabled=False. "
                f"Redis client: {redis_client}. "
                "This indicates Redis client was not properly wired."
            )
            raise RuntimeError(msg)

    return _api_key_manager


def get_user_provider() -> UserProvider:
    """
    Get UserProvider instance (singleton).

    Creates an InMemoryUserProvider for development/testing or
    KeycloakUserProvider for production based on configuration.

    Returns:
        UserProvider instance

    Example:
        @router.get("/admin/users")
        async def list_users(
            provider: UserProvider = Depends(get_user_provider),
        ):
            return await provider.list_users()
    """
    global _user_provider

    if _user_provider is None:
        from mcp_server_langgraph.auth.user_provider import (
            InMemoryUserProvider,
            KeycloakUserProvider,
        )
        from mcp_server_langgraph.auth.keycloak import KeycloakConfig

        # Use Keycloak if configured, otherwise fall back to InMemory
        if settings.keycloak_server_url and settings.keycloak_realm:
            keycloak_config = KeycloakConfig(
                server_url=settings.keycloak_server_url,
                realm=settings.keycloak_realm,
                admin_realm=settings.keycloak_admin_realm,
                client_id=settings.keycloak_client_id,
                client_secret=settings.keycloak_client_secret,
                admin_username=settings.keycloak_admin_username,
                admin_password=settings.keycloak_admin_password,
            )
            openfga_client = get_openfga_client()
            _user_provider = KeycloakUserProvider(
                config=keycloak_config,
                openfga_client=openfga_client,
            )
        else:
            # Development mode - use InMemory provider
            _user_provider = InMemoryUserProvider()

    return _user_provider


def get_token_denylist() -> TokenDenylist:
    """
    Get TokenDenylist instance (singleton).

    Creates an InMemoryTokenDenylist for development or RedisTokenDenylist
    for production based on session_backend configuration.

    Per OWASP: Token denylist enables immediate JWT revocation on logout,
    preventing tokens from being used after explicit session termination.

    Returns:
        TokenDenylist instance

    Example:
        @router.post("/logout")
        async def logout(
            token: str = Depends(get_bearer_token),
            denylist: TokenDenylist = Depends(get_token_denylist),
        ):
            # Add token to denylist
            await denylist.add(token_jti, token_expires_at)
    """
    global _token_denylist

    if _token_denylist is None:
        # Use Redis if session_backend is redis, otherwise use in-memory
        if settings.session_backend == "redis":
            import redis.asyncio as redis

            # Use same Redis URL as sessions for consistency
            redis_client = redis.from_url(  # type: ignore[no-untyped-call]
                settings.redis_url, decode_responses=True
            )
            _token_denylist = create_token_denylist(
                backend="redis",
                redis_client=redis_client,
                key_prefix="token_denylist:",
            )
        else:
            # Development mode - use in-memory denylist
            _token_denylist = create_token_denylist(backend="memory")

    return _token_denylist


# ==============================================================================
# Semantic Index Manager (ADR-0099)
# ==============================================================================


def get_semantic_index_manager() -> Any:
    """
    Get SemanticIndexManager instance (singleton).

    Returns the cached SemanticIndexManager for semantic tool/skill/memory search.
    Returns None if not initialized (call set_semantic_index_manager during startup).

    ADR-0099: Semantic Tool Selection for Dynamic Capability Discovery

    Returns:
        SemanticIndexManager instance or None if not initialized

    Example:
        # In bootstrap/lifespan
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(embedder=..., qdrant_client=...)
        set_semantic_index_manager(manager)

        # Later in code
        manager = get_semantic_index_manager()
        if manager:
            tools = await manager.search_tools(query, user_id)
    """
    return _semantic_index_manager


def set_semantic_index_manager(manager: Any) -> None:
    """
    Set the SemanticIndexManager singleton instance.

    Called during app startup to initialize the manager.
    The manager handles semantic search for tools, skills, and memories.

    Args:
        manager: SemanticIndexManager instance to cache

    Example:
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(embedder=embedder, qdrant_client=client)
        set_semantic_index_manager(manager)
    """
    global _semantic_index_manager
    _semantic_index_manager = manager
    logger.debug("SemanticIndexManager singleton initialized")


# ==============================================================================
# Message Semantic Index Manager (Session Similarity - v8 Phase 1)
# ==============================================================================

# Singleton instance for message semantic index manager
_message_index_manager: Any = None


def get_message_index_manager() -> Any:
    """
    Get MessageSemanticIndexManager instance (singleton).

    Returns the cached manager for message embedding search.
    Returns None if not initialized (enable_message_embedding=false).

    v8 Phase 1: Message Embedding & Session Similarity

    Returns:
        MessageSemanticIndexManager instance or None if not initialized

    Example:
        # In AI UX service
        manager = get_message_index_manager()
        if manager:
            similar = await manager.search_similar_sessions(query, user_id)
    """
    return _message_index_manager


def set_message_index_manager(manager: Any) -> None:
    """
    Set the MessageSemanticIndexManager singleton instance.

    Called during app startup when enable_message_embedding is true.
    The manager handles semantic search for session similarity.

    v8 Phase 1: Uses dedicated 'message_index' collection.

    Args:
        manager: MessageSemanticIndexManager instance
    """
    global _message_index_manager
    _message_index_manager = manager
    logger.debug("MessageSemanticIndexManager singleton initialized")


# ==============================================================================
# Decision Trace Repository (ADR-0101 Context Graphs)
# ==============================================================================

# Singleton instance for decision trace repository
_decision_trace_repository: Any = None


def get_decision_trace_repository() -> Any:
    """
    Get DecisionTraceRepository instance (singleton).

    Returns the cached PostgresDecisionTraceRepository for decision trace storage.
    Returns None if not initialized (context graph disabled).

    ADR-0101: Context Graphs - Decision Trace Capture

    Returns:
        DecisionTraceRepositoryBase instance or None if not initialized

    Example:
        # In GDPR data export/deletion
        repo = get_decision_trace_repository()
        if repo:
            traces = await repo.get_by_user(user_id)
    """
    return _decision_trace_repository


def set_decision_trace_repository(repository: Any) -> None:
    """
    Set the DecisionTraceRepository singleton instance.

    Called during app startup (bootstrap/context_graph.py) to initialize
    the repository when FF_ENABLE_CONTEXT_GRAPH=true.

    Args:
        repository: DecisionTraceRepositoryBase instance to cache

    Example:
        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        repo = PostgresDecisionTraceRepository(session_factory=get_async_session)
        set_decision_trace_repository(repo)
    """
    global _decision_trace_repository
    _decision_trace_repository = repository
    logger.debug("DecisionTraceRepository singleton initialized")


# ==============================================================================
# LangGraph Execution Trace Repository Dependency (Phase 4)
# ==============================================================================

# Singleton instance for LangGraph execution trace repository
_langgraph_execution_trace_repository: "LangGraphExecutionTraceRepositoryBase | None" = None


def get_langgraph_execution_trace_repository() -> "LangGraphExecutionTraceRepositoryBase | None":
    """
    Get LangGraphExecutionTraceRepository instance (singleton).

    Returns the cached PostgresLangGraphExecutionTraceRepository for
    storing LangGraph node execution traces for DevTools AgentTraceTab.

    Phase 4: LangGraph Execution Trace Persistence

    Returns:
        LangGraphExecutionTraceRepositoryBase instance or None if not initialized

    Example:
        repo = get_langgraph_execution_trace_repository()
        if repo:
            traces = await repo.get_by_session(session_id)
    """
    return _langgraph_execution_trace_repository


def set_langgraph_execution_trace_repository(repository: "LangGraphExecutionTraceRepositoryBase") -> None:
    """
    Set the LangGraphExecutionTraceRepository singleton instance.

    Called during app startup to initialize the repository.

    Args:
        repository: LangGraphExecutionTraceRepositoryBase instance to cache
    """
    global _langgraph_execution_trace_repository
    _langgraph_execution_trace_repository = repository
    logger.debug("LangGraphExecutionTraceRepository singleton initialized")


# ==============================================================================
# Testing Utilities (CODEX Finding #6)
# ==============================================================================


def reset_singleton_dependencies() -> None:
    """
    Reset all singleton dependencies to None.

    CODEX FINDING #6: Permanently skipped test due to singleton cache.
    This function enables proper testing of dependency wiring logic by
    allowing tests to reset singletons between test runs.

    Usage in tests:
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        def test_dependency_wiring():
            reset_singleton_dependencies()
            # Now test dependency initialization with mocked settings
            ...

    WARNING: This should ONLY be used in tests. Never call in production code.
    """
    global \
        _keycloak_client, \
        _openfga_client, \
        _service_principal_manager, \
        _api_key_manager, \
        _user_provider, \
        _token_denylist, \
        _semantic_index_manager, \
        _decision_trace_repository, \
        _execution_plan_repository

    _keycloak_client = None
    _openfga_client = None
    _service_principal_manager = None
    _api_key_manager = None
    _user_provider = None
    _token_denylist = None
    _semantic_index_manager = None
    _decision_trace_repository = None
    _execution_plan_repository = None


# ==============================================================================
# Database Dependencies
# ==============================================================================


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session for dependency injection.

    This dependency creates a new session for each request and handles
    commit/rollback/close automatically.

    Yields:
        AsyncSession: Database session for the request

    Example:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()
    """
    from mcp_server_langgraph.database.session import get_session_maker

    # Get database URL from settings
    database_url = settings.database_url

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured. Set the DATABASE_URL environment variable.")

    session_maker = get_session_maker(database_url)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session for use outside FastAPI request context.

    This is an alias for get_db_session that can be used with async iteration
    pattern in non-FastAPI contexts (e.g., WebSocket handlers, background tasks).

    Yields:
        AsyncSession: Database session

    Example:
        async for session in get_async_session():
            repo = UserPreferencesRepository(session)
            prefs = await repo.get_preferences(user_id)

    Note:
        For FastAPI route handlers, prefer using get_db_session with Depends():
            @router.get("/items")
            async def get_items(session: AsyncSession = Depends(get_db_session)):
                ...
    """
    from mcp_server_langgraph.database.session import get_session_maker

    database_url = settings.database_url

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured. Set the DATABASE_URL environment variable.")

    session_maker = get_session_maker(database_url)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_project_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProjectRepository:
    """
    Get ProjectRepository instance for dependency injection.

    Args:
        session: Database session (injected)

    Returns:
        PostgresProjectRepository instance

    Example:
        @router.get("/projects/{id}")
        async def get_project(
            id: str,
            repo: ProjectRepository = Depends(get_project_repository),
        ):
            return await repo.get(id)
    """
    return PostgresProjectRepository(session)


# ==============================================================================
# Connection Repository Dependencies
# ==============================================================================


def get_connection_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ConnectionRepository:
    """
    Get ConnectionRepository instance for dependency injection.

    Returns a CachedConnectionRepository wrapping PostgresConnectionRepository
    for improved read performance via L1/L2 caching.

    Args:
        session: Database session (injected)

    Returns:
        CachedConnectionRepository instance (wraps PostgresConnectionRepository)

    Example:
        @router.get("/connections/{id}")
        async def get_connection(
            id: str,
            repo: ConnectionRepository = Depends(get_connection_repository),
        ):
            return await repo.get(id)
    """
    from mcp_server_langgraph.core.secrets import get_secrets_provider
    from mcp_server_langgraph.repositories.cached_connections import (
        CachedConnectionRepository,
    )

    secrets_provider = get_secrets_provider()
    postgres_repo = PostgresConnectionRepository(session, secrets_provider)

    # Wrap with caching for improved read performance
    return CachedConnectionRepository(postgres_repo)


# ==============================================================================
# Audit Log Repository Dependencies
# ==============================================================================


def get_audit_log_repository(
    session: AsyncSession = Depends(get_db_session),
) -> "AuditLogRepository":
    """
    Get AuditLogRepository instance for dependency injection.

    Args:
        session: Database session (injected)

    Returns:
        PostgresAuditLogRepository instance

    Example:
        @router.post("/connections/audit/log")
        async def log_event(
            event: AuditEvent,
            repo: AuditLogRepository = Depends(get_audit_log_repository),
        ):
            return await repo.log_event(...)
    """
    from mcp_server_langgraph.repositories.audit_log import (
        PostgresAuditLogRepository,
    )

    return PostgresAuditLogRepository(session)


# ==============================================================================
# Session Goal Repository Dependencies
# ==============================================================================


def get_session_goal_repository(
    session: AsyncSession = Depends(get_db_session),
) -> "SessionGoalRepository":
    """
    Get SessionGoalRepository instance for dependency injection.

    Args:
        session: Database session (injected)

    Returns:
        PostgresSessionGoalRepository instance

    Example:
        @router.post("/sessions/{session_id}/goal")
        async def set_goal(
            session_id: str,
            repo: SessionGoalRepository = Depends(get_session_goal_repository),
        ):
            return await repo.create_goal(...)
    """
    from mcp_server_langgraph.repositories.session_goal import (
        PostgresSessionGoalRepository,
    )

    return PostgresSessionGoalRepository(session)


# ==============================================================================
# OAuth2 Service Dependencies
# ==============================================================================


class OAuth2Service:
    """
    OAuth2 service for handling PKCE authorization flow.

    This is a placeholder implementation. In production, this should be
    replaced with a proper OAuth2 client library.
    """

    async def discover_metadata(self, url: str) -> dict[str, str]:
        """Discover OAuth2 metadata from MCP server."""
        # In production, fetch from {url}/.well-known/oauth-authorization-server
        return {
            "authorization_endpoint": f"{url}/oauth/authorize",
            "token_endpoint": f"{url}/oauth/token",
        }

    def generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        import secrets

        return secrets.token_urlsafe(64)

    def generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge (S256)."""
        import base64
        import hashlib

        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def build_authorization_url(
        self,
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        code_challenge: str,
    ) -> str:
        """Build OAuth2 authorization URL with PKCE."""
        from urllib.parse import urlencode

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(
        self,
        token_endpoint: str,
        client_id: str,
        client_secret: str | None,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens."""

        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        if client_secret:
            data["client_secret"] = client_secret

        async with httpx.AsyncClient() as client:
            response = await client.post(token_endpoint, data=data)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result


_oauth2_service: OAuth2Service | None = None


def get_oauth2_service() -> OAuth2Service:
    """Get OAuth2 service instance (singleton)."""
    global _oauth2_service

    if _oauth2_service is None:
        _oauth2_service = OAuth2Service()

    return _oauth2_service


# ==============================================================================
# Execution Plan Repository Dependencies (v35.0)
# ==============================================================================

# Singleton instance for execution plan repository
_execution_plan_repository: Any = None


def get_execution_plan_repository() -> Any:
    """
    Get ExecutionPlanRepository instance (singleton).

    Returns the cached repository for execution plan persistence.
    Returns InMemoryExecutionPlanRepository if settings.plan_storage_backend != "postgres",
    otherwise returns PostgresExecutionPlanRepository.

    v35.0 RLM Phase: Execution plan persistence for approval workflows.

    Returns:
        ExecutionPlanRepository instance

    Example:
        # In API routes
        repo = get_execution_plan_repository()
        plan = await repo.get(plan_id)
    """
    global _execution_plan_repository

    if _execution_plan_repository is None:
        if settings.plan_storage_backend == "postgres":
            from mcp_server_langgraph.database.session import get_session_maker
            from mcp_server_langgraph.repositories.postgres_execution_plan import (
                PostgresExecutionPlanRepository,
            )

            database_url = settings.database_url
            if not database_url:
                raise RuntimeError("DATABASE_URL is not configured for postgres plan storage.")

            session_maker = get_session_maker(database_url)
            _execution_plan_repository = PostgresExecutionPlanRepository(session_maker)
        else:
            from mcp_server_langgraph.repositories.execution_plan import (
                get_plan_repository,
            )

            _execution_plan_repository = get_plan_repository()

    return _execution_plan_repository


def set_execution_plan_repository(repository: Any) -> None:
    """
    Set the ExecutionPlanRepository singleton instance.

    Called during app startup or testing to inject a specific repository.

    v35.0 RLM Phase: Allows DI for testing.

    Args:
        repository: ExecutionPlanRepository instance to cache
    """
    global _execution_plan_repository
    _execution_plan_repository = repository
    logger.debug("ExecutionPlanRepository singleton initialized")


# ==============================================================================
# MCP Client Dependencies
# ==============================================================================


class MCPClient:
    """
    MCP client for testing connections.

    Uses the official MCP SDK for Streamable HTTP transport to:
    - Establish connection with MCP server
    - Exchange initialization handshake
    - Retrieve server info and capabilities (tools, resources, prompts)
    """

    def __init__(
        self,
        connection_timeout: float = 10.0,
        sse_read_timeout: float = 30.0,
    ) -> None:
        """
        Initialize MCP client.

        Args:
            connection_timeout: Timeout for HTTP operations
            sse_read_timeout: Timeout for SSE event reading
        """
        self.connection_timeout = connection_timeout
        self.sse_read_timeout = sse_read_timeout

    async def test_connection(
        self,
        url: str,
        auth_header: str | None = None,
    ) -> Any:
        """
        Test connection to an MCP server using Streamable HTTP transport.

        Args:
            url: The MCP server URL (e.g., https://mcp.example.com)
            auth_header: Optional authorization header value (e.g., "Bearer token")

        Returns:
            MCPConnectionTestResult with success status and server info
        """
        from mcp_server_langgraph.storage.models import MCPConnectionTestResult

        headers: dict[str, str] = {}
        if auth_header:
            headers["Authorization"] = auth_header

        try:
            # Use MCP SDK's streamable HTTP client
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
            from mcp.types import Implementation

            async with streamablehttp_client(
                url=url,
                headers=headers if headers else None,
                timeout=self.connection_timeout,
                sse_read_timeout=self.sse_read_timeout,
            ) as (read_stream, write_stream, _get_session_id):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    client_info=Implementation(
                        name="mcp-server-langgraph",
                        version="1.0.0",
                    ),
                ) as session:
                    # Initialize the connection
                    init_result = await session.initialize()

                    # Get lists of tools, resources, and prompts if supported
                    tool_count = 0
                    resource_count = 0
                    prompt_count = 0

                    # Check capabilities and fetch lists
                    if init_result.capabilities:
                        if init_result.capabilities.tools:
                            try:
                                tools = await session.list_tools()
                                tool_count = len(tools.tools) if tools.tools else 0
                            except Exception as e:
                                logger.debug("Operation failed: %s", e)

                        if init_result.capabilities.resources:
                            try:
                                resources = await session.list_resources()
                                resource_count = len(resources.resources) if resources.resources else 0
                            except Exception as e:
                                logger.debug("Operation failed: %s", e)

                        if init_result.capabilities.prompts:
                            try:
                                prompts = await session.list_prompts()
                                prompt_count = len(prompts.prompts) if prompts.prompts else 0
                            except Exception as e:
                                logger.debug("Operation failed: %s", e)

                    return MCPConnectionTestResult(
                        success=True,
                        server_name=init_result.serverInfo.name if init_result.serverInfo else None,
                        server_version=init_result.serverInfo.version if init_result.serverInfo else None,
                        tool_count=tool_count,
                        resource_count=resource_count,
                        prompt_count=prompt_count,
                    )

        except Exception as e:
            # Categorize the error for better diagnostics
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                error_msg = f"Connection timeout: {e}"
            elif "refused" in error_msg.lower():
                error_msg = f"Connection refused: {e}"
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                error_msg = f"Authentication failed: {e}"
            elif "forbidden" in error_msg.lower() or "403" in error_msg:
                error_msg = f"Access forbidden: {e}"

            return MCPConnectionTestResult(
                success=False,
                error=error_msg,
            )


_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get MCP client instance (singleton)."""
    global _mcp_client

    if _mcp_client is None:
        _mcp_client = MCPClient()

    return _mcp_client
