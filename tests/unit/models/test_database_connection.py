"""
Unit tests for DatabaseConnection SQLAlchemy model.

Tests the DatabaseConnection model and DatabaseDialect enum
for structural correctness without requiring a database session.
"""

import gc
import uuid
from datetime import datetime, UTC

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group("db_connection_model"),
]


class TestDatabaseDialect:
    """Test DatabaseDialect enum values and StrEnum behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_dialect_postgres_has_expected_value(self) -> None:
        """Test POSTGRES enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.POSTGRES == "postgres"

    def test_dialect_mysql_has_expected_value(self) -> None:
        """Test MYSQL enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.MYSQL == "mysql"

    def test_dialect_sqlite_has_expected_value(self) -> None:
        """Test SQLITE enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.SQLITE == "sqlite"

    def test_dialect_bigquery_has_expected_value(self) -> None:
        """Test BIGQUERY enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.BIGQUERY == "bigquery"

    def test_dialect_snowflake_has_expected_value(self) -> None:
        """Test SNOWFLAKE enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.SNOWFLAKE == "snowflake"

    def test_dialect_duckdb_has_expected_value(self) -> None:
        """Test DUCKDB enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.DUCKDB == "duckdb"

    def test_dialect_redshift_has_expected_value(self) -> None:
        """Test REDSHIFT enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.REDSHIFT == "redshift"

    def test_dialect_clickhouse_has_expected_value(self) -> None:
        """Test CLICKHOUSE enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.CLICKHOUSE == "clickhouse"

    def test_dialect_trino_has_expected_value(self) -> None:
        """Test TRINO enum value."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.TRINO == "trino"

    def test_dialect_enum_has_expected_count(self) -> None:
        """Test that all 9 dialects are defined."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert len(DatabaseDialect) == 9

    def test_dialect_strenum_has_string_behavior(self) -> None:
        """Test that DatabaseDialect is a StrEnum (values are strings)."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        # StrEnum values are strings - can be used directly in string operations
        assert isinstance(DatabaseDialect.POSTGRES, str)
        assert f"dialect={DatabaseDialect.POSTGRES}" == "dialect=postgres"

    def test_dialect_strenum_equals_string_value(self) -> None:
        """Test that StrEnum values compare equal to plain strings."""
        from mcp_server_langgraph.models.database_connection import DatabaseDialect

        assert DatabaseDialect.POSTGRES == "postgres"
        assert DatabaseDialect.POSTGRES == "postgres"


