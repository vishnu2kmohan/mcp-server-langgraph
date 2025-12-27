"""
Tests for OTLP protocol detection in telemetry module.

This test follows TDD principles:
- Written FIRST to define expected behavior for OTLP protocol detection
- Fails initially (RED phase) because telemetry.py always uses gRPC when available
- Passes after adding port-based protocol detection (GREEN phase)

The issue:
- docker-compose.test.yml sets OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy-test:4318
- Port 4318 is for HTTP/protobuf protocol
- Port 4317 is for gRPC protocol
- telemetry.py was using gRPC exporter regardless of port, causing:
  "Failed to export metrics to alloy-test:4318, error code: StatusCode.UNAVAILABLE"

OpenTelemetry Spec Compliance (2025):
- Default protocol SHOULD be http/protobuf per OTel spec
- Port 4317 = gRPC, Port 4318 = HTTP
- Compression SHOULD use gzip for HTTP payloads
- Retry SHOULD use exponential backoff with jitter

See: ADR-0026, Grafana LGTM stack integration
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="telemetry_protocol_tests")
class TestOTLPProtocolDetection:
    """Test OTLP protocol detection based on endpoint port."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_http_protocol_from_port_4318(self) -> None:
        """
        Test that port 4318 in endpoint is detected as HTTP protocol.

        GIVEN: An endpoint URL with port 4318
        WHEN: Protocol detection function is called
        THEN: HTTP protocol should be detected

        Port conventions:
        - 4317 = gRPC (OTLP/gRPC)
        - 4318 = HTTP (OTLP/HTTP with protobuf or JSON)
        """
        from mcp_server_langgraph.observability.telemetry import detect_otlp_protocol

        result = detect_otlp_protocol("http://alloy-test:4318")
        assert result == "http", f"Expected 'http' protocol for port 4318, got: {result}"

    def test_detect_http_protocol_from_port_4318_with_path(self) -> None:
        """
        Test that port 4318 is detected even with path suffix.

        GIVEN: An endpoint URL with port 4318 and a path
        WHEN: Protocol detection function is called
        THEN: HTTP protocol should be detected
        """
        from mcp_server_langgraph.observability.telemetry import detect_otlp_protocol

        result = detect_otlp_protocol("http://alloy-test:4318/v1/metrics")
        assert result == "http", f"Expected 'http' protocol for port 4318, got: {result}"

    def test_detect_grpc_protocol_from_port_4317(self) -> None:
        """
        Test that port 4317 in endpoint is detected as gRPC protocol.

        GIVEN: An endpoint URL with port 4317
        WHEN: Protocol detection function is called
        THEN: gRPC protocol should be detected
        """
        from mcp_server_langgraph.observability.telemetry import detect_otlp_protocol

        result = detect_otlp_protocol("http://collector:4317")
        assert result == "grpc", f"Expected 'grpc' protocol for port 4317, got: {result}"

    def test_detect_grpc_protocol_from_standard_grpc_endpoint(self) -> None:
        """
        Test that endpoints without http:// prefix are treated as gRPC.

        GIVEN: An endpoint URL without http:// prefix (gRPC convention)
        WHEN: Protocol detection function is called
        THEN: gRPC protocol should be detected
        """
        from mcp_server_langgraph.observability.telemetry import detect_otlp_protocol

        result = detect_otlp_protocol("collector:4317")
        assert result == "grpc", f"Expected 'grpc' protocol for gRPC endpoint, got: {result}"

    def test_detect_http_as_default_per_otel_spec(self) -> None:
        """
        Test that HTTP/protobuf is the default protocol per OpenTelemetry spec.

        Per OpenTelemetry Protocol Exporter specification:
        "The default protocol SHOULD be http/protobuf, unless there are
        strong reasons for SDKs to select grpc as the default."

        GIVEN: An endpoint URL with non-standard port (no explicit protocol hint)
        WHEN: Protocol detection function is called
        THEN: HTTP protocol should be used as default per OTel spec
        """
        from mcp_server_langgraph.observability.telemetry import detect_otlp_protocol

        result = detect_otlp_protocol("http://collector:9999")
        assert result == "http", f"Expected 'http' as default protocol per OTel spec, got: {result}"

    def test_detect_http_for_localhost_default(self) -> None:
        """
        Test that default localhost endpoint uses HTTP per OTel spec.

        The default OTLP_ENDPOINT should use port 4318 (HTTP) per spec.

        GIVEN: The default localhost:4318 endpoint
        WHEN: Protocol detection function is called
        THEN: HTTP protocol should be detected
        """
        from mcp_server_langgraph.observability.telemetry import (
            OTLP_ENDPOINT,
            detect_otlp_protocol,
        )

        # Verify default endpoint uses HTTP port
        assert ":4318" in OTLP_ENDPOINT, f"Default OTLP_ENDPOINT should use port 4318, got: {OTLP_ENDPOINT}"

        result = detect_otlp_protocol(OTLP_ENDPOINT)
        assert result == "http", f"Expected 'http' protocol for default endpoint, got: {result}"


