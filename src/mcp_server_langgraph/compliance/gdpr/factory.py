"""
GDPR Storage Factory

Creates storage backend instances based on configuration.
Supports multiple backends:
- PostgreSQL (production-ready, recommended)
- In-memory (development/testing only)

Pattern: Factory pattern with dependency injection
"""

from typing import Literal

import asyncpg

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

    Args:
        postgres_url: PostgreSQL connection URL
                     Example: postgresql://user:pass@localhost:5432/gdpr

    Returns:
        GDPRStorage instance with PostgreSQL backends

    Raises:
        asyncpg.PostgresError: If connection fails

    Example:
        >>> storage = await create_postgres_storage("postgresql://postgres:postgres@localhost:5432/gdpr")
        >>> profile = await storage.user_profiles.get("user:alice")
    """
    # Create connection pool
    pool = await asyncpg.create_pool(
        postgres_url,
        min_size=2,
        max_size=10,
        command_timeout=60,
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


# Global storage instance (initialized by application startup)
_gdpr_storage: GDPRStorage | None = None


async def initialize_gdpr_storage(
    backend: Literal["postgres", "memory"] = "postgres",
    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/gdpr",
) -> None:
    """
    Initialize global GDPR storage instance

    Should be called during application startup.

    Args:
        backend: Storage backend type
        postgres_url: PostgreSQL connection URL

    Example:
        >>> # In main application startup
        >>> await initialize_gdpr_storage(
        ...     backend=settings.gdpr_storage_backend,
        ...     postgres_url=settings.gdpr_postgres_url
        ... )
    """
    global _gdpr_storage
    _gdpr_storage = await create_gdpr_storage(backend, postgres_url)


def get_gdpr_storage() -> GDPRStorage:
    """
    Get global GDPR storage instance

    Returns:
        GDPRStorage instance

    Raises:
        RuntimeError: If storage not initialized

    Example:
        >>> storage = get_gdpr_storage()
        >>> profile = await storage.user_profiles.get("user:alice")
    """
    if _gdpr_storage is None:
        raise RuntimeError("GDPR storage not initialized. Call initialize_gdpr_storage() during application startup.")
    return _gdpr_storage


def reset_gdpr_storage() -> None:
    """
    Reset global GDPR storage instance

    Used for testing to reset storage between tests.

    Example:
        >>> # In test teardown
        >>> reset_gdpr_storage()
    """
    global _gdpr_storage
    _gdpr_storage = None
