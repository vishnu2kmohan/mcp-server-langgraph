"""Database connection tester.

Tests database connectivity by resolving credentials, creating a
one-shot driver, executing ``SELECT 1``, and querying the dialect
version. Cleans up all resources in the ``finally`` block.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cachetools import TTLCache

from mcp_server_langgraph.execution.sql.credential_manager import (
    CredentialRetrievalError,
    SecureConnectionConfig,
    SecretsProvider,
)
from mcp_server_langgraph.execution.sql.exceptions import (
    EgressValidationError,
    sanitize_connection_error,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.execution.sql.drivers.base import DatabaseDriver
    from mcp_server_langgraph.execution.sql.drivers.registry import DriverRegistry
    from mcp_server_langgraph.network.egress_validator import RuntimeEgressValidator
    from mcp_server_langgraph.repositories.database_connections import (
        DatabaseConnectionEntity,
    )

logger = logging.getLogger(__name__)

# Dialects that are in-process or cloud-managed — no network egress
HOSTLESS_DIALECTS = frozenset({"sqlite", "duckdb", "bigquery"})

VERSION_QUERIES: dict[str, str] = {
    "postgres": "SELECT version()",
    "mysql": "SELECT version()",
    "sqlite": "SELECT sqlite_version()",
    "snowflake": "SELECT CURRENT_VERSION()",
    "bigquery": "SELECT 1",
    "duckdb": "SELECT version()",
    "redshift": "SELECT version()",
    "clickhouse": "SELECT version()",
    "trino": "SELECT version()",
}


@dataclass
class ConnectionTestResult:
    """Result of testing a database connection."""

    __test__ = False  # Prevent pytest collection

    success: bool
    error: str | None = None
    dialect_version: str | None = None


class ConnectionTester:
    """Tests database connections by resolving credentials and
    executing a health-check query.

    Args:
        driver_registry: Registry mapping dialects to driver classes.
        secrets_provider: Provider for resolving stored credentials.
        egress_validator: Optional egress validator for SSRF protection.
        timeout: Maximum time (seconds) for the entire test operation.
    """

    def __init__(
        self,
        driver_registry: DriverRegistry,
        secrets_provider: SecretsProvider,
        egress_validator: RuntimeEgressValidator | None = None,
        timeout: float = 15.0,
        credential_cache: TTLCache | None = None,
        credential_cache_lock: asyncio.Lock | None = None,
    ) -> None:
        self._registry = driver_registry
        self._secrets = secrets_provider
        self._egress = egress_validator
        self._timeout = timeout
        self._credential_cache = credential_cache
        self._credential_cache_lock = credential_cache_lock

    async def test(self, entity: DatabaseConnectionEntity) -> ConnectionTestResult:
        """Test a database connection end-to-end.

        Steps:
        1. Resolve credentials from Secrets Manager
        2. Validate egress (if validator present and not hostless dialect)
        3. Create one-shot driver and connect
        4. Execute SELECT 1 + version query
        5. Return result with dialect version

        Resources are cleaned up in the finally block regardless of outcome.
        """
        try:
            result = await asyncio.wait_for(
                self._do_test(entity),
                timeout=self._timeout,
            )
            return result
        except TimeoutError:
            return ConnectionTestResult(
                success=False,
                error="Connection timeout - server may be unreachable",
            )
        except asyncio.CancelledError:
            return ConnectionTestResult(
                success=False,
                error="Connection test was cancelled",
            )
        except Exception as exc:
            logger.warning("Connection test failed: %s", exc, exc_info=True)
            return ConnectionTestResult(
                success=False,
                error=sanitize_connection_error(exc),
            )

    async def _do_test(self, entity: DatabaseConnectionEntity) -> ConnectionTestResult:
        """Internal test flow with resource cleanup."""
        driver: DatabaseDriver | None = None
        resource: Any = None
        try:
            # 1. Resolve credentials
            config = SecureConnectionConfig(
                secrets_provider=self._secrets,
                dialect=entity.dialect,
                tenant_id=entity.tenant_id,
                cache=self._credential_cache,
                cache_lock=self._credential_cache_lock,
            )
            credentials = await config.get_credentials(entity.secret_path, entity.secret_key)

            # 2. Egress validation (skip for hostless dialects)
            # Resolve host/port from credentials for secret_ref/connection_string flows
            host = credentials.get("host") or entity.host
            port = credentials.get("port") or entity.port
            if "connection_string" in credentials:
                from mcp_server_langgraph.api.v1.database_connections import (
                    _resolve_host_from_connection_string,
                )

                resolved_host, resolved_port = _resolve_host_from_connection_string(credentials["connection_string"])
                host = resolved_host or host
                port = resolved_port or port

            if self._egress and entity.dialect not in HOSTLESS_DIALECTS:
                if not host:
                    return ConnectionTestResult(
                        success=False,
                        error="Unable to resolve connection target for validation",
                    )
                # SECURITY: Use resolved IP for connection to prevent DNS rebinding (TOCTOU)
                validated_ip, _ = await self._egress.validate_before_connect(host, port or 443)
                # Override the host with the validated IP to ensure we connect to the
                # same IP that was validated (prevents DNS rebinding attacks)
                credentials["host"] = validated_ip

            # 3. Create driver (per-dialect factory)
            driver, resource = await self._create_driver(entity.dialect, credentials)

            # 4. Connect + execute
            await driver.connect()
            await driver.execute("SELECT 1")

            # 5. Version query
            dialect_version = await self._get_version(driver, entity.dialect)

            return ConnectionTestResult(
                success=True,
                dialect_version=dialect_version,
            )
        except EgressValidationError:
            return ConnectionTestResult(
                success=False,
                error="Connection target blocked by security policy",
            )
        except CredentialRetrievalError as exc:
            return ConnectionTestResult(
                success=False,
                error=sanitize_connection_error(exc),
            )
        except Exception as exc:
            return ConnectionTestResult(
                success=False,
                error=sanitize_connection_error(exc),
            )
        finally:
            if driver is not None:
                try:
                    await driver.close()
                except Exception:
                    logger.debug("Failed to close driver during cleanup", exc_info=True)
            if resource is not None:
                try:
                    if hasattr(resource, "close"):
                        result = resource.close()
                        if asyncio.iscoroutine(result):
                            await result
                except Exception:
                    logger.debug("Failed to close resource during cleanup", exc_info=True)

    async def _create_driver(self, dialect: str, credentials: dict[str, Any]) -> tuple[DatabaseDriver, Any]:
        """Create a one-shot driver instance for the given dialect.

        Returns a tuple of (driver, resource_to_cleanup). The resource
        is a pool/connection/client that must be closed separately from
        the driver in the finally block.

        Each driver has a unique constructor signature, so we map
        credential fields to the correct arguments per dialect.
        """
        if dialect == "postgres":
            import asyncpg

            pool = await asyncpg.create_pool(
                host=credentials.get("host"),
                port=int(credentials.get("port") or 5432),
                user=credentials.get("username"),
                password=credentials.get("password"),
                database=credentials.get("database"),
                min_size=1,
                max_size=1,
                timeout=10,
            )
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(pool=pool), pool

        if dialect == "sqlite":
            db_path = credentials.get("db_path") or credentials.get("database") or ":memory:"
            # SECURITY: Validate path to prevent directory traversal attacks
            if db_path != ":memory:":
                import os

                allowed_dir = os.environ.get("SQLITE_DATA_DIR", "/data")
                abs_path = os.path.abspath(db_path)
                if not abs_path.startswith(os.path.abspath(allowed_dir) + os.sep):
                    raise ValueError(f"SQLite path must be within {allowed_dir}")
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(db_path=db_path), None

        if dialect == "duckdb":
            db_path = credentials.get("db_path") or credentials.get("database") or ":memory:"
            # SECURITY: Validate path to prevent directory traversal attacks
            if db_path != ":memory:":
                import os

                allowed_dir = os.environ.get("DUCKDB_DATA_DIR", "/data")
                abs_path = os.path.abspath(db_path)
                if not abs_path.startswith(os.path.abspath(allowed_dir) + os.sep):
                    raise ValueError(f"DuckDB path must be within {allowed_dir}")
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(db_path=db_path), None

        if dialect == "bigquery":
            project = credentials.get("project_id") or credentials.get("project", "")
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(project=project), None

        if dialect == "mysql":
            import aiomysql  # type: ignore[import-untyped]

            pool = await aiomysql.create_pool(
                host=credentials.get("host") or "localhost",
                port=int(credentials.get("port") or 3306),
                user=credentials.get("username") or "",
                password=credentials.get("password") or "",
                db=credentials.get("database") or "",
                minsize=1,
                maxsize=1,
                connect_timeout=10,
            )
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(pool=pool), pool

        if dialect == "redshift":
            import redshift_connector  # type: ignore[import-untyped]

            # Run sync connector in thread executor to avoid blocking event loop
            conn = await asyncio.to_thread(
                redshift_connector.connect,
                host=credentials.get("host") or "localhost",
                port=int(credentials.get("port") or 5439),
                user=credentials.get("username") or "",
                password=credentials.get("password") or "",
                database=credentials.get("database") or "",
            )
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(connection=conn), conn

        if dialect == "snowflake":
            import snowflake.connector  # type: ignore[import-untyped]

            # Run sync connector in thread executor to avoid blocking event loop
            conn = await asyncio.to_thread(
                snowflake.connector.connect,
                account=credentials.get("account_id") or "",
                user=credentials.get("username") or "",
                password=credentials.get("password") or "",
                warehouse=credentials.get("warehouse_id") or "",
                database=credentials.get("database") or "",
            )
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(connection=conn), conn

        if dialect == "clickhouse":
            import asynch  # type: ignore[import-untyped]

            client = await asynch.connect(
                host=credentials.get("host") or "localhost",
                port=int(credentials.get("port") or 9000),
                user=credentials.get("username") or "default",
                password=credentials.get("password") or "",
                database=credentials.get("database") or "default",
            )
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(client=client), client

        if dialect == "trino":
            from trino.dbapi import connect as trino_connect  # type: ignore[import-untyped]

            # Run sync connector in thread executor to avoid blocking event loop
            conn = await asyncio.to_thread(
                trino_connect,
                host=credentials.get("host") or "localhost",
                port=int(credentials.get("port") or 8080),
                user=credentials.get("username") or "",
                catalog=credentials.get("catalog") or "",
                schema=credentials.get("schema") or "",
            )
            driver_cls = self._registry.get_driver(dialect)
            return driver_cls(connection=conn), conn

        # Fallback: unknown dialect
        raise KeyError(f"No driver factory for dialect '{dialect}'")

    async def _get_version(self, driver: DatabaseDriver, dialect: str) -> str | None:
        """Execute version query and extract version string."""
        query = VERSION_QUERIES.get(dialect)
        if not query:
            return None

        try:
            rows = await driver.execute(query)
            if rows:
                # Most version queries return a single column
                first_row = rows[0]
                # Get the first value from the row dict
                return str(next(iter(first_row.values())))
        except Exception:
            logger.debug("Version query failed for dialect %s", dialect, exc_info=True)

        return None