@pytest.mark.xdist_group(name="telemetry_protocol_tests")
class TestOTLPExporterSelection:
    """Test that correct exporter type is selected based on protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_http_endpoint_uses_http_exporter_for_metrics(self) -> None:
        """
        Test that HTTP endpoint results in HTTP metric exporter being used.

        GIVEN: An endpoint with port 4318 (HTTP)
        WHEN: ObservabilityConfig sets up metric exporters
        THEN: HTTP exporter should be used, not gRPC

        This test verifies the fix for:
        "Failed to export metrics to alloy-test:4318, error code: StatusCode.UNAVAILABLE"
        """
        from mcp_server_langgraph.observability.telemetry import (
            HTTP_AVAILABLE,
            get_metric_exporter_type,
        )

        if not HTTP_AVAILABLE:
            pytest.skip("HTTP exporter not available")

        exporter_type = get_metric_exporter_type("http://alloy-test:4318")
        assert exporter_type == "http", f"Expected HTTP exporter for port 4318, got: {exporter_type}"

    def test_grpc_endpoint_uses_grpc_exporter_for_metrics(self) -> None:
        """
        Test that gRPC endpoint results in gRPC metric exporter being used.

        GIVEN: An endpoint with port 4317 (gRPC)
        WHEN: ObservabilityConfig sets up metric exporters
        THEN: gRPC exporter should be used
        """
        from mcp_server_langgraph.observability.telemetry import (
            GRPC_AVAILABLE,
            get_metric_exporter_type,
        )

        if not GRPC_AVAILABLE:
            pytest.skip("gRPC exporter not available")

        exporter_type = get_metric_exporter_type("http://collector:4317")
        assert exporter_type == "grpc", f"Expected gRPC exporter for port 4317, got: {exporter_type}"

    def test_http_endpoint_uses_http_exporter_for_traces(self) -> None:
        """
        Test that HTTP endpoint results in HTTP span exporter being used.

        GIVEN: An endpoint with port 4318 (HTTP)
        WHEN: ObservabilityConfig sets up span exporters
        THEN: HTTP exporter should be used, not gRPC
        """
        from mcp_server_langgraph.observability.telemetry import (
            HTTP_AVAILABLE,
            get_span_exporter_type,
        )

        if not HTTP_AVAILABLE:
            pytest.skip("HTTP exporter not available")

        exporter_type = get_span_exporter_type("http://alloy-test:4318")
        assert exporter_type == "http", f"Expected HTTP exporter for port 4318, got: {exporter_type}"

    def test_grpc_endpoint_uses_grpc_exporter_for_traces(self) -> None:
        """
        Test that gRPC endpoint results in gRPC span exporter being used.

        GIVEN: An endpoint with port 4317 (gRPC)
        WHEN: ObservabilityConfig sets up span exporters
        THEN: gRPC exporter should be used
        """
        from mcp_server_langgraph.observability.telemetry import (
            GRPC_AVAILABLE,
            get_span_exporter_type,
        )

        if not GRPC_AVAILABLE:
            pytest.skip("gRPC exporter not available")

        exporter_type = get_span_exporter_type("http://collector:4317")
        assert exporter_type == "grpc", f"Expected gRPC exporter for port 4317, got: {exporter_type}"


@pytest.mark.xdist_group(name="telemetry_protocol_tests")
class TestOTLPExporterConfiguration:
    """Test OTLP exporter configuration following OTel best practices."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_compression_returns_gzip_by_default(self) -> None:
        """
        Test that compression defaults to gzip per OTel best practices.

        Per OpenTelemetry best practices:
        "Use Gzip compression for your telemetry payloads to reduce
        network bandwidth usage, especially in high-volume environments."

        GIVEN: No explicit compression configuration
        WHEN: get_otlp_compression() is called
        THEN: Should return "gzip" as the default
        """
        from mcp_server_langgraph.observability.telemetry import get_otlp_compression

        result = get_otlp_compression()
        assert result == "gzip", f"Expected 'gzip' compression by default, got: {result}"

    def test_get_compression_respects_env_var(self) -> None:
        """
        Test that compression can be configured via environment variable.

        GIVEN: OTEL_EXPORTER_OTLP_COMPRESSION env var is set to "none"
        WHEN: get_otlp_compression() is called
        THEN: Should return the configured value
        """
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.observability.telemetry import get_otlp_compression

        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_COMPRESSION": "none"}):
            result = get_otlp_compression()
            assert result == "none", f"Expected 'none' from env var, got: {result}"

    def test_get_retry_config_returns_exponential_backoff(self) -> None:
        """
        Test that retry configuration uses exponential backoff per OTel best practices.

        Per OpenTelemetry best practices:
        "Ensure to configure the appropriate retry mechanisms with exponential
        backoff to ensure data is delivered even during temporary network issues."

        GIVEN: No explicit retry configuration
        WHEN: get_otlp_retry_config() is called
        THEN: Should return config with exponential backoff parameters
        """
        from mcp_server_langgraph.observability.telemetry import get_otlp_retry_config

        config = get_otlp_retry_config()

        # Verify required retry parameters are present
        assert "enabled" in config, "Retry config should have 'enabled' field"
        assert config["enabled"] is True, "Retries should be enabled by default"

        assert "initial_backoff_ms" in config, "Should have initial backoff"
        assert config["initial_backoff_ms"] > 0, "Initial backoff should be positive"

        assert "max_backoff_ms" in config, "Should have max backoff"
        assert config["max_backoff_ms"] >= config["initial_backoff_ms"], "Max backoff should be >= initial"

        assert "backoff_multiplier" in config, "Should have backoff multiplier"
        assert config["backoff_multiplier"] > 1.0, "Backoff multiplier should be > 1 for exponential growth"

    def test_get_retry_config_has_max_elapsed_time(self) -> None:
        """
        Test that retry configuration includes max elapsed time.

        Per Grafana Alloy docs:
        "If a batch hasn't been sent successfully, it's discarded after
        the time specified by max_elapsed_time elapses."

        GIVEN: Default retry configuration
        WHEN: get_otlp_retry_config() is called
        THEN: Should include max_elapsed_time parameter
        """
        from mcp_server_langgraph.observability.telemetry import get_otlp_retry_config

        config = get_otlp_retry_config()

        assert "max_elapsed_time_ms" in config, "Should have max elapsed time"
        assert config["max_elapsed_time_ms"] > 0, "Max elapsed time should be positive"

    def test_default_endpoint_uses_http_port(self) -> None:
        """
        Test that the default OTLP_ENDPOINT uses HTTP port 4318.

        Per OpenTelemetry spec, HTTP/protobuf should be the default.

        GIVEN: The module-level OTLP_ENDPOINT constant
        WHEN: Inspecting the value
        THEN: Should use port 4318 (HTTP) not 4317 (gRPC)
        """
        from mcp_server_langgraph.observability.telemetry import OTLP_ENDPOINT

        assert ":4318" in OTLP_ENDPOINT, f"Default endpoint should use HTTP port 4318, got: {OTLP_ENDPOINT}"
        assert "http://" in OTLP_ENDPOINT.lower(), f"Default endpoint should use http:// scheme, got: {OTLP_ENDPOINT}"
