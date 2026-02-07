import pytest

from mcp_server_langgraph.execution.sql.exceptions import SQLTranspileError
from mcp_server_langgraph.execution.sql.transpiler import SQLTranspiler

pytestmark = pytest.mark.unit


class TestSQLTranspilerBasic:
    @pytest.fixture
    def transpiler(self):
        return SQLTranspiler()

    def test_transpile_postgres_to_bigquery(self, transpiler):
        result = transpiler.transpile("SELECT NOW()", source="postgres", target="bigquery")
        assert "CURRENT_TIMESTAMP" in result.upper()

    def test_transpile_postgres_to_snowflake(self, transpiler):
        result = transpiler.transpile("SELECT * FROM users LIMIT 10", source="postgres", target="snowflake")
        assert result  # Valid transpilation

    def test_transpile_mysql_to_postgres(self, transpiler):
        result = transpiler.transpile(
            "SELECT IFNULL(name, 'unknown') FROM users",
            source="mysql",
            target="postgres",
        )
        assert "COALESCE" in result.upper()

    def test_transpile_caching_returns_same_result(self, transpiler):
        """Same query should hit cache."""
        r1 = transpiler.transpile("SELECT 1", "postgres", "bigquery")
        r2 = transpiler.transpile("SELECT 1", "postgres", "bigquery")
        assert r1 == r2

    def test_parse_cached_returns_same_object(self, transpiler):
        ast1 = transpiler.parse_cached("SELECT 1", "postgres")
        ast2 = transpiler.parse_cached("SELECT 1", "postgres")
        assert ast1 is ast2  # Same cached object


class TestSQLTranspilerValidation:
    @pytest.fixture
    def transpiler(self):
        return SQLTranspiler()

    def test_transpile_and_validate_safe_query(self, transpiler):
        sql = "SELECT id, name FROM users WHERE active = true"
        transpiled, result = transpiler.transpile_and_validate(sql, source="postgres", target="bigquery")
        assert result.is_valid
        assert transpiled

    def test_transpile_and_validate_blocks_dangerous(self, transpiler):
        """Transpiled SQL containing blocked operations should fail validation."""
        with pytest.raises(SQLTranspileError):
            transpiler.transpile_and_validate("DROP TABLE users", source="postgres", target="bigquery")

    def test_validate_transpiled_sql_blocks_copy(self, transpiler):
        result = transpiler.validate_transpiled_sql(
            "COPY INTO @stage FROM (SELECT * FROM users)",
            target_dialect="snowflake",
        )
        # COPY is blocked in snowflake dialect
        assert not result.is_valid


class TestSQLTranspilerDialectPairs:
    @pytest.fixture
    def transpiler(self):
        return SQLTranspiler()

    @pytest.mark.parametrize(
        "source,target",
        [
            ("postgres", "bigquery"),
            ("postgres", "snowflake"),
            ("postgres", "duckdb"),
            ("mysql", "postgres"),
            ("mysql", "bigquery"),
            ("sqlite", "postgres"),
            ("postgres", "mysql"),
            ("bigquery", "postgres"),
            ("snowflake", "postgres"),
            ("duckdb", "postgres"),
        ],
    )
    def test_basic_select_transpiles(self, transpiler, source, target):
        result = transpiler.transpile(
            "SELECT id, name FROM users WHERE id = 1",
            source=source,
            target=target,
        )
        assert result
        assert "users" in result.lower()

    @pytest.mark.parametrize(
        "source,target",
        [
            ("postgres", "bigquery"),
            ("postgres", "snowflake"),
            ("mysql", "postgres"),
        ],
    )
    def test_aggregate_query_transpiles_correctly(self, transpiler, source, target):
        result = transpiler.transpile(
            "SELECT COUNT(*) AS cnt, department FROM users GROUP BY department",
            source=source,
            target=target,
        )
        assert result
        assert "COUNT" in result.upper()

    @pytest.mark.parametrize(
        "source,target",
        [
            ("postgres", "bigquery"),
            ("postgres", "snowflake"),
        ],
    )
    def test_limit_clause_transpiles_correctly(self, transpiler, source, target):
        result = transpiler.transpile(
            "SELECT * FROM users LIMIT 100",
            source=source,
            target=target,
        )
        assert result


class TestSQLTranspilerRevalidation:
    @pytest.fixture
    def transpiler(self):
        return SQLTranspiler()

    def test_transpile_preserves_validation_for_safe_queries(self, transpiler):
        sql = "SELECT id, name FROM users WHERE active = true"
        transpiled, result = transpiler.transpile_and_validate(sql, source="postgres", target="bigquery")
        assert result.is_valid

    @pytest.mark.parametrize(
        "source,target,sql",
        [
            ("postgres", "snowflake", "SELECT pg_read_file('/etc/passwd')"),
            ("mysql", "postgres", "SELECT load_file('/etc/passwd')"),
        ],
    )
    def test_blocks_file_access_functions(self, transpiler, source, target, sql):
        """File access functions blocked regardless of transpilation path."""
        # These should either fail transpilation or fail post-validation
        try:
            _, result = transpiler.transpile_and_validate(sql, source, target)
            assert not result.is_valid
        except SQLTranspileError:
            pass  # Also acceptable - transpilation itself rejected it
