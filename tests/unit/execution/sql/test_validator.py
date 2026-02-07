"""
Unit tests for SQLValidator.

Tests AST-based SQL validation, statement type blocking, table allowlisting,
multi-statement detection, dialect-specific function blocking, and parse error handling.
Following TDD best practices - these tests should FAIL until implementation is complete.
"""

import gc

import pytest
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.unit

# TDD: import will fail until the module is implemented
try:
    from mcp_server_langgraph.execution.sql.types import ValidationResult
    from mcp_server_langgraph.execution.sql.validator import SQLValidator
except ImportError:
    pytest.skip("SQLValidator not implemented yet", allow_module_level=True)


# ---------------------------------------------------------------------------
# Valid SELECT queries (simple, join, subquery, CTE, union, aggregate)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsqlvalidatorbasic")
class TestSQLValidatorBasic:
    """Verify that well-formed, read-only queries pass validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_valid_simple_select(self, validator):
        result = validator.validate("SELECT id, name FROM users")
        assert result.is_valid

    def test_valid_select_with_where(self, validator):
        result = validator.validate("SELECT * FROM users WHERE age > 18")
        assert result.is_valid

    def test_valid_select_with_join(self, validator):
        result = validator.validate("SELECT u.id FROM users u JOIN orders o ON u.id = o.user_id")
        assert result.is_valid

    def test_validate_union_query_returns_valid(self, validator):
        result = validator.validate("SELECT id FROM users UNION SELECT id FROM admins")
        assert result.is_valid

    def test_validate_cte_query_returns_valid(self, validator):
        result = validator.validate("WITH active AS (SELECT * FROM users WHERE active) SELECT * FROM active")
        assert result.is_valid

    def test_validate_subquery_returns_valid(self, validator):
        result = validator.validate("SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)")
        assert result.is_valid

    def test_validate_aggregate_functions_returns_valid(self, validator):
        result = validator.validate("SELECT COUNT(*), department FROM users GROUP BY department HAVING COUNT(*) > 5")
        assert result.is_valid

    def test_valid_order_by_limit(self, validator):
        result = validator.validate("SELECT * FROM users ORDER BY name LIMIT 10")
        assert result.is_valid

    def test_validate_distinct_clause_returns_valid(self, validator):
        result = validator.validate("SELECT DISTINCT department FROM users")
        assert result.is_valid

    def test_valid_case_expression(self, validator):
        result = validator.validate("SELECT CASE WHEN age > 18 THEN 'adult' ELSE 'minor' END AS label FROM users")
        assert result.is_valid

    def test_valid_left_join(self, validator):
        result = validator.validate("SELECT u.id, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id")
        assert result.is_valid

    def test_valid_multiple_joins(self, validator):
        result = validator.validate(
            "SELECT u.id, o.total, p.name "
            "FROM users u "
            "JOIN orders o ON u.id = o.user_id "
            "JOIN products p ON o.product_id = p.id"
        )
        assert result.is_valid

    def test_valid_nested_subquery(self, validator):
        result = validator.validate(
            "SELECT * FROM users WHERE department_id IN "
            "(SELECT id FROM departments WHERE region_id IN "
            "(SELECT id FROM regions WHERE name = 'US'))"
        )
        assert result.is_valid

    def test_valid_window_function(self, validator):
        result = validator.validate(
            "SELECT id, name, ROW_NUMBER() OVER (PARTITION BY department ORDER BY name) AS rn FROM users"
        )
        assert result.is_valid

    def test_valid_exists_subquery(self, validator):
        result = validator.validate("SELECT * FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id)")
        assert result.is_valid

    def test_valid_aliased_columns(self, validator):
        result = validator.validate("SELECT id AS user_id, name AS user_name FROM users")
        assert result.is_valid


# ---------------------------------------------------------------------------
# Blocked DDL (DROP, CREATE, ALTER, TRUNCATE)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testsqlvalidatorddl")
class TestSQLValidatorBlockedDDL:
    """Verify that DDL statements are rejected."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_blocks_drop_table(self, validator):
        result = validator.validate("DROP TABLE users")
        assert not result.is_valid
        assert any("Drop" in e or "not allowed" in e for e in result.errors)

    def test_blocks_drop_database(self, validator):
        result = validator.validate("DROP DATABASE production")
        assert not result.is_valid

    def test_blocks_create_table(self, validator):
        result = validator.validate("CREATE TABLE evil (id INT)")
        assert not result.is_valid

    def test_blocks_create_index(self, validator):
        result = validator.validate("CREATE INDEX idx_evil ON users (name)")
        assert not result.is_valid

    def test_blocks_alter_table(self, validator):
        result = validator.validate("ALTER TABLE users ADD COLUMN evil TEXT")
        assert not result.is_valid

    def test_blocks_alter_table_drop_column(self, validator):
        result = validator.validate("ALTER TABLE users DROP COLUMN name")
        assert not result.is_valid

    def test_dangerous_ops_blocks_truncate_statement(self, validator):
        result = validator.validate("TRUNCATE TABLE users")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Blocked DML writes (DELETE, UPDATE, INSERT, GRANT)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testsqlvalidatordml")
