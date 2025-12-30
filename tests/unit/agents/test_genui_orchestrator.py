"""
TDD: Unit tests for GenUI Orchestrator.

Tests that GenUIOrchestrator generates dynamic UI components
using LLM intelligence when enabled.

Sprint 6: GenUI
- generate_widget() creates chart/table/text widgets
- render_data() transforms data into renderable format
- execute_form() handles form submission logic

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.agents import genui_orchestrator as genui_module

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.genui]


def _mock_feature_flags(enable_genui: bool = True) -> MagicMock:
    """Create a mock feature flags object."""
    mock_flags = MagicMock()
    mock_flags.enable_genui = enable_genui
    return mock_flags


# =============================================================================
# GenUI Orchestrator Tests
# =============================================================================


@pytest.mark.xdist_group(name="genui_orchestrator")
class TestGenUIOrchestrator:
    """Test GenUIOrchestrator class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_widget_creates_chart(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN prompt for chart WHEN generate_widget THEN returns chart config."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUITask,
        )

        # Enable the feature flag at module level
        monkeypatch.setattr(genui_module, "feature_flags", _mock_feature_flags(enable_genui=True))

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "widget_type": "chart",
            "title": "Monthly Sales",
            "data": {
                "labels": ["Jan", "Feb", "Mar"],
                "values": [100, 150, 200]
            },
            "confidence": 0.92
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        task = GenUITask(
            task_type="generate_widget",
            data={
                "prompt": "Show monthly sales data",
                "context": {"sales": [100, 150, 200]},
            },
        )

        results = await orchestrator.execute([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result is not None
        assert results[0].result["widget_type"] == "chart"

    @pytest.mark.asyncio
    async def test_generate_widget_creates_table(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN data for table WHEN generate_widget THEN returns table config."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUITask,
        )

        # Enable the feature flag at module level
        monkeypatch.setattr(genui_module, "feature_flags", _mock_feature_flags(enable_genui=True))

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "widget_type": "table",
            "title": "User Data",
            "data": {
                "columns": ["Name", "Email"],
                "rows": [["Alice", "alice@example.com"]]
            },
            "confidence": 0.88
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        task = GenUITask(
            task_type="generate_widget",
            data={
                "prompt": "Show user list as table",
                "context": {"users": [{"name": "Alice", "email": "alice@example.com"}]},
            },
        )

        results = await orchestrator.execute([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result["widget_type"] == "table"

    @pytest.mark.asyncio
    async def test_render_data_transforms_to_widget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN raw data WHEN render_data THEN transforms to widget format."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUITask,
        )

        # Enable the feature flag at module level
        monkeypatch.setattr(genui_module, "feature_flags", _mock_feature_flags(enable_genui=True))

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "widget_type": "text",
            "title": "Summary",
            "data": {
                "content": "Total revenue: $450"
            },
            "confidence": 0.95
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        task = GenUITask(
            task_type="render_data",
            data={
                "raw_data": {"revenue": 450},
                "format_hint": "text summary",
            },
        )

        results = await orchestrator.execute([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result["widget_type"] == "text"

    @pytest.mark.asyncio
    async def test_execute_form_returns_action(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN form data WHEN execute_form THEN returns action result."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUITask,
        )

        # Enable the feature flag at module level
        monkeypatch.setattr(genui_module, "feature_flags", _mock_feature_flags(enable_genui=True))

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "action": "submit",
            "validated_data": {"email": "test@example.com"},
            "next_step": "confirmation",
            "confidence": 0.97
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        task = GenUITask(
            task_type="execute_form",
            data={
                "form_id": "contact-form",
                "form_data": {"email": "test@example.com"},
            },
        )

        results = await orchestrator.execute([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result["action"] == "submit"

    @pytest.mark.asyncio
    async def test_genui_respects_feature_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN feature flag disabled WHEN execute THEN uses fallback."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUITask,
        )

        # Disable the feature flag at module level
        monkeypatch.setattr(genui_module, "feature_flags", _mock_feature_flags(enable_genui=False))

        mock_llm = MagicMock()
        # Should not be called, but configure to satisfy linting
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="{}"))

        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        task = GenUITask(
            task_type="generate_widget",
            data={"prompt": "Test"},
        )

        results = await orchestrator.execute([task])

        # LLM should not be called when feature is disabled
        mock_llm.ainvoke.assert_not_called()

        # Should still return valid result (fallback)
        assert len(results) == 1
        assert results[0].result is not None

    @pytest.mark.asyncio
    async def test_genui_fallback_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN LLM error WHEN execute THEN returns fallback result."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUITask,
        )

        # Enable the feature flag at module level
        monkeypatch.setattr(genui_module, "feature_flags", _mock_feature_flags(enable_genui=True))

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        task = GenUITask(
            task_type="generate_widget",
            data={"prompt": "Test"},
        )

        results = await orchestrator.execute([task])

        # Should return result even on error (graceful degradation)
        assert len(results) == 1
        # Could be success with fallback or failure with error message
        assert results[0].result is not None or results[0].error is not None


# =============================================================================
# Synthesis Tests
# =============================================================================


@pytest.mark.xdist_group(name="genui_synthesis")
class TestGenUISynthesis:
    """Test GenUI result synthesis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_synthesize_combines_widgets(self) -> None:
        """GIVEN multiple widget results WHEN synthesize THEN combines into layout."""
        from mcp_server_langgraph.agents.genui_orchestrator import (
            GenUIOrchestrator,
            GenUIResult,
        )

        mock_llm = MagicMock()
        orchestrator = GenUIOrchestrator(llm_factory=mock_llm)

        results = [
            GenUIResult(
                task_type="generate_widget",
                success=True,
                result={"widget_type": "chart", "title": "Chart 1"},
            ),
            GenUIResult(
                task_type="generate_widget",
                success=True,
                result={"widget_type": "table", "title": "Table 1"},
            ),
        ]

        synthesized = orchestrator.synthesize(results)

        assert "widgets" in synthesized
        assert len(synthesized["widgets"]) == 2
        assert "layout" in synthesized
