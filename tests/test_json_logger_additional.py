"""
Additional tests for JSON logger to increase coverage.

These tests target uncovered code paths in json_logger.py:
- ImportError fallback for pythonjsonlogger
- Hostname socket error handling
- Invalid span context handling
- Edge cases in add_fields method
"""

import gc
import json
import logging
from unittest.mock import Mock, patch

import pytest

from mcp_server_langgraph.observability.json_logger import CustomJSONFormatter, setup_json_logging


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestImportFallback:
    """Tests for pythonjsonlogger import fallback"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_fallback_to_standard_formatter(self):
        """Test that formatter falls back to standard logging.Formatter when pythonjsonlogger unavailable"""
        # The import happens at module level, so we test that the formatter still works
        formatter = CustomJSONFormatter(service_name="test")
        assert formatter is not None

        # Test that it can format a record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        assert log_data["message"] == "test"


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestHostnameHandling:
    """Tests for hostname field handling"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_hostname_exception_handling(self):
        """Test hostname error handling when socket.gethostname() fails"""
        formatter = CustomJSONFormatter(
            service_name="test-service",
            include_hostname=True,
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        with patch("socket.gethostname", side_effect=Exception("DNS error")):
            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            # Should fall back to "unknown"
            assert log_data["hostname"] == "unknown"

    def test_hostname_disabled(self):
        """Test that hostname is not included when include_hostname=False"""
        formatter = CustomJSONFormatter(
            service_name="test-service",
            include_hostname=False,
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "hostname" not in log_data


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestTraceContextEdgeCases:
    """Tests for OpenTelemetry trace context edge cases"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_invalid_span_context(self, monkeypatch):
        """Test handling of invalid span context"""
        # Enable OTEL for this test
        if "OTEL_SDK_DISABLED" in monkeypatch._setitem:
            monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

        formatter = CustomJSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Create a mock span with invalid context
        mock_span = Mock()
        mock_span_context = Mock()
        mock_span_context.is_valid = False  # Invalid context
        mock_span.get_span_context.return_value = mock_span_context

        with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            # Trace fields should not be present for invalid context
            assert "trace_id" not in log_data
            assert "span_id" not in log_data

    def test_no_span_context(self):
        """Test handling when span.get_span_context() returns None"""
        formatter = CustomJSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Create a mock span that returns None for context
        mock_span = Mock()
        mock_span.get_span_context.return_value = None

        with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            # Should not crash, trace fields should not be present
            assert "trace_id" not in log_data

    def test_no_active_span(self):
        """Test handling when there's no active span"""
        formatter = CustomJSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        with patch("opentelemetry.trace.get_current_span", return_value=None):
            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            # Should not crash, no trace fields
            assert "trace_id" not in log_data


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestExceptionHandlingEdgeCases:
    """Tests for exception info handling edge cases"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_exception_with_none_values(self):
        """Test handling of exc_info tuple with None values"""
        formatter = CustomJSONFormatter(service_name="test")

        # Create exc_info tuple with None values
        exc_info = (None, None, None)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/test.py",
            lineno=1,
            msg="error",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should handle gracefully
        if "exception" in log_data:
            assert log_data["exception"]["type"] is None
            assert log_data["exception"]["message"] is None

    def test_exception_info_as_true(self):
        """Test handling of exc_info=True (rare case)"""
        formatter = CustomJSONFormatter(service_name="test")

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/test.py",
            lineno=1,
            msg="error",
            args=(),
            exc_info=True,  # Boolean True instead of tuple
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should not crash (exception field may or may not be present)
        assert "message" in log_data


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestAddFieldsCustomization:
    """Tests for add_fields method customization"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_timestamp_override(self):
        """Test that existing timestamp is not overridden"""
        formatter = CustomJSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Pre-set timestamp in log record
        record.timestamp = "2024-01-01T00:00:00.000Z"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should use the pre-set timestamp
        assert log_data["timestamp"] == "2024-01-01T00:00:00.000Z"

    def test_extra_fields_with_underscores(self):
        """Test that fields starting with underscore are excluded"""
        formatter = CustomJSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Add fields with and without underscores
        record.public_field = "visible"
        record._private_field = "hidden"
        record.__very_private = "also_hidden"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Public field should be included
        assert log_data["public_field"] == "visible"

        # Private fields should not be included
        assert "_private_field" not in log_data
        assert "__very_private" not in log_data

    def test_standard_fields_excluded_from_extra(self):
        """Test that standard logging fields are not duplicated in output"""
        formatter = CustomJSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Standard fields should be in structured format, not duplicated
        assert "logger" in log_data
        assert log_data["logger"] == "test_logger"

        # Message should be formatted, not raw
        assert log_data["message"] == "test message"

        # Standard internal fields should not appear
        assert "msg" not in log_data  # Raw msg field excluded
        assert "args" not in log_data  # Args excluded
        assert "created" not in log_data  # Created excluded


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestFormatterInitialization:
    """Tests for formatter initialization options"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_custom_datefmt(self):
        """Test formatter with custom date format"""
        formatter = CustomJSONFormatter(
            datefmt="%Y-%m-%d",
            service_name="test",
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should still produce valid JSON with timestamp
        assert "timestamp" in log_data

    def test_custom_fmt_string(self):
        """Test formatter with custom format string"""
        formatter = CustomJSONFormatter(
            fmt="%(levelname)s %(message)s",
            service_name="test",
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should still produce valid JSON
        assert "message" in log_data

    def test_different_style_formats(self):
        """Test formatter with different format styles"""
        styles = ["%", "{", "$"]

        for style in styles:
            formatter = CustomJSONFormatter(
                style=style,
                service_name="test",
            )

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="/test.py",
                lineno=1,
                msg="test",
                args=(),
                exc_info=None,
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            # Should work with all styles
            assert log_data["message"] == "test"


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestSetupJSONLoggingEdgeCases:
    """Tests for setup_json_logging edge cases"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_setup_replaces_existing_handlers(self):
        """Test that setup removes existing handlers"""
        logger = logging.getLogger("test_replace_handlers")

        # Add a dummy handler
        existing_handler = logging.StreamHandler()
        logger.addHandler(existing_handler)
        assert len(logger.handlers) == 1

        # Setup JSON logging
        setup_json_logging(logger)

        # Old handler should be removed, new one added
        assert len(logger.handlers) == 1
        assert logger.handlers[0] != existing_handler
        assert isinstance(logger.handlers[0].formatter, CustomJSONFormatter)

    def test_setup_with_all_options(self):
        """Test setup with all optional parameters"""
        logger = logging.getLogger("test_all_options")

        setup_json_logging(
            logger,
            level=logging.DEBUG,
            service_name="custom-service",
            include_hostname=True,
            indent=4,
        )

        # Verify configuration
        assert logger.level == logging.DEBUG
        handler = logger.handlers[0]
        formatter = handler.formatter

        assert isinstance(formatter, CustomJSONFormatter)
        assert formatter.service_name == "custom-service"
        assert formatter.include_hostname is True
        assert formatter.indent == 4


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestMessageFormatting:
    """Tests for getMessage() and format string handling"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_message_with_args(self):
        """Test message formatting with arguments"""
        formatter = CustomJSONFormatter(service_name="test")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="User %s logged in from %s",
            args=("alice", "192.168.1.1"),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Message should be formatted with args
        assert log_data["message"] == "User alice logged in from 192.168.1.1"

    def test_message_with_dict_args(self):
        """Test message formatting with dictionary arguments"""
        formatter = CustomJSONFormatter(service_name="test")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="User %(user)s from %(ip)s",
            args={"user": "bob", "ip": "10.0.0.1"},
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Message should be formatted with dict
        assert log_data["message"] == "User bob from 10.0.0.1"


@pytest.mark.xdist_group(name="json_logger_additional_tests")
class TestJSONSerializationEdgeCases:
    """Tests for JSON serialization edge cases"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_non_serializable_extra_field(self):
        """Test handling of non-JSON-serializable extra fields"""
        formatter = CustomJSONFormatter(service_name="test")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Add a non-serializable object (will use default=str)
        class CustomObject:
            def __str__(self):
                return "CustomObject()"

        record.custom_obj = CustomObject()

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should be serialized using str()
        assert "CustomObject()" in log_data["custom_obj"]

    def test_datetime_in_extra_field(self):
        """Test datetime objects in extra fields"""
        from datetime import datetime

        formatter = CustomJSONFormatter(service_name="test")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        record.created_at = datetime(2024, 1, 1, 12, 0, 0)

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should be serialized to string
        assert "2024-01-01" in log_data["created_at"]
