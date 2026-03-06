"""Unified parameter binding across database drivers using SQLGlot AST."""

import logging

from collections.abc import Mapping

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from typing import Any

from .exceptions import SQLParseError

logger = logging.getLogger(__name__)


def _placeholder_name(node: exp.Placeholder) -> str | None:
    """Extract a string name from a Placeholder node.

    After a parse→sql→parse round-trip through SQLGlot, the
    ``Placeholder.this`` attribute may be either a plain ``str``
    (from the first parse) or an ``exp.Identifier`` wrapper (from
    the second parse of ``%(name)s`` format). This helper normalises
    both to a plain string.
    """
    raw = node.this
    if raw is None:
        return getattr(node, "name", None)
    if isinstance(raw, str):
        return raw if raw != "?" else None
    # exp.Identifier (or other Expression subclass)
    if hasattr(raw, "this"):
        return str(raw.this)
    return str(raw)


class ParameterContract:
    """Unified parameter binding across database drivers.

    Uses SQLGlot's tokenizer to safely identify placeholders without
    corrupting string literals or comments.
    """

    DRIVER_STYLES: dict[str, dict[str, str]] = {
        "asyncpg": {"style": "positional", "format": "${}"},
        "aiosqlite": {"style": "positional", "format": "?"},
        "psycopg": {"style": "named", "format": "%({})s"},
        "bigquery": {"style": "named", "format": "@{}"},
        "snowflake": {"style": "named", "format": ":{}"},
        "sql.js": {"style": "positional", "format": "?"},
        "aiomysql": {"style": "positional", "format": "%s"},
        "duckdb": {"style": "positional", "format": "?"},
        "redshift_connector": {"style": "named", "format": "%({})s"},
        "asynch": {"style": "named", "format": "%({})s"},
        "trino": {"style": "positional", "format": "?"},
    }

    def __init__(self, driver: str, dialect: str = "postgres"):
        if driver not in self.DRIVER_STYLES:
            raise ValueError(f"Unknown driver: {driver}. Valid: {list(self.DRIVER_STYLES)}")
        self.driver = driver
        self.dialect = dialect
        self.style = self.DRIVER_STYLES[driver]

    def translate(self, sql: str, params: Mapping[str, Any]) -> tuple[str, list[Any] | dict[str, Any]]:
        """Translate canonical :name placeholders to driver-specific format."""
        try:
            ast = sqlglot.parse_one(sql, dialect=self.dialect)
        except ParseError as e:
            raise SQLParseError(f"Failed to parse SQL for parameter translation: {e}")

        placeholder_nodes = list(ast.find_all(exp.Placeholder))

        if not placeholder_nodes:
            if params:
                raise SQLParseError(f"Parameters provided but no placeholders in SQL: {list(params.keys())}")
            return sql, [] if self.style["style"] == "positional" else {}

        placeholder_names = []
        for node in placeholder_nodes:
            name = _placeholder_name(node)
            if name:
                placeholder_names.append(name)

        missing = set(placeholder_names) - set(params.keys())
        if missing:
            raise SQLParseError(f"Missing parameters: {missing}")

        if self.style["style"] == "positional":
            positional_params: list[Any] = []
            counter = [0]

            def transform_positional(node: exp.Expression) -> exp.Expression:
                if isinstance(node, exp.Placeholder):
                    name = _placeholder_name(node)
                    if name and name in params:
                        positional_params.append(params[name])
                        counter[0] += 1
                        fmt = self.style["format"]
                        if fmt == "?":
                            return exp.Placeholder(this="?")
                        return exp.Placeholder(this=fmt.format(counter[0]))
                return node

            translated_ast = ast.transform(transform_positional)
            return translated_ast.sql(dialect=self.dialect), positional_params
        else:

            def transform_named(node: exp.Expression) -> exp.Expression:
                if isinstance(node, exp.Placeholder):
                    name = _placeholder_name(node)
                    if name and name in params:
                        new_placeholder = self.style["format"].format(name)
                        return exp.Placeholder(this=new_placeholder)
                return node

            translated_ast = ast.transform(transform_named)
            return translated_ast.sql(dialect=self.dialect), dict(params)

    def validate_param_count(self, sql: str, params: Mapping[str, Any]) -> None:
        """Ensure all placeholders have corresponding params."""
        try:
            ast = sqlglot.parse_one(sql, dialect=self.dialect)
        except ParseError as e:
            raise SQLParseError(f"Failed to parse SQL: {e}")

        placeholder_nodes = list(ast.find_all(exp.Placeholder))
        placeholders = {_placeholder_name(node) for node in placeholder_nodes if _placeholder_name(node) is not None}
        param_keys = set(params.keys())

        missing = placeholders - param_keys
        if missing:
            raise SQLParseError(f"Missing parameters: {missing}")

        unused = param_keys - placeholders
        if unused:
            logger.warning("Unused parameters: %s", unused)
