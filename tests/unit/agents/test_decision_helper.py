"""
Unit tests for Decision Helper module.

TDD RED Phase: Tests for agents/decision_helper.py module.

Tests:
- get_decision_emitter function
- emit_routing_decision helper
- emit_tool_selection_decision helper
- emit_model_selection_decision helper
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_request():
    """Create a mock request with app.state."""
    request = MagicMock()
    request.app.state.decision_emitter = MagicMock()
    return request


@pytest.fixture
def mock_request_no_emitter():
    """Create a mock request without decision_emitter."""
    request = MagicMock()
    request.app.state = MagicMock(spec=[])
    return request


@pytest.fixture
def mock_decision_context():
    """Create a mock DecisionContext."""
    from mcp_server_langgraph.agents.decision_emitter import DecisionContext

    return DecisionContext(
        run_id="run-123",
        session_id="session-456",
        workflow_id=None,
        project_id=None,
        organization_id="org:acme",
        user_id="user:alice",
    )


@pytest.mark.xdist_group(name="test_decision_helper")
class TestGetDecisionEmitter:
    """Tests for get_decision_emitter function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_decision_emitter_exists(self) -> None:
        """get_decision_emitter function should exist."""
        from mcp_server_langgraph.agents.decision_helper import get_decision_emitter

        assert callable(get_decision_emitter)

    def test_get_decision_emitter_returns_emitter(self, mock_request) -> None:
        """get_decision_emitter should return emitter from app.state."""
        from mcp_server_langgraph.agents.decision_helper import get_decision_emitter

        emitter = get_decision_emitter(mock_request)
        assert emitter is mock_request.app.state.decision_emitter

    def test_get_decision_emitter_returns_none_when_not_configured(
        self, mock_request_no_emitter
    ) -> None:
        """get_decision_emitter should return None when not configured."""
        from mcp_server_langgraph.agents.decision_helper import get_decision_emitter

        emitter = get_decision_emitter(mock_request_no_emitter)
        assert emitter is None


@pytest.mark.xdist_group(name="test_decision_helper")
class TestEmitRoutingDecision:
    """Tests for emit_routing_decision helper."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emit_routing_decision_exists(self) -> None:
        """emit_routing_decision function should exist."""
        from mcp_server_langgraph.agents.decision_helper import emit_routing_decision

        assert callable(emit_routing_decision)

    @pytest.mark.asyncio
    async def test_emit_routing_decision_calls_emitter(
        self, mock_request, mock_decision_context
    ) -> None:
        """emit_routing_decision should call emitter.emit with correct params."""
        from mcp_server_langgraph.agents.decision_helper import emit_routing_decision

        mock_request.app.state.decision_emitter.emit = AsyncMock(
            return_value="trace-abc"
        )

        result = await emit_routing_decision(
            request=mock_request,
            context=mock_decision_context,
            query="What's the weather?",
            chosen_action="weather_tool",
            confidence=0.95,
            rationale="User is asking about weather",
            available_actions=["weather_tool", "search_tool"],
        )

        assert result == "trace-abc"
        mock_request.app.state.decision_emitter.emit.assert_called_once()
        call_kwargs = mock_request.app.state.decision_emitter.emit.call_args
        assert call_kwargs.kwargs["decision_type"] == "routing"
        assert call_kwargs.kwargs["decision_stage"] == "action"

    @pytest.mark.asyncio
    async def test_emit_routing_decision_returns_none_when_no_emitter(
        self, mock_request_no_emitter, mock_decision_context
    ) -> None:
        """emit_routing_decision should return None when emitter not available."""
        from mcp_server_langgraph.agents.decision_helper import emit_routing_decision

        result = await emit_routing_decision(
            request=mock_request_no_emitter,
            context=mock_decision_context,
            query="Test query",
            chosen_action="test_action",
            confidence=0.9,
            rationale="Test rationale",
        )

        assert result is None


@pytest.mark.xdist_group(name="test_decision_helper")
class TestEmitToolSelectionDecision:
    """Tests for emit_tool_selection_decision helper."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emit_tool_selection_decision_exists(self) -> None:
        """emit_tool_selection_decision function should exist."""
        from mcp_server_langgraph.agents.decision_helper import (
            emit_tool_selection_decision,
        )

        assert callable(emit_tool_selection_decision)

    @pytest.mark.asyncio
    async def test_emit_tool_selection_decision_calls_emitter(
        self, mock_request, mock_decision_context
    ) -> None:
        """emit_tool_selection_decision should call emitter with tool_selection type."""
        from mcp_server_langgraph.agents.decision_helper import (
            emit_tool_selection_decision,
        )

        mock_request.app.state.decision_emitter.emit = AsyncMock(
            return_value="trace-tool-123"
        )

        result = await emit_tool_selection_decision(
            request=mock_request,
            context=mock_decision_context,
            query="Deploy the application",
            selected_tools=["kubernetes_deploy", "helm_upgrade"],
            confidence=0.88,
            rationale="User wants deployment, selected K8s tools",
            available_tools=["kubernetes_deploy", "helm_upgrade", "docker_push"],
        )

        assert result == "trace-tool-123"
        call_kwargs = mock_request.app.state.decision_emitter.emit.call_args
        assert call_kwargs.kwargs["decision_type"] == "tool_selection"


