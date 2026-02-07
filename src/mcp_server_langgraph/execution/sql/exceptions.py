"""SQL execution exception hierarchy.

Extends MCPServerException for consistent error handling, metrics,
and HTTP status code mapping.
"""

from mcp_server_langgraph.core.exceptions import (
    ErrorCategory,
    MCPServerException,
    RetryPolicy,
)


class SQLExecutionError(MCPServerException):
    """Base for SQL execution errors."""

    default_message = "SQL execution error"
    default_error_code = "sql.execution_error"
    default_status_code = 500
    default_category = ErrorCategory.EXTERNAL_ERROR
    default_retry_policy = RetryPolicy.CONDITIONAL


class SQLValidationError(SQLExecutionError):
    """SQL validation error (blocked statement, policy violation)."""

    default_message = "SQL validation error"
    default_error_code = "sql.validation_error"
    default_status_code = 400
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


class SQLParseError(SQLExecutionError):
    """SQL syntax or validation error."""

    default_message = "SQL parse or validation error"
    default_error_code = "sql.parse_error"
    default_status_code = 400
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


class SQLSecurityError(SQLExecutionError):
    """SQL security violation (blocked operation, injection attempt)."""

    default_message = "SQL security violation"
    default_error_code = "sql.security_error"
    default_status_code = 403
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


class SQLConnectionError(SQLExecutionError):
    """Database connection failure."""

    default_message = "Database connection failed"
    default_error_code = "sql.connection_error"
    default_status_code = 503
    default_category = ErrorCategory.EXTERNAL_ERROR
    default_retry_policy = RetryPolicy.ALWAYS


class SQLTimeoutError(SQLExecutionError):
    """Query execution timeout."""

    default_message = "Query execution timed out"
    default_error_code = "sql.timeout"
    default_status_code = 504
    default_category = ErrorCategory.EXTERNAL_ERROR
    default_retry_policy = RetryPolicy.CONDITIONAL


class SQLTranspileError(SQLExecutionError):
    """SQL dialect transpilation error."""

    default_message = "SQL transpilation failed"
    default_error_code = "sql.transpile_error"
    default_status_code = 400
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


class EgressValidationError(SQLExecutionError):
    """Network egress validation failure (SSRF protection)."""

    default_message = "Connection target blocked by security policy"
    default_error_code = "sql.egress_blocked"
    default_status_code = 400
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


class SQLPolicyError(SQLExecutionError):
    """Data access policy violation."""

    default_message = "Data access policy violation"
    default_error_code = "sql.policy_error"
    default_status_code = 403
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


def sanitize_connection_error(exc: Exception) -> str:
    """Map exceptions to safe user-facing messages.

    SECURITY: Never expose raw exception details to the client.
    Internal errors, stack traces, and connection strings must never leak.
    """
    if isinstance(exc, EgressValidationError):
        return "Connection target blocked by security policy"

    error_map = {
        "connection refused": "Unable to connect - check host and port",
        "authentication failed": "Authentication failed - check credentials",
        "timeout": "Connection timeout - server may be unreachable",
        "ssl": "SSL/TLS error - check security settings",
        "name resolution": "Host not found - check hostname",
        "dns": "DNS resolution failed - check hostname",
    }
    error_str = str(exc).lower()
    for pattern, message in error_map.items():
        if pattern in error_str:
            return message
    return "Connection failed - check configuration"
