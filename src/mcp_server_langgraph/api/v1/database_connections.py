"""
Database Connections API Endpoints

Implements CRUD operations for database connections with:
- Credential storage via Secrets Manager reference
- SSRF/Egress validation for connection hosts
- Tenant-scoped access control
- Connection testing with sanitized error messages

Usage:
    from mcp_server_langgraph.api.v1.database_connections import database_connections_router
    app.include_router(database_connections_router)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.feature_flags import feature_flags
from cachetools import TTLCache

from mcp_server_langgraph.execution.sql.credential_manager import (
    SecureConnectionConfig,
    SecretsProvider,
)
from mcp_server_langgraph.execution.sql.exceptions import EgressValidationError
from mcp_server_langgraph.network.egress_validator import (
    EgressValidator,
    RuntimeEgressValidator,
)

logger = logging.getLogger(__name__)

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# ============================================================================
# Pydantic Models
# ============================================================================


class DatabaseConnectionCreateRequest(BaseModel):
    """Request to create a database connection."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    dialect: str = Field(
        ...,
        description="Database dialect (postgres, mysql, sqlite, bigquery, snowflake, duckdb, redshift, clickhouse, trino)",
    )
    host: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    database: str | None = None

    # Cloud-specific
    project_id: str | None = None  # BigQuery
    account_id: str | None = None  # Snowflake
    warehouse_id: str | None = None  # Snowflake, Databricks

    # Credential source
    connection_method: str = Field(
        default="credentials",
        description="credentials | secret_ref | connection_string",
    )

    # Direct credentials (stored in Secrets Manager, never persisted in DB)
    username: str | None = None
    password: str | None = None  # Sent once, stored in Secrets Manager

    # Secret reference (already in Secrets Manager)
    secret_path: str | None = None
    secret_key: str | None = None

    # Connection string (parsed for host/port, stored in Secrets Manager)
    connection_string: str | None = None

    # SSL/TLS
    ssl_mode: str = Field(
        default="require",
        description="disable | require | verify-ca | verify-full",
    )

    # Scope
    scope: str = Field(default="user", description="user | project | session")


class DatabaseConnectionResponse(BaseModel):
    """Database connection response (without secrets)."""

    id: str
    name: str
    description: str | None = None
    dialect: str
    host: str | None = None
    port: int | None = None
    database: str | None = None
    project_id: str | None = None
    account_id: str | None = None
    warehouse_id: str | None = None
    ssl_mode: str = "require"
    status: str = "disconnected"
    last_tested_at: str | None = None
    dialect_version: str | None = None
    owner_id: str
    tenant_id: str
    created_at: str
    updated_at: str


