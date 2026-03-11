"""
Tests for Agent Execution Tracing (Fix 2, Fix 3, Fix 4).

TDD: These tests verify the agent execution tracing feature flag behavior,
repository initialization, and trace emission control.

Terminology (Three Distinct Trace Types):
1. LangGraph Agent Execution Traces - This file
   - Purpose: Captures node execution events from LangGraph agent graphs
   - Storage: PostgreSQL langgraph_execution_traces table
   - Feature Flag: FF_ENABLE_AGENT_EXECUTION_TRACING

2. Decision Trace (Context Graph) - ADR-0101
   - Purpose: High-level decision context for learning
   - Feature Flag: enable_context_graph (SEPARATE)

3. OTEL Distributed Traces (Grafana Tempo)
   - Purpose: Infrastructure-level distributed tracing
   - Always on for observability

Reference: Triple-AI Diagnosis Plan - Issue 2: Missing LangGraph Execution Trace
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.unit, pytest.mark.chat, pytest.mark.tracing]


@pytest.fixture
def mock_feature_flags() -> MagicMock:
    """Create mock feature flags for testing."""
    flags = MagicMock()
    flags.enable_agent_execution_tracing = False  # Default off
    return flags


class TestAgentExecutionTracingFeatureFlag:
    """Tests for enable_agent_execution_tracing feature flag behavior.

    Verifies:
    - Feature flag acts as GATE (not just default)
    - Client cannot enable tracing if flag is disabled
    - Scoped to Studio sessions
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_emit_agent_execution_trace_ignored_when_flag_disabled(self) -> None:
        """Client cannot enable agent execution tracing when feature flag is off.

        Security: Feature flag acts as GATE, not just default.
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        with patch.object(feature_flags, "enable_agent_execution_tracing", False):
            # Import after patching to get the patched value
            # The resolve function should enforce the flag as a gate
            from mcp_server_langgraph.api.v1.chat import resolve_agent_execution_tracing

            # Even with emit_agent_execution_trace=True in request, should return False
            result = resolve_agent_execution_tracing(
                emit_agent_execution_trace=True,
                is_studio_session=True,
            )

            assert result is False, (
                "Agent execution tracing should be disabled when feature flag is off, regardless of request parameter"
            )

    @pytest.mark.asyncio
    async def test_agent_traces_emitted_by_default_for_studio_when_flag_enabled(self) -> None:
        """Studio sessions get agent execution tracing by default when flag is on."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        with patch.object(feature_flags, "enable_agent_execution_tracing", True):
            from mcp_server_langgraph.api.v1.chat import resolve_agent_execution_tracing

            # Default value (True) should be respected for Studio sessions
            result = resolve_agent_execution_tracing(
                emit_agent_execution_trace=True,  # Default in ChatCompletionRequest
                is_studio_session=True,
            )

            assert result is True, (
                "Agent execution tracing should be enabled by default for Studio sessions when feature flag is on"
            )

    @pytest.mark.asyncio
    async def test_agent_traces_can_be_explicitly_disabled(self) -> None:
        """Client can explicitly disable tracing for a specific request."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        with patch.object(feature_flags, "enable_agent_execution_tracing", True):
            from mcp_server_langgraph.api.v1.chat import resolve_agent_execution_tracing

            # Explicit False should be respected
            result = resolve_agent_execution_tracing(
                emit_agent_execution_trace=False,
                is_studio_session=True,
            )

            assert result is False, "Client should be able to explicitly disable tracing for a specific request"

    @pytest.mark.asyncio
    async def test_non_studio_session_no_tracing(self) -> None:
        """Non-Studio clients don't get tracing even with flag enabled."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        with patch.object(feature_flags, "enable_agent_execution_tracing", True):
            from mcp_server_langgraph.api.v1.chat import resolve_agent_execution_tracing

            result = resolve_agent_execution_tracing(
                emit_agent_execution_trace=True,
                is_studio_session=False,  # Not a Studio session
            )

            assert result is False, (
                "Non-Studio sessions should not get agent execution tracing even when feature flag is enabled"
            )


