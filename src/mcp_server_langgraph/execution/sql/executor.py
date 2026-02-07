"""Unified SQL executor with validate -> transpile -> execute pipeline."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
from typing import Any

import sqlglot

from mcp_server_langgraph.execution.sql.drivers.base import DatabaseDriver
from mcp_server_langgraph.execution.sql.drivers.registry import DriverRegistry
from mcp_server_langgraph.execution.sql.exceptions import (
    SQLConnectionError,
    SQLExecutionError,
    SQLParseError,
    SQLSecurityError,
    SQLTimeoutError,
)
from mcp_server_langgraph.execution.sql.log_redactor import SQLExecutionLogger
from mcp_server_langgraph.execution.sql.parameter_contract import ParameterContract
from mcp_server_langgraph.execution.sql.policy import DataAccessPolicy, RowLimitEnforcer
from mcp_server_langgraph.execution.sql.transpiler import SQLTranspiler
from mcp_server_langgraph.execution.sql.validator import SQLValidator

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of SQL execution."""

    success: bool
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    dialect: str = ""
    transpiled_sql: str | None = None


class SQLExecutor:
    """Unified SQL executor.

    Pipeline: validate -> policy check -> transpile (optional) -> row limit -> execute
    """

    def __init__(
        self,
        validator: SQLValidator | None = None,
        transpiler: SQLTranspiler | None = None,
        registry: DriverRegistry | None = None,
        execution_logger: SQLExecutionLogger | None = None,
        timeout_seconds: int = 30,
    ):
        self._validator = validator or SQLValidator()
        self._transpiler = transpiler or SQLTranspiler(self._validator)
        self._registry = registry or DriverRegistry()
        self._execution_logger = execution_logger
        self._timeout_seconds = timeout_seconds
        self._raw_sql_disabled = os.getenv("DISABLE_RAW_SQL", "false").lower() == "true"

    async def execute(
        self,
        sql: str,
        dialect: str,
        driver: DatabaseDriver,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
        policy: DataAccessPolicy | None = None,
        target_dialect: str | None = None,
        *,
        allow_raw_sql: bool = False,
    ) -> ExecutionResult:
        """Execute SQL through the full pipeline."""
        warnings: list[str] = []

        # 1. Raw SQL check
        if allow_raw_sql and self._raw_sql_disabled:
            raise SQLSecurityError("Raw SQL execution is disabled in this environment")

        # 1b. Audit log raw SQL execution (SECURITY: plan requires logging all raw SQL)
        if allow_raw_sql and self._execution_logger:
            self._execution_logger.log_query(
                level=logging.WARNING,
                message="Raw SQL execution requested",
                sql=sql,
                extra={"allow_raw_sql": True},
            )

        # 2. Check for string interpolation patterns (security: detect unsanitized SQL)
        if not allow_raw_sql and self._has_interpolation_patterns(sql):
            raise SQLSecurityError("SQL contains string interpolation patterns. Use parameterized queries instead.")

        # 3. Validate SQL
        validation = self._validator.validate(sql, dialect=dialect)
        if not validation.is_valid:
            return ExecutionResult(
                success=False,
                error=f"Validation failed: {'; '.join(validation.errors)}",
                dialect=dialect,
            )
        warnings.extend(validation.warnings)

        # 4. Policy check (if provided)
        if policy:
            ast = sqlglot.parse_one(sql, dialect=dialect)
            policy_errors = policy.validate_query(ast, dialect=dialect)
            if policy_errors:
                return ExecutionResult(
                    success=False,
                    error=f"Policy violation: {'; '.join(policy_errors)}",
                    dialect=dialect,
                )

        # 5. Transpile (if target dialect differs)
        transpiled_sql = sql
        if target_dialect and target_dialect != dialect:
            transpiled, trans_validation = self._transpiler.transpile_and_validate(sql, source=dialect, target=target_dialect)
            transpiled_sql = transpiled
            warnings.extend(trans_validation.warnings)
            dialect = target_dialect  # Use target dialect for execution

        # 6. Enforce row limit (if policy has max_rows)
        if policy:
            ast = sqlglot.parse_one(transpiled_sql, dialect=dialect)
            ast = RowLimitEnforcer.enforce(ast, policy.max_rows)
            transpiled_sql = ast.sql(dialect=dialect)

        # 6.5. Translate parameters to driver-specific format
        # Must happen AFTER row limit enforcement (SQLGlot can't parse $1/? placeholders)
        # Only translate when params is a Mapping (named :param placeholders);
        # Sequence params are already positional and don't need translation.
        translated_params: Sequence[Any] | Mapping[str, Any] | None = params
        if params is not None and isinstance(params, Mapping) and hasattr(driver, "driver_name"):
            driver_name = driver.driver_name
            if driver_name in ParameterContract.DRIVER_STYLES:
                contract = ParameterContract(driver_name, dialect=dialect)
                transpiled_sql, translated_params = contract.translate(transpiled_sql, params)

        # 7. Execute with timeout and cancellation
        try:
            async with asyncio.timeout(self._timeout_seconds):
                rows = await driver.execute(transpiled_sql, translated_params)

            return ExecutionResult(
                success=True,
                rows=rows,
                row_count=len(rows),
                warnings=warnings,
                dialect=dialect,
                transpiled_sql=transpiled_sql if transpiled_sql != sql else None,
            )

        except TimeoutError:
            # Cancel server-side query
            try:
                await driver.cancel()
            except Exception:
                logger.warning("Failed to cancel query after timeout", exc_info=True)
            raise SQLTimeoutError(f"Query exceeded {self._timeout_seconds}s timeout")
        except (SQLConnectionError, SQLTimeoutError, SQLSecurityError, SQLParseError):
            raise  # Re-raise our own exceptions
        except Exception as exc:
            raise SQLExecutionError(f"Query execution failed: {exc}") from exc

    @staticmethod
    def _has_interpolation_patterns(sql: str) -> bool:
        """Detect potential string interpolation patterns.

        Note: Only checks for Python string interpolation markers that are
        unlikely to appear in valid SQL. Avoids false positives by:
        - Using named format patterns %(<name>)s for %-formatting detection
        - Requiring f-string braces with alphanumeric identifiers
        - Skipping string concatenation (valid in SQL Server/T-SQL)
        """
        patterns = [
            r"\{\w+\}",  # f-string style: {var}
            r"%\([^)]+\)[sdifr]",  # Named %-formatting: %(name)s
        ]
        return any(re.search(p, sql) for p in patterns)
