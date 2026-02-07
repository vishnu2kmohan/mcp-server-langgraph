"""Tests for SQL integration in SandboxContext."""

import gc

import pytest

from mcp_server_langgraph.execution.sandbox_context import SandboxContext

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="sandbox_context_sql")
class TestSandboxContextSQL:
    """Tests for SQL validator and transpiler access from SandboxContext."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_get_sql_validator_returns_validator(self) -> None:
        """GIVEN a SandboxContext WHEN get_sql_validator called THEN returns SQLValidator."""
        from mcp_server_langgraph.execution.sql.validator import SQLValidator

        context = SandboxContext()
        validator = context.get_sql_validator()
        assert isinstance(validator, SQLValidator)

    def test_get_sql_validator_returns_new_instance(self) -> None:
        """GIVEN a SandboxContext WHEN get_sql_validator called twice THEN returns different instances."""
        context = SandboxContext()
        v1 = context.get_sql_validator()
        v2 = context.get_sql_validator()
        assert v1 is not v2

    def test_get_sql_transpiler_returns_transpiler(self) -> None:
        """GIVEN a SandboxContext WHEN get_sql_transpiler called THEN returns SQLTranspiler."""
        from mcp_server_langgraph.execution.sql.transpiler import SQLTranspiler

        context = SandboxContext()
        transpiler = context.get_sql_transpiler()
        assert isinstance(transpiler, SQLTranspiler)

    def test_get_sql_transpiler_returns_new_instance(self) -> None:
        """GIVEN a SandboxContext WHEN get_sql_transpiler called twice THEN returns different instances."""
        context = SandboxContext()
        t1 = context.get_sql_transpiler()
        t2 = context.get_sql_transpiler()
        assert t1 is not t2

    def test_validator_can_validate_query(self) -> None:
        """GIVEN a SandboxContext validator WHEN validating a SELECT THEN it returns valid result."""
        context = SandboxContext()
        validator = context.get_sql_validator()
        result = validator.validate("SELECT 1")
        assert result.is_valid

    def test_transpiler_can_transpile(self) -> None:
        """GIVEN a SandboxContext transpiler WHEN transpiling SQL THEN it returns transpiled SQL."""
        context = SandboxContext()
        transpiler = context.get_sql_transpiler()
        result = transpiler.transpile("SELECT NOW()", source="postgres", target="bigquery")
        assert result is not None
