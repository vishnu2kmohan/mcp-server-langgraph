"""
MCP Streaming Metrics Endpoint Tests

TDD RED Phase: Tests for GET /api/v1/mcp/metrics/streams endpoint.
This endpoint exposes streaming statistics for monitoring and debugging.
"""

from __future__ import annotations

import gc

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the MCP WebSocket router."""
    from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

    app = FastAPI()
    app.include_router(mcp_websocket_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_mcp_streaming_metrics_endpoint")
class TestStreamingMetricsEndpointExists:
    """Tests for streaming metrics endpoint availability."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_endpoint_exists(self, client: TestClient) -> None:
        """
        GIVEN the MCP WebSocket router
        WHEN GET /mcp/metrics/streams is called
        THEN should return 200 OK (not 404).
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_streaming_metrics_returns_json(self, client: TestClient) -> None:
        """
        GIVEN the streaming metrics endpoint
        WHEN GET request is made
        THEN should return JSON content type.
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        assert response.headers.get("content-type", "").startswith("application/json")


@pytest.mark.xdist_group(name="test_mcp_streaming_metrics_endpoint")
class TestStreamingMetricsResponseFormat:
    """Tests for streaming metrics response structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_response_contains_aggregate_stats(self, client: TestClient) -> None:
        """
        GIVEN the streaming metrics endpoint
        WHEN GET request is made
        THEN response should contain aggregate statistics.
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        assert "aggregate" in data
        aggregate = data["aggregate"]
        assert "total_streams" in aggregate
        assert "total_chunks" in aggregate
        assert "total_bytes" in aggregate

    def test_response_contains_active_streams(self, client: TestClient) -> None:
        """
        GIVEN the streaming metrics endpoint
        WHEN GET request is made
        THEN response should contain active streams count.
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        assert "active_streams" in data
        assert isinstance(data["active_streams"], int)

    def test_response_contains_streams_list(self, client: TestClient) -> None:
        """
        GIVEN the streaming metrics endpoint
        WHEN GET request is made
        THEN response should contain a list of streams.
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        assert "streams" in data
        assert isinstance(data["streams"], list)


@pytest.mark.xdist_group(name="test_mcp_streaming_metrics_endpoint")
class TestStreamingMetricsWithData:
    """Tests for streaming metrics with actual data."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_reflect_recorded_streams(self, client: TestClient) -> None:
        """
        GIVEN recorded stream metrics
        WHEN GET request is made
        THEN response should reflect recorded data.
        """
        # Import from canonical path (same as endpoint uses) to guarantee object identity
        from mcp_server_langgraph.mcp.websocket.streaming import streaming_metrics_collector

        # Record some test data
        test_stream_id = "test-metrics-api-stream"
        streaming_metrics_collector.record_stream_start(test_stream_id)
        streaming_metrics_collector.record_chunk(test_stream_id, chunk_size=256)
        streaming_metrics_collector.record_stream_end(test_stream_id)

        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        # Should have at least the stream we recorded
        assert data["aggregate"]["total_streams"] >= 1
        assert data["aggregate"]["total_chunks"] >= 1
        assert data["aggregate"]["total_bytes"] >= 256

    def test_active_streams_count_accurate(self, client: TestClient) -> None:
        """
        GIVEN an active stream (started but not ended)
        WHEN GET request is made
        THEN active_streams count should include it.
        """
        from mcp_server_langgraph.mcp.websocket.streaming import streaming_metrics_collector

        # Start a stream without ending it
        active_stream_id = "test-active-stream-api"
        streaming_metrics_collector.record_stream_start(active_stream_id)

        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        # Should have at least 1 active stream
        assert data["active_streams"] >= 1

        # Clean up - end the stream
        streaming_metrics_collector.record_stream_end(active_stream_id)


@pytest.mark.xdist_group(name="test_mcp_streaming_metrics_endpoint")
class TestStreamingMetricsFiltering:
    """Tests for filtering options in streaming metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_by_active_only(self, client: TestClient) -> None:
        """
        GIVEN both active and completed streams
        WHEN GET request is made with active_only=true
        THEN response should only include active streams.
        """
        from mcp_server_langgraph.mcp.websocket.streaming import streaming_metrics_collector

        # Create both active and completed streams
        active_id = "filter-test-active"
        completed_id = "filter-test-completed"

        streaming_metrics_collector.record_stream_start(active_id)
        streaming_metrics_collector.record_stream_start(completed_id)
        streaming_metrics_collector.record_stream_end(completed_id)

        response = client.get("/api/v1/mcp/metrics/streams?active_only=true")
        data = response.json()

        # Verify only active streams are included
        stream_ids = [s.get("stream_id") for s in data.get("streams", [])]
        assert completed_id not in stream_ids

        # Clean up
        streaming_metrics_collector.record_stream_end(active_id)

    def test_limit_parameter_works(self, client: TestClient) -> None:
        """
        GIVEN many recorded streams
        WHEN GET request is made with limit parameter
        THEN response should respect the limit.
        """
        response = client.get("/api/v1/mcp/metrics/streams?limit=5")
        data = response.json()

        # streams list should respect limit
        assert len(data.get("streams", [])) <= 5


@pytest.mark.xdist_group(name="test_mcp_streaming_metrics_endpoint")
class TestStreamingMetricsSchema:
    """Tests for streaming metrics response schema validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_aggregate_stats_types(self, client: TestClient) -> None:
        """
        GIVEN the streaming metrics endpoint
        WHEN GET request is made
        THEN aggregate fields should have correct types.
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        aggregate = data["aggregate"]
        assert isinstance(aggregate["total_streams"], int)
        assert isinstance(aggregate["total_chunks"], int)
        assert isinstance(aggregate["total_bytes"], int)

    def test_stream_entry_schema(self, client: TestClient) -> None:
        """
        GIVEN a recorded stream
        WHEN GET request is made
        THEN stream entries should have expected fields.
        """
        from mcp_server_langgraph.mcp.websocket.streaming import streaming_metrics_collector

        # Record a stream
        stream_id = "schema-test-stream"
        streaming_metrics_collector.record_stream_start(stream_id)
        streaming_metrics_collector.record_chunk(stream_id, chunk_size=100)
        streaming_metrics_collector.record_stream_end(stream_id)

        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        # Find our stream
        streams = data.get("streams", [])
        test_stream = next((s for s in streams if s.get("stream_id") == stream_id), None)

        if test_stream:
            # Verify schema
            assert "stream_id" in test_stream
            assert "chunk_count" in test_stream
            assert "total_bytes" in test_stream
            assert "avg_chunk_size" in test_stream
            assert "duration_ms" in test_stream

    def test_response_includes_timestamp(self, client: TestClient) -> None:
        """
        GIVEN the streaming metrics endpoint
        WHEN GET request is made
        THEN response should include a timestamp for cache invalidation.
        """
        response = client.get("/api/v1/mcp/metrics/streams")
        data = response.json()

        assert "timestamp" in data
