"""
GDPR Storage Factory

Creates storage backend instances based on configuration.
Supports multiple backends:
- PostgreSQL (production-ready, recommended)
- In-memory (development/testing only)

Pattern: Factory pattern with dependency injection
"""

from typing import Any, Literal

from mcp_server_langgraph.compliance.gdpr.postgres_storage import (
    PostgresAuditLogStore,
    PostgresConsentStore,
    PostgresConversationStore,
    PostgresPreferencesStore,
    PostgresUserProfileStore,
)
from mcp_server_langgraph.compliance.gdpr.storage import (
    AuditLogStore,
    ConsentStore,
    ConversationStore,
    InMemoryAuditLogStore,
    InMemoryConsentStore,
    InMemoryConversationStore,
    InMemoryPreferencesStore,
    InMemoryUserProfileStore,
    PreferencesStore,
    UserProfileStore,
)


class GDPRStorage:
    """
    Container for all GDPR storage backends

    Provides unified access to all storage components:
    - user_profiles: User profile storage
    - preferences: User preferences storage
    - consents: Consent record storage
    - conversations: Conversation storage
    - audit_logs: Audit log storage
    """

    def __init__(
        self,
        user_profiles: UserProfileStore,
        preferences: PreferencesStore,
        consents: ConsentStore,
        conversations: ConversationStore,
        audit_logs: AuditLogStore,
    ):
        self.user_profiles = user_profiles
        self.preferences = preferences
        self.consents = consents
        self.conversations = conversations
        self.audit_logs = audit_logs


async def create_postgres_storage(postgres_url: str) -> GDPRStorage:
    """
    Create PostgreSQL-backed GDPR storage (RECOMMENDED for production)

    Uses retry logic with exponential backoff to handle transient connection failures.

    Args:
        postgres_url: PostgreSQL connection URL
                     Example: postgresql://user:pass@localhost:5432/gdpr

    Returns:
        GDPRStorage instance with PostgreSQL backends

    Raises:
        asyncpg.PostgresError: If connection fails after retries
        Exception: If retries are exhausted

    Example:
        >>> storage = await create_postgres_storage("postgresql://postgres:postgres@localhost:5432/gdpr")
        >>> profile = await storage.user_profiles.get("user:alice")
    """
    from mcp_server_langgraph.infrastructure.database import create_connection_pool

    # Create connection pool with retry logic
    # Retries: 3, Backoff: 1s, 2s, 4s (with jitter)
    pool = await create_connection_pool(
        postgres_url,
        min_size=2,
        max_size=10,
        command_timeout=60.0,
        max_retries=3,
        initial_delay=1.0,
        max_delay=8.0,
    )

    # Create storage instances
    return GDPRStorage(
        user_profiles=PostgresUserProfileStore(pool),
        preferences=PostgresPreferencesStore(pool),
        consents=PostgresConsentStore(pool),
        conversations=PostgresConversationStore(pool),
        audit_logs=PostgresAuditLogStore(pool),
    )


def create_memory_storage() -> GDPRStorage:
    """
    Create in-memory GDPR storage (DEVELOPMENT/TESTING ONLY)

    WARNING: Data is lost when process restarts.
    NOT suitable for production use.

    Returns:
        GDPRStorage instance with in-memory backends

    Example:
        >>> storage = create_memory_storage()
        >>> # Use for testing only
    """
    return GDPRStorage(
        user_profiles=InMemoryUserProfileStore(),
        preferences=InMemoryPreferencesStore(),
        consents=InMemoryConsentStore(),
        conversations=InMemoryConversationStore(),
        audit_logs=InMemoryAuditLogStore(),
    )


async def create_gdpr_storage(
    backend: Literal["postgres", "memory"] = "postgres",
    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/gdpr",
) -> GDPRStorage:
    """
    Create GDPR storage with specified backend

    Factory function that creates appropriate storage backend based on configuration.

    Args:
        backend: Storage backend type ("postgres" or "memory")
        postgres_url: PostgreSQL connection URL (required if backend="postgres")

    Returns:
        GDPRStorage instance

    Raises:
        ValueError: If backend is invalid
        asyncpg.PostgresError: If PostgreSQL connection fails

    Example:
        >>> # Production (PostgreSQL)
        >>> storage = await create_gdpr_storage(
        ...     backend="postgres",
        ...     postgres_url="postgresql://user:pass@db.example.com:5432/gdpr"
        ... )

        >>> # Development (in-memory)
        >>> storage = await create_gdpr_storage(backend="memory")
    """
    if backend == "postgres":
        return await create_postgres_storage(postgres_url)
    elif backend == "memory":
        return create_memory_storage()
    else:
        raise ValueError(f"Invalid GDPR storage backend: {backend}. Must be 'postgres' or 'memory'.")


# ============================================================================
# Global Singleton Pattern (DEPRECATED - for backward compatibility only)
# ============================================================================
# WARNING: Global singleton causes pytest-xdist cross-worker pollution
# NEW CODE: Use get_gdpr_storage_dependency() for request-scoped storage
# See: CODEX_FINDINGS_VALIDATION_REPORT_2025-11-21.md
# ============================================================================

_gdpr_storage: GDPRStorage | None = None


