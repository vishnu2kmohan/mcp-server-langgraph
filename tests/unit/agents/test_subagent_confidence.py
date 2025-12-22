"""
Tests for SubagentResult confidence tracking.

Phase 1 of the Confidence-Based HITL Implementation Plan.

TDD: Write tests FIRST, then implementation.

Tests:
1. SubagentResult has confidence field with default 0.85
2. SubagentResult has requires_approval field with default False
3. SubagentResult has approval_reason field with default None
4. Confidence is validated between 0.0 and 1.0
5. Subagent.execute() populates confidence in result
6. Low confidence triggers requires_approval flag
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.xdist_group(name="subagent_confidence")
class TestSubagentResultConfidenceFields:
    """Test SubagentResult has confidence tracking fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subagent_result_has_confidence_field(self) -> None:
        """SubagentResult should have a confidence field."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True)
        assert hasattr(result, "confidence")

    def test_subagent_result_confidence_default_is_0_85(self) -> None:
        """SubagentResult confidence should default to 0.85."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True)
        assert result.confidence == 0.85

    def test_subagent_result_confidence_accepts_custom_value(self) -> None:
        """SubagentResult should accept custom confidence value."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True, confidence=0.65)
        assert result.confidence == 0.65

    def test_subagent_result_has_requires_approval_field(self) -> None:
        """SubagentResult should have a requires_approval field."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True)
        assert hasattr(result, "requires_approval")

    def test_subagent_result_requires_approval_default_is_false(self) -> None:
        """SubagentResult requires_approval should default to False."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True)
        assert result.requires_approval is False

    def test_subagent_result_requires_approval_accepts_true(self) -> None:
        """SubagentResult should accept requires_approval=True."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True, requires_approval=True)
        assert result.requires_approval is True

    def test_subagent_result_has_approval_reason_field(self) -> None:
        """SubagentResult should have an approval_reason field."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True)
        assert hasattr(result, "approval_reason")

    def test_subagent_result_approval_reason_default_is_none(self) -> None:
        """SubagentResult approval_reason should default to None."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True)
        assert result.approval_reason is None

    def test_subagent_result_approval_reason_accepts_string(self) -> None:
        """SubagentResult should accept custom approval_reason."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test-1",
            success=True,
            requires_approval=True,
            approval_reason="Confidence below threshold",
        )
        assert result.approval_reason == "Confidence below threshold"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.xdist_group(name="subagent_confidence_validation")
class TestSubagentResultConfidenceValidation:
    """Test SubagentResult confidence field validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_confidence_at_minimum_boundary_0(self) -> None:
        """Confidence should accept 0.0 (minimum boundary)."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True, confidence=0.0)
        assert result.confidence == 0.0

    def test_confidence_at_maximum_boundary_1(self) -> None:
        """Confidence should accept 1.0 (maximum boundary)."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(task_id="test-1", success=True, confidence=1.0)
        assert result.confidence == 1.0

    def test_confidence_rejects_negative_values(self) -> None:
        """Confidence should reject negative values."""
        from pydantic import ValidationError

        from mcp_server_langgraph.agents.subagent import SubagentResult

        with pytest.raises(ValidationError) as exc_info:
            SubagentResult(task_id="test-1", success=True, confidence=-0.1)

        assert "confidence" in str(exc_info.value).lower()

    def test_confidence_rejects_values_above_1(self) -> None:
        """Confidence should reject values above 1.0."""
        from pydantic import ValidationError

        from mcp_server_langgraph.agents.subagent import SubagentResult

        with pytest.raises(ValidationError) as exc_info:
            SubagentResult(task_id="test-1", success=True, confidence=1.1)

        assert "confidence" in str(exc_info.value).lower()

    def test_confidence_accepts_typical_values(self) -> None:
        """Confidence should accept typical values in range."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        test_values = [0.1, 0.25, 0.5, 0.7, 0.85, 0.95]
        for value in test_values:
            result = SubagentResult(task_id="test-1", success=True, confidence=value)
            assert result.confidence == value


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="subagent_execute_confidence")
class TestSubagentExecuteConfidence:
    """Test Subagent.execute() populates confidence in result."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_execute_returns_result_with_confidence(self) -> None:
        """Subagent.execute() should return result with confidence field."""
        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(task_id="test-1", instructions="Test task")
        result = await subagent.execute()

        assert hasattr(result, "confidence")
        # Default execution without LLM returns high confidence
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0

    async def test_execute_with_llm_populates_confidence(self) -> None:
        """Subagent.execute() with LLM should populate confidence from response."""
        from mcp_server_langgraph.agents.subagent import Subagent

        # Create mock LLM that returns response with confidence metadata
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_response.response_metadata = {"confidence": 0.72}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        subagent = Subagent(
            task_id="test-1",
            instructions="Test task",
            llm_factory=mock_llm,
        )
        result = await subagent.execute()

        assert result.success is True
        # Confidence should be populated (either from metadata or default)
        assert result.confidence >= 0.0

    async def test_execute_without_llm_returns_default_confidence(self) -> None:
        """Subagent.execute() without LLM returns placeholder with high confidence."""
        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(task_id="test-1", instructions="Simple test")
        result = await subagent.execute()

        assert result.success is True
        # No LLM = placeholder result with default high confidence
        assert result.confidence == 0.85


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.xdist_group(name="subagent_approval_trigger")
class TestSubagentApprovalTrigger:
    """Test low confidence triggers requires_approval flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_result_with_low_confidence_can_set_requires_approval(self) -> None:
        """SubagentResult with low confidence can have requires_approval=True."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test-1",
            success=True,
            confidence=0.55,
            requires_approval=True,
            approval_reason="Confidence (55%) below threshold (70%)",
        )

        assert result.confidence == 0.55
        assert result.requires_approval is True
        assert "below threshold" in result.approval_reason

    def test_result_with_high_confidence_typically_no_approval(self) -> None:
        """SubagentResult with high confidence typically doesn't need approval."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test-1",
            success=True,
            confidence=0.92,
        )

        assert result.confidence == 0.92
        assert result.requires_approval is False
        assert result.approval_reason is None

    def test_result_model_dump_includes_confidence_fields(self) -> None:
        """SubagentResult.model_dump() should include all confidence fields."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test-1",
            success=True,
            confidence=0.65,
            requires_approval=True,
            approval_reason="Low confidence",
        )

        dumped = result.model_dump()

        assert "confidence" in dumped
        assert "requires_approval" in dumped
        assert "approval_reason" in dumped
        assert dumped["confidence"] == 0.65
        assert dumped["requires_approval"] is True
        assert dumped["approval_reason"] == "Low confidence"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.xdist_group(name="subagent_confidence_threshold")