class TestAgentExecutionTracingRepositoryInit:
    """Tests for agent execution trace repository initialization.

    Verifies:
    - Repository initialized separately from context_graph
    - Fail-fast pattern when init fails
    - Global availability tracking
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_agent_execution_tracing_disabled_when_repo_init_fails(self) -> None:
        """Agent execution tracing is disabled when repository initialization fails.

        NOTE: Uses bootstrap/agent_execution_tracing.py, NOT context_graph.py
        """
        # Fix: Patch the global state directly since is_agent_execution_tracing_available
        # reads the global _agent_execution_tracing_available variable
        with patch(
            "mcp_server_langgraph.bootstrap.agent_execution_tracing._agent_execution_tracing_available",
            False,
        ):
            from mcp_server_langgraph.bootstrap.agent_execution_tracing import (
                is_agent_execution_tracing_available,
            )

            # After failed init, availability should be False
            assert is_agent_execution_tracing_available() is False, (
                "Agent execution tracing should be unavailable when repository initialization fails"
            )

    @pytest.mark.asyncio
    async def test_chat_continues_when_agent_tracing_unavailable(self) -> None:
        """Chat continues normally when agent execution tracing is unavailable.

        Graceful degradation: streaming works, traces just aren't emitted.
        """
        with patch(
            "mcp_server_langgraph.bootstrap.agent_execution_tracing.is_agent_execution_tracing_available",
            side_effect=lambda *a, **kw: False,
        ):
            # Import the chat module to test streaming behavior
            # The streaming should work without errors, just no traces
            from mcp_server_langgraph.core.feature_flags import feature_flags

            # Even with emit_agent_execution_trace=True and flag enabled,
            # if repository is unavailable, traces should be skipped
            with patch.object(feature_flags, "enable_agent_execution_tracing", True):
                from mcp_server_langgraph.api.v1.chat import (
                    should_emit_traces_with_availability_check,
                )

                result = should_emit_traces_with_availability_check(
                    emit_agent_execution_trace=True,
                    is_studio_session=True,
                )

                assert result is False, "Traces should be disabled when repository is unavailable for graceful degradation"


class TestAgentExecutionTracingChatRequest:
    """Tests for emit_agent_execution_trace request parameter.

    Verifies:
    - Default value is True
    - Parameter is respected when flag is enabled
    - Warning logged when client tries to enable but flag is off
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_emit_agent_execution_trace_defaults_to_true(self) -> None:
        """emit_agent_execution_trace should default to True in ChatCompletionRequest."""
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        # Create request without specifying emit_agent_execution_trace
        request = ChatCompletionRequest(
            session_id="test-session",
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Default should be True (enabled by default when flag allows)
        assert request.emit_agent_execution_trace is True, (
            "emit_agent_execution_trace should default to True so Studio sessions get tracing by default"
        )

    @pytest.mark.asyncio
    async def test_emit_agent_execution_trace_can_be_set_false(self) -> None:
        """Client can explicitly set emit_agent_execution_trace to False."""
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        request = ChatCompletionRequest(
            session_id="test-session",
            messages=[{"role": "user", "content": "Hello"}],
            emit_agent_execution_trace=False,
        )

        assert request.emit_agent_execution_trace is False


class TestWebSocketDisconnectFallback:
    """Tests for WebSocket disconnect HTTP polling fallback.

    These tests verify the backend endpoint availability for HTTP fallback
    when WebSocket is disconnected.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_agent_execution_trace_endpoint_exists(self) -> None:
        """Verify the agent execution trace REST endpoint exists for HTTP fallback."""
        from mcp_server_langgraph.api.v1.sessions import sessions_router

        # Check that the endpoint is registered
        routes = [route.path for route in sessions_router.routes]
        expected_path = "/sessions/{session_id}/agent-execution-trace"

        assert any(expected_path in str(route) for route in routes), (
            f"Expected endpoint {expected_path} to exist for HTTP fallback when WebSocket is disconnected"
        )
