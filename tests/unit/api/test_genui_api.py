"""
TDD: Unit tests for GenUI API endpoint.

Tests that the GenUI endpoint correctly routes to GenUIOrchestrator.

Sprint 6: GenUI feature
- POST /api/v1/studio/genui - Generate dynamic UI widgets

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.agents.genui_orchestrator import (
    GenUIOrchestrator,
    GenUIResult,
)

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.genui]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_genui_orchestrator() -> MagicMock:
    """Mock GenUI orchestrator."""
    mock = MagicMock(spec=GenUIOrchestrator)
    mock.execute = AsyncMock(
        return_value=[
            GenUIResult(
                task_type="generate_widget",
                success=True,
                result={
                    "widget_type": "chart",
                    "title": "Test Chart",
                    "data": {"labels": ["A", "B"], "values": [1, 2]},
                    "confidence": 0.9,
                },
            )
        ]
    )
    mock.synthesize = MagicMock(
        return_value={
            "widgets": [
                {
                    "id": "widget-0",
                    "widget_type": "chart",
                    "title": "Test Chart",
                }
            ],
            "layout": "single",
            "total_count": 1,
        }
    )
    return mock


# =============================================================================
# GenUI API Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="genui_api")
class TestGenUIAPIEndpoint:
    """Test POST /api/v1/studio/genui endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_genui_request_model_validation(self) -> None:
        """GIVEN valid request data WHEN create model THEN succeeds."""
        from mcp_server_langgraph.api.v1.studio_ai import GenUIRequest

        request = GenUIRequest(tasks=[{"task_type": "generate_widget", "data": {"prompt": "Show sales"}}])

        assert len(request.tasks) == 1
        assert request.tasks[0]["task_type"] == "generate_widget"

    def test_genui_response_model_structure(self) -> None:
        """GIVEN response data WHEN create model THEN has required fields."""
        from mcp_server_langgraph.api.v1.studio_ai import GenUIResponse

        response = GenUIResponse(
            widgets=[{"id": "widget-0", "widget_type": "chart"}],
            layout="single",
            total_count=1,
        )

        assert response.widgets is not None
        assert response.layout == "single"
        assert response.total_count == 1

    @pytest.mark.asyncio
    async def test_genui_endpoint_calls_orchestrator(self, mock_genui_orchestrator: MagicMock) -> None:
        """GIVEN valid request WHEN POST genui THEN calls orchestrator."""
        from mcp_server_langgraph.api.v1 import studio_ai as studio_ai_module
        from mcp_server_langgraph.api.v1.studio_ai import generate_ui, GenUIRequest

        request = GenUIRequest(tasks=[{"task_type": "generate_widget", "data": {"prompt": "Show sales"}}])

        # Mock feature flags to enable genui
        mock_flags = MagicMock()
        mock_flags.enable_genui = True

        with patch.object(studio_ai_module, "feature_flags", mock_flags):
            with patch(
                "mcp_server_langgraph.api.v1.studio_ai.get_genui_orchestrator",
                return_value=mock_genui_orchestrator,
            ):
                result = await generate_ui(request, current_user={"sub": "user-123"})

        mock_genui_orchestrator.execute.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_genui_endpoint_returns_widgets(self, mock_genui_orchestrator: MagicMock) -> None:
        """GIVEN valid request WHEN POST genui THEN returns widget list."""
        from mcp_server_langgraph.api.v1 import studio_ai as studio_ai_module
        from mcp_server_langgraph.api.v1.studio_ai import generate_ui, GenUIRequest

        request = GenUIRequest(tasks=[{"task_type": "generate_widget", "data": {"prompt": "Show chart"}}])

        # Mock feature flags to enable genui
        mock_flags = MagicMock()
        mock_flags.enable_genui = True

        with patch.object(studio_ai_module, "feature_flags", mock_flags):
            with patch(
                "mcp_server_langgraph.api.v1.studio_ai.get_genui_orchestrator",
                return_value=mock_genui_orchestrator,
            ):
                result = await generate_ui(request, current_user={"sub": "user-123"})

        assert "widgets" in result
        assert len(result["widgets"]) > 0

    @pytest.mark.asyncio
    async def test_genui_endpoint_returns_layout(self, mock_genui_orchestrator: MagicMock) -> None:
        """GIVEN multiple widgets WHEN POST genui THEN returns layout."""
        from mcp_server_langgraph.api.v1.studio_ai import generate_ui, GenUIRequest

        request = GenUIRequest(
            tasks=[
                {"task_type": "generate_widget", "data": {"prompt": "Chart 1"}},
                {"task_type": "generate_widget", "data": {"prompt": "Chart 2"}},
            ]
        )

        with patch(
            "mcp_server_langgraph.api.v1.studio_ai.get_genui_orchestrator",
            return_value=mock_genui_orchestrator,
        ):
            result = await generate_ui(request, current_user={"sub": "user-123"})

        assert "layout" in result


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="genui_api_flags")
class TestGenUIFeatureFlag:
    """Test feature flag gating for GenUI endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_genui_respects_feature_flag(self, mock_genui_orchestrator: MagicMock) -> None:
        """GIVEN feature flag disabled WHEN POST genui THEN returns fallback."""
        from mcp_server_langgraph.api.v1 import studio_ai as studio_ai_module
        from mcp_server_langgraph.api.v1.studio_ai import generate_ui, GenUIRequest

        # Mock feature flags to disable genui
        mock_flags = MagicMock()
        mock_flags.enable_genui = False

        request = GenUIRequest(tasks=[{"task_type": "generate_widget", "data": {"prompt": "Test"}}])

        with patch.object(studio_ai_module, "feature_flags", mock_flags):
            with patch(
                "mcp_server_langgraph.api.v1.studio_ai.get_genui_orchestrator",
                return_value=mock_genui_orchestrator,
            ):
                result = await generate_ui(request, current_user={"sub": "user-123"})

        # Should still return valid response (graceful degradation)
        assert result is not None