class DatabaseConnectionUpdateRequest(BaseModel):
    """Request to update a database connection.

    Supports both metadata updates and credential rotation.
    When credential fields are provided, they are stored in Secrets Manager.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    host: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    database: str | None = None
    ssl_mode: str | None = None

    # Credential rotation fields
    username: str | None = None
    password: str | None = None  # Stored in Secrets Manager, never persisted in DB
    connection_string: str | None = None  # Alternative to username/password

    # Cloud-specific fields
    project_id: str | None = None  # BigQuery
    account_id: str | None = None  # Snowflake
    warehouse_id: str | None = None  # Snowflake, Databricks


class DatabaseConnectionTestResult(BaseModel):
    """Result of testing a database connection."""

    success: bool
    error: str | None = None
    dialect_version: str | None = None


class DatabaseConnectionListResponse(BaseModel):
    """Response for listing database connections."""

    items: list[DatabaseConnectionResponse]
    total: int


# ============================================================================
# Helpers
# ============================================================================

VALID_DIALECTS = {
    "postgres",
    "mysql",
    "sqlite",
    "bigquery",
    "snowflake",
    "duckdb",
    "redshift",
    "clickhouse",
    "trino",
}
VALID_SSL_MODES = {"disable", "require", "verify-ca", "verify-full"}
VALID_CONNECTION_METHODS = {"credentials", "secret_ref", "connection_string"}
VALID_SCOPES = {"user", "project", "session"}

DEFAULT_PORTS: dict[str, int] = {
    "postgres": 5432,
    "mysql": 3306,
    "sqlite": 0,
    "bigquery": 443,
    "snowflake": 443,
    "duckdb": 0,
    "redshift": 5439,
    "clickhouse": 9000,  # Native protocol port (asynch driver)
    "trino": 8080,
}


def _validate_dialect(dialect: str) -> None:
    """Validate dialect is one of the supported values."""
    if dialect not in VALID_DIALECTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dialect '{dialect}'. Must be one of: {', '.join(sorted(VALID_DIALECTS))}",
        )


def _resolve_host_from_connection_string(conn_str: str) -> tuple[str | None, int | None]:
    """Extract host and port from a connection string.

    Handles formats like:
    - postgresql://user:pass@host:port/db
    - host:port
    - host
    """
    try:
        parsed = urlparse(conn_str)
        if parsed.hostname:
            return parsed.hostname, parsed.port
    except Exception:
        pass
    # Fallback: handle bare host[:port] strings without a URL scheme
    if "://" not in conn_str:
        stripped = conn_str.strip()
        if ":" in stripped:
            host_part, port_str = stripped.rsplit(":", 1)
            try:
                return host_part, int(port_str)
            except ValueError:
                return host_part, None
        if stripped:
            return stripped, None
    return None, None


# ============================================================================
# FastAPI Dependency Injection
# ============================================================================


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy import wrapper for get_db_session to avoid circular imports."""
    from mcp_server_langgraph.core.dependencies import get_db_session

    async for session in get_db_session():
        yield session


def get_egress_validator() -> RuntimeEgressValidator | None:
    """Return RuntimeEgressValidator when egress validation is enabled.

    Respects ``feature_flags.enable_sql_egress_validation``. Returns
    ``None`` when the feature flag is disabled.
    """
    if not feature_flags.enable_sql_egress_validation:
        return None
    return RuntimeEgressValidator(EgressValidator())


def get_secrets_provider() -> SecretsProvider:
    """Return the configured SecretsProvider instance.

    Uses ``core/secrets.py:get_secrets_provider()`` which auto-detects
    the cloud provider (AWS/Azure/GCP) or falls back to
    ``InMemorySecretsProvider`` for dev/test.

    See ADR-0107 for secrets provider selection rationale.
    Configure via env vars: SECRETS_PROVIDER, AWS_REGION,
    AZURE_KEY_VAULT_URL, or GOOGLE_CLOUD_PROJECT.
    """
    from mcp_server_langgraph.core.secrets import (
        InMemorySecretsProvider,
        get_secrets_provider as _get_provider,
    )

    provider = _get_provider()
    if isinstance(provider, InMemorySecretsProvider):
        import os

        env = os.environ.get("ENVIRONMENT", "").lower()
        if env in {"production", "prod", "staging"}:
            logger.warning(
                "InMemorySecretsProvider is active in %s environment. "
                "Configure a persistent secrets backend via SECRETS_PROVIDER env var.",
                env,
            )
    return provider


# Shared credential cache for cross-instance cache sharing (DI pattern).
# Created once at module import; injected into SecureConnectionConfig instances.
_shared_credential_cache = TTLCache(maxsize=1000, ttl=300)
_shared_credential_cache_lock = asyncio.Lock()


def get_credential_cache() -> TTLCache:
    """Return the shared credential TTLCache for DI."""
    return _shared_credential_cache


def get_credential_cache_lock() -> asyncio.Lock:
    """Return the shared credential cache lock for DI."""
    return _shared_credential_cache_lock


def _sanitize_connection_error(exc: Exception) -> str:
    """Map exceptions to safe user-facing messages.

    SECURITY: Never expose raw exception details to the client.
    Delegates to ``execution.sql.exceptions.sanitize_connection_error()``.
    """
    from mcp_server_langgraph.execution.sql.exceptions import sanitize_connection_error

    return sanitize_connection_error(exc)


