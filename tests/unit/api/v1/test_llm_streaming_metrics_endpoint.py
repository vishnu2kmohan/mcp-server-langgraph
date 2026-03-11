"""
Tests for LLM streaming metrics API endpoint.

TDD: Tests written for /api/v1/observability/metrics/llm-streaming endpoint.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.observability, pytest.mark.metrics]

# Mock user for testing auth-required endpoints
MOCK_USER = {
    "sub": "test-user-id",
    "user_id": "test-user-id",
    "username": "testuser",
    "email": "testuser@example.com",
    "roles": ["user"],
    "realm_access": {"roles": ["user"]},
}


@pytest.mark.xdist_group(name="llm_streaming_metrics_endpoint")
class TestLLMStreamingMetricsEndpointSchema:
    """Tests for LLMStreamingMetricsResponse schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_llm_streaming_metrics_response_exists(self) -> None:
        """
        GIVEN the observability module
        WHEN importing LLMStreamingMetricsResponse
        THEN should be available.
        """
        from mcp_server_langgraph.api.v1.observability import LLMStreamingMetricsResponse

        assert LLMStreamingMetricsResponse is not None

    def test_llm_streaming_metrics_response_has_required_fields(self) -> None:
        """
        GIVEN LLMStreamingMetricsResponse
        WHEN checking fields
        THEN should have all required metric fields.
        """
        from mcp_server_langgraph.api.v1.observability import LLMStreamingMetricsResponse

        schema = LLMStreamingMetricsResponse.model_json_schema()
        properties = schema["properties"]

        # Required metric fields
        assert "ttfc_p50_seconds" in properties
        assert "ttfc_p95_seconds" in properties
        assert "ttfc_p99_seconds" in properties
        assert "inter_chunk_latency_p50_seconds" in properties
        assert "inter_chunk_latency_p95_seconds" in properties
        assert "duration_avg_seconds" in properties
        assert "total_streams" in properties
        assert "success_rate" in properties
        assert "total_chunks" in properties
        assert "feature_enabled" in properties

    def test_llm_streaming_metrics_response_default_values(self) -> None:
        """
        GIVEN LLMStreamingMetricsResponse
        WHEN created with minimal data
        THEN should have sensible defaults.
        """
        from mcp_server_langgraph.api.v1.observability import LLMStreamingMetricsResponse

        response = LLMStreamingMetricsResponse()

        assert response.ttfc_p50_seconds is None
        assert response.ttfc_p95_seconds is None
        assert response.total_streams == 0
        assert response.total_chunks == 0
        assert response.feature_enabled is True


@pytest.mark.xdist_group(name="llm_streaming_metrics_endpoint")
class TestLLMStreamingMetricsEndpointBehavior:
    """Tests for endpoint behavior with feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_endpoint_returns_empty_when_feature_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN calling the endpoint
        THEN should return empty response with feature_enabled=False.
        """
        from mcp_server_langgraph.api.v1.observability import get_llm_streaming_metrics

        with patch("mcp_server_langgraph.core.feature_flags.get_feature_flags") as mock_flags:
            mock_flags.return_value.enable_streaming_metrics = False

            response = await get_llm_streaming_metrics(provider=None, model=None, time_range="1h", user=MOCK_USER)

            assert response.feature_enabled is False
            assert response.total_streams == 0
            assert response.total_chunks == 0

    @pytest.mark.asyncio
    async def test_endpoint_returns_metrics_when_feature_enabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=True and metrics available
        WHEN calling the endpoint
        THEN should return metrics data.
        """
        from mcp_server_langgraph.api.v1.observability import get_llm_streaming_metrics

        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config (method configured below)
        mock_service.get_llm_streaming_metrics = AsyncMock(
            side_effect=lambda *a, **kw: {
                "ttfc_p95_seconds": 1.5,
                "ttfc_p50_seconds": 0.8,
                "inter_chunk_latency_p95_seconds": 0.15,
                "total_streams": 100,
                "total_chunks": 5000,
                "success_rate": 0.95,
            }
        )

        with (
            patch("mcp_server_langgraph.core.feature_flags.get_feature_flags") as mock_flags,
            patch(
                "mcp_server_langgraph.api.v1.observability.get_observability_service",
                side_effect=lambda *a, **kw: mock_service,
            ),
        ):
            mock_flags.return_value.enable_streaming_metrics = True

            response = await get_llm_streaming_metrics(provider="openai", model=None, time_range="1h", user=MOCK_USER)

            assert response.feature_enabled is True
            assert response.ttfc_p95_seconds == 1.5
            assert response.total_streams == 100
            assert response.success_rate == 0.95
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_endpoint_handles_service_error_gracefully(self) -> None:
        """
        GIVEN enable_streaming_metrics=True but service fails
        WHEN calling the endpoint
        THEN should return empty response without raising error.
        """
        from mcp_server_langgraph.api.v1.observability import get_llm_streaming_metrics

        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config (method configured below)
        mock_service.get_llm_streaming_metrics = AsyncMock(side_effect=Exception("Prometheus unavailable"))

        with (
            patch("mcp_server_langgraph.core.feature_flags.get_feature_flags") as mock_flags,
            patch(
                "mcp_server_langgraph.api.v1.observability.get_observability_service",
                side_effect=lambda *a, **kw: mock_service,
            ),
        ):
            mock_flags.return_value.enable_streaming_metrics = True

            # Should not raise
            response = await get_llm_streaming_metrics(provider=None, model=None, time_range="1h", user=MOCK_USER)

            assert response.feature_enabled is True
            assert response.total_streams == 0  # Default empty values
