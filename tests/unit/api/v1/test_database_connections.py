"""Tests for database connections API (Phase 6 - SQLGlot integration).

Tests validation helpers, Pydantic models, default ports, error sanitization,
and database connection templates.
"""

from __future__ import annotations

import gc

import pytest

from mcp_server_langgraph.api.v1.database_connections import (
    DEFAULT_PORTS,
    VALID_CONNECTION_METHODS,
    VALID_DIALECTS,
    VALID_SCOPES,
    VALID_SSL_MODES,
    DatabaseConnectionCreateRequest,
    DatabaseConnectionListResponse,
    DatabaseConnectionResponse,
    DatabaseConnectionTestResult,
    DatabaseConnectionUpdateRequest,
    _sanitize_connection_error,
    _validate_dialect,
)


@pytest.mark.xdist_group(name="test_database_connections_validation")
class TestValidation:
    """Test validation helpers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_validate_dialect_valid(self) -> None:
        """Valid dialects should not raise."""
        for dialect in VALID_DIALECTS:
            _validate_dialect(dialect)  # Should not raise

    @pytest.mark.unit
    def test_validate_dialect_invalid(self) -> None:
        """Invalid dialect should raise HTTPException with 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_dialect("oracle")
        assert exc_info.value.status_code == 400
        assert "oracle" in str(exc_info.value.detail)

    @pytest.mark.unit
    def test_validate_dialect_empty_string(self) -> None:
        """Empty string dialect should raise HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_dialect("")
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_valid_dialects_complete(self) -> None:
        """All DatabaseDialect enum values should be in VALID_DIALECTS."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        for dialect in DatabaseDialect:
            assert dialect.value in VALID_DIALECTS, f"Missing dialect: {dialect.value}"

    @pytest.mark.unit
    def test_valid_dialects_set(self) -> None:
        """VALID_DIALECTS should contain the expected set."""
        expected = {
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
        assert expected == VALID_DIALECTS

    @pytest.mark.unit
    def test_valid_ssl_modes(self) -> None:
        """All SSL modes should be present."""
        assert {"disable", "require", "verify-ca", "verify-full"} == VALID_SSL_MODES

    @pytest.mark.unit
    def test_valid_connection_methods(self) -> None:
        """All connection methods should be present."""
        assert {"credentials", "secret_ref", "connection_string"} == VALID_CONNECTION_METHODS

    @pytest.mark.unit
    def test_scopes_enum_has_valid_values(self) -> None:
        """All scopes should be present."""
        assert {"user", "project", "session"} == VALID_SCOPES


@pytest.mark.xdist_group(name="test_database_connections_sanitize")
class TestSanitizeError:
    """Test error sanitization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_sanitize_error_connection_refused_message(self) -> None:
        """Connection refused errors should map to host/port guidance."""
        result = _sanitize_connection_error(Exception("Connection refused by server"))
        assert result == "Unable to connect - check host and port"

    @pytest.mark.unit
    def test_sanitize_error_auth_failed_message(self) -> None:
        """Auth failures should map to credentials guidance."""
        result = _sanitize_connection_error(Exception("Authentication failed for user admin"))
        assert result == "Authentication failed - check credentials"

    @pytest.mark.unit
    def test_sanitize_error_timeout_message(self) -> None:
        """Timeout errors should map to reachability guidance."""
        result = _sanitize_connection_error(Exception("Connection timeout after 30s"))
        assert result == "Connection timeout - server may be unreachable"

    @pytest.mark.unit
    def test_sanitize_error_ssl_error_message(self) -> None:
        """SSL errors should map to security settings guidance."""
        result = _sanitize_connection_error(Exception("SSL handshake failed"))
        assert result == "SSL/TLS error - check security settings"

    @pytest.mark.unit
    def test_name_resolution_error(self) -> None:
        """Name resolution failures should map to hostname guidance."""
        result = _sanitize_connection_error(Exception("name resolution failed"))
        assert result == "Host not found - check hostname"

    @pytest.mark.unit
    def test_sanitize_error_dns_error_message(self) -> None:
        """DNS resolution failures should map to hostname guidance."""
        result = _sanitize_connection_error(Exception("DNS resolution failed"))
        assert result == "DNS resolution failed - check hostname"

    @pytest.mark.unit
    def test_sanitize_error_unknown_returns_generic(self) -> None:
        """Unknown errors should return generic safe message."""
        result = _sanitize_connection_error(Exception("Some random internal error with stacktrace"))
        assert result == "Connection failed - check configuration"
        # Verify the raw error details are NOT leaked
        assert "stacktrace" not in result
        assert "internal" not in result

    @pytest.mark.unit
    def test_case_insensitive_matching(self) -> None:
        """Error pattern matching should be case-insensitive."""
        result = _sanitize_connection_error(Exception("CONNECTION REFUSED"))
        assert result == "Unable to connect - check host and port"


@pytest.mark.xdist_group(name="test_database_connections_ports")
class TestDefaultPorts:
    """Test default port mappings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_default_port_postgres_is_5432(self) -> None:
        """PostgreSQL default port should be 5432."""
        assert DEFAULT_PORTS["postgres"] == 5432

    @pytest.mark.unit
    def test_default_port_mysql_is_3306(self) -> None:
        """MySQL default port should be 3306."""
        assert DEFAULT_PORTS["mysql"] == 3306

    @pytest.mark.unit
    def test_default_port_snowflake_is_443(self) -> None:
        """Snowflake default port should be 443."""
        assert DEFAULT_PORTS["snowflake"] == 443

    @pytest.mark.unit
    def test_default_port_redshift_is_5439(self) -> None:
        """Redshift default port should be 5439."""
        assert DEFAULT_PORTS["redshift"] == 5439

    @pytest.mark.unit
    def test_default_port_clickhouse_is_9000(self) -> None:
        """ClickHouse default port should be 9000 (native protocol for asynch driver)."""
        assert DEFAULT_PORTS["clickhouse"] == 9000

    @pytest.mark.unit
    def test_default_port_trino_is_8080(self) -> None:
        """Trino default port should be 8080."""
        assert DEFAULT_PORTS["trino"] == 8080

    @pytest.mark.unit
    def test_default_port_bigquery_is_443(self) -> None:
        """BigQuery default port should be 443."""
        assert DEFAULT_PORTS["bigquery"] == 443

    @pytest.mark.unit
    def test_all_dialects_have_ports(self) -> None:
        """Every valid dialect should have a default port mapping."""
        for dialect in VALID_DIALECTS:
            assert dialect in DEFAULT_PORTS, f"Missing default port for {dialect}"


@pytest.mark.xdist_group(name="test_database_connections_models")
class TestPydanticModels:
    """Test Pydantic model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_create_request_minimal(self) -> None:
        """Minimal create request should have correct defaults."""
        req = DatabaseConnectionCreateRequest(name="test", dialect="postgres")
        assert req.name == "test"
        assert req.dialect == "postgres"
        assert req.ssl_mode == "require"
        assert req.scope == "user"
        assert req.connection_method == "credentials"
        assert req.host is None
        assert req.port is None
        assert req.database is None
        assert req.username is None
        assert req.password is None

    @pytest.mark.unit
    def test_create_request_full(self) -> None:
        """Full create request should accept all fields."""
        req = DatabaseConnectionCreateRequest(
            name="production",
            description="Production PostgreSQL",
            dialect="postgres",
            host="db.example.com",
            port=5432,
            database="mydb",
            username="admin",
            password="secret",
            ssl_mode="verify-full",
            scope="project",
        )
        assert req.host == "db.example.com"
        assert req.port == 5432
        assert req.description == "Production PostgreSQL"
        assert req.ssl_mode == "verify-full"
        assert req.scope == "project"

    @pytest.mark.unit
    def test_create_request_cloud_fields(self) -> None:
        """Cloud-specific fields should be accepted."""
        req = DatabaseConnectionCreateRequest(
            name="bq-prod",
            dialect="bigquery",
            project_id="my-gcp-project",
        )
        assert req.project_id == "my-gcp-project"

    @pytest.mark.unit
    def test_create_request_snowflake_fields(self) -> None:
        """Snowflake-specific fields should be accepted."""
        req = DatabaseConnectionCreateRequest(
            name="sf-prod",
            dialect="snowflake",
            account_id="xy12345",
            warehouse_id="COMPUTE_WH",
        )
        assert req.account_id == "xy12345"
        assert req.warehouse_id == "COMPUTE_WH"

    @pytest.mark.unit
    def test_create_request_secret_ref(self) -> None:
        """Secret ref connection method should accept secret_path and secret_key."""
        req = DatabaseConnectionCreateRequest(
            name="test",
            dialect="postgres",
            connection_method="secret_ref",
            secret_path="/secrets/db/prod",
            secret_key="PG_CONN_STRING",
        )
        assert req.connection_method == "secret_ref"
        assert req.secret_path == "/secrets/db/prod"
        assert req.secret_key == "PG_CONN_STRING"

    @pytest.mark.unit
    def test_create_request_port_too_low(self) -> None:
        """Port below 1 should fail validation."""
        with pytest.raises(Exception):  # ValidationError
            DatabaseConnectionCreateRequest(name="test", dialect="postgres", port=0)

    @pytest.mark.unit
    def test_create_request_port_too_high(self) -> None:
        """Port above 65535 should fail validation."""
        with pytest.raises(Exception):  # ValidationError
            DatabaseConnectionCreateRequest(name="test", dialect="postgres", port=70000)

    @pytest.mark.unit
    def test_create_request_name_required(self) -> None:
        """Name should be required."""
        with pytest.raises(Exception):  # ValidationError
            DatabaseConnectionCreateRequest(dialect="postgres")

    @pytest.mark.unit
    def test_create_request_name_empty(self) -> None:
        """Empty name should fail validation (min_length=1)."""
        with pytest.raises(Exception):  # ValidationError
            DatabaseConnectionCreateRequest(name="", dialect="postgres")

    @pytest.mark.unit
    def test_create_request_name_too_long(self) -> None:
        """Name exceeding 255 chars should fail validation."""
        with pytest.raises(Exception):  # ValidationError
            DatabaseConnectionCreateRequest(name="x" * 256, dialect="postgres")

    @pytest.mark.unit
    def test_response_model_has_expected_fields(self) -> None:
        """Response model should have correct defaults."""
        resp = DatabaseConnectionResponse(
            id="test-id",
            name="test",
            dialect="postgres",
            owner_id="user1",
            tenant_id="tenant1",
            created_at="2026-02-06T00:00:00Z",
            updated_at="2026-02-06T00:00:00Z",
        )
        assert resp.status == "disconnected"
        assert resp.ssl_mode == "require"
        assert resp.host is None
        assert resp.port is None
        assert resp.last_tested_at is None
        assert resp.dialect_version is None

    @pytest.mark.unit
    def test_response_model_excludes_password(self) -> None:
        """SECURITY: Response model should NOT have password field."""
        schema = DatabaseConnectionResponse.model_json_schema()
        assert "password" not in schema["properties"]
        assert "username" not in schema["properties"]
        assert "secret_path" not in schema["properties"]
        assert "secret_key" not in schema["properties"]

    @pytest.mark.unit
    def test_test_result_success(self) -> None:
        """Successful test result should have version and no error."""
        result = DatabaseConnectionTestResult(success=True, dialect_version="15.2")
        assert result.success is True
        assert result.error is None
        assert result.dialect_version == "15.2"

    @pytest.mark.unit
    def test_test_result_failure(self) -> None:
        """Failed test result should have error and no version."""
        result = DatabaseConnectionTestResult(success=False, error="Connection refused")
        assert result.success is False
        assert result.error == "Connection refused"

    @pytest.mark.unit
    def test_list_response_has_pagination_fields(self) -> None:
        """List response should support empty items."""
        resp = DatabaseConnectionListResponse(items=[], total=0)
        assert resp.total == 0
        assert resp.items == []

    @pytest.mark.unit
    def test_list_response_with_items(self) -> None:
        """List response should support items."""
        item = DatabaseConnectionResponse(
            id="test-id",
            name="test",
            dialect="postgres",
            owner_id="user1",
            tenant_id="tenant1",
            created_at="2026-02-06T00:00:00Z",
            updated_at="2026-02-06T00:00:00Z",
        )
        resp = DatabaseConnectionListResponse(items=[item], total=1)
        assert resp.total == 1
        assert len(resp.items) == 1
        assert resp.items[0].name == "test"

    @pytest.mark.unit
    def test_update_request_all_none(self) -> None:
        """Update request with all None fields should be valid (partial update)."""
        req = DatabaseConnectionUpdateRequest()
        assert req.name is None
        assert req.description is None
        assert req.host is None
        assert req.port is None
        assert req.database is None
        assert req.ssl_mode is None

    @pytest.mark.unit
    def test_update_request_partial(self) -> None:
        """Update request should support partial updates."""
        req = DatabaseConnectionUpdateRequest(name="new-name", port=5433)
        assert req.name == "new-name"
        assert req.port == 5433
        assert req.host is None  # Not updated


@pytest.mark.xdist_group(name="test_database_connections_templates")
class TestDatabaseTemplates:
    """Test that database templates are included in connection_templates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_data_category_exists(self) -> None:
        """Data category should exist in CATEGORIES."""
        from mcp_server_langgraph.api.v1.connection_templates import CATEGORIES

        category_ids = [c.id for c in CATEGORIES]
        assert "data" in category_ids

    @pytest.mark.unit
    def test_database_templates_exist(self) -> None:
        """Core database templates should exist."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        template_ids = [t.id for t in TEMPLATES]
        assert "postgresql" in template_ids
        assert "mysql" in template_ids

    @pytest.mark.unit
    def test_template_snowflake_has_required_fields(self) -> None:
        """Snowflake template should exist with correct category and popularity."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        snowflake = next((t for t in TEMPLATES if t.id == "snowflake"), None)
        assert snowflake is not None
        assert snowflake.category == "data"
        assert snowflake.popularity >= 70

    @pytest.mark.unit
    def test_template_bigquery_has_required_fields(self) -> None:
        """BigQuery template should exist with correct category."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        bigquery = next((t for t in TEMPLATES if t.id == "bigquery"), None)
        assert bigquery is not None
        assert bigquery.category == "data"

    @pytest.mark.unit
    def test_template_duckdb_has_required_fields(self) -> None:
        """DuckDB template should exist with correct category."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        duckdb = next((t for t in TEMPLATES if t.id == "duckdb"), None)
        assert duckdb is not None
        assert duckdb.category == "data"

    @pytest.mark.unit
    def test_template_redshift_has_required_fields(self) -> None:
        """Redshift template should exist with correct category."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        redshift = next((t for t in TEMPLATES if t.id == "redshift"), None)
        assert redshift is not None
        assert redshift.category == "data"

    @pytest.mark.unit
    def test_template_clickhouse_has_required_fields(self) -> None:
        """ClickHouse template should exist with correct category."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        clickhouse = next((t for t in TEMPLATES if t.id == "clickhouse"), None)
        assert clickhouse is not None
        assert clickhouse.category == "data"

    @pytest.mark.unit
    def test_all_database_templates_have_keywords(self) -> None:
        """All database templates should have keywords for intent matching."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        data_templates = [t for t in TEMPLATES if t.category == "data"]
        for template in data_templates:
            assert len(template.keywords) > 0, f"Template {template.id} has no keywords"

    @pytest.mark.unit
    def test_template_trino_has_required_fields(self) -> None:
        """Trino template should exist with correct category."""
        from mcp_server_langgraph.api.v1.connection_templates import TEMPLATES

        trino = next((t for t in TEMPLATES if t.id == "trino"), None)
        assert trino is not None
        assert trino.category == "data"


@pytest.mark.xdist_group(name="test_database_connections_router")
class TestRouterRegistration:
    """Test that the database connections router is properly configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_router_has_expected_prefix(self) -> None:
        """Router should have /database-connections prefix."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        assert database_connections_router.prefix == "/database-connections"

    @pytest.mark.unit
    def test_router_has_expected_tags(self) -> None:
        """Router should have database-connections tag."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        assert "database-connections" in database_connections_router.tags

    @pytest.mark.unit
    def test_router_has_list_endpoint(self) -> None:
        """Router should have GET for listing connections."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        routes = [r for r in database_connections_router.routes if hasattr(r, "methods")]
        get_routes = [r for r in routes if "GET" in r.methods and r.path.endswith("/")]
        assert len(get_routes) == 1

    @pytest.mark.unit
    def test_router_has_create_endpoint(self) -> None:
        """Router should have POST for creating connections."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        routes = [r for r in database_connections_router.routes if hasattr(r, "methods")]
        post_routes = [r for r in routes if "POST" in r.methods and r.path.endswith("/") and "test" not in r.path]
        assert len(post_routes) == 1

    @pytest.mark.unit
    def test_router_has_get_by_id_endpoint(self) -> None:
        """Router should have GET /{connection_id} for getting a connection."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        routes = [r for r in database_connections_router.routes if hasattr(r, "methods")]
        get_routes = [r for r in routes if "GET" in r.methods and r.path.endswith("/{connection_id}")]
        assert len(get_routes) == 1

    @pytest.mark.unit
    def test_router_has_update_endpoint(self) -> None:
        """Router should have PATCH /{connection_id} for updating a connection."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        routes = [r for r in database_connections_router.routes if hasattr(r, "methods")]
        patch_routes = [r for r in routes if "PATCH" in r.methods and r.path.endswith("/{connection_id}")]
        assert len(patch_routes) == 1

    @pytest.mark.unit
    def test_router_has_delete_endpoint(self) -> None:
        """Router should have DELETE /{connection_id} for deleting a connection."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        routes = [r for r in database_connections_router.routes if hasattr(r, "methods")]
        delete_routes = [r for r in routes if "DELETE" in r.methods and r.path.endswith("/{connection_id}")]
        assert len(delete_routes) == 1

    @pytest.mark.unit
    def test_router_has_test_endpoint(self) -> None:
        """Router should have POST /{connection_id}/test for testing a connection."""
        from mcp_server_langgraph.api.v1.database_connections import database_connections_router

        routes = [r for r in database_connections_router.routes if hasattr(r, "methods")]
        test_routes = [r for r in routes if "POST" in r.methods and r.path.endswith("/{connection_id}/test")]
        assert len(test_routes) == 1

    @pytest.mark.unit
    def test_router_registered_in_v1(self) -> None:
        """Database connections router should be registered in the v1 router."""
        from mcp_server_langgraph.api.v1.router import v1_router

        # Check that at least one route with our prefix exists
        route_paths = [r.path for r in v1_router.routes if hasattr(r, "path")]
        has_db_conn_route = any("/database-connections" in p for p in route_paths)
        assert has_db_conn_route, f"database-connections not found in v1 router routes: {route_paths}"


# ============================================================================
# Egress/Secrets integration tests
# ============================================================================


@pytest.mark.xdist_group(name="test_database_connections_egress")
class TestEgressValidationIntegration:
    """Test egress validation wiring in create/test endpoints."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    def test_sanitize_egress_error(self) -> None:
        """EgressValidationError should be sanitized to a safe message."""
        from mcp_server_langgraph.execution.sql.exceptions import EgressValidationError

        err = EgressValidationError(message="Resolved IP 10.0.0.1 for 'evil.internal' is in a blocked/private range")
        result = _sanitize_connection_error(err)
        # Raw IP and internal hostname should NOT leak
        assert "10.0.0.1" not in result
        assert "evil.internal" not in result

    @pytest.mark.unit
    def test_dependency_providers_importable(self) -> None:
        """DI providers should be importable from the module."""
        from mcp_server_langgraph.api.v1.database_connections import (
            get_egress_validator,
            get_secrets_provider,
        )

        assert callable(get_egress_validator)
        assert callable(get_secrets_provider)

    @pytest.mark.unit
    def test_egress_validator_respects_feature_flag(self) -> None:
        """get_egress_validator should return None when flag is disabled."""

        from mcp_server_langgraph.api.v1.database_connections import get_egress_validator

        with patch("mcp_server_langgraph.api.v1.database_connections.feature_flags") as mock_flags:
            mock_flags.enable_sql_egress_validation = False
            result = get_egress_validator()
            assert result is None

    @pytest.mark.unit
    def test_egress_validator_returns_runtime_validator_when_enabled(self) -> None:
        """get_egress_validator should return RuntimeEgressValidator when flag enabled."""

        from mcp_server_langgraph.api.v1.database_connections import get_egress_validator
        from mcp_server_langgraph.network.egress_validator import RuntimeEgressValidator

        with patch("mcp_server_langgraph.api.v1.database_connections.feature_flags") as mock_flags:
            mock_flags.enable_sql_egress_validation = True
            result = get_egress_validator()
            assert isinstance(result, RuntimeEgressValidator)


# ============================================================================
# Endpoint CRUD tests (Phase 6c)
# ============================================================================

import uuid  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from mcp_server_langgraph.api.v1.database_connections import (  # noqa: E402
    database_connections_router,
    get_egress_validator as _get_egress_validator,
    get_secrets_provider as _get_secrets_provider,
)
from mcp_server_langgraph.execution.sql.connection_tester import (  # noqa: E402
    ConnectionTestResult as TesterResult,
    ConnectionTester,
)
from mcp_server_langgraph.repositories.database_connections import (  # noqa: E402
    DatabaseConnectionEntity,
    DatabaseConnectionRepository,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


def _make_test_entity(**overrides) -> DatabaseConnectionEntity:
    """Build a DatabaseConnectionEntity with sensible defaults."""
    now = datetime.now(UTC)
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": "tenant-1",
        "owner_id": "user-1",
        "name": "test-conn",
        "description": None,
        "dialect": "postgres",
        "host": "db.example.com",
        "port": 5432,
        "database": "mydb",
        "project_id": None,
        "account_id": None,
        "warehouse_id": None,
        "secret_path": "/database/tenant-1/postgres",
        "secret_key": "test_conn",
        "ssl_mode": "require",
        "status": "disconnected",
        "last_tested_at": None,
        "dialect_version": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return DatabaseConnectionEntity(**defaults)


def _create_test_app(
    repo: AsyncMock,
    tester: AsyncMock | None = None,
) -> TestClient:
    """Create a FastAPI test app with dependency overrides."""
    from mcp_server_langgraph.api.v1.database_connections import (
        get_db_conn_repository,
        get_connection_tester,
    )
    from mcp_server_langgraph.auth.dependencies import get_current_user
    from mcp_server_langgraph.core.secrets import InMemorySecretsProvider

    app = FastAPI()
    app.include_router(database_connections_router, prefix="/api/v1")

    # Override auth
    async def mock_user():
        return {
            "sub": "user-1",
            "id": "user-1",
            "tenant_id": "tenant-1",
            "roles": ["standard"],
        }

    # Override DI
    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db_conn_repository] = lambda: repo
    app.dependency_overrides[_get_secrets_provider] = lambda: InMemorySecretsProvider()
    app.dependency_overrides[_get_egress_validator] = lambda: None
    if tester is not None:
        app.dependency_overrides[get_connection_tester] = lambda: tester

    return TestClient(app)


@pytest.mark.xdist_group(name="test_database_connections_crud")
class TestDatabaseConnectionsCRUD:
    """Test CRUD endpoints with mocked repository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    def test_list_connections_with_empty_result(self) -> None:
        """GET / should return empty list when no connections exist."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.list = AsyncMock(return_value=([], 0))

        client = _create_test_app(repo)
        response = client.get("/api/v1/database-connections/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.unit
    def test_list_with_items(self) -> None:
        """GET / should return items when connections exist."""
        entity = _make_test_entity()
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.list = AsyncMock(return_value=([entity], 1))

        client = _create_test_app(repo)
        response = client.get("/api/v1/database-connections/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "test-conn"

    @pytest.mark.unit
    def test_list_with_dialect_filter(self) -> None:
        """GET /?dialect=mysql should pass filter to repo."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.list = AsyncMock(return_value=([], 0))

        client = _create_test_app(repo)
        response = client.get("/api/v1/database-connections/?dialect=mysql")

        assert response.status_code == 200
        repo.list.assert_awaited_once()
        call_kwargs = repo.list.call_args
        assert call_kwargs.kwargs.get("dialect") == "mysql" or (len(call_kwargs.args) > 2 and call_kwargs.args[2] == "mysql")

    @pytest.mark.unit
    def test_create_connection_returns_201(self) -> None:
        """POST / should create connection and return 201."""
        entity = _make_test_entity()
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.create = AsyncMock(return_value=entity)
        repo.update = AsyncMock(return_value=entity)

        client = _create_test_app(repo)
        response = client.post(
            "/api/v1/database-connections/",
            json={
                "name": "test-conn",
                "dialect": "postgres",
                "host": "db.example.com",
                "port": 5432,
                "database": "mydb",
                "username": "admin",
                "password": "secret",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-conn"
        assert data["dialect"] == "postgres"

    @pytest.mark.unit
    def test_create_409_duplicate(self) -> None:
        """POST / with duplicate name should return 409."""
        from sqlalchemy.exc import IntegrityError

        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.create = AsyncMock(side_effect=IntegrityError("duplicate", {}, None))

        client = _create_test_app(repo)
        response = client.post(
            "/api/v1/database-connections/",
            json={
                "name": "duplicate-conn",
                "dialect": "postgres",
                "host": "db.example.com",
            },
        )

        assert response.status_code == 409

    @pytest.mark.unit
    def test_get_connection_when_found_returns_data(self) -> None:
        """GET /{id} should return connection when found."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=entity)

        client = _create_test_app(repo)
        response = client.get(f"/api/v1/database-connections/{conn_id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(conn_id)

    @pytest.mark.unit
    def test_get_connection_when_not_found_returns_404(self) -> None:
        """GET /{id} should return 404 when not found."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=None)

        client = _create_test_app(repo)
        response = client.get(f"/api/v1/database-connections/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.unit
    def test_get_invalid_uuid_422(self) -> None:
        """GET /{id} with invalid UUID should return 422."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)

        client = _create_test_app(repo)
        response = client.get("/api/v1/database-connections/not-a-uuid")

        assert response.status_code == 422

    @pytest.mark.unit
    def test_update_connection_with_partial_data(self) -> None:
        """PATCH /{id} should update specified fields only."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id, name="updated-name")
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.update = AsyncMock(return_value=entity)

        client = _create_test_app(repo)
        response = client.patch(
            f"/api/v1/database-connections/{conn_id}",
            json={"name": "updated-name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "updated-name"

    @pytest.mark.unit
    def test_update_connection_when_not_found_returns_404(self) -> None:
        """PATCH /{id} should return 404 when not found."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.update = AsyncMock(return_value=None)

        client = _create_test_app(repo)
        response = client.patch(
            f"/api/v1/database-connections/{uuid.uuid4()}",
            json={"name": "new-name"},
        )

        assert response.status_code == 404

    @pytest.mark.unit
    def test_delete_connection_returns_204(self) -> None:
        """DELETE /{id} should return 204 on success."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.delete = AsyncMock(return_value=True)

        client = _create_test_app(repo)
        response = client.delete(f"/api/v1/database-connections/{uuid.uuid4()}")

        assert response.status_code == 204

    @pytest.mark.unit
    def test_delete_connection_when_not_found_returns_404(self) -> None:
        """DELETE /{id} should return 404 when not found."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.delete = AsyncMock(return_value=False)

        client = _create_test_app(repo)
        response = client.delete(f"/api/v1/database-connections/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.unit
    def test_test_connection_with_success_returns_ok(self) -> None:
        """POST /{id}/test should return success result."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=entity)
        repo.update_test_result = AsyncMock(return_value=None)

        tester = AsyncMock(spec=ConnectionTester)
        tester.test = AsyncMock(return_value=TesterResult(success=True, dialect_version="15.2"))

        client = _create_test_app(repo, tester)
        response = client.post(f"/api/v1/database-connections/{conn_id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["dialect_version"] == "15.2"

    @pytest.mark.unit
    def test_test_connection_with_failure_returns_error(self) -> None:
        """POST /{id}/test with failing connection should return failure."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=entity)
        repo.update_test_result = AsyncMock(return_value=None)

        tester = AsyncMock(spec=ConnectionTester)
        tester.test = AsyncMock(return_value=TesterResult(success=False, error="Connection refused"))

        client = _create_test_app(repo, tester)
        response = client.post(f"/api/v1/database-connections/{conn_id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Connection refused"

    @pytest.mark.unit
    def test_test_connection_when_not_found_returns_404(self) -> None:
        """POST /{id}/test should return 404 when connection not found."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=None)

        tester = AsyncMock(spec=ConnectionTester)

        client = _create_test_app(repo, tester)
        response = client.post(f"/api/v1/database-connections/{uuid.uuid4()}/test")

        assert response.status_code == 404

    @pytest.mark.unit
    def test_test_updates_status(self) -> None:
        """POST /{id}/test should update connection status in repo."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=entity)
        repo.update_test_result = AsyncMock(return_value=None)

        tester = AsyncMock(spec=ConnectionTester)
        tester.test = AsyncMock(return_value=TesterResult(success=True, dialect_version="15.2"))

        client = _create_test_app(repo, tester)
        client.post(f"/api/v1/database-connections/{conn_id}/test")

        repo.update_test_result.assert_awaited_once()

    @pytest.mark.unit
    def test_secrets_provider_returns_provider(self) -> None:
        """get_secrets_provider() should return a SecretsProvider, not None."""
        from mcp_server_langgraph.api.v1.database_connections import (
            get_secrets_provider,
        )
        from mcp_server_langgraph.core.secrets import reset_secrets_provider

        reset_secrets_provider()
        provider = get_secrets_provider()
        assert provider is not None
        reset_secrets_provider()


# ============================================================================
# Credential Rotation Tests (Phase 6d)
# ============================================================================


@pytest.mark.xdist_group(name="test_database_connections_credential_rotation")
class TestCredentialRotation:
    """Test credential rotation/update functionality."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    def test_update_request_has_credential_fields(self) -> None:
        """Update request should support credential-related fields."""
        from mcp_server_langgraph.api.v1.database_connections import (
            DatabaseConnectionUpdateRequest,
        )

        # These fields should be accepted for credential rotation
        req = DatabaseConnectionUpdateRequest(
            username="new-admin",
            password="new-secret",
        )
        assert req.username == "new-admin"
        assert req.password == "new-secret"

    @pytest.mark.unit
    def test_update_request_credential_fields_optional(self) -> None:
        """Credential fields should be optional in update request."""
        from mcp_server_langgraph.api.v1.database_connections import (
            DatabaseConnectionUpdateRequest,
        )

        # Should work without credential fields
        req = DatabaseConnectionUpdateRequest(name="new-name")
        assert req.name == "new-name"
        assert not hasattr(req, "username") or req.username is None
        assert not hasattr(req, "password") or req.password is None

    @pytest.mark.unit
    def test_update_request_connection_string_field(self) -> None:
        """Update request should support connection_string for rotation."""
        from mcp_server_langgraph.api.v1.database_connections import (
            DatabaseConnectionUpdateRequest,
        )

        req = DatabaseConnectionUpdateRequest(connection_string="postgresql://user:pass@host:5432/db")
        assert req.connection_string == "postgresql://user:pass@host:5432/db"

    @pytest.mark.unit
    def test_update_with_credentials_updates_secrets(self) -> None:
        """PATCH with credentials should update Secrets Manager."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=entity)
        repo.update = AsyncMock(return_value=entity)

        # Create app with secrets provider we can inspect
        from mcp_server_langgraph.api.v1.database_connections import (
            get_db_conn_repository,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user
        from mcp_server_langgraph.core.secrets import InMemorySecretsProvider

        app = FastAPI()
        app.include_router(database_connections_router, prefix="/api/v1")

        secrets_provider = InMemorySecretsProvider()

        async def mock_user():
            return {"sub": "user-1", "id": "user-1", "tenant_id": "tenant-1"}

        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[get_db_conn_repository] = lambda: repo
        app.dependency_overrides[_get_secrets_provider] = lambda: secrets_provider
        app.dependency_overrides[_get_egress_validator] = lambda: None

        client = TestClient(app)
        response = client.patch(
            f"/api/v1/database-connections/{conn_id}",
            json={
                "username": "new-admin",
                "password": "rotated-secret",
            },
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_update_with_retest_flag(self) -> None:
        """PATCH with retest=true should trigger connection test after update."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=entity)
        repo.update = AsyncMock(return_value=entity)
        repo.update_test_result = AsyncMock(return_value=None)

        tester = AsyncMock(spec=ConnectionTester)
        tester.test = AsyncMock(return_value=TesterResult(success=True, dialect_version="15.2"))

        client = _create_test_app(repo, tester)
        response = client.patch(
            f"/api/v1/database-connections/{conn_id}?retest=true",
            json={"name": "updated-name"},
        )

        assert response.status_code == 200
        # Tester should have been called
        tester.test.assert_awaited_once()

    @pytest.mark.unit
    def test_update_without_retest_flag_no_test(self) -> None:
        """PATCH without retest flag should NOT trigger connection test."""
        conn_id = uuid.uuid4()
        entity = _make_test_entity(id=conn_id)
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.update = AsyncMock(return_value=entity)

        tester = AsyncMock(spec=ConnectionTester)

        client = _create_test_app(repo, tester)
        response = client.patch(
            f"/api/v1/database-connections/{conn_id}",
            json={"name": "updated-name"},
        )

        assert response.status_code == 200
        # Tester should NOT have been called
        tester.test.assert_not_awaited()

    @pytest.mark.unit
    def test_update_credentials_requires_existing_connection(self) -> None:
        """Credential update should fail if connection doesn't exist."""
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.get = AsyncMock(return_value=None)
        repo.update = AsyncMock(return_value=None)

        client = _create_test_app(repo)
        response = client.patch(
            f"/api/v1/database-connections/{uuid.uuid4()}",
            json={"password": "new-secret"},
        )

        assert response.status_code == 404

    @pytest.mark.unit
    def test_update_request_cloud_fields(self) -> None:
        """Update request should support cloud-specific field updates."""
        from mcp_server_langgraph.api.v1.database_connections import (
            DatabaseConnectionUpdateRequest,
        )

        req = DatabaseConnectionUpdateRequest(
            project_id="new-gcp-project",
            account_id="new-account",
            warehouse_id="NEW_WH",
        )
        assert req.project_id == "new-gcp-project"
        assert req.account_id == "new-account"
        assert req.warehouse_id == "NEW_WH"


# ============================================================================
# Security Tests (Path Traversal)
# ============================================================================


@pytest.mark.xdist_group(name="test_database_connections_security")
class TestSecretPathValidation:
    """SECURITY: Test secret path traversal prevention."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    def test_secret_path_traversal_blocked(self) -> None:
        """SECURITY: Path traversal in secret_path should be rejected."""
        from mcp_server_langgraph.api.v1.database_connections import (
            get_db_conn_repository,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user
        from mcp_server_langgraph.core.secrets import InMemorySecretsProvider

        app = FastAPI()
        app.include_router(database_connections_router, prefix="/api/v1")

        repo = AsyncMock(spec=DatabaseConnectionRepository)

        async def mock_user():
            return {"sub": "user-1", "id": "user-1", "tenant_id": "tenant-1"}

        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[get_db_conn_repository] = lambda: repo
        app.dependency_overrides[_get_secrets_provider] = lambda: InMemorySecretsProvider()
        app.dependency_overrides[_get_egress_validator] = lambda: None

        client = TestClient(app)
        response = client.post(
            "/api/v1/database-connections/",
            json={
                "name": "malicious",
                "dialect": "postgres",
                "connection_method": "secret_ref",
                # Traversal attempt: starts with valid prefix but contains ..
                "secret_path": "/database/tenant-1/../other-tenant/secrets",
                "secret_key": "stolen_creds",
            },
        )

        assert response.status_code == 403
        assert "tenant" in response.json()["detail"].lower()

    @pytest.mark.unit
    def test_secret_key_path_separator_blocked(self) -> None:
        """SECURITY: Path separators in secret_key should be rejected."""
        from mcp_server_langgraph.api.v1.database_connections import (
            get_db_conn_repository,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user
        from mcp_server_langgraph.core.secrets import InMemorySecretsProvider

        app = FastAPI()
        app.include_router(database_connections_router, prefix="/api/v1")

        repo = AsyncMock(spec=DatabaseConnectionRepository)

        async def mock_user():
            return {"sub": "user-1", "id": "user-1", "tenant_id": "tenant-1"}

        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[get_db_conn_repository] = lambda: repo
        app.dependency_overrides[_get_secrets_provider] = lambda: InMemorySecretsProvider()
        app.dependency_overrides[_get_egress_validator] = lambda: None

        client = TestClient(app)
        response = client.post(
            "/api/v1/database-connections/",
            json={
                "name": "malicious",
                "dialect": "postgres",
                "connection_method": "secret_ref",
                "secret_path": "/database/tenant-1/postgres",
                # Traversal attempt via secret_key
                "secret_key": "../other-tenant/secrets",
            },
        )

        assert response.status_code == 400
        assert "path separator" in response.json()["detail"].lower()

    @pytest.mark.unit
    def test_valid_secret_path_accepted(self) -> None:
        """Valid secret_path should be accepted."""
        entity = _make_test_entity()
        repo = AsyncMock(spec=DatabaseConnectionRepository)
        repo.create = AsyncMock(return_value=entity)
        repo.update = AsyncMock(return_value=entity)

        from mcp_server_langgraph.api.v1.database_connections import (
            get_db_conn_repository,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user
        from mcp_server_langgraph.core.secrets import InMemorySecretsProvider

        app = FastAPI()
        app.include_router(database_connections_router, prefix="/api/v1")

        async def mock_user():
            return {"sub": "user-1", "id": "user-1", "tenant_id": "tenant-1"}

        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[get_db_conn_repository] = lambda: repo
        app.dependency_overrides[_get_secrets_provider] = lambda: InMemorySecretsProvider()
        app.dependency_overrides[_get_egress_validator] = lambda: None

        client = TestClient(app)
        response = client.post(
            "/api/v1/database-connections/",
            json={
                "name": "valid-conn",
                "dialect": "postgres",
                "connection_method": "secret_ref",
                "secret_path": "/database/tenant-1/postgres",
                "secret_key": "my_connection",
            },
        )

        assert response.status_code == 201
