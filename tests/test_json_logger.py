"""
Unit tests for JSON logger with OpenTelemetry trace injection

Tests the CustomJSONFormatter class and structured logging functionality.
"""

import gc
import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mcp_server_langgraph.observability.json_logger import CustomJSONFormatter, log_with_context, setup_json_logging


@pytest.fixture
def tracer_provider(monkeypatch):
    """Get the current tracer provider for testing"""
    # Temporarily enable OTEL SDK for these trace injection tests
    # This ensures we get real trace IDs even when OTEL_SDK_DISABLED=true is set globally
    import os

    if os.getenv("OTEL_SDK_DISABLED"):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

    # Create a real tracer provider for these tests
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield provider


@pytest.fixture
def json_formatter():
    """Create a JSON formatter instance for testing"""
    return CustomJSONFormatter(
        service_name="test-service",
        include_hostname=False,  # Disable hostname for consistent tests
        indent=None,  # Compact JSON
    )


@pytest.fixture
def json_formatter_pretty():
    """Create a JSON formatter with pretty printing"""
    return CustomJSONFormatter(
        service_name="test-service",
        include_hostname=False,
        indent=2,  # Pretty-print
    )


@pytest.fixture
def log_record():
    """Create a test log record"""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="/app/test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
        func="test_function",  # Set function name
    )
    record.process = 1234
    record.processName = "TestProcess"
    record.thread = 5678
    record.threadName = "TestThread"
    return record


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcustomjsonformatter")
class TestCustomJSONFormatter:
    """Tests for CustomJSONFormatter class"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_basic_formatting(self, json_formatter, log_record):
        """Test basic JSON formatting without trace context"""
        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        # Verify required fields
        assert "timestamp" in log_data
        assert "level" in log_data
        assert "logger" in log_data
        assert "service" in log_data
        assert "message" in log_data

        # Verify values
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["service"] == "test-service"
        assert log_data["message"] == "Test message"

    def test_timestamp_format(self, json_formatter, log_record):
        """Test ISO 8601 timestamp with milliseconds"""
        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        # Verify timestamp format: YYYY-MM-DDTHH:MM:SS.sssZ
        timestamp = log_data["timestamp"]
        assert timestamp.endswith("Z")
        assert "T" in timestamp
        assert len(timestamp.split(".")) == 2  # Has milliseconds

        # Validate it's a valid ISO 8601 timestamp
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_trace_context_injection(self, json_formatter, log_record, tracer_provider):
        """Test OpenTelemetry trace context injection"""
        tracer = tracer_provider.get_tracer(__name__)

        with tracer.start_as_current_span("test_span") as span:  # noqa: F841
            formatted = json_formatter.format(log_record)
            log_data = json.loads(formatted)

            # Verify trace fields are present
            assert "trace_id" in log_data
            assert "span_id" in log_data
            assert "trace_flags" in log_data

            # Verify trace ID format (32 hex characters)
            assert len(log_data["trace_id"]) == 32
            assert all(c in "0123456789abcdef" for c in log_data["trace_id"])

            # Verify span ID format (16 hex characters)
            assert len(log_data["span_id"]) == 16
            assert all(c in "0123456789abcdef" for c in log_data["span_id"])

    def test_process_and_thread_info(self, json_formatter, log_record):
        """Test process and thread information"""
        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        assert "process" in log_data
        assert log_data["process"]["pid"] == 1234
        assert log_data["process"]["name"] == "TestProcess"

        assert "thread" in log_data
        assert log_data["thread"]["id"] == 5678
        assert log_data["thread"]["name"] == "TestThread"

    def test_location_info(self, json_formatter, log_record):
        """Test file location information"""
        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        assert "location" in log_data
        assert log_data["location"]["file"] == "/app/test.py"
        assert log_data["location"]["line"] == 42
        assert log_data["location"]["function"] is not None

    def test_custom_extra_fields(self, json_formatter, log_record):
        """Test custom extra fields via logging.extra"""
        # Add custom fields
        log_record.user_id = "alice"
        log_record.ip_address = "192.168.1.100"
        log_record.request_id = "req-123"

        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        # Verify custom fields are included
        assert log_data["user_id"] == "alice"
        assert log_data["ip_address"] == "192.168.1.100"
        assert log_data["request_id"] == "req-123"

    def test_exception_handling(self, json_formatter):
        """Test exception stack trace capture"""
        import sys

        try:
            raise ValueError("Test error")
        except ValueError:
            # Capture the actual exception info tuple
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/app/test.py",
                lineno=42,
                msg="An error occurred",
                args=(),
                exc_info=exc_info,  # Pass the actual exception tuple
            )

        formatted = json_formatter.format(record)
        log_data = json.loads(formatted)

        # Verify exception fields
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test error"
        assert "stacktrace" in log_data["exception"]
        assert "Traceback" in log_data["exception"]["stacktrace"]

    def test_pretty_print_formatting(self, json_formatter_pretty, log_record):
        """Test pretty-print JSON formatting"""
        formatted = json_formatter_pretty.format(log_record)

        # Verify it's valid JSON
        log_data = json.loads(formatted)
        assert log_data["message"] == "Test message"

        # Verify it contains newlines (pretty-printed)
        assert "\n" in formatted
        assert "  " in formatted  # Contains indentation

    def test_compact_formatting(self, json_formatter, log_record):
        """Test compact JSON formatting (no indentation)"""
        formatted = json_formatter.format(log_record)

        # Verify it's valid JSON
        log_data = json.loads(formatted)
        assert log_data["message"] == "Test message"

        # Verify it's compact (single line, no extra whitespace)
        assert "\n" not in formatted
        assert "  " not in formatted  # No indentation

    def test_hostname_inclusion(self):
        """Test hostname field inclusion"""
        formatter_with_hostname = CustomJSONFormatter(
            service_name="test-service",
            include_hostname=True,
        )

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter_with_hostname.format(record)
        log_data = json.loads(formatted)

        assert "hostname" in log_data
        assert log_data["hostname"] != "unknown"

    def test_no_trace_context(self, json_formatter, log_record):
        """Test logging without active trace context"""
        # Ensure no active span
        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        # Trace fields should not be present (or be None/empty)
        assert "trace_id" not in log_data or log_data.get("trace_id") is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsetupjsonlogging")
class TestSetupJSONLogging:
    """Tests for setup_json_logging helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_setup_json_logging(self):
        """Test logger setup with JSON formatting"""
        logger = logging.getLogger("test_setup_logger")
        setup_json_logging(logger, level=logging.DEBUG, service_name="test-service")

        # Verify logger is configured
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

        # Verify handler has JSON formatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, CustomJSONFormatter)

    def test_logger_output(self):
        """Test actual logger output is valid JSON"""
        logger = logging.getLogger("test_output_logger")
        setup_json_logging(logger, service_name="test-service", indent=None)

        # Capture log output
        with patch.object(logger.handlers[0].stream, "write") as mock_write:
            logger.info("Test log message")

            # Get the written output
            written_output = "".join(call.args[0] for call in mock_write.call_args_list)

            # Verify it contains valid JSON
            # Extract JSON from output (may have newline)
            json_str = written_output.strip()
            log_data = json.loads(json_str)

            assert log_data["message"] == "Test log message"
            assert log_data["level"] == "INFO"


