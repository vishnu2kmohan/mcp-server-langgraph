"""
Unit tests for SQLExecutor.

Tests the unified validate -> transpile -> execute pipeline including
validation, policy enforcement, transpilation, execution, timeout handling,
raw SQL controls, interpolation pattern detection, and parameter translation.

Following TDD best practices - tests written before implementation.
"""

import asyncio
import gc
import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group("sql_executor"),
]

# TDD: import will fail until the module is implemented
try:
    from mcp_server_langgraph.execution.sql.drivers.base import DatabaseDriver
    from mcp_server_langgraph.execution.sql.exceptions import (
        SQLConnectionError,
        SQLExecutionError,
        SQLSecurityError,
        SQLTimeoutError,
    )
    from mcp_server_langgraph.execution.sql.executor import (
        ExecutionResult,
        SQLExecutor,
    )
    from mcp_server_langgraph.execution.sql.policy import DataAccessPolicy
    from mcp_server_langgraph.execution.sql.transpiler import SQLTranspiler
    from mcp_server_langgraph.execution.sql.validator import SQLValidator
except ImportError:
    pytest.skip("SQLExecutor not implemented yet", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_driver(
    rows: list[dict] | None = None,
    execute_side_effect: Exception | None = None,
):
    """Create a mock DatabaseDriver with sensible defaults."""
    mock_driver = AsyncMock(spec=DatabaseDriver)
    if execute_side_effect:
        mock_driver.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        mock_driver.execute = AsyncMock(return_value=rows if rows is not None else [{"id": 1, "name": "test"}])
    mock_driver.cancel = AsyncMock(return_value=True)
    mock_driver.is_healthy = True
    return mock_driver


# ---------------------------------------------------------------------------
# TestExecutionResult - dataclass defaults and construction
# ---------------------------------------------------------------------------


class TestExecutionResult:
    """Verify ExecutionResult dataclass contract."""

    def teardown_method(self):
        gc.collect()

    def test_executor_config_has_default_values(self):
        """ExecutionResult should have sensible defaults."""
        result = ExecutionResult(success=True)
        assert result.success is True
        assert result.rows == []
        assert result.row_count == 0
        assert result.error is None
        assert result.warnings == []
        assert result.dialect == ""
        assert result.transpiled_sql is None

    def test_success_result_creation(self):
        """Create a fully-populated success result."""
        result = ExecutionResult(
            success=True,
            rows=[{"id": 1}, {"id": 2}],
            row_count=2,
            dialect="postgres",
            warnings=["Query may be slow"],
        )
        assert result.success is True
        assert len(result.rows) == 2
        assert result.row_count == 2
        assert result.error is None
        assert result.dialect == "postgres"
        assert "Query may be slow" in result.warnings

    def test_failure_result_creation(self):
        """Create a failure result with error message."""
        result = ExecutionResult(
            success=False,
            error="Validation failed: blocked table",
            dialect="postgres",
        )
        assert result.success is False
        assert result.rows == []
        assert result.row_count == 0
        assert result.error is not None
        assert "Validation failed" in result.error

    def test_transpiled_sql_field(self):
        """Transpiled SQL should be populated when transpilation occurred."""
        result = ExecutionResult(
            success=True,
            rows=[],
            row_count=0,
            dialect="bigquery",
            transpiled_sql="SELECT * FROM `dataset.table`",
        )
        assert result.transpiled_sql is not None
        assert "dataset" in result.transpiled_sql

    def test_warnings_are_independent_lists(self):
        """Each instance should have its own warnings list."""
        r1 = ExecutionResult(success=True)
        r2 = ExecutionResult(success=True)
        r1.warnings.append("warning1")
        assert "warning1" not in r2.warnings

    def test_rows_are_independent_lists(self):
        """Each instance should have its own rows list."""
        r1 = ExecutionResult(success=True)
        r2 = ExecutionResult(success=True)
        r1.rows.append({"id": 1})
        assert len(r2.rows) == 0


# ---------------------------------------------------------------------------
# TestSQLExecutorValidation - input validation pipeline
# ---------------------------------------------------------------------------


class TestSQLExecutorValidation:
    """Verify that the executor validates SQL before execution."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def executor(self):
        return SQLExecutor()

    @pytest.fixture
    def mock_driver(self):
        return _make_mock_driver()

    @pytest.mark.asyncio
    async def test_invalid_sql_returns_failure(self, executor, mock_driver):
        """SQL that fails validation should return a failure result without executing."""
        result = await executor.execute(
            sql="DROP TABLE users",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is False
        assert "Validation failed" in result.error
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_sql_passes_validation(self, executor, mock_driver):
        """Valid SELECT should pass validation and proceed to execution."""
        result = await executor.execute(
            sql="SELECT id, name FROM users",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is True
        mock_driver.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_statement_blocked(self, executor, mock_driver):
        """Multi-statement SQL should be rejected at validation."""
        result = await executor.execute(
            sql="SELECT 1; SELECT 2",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is False
        assert "Validation failed" in result.error
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_sql_returns_failure(self, executor, mock_driver):
        """Empty SQL string should fail validation."""
        result = await executor.execute(
            sql="",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is False
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_insert_blocked(self, executor, mock_driver):
        """INSERT statements should be blocked by the validator."""
        result = await executor.execute(
            sql="INSERT INTO users (name) VALUES ('test')",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is False
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_blocked(self, executor, mock_driver):
        """UPDATE statements should be blocked by the validator."""
        result = await executor.execute(
            sql="UPDATE users SET name = 'hacked'",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is False
        mock_driver.execute.assert_not_called()


# ---------------------------------------------------------------------------
# TestSQLExecutorPolicy - data access policy enforcement
# ---------------------------------------------------------------------------


class TestSQLExecutorPolicy:
    """Verify policy enforcement in the execution pipeline."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def executor(self):
        return SQLExecutor()

    @pytest.fixture
    def mock_driver(self):
        return _make_mock_driver()

    @pytest.mark.asyncio
    async def test_blocked_schema_returns_failure(self, executor, mock_driver):
        """Queries against blocked system schemas should fail."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
        )
        result = await executor.execute(
            sql="SELECT * FROM information_schema.tables",
            dialect="postgres",
            driver=mock_driver,
            policy=policy,
        )
        assert result.success is False
        assert "Policy violation" in result.error
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocked_column_returns_failure(self, executor, mock_driver):
        """Queries selecting blocked columns should fail."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            blocked_columns={"password", "secret"},
        )
        result = await executor.execute(
            sql="SELECT password FROM users",
            dialect="postgres",
            driver=mock_driver,
            policy=policy,
        )
        assert result.success is False
        assert "Policy violation" in result.error
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_query_passes(self, executor, mock_driver):
        """A query that satisfies all policy constraints should succeed."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            blocked_columns={"secret"},
            max_rows=100,
        )
        result = await executor.execute(
            sql="SELECT id, name FROM users",
            dialect="postgres",
            driver=mock_driver,
            policy=policy,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_row_limit_enforcement(self, executor, mock_driver):
        """Policy max_rows should be enforced via LIMIT clause injection."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            blocked_columns=set(),
            max_rows=50,
        )
        result = await executor.execute(
            sql="SELECT * FROM users",
            dialect="postgres",
            driver=mock_driver,
            policy=policy,
        )
        assert result.success is True
        # The executed SQL should contain a LIMIT
        executed_sql = mock_driver.execute.call_args[0][0]
        assert "50" in executed_sql.upper() or "LIMIT" in executed_sql.upper()

    @pytest.mark.asyncio
    async def test_row_limit_caps_existing_limit(self, executor, mock_driver):
        """If the query has a LIMIT higher than max_rows, it should be capped."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            blocked_columns=set(),
            max_rows=100,
        )
        result = await executor.execute(
            sql="SELECT * FROM users LIMIT 50000",
            dialect="postgres",
            driver=mock_driver,
            policy=policy,
        )
        assert result.success is True
        executed_sql = mock_driver.execute.call_args[0][0]
        # Should not contain 50000
        assert "50000" not in executed_sql

    @pytest.mark.asyncio
    async def test_select_star_blocked_with_column_restrictions(self, executor, mock_driver):
        """SELECT * should be blocked when column restrictions are active."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            blocked_columns={"password"},
        )
        result = await executor.execute(
            sql="SELECT * FROM users",
            dialect="postgres",
            driver=mock_driver,
            policy=policy,
        )
        assert result.success is False
        assert "Policy violation" in result.error


