"""
Storage Configuration Module.

Settings for PostgreSQL, Redis, Qdrant, and cloud storage backends.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class StorageSettings(DomainSettings):
    """
    Storage backend settings.

    Covers:
    - PostgreSQL database configuration
    - Redis session and cache configuration
    - Qdrant vector database (semantic search)
    - Workflow storage backend
    - Cloud storage (S3, GCS, Azure Blob) for audit archival
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # Primary Database (PostgreSQL)
    # NOTE: Default uses placeholder credentials for dev. Set DATABASE_URL env var in production.
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/mcp",
        description="PostgreSQL URL. Set DATABASE_URL env var with credentials in production.",
    )

    # Session Management
    session_backend: str = "memory"  # "memory", "redis"
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="redis_session_url",
    )
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_ssl: bool = False
    session_ttl_seconds: int = 86400  # 24 hours
    session_idle_seconds: int = 1800  # 30 minutes (OWASP recommendation)
    session_sliding_window: bool = True
    session_max_concurrent: int = 5

    # Checkpoint Configuration (for distributed state)
    checkpoint_backend: str = "memory"  # "memory", "redis"
    checkpoint_redis_url: str = Field(
        default="redis://localhost:6379/1",
        # Accept multiple input names:
        # - CHECKPOINT_REDIS_URL: Primary (docker-compose.test.yml, .env.example)
        # - REDIS_CHECKPOINT_URL: SCREAMING_SNAKE_CASE alternative
        # - redis_checkpoint_url: snake_case for constructor args (test compatibility)
        validation_alias=AliasChoices("CHECKPOINT_REDIS_URL", "REDIS_CHECKPOINT_URL", "redis_checkpoint_url"),
    )
    checkpoint_redis_ttl: int = 604800  # 7 days

    # API Key Cache Configuration
    api_key_cache_enabled: bool = True
    api_key_cache_db: int = 3
    api_key_cache_ttl: int = 3600

    # Workflow Storage Backend
    workflow_storage_backend: str = "postgres"  # "postgres", "redis", "memory"

    # Conversation Storage
    conversation_storage_backend: str = "checkpoint"  # "checkpoint", "database"

    # Cost Metrics Storage
    cost_storage_backend: str = "memory"  # "postgres", "memory"

    # Qdrant Vector Database
    qdrant_url: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "mcp_context"
    dynamic_context_max_tokens: int = 2000
    dynamic_context_top_k: int = 3
    context_cache_size: int = 100

    # S3 Configuration
    aws_s3_bucket: str | None = None
    aws_s3_region: str | None = None
    aws_s3_prefix: str = "audit-logs/"

    # GCS Configuration
    gcp_storage_bucket: str | None = None
    gcp_storage_prefix: str = "audit-logs/"
    gcp_credentials_path: str | None = None

    # Azure Blob Storage Configuration
    azure_storage_account: str | None = None
    azure_storage_container: str | None = None
    azure_storage_prefix: str = "audit-logs/"
    azure_storage_connection_string: str | None = None

    # Aliases for test compatibility
    @property
    def redis_checkpoint_url(self) -> str:
        """Alias for checkpoint_redis_url (test compatibility)."""
        return self.checkpoint_redis_url

    @property
    def redis_session_url(self) -> str:
        """Alias for redis_url (test compatibility)."""
        return self.redis_url


__all__ = ["StorageSettings"]