@pytest.mark.unit
@pytest.mark.xdist_group(name="testlogwithcontext")
class TestLogWithContext:
    """Tests for log_with_context helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_log_with_context(self):
        """Test logging with custom context fields"""
        logger = logging.getLogger("test_context_logger")
        setup_json_logging(logger, service_name="test-service")

        with patch.object(logger, "log") as mock_log:
            log_with_context(
                logger,
                logging.INFO,
                "User action",
                user_id="alice",
                action="login",
                ip="192.168.1.100",
            )

            # Verify log was called with extra context
            mock_log.assert_called_once()
            call_args = mock_log.call_args

            assert call_args[0][0] == logging.INFO
            assert call_args[0][1] == "User action"
            assert call_args[1]["extra"]["user_id"] == "alice"
            assert call_args[1]["extra"]["action"] == "login"
            assert call_args[1]["extra"]["ip"] == "192.168.1.100"


@pytest.mark.unit
@pytest.mark.xdist_group(name="testedgecases")
class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_empty_message(self, json_formatter):
        """Test handling of empty log message"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="",
            args=(),
            exc_info=None,
        )

        formatted = json_formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["message"] == ""
        assert "level" in log_data

    def test_unicode_message(self, json_formatter):
        """Test handling of Unicode characters"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Hello 世界 🌍",
            args=(),
            exc_info=None,
        )

        formatted = json_formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["message"] == "Hello 世界 🌍"

    def test_large_extra_data(self, json_formatter, log_record):
        """Test handling of large custom data"""
        log_record.large_data = {"key": "value" * 1000}

        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        assert "large_data" in log_data
        assert len(log_data["large_data"]["key"]) == 5000  # "value" * 1000

    def test_special_characters_in_fields(self, json_formatter, log_record):
        """Test handling of special characters in field values"""
        log_record.special_field = 'Test "quotes" and \\backslashes\\ and \nnewlines'

        formatted = json_formatter.format(log_record)
        log_data = json.loads(formatted)

        # JSON should properly escape special characters
        assert '"' in log_data["special_field"]
        assert "\\" in log_data["special_field"]


@pytest.mark.benchmark
@pytest.mark.unit
@pytest.mark.xdist_group(name="testperformance")
class TestPerformance:
    """Performance tests for JSON logging"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_formatting_performance(self, json_formatter, log_record, benchmark):
        """Benchmark JSON formatting performance"""

        def format_log():
            return json_formatter.format(log_record)

        result = benchmark(format_log)
        # Verify it's valid JSON
        json.loads(result)

    def test_formatting_with_trace_performance(self, json_formatter, log_record, tracer_provider, benchmark):
        """Benchmark JSON formatting with active trace"""
        tracer = tracer_provider.get_tracer(__name__)

        def format_with_trace():
            with tracer.start_as_current_span("test_span"):
                return json_formatter.format(log_record)

        result = benchmark(format_with_trace)
        log_data = json.loads(result)
        assert "trace_id" in log_data