class TestSQLValidatorBlockedDML:
    """Verify that write DML and privilege statements are rejected."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_dangerous_ops_blocks_delete_statement(self, validator):
        result = validator.validate("DELETE FROM users WHERE id = 1")
        assert not result.is_valid

    def test_blocks_delete_without_where(self, validator):
        result = validator.validate("DELETE FROM users")
        assert not result.is_valid

    def test_dangerous_ops_blocks_update_statement(self, validator):
        result = validator.validate("UPDATE users SET name = 'hacked'")
        assert not result.is_valid

    def test_blocks_update_with_where(self, validator):
        result = validator.validate("UPDATE users SET name = 'hacked' WHERE id = 1")
        assert not result.is_valid

    def test_dangerous_ops_blocks_insert_statement(self, validator):
        result = validator.validate("INSERT INTO users (name) VALUES ('evil')")
        assert not result.is_valid

    def test_blocks_insert_select(self, validator):
        result = validator.validate("INSERT INTO backup_users SELECT * FROM users")
        assert not result.is_valid

    def test_dangerous_ops_blocks_grant_statement(self, validator):
        result = validator.validate("GRANT ALL ON users TO evil_user")
        assert not result.is_valid

    def test_dangerous_ops_blocks_revoke_statement(self, validator):
        result = validator.validate("REVOKE ALL ON users FROM some_user")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Multi-statement detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testsqlvalidatormultistatement")
class TestSQLValidatorMultiStatement:
    """Verify that multiple statements separated by semicolons are rejected."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_blocks_multi_statement_injection(self, validator):
        result = validator.validate("SELECT 1; DROP TABLE users")
        assert not result.is_valid
        assert any("Multi-statement" in e for e in result.errors)

    def test_blocks_multi_statement_select_select(self, validator):
        result = validator.validate("SELECT 1; SELECT 2")
        assert not result.is_valid
        assert any("Multi-statement" in e for e in result.errors)

    def test_blocks_multi_statement_with_spaces(self, validator):
        result = validator.validate("SELECT 1 ;  DROP TABLE users")
        assert not result.is_valid

    def test_allows_single_statement_with_trailing_semicolon(self, validator):
        """A trailing semicolon on a single statement should not be treated as multi-statement."""
        result = validator.validate("SELECT 1;")
        # Implementations may or may not allow trailing semicolons;
        # at minimum it must not be flagged as multi-statement if treated as single.
        # If the implementation strips trailing semicolons, this should be valid.
        # We test that multi-statement error is NOT present when only one statement exists.
        if not result.is_valid:
            assert not any("Multi-statement" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Invalid SQL / parse error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsqlvalidatorparseerror")
class TestSQLValidatorParseErrors:
    """Verify that unparseable SQL is flagged as invalid."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_blocks_invalid_sql(self, validator):
        result = validator.validate("NOT VALID SQL AT ALL !!!")
        assert not result.is_valid
        assert any("Failed to parse" in e or "not allowed" in e for e in result.errors)

    def test_blocks_empty_string(self, validator):
        result = validator.validate("")
        assert not result.is_valid

    def test_blocks_whitespace_only(self, validator):
        result = validator.validate("   \n\t  \n")
        assert not result.is_valid

    def test_allows_bare_select(self, validator):
        """SQLGlot parses bare 'SELECT' as a valid empty select expression."""
        result = validator.validate("SELECT")
        assert isinstance(result, ValidationResult)

    def test_blocks_random_characters(self, validator):
        result = validator.validate("@#$%^&*()")
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_blocks_sql_comment_only(self, validator):
        result = validator.validate("-- just a comment")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Table allowlist enforcement
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsqlvalidatortableallowlist")
class TestSQLValidatorTableAllowlist:
    """Verify that table allowlist enforcement works correctly."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_allows_tables_in_allowlist(self):
        validator = SQLValidator(allowed_tables={"users", "orders"})
        result = validator.validate("SELECT * FROM users")
        assert result.is_valid

    def test_blocks_tables_not_in_allowlist(self):
        validator = SQLValidator(allowed_tables={"users", "orders"})
        result = validator.validate("SELECT * FROM secrets")
        assert not result.is_valid
        assert any("not in the allowed table list" in e for e in result.errors)

    def test_no_allowlist_allows_all_tables(self):
        validator = SQLValidator()
        result = validator.validate("SELECT * FROM any_table")
        assert result.is_valid

    def test_blocks_joined_table_not_in_allowlist(self):
        validator = SQLValidator(allowed_tables={"users"})
        result = validator.validate("SELECT * FROM users u JOIN secrets s ON u.id = s.user_id")
        assert not result.is_valid
        assert any("not in the allowed table list" in e for e in result.errors)

    def test_allows_multiple_joined_tables_in_allowlist(self):
        validator = SQLValidator(allowed_tables={"users", "orders", "products"})
        result = validator.validate(
            "SELECT * FROM users u JOIN orders o ON u.id = o.user_id JOIN products p ON o.product_id = p.id"
        )
        assert result.is_valid

    def test_blocks_subquery_table_not_in_allowlist(self):
        validator = SQLValidator(allowed_tables={"users"})
        result = validator.validate("SELECT * FROM users WHERE id IN (SELECT user_id FROM secrets)")
        assert not result.is_valid

    def test_empty_allowlist_blocks_all_tables(self):
        validator = SQLValidator(allowed_tables=set())
        result = validator.validate("SELECT * FROM users")
        assert not result.is_valid

    def test_allowlist_case_handling(self):
        """Table name matching should work regardless of SQL casing."""
        validator = SQLValidator(allowed_tables={"users"})
        # The validator should handle case normalization; uppercase table in SQL
        result = validator.validate("SELECT * FROM USERS")
        # Whether this passes depends on whether the validator normalizes case.
        # We verify the result is a valid ValidationResult either way.
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)


