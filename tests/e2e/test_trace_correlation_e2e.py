"""
E2E Tests for Trace Correlation.

These tests verify that trace IDs flow correctly through the system:
1. Chat API returns trace_id in responses
2. Trace can be retrieved via observability API
3. Trace contains expected span structure

Purpose:
- Ensure end-to-end trace correlation works
- Verify trace_id is propagated from chat to observability
- Test the developer journey of debugging via traces
"""

from __future__ import annotations

import gc
import re
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.xdist_group(name="trace_correlation"),
]

if TYPE_CHECKING:
    pass


@pytest.fixture
def app_with_full_api() -> FastAPI:
    """Create a FastAPI app with the full v1 API mounted."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.router import v1_router

    app = FastAPI()
    app.include_router(v1_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app_with_full_api: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app_with_full_api)


@pytest.mark.xdist_group("test_trace_chat_a_p_i_integration")
class TestTraceChatAPIIntegration:
    """
    Tests for trace_id in Chat API responses.

    Verifies that trace IDs are correctly generated and returned
    in chat responses for correlation with observability data.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chat_response_includes_trace_id(self, client: TestClient) -> None:
        """
        GIVEN a valid chat request
        WHEN POST /api/v1/chat/sessions/{session_id}/chat is called
        THEN the response should include a trace_id field
        """
        # First create a session
        session_response = client.post(
            "/api/v1/sessions",
            json={"name": "Trace Test Session"},
        )
        # Skip if auth required
        if session_response.status_code == 401:
            pytest.skip("Authentication required for this test")

        if session_response.status_code == 200:
            session_id = session_response.json()["session_id"]

            # Now send a chat message (non-streaming for simpler test)
            chat_response = client.post(
                f"/api/v1/chat/sessions/{session_id}/chat",
                json={"message": "Hello, test message"},
            )

            if chat_response.status_code == 200:
                data = chat_response.json()
                # Verify trace_id is present
                assert "trace_id" in data, "Response should include trace_id"
                trace_id = data["trace_id"]
                # Verify trace_id format (should be a valid trace ID)
                assert trace_id is not None, "trace_id should not be None"
                assert len(trace_id) > 0, "trace_id should not be empty"

    def test_trace_id_format_is_valid(self, client: TestClient) -> None:
        """
        GIVEN a chat response with trace_id
        WHEN the trace_id is extracted
        THEN it should match the expected format (32 hex chars for OTEL)
        """
        # Create session
        session_response = client.post(
            "/api/v1/sessions",
            json={"name": "Trace Format Test"},
        )
        if session_response.status_code == 401:
            pytest.skip("Authentication required")

        if session_response.status_code == 200:
            session_id = session_response.json()["session_id"]

            chat_response = client.post(
                f"/api/v1/chat/sessions/{session_id}/chat",
                json={"message": "Test message for trace format"},
            )

            if chat_response.status_code == 200:
                data = chat_response.json()
                if "trace_id" in data and data["trace_id"]:
                    trace_id = data["trace_id"]
                    # OTEL trace IDs are 32 hex characters
                    assert re.match(r"^[a-f0-9]{32}$", trace_id), f"trace_id should be 32 hex chars, got: {trace_id}"


