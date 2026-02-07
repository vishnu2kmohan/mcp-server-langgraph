"""SQL log redaction and structured logging."""

import logging
import re
from typing import Any

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)


class SQLLogRedactor:
    """Redact sensitive data from SQL queries and parameters before logging."""

    REDACT_PATTERNS: list[tuple[str, str]] = [
        (r"password\s*=\s*'[^']*'", "password='[REDACTED]'"),
        (r"password\s*=\s*\"[^\"]*\"", 'password="[REDACTED]"'),
        (r"secret\s*=\s*'[^']*'", "secret='[REDACTED]'"),
        (r"api_key\s*=\s*'[^']*'", "api_key='[REDACTED]'"),
        (r"token\s*=\s*'[^']*'", "token='[REDACTED]'"),
        (r"://[^:]+:[^@]+@", "://[REDACTED]:[REDACTED]@"),
    ]

    SENSITIVE_PARAMS: frozenset[str] = frozenset(
        {
            "password",
            "secret",
            "api_key",
            "token",
            "auth",
            "credential",
            "private_key",
            "ssn",
            "credit_card",
        }
    )

    @classmethod
    def redact_sql(cls, sql: str) -> str:
        result = sql
        for pattern, replacement in cls.REDACT_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    @classmethod
    def redact_params(cls, params: dict[str, Any]) -> dict[str, str]:
        if not params:
            return {}
        redacted: dict[str, str] = {}
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_PARAMS):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                redacted[key] = f"{value[:20]}...[TRUNCATED]"
            else:
                redacted[key] = str(value)
        return redacted


class SQLExecutionLogger:
    """Logger that automatically redacts sensitive SQL/params."""

    def __init__(self, base_logger: logging.Logger | None = None):
        self._logger = base_logger or logging.getLogger("sql.executor")

    def log_query(
        self,
        level: int,
        message: str,
        *,
        sql: str | None = None,
        params: dict | None = None,
        tenant_id: str | None = None,
        duration_ms: float | None = None,
        error: Exception | None = None,
        extra: dict | None = None,
    ) -> None:
        log_extra: dict[str, Any] = {
            "tenant_id": tenant_id,
            "duration_ms": duration_ms,
        }
        if extra:
            log_extra.update(extra)

        if sql:
            log_extra["sql_fingerprint"] = self._fingerprint(sql)
            log_extra["sql_redacted"] = SQLLogRedactor.redact_sql(sql)

        if params:
            log_extra["param_names"] = list(params.keys())
            if self._logger.isEnabledFor(logging.DEBUG):
                log_extra["params_redacted"] = SQLLogRedactor.redact_params(params)

        if error:
            log_extra["error_type"] = type(error).__name__
            log_extra["error_safe"] = str(error)[:200]

        self._logger.log(level, message, extra=log_extra)

    @staticmethod
    def _fingerprint(sql: str) -> str:
        try:
            ast = sqlglot.parse_one(sql)
            for literal in ast.find_all(exp.Literal):
                literal.replace(exp.Placeholder(this="?"))
            return ast.sql()[:200]
        except Exception:
            return "[UNPARSEABLE]"