def get_db_conn_repository(
    session: Any = Depends(_get_db_session),
    secrets_provider: SecretsProvider = Depends(get_secrets_provider),
) -> Any:
    """Return DatabaseConnectionRepository for DI.

    In production, ``session`` comes from ``get_db_session()``.
    In tests, this dependency is overridden entirely.
    """
    from mcp_server_langgraph.repositories.database_connections import (
        PostgresDatabaseConnectionRepository,
    )

    return PostgresDatabaseConnectionRepository(session, secrets_provider)


def get_connection_tester(
    secrets_provider: SecretsProvider = Depends(get_secrets_provider),
    egress_validator: RuntimeEgressValidator | None = Depends(get_egress_validator),
    credential_cache: TTLCache = Depends(get_credential_cache),
    credential_cache_lock: asyncio.Lock = Depends(get_credential_cache_lock),
) -> Any:
    """Return ConnectionTester for DI."""
    from mcp_server_langgraph.execution.sql.connection_tester import ConnectionTester
    from mcp_server_langgraph.execution.sql.drivers.registry import DriverRegistry

    return ConnectionTester(
        DriverRegistry(),
        secrets_provider,
        egress_validator,
        credential_cache=credential_cache,
        credential_cache_lock=credential_cache_lock,
    )


def _entity_to_response(
    entity: Any,
) -> DatabaseConnectionResponse:
    """Convert DatabaseConnectionEntity to API response model."""
    return DatabaseConnectionResponse(
        id=str(entity.id),
        name=entity.name,
        description=entity.description,
        dialect=entity.dialect,
        host=entity.host,
        port=entity.port,
        database=entity.database,
        project_id=entity.project_id,
        account_id=entity.account_id,
        warehouse_id=entity.warehouse_id,
        ssl_mode=entity.ssl_mode,
        status=entity.status,
        last_tested_at=entity.last_tested_at.isoformat() if entity.last_tested_at else None,
        dialect_version=entity.dialect_version,
        owner_id=entity.owner_id,
        tenant_id=entity.tenant_id,
        created_at=entity.created_at.isoformat() if hasattr(entity.created_at, "isoformat") else str(entity.created_at),
        updated_at=entity.updated_at.isoformat() if hasattr(entity.updated_at, "isoformat") else str(entity.updated_at),
    )


# ============================================================================
# Router
# ============================================================================

database_connections_router = APIRouter(
    prefix="/database-connections",
    tags=["database-connections"],
)


