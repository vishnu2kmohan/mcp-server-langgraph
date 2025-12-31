"""
Tests for ObservabilityServiceImpl.

TDD: These tests are written FIRST to define the expected behavior
of ObservabilityServiceImpl, which wraps TracingQueryClient and MetricsQueryClient.

Tests verify:
1. list_traces() delegates to tracing.search_traces()
2. get_trace() delegates to tracing.get_trace()
3. get_metrics() returns proper metrics data
4. Cursor-based pagination is handled
5. Data is converted to dict format matching response models
"""

from __future__ import annotations

import gc
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.observability.query.interfaces import (
        TraceInfo,
        TraceSearchResult,
    )


@pytest.mark.xdist_group(name="observability_service_impl")
class TestObservabilityServiceImpl:
    """Test suite for ObservabilityServiceImpl."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_tracing_client(self) -> MagicMock:
        """Create a mock TracingQueryClient."""
        client = MagicMock()
        client.search_traces = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        client.get_trace = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        client.search_by_attribute = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        return client

    @pytest.fixture
    def mock_metrics_client(self) -> MagicMock:
        """Create a mock MetricsQueryClient."""
        client = MagicMock()
        client.get_service_metrics = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        client.query_instant = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        return client

    @pytest.fixture
    def sample_trace_info(self) -> TraceInfo:
        """Create a sample TraceInfo for testing."""
        from mcp_server_langgraph.observability.query.interfaces import (
            SpanInfo,
            SpanStatusCode,
            TraceInfo,
        )

        return TraceInfo(
            trace_id="abc123def456",
            root_service="mcp-server",
            root_operation="handle_request",
            start_time=datetime(2025, 1, 15, 10, 30, 0),
            duration_ms=150.5,
            span_count=5,
            error_count=0,
            spans=[
                SpanInfo(
                    span_id="span1",
                    trace_id="abc123def456",
                    operation_name="handle_request",
                    service_name="mcp-server",
                    start_time=datetime(2025, 1, 15, 10, 30, 0),
                    duration_ms=150.5,
                    status_code=SpanStatusCode.OK,
                )
            ],
        )

    @pytest.fixture
    def sample_trace_search_result(self, sample_trace_info: TraceInfo) -> TraceSearchResult:
        """Create a sample TraceSearchResult for testing."""
        from mcp_server_langgraph.observability.query.interfaces import TraceSearchResult

        return TraceSearchResult(
            traces=[sample_trace_info],
            total_count=1,
            next_cursor=None,
        )

    # =========================================================================
    # list_traces() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_traces_delegates_to_tracing_client(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_search_result: TraceSearchResult,
    ) -> None:
        """GIVEN an ObservabilityServiceImpl with tracing client
        WHEN list_traces() is called
        THEN it delegates to tracing.search_traces()
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing_client.search_traces.return_value = sample_trace_search_result
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        traces, next_cursor = await service.list_traces()

        mock_tracing_client.search_traces.assert_called_once()
        assert len(traces) == 1

    @pytest.mark.asyncio
    async def test_list_traces_returns_list_of_dicts(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_search_result: TraceSearchResult,
    ) -> None:
        """GIVEN traces from tracing client
        WHEN list_traces() is called
        THEN it returns list of dicts matching TraceListItem format
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing_client.search_traces.return_value = sample_trace_search_result
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        traces, _ = await service.list_traces()

        assert traces[0]["trace_id"] == "abc123def456"
        assert traces[0]["name"] == "handle_request"
        assert traces[0]["duration_ms"] == 150.5
        assert traces[0]["span_count"] == 5

    @pytest.mark.asyncio
    async def test_list_traces_handles_session_id_filter(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_search_result: TraceSearchResult,
    ) -> None:
        """GIVEN session_id parameter
        WHEN list_traces() is called
        THEN it uses search_by_attribute for session filtering
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing_client.search_by_attribute.return_value = sample_trace_search_result
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        await service.list_traces(session_id="session-123")

        mock_tracing_client.search_by_attribute.assert_called_once()
        call_kwargs = mock_tracing_client.search_by_attribute.call_args.kwargs
        assert call_kwargs["attribute"] == "session_id"
        assert call_kwargs["value"] == "session-123"

    @pytest.mark.asyncio
    async def test_list_traces_returns_next_cursor(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_info: TraceInfo,
    ) -> None:
        """GIVEN more traces available
        WHEN list_traces() is called
        THEN it returns next_cursor for pagination
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl
        from mcp_server_langgraph.observability.query.interfaces import TraceSearchResult

        result = TraceSearchResult(
            traces=[sample_trace_info],
            total_count=10,
            next_cursor="cursor-abc",
        )
        mock_tracing_client.search_traces.return_value = result
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        _, next_cursor = await service.list_traces()

        assert next_cursor == "cursor-abc"

    # =========================================================================
    # get_trace() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_trace_delegates_to_tracing_client(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_info: TraceInfo,
    ) -> None:
        """GIVEN a trace_id
        WHEN get_trace() is called
        THEN it delegates to tracing.get_trace()
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing_client.get_trace.return_value = sample_trace_info
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        result = await service.get_trace("abc123def456")

        mock_tracing_client.get_trace.assert_called_once_with("abc123def456")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_trace_returns_dict_with_spans(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_info: TraceInfo,
    ) -> None:
        """GIVEN a trace with spans
        WHEN get_trace() is called
        THEN it returns dict with spans list
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing_client.get_trace.return_value = sample_trace_info
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        result = await service.get_trace("abc123def456")

        assert result is not None
        assert result["trace_id"] == "abc123def456"
        assert result["name"] == "handle_request"
        assert "spans" in result
        assert len(result["spans"]) == 1

    @pytest.mark.asyncio
    async def test_get_trace_returns_none_for_not_found(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
    ) -> None:
        """GIVEN trace not found
        WHEN get_trace() is called
        THEN it returns None
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing_client.get_trace.return_value = None
        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        result = await service.get_trace("nonexistent")

        assert result is None

    # =========================================================================
    # get_metrics() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_metrics_returns_metrics_dict(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
    ) -> None:
        """GIVEN metrics client
        WHEN get_metrics() is called
        THEN it returns dict matching MetricsResponse format
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl
        from mcp_server_langgraph.observability.query.interfaces import (
            MetricQueryResult,
            MetricSeries,
            MetricValue,
        )

        # Mock metric query results
        mock_metrics_client.query_instant.return_value = MetricQueryResult(
            series=[
                MetricSeries(
                    metric_name="requests_total",
                    labels={},
                    values=[MetricValue(timestamp=datetime.now(), value=1000)],
                )
            ]
        )

        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        result = await service.get_metrics()

        assert "requests_total" in result
        assert "errors_total" in result

    # =========================================================================
    # get_observability_service() integration tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_observability_service_returns_impl(self) -> None:
        """GIVEN the observability service getter
        WHEN get_observability_service() is called
        THEN it returns an ObservabilityServiceImpl (not the stub)
        """
        from mcp_server_langgraph.api.v1.observability import (
            ObservabilityServiceImpl,
            get_observability_service,
        )

        service = get_observability_service()

        assert isinstance(service, ObservabilityServiceImpl)

    @pytest.mark.asyncio
    async def test_observability_service_impl_does_not_raise_not_implemented(
        self,
        mock_tracing_client: MagicMock,
        mock_metrics_client: MagicMock,
        sample_trace_search_result: TraceSearchResult,
        sample_trace_info: TraceInfo,
    ) -> None:
        """GIVEN an ObservabilityServiceImpl
        WHEN any method is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl
        from mcp_server_langgraph.observability.query.interfaces import MetricQueryResult

        mock_tracing_client.search_traces.return_value = sample_trace_search_result
        mock_tracing_client.get_trace.return_value = sample_trace_info
        mock_metrics_client.query_instant.return_value = MetricQueryResult(series=[])

        service = ObservabilityServiceImpl(
            tracing=mock_tracing_client,
            metrics=mock_metrics_client,
        )

        # These should NOT raise NotImplementedError
        await service.list_traces()
        await service.get_trace("test-id")
        await service.get_metrics()
