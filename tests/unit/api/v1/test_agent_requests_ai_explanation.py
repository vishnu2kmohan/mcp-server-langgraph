"""
Agent Request AI Explanation Integration Tests.

Tests for integrating ExplanationOrchestrator into the HITL request flow.
This ensures AI-generated explanations are included in approval requests
when the enable_ai_explanations feature flag is enabled.

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.hitl,
    pytest.mark.ai_explanations,
]


@pytest.mark.xdist_group(name="agent_request_ai_explanation")
class TestAgentRequestAIExplanationField:
    """Tests for AgentRequest model supporting AI explanation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_has_ai_explanation_field(self) -> None:
        """
        GIVEN the AgentRequest model
        WHEN checking its fields
        THEN should have optional ai_explanation field.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequest

        fields = AgentRequest.model_fields
        assert "ai_explanation" in fields, "AgentRequest should have ai_explanation field"

    def test_agent_request_ai_explanation_is_optional(self) -> None:
        """
        GIVEN the AgentRequest model
        WHEN creating without ai_explanation
        THEN should succeed with None.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestStatus,
            AgentRequestType,
        )

        request = AgentRequest(
            request_id="req_test123",
            session_id="session-1",
            task_id="task-1",
            agent_name="TestAgent",
            request_type=AgentRequestType.APPROVAL,
            question="Approve action?",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert request.ai_explanation is None

    def test_agent_request_accepts_ai_explanation(self) -> None:
        """
        GIVEN the AgentRequest model
        WHEN created with ai_explanation
        THEN should store the explanation.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestStatus,
            AgentRequestType,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="The input is ambiguous",
            what_could_go_wrong="Wrong files could be deleted",
        )

        request = AgentRequest(
            request_id="req_test123",
            session_id="session-1",
            task_id="task-1",
            agent_name="TestAgent",
            request_type=AgentRequestType.APPROVAL,
            question="Approve action?",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
            ai_explanation=explanation,
        )

        assert request.ai_explanation is not None
        assert request.ai_explanation.why_uncertain == "The input is ambiguous"

    def test_agent_request_serializes_ai_explanation(self) -> None:
        """
        GIVEN an AgentRequest with ai_explanation
        WHEN serialized to JSON
        THEN should include the explanation.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestStatus,
            AgentRequestType,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test uncertainty",
            what_could_go_wrong="Test risk",
        )

        request = AgentRequest(
            request_id="req_test123",
            session_id="session-1",
            task_id="task-1",
            agent_name="TestAgent",
            request_type=AgentRequestType.APPROVAL,
            question="Approve action?",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
            ai_explanation=explanation,
        )

        json_data = request.model_dump()
        assert "ai_explanation" in json_data
        assert json_data["ai_explanation"]["why_uncertain"] == "Test uncertainty"


