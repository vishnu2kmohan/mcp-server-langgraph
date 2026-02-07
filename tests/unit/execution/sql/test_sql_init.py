"""Tests for SQL module public API.

TDD: Written FIRST to define expected public API surface
for the sql/ package __init__.py exports.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="sql_init")
class TestSQLModulePublicAPI:
    """Tests for SQL module __init__.py public API exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_import_sql_validator(self) -> None:
        """
        GIVEN: sql module
        WHEN: SQLValidator is imported
        THEN: It is importable and not None
        """
        from mcp_server_langgraph.execution.sql import SQLValidator

        assert SQLValidator is not None

    def test_import_sql_transpiler(self) -> None:
        """
        GIVEN: sql module
        WHEN: SQLTranspiler is imported
        THEN: It is importable and not None
        """
        from mcp_server_langgraph.execution.sql import SQLTranspiler

        assert SQLTranspiler is not None

    def test_import_sql_executor(self) -> None:
        """
        GIVEN: sql module
        WHEN: SQLExecutor is imported
        THEN: It is importable and not None
        """
        from mcp_server_langgraph.execution.sql import SQLExecutor

        assert SQLExecutor is not None

    def test_import_execution_result(self) -> None:
        """
        GIVEN: sql module
        WHEN: ExecutionResult is imported
        THEN: It is importable and not None
        """
        from mcp_server_langgraph.execution.sql import ExecutionResult

        assert ExecutionResult is not None

    def test_import_validation_result(self) -> None:
        """
        GIVEN: sql module
        WHEN: ValidationResult is imported
        THEN: It is importable and not None
        """
        from mcp_server_langgraph.execution.sql import ValidationResult

        assert ValidationResult is not None

    def test_module_exports_exception_classes(self) -> None:
        """
        GIVEN: sql module
        WHEN: Exception classes are imported
        THEN: All three are importable and not None
        """
        from mcp_server_langgraph.execution.sql import (
            SQLExecutionError,
            SQLTimeoutError,
            SQLValidationError,
        )

        assert SQLExecutionError is not None
        assert SQLTimeoutError is not None
        assert SQLValidationError is not None

    def test_module_all_exports_complete(self) -> None:
        """
        GIVEN: sql module
        WHEN: __all__ is inspected
        THEN: It contains exactly the expected public API
        """
        import mcp_server_langgraph.execution.sql as sql_mod

        expected = {
            "ExecutionResult",
            "SQLExecutionError",
            "SQLExecutor",
            "SQLTimeoutError",
            "SQLTranspiler",
            "SQLValidationError",
            "SQLValidator",
            "ValidationResult",
        }
        assert set(sql_mod.__all__) == expected
