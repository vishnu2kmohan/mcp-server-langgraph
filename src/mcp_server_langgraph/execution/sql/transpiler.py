"""SQL dialect transpiler with caching and post-transpilation validation."""

import logging
from functools import lru_cache

import sqlglot
from sqlglot import exp

from .exceptions import SQLTranspileError
from .types import ValidationResult
from .validator import SQLValidator

logger = logging.getLogger(__name__)


class SQLTranspiler:
    """SQL dialect transpiler with post-transpilation validation.

    SECURITY: Transpilation can introduce dialect-specific constructs that
    may bypass the original validation. Always re-validate after transpiling.
    """

    def __init__(self, validator: SQLValidator | None = None):
        self._validator = validator or SQLValidator()

    @staticmethod
    @lru_cache(maxsize=1000)
    def parse_cached(sql: str, dialect: str) -> exp.Expression:
        """Cache parsed ASTs for repeated queries."""
        return sqlglot.parse_one(sql, dialect=dialect)

    @staticmethod
    @lru_cache(maxsize=500)
    def transpile(sql: str, source: str, target: str) -> str:
        """Transpile SQL between dialects with caching."""
        result = sqlglot.transpile(sql, read=source, write=target)
        if not result:
            raise SQLTranspileError(f"Transpilation produced no output: {sql[:100]}")
        return result[0]

    def transpile_and_validate(self, sql: str, source: str, target: str) -> tuple[str, ValidationResult]:
        """Transpile SQL and re-validate in target dialect.

        Pre-validates against the source dialect to catch dangerous functions
        before transpilation, then re-validates transpiled output against
        the target dialect's blocklists.

        Returns:
            (transpiled_sql, validation_result)

        Raises:
            SQLTranspileError: If transpilation or validation fails.
        """
        # Pre-validate against source dialect blocklists
        source_validation = self._validator.validate(sql, dialect=source)
        if not source_validation.is_valid:
            raise SQLTranspileError(f"Source SQL failed validation for {source}: {source_validation.errors}")

        try:
            transpiled = self.transpile(sql, source, target)
        except Exception as e:
            raise SQLTranspileError(f"Transpilation failed ({source}->{target}): {e}")

        # Re-validate with target dialect's blocklists
        validation = self._validator.validate(transpiled, dialect=target)
        if not validation.is_valid:
            raise SQLTranspileError(f"Transpiled SQL failed validation for {target}: {validation.errors}")

        return transpiled, validation

    def validate_transpiled_sql(self, sql: str, target_dialect: str) -> ValidationResult:
        """Validate already-transpiled SQL against target dialect rules."""
        return self._validator.validate(sql, dialect=target_dialect)
