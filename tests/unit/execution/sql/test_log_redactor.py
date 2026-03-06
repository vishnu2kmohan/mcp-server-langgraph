"""
Unit tests for SQLLogRedactor and SQLExecutionLogger.

Tests SQL redaction patterns, parameter redaction for sensitive keys,
query fingerprinting, and structured log_query output.
"""

import gc
import logging
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.execution.sql.log_redactor import (
    SQLExecutionLogger,
    SQLLogRedactor,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# SQLLogRedactor.redact_sql() - password patterns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLLogRedactorPassword:
    """Verify password-related redaction patterns in SQL strings."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_redacts_single_quoted_password(self):
        sql = "SELECT * FROM users WHERE password = 'secret123'"
        result = SQLLogRedactor.redact_sql(sql)
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_redacts_double_quoted_password(self):
        sql = 'SELECT * FROM users WHERE password = "secret123"'
        result = SQLLogRedactor.redact_sql(sql)
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_redacts_password_case_insensitive(self):
        sql = "SELECT * FROM users WHERE PASSWORD = 'secret123'"
        result = SQLLogRedactor.redact_sql(sql)
        assert "secret123" not in result

    def test_redacts_password_with_spaces(self):
        sql = "SELECT * FROM users WHERE password  =  'my_pass'"
        result = SQLLogRedactor.redact_sql(sql)
        assert "my_pass" not in result


# ---------------------------------------------------------------------------
# SQLLogRedactor.redact_sql() - secret, api_key, token patterns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLLogRedactorSensitivePatterns:
    """Verify redaction of secret, api_key, and token patterns."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_redact_sql_removes_secret_values(self):
        sql = "INSERT INTO config (secret = 'mysecret')"
        result = SQLLogRedactor.redact_sql(sql)
        assert "mysecret" not in result
        assert "[REDACTED]" in result

    def test_redacts_api_key(self):
        sql = "SELECT * FROM config WHERE api_key = 'ak-12345'"
        result = SQLLogRedactor.redact_sql(sql)
        assert "ak-12345" not in result
        assert "[REDACTED]" in result

    def test_redact_sql_removes_token_values(self):
        sql = "SELECT * FROM sessions WHERE token = 'tok_abc123'"
        result = SQLLogRedactor.redact_sql(sql)
        assert "tok_abc123" not in result
        assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# SQLLogRedactor.redact_sql() - connection URI pattern
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLLogRedactorURIPattern:
    """Verify connection URI credential redaction."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_redacts_uri_credentials(self):
        sql = "CONNECT TO postgres://admin:s3cret@db.example.com:5432/mydb"
        result = SQLLogRedactor.redact_sql(sql)
        assert "admin" not in result
        assert "s3cret" not in result
        assert "[REDACTED]" in result
        assert "db.example.com" in result

    def test_redacts_uri_with_special_chars_in_password(self):
        sql = "CONNECT TO postgres://user:p@ss!w0rd@db.host.com/db"
        result = SQLLogRedactor.redact_sql(sql)
        assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# SQLLogRedactor.redact_sql() - no false positives
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLLogRedactorNoFalsePositives:
    """Verify that non-sensitive SQL is not modified."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_preserves_normal_select(self):
        sql = "SELECT id, name FROM users WHERE age > 18"
        result = SQLLogRedactor.redact_sql(sql)
        assert result == sql

    def test_preserves_normal_join(self):
        sql = "SELECT u.id FROM users u JOIN orders o ON u.id = o.user_id"
        result = SQLLogRedactor.redact_sql(sql)
        assert result == sql


# ---------------------------------------------------------------------------
# SQLLogRedactor.redact_params()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLLogRedactorParams:
    """Verify parameter redaction based on key sensitivity."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_redacts_password_param(self):
        result = SQLLogRedactor.redact_params({"password": "secret123"})
        assert result["password"] == "[REDACTED]"

    def test_redacts_secret_param(self):
        result = SQLLogRedactor.redact_params({"secret": "my-secret"})
        assert result["secret"] == "[REDACTED]"

    def test_redacts_api_key_param(self):
        result = SQLLogRedactor.redact_params({"api_key": "ak-12345"})
        assert result["api_key"] == "[REDACTED]"

    def test_redacts_token_param(self):
        result = SQLLogRedactor.redact_params({"token": "tok_abc"})
        assert result["token"] == "[REDACTED]"

    def test_redacts_auth_param(self):
        result = SQLLogRedactor.redact_params({"auth": "bearer xyz"})
        assert result["auth"] == "[REDACTED]"

    def test_redacts_credential_param(self):
        result = SQLLogRedactor.redact_params({"credential": "cred-123"})
        assert result["credential"] == "[REDACTED]"

    def test_redacts_private_key_param(self):
        result = SQLLogRedactor.redact_params({"private_key": "-----BEGIN RSA-----"})
        assert result["private_key"] == "[REDACTED]"

    def test_redacts_ssn_param(self):
        result = SQLLogRedactor.redact_params({"ssn": "123-45-6789"})
        assert result["ssn"] == "[REDACTED]"

    def test_redacts_credit_card_param(self):
        result = SQLLogRedactor.redact_params({"credit_card": "4111111111111111"})
        assert result["credit_card"] == "[REDACTED]"

    def test_redacts_case_insensitive_key(self):
        result = SQLLogRedactor.redact_params({"Password": "secret123"})
        assert result["Password"] == "[REDACTED]"

    def test_redacts_key_containing_sensitive_substring(self):
        result = SQLLogRedactor.redact_params({"user_password_hash": "abc123"})
        assert result["user_password_hash"] == "[REDACTED]"

    def test_preserves_normal_param(self):
        result = SQLLogRedactor.redact_params({"name": "alice"})
        assert result["name"] == "alice"

    def test_preserves_numeric_param_as_string(self):
        result = SQLLogRedactor.redact_params({"age": 25})
        assert result["age"] == "25"

    def test_truncates_long_string_param(self):
        long_value = "x" * 200
        result = SQLLogRedactor.redact_params({"description": long_value})
        assert "[TRUNCATED]" in result["description"]
        assert len(result["description"]) < 200

    def test_long_param_shows_first_20_chars(self):
        long_value = "abcdefghijklmnopqrstuvwxyz" * 10
        result = SQLLogRedactor.redact_params({"bio": long_value})
        assert result["bio"].startswith(long_value[:20])

    def test_empty_params_returns_empty_dict(self):
        result = SQLLogRedactor.redact_params({})
        assert result == {}

    def test_mixed_sensitive_and_normal_params(self):
        result = SQLLogRedactor.redact_params(
            {
                "name": "alice",
                "password": "secret",
                "age": 30,
            }
        )
        assert result["name"] == "alice"
        assert result["password"] == "[REDACTED]"
        assert result["age"] == "30"


# ---------------------------------------------------------------------------
# SQLExecutionLogger._fingerprint()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLExecutionLoggerFingerprint:
    """Verify query fingerprinting replaces literals with placeholders."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def exec_logger(self):
        return SQLExecutionLogger()

    def test_fingerprint_replaces_string_literal(self, exec_logger):
        result = exec_logger._fingerprint("SELECT * FROM users WHERE name = 'alice'")
        assert "alice" not in result
        assert "?" in result

    def test_fingerprint_replaces_numeric_literal(self, exec_logger):
        result = exec_logger._fingerprint("SELECT * FROM users WHERE id = 42")
        assert "42" not in result
        assert "?" in result

    def test_fingerprint_preserves_table_names(self, exec_logger):
        result = exec_logger._fingerprint("SELECT * FROM users WHERE id = 1")
        assert "users" in result

    def test_fingerprint_preserves_column_names(self, exec_logger):
        result = exec_logger._fingerprint("SELECT id, name FROM users WHERE id = 1")
        assert "id" in result
        assert "name" in result

    def test_fingerprint_truncates_long_sql(self, exec_logger):
        long_sql = "SELECT " + ", ".join(f"col_{i}" for i in range(500)) + " FROM big_table WHERE id = 1"
        result = exec_logger._fingerprint(long_sql)
        assert len(result) <= 200

    def test_fingerprint_unparseable_returns_marker(self, exec_logger):
        result = exec_logger._fingerprint("NOT VALID SQL @@@ !!!")
        assert result == "[UNPARSEABLE]"

    def test_fingerprint_replaces_multiple_literals(self, exec_logger):
        result = exec_logger._fingerprint("SELECT * FROM users WHERE id = 1 AND name = 'bob'")
        assert "1" not in result.replace("?", "")  # '1' shouldn't appear except as ?
        assert "bob" not in result


# ---------------------------------------------------------------------------
# SQLExecutionLogger.log_query()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLExecutionLoggerLogQuery:
    """Verify structured log_query output with mock logger."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def mock_logger(self):
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def exec_logger(self, mock_logger):
        return SQLExecutionLogger(base_logger=mock_logger)

    def test_log_query_basic_message(self, exec_logger, mock_logger):
        exec_logger.log_query(logging.INFO, "Query executed")
        mock_logger.log.assert_called_once()
        args = mock_logger.log.call_args
        assert args[0][0] == logging.INFO
        assert args[0][1] == "Query executed"

    def test_log_query_includes_tenant_id(self, exec_logger, mock_logger):
        exec_logger.log_query(logging.INFO, "Query executed", tenant_id="tenant-abc")
        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["tenant_id"] == "tenant-abc"

    def test_log_query_includes_duration_ms(self, exec_logger, mock_logger):
        exec_logger.log_query(logging.INFO, "Query executed", duration_ms=123.45)
        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["duration_ms"] == 123.45

    def test_log_query_includes_sql_fingerprint(self, exec_logger, mock_logger):
        exec_logger.log_query(
            logging.INFO,
            "Query executed",
            sql="SELECT * FROM users WHERE id = 1",
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert "sql_fingerprint" in extra
        assert "1" not in extra["sql_fingerprint"].replace("?", "")

    def test_log_query_includes_param_names(self, exec_logger, mock_logger):
        exec_logger.log_query(
            logging.INFO,
            "Query executed",
            params={"id": 1, "name": "alice"},
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert "param_names" in extra
        assert set(extra["param_names"]) == {"id", "name"}

    def test_log_query_includes_redacted_params_at_debug(self, exec_logger, mock_logger):
        mock_logger.isEnabledFor.return_value = True
        exec_logger.log_query(
            logging.DEBUG,
            "Query executed",
            params={"id": 1, "password": "secret"},
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert "params_redacted" in extra
        assert extra["params_redacted"]["password"] == "[REDACTED]"
        assert extra["params_redacted"]["id"] == "1"

    def test_log_query_excludes_redacted_params_above_debug(self, exec_logger, mock_logger):
        mock_logger.isEnabledFor.return_value = False
        exec_logger.log_query(
            logging.INFO,
            "Query executed",
            params={"id": 1, "password": "secret"},
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert "params_redacted" not in extra

    def test_log_query_includes_error_info(self, exec_logger, mock_logger):
        error = ValueError("something went wrong with a very long message")
        exec_logger.log_query(
            logging.ERROR,
            "Query failed",
            error=error,
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["error_type"] == "ValueError"
        assert "something went wrong" in extra["error_safe"]

    def test_log_query_error_safe_truncated(self, exec_logger, mock_logger):
        error = ValueError("x" * 500)
        exec_logger.log_query(
            logging.ERROR,
            "Query failed",
            error=error,
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert len(extra["error_safe"]) <= 200

    def test_log_query_includes_extra_fields(self, exec_logger, mock_logger):
        exec_logger.log_query(
            logging.INFO,
            "Query executed",
            extra={"rows_affected": 42, "cache_hit": True},
        )
        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["rows_affected"] == 42
        assert extra["cache_hit"] is True

    def test_log_query_null_optional_fields(self, exec_logger, mock_logger):
        exec_logger.log_query(logging.INFO, "Query executed")
        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["tenant_id"] is None
        assert extra["duration_ms"] is None


# ---------------------------------------------------------------------------
# SQLExecutionLogger constructor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLExecutionLoggerConstructor:
    """Verify default and custom logger initialization."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_default_logger_name(self):
        exec_logger = SQLExecutionLogger()
        assert exec_logger._logger.name == "sql.executor"

    def test_execution_logger_with_custom_base_logger(self):
        custom = logging.getLogger("custom.sql")
        exec_logger = SQLExecutionLogger(base_logger=custom)
        assert exec_logger._logger is custom