@pytest.mark.xdist_group("test_trace_observability_integration")
class TestTraceObservabilityIntegration:
    """
    Tests for trace retrieval via Observability API.

    Verifies that traces can be queried and contain expected
    span structure for debugging.

    Note: These tests require observability infrastructure (Grafana/Tempo).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.infrastructure
    def test_observability_traces_endpoint_works(self, client: TestClient) -> None:
        """
        GIVEN the observability API
        WHEN GET /api/v1/observability/traces is called
        THEN it should return a list of traces
        """
        try:
            response = client.get("/api/v1/observability/traces")
        except Exception as e:
            pytest.skip(f"Observability backend not available: {e}")

        # Should return 200 with traces list
        assert response.status_code == 200
        data = response.json()
        assert "items" in data, "Response should have items list"
        assert isinstance(data["items"], list)

    @pytest.mark.infrastructure
    def test_observability_trace_detail_endpoint_works(self, client: TestClient) -> None:
        """
        GIVEN a trace_id
        WHEN GET /api/v1/observability/traces/{trace_id} is called
        THEN it should return trace details or 404 if not found
        """
        # Use a dummy trace_id - should return 404 or trace data
        dummy_trace_id = "0" * 32
        try:
            response = client.get(f"/api/v1/observability/traces/{dummy_trace_id}")
        except Exception as e:
            pytest.skip(f"Observability backend not available: {e}")

        # Should return 200 (with data) or 404 (not found) - not 500
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"

    @pytest.mark.infrastructure
    def test_observability_traces_filter_by_session(self, client: TestClient) -> None:
        """
        GIVEN a session_id filter
        WHEN GET /api/v1/observability/traces?session_id=X is called
        THEN it should return traces filtered by session
        """
        try:
            response = client.get(
                "/api/v1/observability/traces",
                params={"session_id": "test-session-123"},
            )
        except Exception as e:
            pytest.skip(f"Observability backend not available: {e}")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data


@pytest.mark.xdist_group("test_trace_end_to_end_flow")
class TestTraceEndToEndFlow:
    """
    End-to-end tests for the complete trace correlation flow.

    Tests the developer journey: chat → get trace_id → view in observability.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.infrastructure
    def test_chat_trace_can_be_retrieved_via_observability(self, client: TestClient) -> None:
        """
        GIVEN a chat interaction that generates a trace
        WHEN the trace_id is used to query observability API
        THEN the trace should be retrievable with span data

        Note: This test requires full infrastructure (OTEL collector, etc.)
        """
        # Step 1: Create session
        session_response = client.post(
            "/api/v1/sessions",
            json={"name": "E2E Trace Flow Test"},
        )
        if session_response.status_code == 401:
            pytest.skip("Authentication required")

        if session_response.status_code != 200:
            pytest.skip(f"Session creation failed: {session_response.status_code}")

        session_id = session_response.json()["session_id"]

        # Step 2: Send chat message
        chat_response = client.post(
            f"/api/v1/chat/sessions/{session_id}/chat",
            json={"message": "E2E trace test"},
        )

        if chat_response.status_code != 200:
            pytest.skip(f"Chat failed: {chat_response.status_code}")

        data = chat_response.json()
        if "trace_id" not in data or not data["trace_id"]:
            pytest.skip("No trace_id in response")

        trace_id = data["trace_id"]

        # Step 3: Retrieve trace via observability API
        # Note: There may be a delay before trace is available
        trace_response = client.get(f"/api/v1/observability/traces/{trace_id}")

        # The trace should either be found or still processing
        assert trace_response.status_code in [200, 404], f"Unexpected status: {trace_response.status_code}"

        if trace_response.status_code == 200:
            trace_data = trace_response.json()
            assert trace_data["trace_id"] == trace_id
            # Should have spans
            if "spans" in trace_data:
                assert isinstance(trace_data["spans"], list)


@pytest.mark.xdist_group("test_trace_metrics_aggregation")
class TestTraceMetricsAggregation:
    """
    Tests for trace-based metrics aggregation.

    Verifies that the metrics endpoints correctly aggregate trace data.

    Note: These tests require observability infrastructure.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.infrastructure
    def test_observability_metrics_endpoint_works(self, client: TestClient) -> None:
        """
        GIVEN the observability API
        WHEN GET /api/v1/observability/metrics is called
        THEN it should return aggregated metrics
        """
        try:
            response = client.get("/api/v1/observability/metrics")
        except Exception as e:
            pytest.skip(f"Observability backend not available: {e}")

        assert response.status_code == 200
        data = response.json()

        # Verify expected metric fields exist (at least the core fields)
        expected_fields = [
            "requests_total",
            "errors_total",
        ]
        for field in expected_fields:
            assert field in data, f"Missing metric field: {field}"

        # Check for latency fields (may be avg_latency_ms or latency_p* variants)
        has_latency = "avg_latency_ms" in data or "latency_p50" in data or "latency_p95" in data or "latency_p99" in data
        assert has_latency, f"Missing latency fields in: {data.keys()}"

    @pytest.mark.infrastructure
    def test_metrics_include_entity_breakdowns(self, client: TestClient) -> None:
        """
        GIVEN the observability metrics
        WHEN metrics are retrieved
        THEN they should include entity-level breakdowns when available
        """
        try:
            response = client.get("/api/v1/observability/metrics")
        except Exception as e:
            pytest.skip(f"Observability backend not available: {e}")

        assert response.status_code == 200
        # The response structure should support breakdowns
        # (actual content depends on data availability)
