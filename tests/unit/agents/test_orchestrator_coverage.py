"""
Additional orchestrator tests for coverage improvement.

These tests focus on:
- scale_effort method
- execute async method
- synthesize async method
- get_verifier_model method
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.agents.orchestrator import (
    Orchestrator,
    Subtask,
    TaskDecomposition,
)
from mcp_server_langgraph.agents.subagent import SubagentResult

pytestmark = [pytest.mark.unit, pytest.mark.agents]


@pytest.mark.xdist_group(name="test_orchestrator_scale_effort")
class TestOrchestratorScaleEffort:
    """Tests for scale_effort method."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_scale_effort_simple_task(self) -> None:
        """Test scaling effort for a simple short task."""
        orchestrator = Orchestrator()

        count = orchestrator.scale_effort("Fix bug")

        assert count >= 1
        assert count <= 10

    def test_scale_effort_complex_keywords_increase_count(self) -> None:
        """Test that complex keywords increase subagent count."""
        orchestrator = Orchestrator()

        simple_count = orchestrator.scale_effort("Do something")
        complex_count = orchestrator.scale_effort("Comprehensive thorough detailed analyze research investigate compare")

        assert complex_count > simple_count

    def test_scale_effort_long_task_increases_count(self) -> None:
        """Test that longer tasks increase base count."""
        orchestrator = Orchestrator()

        short_count = orchestrator.scale_effort("Short task")
        long_task = " ".join(["word"] * 50)  # 50 words
        long_count = orchestrator.scale_effort(long_task)

        assert long_count >= short_count

    def test_scale_effort_max_is_10(self) -> None:
        """Test that scale_effort caps at 10."""
        orchestrator = Orchestrator()

        # Create a task with many complex keywords and lots of words
        complex_keywords = "comprehensive thorough detailed analyze research investigate compare multiple"
        long_task = f"{complex_keywords} " + " ".join(["word"] * 200)

        count = orchestrator.scale_effort(long_task)

        assert count <= 10

    def test_scale_effort_min_is_1(self) -> None:
        """Test that scale_effort returns at least 1."""
        orchestrator = Orchestrator()

        count = orchestrator.scale_effort("")

        assert count >= 1


@pytest.mark.xdist_group(name="test_orchestrator_execute")
class TestOrchestratorExecute:
    """Tests for execute method."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_creates_subagents(self) -> None:
        """Test that execute creates subagents for each subtask."""
        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="sub-1",
                    title="Subtask 1",
                    instructions="Do subtask 1",
                ),
                Subtask(
                    task_id="sub-2",
                    title="Subtask 2",
                    instructions="Do subtask 2",
                ),
            ],
            synthesis_instructions="Synthesize results",
        )

        # Patch the coordinator's execute_all
        with patch.object(
            orchestrator.coordinator,
            "execute_all",
            new_callable=AsyncMock,
            return_value=[
                SubagentResult(task_id="sub-1", success=True, output="output1"),
                SubagentResult(task_id="sub-2", success=True, output="output2"),
            ],
        ):
            results = await orchestrator.execute(decomposition)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

    @pytest.mark.asyncio
    async def test_execute_stores_successful_outputs_as_artifacts(self) -> None:
        """Test that successful outputs are stored as artifacts."""
        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="sub-1",
                    title="Subtask 1",
                    instructions="Do subtask 1",
                ),
            ],
        )

        with patch.object(
            orchestrator.coordinator,
            "execute_all",
            new_callable=AsyncMock,
            return_value=[
                SubagentResult(task_id="sub-1", success=True, output="result data"),
            ],
        ):
            await orchestrator.execute(decomposition)

        # Check artifact was stored
        artifact = orchestrator.artifact_storage.retrieve("sub-1", "result")
        assert artifact == "result data"

    @pytest.mark.asyncio
    async def test_execute_does_not_store_failed_outputs(self) -> None:
        """Test that failed outputs are not stored as artifacts."""
        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="sub-1",
                    title="Subtask 1",
                    instructions="Do subtask 1",
                ),
            ],
        )

        with patch.object(
            orchestrator.coordinator,
            "execute_all",
            new_callable=AsyncMock,
            return_value=[
                SubagentResult(task_id="sub-1", success=False, error="failed"),
            ],
        ):
            await orchestrator.execute(decomposition)

        # Check no artifact was stored
        artifact = orchestrator.artifact_storage.retrieve("sub-1", "result")
        assert artifact is None

    @pytest.mark.asyncio
    async def test_execute_uses_model_selector(self) -> None:
        """Test that execute uses model selector for each subtask."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        mock_selector = MagicMock(spec=ModelSelector)
        mock_selector.select_model.return_value = "test-model"

        orchestrator = Orchestrator(model_selector=mock_selector)
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="sub-1",
                    title="Subtask 1",
                    instructions="Do subtask 1",
                    complexity="complicated",
                ),
            ],
        )

        with patch.object(
            orchestrator.coordinator,
            "execute_all",
            new_callable=AsyncMock,
            return_value=[
                SubagentResult(task_id="sub-1", success=True, output="output"),
            ],
        ):
            await orchestrator.execute(decomposition)

        mock_selector.select_model.assert_called_with("complicated")


