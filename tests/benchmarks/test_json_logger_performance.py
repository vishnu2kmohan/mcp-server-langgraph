"""
Performance benchmarks for JSON logging.

These tests measure formatting performance and are NOT correctness tests.
Run with: pytest tests/benchmarks/ --benchmark-enable

See: tests/unit/observability/test_json_logger.py for correctness tests
"""

from __future__ import annotations

import gc
import json
import logging

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.benchmark,
    pytest.mark.xdist_group(name="json_logger_benchmarks"),
]


@pytest.fixture
def json_formatter():
    """Create a JSONFormatter instance for testing."""
    from mcp_server_langgraph.observability.json_logger import JSONFormatter

    return JSONFormatter()


@pytest.fixture
def log_record():
    """Create a sample log record for testing."""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message with %s",
        args=("args",),
        exc_info=None,
    )
    return record


@pytest.fixture
def tracer_provider():
    """Create a tracer provider for testing."""
    from opentelemetry.sdk.trace import TracerProvider

    return TracerProvider()


@pytest.mark.xdist_group("test_j_s_o_n_logger_performance")
class TestJSONLoggerPerformance:
    """Performance benchmarks for JSON logging."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_formatting_without_trace_measures_baseline_speed(self, json_formatter, log_record, benchmark):
        """Benchmark JSON formatting performance without active trace context."""

        def format_log():
            return json_formatter.format(log_record)

        result = benchmark(format_log)
        # Verify it's valid JSON
        json.loads(result)

    def test_formatting_with_trace_performance(self, json_formatter, log_record, tracer_provider, benchmark):
        """Benchmark JSON formatting with active trace."""
        tracer = tracer_provider.get_tracer(__name__)

        def format_with_trace():
            with tracer.start_as_current_span("test_span"):
                return json_formatter.format(log_record)

        result = benchmark(format_with_trace)
        log_data = json.loads(result)
        assert "trace_id" in log_data
