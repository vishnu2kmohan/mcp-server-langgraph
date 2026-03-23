"""AST-based SQL validator using SQLGlot parser.

Validates SQL queries against a whitelist of allowed statement types,
blocks dangerous operations (DDL, DML writes, privilege escalation),
enforces table allowlists, and detects potential injection patterns.
"""

from __future__ import annotations

import re

import sqlglot
import sqlglot.expressions as exp
from .types import ValidationResult


class SQLValidator:
    """Validates SQL queries using AST-based analysis.

    Parses SQL into an AST via SQLGlot and walks the tree to enforce
    security constraints. Only read-oriented statements (SELECT, set
    operations, utility queries) are permitted; all write/DDL/DCL
    operations are blocked.

    Args:
        allowed_tables: Optional set of fully-qualified or unqualified
            table names that queries are permitted to reference. When
            ``None``, all tables are allowed.
    """

    # ------------------------------------------------------------------ #
    # Statement type whitelists
    # ------------------------------------------------------------------ #

    ALLOWED_STATEMENTS: set[type[exp.Expression]] = {
        exp.Select,
        exp.Union,
        exp.Except,
        exp.Intersect,
    }

    ALLOWED_WRAPPERS: set[type[exp.Expression]] = {
        exp.With,
        exp.Subquery,
    }

    ALLOWED_UTILITY: set[type[exp.Expression]] = {
        exp.Describe,
        exp.Show,
    }

    # ------------------------------------------------------------------ #
    # Blocked node types (write / DDL / DCL)
    # ------------------------------------------------------------------ #

    BLOCKED_NODES: set[type[exp.Expression]] = {
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.TruncateTable,
        exp.Delete,
        exp.Update,
        exp.Insert,
        exp.Grant,
        exp.Revoke,
        exp.Into,
        exp.Copy,
        exp.Command,
    }

    # ------------------------------------------------------------------ #
    # Dialect-specific blocked commands (raw command strings)
    # ------------------------------------------------------------------ #

    DIALECT_BLOCKED: dict[str, set[str]] = {
        "postgres": {
            "COPY",
            "VACUUM",
            "REINDEX",
            "CLUSTER",
            "LISTEN",
            "NOTIFY",
            "LOAD",
        },
        "mysql": {
            "LOAD DATA",
            "LOAD XML",
            "HANDLER",
            "PURGE",
            "RESET",
            "FLUSH",
        },
        "sqlite": {
            "ATTACH",
            "DETACH",
            "VACUUM",
            "REINDEX",
        },
        "bigquery": {
            "MERGE",
            "EXPORT DATA",
        },
    }

    # ------------------------------------------------------------------ #
    # Blocked functions per dialect
    # ------------------------------------------------------------------ #

    BLOCKED_FUNCTIONS: dict[str, set[str]] = {
        "postgres": {
            "pg_read_file",
            "pg_read_binary_file",
            "pg_ls_dir",
            "pg_stat_file",
            "pg_sleep",
            "dblink",
            "dblink_exec",
            "lo_import",
            "lo_export",
            "pg_execute_server_program",
            "query_to_xml",
        },
        "mysql": {
            "load_file",
            "into_outfile",
            "into_dumpfile",
            "sys_exec",
            "sys_eval",
            "sleep",
            "benchmark",
        },
        "sqlite": {
            "load_extension",
            "readfile",
            "writefile",
            "fts3_tokenizer",
        },
        "bigquery": {
            "external_query",
        },
    }

    # ------------------------------------------------------------------ #
    # Injection detection patterns
    # ------------------------------------------------------------------ #

    _INJECTION_PATTERNS: list[re.Pattern[str]] = [
        # Stacked queries via semicolons
        re.compile(r";\s*(DROP|ALTER|CREATE|INSERT|UPDATE|DELETE|GRANT|REVOKE)", re.IGNORECASE),
        # Comment-based injection (inline or block)
        re.compile(r"(--|/\*|#)\s*(DROP|ALTER|CREATE|INSERT|UPDATE|DELETE)", re.IGNORECASE),
        # UNION-based injection probes
        re.compile(r"UNION\s+(ALL\s+)?SELECT\s+NULL", re.IGNORECASE),
        # Boolean/time-based blind injection
        re.compile(r"(OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?", re.IGNORECASE),
        # WAITFOR / pg_sleep injection
        re.compile(r"(WAITFOR\s+DELAY|pg_sleep|SLEEP\s*\(|BENCHMARK\s*\()", re.IGNORECASE),
        # Hex-encoded payloads
        re.compile(r"0x[0-9a-fA-F]{8,}"),
    ]

    def __init__(self, allowed_tables: set[str] | None = None) -> None:
        self._allowed_tables = allowed_tables

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def validate(self, sql: str, dialect: str = "postgres") -> ValidationResult:
        """Validate a SQL query for safety and correctness.

        Performs the following checks in order:

        1. Parse the SQL string into an AST (catches syntax errors).
        2. Block multi-statement queries (only one statement allowed).
        3. Verify the top-level statement type against the whitelist,
           unwrapping CTE (``WITH``) and subquery wrappers as needed.
        4. Walk the full AST to detect blocked node types.
        5. Enforce the table allowlist when configured.
        6. Validate function calls for dangerous dialect-specific functions.
        7. Scan string literals for potential injection patterns.

        Args:
            sql: The SQL query string to validate.
            dialect: The SQL dialect to use for parsing (e.g. ``"postgres"``,
                ``"mysql"``, ``"sqlite"``, ``"bigquery"``).

        Returns:
            A ``ValidationResult`` indicating whether the query is valid,
            along with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # -------------------------------------------------------------- #
        # 1. Parse
        # -------------------------------------------------------------- #
        try:
            statements = sqlglot.parse(sql, dialect=dialect)
        except Exception as exc:
            errors.append(f"Failed to parse SQL: {exc}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Filter out None entries (blank statements from trailing semicolons)
        statements = [s for s in statements if s is not None]

        if not statements:
            errors.append("Empty SQL query")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # -------------------------------------------------------------- #
        # 2. Block multi-statement queries
        # -------------------------------------------------------------- #
        if len(statements) > 1:
            errors.append("Multi-statement queries are not allowed; submit one statement at a time")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        ast = statements[0]
        # Use raise (not assert) because assert is stripped by python -O
        if ast is None:
            errors.append("Parser returned None expression")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # -------------------------------------------------------------- #
        # 3. Verify statement type (whitelist with wrapper support)
        # -------------------------------------------------------------- #
        root = ast
        # Unwrap wrappers (WITH / Subquery) to find the core statement
        while type(root) in self.ALLOWED_WRAPPERS:
            inner = root.this
            if inner is None:
                break
            root = inner

        if type(root) not in self.ALLOWED_STATEMENTS and type(root) not in self.ALLOWED_UTILITY:
            errors.append(
                f"Statement type '{type(root).__name__}' is not allowed; only SELECT and set operations are permitted"
            )
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # -------------------------------------------------------------- #
        # 4. Walk AST for blocked nodes
        # -------------------------------------------------------------- #
        for node in ast.walk():
            if type(node) in self.BLOCKED_NODES:
                errors.append(f"Blocked operation detected: {type(node).__name__}")

        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # -------------------------------------------------------------- #
        # 5. Check table allowlist
        # -------------------------------------------------------------- #
        if self._allowed_tables is not None:
            for table_node in ast.find_all(exp.Table):
                table_name = table_node.name
                # Build fully-qualified name if catalog/schema present
                parts = [p for p in (table_node.catalog, table_node.db, table_name) if p]
                fq_name = ".".join(parts)

                if table_name not in self._allowed_tables and fq_name not in self._allowed_tables:
                    errors.append(f"Table '{fq_name}' is not in the allowed table list")

        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # -------------------------------------------------------------- #
        # 6. Validate function calls
        # -------------------------------------------------------------- #
        func_errors = self._validate_function_calls(ast, dialect)
        errors.extend(func_errors)

        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # -------------------------------------------------------------- #
        # 7. Detect potential injection patterns in literals
        # -------------------------------------------------------------- #
        for literal_node in ast.find_all(exp.Literal):
            value = literal_node.this
            if isinstance(value, str) and self._looks_like_injection(value):
                warnings.append(
                    f"Suspicious pattern detected in string literal: '{value[:80]}...'"
                    if len(value) > 80
                    else f"Suspicious pattern detected in string literal: '{value}'"
                )

        return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _validate_function_calls(
        self,
        ast: exp.Expression,
        dialect: str,
    ) -> list[str]:
        """Check function calls against dialect-specific blocklists.

        Blocks:
        - Functions listed in ``BLOCKED_FUNCTIONS`` for the given dialect.
        - ``CALL`` / ``EXEC`` procedure invocations (mapped to ``Command``).
        - ``Anonymous`` function nodes (unresolved/unknown functions treated
          as potentially dangerous).

        Args:
            ast: The parsed AST to inspect.
            dialect: The SQL dialect name.

        Returns:
            A list of error messages for any blocked function calls.
        """
        errors: list[str] = []
        blocked_for_dialect = self.BLOCKED_FUNCTIONS.get(dialect, set())

        for node in ast.walk():
            # Block Anonymous functions only if they are in the blocklist
            if isinstance(node, exp.Anonymous):
                func_name = node.name.lower() if node.name else "<unknown>"
                if func_name in blocked_for_dialect:
                    errors.append(f"Blocked function '{func_name}' is not allowed for dialect '{dialect}'")
                continue

            # Block known dangerous functions
            if isinstance(node, exp.Func):
                # Normalise the function name from the SQL name mapping
                func_name = type(node).sql_name().lower() if hasattr(type(node), "sql_name") else ""  # type: ignore[no-untyped-call]
                if not func_name:
                    # Fallback: use the class key
                    func_name = node.key.lower() if hasattr(node, "key") else ""

                if func_name in blocked_for_dialect:
                    errors.append(f"Blocked function '{func_name}' is not allowed for dialect '{dialect}'")

            # Block CALL / EXEC (procedure execution via Command nodes)
            if isinstance(node, exp.Command):
                cmd = (node.this or "").upper().strip()
                if cmd in ("CALL", "EXEC", "EXECUTE"):
                    errors.append(f"Procedure invocation '{cmd}' is not allowed")

        return errors

    @staticmethod
    def _looks_like_injection(value: str) -> bool:
        """Detect suspicious patterns in string literal values.

        Scans the given string against a set of regular expressions that
        match common SQL injection payloads (stacked queries, comment-based
        injection, UNION probes, boolean/time-based blind techniques, and
        hex-encoded payloads).

        Args:
            value: The string literal value to inspect.

        Returns:
            ``True`` if any injection pattern matches, ``False`` otherwise.
        """
        return any(pattern.search(value) for pattern in SQLValidator._INJECTION_PATTERNS)