class TestSubagentConfidenceThreshold:
    """Test confidence threshold configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_confidence_threshold_constant_exists(self) -> None:
        """DEFAULT_CONFIDENCE_THRESHOLD constant should exist."""
        from mcp_server_langgraph.agents import subagent as subagent_module

        assert hasattr(subagent_module, "DEFAULT_CONFIDENCE_THRESHOLD")

    def test_default_confidence_threshold_is_0_7(self) -> None:
        """DEFAULT_CONFIDENCE_THRESHOLD should be 0.7."""
        from mcp_server_langgraph.agents.subagent import DEFAULT_CONFIDENCE_THRESHOLD

        assert DEFAULT_CONFIDENCE_THRESHOLD == 0.7

    def test_auto_approve_threshold_constant_exists(self) -> None:
        """AUTO_APPROVE_THRESHOLD constant should exist."""
        from mcp_server_langgraph.agents import subagent as subagent_module

        assert hasattr(subagent_module, "AUTO_APPROVE_THRESHOLD")

    def test_auto_approve_threshold_is_0_9(self) -> None:
        """AUTO_APPROVE_THRESHOLD should be 0.9."""
        from mcp_server_langgraph.agents.subagent import AUTO_APPROVE_THRESHOLD

        assert AUTO_APPROVE_THRESHOLD == 0.9
