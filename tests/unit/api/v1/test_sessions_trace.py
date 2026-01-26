"""
Tests for Session Trace Retrieval.

TDD tests for GET /api/v1/sessions/{session_id}/trace endpoint.
Verifies trace retrieval from Tempo backend.

PYTEST-XDIST FIX: Uses gc.collect() in teardown for memory safety.
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="sessions_trace")
class TestSessionTraceEndpoint:
    """Tests for GET /api/v1/sessions/{session_id}/trace endpoint."""

    def setup_method(self) -> None:
        """Reset singletons before each test."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_session_service(self, session_exists: bool = True) -> AsyncMock:
        """Create mock session service."""
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        if session_exists:
            mock_service.get_session.return_value = MagicMock(
                session_id="session-123",
                user_id="user:alice",
            )
        else:
            mock_service.get_session.return_value = None
        return mock_service

    def _create_mock_tempo_client(
        self,
        traces: list | None = None,
        raise_error: Exception | None = None,
    ) -> AsyncMock:
        """Create mock Tempo client."""
        mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config

        if raise_error:
            mock_client.search_by_attribute.side_effect = raise_error
        else:
            # Create mock TraceSearchResult
            mock_result = MagicMock()
            mock_result.traces = traces or []
            mock_result.total_count = len(traces) if traces else 0
            mock_client.search_by_attribute.return_value = mock_result

        return mock_client

    def _create_mock_trace(
        self,
        trace_id: str = "abc123",
        spans: list | None = None,
    ) -> MagicMock:
        """Create a mock TraceInfo object."""
        mock_trace = MagicMock()
        mock_trace.trace_id = trace_id
        mock_trace.start_time = datetime(2025, 12, 31, 12, 0, 0, tzinfo=UTC)
        mock_trace.duration_ms = 1500.0
        mock_trace.span_count = len(spans) if spans else 0
        mock_trace.error_count = 0
        mock_trace.spans = spans or []
        return mock_trace

    def _create_mock_span(
        self,
        operation_name: str = "LLMCall",
        status: str = "OK",
        duration_ms: float = 500.0,
    ) -> MagicMock:
        """Create a mock SpanInfo object."""
        mock_span = MagicMock()
        mock_span.operation_name = operation_name
        mock_span.status_code = MagicMock()
        mock_span.status_code.name = status
        mock_span.duration_ms = duration_ms
        mock_span.attributes = {}
        return mock_span

    def _create_app(
        self,
        mock_tempo_client: AsyncMock | None = None,
    ) -> FastAPI:
        """Create FastAPI app with session router."""
        from mcp_server_langgraph.api.deps import get_tempo_client
        from mcp_server_langgraph.api.v1.sessions import sessions_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(sessions_router, prefix="/api/v1")

        # Mock current user
        mock_user = {
            "sub": "user-123",
            "user_id": "user:alice",
            "username": "alice",
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        # Mock Tempo client
        if mock_tempo_client:
            app.dependency_overrides[get_tempo_client] = lambda: mock_tempo_client

        return app

    @pytest.mark.asyncio
    async def test_get_session_trace_queries_tempo(self) -> None:
        """GET /sessions/{id}/trace calls Tempo with session_id tag."""
        mock_session_service = self._create_mock_session_service(session_exists=True)

        # Create trace with spans
        mock_spans = [
            self._create_mock_span("agent.run", "OK", 1000.0),
            self._create_mock_span("llm.call", "OK", 500.0),
        ]
        mock_trace = self._create_mock_trace("trace-123", mock_spans)
        mock_tempo = self._create_mock_tempo_client(traces=[mock_trace])

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            app = self._create_app(mock_tempo)
            client = TestClient(app)
            response = client.get("/api/v1/sessions/session-123/trace")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "steps" in data
        assert "start_time" in data
        assert "end_time" in data

        # Verify Tempo was queried with session.id attribute
        mock_tempo.search_by_attribute.assert_called_once()
        call_kwargs = mock_tempo.search_by_attribute.call_args.kwargs
        assert call_kwargs.get("attribute") == "session.id"
        assert call_kwargs.get("value") == "session-123"

    @pytest.mark.asyncio
    async def test_get_session_trace_maps_spans_to_steps(self) -> None:
        """GET /sessions/{id}/trace maps SpanInfo to TraceStep."""
        mock_session_service = self._create_mock_session_service(session_exists=True)

        mock_spans = [
            self._create_mock_span("node.process", "OK", 750.0),
        ]
        mock_trace = self._create_mock_trace("trace-456", mock_spans)
        mock_tempo = self._create_mock_tempo_client(traces=[mock_trace])

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            app = self._create_app(mock_tempo)
            client = TestClient(app)
            response = client.get("/api/v1/sessions/session-123/trace")

        assert response.status_code == 200
        data = response.json()

        # Verify steps are mapped from spans
        assert len(data["steps"]) >= 1
        step = data["steps"][0]
        assert "name" in step
        assert "status" in step
        assert "duration" in step

    @pytest.mark.asyncio
    async def test_get_session_trace_empty_when_no_traces(self) -> None:
        """GET /sessions/{id}/trace returns empty when no traces found."""
        mock_session_service = self._create_mock_session_service(session_exists=True)
        mock_tempo = self._create_mock_tempo_client(traces=[])

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            app = self._create_app(mock_tempo)
            client = TestClient(app)
            response = client.get("/api/v1/sessions/session-123/trace")

        assert response.status_code == 200
        data = response.json()

        # Should return empty but valid response
        assert data["steps"] == []
        assert data["raw_output"] is None

    @pytest.mark.asyncio
    async def test_get_session_trace_session_not_found_returns_404(self) -> None:
        """GET /sessions/{id}/trace returns 404 for missing session."""
        mock_session_service = self._create_mock_session_service(session_exists=False)
        mock_tempo = self._create_mock_tempo_client()

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            app = self._create_app(mock_tempo)
            client = TestClient(app)
            response = client.get("/api/v1/sessions/nonexistent/trace")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session_trace_graceful_on_tempo_error(self) -> None:
        """GET /sessions/{id}/trace returns empty on Tempo error (graceful degradation)."""
        mock_session_service = self._create_mock_session_service(session_exists=True)
        mock_tempo = self._create_mock_tempo_client(raise_error=Exception("Tempo connection failed"))

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            app = self._create_app(mock_tempo)
            client = TestClient(app)
            response = client.get("/api/v1/sessions/session-123/trace")

        # Should return 200 with empty trace, not 500
        assert response.status_code == 200
        data = response.json()
        assert data["steps"] == []
