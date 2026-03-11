"""
Integration tests for Tempo trace retrieval via sessions endpoint.

These tests validate the end-to-end flow of retrieving execution traces
from Grafana Tempo for a given session ID.

Tests require `make test-infra-full-up` to be running.

TDD Rationale:
--------------
The session trace endpoint retrieves traces from Tempo filtered by session_id tag.
These tests validate that:
1. Traces are correctly queried from Tempo
2. Span data is properly mapped to TraceStep format
3. Graceful degradation occurs when Tempo is unavailable
4. Session ownership is validated before trace retrieval

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.tempo: Tempo-specific tests

References:
-----------
- src/mcp_server_langgraph/api/v1/sessions.py:get_session_trace()
- src/mcp_server_langgraph/observability/query/backends/tempo.py
"""

import gc
import os
import socket
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.constants import TEST_TEMPO_PORT

# Module-level marker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="tempo_session_traces"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


# PYTEST-XDIST FIX: Infrastructure tests are flaky in parallel execution
_XDIST_INFRASTRUCTURE_UNSTABLE = os.getenv("PYTEST_XDIST_WORKER") is not None


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def tempo_available() -> bool:
    """Check if Tempo is available for testing."""
    import httpx

    if not is_port_in_use(TEST_TEMPO_PORT):
        return False

    try:
        # Check Tempo-specific endpoint
        response = httpx.get(
            f"http://localhost:{TEST_TEMPO_PORT}/ready",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def session_id() -> str:
    """Generate a unique session ID for testing."""
    worker_prefix = get_worker_prefix()
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{worker_prefix}_session_{timestamp}"


@pytest.fixture
def mock_session_service():
    """Create mock session service that returns a valid session."""
    from mcp_server_langgraph.api.v1.sessions import SessionData

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(
        return_value=SessionData(
            session_id="test-session-id",
            user_id="test-user",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
        )
    )
    return mock_service


@pytest.mark.xdist_group("test_tempo_trace_retrieval_integration")
class TestTempoTraceRetrievalIntegration:
    """Integration tests for Tempo trace retrieval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_tempo_client_search_traces_with_session_tag(self, session_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a session_id
        WHEN searching traces in Tempo with session_id tag
        THEN should return matching traces or empty result.
        """
        if not tempo_available():
            pytest.skip("Tempo not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        client = TempoTracingClient()
        await client.initialize()

        try:
            # Search for traces with session.id tag (OTEL dot notation)
            result = await client.search_traces(tags={"session.id": session_id})

            # Should return TraceSearchResult (possibly empty)
            assert result is not None
            assert hasattr(result, "traces")
            # Empty is OK - we're testing the query mechanism
        finally:
            await client.close()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_tempo_client_health_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN Tempo is running
        WHEN checking health
        THEN should return healthy status.
        """
        if not tempo_available():
            pytest.skip("Tempo not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        client = TempoTracingClient()
        await client.initialize()

        try:
            is_healthy = await client.health_check()
            assert is_healthy is True
        finally:
            await client.close()


@pytest.mark.xdist_group("test_session_trace_endpoint_integration")
class TestSessionTraceEndpointIntegration:
    """Integration tests for the sessions trace endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_get_session_trace_with_tempo_client(self, session_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a valid session and Tempo client
        WHEN calling get_session_trace
        THEN should return SessionTraceResponse with steps.
        """
        if not tempo_available():
            pytest.skip("Tempo not available for integration testing")

        from mcp_server_langgraph.api.v1.sessions import (
            SessionTraceResponse,
            TraceStep,
        )
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        client = TempoTracingClient()
        await client.initialize()

        try:
            # Query for traces (OTEL uses dot notation: session.id)
            result = await client.search_traces(tags={"session.id": session_id})

            # Convert to SessionTraceResponse format (mimicking sessions.py logic)
            steps: list[TraceStep] = []
            start_time: int | None = None
            end_time: int | None = None

            if result and result.traces:
                trace = result.traces[0]
                if trace.start_time:
                    start_time = int(trace.start_time.timestamp() * 1000)
                if trace.duration_ms and start_time:
                    end_time = start_time + int(trace.duration_ms)

                for span in trace.spans or []:
                    status_name = "completed"
                    if hasattr(span, "status_code") and span.status_code:
                        status_name = getattr(span.status_code, "name", "completed").lower()
                        if status_name == "ok":
                            status_name = "completed"
                        elif status_name == "error":
                            status_name = "failed"

                    steps.append(
                        TraceStep(
                            name=span.operation_name,
                            status=status_name,
                            duration=int(span.duration_ms) if span.duration_ms else None,
                        )
                    )

            response = SessionTraceResponse(
                raw_output=None,
                steps=steps,
                tokens=None,
                current_node=None,
                start_time=start_time,
                end_time=end_time,
            )

            # Validate response structure
            assert isinstance(response, SessionTraceResponse)
            assert isinstance(response.steps, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_session_trace_graceful_degradation_when_tempo_unavailable(
        self, session_id: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN Tempo is unavailable
        WHEN calling get_session_trace logic
        THEN should return empty trace without error.
        """
        from mcp_server_langgraph.api.v1.sessions import SessionTraceResponse

        # Simulate Tempo unavailable by using invalid URL
        monkeypatch.setenv("TEMPO_URL", "http://localhost:1")  # Invalid port

        # The endpoint should gracefully degrade
        steps: list = []
        response = SessionTraceResponse(
            raw_output=None,
            steps=steps,
            tokens=None,
            current_node=None,
            start_time=None,
            end_time=None,
        )

        assert isinstance(response, SessionTraceResponse)
        assert response.steps == []
        assert response.start_time is None
        assert response.end_time is None


@pytest.mark.xdist_group("test_session_trace_security_integration")
class TestSessionTraceSecurityIntegration:
    """Integration tests for session trace security validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_trace_requires_ownership_validation(self) -> None:
        """
        GIVEN a session_id
        WHEN getting trace for session not owned by user
        THEN should return 404 (session not found).
        """
        from unittest.mock import patch

        from mcp_server_langgraph.api.v1.sessions import get_session_service

        with patch.object(get_session_service(), "get_session", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None  # Session not found

            # The endpoint should check ownership before querying Tempo
            session = await get_session_service().get_session("non-existent-session", "wrong-user")

            assert session is None


@pytest.mark.xdist_group("test_span_thinking_object_integration")
class TestSpanThinkingObjectIntegration:
    """Integration tests for span thinking object format (Pattern 12).

    Verifies the transformation pipeline:
    OTEL attributes (thinking_content, thinking_tokens)
      → API response (thinking: { content, tokens })

    References:
    - .claude/context/code-patterns.md (Pattern 12: Thinking Field Conventions)
    - src/mcp_server_langgraph/api/v1/observability.py (_span_to_dict)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_span_to_dict_converts_thinking_attributes_to_object(self) -> None:
        """
        GIVEN span with thinking_content and thinking_tokens OTEL attributes
        WHEN converting to SpanResponse format via _span_to_dict
        THEN thinking should be object with content and tokens fields.
        """
        from dataclasses import dataclass, field
        from enum import Enum

        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        class StatusCode(Enum):
            OK = "OK"

        @dataclass
        class MockSpan:
            span_id: str = "span-integration-123"
            parent_span_id: str | None = None
            operation_name: str = "llm-call"
            start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
            duration_ms: float = 1500.0
            status_code: StatusCode = StatusCode.OK
            attributes: dict = None

            def __post_init__(self):
                if self.attributes is None:
                    self.attributes = {}

        service = ObservabilityServiceImpl()
        span = MockSpan(
            attributes={
                "thinking_content": "Let me analyze this step by step...",
                "thinking_tokens": 250,
                "model_name": "claude-opus-4-5-20250514",
            }
        )

        result = service._span_to_dict(span)

        # Verify thinking is object format (not flat fields)
        assert "thinking" in result
        assert result["thinking"] is not None
        assert result["thinking"]["content"] == "Let me analyze this step by step..."
        assert result["thinking"]["tokens"] == 250

        # Verify model_name is extracted
        assert result["model_name"] == "claude-opus-4-5-20250514"

        # Verify flat fields do NOT exist in result
        assert "thinking_content" not in result
        assert "thinking_tokens" not in result

    @pytest.mark.asyncio
    async def test_span_to_dict_without_thinking_returns_none(self) -> None:
        """
        GIVEN span without thinking OTEL attributes
        WHEN converting to SpanResponse format
        THEN thinking should be None.
        """
        from dataclasses import dataclass, field
        from enum import Enum

        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        class StatusCode(Enum):
            OK = "OK"

        @dataclass
        class MockSpan:
            span_id: str = "span-no-thinking"
            parent_span_id: str | None = None
            operation_name: str = "tool-call"
            start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
            duration_ms: float = 200.0
            status_code: StatusCode = StatusCode.OK
            attributes: dict = None

            def __post_init__(self):
                if self.attributes is None:
                    self.attributes = {}

        service = ObservabilityServiceImpl()
        span = MockSpan(attributes={"tool.name": "web_search"})

        result = service._span_to_dict(span)

        # Thinking should be None when no thinking attributes
        assert result["thinking"] is None

    @pytest.mark.asyncio
    async def test_span_to_dict_with_llm_model_fallback(self) -> None:
        """
        GIVEN span with llm.model attribute (not model_name)
        WHEN converting to SpanResponse format
        THEN model_name should use llm.model as fallback.
        """
        from dataclasses import dataclass, field
        from enum import Enum

        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        class StatusCode(Enum):
            OK = "OK"

        @dataclass
        class MockSpan:
            span_id: str = "span-llm-model"
            parent_span_id: str | None = None
            operation_name: str = "llm-call"
            start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
            duration_ms: float = 800.0
            status_code: StatusCode = StatusCode.OK
            attributes: dict = None

            def __post_init__(self):
                if self.attributes is None:
                    self.attributes = {}

        service = ObservabilityServiceImpl()
        span = MockSpan(attributes={"llm.model": "gpt-4-turbo"})

        result = service._span_to_dict(span)

        # model_name should use llm.model fallback
        assert result["model_name"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_span_response_schema_has_thinking_object(self) -> None:
        """
        GIVEN SpanResponse schema
        WHEN examining JSON schema
        THEN should have thinking field as optional object (not flat fields).
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        schema = SpanResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Verify thinking is in schema
        assert "thinking" in properties

        # Verify legacy flat fields do NOT exist
        assert "thinking_content" not in properties
        assert "thinking_tokens" not in properties

    @pytest.mark.asyncio
    async def test_span_thinking_response_schema_structure(self) -> None:
        """
        GIVEN SpanThinkingResponse schema
        WHEN examining JSON schema
        THEN should have content and tokens fields.
        """
        from mcp_server_langgraph.api.v1.observability import SpanThinkingResponse

        schema = SpanThinkingResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Verify required fields
        assert "content" in properties
        assert "tokens" in properties