@database_connections_router.get("/", response_model=DatabaseConnectionListResponse)
async def list_database_connections(
    user: CurrentUser,
    repo: Annotated[Any, Depends(get_db_conn_repository)],
    dialect: str | None = Query(None, description="Filter by dialect"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    search: str | None = Query(None, description="Search by name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> DatabaseConnectionListResponse:
    """List database connections for the current user's tenant."""
    if dialect is not None:
        _validate_dialect(dialect)

    tenant_id = user.get("tenant_id", "default")
    owner_id = user.get("sub", user.get("id", "unknown"))

    items, total = await repo.list(
        tenant_id=tenant_id,
        owner_id=owner_id,
        dialect=dialect,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )

    return DatabaseConnectionListResponse(
        items=[_entity_to_response(e) for e in items],
        total=total,
    )


@database_connections_router.post(
    "/",
    response_model=DatabaseConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_database_connection(
    request: DatabaseConnectionCreateRequest,
    user: CurrentUser,
    repo: Annotated[Any, Depends(get_db_conn_repository)],
    egress_validator: Annotated[RuntimeEgressValidator | None, Depends(get_egress_validator)] = None,
    secrets_provider: Annotated[SecretsProvider, Depends(get_secrets_provider)] = None,  # type: ignore[assignment]
    credential_cache: Annotated[TTLCache, Depends(get_credential_cache)] = None,
    credential_cache_lock: Annotated[asyncio.Lock, Depends(get_credential_cache_lock)] = None,  # type: ignore[assignment]
) -> DatabaseConnectionResponse:
    """Create a database connection with credentials stored in Secrets Manager."""
    from mcp_server_langgraph.repositories.database_connections import (
        DatabaseConnectionCreateData,
        DatabaseConnectionUpdateData,
    )

    _validate_dialect(request.dialect)

    if request.ssl_mode not in VALID_SSL_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ssl_mode '{request.ssl_mode}'. Must be one of: {', '.join(sorted(VALID_SSL_MODES))}",
        )

    if request.connection_method not in VALID_CONNECTION_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid connection_method. Must be one of: {', '.join(sorted(VALID_CONNECTION_METHODS))}",
        )

    if request.scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope. Must be one of: {', '.join(sorted(VALID_SCOPES))}",
        )

    if request.connection_method == "credentials":
        if request.dialect not in ("bigquery", "duckdb", "sqlite") and not request.host:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host is required for credential-based connections with this dialect",
            )
    elif request.connection_method == "secret_ref":
        if not request.secret_path or not request.secret_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="secret_path and secret_key are required for secret reference connections",
            )
        # Validate secret_path scope for cross-tenant protection
        # SECURITY: Normalize path and check for traversal sequences
        import posixpath

        tenant_id = user.get("tenant_id", "default")
        normalized = posixpath.normpath(request.secret_path)
        prefix = f"/database/{tenant_id}/"
        if not normalized.startswith(prefix) or ".." in request.secret_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Secret path must be scoped to your tenant",
            )
        if "/" in (request.secret_key or ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="secret_key cannot contain path separators",
            )
    elif request.connection_method == "connection_string":
        if not request.connection_string:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="connection_string is required for connection string connections",
            )

    # Egress validation
    if egress_validator:
        host = request.host
        port = request.port or DEFAULT_PORTS.get(request.dialect, 443)

        if request.connection_method == "secret_ref":
            if not secrets_provider:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Secrets provider unavailable for egress validation",
                )
            try:
                tenant_id = user.get("tenant_id", "default")
                config = SecureConnectionConfig(
                    secrets_provider=secrets_provider,
                    dialect=request.dialect,
                    tenant_id=tenant_id,
                    cache=credential_cache,
                    cache_lock=credential_cache_lock,
                )
                creds = await config.get_credentials(request.secret_path or "", request.secret_key or "")
                host = creds.get("host", host)
                port = creds.get("port", port)
                if "connection_string" in creds:
                    resolved_host, resolved_port = _resolve_host_from_connection_string(creds["connection_string"])
                    host = resolved_host or host
                    port = resolved_port or port
            except HTTPException:
                raise
            except Exception:
                logger.warning(
                    "Failed to resolve host from secret_ref for egress validation",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to resolve connection target for validation",
                )

        if request.connection_method == "connection_string" and request.connection_string:
            resolved_host, resolved_port = _resolve_host_from_connection_string(request.connection_string)
            if not resolved_host:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to resolve host from connection_string for egress validation",
                )
            host = resolved_host
            port = resolved_port or port

        HOSTLESS_DIALECTS = {"sqlite", "duckdb", "bigquery"}
        if request.dialect not in HOSTLESS_DIALECTS:
            if not host:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to resolve connection target for egress validation",
                )
            try:
                await egress_validator.validate_before_connect(host, port)
            except EgressValidationError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Connection target blocked by security policy",
                )

    user_id = user.get("sub", user.get("id", "unknown"))
    tenant_id = user.get("tenant_id", "default")

    # Determine secret_path/secret_key for DB storage
    secret_path = request.secret_path or ""
    secret_key = request.secret_key or ""

    # 1. Create DB row first (to get connection_id)
    create_data = DatabaseConnectionCreateData(
        name=request.name,
        description=request.description,
        dialect=request.dialect,
        host=request.host,
        port=request.port or DEFAULT_PORTS.get(request.dialect),
        database=request.database,
        project_id=request.project_id,
        account_id=request.account_id,
        warehouse_id=request.warehouse_id,
        ssl_mode=request.ssl_mode,
        secret_path=secret_path,
        secret_key=secret_key,
    )

    from sqlalchemy.exc import IntegrityError

    try:
        entity = await repo.create(create_data, owner_id=user_id, tenant_id=tenant_id)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A connection named '{request.name}' already exists",
        )

    # 2. Store credentials in Secrets Manager using connection_id as key
    if request.connection_method in ("credentials", "connection_string"):
        if not secrets_provider:
            # Rollback: delete the DB row
            await repo.delete(entity.id, tenant_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credential storage service is not available",
            )

        secret_path = f"/database/{tenant_id}/{request.dialect}"
        secret_key = str(entity.id)

        try:
            if request.connection_method == "credentials":
                import json

                credential_payload = json.dumps(
                    {
                        "host": request.host,
                        "port": request.port or DEFAULT_PORTS.get(request.dialect),
                        "database": request.database,
                        "username": request.username,
                        "password": request.password,
                        # Cloud-specific fields for BigQuery/Snowflake/Databricks
                        "project_id": request.project_id,
                        "account_id": request.account_id,
                        "warehouse_id": request.warehouse_id,
                    }
                )
                await secrets_provider.set_secret(f"{secret_path}/{secret_key}", credential_payload)
            elif request.connection_method == "connection_string":
                await secrets_provider.set_secret(f"{secret_path}/{secret_key}", request.connection_string or "")
        except Exception:
            logger.error("Failed to store credentials in Secrets Manager", exc_info=True)
            await repo.delete(entity.id, tenant_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to store credentials securely",
            )

        # 3. Update entity's secret_path/secret_key
        update_data = DatabaseConnectionUpdateData(
            secret_path=secret_path,
            secret_key=secret_key,
        )
        entity = await repo.update(entity.id, tenant_id, user_id, update_data)

    return _entity_to_response(entity)