@pytest.mark.xdist_group(name="agent_request_ai_explanation")
class TestQueueApprovalRequestWithExplanation:
    """Tests for queue_approval_request generating AI explanations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_queue_approval_request_generates_explanation_when_enabled(
        self,
    ) -> None:
        """
        GIVEN enable_ai_explanations feature flag is enabled
        WHEN queue_approval_request is called
        THEN should generate and attach AI explanation.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        queue = AgentRequestQueue()

        # Mock the ExplanationOrchestrator
        mock_explanation = AIExplanation(
            why_uncertain="Agent confidence is below threshold",
            what_could_go_wrong="Action may have unintended effects",
        )

        with patch(
            "mcp_server_langgraph.api.v1.agent_requests.feature_flags"
        ) as mock_ff:
            mock_ff.enable_ai_explanations = True

            # Patch at the source module, not where it's imported
            with patch(
                "mcp_server_langgraph.agents.explanation_orchestrator.CachedExplanationOrchestrator"
            ) as mock_orch_class:
                mock_orch = AsyncMock()
                mock_orch.generate_explanation_cached = AsyncMock(
                    return_value=mock_explanation
                )
                mock_orch_class.return_value = mock_orch

                request = await queue.queue_approval_request(
                    session_id="session-1",
                    task_id="task-1",
                    agent_name="TestAgent",
                    confidence=0.65,
                    threshold=0.7,
                    proposed_action="Delete files matching *.tmp",
                )

                # Verify explanation was generated and attached
                assert request.ai_explanation is not None
                assert request.ai_explanation.why_uncertain is not None

    @pytest.mark.asyncio
    async def test_queue_approval_request_skips_explanation_when_disabled(
        self,
    ) -> None:
        """
        GIVEN enable_ai_explanations feature flag is disabled
        WHEN queue_approval_request is called
        THEN should NOT generate AI explanation.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()

        with patch(
            "mcp_server_langgraph.api.v1.agent_requests.feature_flags"
        ) as mock_ff:
            mock_ff.enable_ai_explanations = False

            request = await queue.queue_approval_request(
                session_id="session-1",
                task_id="task-1",
                agent_name="TestAgent",
                confidence=0.65,
                threshold=0.7,
                proposed_action="Delete files",
            )

            # Should not have explanation when disabled
            assert request.ai_explanation is None

    @pytest.mark.asyncio
    async def test_queue_approval_request_handles_explanation_error_gracefully(
        self,
    ) -> None:
        """
        GIVEN enable_ai_explanations is enabled but orchestrator fails
        WHEN queue_approval_request is called
        THEN should still create request with None explanation.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()

        with patch(
            "mcp_server_langgraph.api.v1.agent_requests.feature_flags"
        ) as mock_ff:
            mock_ff.enable_ai_explanations = True

            # Patch at the source module, not where it's imported
            with patch(
                "mcp_server_langgraph.agents.explanation_orchestrator.CachedExplanationOrchestrator"
            ) as mock_orch_class:
                mock_orch = AsyncMock()
                mock_orch.generate_explanation_cached = AsyncMock(
                    side_effect=Exception("LLM service unavailable")
                )
                mock_orch_class.return_value = mock_orch

                # Should not raise, should gracefully handle error
                request = await queue.queue_approval_request(
                    session_id="session-1",
                    task_id="task-1",
                    agent_name="TestAgent",
                    confidence=0.65,
                    threshold=0.7,
                    proposed_action="Delete files",
                )

                # Request should still be created, just without explanation
                assert request.request_id is not None
                assert request.ai_explanation is None

    @pytest.mark.asyncio
    async def test_queue_approval_request_passes_reasoning_trace_to_orchestrator(
        self,
    ) -> None:
        """
        GIVEN context contains reasoning_trace
        WHEN queue_approval_request is called with AI explanations enabled
        THEN should pass reasoning_trace to ExplanationOrchestrator.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        queue = AgentRequestQueue()

        mock_explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )

        with patch(
            "mcp_server_langgraph.api.v1.agent_requests.feature_flags"
        ) as mock_ff:
            mock_ff.enable_ai_explanations = True

            # Patch at the source module, not where it's imported
            with patch(
                "mcp_server_langgraph.agents.explanation_orchestrator.CachedExplanationOrchestrator"
            ) as mock_orch_class:
                mock_orch = AsyncMock()
                mock_orch.generate_explanation_cached = AsyncMock(
                    return_value=mock_explanation
                )
                mock_orch_class.return_value = mock_orch

                reasoning_trace = [
                    "Step 1: Matched 50 files",
                    "Step 2: Uncertain about scope",
                ]

                await queue.queue_approval_request(
                    session_id="session-1",
                    task_id="task-1",
                    agent_name="TestAgent",
                    confidence=0.65,
                    threshold=0.7,
                    proposed_action="Delete files",
                    context={"reasoning_trace": reasoning_trace},
                )

                # Verify reasoning_trace was passed
                call_kwargs = mock_orch.generate_explanation_cached.call_args.kwargs
                assert call_kwargs.get("reasoning_trace") == reasoning_trace


@pytest.mark.xdist_group(name="agent_request_ai_explanation")
class TestQueueApprovalRequestWithTriggerReason:
    """Tests for queue_approval_request with trigger_reason support."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_queue_approval_request_accepts_trigger_reason(self) -> None:
        """
        GIVEN queue_approval_request
        WHEN called with trigger_reason parameter
        THEN should store trigger_reason in request.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()

        with patch(
            "mcp_server_langgraph.api.v1.agent_requests.feature_flags"
        ) as mock_ff:
            mock_ff.enable_ai_explanations = False

            request = await queue.queue_approval_request(
                session_id="session-1",
                task_id="task-1",
                agent_name="TestAgent",
                confidence=0.65,
                threshold=0.7,
                proposed_action="Delete files",
                trigger_reason="low_confidence",
            )

            assert request.trigger_reason == "low_confidence"

    @pytest.mark.asyncio
    async def test_queue_approval_request_defaults_trigger_reason_to_low_confidence(
        self,
    ) -> None:
        """
        GIVEN queue_approval_request
        WHEN called without trigger_reason parameter
        THEN should default to 'low_confidence'.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()

        with patch(
            "mcp_server_langgraph.api.v1.agent_requests.feature_flags"
        ) as mock_ff:
            mock_ff.enable_ai_explanations = False

            request = await queue.queue_approval_request(
                session_id="session-1",
                task_id="task-1",
                agent_name="TestAgent",
                confidence=0.65,
                threshold=0.7,
                proposed_action="Delete files",
            )

            assert request.trigger_reason == "low_confidence"
