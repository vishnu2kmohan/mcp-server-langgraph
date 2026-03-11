import pytest
import sqlglot

from mcp_server_langgraph.execution.sql.policy import DataAccessPolicy, RowLimitEnforcer

pytestmark = pytest.mark.unit


class TestDataAccessPolicy:
    @pytest.fixture
    def policy(self):
        return DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            allowed_tables={"users", "orders"},
            blocked_columns={"password", "secret"},
        )

    @pytest.fixture
    def open_policy(self):
        return DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            blocked_columns=set(),
        )

    def test_allows_valid_table(self, policy):
        ast = sqlglot.parse_one("SELECT id FROM users")
        errors = policy.validate_query(ast)
        assert not errors

    def test_blocks_disallowed_table(self, policy):
        ast = sqlglot.parse_one("SELECT id FROM secrets")
        errors = policy.validate_query(ast)
        assert any("not allowed" in e for e in errors)

    def test_blocks_system_schema(self, policy):
        ast = sqlglot.parse_one("SELECT * FROM information_schema.tables")
        errors = policy.validate_query(ast)
        assert any("System schema" in e for e in errors)

    def test_blocks_pg_catalog(self, policy):
        ast = sqlglot.parse_one("SELECT * FROM pg_catalog.pg_tables")
        errors = policy.validate_query(ast)
        assert any("System schema" in e for e in errors)

    def test_blocks_select_star_with_blocked_columns(self, policy):
        ast = sqlglot.parse_one("SELECT * FROM users")
        errors = policy.validate_query(ast)
        assert any("SELECT *" in e for e in errors)

    def test_allows_select_star_without_blocked_columns(self, open_policy):
        ast = sqlglot.parse_one("SELECT * FROM users")
        errors = open_policy.validate_query(ast)
        assert not any("SELECT *" in e for e in errors)

    def test_blocks_password_column(self, policy):
        ast = sqlglot.parse_one("SELECT id, password FROM users")
        errors = policy.validate_query(ast)
        assert any("blocked" in e.lower() for e in errors)

    def test_allows_non_blocked_columns(self, policy):
        ast = sqlglot.parse_one("SELECT id, name, email FROM users")
        errors = policy.validate_query(ast)
        assert not any("blocked" in e.lower() for e in errors)

    def test_blocks_disallowed_schema(self):
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
        )
        ast = sqlglot.parse_one("SELECT * FROM private.secrets")
        errors = policy.validate_query(ast)
        assert any("not allowed" in e for e in errors)

    def test_empty_allowed_tables_allows_all(self):
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            allowed_tables=set(),
            blocked_columns=set(),
        )
        ast = sqlglot.parse_one("SELECT * FROM any_table")
        errors = policy.validate_query(ast)
        assert not errors

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestRowLimitEnforcer:
    def test_adds_limit_when_none(self):
        ast = sqlglot.parse_one("SELECT * FROM users")
        result = RowLimitEnforcer.enforce(ast, max_rows=100)
        sql = result.sql()
        assert "100" in sql

    def test_reduces_excessive_limit(self):
        ast = sqlglot.parse_one("SELECT * FROM users LIMIT 50000")
        result = RowLimitEnforcer.enforce(ast, max_rows=10000)
        sql = result.sql()
        assert "10000" in sql
        assert "50000" not in sql

    def test_preserves_acceptable_limit(self):
        ast = sqlglot.parse_one("SELECT * FROM users LIMIT 50")
        result = RowLimitEnforcer.enforce(ast, max_rows=10000)
        sql = result.sql()
        assert "50" in sql

    def test_preserves_exact_max_limit(self):
        ast = sqlglot.parse_one("SELECT * FROM users LIMIT 10000")
        result = RowLimitEnforcer.enforce(ast, max_rows=10000)
        sql = result.sql()
        assert "10000" in sql

    def test_enforces_parameterized_limit(self):
        """Parameterized LIMIT should be wrapped to enforce max_rows cap."""
        # Named parameter style
        ast = sqlglot.parse_one("SELECT * FROM users LIMIT :limit")
        result = RowLimitEnforcer.enforce(ast, max_rows=100)
        sql = result.sql()
        # Should wrap in subquery with outer LIMIT
        assert "100" in sql
        # The outer query should enforce the cap
        assert sql.count("LIMIT") >= 1

    def test_enforces_expression_limit(self):
        """Expression-based LIMIT should be wrapped to enforce max_rows cap."""
        ast = sqlglot.parse_one("SELECT * FROM users LIMIT 10 + 10")
        result = RowLimitEnforcer.enforce(ast, max_rows=100)
        sql = result.sql()
        # Should wrap in subquery with outer LIMIT 100
        assert "100" in sql

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