@database_connections_router.get("/{connection_id}", response_model=DatabaseConnectionResponse)
async def get_database_connection(
    connection_id: UUID,
    user: CurrentUser,
    repo: Annotated[Any, Depends(get_db_conn_repository)],
) -> DatabaseConnectionResponse:
    """Get a database connection by ID."""
    tenant_id = user.get("tenant_id", "default")
    owner_id = user.get("sub", user.get("id", "unknown"))

    entity = await repo.get(connection_id, tenant_id=tenant_id, owner_id=owner_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    return _entity_to_response(entity)


@database_connections_router.patch("/{connection_id}", response_model=DatabaseConnectionResponse)
async def update_database_connection(
    connection_id: UUID,
    request: DatabaseConnectionUpdateRequest,
    user: CurrentUser,
    repo: Annotated[Any, Depends(get_db_conn_repository)],
    secrets_provider: Annotated[SecretsProvider, Depends(get_secrets_provider)] = None,  # type: ignore[assignment]
    tester: Annotated[Any, Depends(get_connection_tester)] = None,
    retest: bool = Query(False, description="Re-test connection after update"),
) -> DatabaseConnectionResponse:
    """Update a database connection.

    Supports both metadata updates and credential rotation.
    When credential fields (username, password, connection_string) are provided,
    the credentials are updated in Secrets Manager.

    Args:
        retest: If True, automatically test the connection after updating.
    """
    from mcp_server_langgraph.repositories.database_connections import (
        DatabaseConnectionUpdateData,
    )

    tenant_id = user.get("tenant_id", "default")
    owner_id = user.get("sub", user.get("id", "unknown"))

    # Validate ssl_mode if provided (same validation as create endpoint)
    if request.ssl_mode is not None and request.ssl_mode not in VALID_SSL_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ssl_mode '{request.ssl_mode}'. Must be one of: {', '.join(sorted(VALID_SSL_MODES))}",
        )

    # Check if connection exists first (needed for credential rotation)
    existing = await repo.get(connection_id, tenant_id=tenant_id, owner_id=owner_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    # Handle credential rotation if credential fields are provided
    # Include host/port/database and cloud fields as they are stored in Secrets Manager
    has_credential_update = any(
        field is not None
        for field in (
            request.username,
            request.password,
            request.connection_string,
            request.host,
            request.port,
            request.database,
            request.project_id,
            request.account_id,
            request.warehouse_id,
        )
    )

    if has_credential_update:
        if not secrets_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credential storage service is not available",
            )

        # Build the secret path from existing entity or construct new one
        secret_path = existing.secret_path or f"/database/{tenant_id}/{existing.dialect}"
        secret_key = existing.secret_key or str(connection_id)
        secret_id = f"{secret_path}/{secret_key}"

        try:
            import json

            # Get existing credentials to merge with updates
            existing_secret = await secrets_provider.get_secret(secret_id)
            if existing_secret:
                try:
                    existing_creds = json.loads(existing_secret)
                except json.JSONDecodeError:
                    # Connection string format
                    existing_creds = {"connection_string": existing_secret}
            else:
                existing_creds = {}

            if request.connection_string is not None:
                # Replace with connection string
                await secrets_provider.set_secret(secret_id, request.connection_string)
            else:
                # Merge credential updates
                if request.username is not None:
                    existing_creds["username"] = request.username
                if request.password is not None:
                    existing_creds["password"] = request.password
                if request.host is not None:
                    existing_creds["host"] = request.host
                if request.port is not None:
                    existing_creds["port"] = request.port
                if request.database is not None:
                    existing_creds["database"] = request.database
                # Cloud-specific fields
                if request.project_id is not None:
                    existing_creds["project_id"] = request.project_id
                if request.account_id is not None:
                    existing_creds["account_id"] = request.account_id
                if request.warehouse_id is not None:
                    existing_creds["warehouse_id"] = request.warehouse_id

                await secrets_provider.set_secret(secret_id, json.dumps(existing_creds))

        except Exception:
            logger.error("Failed to update credentials in Secrets Manager", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to update credentials securely",
            )

    # Update metadata fields in DB (including cloud-specific fields)
    update_data = DatabaseConnectionUpdateData(
        name=request.name,
        description=request.description,
        host=request.host,
        port=request.port,
        database=request.database,
        ssl_mode=request.ssl_mode,
        project_id=request.project_id,
        account_id=request.account_id,
        warehouse_id=request.warehouse_id,
    )

    entity = await repo.update(connection_id, tenant_id=tenant_id, owner_id=owner_id, data=update_data)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    # Optionally re-test the connection after update
    if retest and tester is not None:
        test_result = await tester.test(entity)
        test_status = "connected" if test_result.success else "error"
        await repo.update_test_result(
            connection_id,
            tenant_id=tenant_id,
            status=test_status,
            dialect_version=test_result.dialect_version,
        )
        # Refresh entity to get updated status
        entity = await repo.get(connection_id, tenant_id=tenant_id, owner_id=owner_id)

    return _entity_to_response(entity)