async def initialize_gdpr_storage(
    backend: Literal["postgres", "memory"] = "postgres",
    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/gdpr",
) -> None:
    """
    Initialize global GDPR storage instance

    .. deprecated:: 2025-11-22
        Use get_gdpr_storage_dependency() for request-scoped storage instead.
        This function will be removed in v2.0.

    Should be called during application startup.

    Args:
        backend: Storage backend type
        postgres_url: PostgreSQL connection URL

    Example:
        >>> # DEPRECATED - Old pattern
        >>> await initialize_gdpr_storage(
        ...     backend=settings.gdpr_storage_backend,
        ...     postgres_url=settings.gdpr_postgres_url
        ... )
        >>>
        >>> # NEW pattern - Request-scoped dependency injection
        >>> # No initialization needed - storage created per-request
    """
    global _gdpr_storage
    _gdpr_storage = await create_gdpr_storage(backend, postgres_url)


def get_gdpr_storage() -> GDPRStorage:
    """
    Get global GDPR storage instance

    .. deprecated:: 2025-11-22
        Use get_gdpr_storage_dependency() for request-scoped storage instead.
        This function will be removed in v2.0.

    Returns:
        GDPRStorage instance

    Raises:
        RuntimeError: If storage not initialized

    Example:
        >>> # DEPRECATED - Old pattern
        >>> storage = get_gdpr_storage()
        >>> profile = await storage.user_profiles.get("user:alice")
        >>>
        >>> # NEW pattern - FastAPI dependency injection
        >>> from fastapi import Depends
        >>> def my_endpoint(storage: GDPRStorage = Depends(get_gdpr_storage_dependency)):
        ...     profile = await storage.user_profiles.get("user:alice")
    """
    if _gdpr_storage is None:
        raise RuntimeError("GDPR storage not initialized. Call initialize_gdpr_storage() during application startup.")
    return _gdpr_storage


def reset_gdpr_storage() -> None:
    """
    Reset global GDPR storage instance

    .. deprecated:: 2025-11-22
        Not needed with request-scoped storage - each request gets fresh instance.
        This function will be removed in v2.0.

    Used for testing to reset storage between tests.

    Example:
        >>> # DEPRECATED - Old pattern
        >>> reset_gdpr_storage()
        >>>
        >>> # NEW pattern - No reset needed (request-scoped)
        >>> # Each test request gets isolated storage instance
    """
    global _gdpr_storage
    _gdpr_storage = None


# ============================================================================
# Request-Scoped Dependency Injection (RECOMMENDED)
# ============================================================================
# Benefits:
# - No global state - eliminates pytest-xdist cross-worker pollution
# - Better testability - each request gets isolated storage
# - Thread-safe - no shared mutable state
# - Cloud-native - works with serverless/multi-instance deployments
# ============================================================================

# Configuration for request-scoped storage (set during app startup)
_gdpr_storage_config: dict[str, Any] | None = None


def configure_gdpr_storage(
    backend: Literal["postgres", "memory"] = "postgres",
    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/gdpr",
) -> None:
    """
    Configure GDPR storage for request-scoped dependency injection

    Call this during application startup to set configuration.
    Unlike initialize_gdpr_storage(), this does NOT create storage immediately.
    Storage is created per-request using get_gdpr_storage_dependency().

    Args:
        backend: Storage backend type ("postgres" or "memory")
        postgres_url: PostgreSQL connection URL

    Example:
        >>> # In main.py application startup
        >>> configure_gdpr_storage(
        ...     backend="postgres",
        ...     postgres_url="postgresql://user:pass@localhost:5432/gdpr"
        ... )
        >>>
        >>> # In API endpoints (automatic via dependency injection)
        >>> @router.get("/users/me")
        >>> async def get_user(storage: GDPRStorage = Depends(get_gdpr_storage_dependency)):
        ...     return await storage.user_profiles.get("user:alice")
    """
    global _gdpr_storage_config
    _gdpr_storage_config = {
        "backend": backend,
        "postgres_url": postgres_url,
    }


async def get_gdpr_storage_dependency() -> GDPRStorage:
    """
    FastAPI dependency for request-scoped GDPR storage

    Creates a new storage instance for each request using configured settings.
    No global state - eliminates pytest-xdist cross-worker pollution.

    Returns:
        GDPRStorage instance (fresh per request)

    Raises:
        RuntimeError: If storage not configured (call configure_gdpr_storage() first)

    Example:
        >>> from fastapi import Depends, APIRouter
        >>> router = APIRouter()
        >>>
        >>> @router.get("/users/{user_id}")
        >>> async def get_user(
        ...     user_id: str,
        ...     storage: GDPRStorage = Depends(get_gdpr_storage_dependency)
        >>> ):
        ...     return await storage.user_profiles.get(user_id)
    """
    if _gdpr_storage_config is None:
        # Fallback to global singleton for backward compatibility
        # This allows tests to work without migration
        if _gdpr_storage is not None:
            return _gdpr_storage

        # If neither is configured, use default memory storage for development
        return create_memory_storage()

    # Create fresh storage instance per request
    backend = _gdpr_storage_config.get("backend", "memory")
    postgres_url = _gdpr_storage_config.get("postgres_url", "postgresql://postgres:postgres@localhost:5432/gdpr")

    return await create_gdpr_storage(backend=backend, postgres_url=postgres_url)