@pytest.mark.xdist_group(name="test_orchestrator_synthesize")
class TestOrchestratorSynthesize:
    """Tests for synthesize method."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_synthesize_collects_successful_outputs(self) -> None:
        """Test that synthesize collects all successful outputs."""
        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Original research task",
            subtasks=[
                Subtask(task_id="sub-1", title="S1", instructions="I1"),
                Subtask(task_id="sub-2", title="S2", instructions="I2"),
            ],
        )
        results = [
            SubagentResult(task_id="sub-1", success=True, output="output1"),
            SubagentResult(task_id="sub-2", success=True, output="output2"),
        ]

        synthesis = await orchestrator.synthesize(decomposition, results)

        assert synthesis["original_task"] == "Original research task"
        assert synthesis["subtask_count"] == 2
        assert synthesis["successful_count"] == 2
        assert "output1" in synthesis["outputs"]
        assert "output2" in synthesis["outputs"]

    @pytest.mark.asyncio
    async def test_synthesize_excludes_failed_outputs(self) -> None:
        """Test that synthesize excludes failed outputs."""
        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Task",
            subtasks=[
                Subtask(task_id="sub-1", title="S1", instructions="I1"),
                Subtask(task_id="sub-2", title="S2", instructions="I2"),
            ],
        )
        results = [
            SubagentResult(task_id="sub-1", success=True, output="good output"),
            SubagentResult(task_id="sub-2", success=False, error="failed"),
        ]

        synthesis = await orchestrator.synthesize(decomposition, results)

        assert synthesis["successful_count"] == 1
        assert len(synthesis["outputs"]) == 1
        assert "good output" in synthesis["outputs"]

    @pytest.mark.asyncio
    async def test_synthesize_handles_empty_outputs(self) -> None:
        """Test that synthesize handles results with no output."""
        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Task",
            subtasks=[
                Subtask(task_id="sub-1", title="S1", instructions="I1"),
            ],
        )
        results = [
            SubagentResult(task_id="sub-1", success=True, output=None),
        ]

        synthesis = await orchestrator.synthesize(decomposition, results)

        assert synthesis["successful_count"] == 0
        assert len(synthesis["outputs"]) == 0


@pytest.mark.xdist_group(name="test_orchestrator_verifier")
class TestOrchestratorVerifier:
    """Tests for get_verifier_model method."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_get_verifier_model_returns_model(self) -> None:
        """Test that get_verifier_model returns a valid model."""
        orchestrator = Orchestrator()

        verifier = orchestrator.get_verifier_model()

        assert verifier is not None
        assert isinstance(verifier, str)
        assert len(verifier) > 0

    def test_get_verifier_model_uses_auto_mode(self) -> None:
        """Test that get_verifier_model uses auto mode."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector, SelectionResult

        mock_selector = MagicMock(spec=ModelSelector)
        mock_result = SelectionResult(model="claude-sonnet", tier="complicated", vendor="anthropic", is_fallback=False)
        mock_selector.select_verifier.return_value = mock_result

        orchestrator = Orchestrator(model_selector=mock_selector)

        verifier = orchestrator.get_verifier_model()

        mock_selector.select_verifier.assert_called_once_with("auto")
        assert verifier == "claude-sonnet"