class TestDatabaseConnection:
    """Test DatabaseConnection SQLAlchemy model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_database_connection_has_expected_tablename(self) -> None:
        """Test table name is 'database_connections'."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        assert DatabaseConnection.__tablename__ == "database_connections"

    def test_model_creation_with_required_fields(self) -> None:
        """Test in-memory model creation with required fields."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        conn = DatabaseConnection(
            tenant_id="tenant-1",
            owner_id="owner-1",
            name="prod-db",
            dialect="postgres",
            secret_path="/database/tenant-1",
            secret_key="DB_PROD",
        )
        assert conn.tenant_id == "tenant-1"
        assert conn.owner_id == "owner-1"
        assert conn.name == "prod-db"
        assert conn.dialect == "postgres"
        assert conn.secret_path == "/database/tenant-1"
        assert conn.secret_key == "DB_PROD"

    def test_model_creation_with_all_fields(self) -> None:
        """Test in-memory model creation with all fields populated."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        test_id = uuid.uuid4()
        now = datetime.now(UTC)
        conn = DatabaseConnection(
            id=test_id,
            tenant_id="tenant-1",
            owner_id="owner-1",
            name="analytics-db",
            description="Analytics BigQuery dataset",
            dialect="bigquery",
            host=None,
            port=None,
            database="analytics_dataset",
            project_id="gcp-project-123",
            account_id=None,
            warehouse_id=None,
            secret_path="/database/tenant-1/bigquery",
            secret_key="BQ_CREDS",
            ssl_mode="disable",
            status="connected",
            last_tested_at=now,
            dialect_version="2.0",
            created_at=now,
            updated_at=now,
        )
        assert conn.id == test_id
        assert conn.description == "Analytics BigQuery dataset"
        assert conn.dialect == "bigquery"
        assert conn.database == "analytics_dataset"
        assert conn.project_id == "gcp-project-123"
        assert conn.ssl_mode == "disable"
        assert conn.status == "connected"
        assert conn.last_tested_at == now
        assert conn.dialect_version == "2.0"

    def test_default_ssl_mode(self) -> None:
        """Test default ssl_mode is 'require'."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["ssl_mode"]
        assert col.default.arg == "require"

    def test_database_connection_has_default_status(self) -> None:
        """Test default status is 'disconnected'."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["status"]
        assert col.default.arg == "disconnected"

    def test_database_connection_repr_shows_name(self) -> None:
        """Test __repr__ output."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        test_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        conn = DatabaseConnection(
            id=test_id,
            tenant_id="tenant-1",
            owner_id="owner-1",
            name="my-db",
            dialect="postgres",
            secret_path="/path",
            secret_key="key",
        )
        repr_str = repr(conn)
        assert "DatabaseConnection" in repr_str
        assert "my-db" in repr_str
        assert "postgres" in repr_str
        assert "tenant-1" in repr_str

    def test_id_column_is_uuid(self) -> None:
        """Test id column uses UUID type."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["id"]
        assert col.type.__class__.__name__ == "UUID"
        assert col.primary_key is True

    def test_tenant_id_not_nullable(self) -> None:
        """Test tenant_id column is not nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["tenant_id"]
        assert col.nullable is False

    def test_owner_id_not_nullable(self) -> None:
        """Test owner_id column is not nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["owner_id"]
        assert col.nullable is False

    def test_name_not_nullable(self) -> None:
        """Test name column is not nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["name"]
        assert col.nullable is False

    def test_dialect_not_nullable(self) -> None:
        """Test dialect column is not nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["dialect"]
        assert col.nullable is False

    def test_secret_path_not_nullable(self) -> None:
        """Test secret_path column is not nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["secret_path"]
        assert col.nullable is False

    def test_secret_key_not_nullable(self) -> None:
        """Test secret_key column is not nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["secret_key"]
        assert col.nullable is False

    def test_database_connection_description_is_nullable(self) -> None:
        """Test description column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["description"]
        assert col.nullable is True

    def test_database_connection_host_is_nullable(self) -> None:
        """Test host column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["host"]
        assert col.nullable is True

    def test_database_connection_port_is_nullable(self) -> None:
        """Test port column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["port"]
        assert col.nullable is True

    def test_database_connection_database_is_nullable(self) -> None:
        """Test database column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["database"]
        assert col.nullable is True

    def test_project_id_nullable(self) -> None:
        """Test project_id column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["project_id"]
        assert col.nullable is True

    def test_account_id_nullable(self) -> None:
        """Test account_id column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["account_id"]
        assert col.nullable is True

    def test_warehouse_id_nullable(self) -> None:
        """Test warehouse_id column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["warehouse_id"]
        assert col.nullable is True

    def test_last_tested_at_nullable(self) -> None:
        """Test last_tested_at column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["last_tested_at"]
        assert col.nullable is True

    def test_dialect_version_nullable(self) -> None:
        """Test dialect_version column is nullable."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["dialect_version"]
        assert col.nullable is True

    def test_unique_tenant_name_index(self) -> None:
        """Test unique composite index on (tenant_id, name) exists."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        indexes = {idx.name: idx for idx in DatabaseConnection.__table__.indexes}
        assert "ix_db_conn_tenant_name" in indexes
        idx = indexes["ix_db_conn_tenant_name"]
        assert idx.unique is True
        col_names = [col.name for col in idx.columns]
        assert "tenant_id" in col_names
        assert "name" in col_names

    def test_database_connection_owner_index_exists(self) -> None:
        """Test index on owner_id exists."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        indexes = {idx.name: idx for idx in DatabaseConnection.__table__.indexes}
        assert "ix_db_conn_owner" in indexes
        col_names = [col.name for col in indexes["ix_db_conn_owner"].columns]
        assert "owner_id" in col_names

    def test_database_connection_has_expected_column_count(self) -> None:
        """Test total number of columns on the model."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col_names = [col.name for col in DatabaseConnection.__table__.columns]
        # id, tenant_id, owner_id, name, description, dialect, host, port,
        # database, project_id, account_id, warehouse_id, secret_path,
        # secret_key, ssl_mode, status, last_tested_at, dialect_version,
        # created_at, updated_at = 20 columns
        assert len(col_names) == 20

    def test_created_at_has_timezone(self) -> None:
        """Test created_at uses timezone-aware DateTime."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["created_at"]
        assert col.type.timezone is True

    def test_updated_at_has_timezone(self) -> None:
        """Test updated_at uses timezone-aware DateTime."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["updated_at"]
        assert col.type.timezone is True

    def test_cloud_specific_fields(self) -> None:
        """Test model creation with cloud-specific fields (Snowflake)."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        conn = DatabaseConnection(
            tenant_id="tenant-1",
            owner_id="owner-1",
            name="snowflake-warehouse",
            dialect="snowflake",
            secret_path="/database/tenant-1/snowflake",
            secret_key="SF_CREDS",
            account_id="xy12345.us-east-1",
            warehouse_id="COMPUTE_WH",
            database="ANALYTICS",
        )
        assert conn.account_id == "xy12345.us-east-1"
        assert conn.warehouse_id == "COMPUTE_WH"
        assert conn.database == "ANALYTICS"

    def test_port_column_is_integer(self) -> None:
        """Test port column uses Integer type."""
        from mcp_server_langgraph.models.database_connection import DatabaseConnection

        col = DatabaseConnection.__table__.columns["port"]
        assert col.type.__class__.__name__ == "Integer"
