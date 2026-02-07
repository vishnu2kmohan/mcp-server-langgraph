"""Per-tenant data access policy enforcement using SQLGlot AST."""

import logging
from dataclasses import dataclass, field

from sqlglot import exp

logger = logging.getLogger(__name__)


@dataclass
class DataAccessPolicy:
    """Per-session data access constraints.

    SECURITY: Uses fully-qualified table names and blocks system schemas.
    """

    tenant_id: str
    # Default schemas: "public" (Postgres), "main" (SQLite), "" (DuckDB/others)
    allowed_schemas: set[str] = field(default_factory=lambda: {"public", "main", ""})
    allowed_tables: set[str] = field(default_factory=set)  # Empty = all in allowed schemas
    blocked_columns: set[str] = field(default_factory=lambda: {"password", "secret"})
    max_rows: int = 10000

    BLOCKED_SYSTEM_SCHEMAS: frozenset[str] = frozenset(
        {
            "information_schema",
            "pg_catalog",
            "pg_temp",
            "sys",
            "mysql",
            "performance_schema",
        }
    )

    def validate_query(self, ast: exp.Expression, dialect: str = "postgres") -> list[str]:
        """Validate AST against policy. Returns list of error strings."""
        errors = []

        for table in ast.find_all(exp.Table):
            schema = table.db or "public"
            normalized_schema = self._normalize_identifier(schema, dialect)
            normalized_table = self._normalize_identifier(table.name, dialect)

            if normalized_schema.lower() in {s.lower() for s in self.BLOCKED_SYSTEM_SCHEMAS}:
                errors.append(f"System schema '{schema}' access blocked")
                continue

            if normalized_schema not in self.allowed_schemas:
                errors.append(f"Schema '{schema}' not allowed for tenant")

            if self.allowed_tables:
                fq_table = f"{normalized_schema}.{normalized_table}"
                if normalized_table not in self.allowed_tables and fq_table not in self.allowed_tables:
                    errors.append(f"Table '{table.name}' not allowed")

        if self.blocked_columns:
            for star in ast.find_all(exp.Star):
                errors.append("SELECT * not allowed when column restrictions are active")
                break

        for col in ast.find_all(exp.Column):
            normalized_col = self._normalize_identifier(col.name, dialect)
            if normalized_col in self.blocked_columns:
                errors.append(f"Column '{col.name}' is blocked")

        return errors

    @staticmethod
    def _normalize_identifier(identifier: str, dialect: str) -> str:
        if dialect in ("postgres", "snowflake", "bigquery"):
            return identifier.lower()
        return identifier


class RowLimitEnforcer:
    """Centralized row limit enforcement at AST level."""

    @staticmethod
    def enforce(ast: exp.Expression, max_rows: int) -> exp.Expression:
        """Enforce max_rows limit on the query.

        Handles:
        - No LIMIT: adds LIMIT max_rows
        - Literal LIMIT > max_rows: caps to max_rows
        - Parameterized/expression LIMIT: wraps in subquery with LIMIT max_rows
          to prevent bypass via user-controlled parameters
        """
        existing_limit = RowLimitEnforcer._get_limit_value(ast)

        if existing_limit is None:
            return ast.limit(max_rows)
        elif isinstance(existing_limit, int):
            if existing_limit > max_rows:
                return RowLimitEnforcer._replace_limit(ast, max_rows)
            return ast
        else:
            # Parameterized or expression-based LIMIT (e.g., LIMIT :limit, LIMIT ?)
            # Wrap in subquery to enforce hard cap regardless of parameter value
            return exp.select("*").from_(ast.subquery()).limit(max_rows)

    @staticmethod
    def _get_limit_value(ast: exp.Expression) -> int | str | None:
        if limit_node := ast.args.get("limit"):
            limit_expr = limit_node.expression
            if isinstance(limit_expr, exp.Literal):
                try:
                    return int(limit_expr.this)
                except (ValueError, TypeError):
                    return str(limit_expr.this)
            if limit_expr is not None:
                return str(limit_expr)
        return None

    @staticmethod
    def _replace_limit(ast: exp.Expression, new_limit: int) -> exp.Expression:
        return ast.copy().limit(new_limit, copy=False)
