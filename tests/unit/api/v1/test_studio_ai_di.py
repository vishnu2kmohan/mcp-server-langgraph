"""
Unit tests for Studio AI Dependency Injection.

Tests for proper DI in StudioOrchestrator and GenUIOrchestrator.

Reference: Phase 3.3 - DI Refactor for Studio AI
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock

import pytest
from fastapi import Request

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.mark.xdist_group(name="test_studio_ai_di")
class TestStudioOrchestratorDI:
    """Tests for StudioOrchestrator dependency injection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_studio_orchestrator_dependency_exists(self) -> None:
        """
        GIVEN the studio_ai module
        WHEN importing get_studio_orchestrator
        THEN should export the dependency function.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        assert get_studio_orchestrator is not None
        assert callable(get_studio_orchestrator)

    def test_get_studio_orchestrator_accepts_request_parameter(self) -> None:
        """
        GIVEN the get_studio_orchestrator function
        WHEN checking the signature
        THEN should accept a Request parameter for DI.
        """
        import inspect

        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        sig = inspect.signature(get_studio_orchestrator)
        params = list(sig.parameters.keys())

        assert "request" in params, "Should accept request parameter for app.state DI"

    def test_get_studio_orchestrator_returns_orchestrator_type(self) -> None:
        """
        GIVEN a mock request with app.state
        WHEN calling get_studio_orchestrator
        THEN should return a StudioOrchestrator instance.
        """
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        mock_request = MagicMock(spec=Request)
        mock_request.app.state.ai_ux_service = None
        mock_request.app.state.llm_factory = None

        result = get_studio_orchestrator(mock_request)

        assert isinstance(result, StudioOrchestrator)

    def test_get_studio_orchestrator_injects_ai_ux_service(self) -> None:
        """
        GIVEN a request with ai_ux_service on app.state
        WHEN calling get_studio_orchestrator
        THEN should pass ai_ux_service to the orchestrator.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        mock_ai_ux_service = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.ai_ux_service = mock_ai_ux_service
        mock_request.app.state.llm_factory = None

        result = get_studio_orchestrator(mock_request)

        assert result._ai_ux_service is mock_ai_ux_service

    def test_get_studio_orchestrator_injects_llm_factory(self) -> None:
        """
        GIVEN a request with llm_factory on app.state
        WHEN calling get_studio_orchestrator
        THEN should pass llm_factory to the orchestrator.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        mock_llm_factory = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.ai_ux_service = None
        mock_request.app.state.llm_factory = mock_llm_factory

        result = get_studio_orchestrator(mock_request)

        assert result._llm_factory is mock_llm_factory

    def test_get_studio_orchestrator_handles_missing_state(self) -> None:
        """
        GIVEN a request without app.state attributes
        WHEN calling get_studio_orchestrator
        THEN should handle gracefully (use None).
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        mock_request = MagicMock(spec=Request)
        # Simulate missing attributes
        mock_request.app.state = MagicMock(spec=[])

        result = get_studio_orchestrator(mock_request)

        # Should not raise, use defaults
        assert result is not None


@pytest.mark.xdist_group(name="test_studio_ai_di")
class TestGenUIOrchestratorDI:
    """Tests for GenUIOrchestrator dependency injection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_genui_orchestrator_dependency_exists(self) -> None:
        """
        GIVEN the studio_ai module
        WHEN importing get_genui_orchestrator
        THEN should export the dependency function.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_genui_orchestrator

        assert get_genui_orchestrator is not None
        assert callable(get_genui_orchestrator)

    def test_get_genui_orchestrator_accepts_request_parameter(self) -> None:
        """
        GIVEN the get_genui_orchestrator function
        WHEN checking the signature
        THEN should accept a Request parameter for DI.
        """
        import inspect

        from mcp_server_langgraph.api.v1.studio_ai import get_genui_orchestrator

        sig = inspect.signature(get_genui_orchestrator)
        params = list(sig.parameters.keys())

        assert "request" in params, "Should accept request parameter for app.state DI"

    def test_get_genui_orchestrator_returns_orchestrator_type(self) -> None:
        """
        GIVEN a mock request with app.state
        WHEN calling get_genui_orchestrator
        THEN should return a GenUIOrchestrator instance.
        """
        from mcp_server_langgraph.agents.genui_orchestrator import GenUIOrchestrator
        from mcp_server_langgraph.api.v1.studio_ai import get_genui_orchestrator

        mock_request = MagicMock(spec=Request)
        mock_request.app.state.llm_factory = None

        result = get_genui_orchestrator(mock_request)

        assert isinstance(result, GenUIOrchestrator)

    def test_get_genui_orchestrator_injects_llm_factory(self) -> None:
        """
        GIVEN a request with llm_factory on app.state
        WHEN calling get_genui_orchestrator
        THEN should pass llm_factory to the orchestrator.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_genui_orchestrator

        mock_llm_factory = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.llm_factory = mock_llm_factory

        result = get_genui_orchestrator(mock_request)

        # GenUIOrchestrator uses public llm_factory attribute
        assert result.llm_factory is mock_llm_factory

    def test_get_genui_orchestrator_handles_missing_state(self) -> None:
        """
        GIVEN a request without app.state attributes
        WHEN calling get_genui_orchestrator
        THEN should handle gracefully (use None).
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_genui_orchestrator

        mock_request = MagicMock(spec=Request)
        mock_request.app.state = MagicMock(spec=[])

        result = get_genui_orchestrator(mock_request)

        # Should not raise, use defaults
        assert result is not None