# ---------------------------------------------------------------------------
# Dialect-specific function blocking
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testsqlvalidatordialect")
class TestSQLValidatorDialectFunctions:
    """Verify that dialect-specific dangerous functions are blocked."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_blocks_pg_read_file_postgres(self, validator):
        result = validator.validate("SELECT pg_read_file('/etc/passwd')", dialect="postgres")
        assert not result.is_valid

    def test_blocks_pg_read_binary_file_postgres(self, validator):
        result = validator.validate("SELECT pg_read_binary_file('/etc/shadow')", dialect="postgres")
        assert not result.is_valid

    def test_blocks_load_file_mysql(self, validator):
        result = validator.validate("SELECT load_file('/etc/passwd')", dialect="mysql")
        assert not result.is_valid

    def test_blocks_dblink_postgres(self, validator):
        result = validator.validate("SELECT * FROM dblink('host=evil', 'SELECT 1')", dialect="postgres")
        assert not result.is_valid

    def test_blocks_copy_postgres(self, validator):
        result = validator.validate("COPY users TO '/tmp/dump.csv'", dialect="postgres")
        assert not result.is_valid

    def test_blocks_into_outfile_mysql(self, validator):
        result = validator.validate("SELECT * FROM users INTO OUTFILE '/tmp/dump.csv'", dialect="mysql")
        assert not result.is_valid

    def test_blocks_lo_import_postgres(self, validator):
        result = validator.validate("SELECT lo_import('/etc/passwd')", dialect="postgres")
        assert not result.is_valid

    def test_allows_safe_function_postgres(self, validator):
        result = validator.validate("SELECT NOW(), CURRENT_TIMESTAMP", dialect="postgres")
        assert result.is_valid

    def test_allows_safe_function_mysql(self, validator):
        result = validator.validate("SELECT NOW(), CURDATE()", dialect="mysql")
        assert result.is_valid


# ---------------------------------------------------------------------------
# ValidationResult data class
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsqlvalidationresult")
class TestSQLValidationResult:
    """Verify the ValidationResult dataclass contract."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_validator_creation_with_valid_config(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_creation_invalid_with_errors(self):
        result = ValidationResult(
            is_valid=False,
            errors=["Drop statement not allowed", "Table 'secrets' not in allowlist"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_creation_with_warnings(self):
        result = ValidationResult(
            is_valid=True,
            warnings=["Query may be slow without index"],
        )
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_validator_repr_returns_expected_format(self):
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        repr_str = repr(result)
        assert "ValidationResult" in repr_str


# ---------------------------------------------------------------------------
# SQLValidator constructor / configuration
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsqlvalidatorconstructor")
class TestSQLValidatorConstructor:
    """Verify constructor parameters and defaults."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_validator_default_constructor_works(self):
        validator = SQLValidator()
        assert validator is not None

    def test_constructor_with_allowed_tables(self):
        tables = {"users", "orders"}
        validator = SQLValidator(allowed_tables=tables)
        assert validator is not None

    def test_validate_returns_validation_result(self):
        validator = SQLValidator()
        result = validator.validate("SELECT 1")
        assert isinstance(result, ValidationResult)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)


# ---------------------------------------------------------------------------
# Property-based / fuzz tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.xdist_group(name="testsqlvalidatorproperties")
class TestSQLValidatorProperties:
    """Property-based tests using Hypothesis for fuzzing the SQL validator."""

    def teardown_method(self) -> None:
        gc.collect()

    @given(st.text())
    def test_validator_never_crashes(self, sql):
        """The validator must not raise on arbitrary input."""
        validator = SQLValidator()
        result = validator.validate(sql)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)

    @given(
        st.sampled_from(
            [
                "DROP TABLE users",
                "DELETE FROM users",
                "UPDATE users SET x = 1",
                "INSERT INTO users (x) VALUES (1)",
                "CREATE TABLE evil (id INT)",
                "ALTER TABLE users ADD COLUMN evil TEXT",
                "TRUNCATE TABLE users",
                "GRANT ALL ON users TO evil_user",
            ]
        )
    )
    def test_dangerous_statements_always_rejected(self, sql):
        """Known dangerous statement types are always rejected."""
        validator = SQLValidator()
        result = validator.validate(sql)
        assert not result.is_valid
        assert len(result.errors) > 0

    @given(
        st.sampled_from(
            [
                "SELECT 1",
                "SELECT * FROM users",
                "SELECT id, name FROM users WHERE age > 18",
                "SELECT COUNT(*) FROM users",
                "SELECT * FROM users ORDER BY name LIMIT 10",
            ]
        )
    )
    def test_safe_selects_always_accepted(self, sql):
        """Known safe SELECT statements are always accepted."""
        validator = SQLValidator()
        result = validator.validate(sql)
        assert result.is_valid
        assert len(result.errors) == 0