@database_connections_router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database_connection(
    connection_id: UUID,
    user: CurrentUser,
    repo: Annotated[Any, Depends(get_db_conn_repository)],
) -> None:
    """Delete a database connection."""
    tenant_id = user.get("tenant_id", "default")
    owner_id = user.get("sub", user.get("id", "unknown"))

    deleted = await repo.delete(connection_id, tenant_id=tenant_id, owner_id=owner_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )


@database_connections_router.post(
    "/{connection_id}/test",
    response_model=DatabaseConnectionTestResult,
)
async def test_database_connection(
    connection_id: UUID,
    user: CurrentUser,
    repo: Annotated[Any, Depends(get_db_conn_repository)],
    tester: Annotated[Any, Depends(get_connection_tester)],
) -> DatabaseConnectionTestResult:
    """Test a database connection.

    Retrieves the connection from the DB, resolves credentials from
    Secrets Manager, validates egress, and attempts a driver connection.
    Updates the connection status with the test result.
    """
    tenant_id = user.get("tenant_id", "default")
    owner_id = user.get("sub", user.get("id", "unknown"))

    entity = await repo.get(connection_id, tenant_id=tenant_id, owner_id=owner_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    result = await tester.test(entity)

    # Update test result in DB
    test_status = "connected" if result.success else "error"
    await repo.update_test_result(
        connection_id,
        tenant_id=tenant_id,
        status=test_status,
        dialect_version=result.dialect_version,
    )

    return DatabaseConnectionTestResult(
        success=result.success,
        error=result.error,
        dialect_version=result.dialect_version,
    )