@pytest.mark.xdist_group(name="test_decision_helper")
class TestEmitModelSelectionDecision:
    """Tests for emit_model_selection_decision helper."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emit_model_selection_decision_exists(self) -> None:
        """emit_model_selection_decision function should exist."""
        from mcp_server_langgraph.agents.decision_helper import (
            emit_model_selection_decision,
        )

        assert callable(emit_model_selection_decision)

    @pytest.mark.asyncio
    async def test_emit_model_selection_decision_calls_emitter(
        self, mock_request, mock_decision_context
    ) -> None:
        """emit_model_selection_decision should call emitter with model_selection type."""
        from mcp_server_langgraph.agents.decision_helper import (
            emit_model_selection_decision,
        )

        mock_request.app.state.decision_emitter.emit = AsyncMock(
            return_value="trace-model-456"
        )

        result = await emit_model_selection_decision(
            request=mock_request,
            context=mock_decision_context,
            query="Analyze this complex dataset",
            selected_model="claude-opus-4",
            confidence=0.92,
            rationale="Complex analysis requires advanced reasoning",
            available_models=["claude-sonnet-4", "claude-opus-4", "gpt-4"],
        )

        assert result == "trace-model-456"
        call_kwargs = mock_request.app.state.decision_emitter.emit.call_args
        assert call_kwargs.kwargs["decision_type"] == "model_selection"


@pytest.mark.xdist_group(name="test_decision_helper")
class TestEmitApprovalDecision:
    """Tests for emit_approval_decision helper."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emit_approval_decision_exists(self) -> None:
        """emit_approval_decision function should exist."""
        from mcp_server_langgraph.agents.decision_helper import emit_approval_decision

        assert callable(emit_approval_decision)

    @pytest.mark.asyncio
    async def test_emit_approval_decision_calls_emitter(
        self, mock_request, mock_decision_context
    ) -> None:
        """emit_approval_decision should call emitter with approval type."""
        from mcp_server_langgraph.agents.decision_helper import emit_approval_decision

        mock_request.app.state.decision_emitter.emit = AsyncMock(
            return_value="trace-approval-789"
        )

        result = await emit_approval_decision(
            request=mock_request,
            context=mock_decision_context,
            query="Delete production database",
            approved=False,
            confidence=0.99,
            rationale="High-risk operation requires human approval",
        )

        assert result == "trace-approval-789"
        call_kwargs = mock_request.app.state.decision_emitter.emit.call_args
        assert call_kwargs.kwargs["decision_type"] == "approval"
        assert call_kwargs.kwargs["decision_stage"] == "policy_check"


@pytest.mark.xdist_group(name="test_decision_helper")
class TestDecisionHelperExports:
    """Tests for module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_helpers_exported(self) -> None:
        """All helper functions should be importable from module."""
        from mcp_server_langgraph.agents.decision_helper import (
            emit_approval_decision,
            emit_model_selection_decision,
            emit_routing_decision,
            emit_tool_selection_decision,
            get_decision_emitter,
        )

        assert all(
            [
                get_decision_emitter,
                emit_routing_decision,
                emit_tool_selection_decision,
                emit_model_selection_decision,
                emit_approval_decision,
            ]
        )
