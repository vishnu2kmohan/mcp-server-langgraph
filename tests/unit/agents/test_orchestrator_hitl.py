"""
Unit tests for Orchestrator HITL (Human-in-the-Loop) Integration

Tests the execute_with_hitl method that enables confidence-based
human intervention in multi-agent orchestration.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.agents.orchestrator import Orchestrator, Subtask, TaskDecomposition
from mcp_server_langgraph.agents.subagent import SubagentResult

pytestmark = [pytest.mark.unit, pytest.mark.multi_agent, pytest.mark.hitl]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_hitl")
class TestOrchestratorHITLMethod:
    """Test suite for execute_with_hitl method existence and signature."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execute_with_hitl_method_exists(self):
        """GIVEN an Orchestrator
        WHEN checking for execute_with_hitl method
        THEN it should exist
        """
        orchestrator = Orchestrator()
        assert hasattr(orchestrator, "execute_with_hitl")
        assert callable(orchestrator.execute_with_hitl)

    def test_execute_with_hitl_accepts_threshold_parameter(self):
        """GIVEN an Orchestrator
        WHEN calling execute_with_hitl
        THEN it should accept a threshold parameter
        """
        orchestrator = Orchestrator()
        # Just check the method signature accepts threshold
        # The actual execution will be tested separately
        import inspect
        sig = inspect.signature(orchestrator.execute_with_hitl)
        params = list(sig.parameters.keys())
        assert "threshold" in params or any(
            p.name == "threshold" for p in sig.parameters.values()
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_hitl_confidence")
class TestOrchestratorHITLConfidenceChecking:
    """Test suite for confidence-based HITL triggers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_high_confidence_proceeds_without_approval(self):
        """GIVEN results with confidence >= threshold
        WHEN executing with HITL
        THEN it should proceed without requesting approval
        """
        orchestrator = Orchestrator()

        # Create mock decomposition
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        # Mock coordinator to return high-confidence result
        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.95,  # High confidence
                    requires_approval=False,
                ),
            ]

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
            )

        # Should not require approval
        assert all(not r.requires_approval for r in results)

    @pytest.mark.asyncio
    async def test_low_confidence_marks_requires_approval(self):
        """GIVEN results with confidence < threshold
        WHEN executing with HITL
        THEN it should mark results as requiring approval
        """
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.5,  # Low confidence
                ),
            ]

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
            )

        # Low-confidence result should be marked as requiring approval
        low_confidence_results = [r for r in results if r.confidence < 0.7]
        assert all(r.requires_approval for r in low_confidence_results)

    @pytest.mark.asyncio
    async def test_custom_threshold_respected(self):
        """GIVEN a custom threshold
        WHEN executing with HITL
        THEN the custom threshold should be used for approval determination
        """
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.75,  # Between 0.7 and 0.9
                ),
            ]

            # With threshold 0.7, should NOT require approval
            results_70 = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
            )
            assert not results_70[0].requires_approval

            # With threshold 0.9, should require approval
            results_90 = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.9,
            )
            assert results_90[0].requires_approval


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_hitl_approval_reason")
class TestOrchestratorHITLApprovalReason:
    """Test suite for approval reason generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_reason_includes_confidence(self):
        """GIVEN low confidence result
        WHEN marking for approval
        THEN approval_reason should include confidence score
        """
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.45,
                ),
            ]

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
            )

        # Approval reason should explain why approval is needed
        assert results[0].approval_reason is not None
        assert "45" in results[0].approval_reason or "0.45" in results[0].approval_reason

    @pytest.mark.asyncio
    async def test_approval_reason_includes_threshold(self):
        """GIVEN low confidence result
        WHEN marking for approval
        THEN approval_reason should include threshold
        """
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.5,
                ),
            ]

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.8,
            )

        # Approval reason should mention the threshold
        assert results[0].approval_reason is not None
        assert "80" in results[0].approval_reason or "0.8" in results[0].approval_reason


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_hitl_feature_flag")
class TestOrchestratorHITLFeatureFlag:
    """Test suite for HITL feature flag gating."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hitl_respects_feature_flag(self):
        """GIVEN agent_hitl feature flag disabled
        WHEN executing with HITL
        THEN it should skip HITL checks and execute normally
        """
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with (
            patch.object(orchestrator.coordinator, "execute_all") as mock_execute,
            patch(
                "mcp_server_langgraph.agents.orchestrator.feature_flags"
            ) as mock_flags,
        ):
            mock_flags.enable_agent_hitl = False
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.3,  # Very low confidence
                ),
            ]

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
            )

        # With flag disabled, should NOT mark for approval despite low confidence
        assert not results[0].requires_approval


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_hitl_callback")
class TestOrchestratorHITLCallback:
    """Test suite for approval callback handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_approval_required_callback_called(self):
        """GIVEN an on_approval_required callback
        WHEN low confidence result occurs
        THEN the callback should be invoked with approval details
        """
        orchestrator = Orchestrator()
        callback = AsyncMock()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.4,
                ),
            ]

            await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
                on_approval_required=callback,
            )

        # Callback should have been called with approval request details
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["task_id"] == "subtask-1"
        assert call_args["confidence"] == 0.4
        assert call_args["threshold"] == 0.7

    @pytest.mark.asyncio
    async def test_callback_not_called_for_high_confidence(self):
        """GIVEN high confidence results
        WHEN executing with HITL
        THEN the callback should NOT be invoked
        """
        orchestrator = Orchestrator()
        callback = AsyncMock()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Test instructions",
                ),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="Result output",
                    confidence=0.95,  # High confidence
                ),
            ]

            await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
                on_approval_required=callback,
            )

        # Callback should NOT be called
        callback.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_hitl_multiple")
class TestOrchestratorHITLMultipleSubtasks:
    """Test suite for HITL with multiple subtasks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_mixed_confidence_handled_correctly(self):
        """GIVEN multiple subtasks with mixed confidence
        WHEN executing with HITL
        THEN only low-confidence results should require approval
        """
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(task_id="subtask-1", title="Task 1", instructions="Test 1"),
                Subtask(task_id="subtask-2", title="Task 2", instructions="Test 2"),
                Subtask(task_id="subtask-3", title="Task 3", instructions="Test 3"),
            ],
            synthesis_instructions="Test synthesis",
        )

        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_execute.return_value = [
                SubagentResult(
                    task_id="subtask-1",
                    success=True,
                    output="High confidence result",
                    confidence=0.95,
                ),
                SubagentResult(
                    task_id="subtask-2",
                    success=True,
                    output="Low confidence result",
                    confidence=0.4,
                ),
                SubagentResult(
                    task_id="subtask-3",
                    success=True,
                    output="Medium confidence result",
                    confidence=0.75,
                ),
            ]

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
            )

        # Check each result
        result_map = {r.task_id: r for r in results}

        # High confidence - no approval needed
        assert not result_map["subtask-1"].requires_approval

        # Low confidence - approval needed
        assert result_map["subtask-2"].requires_approval
        assert result_map["subtask-2"].approval_reason is not None

        # Above threshold - no approval needed
        assert not result_map["subtask-3"].requires_approval