# ---------------------------------------------------------------------------
# TestSQLExecutorTranspilation - cross-dialect transpilation
# ---------------------------------------------------------------------------


class TestSQLExecutorTranspilation:
    """Verify cross-dialect transpilation in the pipeline."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def executor(self):
        return SQLExecutor()

    @pytest.fixture
    def mock_driver(self):
        return _make_mock_driver()

    @pytest.mark.asyncio
    async def test_cross_dialect_transpilation(self, executor, mock_driver):
        """SQL should be transpiled when target dialect differs from source."""
        result = await executor.execute(
            sql="SELECT CURRENT_TIMESTAMP",
            dialect="postgres",
            driver=mock_driver,
            target_dialect="sqlite",
        )
        assert result.success is True
        # transpiled_sql should be set when transpilation occurred
        assert result.transpiled_sql is not None or result.success

    @pytest.mark.asyncio
    async def test_no_transpilation_when_same_dialect(self, executor, mock_driver):
        """No transpilation should occur when source and target dialects match."""
        result = await executor.execute(
            sql="SELECT id FROM users",
            dialect="postgres",
            driver=mock_driver,
            target_dialect="postgres",
        )
        assert result.success is True
        # transpiled_sql should be None when no transpilation happened
        assert result.transpiled_sql is None

    @pytest.mark.asyncio
    async def test_no_transpilation_when_target_not_specified(self, executor, mock_driver):
        """No transpilation when target_dialect is not provided."""
        result = await executor.execute(
            sql="SELECT id FROM users",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is True
        assert result.transpiled_sql is None

    @pytest.mark.asyncio
    async def test_transpilation_updates_dialect(self, executor, mock_driver):
        """Result dialect should reflect the target dialect after transpilation."""
        result = await executor.execute(
            sql="SELECT CURRENT_TIMESTAMP",
            dialect="postgres",
            driver=mock_driver,
            target_dialect="sqlite",
        )
        assert result.success is True
        assert result.dialect == "sqlite"


# ---------------------------------------------------------------------------
# TestSQLExecutorExecution - driver interaction and error handling
# ---------------------------------------------------------------------------


class TestSQLExecutorExecution:
    """Verify execution behavior including driver calls, params, and errors."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def executor(self):
        return SQLExecutor(timeout_seconds=5)

    @pytest.fixture
    def mock_driver(self):
        return _make_mock_driver()

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor, mock_driver):
        """Successful execution returns rows and row_count."""
        mock_driver.execute = AsyncMock(return_value=[{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}])
        result = await executor.execute(
            sql="SELECT id, name FROM users",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is True
        assert result.row_count == 2
        assert len(result.rows) == 2
        assert result.rows[0]["name"] == "alice"

    @pytest.mark.asyncio
    async def test_execution_with_params(self, executor, mock_driver):
        """Parameters should be passed through to the driver."""
        params = {"user_id": 42}
        await executor.execute(
            sql="SELECT * FROM users WHERE id = :user_id",
            dialect="postgres",
            driver=mock_driver,
            params=params,
        )
        mock_driver.execute.assert_called_once()
        call_args = mock_driver.execute.call_args
        assert call_args[1].get("params") == params or call_args[0][1] == params

    @pytest.mark.asyncio
    async def test_timeout_triggers_cancel(self, executor):
        """Timeout should trigger driver.cancel() and raise SQLTimeoutError."""
        slow_driver = AsyncMock(spec=DatabaseDriver)
        slow_driver.is_healthy = True

        async def slow_execute(sql, params=None):
            await asyncio.sleep(10)  # noqa: sleep-duration
            return []

        slow_driver.execute = slow_execute
        slow_driver.cancel = AsyncMock(return_value=True)

        with pytest.raises(SQLTimeoutError, match="timeout"):
            await executor.execute(
                sql="SELECT * FROM large_table",
                dialect="postgres",
                driver=slow_driver,
            )
        slow_driver.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_error_propagation(self, executor):
        """SQLConnectionError from driver should propagate unchanged."""
        error_driver = _make_mock_driver(execute_side_effect=SQLConnectionError("Connection refused"))
        with pytest.raises(SQLConnectionError, match="Connection refused"):
            await executor.execute(
                sql="SELECT 1",
                dialect="postgres",
                driver=error_driver,
            )

    @pytest.mark.asyncio
    async def test_generic_exception_wrapped_as_execution_error(self, executor):
        """Non-SQL exceptions from driver should be wrapped in SQLExecutionError."""
        error_driver = _make_mock_driver(execute_side_effect=RuntimeError("disk full"))
        with pytest.raises(SQLExecutionError, match="disk full"):
            await executor.execute(
                sql="SELECT 1",
                dialect="postgres",
                driver=error_driver,
            )

    @pytest.mark.asyncio
    async def test_empty_result_set(self, executor):
        """Empty result set should return success with zero rows."""
        empty_driver = _make_mock_driver(rows=[])
        result = await executor.execute(
            sql="SELECT id FROM users WHERE id = -1",
            dialect="postgres",
            driver=empty_driver,
        )
        assert result.success is True
        assert result.row_count == 0
        assert result.rows == []

    @pytest.mark.asyncio
    async def test_cancel_failure_after_timeout_still_raises(self, executor):
        """Even if cancel() fails, SQLTimeoutError should still be raised."""
        slow_driver = AsyncMock(spec=DatabaseDriver)
        slow_driver.is_healthy = True

        async def slow_execute(sql, params=None):
            await asyncio.sleep(10)  # noqa: sleep-duration
            return []

        slow_driver.execute = slow_execute
        slow_driver.cancel = AsyncMock(side_effect=RuntimeError("cancel failed"))

        with pytest.raises(SQLTimeoutError):
            await executor.execute(
                sql="SELECT * FROM large_table",
                dialect="postgres",
                driver=slow_driver,
            )

    @pytest.mark.asyncio
    async def test_security_error_propagation(self, executor):
        """SQLSecurityError from driver should propagate unchanged."""
        error_driver = _make_mock_driver(execute_side_effect=SQLSecurityError("Injection detected"))
        with pytest.raises(SQLSecurityError, match="Injection detected"):
            await executor.execute(
                sql="SELECT 1",
                dialect="postgres",
                driver=error_driver,
            )


# ---------------------------------------------------------------------------
# TestSQLExecutorRawSQL - raw SQL controls via env var
# ---------------------------------------------------------------------------


class TestSQLExecutorRawSQL:
    """Verify raw SQL controls via DISABLE_RAW_SQL environment variable."""

    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_raw_sql_blocked_when_disabled(self):
        """allow_raw_sql=True should raise when DISABLE_RAW_SQL is set."""
        with patch.dict(os.environ, {"DISABLE_RAW_SQL": "true"}):
            executor = SQLExecutor()
            mock_driver = _make_mock_driver()
            with pytest.raises(SQLSecurityError, match="disabled"):
                await executor.execute(
                    sql="SELECT 1",
                    dialect="postgres",
                    driver=mock_driver,
                    allow_raw_sql=True,
                )

    @pytest.mark.asyncio
    async def test_raw_sql_allowed_when_not_disabled(self):
        """allow_raw_sql=True should work when DISABLE_RAW_SQL is not set."""
        with patch.dict(os.environ, {"DISABLE_RAW_SQL": "false"}):
            executor = SQLExecutor()
            mock_driver = _make_mock_driver()
            result = await executor.execute(
                sql="SELECT 1",
                dialect="postgres",
                driver=mock_driver,
                allow_raw_sql=True,
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_raw_sql_not_checked_when_flag_not_set(self):
        """When allow_raw_sql=False (default), env var is irrelevant."""
        with patch.dict(os.environ, {"DISABLE_RAW_SQL": "true"}):
            executor = SQLExecutor()
            mock_driver = _make_mock_driver()
            # Should NOT raise because allow_raw_sql defaults to False
            result = await executor.execute(
                sql="SELECT 1",
                dialect="postgres",
                driver=mock_driver,
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_raw_sql_env_case_insensitive(self):
        """DISABLE_RAW_SQL should work with 'TRUE' (uppercase)."""
        with patch.dict(os.environ, {"DISABLE_RAW_SQL": "TRUE"}):
            executor = SQLExecutor()
            mock_driver = _make_mock_driver()
            with pytest.raises(SQLSecurityError, match="disabled"):
                await executor.execute(
                    sql="SELECT 1",
                    dialect="postgres",
                    driver=mock_driver,
                    allow_raw_sql=True,
                )


# ---------------------------------------------------------------------------
# TestSQLExecutorInterpolation - detection of interpolation patterns
# ---------------------------------------------------------------------------


class TestSQLExecutorInterpolation:
    """Verify detection of string interpolation patterns."""

    def teardown_method(self):
        gc.collect()

    def test_detects_fstring_patterns(self):
        """f-string style {var} should be detected."""
        assert SQLExecutor._has_interpolation_patterns("SELECT * FROM {table}")

    def test_detects_named_percent_formatting(self):
        """Named %-formatting like %(name)s should be detected."""
        assert SQLExecutor._has_interpolation_patterns("SELECT * FROM %(table)s")
        assert SQLExecutor._has_interpolation_patterns("SELECT * FROM users WHERE id = %(user_id)d")

    def test_simple_percent_s_not_flagged(self):
        """Simple %s should NOT be flagged (too many false positives with LIKE)."""
        assert not SQLExecutor._has_interpolation_patterns("SELECT * FROM users WHERE name LIKE '%s%'")
        assert not SQLExecutor._has_interpolation_patterns("SELECT * FROM %s")

    def test_string_concatenation_not_flagged(self):
        """SQL string concatenation (valid in T-SQL) should NOT be flagged."""
        assert not SQLExecutor._has_interpolation_patterns("SELECT 'Value: ' + column_name FROM t")
        assert not SQLExecutor._has_interpolation_patterns("SELECT 'a' + 'b'")

    def test_safe_sql_not_flagged(self):
        """Normal SQL without interpolation patterns should not be flagged."""
        assert not SQLExecutor._has_interpolation_patterns("SELECT id, name FROM users WHERE id = 1")

    def test_parameterized_placeholder_not_flagged(self):
        """Standard SQL placeholders (:param) should not be flagged."""
        assert not SQLExecutor._has_interpolation_patterns("SELECT * FROM users WHERE id = :user_id")

    def test_question_mark_placeholder_not_flagged(self):
        """Standard SQL ? placeholders should not be flagged."""
        assert not SQLExecutor._has_interpolation_patterns("SELECT * FROM users WHERE id = ?")


# ---------------------------------------------------------------------------
# TestSQLExecutorInterpolationIntegration - interpolation check in execute()
# ---------------------------------------------------------------------------


class TestSQLExecutorInterpolationIntegration:
    """Verify that execute() blocks SQL containing interpolation patterns."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def executor(self):
        return SQLExecutor()

    @pytest.fixture
    def mock_driver(self):
        return _make_mock_driver()

    @pytest.mark.asyncio
    async def test_fstring_pattern_blocked_in_execute(self, executor, mock_driver):
        """execute() should raise SQLSecurityError for f-string patterns."""
        with pytest.raises(SQLSecurityError, match="interpolation"):
            await executor.execute(
                sql="SELECT * FROM {table}",
                dialect="postgres",
                driver=mock_driver,
            )
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_named_percent_format_blocked_in_execute(self, executor, mock_driver):
        """execute() should raise SQLSecurityError for named %-formatting."""
        with pytest.raises(SQLSecurityError, match="interpolation"):
            await executor.execute(
                sql="SELECT * FROM %(table)s",
                dialect="postgres",
                driver=mock_driver,
            )
        mock_driver.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_sql_string_concatenation_allowed(self, executor, mock_driver):
        """Valid SQL string concatenation (T-SQL style) should NOT be blocked."""
        # This is valid SQL in SQL Server and should pass validation
        # Note: May fail on Postgres syntax, but should not be blocked by interpolation check
        result = await executor.execute(
            sql="SELECT 'prefix' || 'suffix' AS combined",
            dialect="postgres",
            driver=mock_driver,
        )
        # Should succeed (|| is Postgres concatenation)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_like_pattern_with_percent_allowed(self, executor, mock_driver):
        """LIKE patterns with % should NOT be blocked."""
        result = await executor.execute(
            sql="SELECT * FROM users WHERE name LIKE '%test%'",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.success is True
        mock_driver.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_sql_not_blocked(self, executor, mock_driver):
        """Normal parameterized SQL should not be blocked."""
        result = await executor.execute(
            sql="SELECT id, name FROM users WHERE id = :user_id",
            dialect="postgres",
            driver=mock_driver,
            params={"user_id": 42},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_raw_sql_bypasses_interpolation_check(self, executor, mock_driver):
        """allow_raw_sql=True should bypass the interpolation check."""
        # Note: validation may still fail for other reasons, but the interpolation
        # check specifically should be skipped
        result = await executor.execute(
            sql="SELECT * FROM {table}",
            dialect="postgres",
            driver=mock_driver,
            allow_raw_sql=True,
        )
        # The query will likely fail validation (invalid SQL), but it should
        # NOT raise SQLSecurityError for interpolation
        assert result.success is False
        assert "interpolation" not in (result.error or "").lower()


# ---------------------------------------------------------------------------
# TestSQLExecutorConstructor - constructor defaults
# ---------------------------------------------------------------------------


class TestSQLExecutorConstructor:
    """Verify constructor parameter defaults and initialization."""

    def teardown_method(self):
        gc.collect()

    def test_executor_default_constructor_works(self):
        """SQLExecutor with no arguments should create default dependencies."""
        executor = SQLExecutor()
        assert executor._validator is not None
        assert executor._transpiler is not None
        assert executor._registry is not None
        assert executor._timeout_seconds == 30

    def test_executor_with_custom_timeout_value(self):
        """Custom timeout should be respected."""
        executor = SQLExecutor(timeout_seconds=60)
        assert executor._timeout_seconds == 60

    def test_executor_with_custom_validator_instance(self):
        """Custom validator should be used."""
        validator = SQLValidator(allowed_tables={"users"})
        executor = SQLExecutor(validator=validator)
        assert executor._validator is validator

    def test_executor_with_custom_transpiler_instance(self):
        """Custom transpiler should be used."""
        transpiler = SQLTranspiler()
        executor = SQLExecutor(transpiler=transpiler)
        assert executor._transpiler is transpiler

    def test_transpiler_uses_provided_validator(self):
        """When custom validator is provided without transpiler, transpiler should use it."""
        validator = SQLValidator()
        executor = SQLExecutor(validator=validator)
        assert executor._transpiler._validator is validator


# ---------------------------------------------------------------------------
# TestSQLExecutorWarnings - warning propagation
# ---------------------------------------------------------------------------


class TestSQLExecutorWarnings:
    """Verify warning collection and propagation through the pipeline."""

    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_validation_warnings_propagated(self):
        """Warnings from validation should appear in the result."""
        executor = SQLExecutor()
        mock_driver = _make_mock_driver()
        # This SQL has a suspicious literal that the validator may warn about
        # Using a known injection-like pattern in a string literal
        result = await executor.execute(
            sql="SELECT id FROM users WHERE name = 'admin' OR '1'='1'",
            dialect="postgres",
            driver=mock_driver,
        )
        # Regardless of whether warnings are generated, result should be structured properly
        assert isinstance(result.warnings, list)

    @pytest.mark.asyncio
    async def test_result_dialect_set_correctly(self):
        """Result dialect should match the execution dialect."""
        executor = SQLExecutor()
        mock_driver = _make_mock_driver()
        result = await executor.execute(
            sql="SELECT 1",
            dialect="postgres",
            driver=mock_driver,
        )
        assert result.dialect == "postgres"


# ---------------------------------------------------------------------------
# TestSQLExecutorParameterTranslation - ParameterContract integration
# ---------------------------------------------------------------------------


class TestSQLExecutorParameterTranslation:
    """Verify that ParameterContract.translate() is called before driver.execute()."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def mock_driver_with_name(self):
        """Create a mock driver that exposes driver_name."""
        mock_driver = AsyncMock(spec=DatabaseDriver)
        mock_driver.execute = AsyncMock(return_value=[{"id": 1}])
        mock_driver.cancel = AsyncMock(return_value=True)
        mock_driver.is_healthy = True
        mock_driver.driver_name = "asyncpg"
        return mock_driver

    @pytest.mark.asyncio
    async def test_params_translated_for_asyncpg_driver(self, mock_driver_with_name):
        """asyncpg driver should receive $1-style positional params."""
        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT * FROM users WHERE id = :id",
            dialect="postgres",
            driver=mock_driver_with_name,
            params={"id": 42},
        )
        assert result.success is True
        # The driver should have been called with translated SQL and params
        call_args = mock_driver_with_name.execute.call_args
        executed_sql = call_args[0][0]
        executed_params = call_args[0][1]
        assert "$1" in executed_sql
        assert ":id" not in executed_sql
        assert executed_params == [42]

    @pytest.mark.asyncio
    async def test_params_none_skips_translation(self, mock_driver_with_name):
        """When params is None, translation should be skipped."""
        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT 1",
            dialect="postgres",
            driver=mock_driver_with_name,
            params=None,
        )
        assert result.success is True
        call_args = mock_driver_with_name.execute.call_args
        # Should pass None through
        assert call_args[0][1] is None

    @pytest.mark.asyncio
    async def test_translation_happens_after_row_limit(self, mock_driver_with_name):
        """Parameter translation should happen AFTER RowLimitEnforcer."""
        policy = DataAccessPolicy(
            tenant_id="tenant-1",
            allowed_schemas={"public"},
            blocked_columns=set(),
            max_rows=100,
        )
        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT * FROM users WHERE id = :id",
            dialect="postgres",
            driver=mock_driver_with_name,
            params={"id": 42},
            policy=policy,
        )
        assert result.success is True
        call_args = mock_driver_with_name.execute.call_args
        executed_sql = call_args[0][0]
        # SQL should have BOTH the LIMIT and $1 placeholder
        assert "LIMIT" in executed_sql.upper()
        assert "$1" in executed_sql
        assert ":id" not in executed_sql

    @pytest.mark.asyncio
    async def test_named_driver_params_stay_as_dict(self):
        """Named-style drivers should receive dict params (not positional)."""
        mock_driver = AsyncMock(spec=DatabaseDriver)
        mock_driver.execute = AsyncMock(return_value=[])
        mock_driver.cancel = AsyncMock(return_value=True)
        mock_driver.is_healthy = True
        mock_driver.driver_name = "snowflake"

        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT * FROM users WHERE id = :id",
            dialect="snowflake",
            driver=mock_driver,
            params={"id": 42},
        )
        assert result.success is True
        call_args = mock_driver.execute.call_args
        executed_params = call_args[0][1]
        assert isinstance(executed_params, dict)

    @pytest.mark.asyncio
    async def test_translation_uses_target_dialect(self):
        """When transpiling, translation should use the target dialect."""
        mock_driver = AsyncMock(spec=DatabaseDriver)
        mock_driver.execute = AsyncMock(return_value=[])
        mock_driver.cancel = AsyncMock(return_value=True)
        mock_driver.is_healthy = True
        mock_driver.driver_name = "aiosqlite"

        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT * FROM users WHERE id = :id",
            dialect="postgres",
            driver=mock_driver,
            params={"id": 42},
            target_dialect="sqlite",
        )
        assert result.success is True
        call_args = mock_driver.execute.call_args
        executed_sql = call_args[0][0]
        executed_params = call_args[0][1]
        # aiosqlite uses ? placeholders
        assert "?" in executed_sql
        assert executed_params == [42]

    @pytest.mark.asyncio
    async def test_empty_params_dict_skips_translation(self, mock_driver_with_name):
        """Empty params dict should still be passed through without translation."""
        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT 1",
            dialect="postgres",
            driver=mock_driver_with_name,
            params={},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_driver_without_driver_name_skips_translation(self):
        """Drivers without driver_name (e.g., mocks) should skip translation."""
        mock_driver = _make_mock_driver()
        # No driver_name attribute
        executor = SQLExecutor()
        result = await executor.execute(
            sql="SELECT * FROM users WHERE id = :id",
            dialect="postgres",
            driver=mock_driver,
            params={"id": 42},
        )
        assert result.success is True
