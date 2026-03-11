"""
Integration tests for OTLP gRPC exporter selection.

These tests require the optional opentelemetry-exporter-otlp-proto-grpc package.
They verify that gRPC exporters are correctly selected for port 4317 endpoints.

Note: The default/recommended protocol is HTTP (port 4318) per OpenTelemetry spec.
gRPC is only needed for high-throughput scenarios with full HTTP/2 infrastructure support.

See: tests/unit/observability/test_telemetry_protocol_detection.py for HTTP tests
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="otlp_grpc_exporter"),
]


@pytest.mark.xdist_group("test_g_r_p_c_exporter_selection")
class TestGRPCExporterSelection:
    """
    Integration tests for gRPC exporter selection.

    These tests depend on the optional opentelemetry-exporter-otlp-proto-grpc package.
    They are skipped if the package is not installed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

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
            pytest.skip("gRPC exporter not available - install opentelemetry-exporter-otlp-proto-grpc")

        exporter_type = get_metric_exporter_type("http://collector:4317")
        assert exporter_type == "grpc", f"Expected gRPC exporter for port 4317, got: {exporter_type}"

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
            pytest.skip("gRPC exporter not available - install opentelemetry-exporter-otlp-proto-grpc")

        exporter_type = get_span_exporter_type("http://collector:4317")
        assert exporter_type == "grpc", f"Expected gRPC exporter for port 4317, got: {exporter_type}"

    def test_grpc_available_flag_reflects_package_installation(self) -> None:
        """
        Test that GRPC_AVAILABLE correctly reflects package availability.

        GIVEN: The telemetry module
        WHEN: Checking GRPC_AVAILABLE flag
        THEN: Should be True only if opentelemetry-exporter-otlp-proto-grpc is installed
        """
        from mcp_server_langgraph.observability.telemetry import GRPC_AVAILABLE

        # Try to import the gRPC exporter directly
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,  # noqa: F401
            )

            grpc_installed = True
        except ImportError:
            grpc_installed = False

        assert grpc_installed == GRPC_AVAILABLE, (
            f"GRPC_AVAILABLE ({GRPC_AVAILABLE}) should match package availability ({grpc_installed})"
        )
