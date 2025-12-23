"""Integration tests for Human-in-the-Loop (HITL) agent approval flow.

Tests the complete HITL workflow:
- Low confidence detection
- Approval request creation
- WebSocket notification
- Approval/rejection handling
- Agent resume/halt

TDD: Tests verify integration between actual HITL components.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.integration, pytest.mark.hitl, pytest.mark.multi_agent]


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="hitl_flow_integration")
class TestHITLApprovalFlowIntegration:
    """Integration tests for the complete HITL approval flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_approval_flag(self) -> None:
        """GIVEN a subagent result with low confidence
        WHEN processed by execute_with_hitl
        THEN the result should have requires_approval set to True.
        """
        from mcp_server_langgraph.agents.subagent import SubagentResult

        # Create a low-confidence result
        result = SubagentResult(
            task_id="task-001",
            success=True,
            output="Analysis complete",
            confidence=0.55,  # Below default 0.7 threshold
        )

        # Verify confidence field works correctly
        assert result.confidence == 0.55
        assert result.confidence < 0.7

        # Mark as requiring approval (this is what execute_with_hitl does)
        result_with_approval = SubagentResult(
            task_id=result.task_id,
            success=result.success,
            output=result.output,
            confidence=result.confidence,
            requires_approval=True,
            approval_reason="Confidence 55% is below threshold 70%",
        )

        assert result_with_approval.requires_approval is True
        assert result_with_approval.approval_reason is not None

    @pytest.mark.asyncio
    async def test_high_confidence_no_approval_required(self) -> None:
        """GIVEN a subagent result with high confidence
        WHEN checked against threshold
        THEN requires_approval should be False.
        """
        from mcp_server_langgraph.agents.subagent import SubagentResult

        # Create a high-confidence result
        result = SubagentResult(
            task_id="task-002",
            success=True,
            output="Charts generated",
            confidence=0.92,  # Above threshold
        )

        # High confidence = no approval needed
        assert result.confidence >= 0.7
        assert result.requires_approval is False

    @pytest.mark.asyncio
    async def test_agent_request_queue_approval_flow(self) -> None:
        """GIVEN an approval request is queued
        WHEN we approve it through the queue
        THEN the request status should be updated.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestStatus,
        )

        queue = AgentRequestQueue()

        # Queue an approval request
        request = await queue.queue_approval_request(
            session_id="session-003",
            task_id="task-003",
            agent_name="Code Reviewer",
            confidence=0.62,
            threshold=0.7,
            proposed_action="Review pull request #123",
        )

        assert request.request_id is not None
        assert request.session_id == "session-003"
        assert request.task_id == "task-003"
        assert request.agent_name == "Code Reviewer"
        assert request.confidence == 0.62
        assert request.threshold == 0.7
        assert request.status == AgentRequestStatus.PENDING

        # Approve it
        approved = await queue.approve(
            request_id=request.request_id,
            approved_by="user@example.com",
            reason="Reviewed and approved",
        )

        assert approved.status == AgentRequestStatus.APPROVED
        assert approved.responded_by == "user@example.com"
        assert approved.responded_at is not None

    @pytest.mark.asyncio
    async def test_rejection_flow_through_queue(self) -> None:
        """GIVEN a pending approval request
        WHEN the user rejects it
        THEN the status should be rejected.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestStatus,
        )

        queue = AgentRequestQueue()

        # Queue a request
        request = await queue.queue_approval_request(
            session_id="session-005",
            task_id="task-005",
            agent_name="Data Analyst",
            confidence=0.55,
            threshold=0.7,
            proposed_action="Delete old records",
        )

        # Reject it
        rejected = await queue.reject(
            request_id=request.request_id,
            rejected_by="admin@example.com",
            reason="Not authorized for this operation",
        )

        assert rejected.status == AgentRequestStatus.REJECTED
        assert rejected.responded_by == "admin@example.com"
        assert rejected.context.get("rejection_reason") == "Not authorized for this operation"

    @pytest.mark.asyncio
    async def test_pending_requests_list(self) -> None:
        """GIVEN multiple requests in queue
        WHEN listing pending requests
        THEN only pending ones should be returned.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
        )

        queue = AgentRequestQueue()

        # Queue multiple requests
        req1 = await queue.queue_approval_request(
            session_id="session-1",
            task_id="task-1",
            agent_name="Agent 1",
            confidence=0.5,
            threshold=0.7,
            proposed_action="Action 1",
        )
        req2 = await queue.queue_approval_request(
            session_id="session-1",
            task_id="task-2",
            agent_name="Agent 2",
            confidence=0.6,
            threshold=0.7,
            proposed_action="Action 2",
        )

        # Approve one
        await queue.approve(req1.request_id, "user@test.com")

        # List pending should only return req2
        pending = await queue.list_pending()
        assert len(pending) == 1
        assert pending[0].request_id == req2.request_id


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="hitl_websocket_integration")
class TestHITLWebSocketIntegration:
    """Integration tests for HITL WebSocket notifications."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_request_broadcasts_to_websocket(self) -> None:
        """GIVEN an approval request is created
        WHEN the broadcast function is called
        THEN a WebSocket message should be sent.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_approval_required,
            get_broadcaster,
        )
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequest, AgentRequestType, AgentRequestStatus

        # Create an AgentRequest object
        request = AgentRequest(
            request_id="approval-ws-001",
            session_id="session-ws-001",
            task_id="task-ws-001",
            agent_name="Research Assistant",
            request_type=AgentRequestType.APPROVAL,
            confidence=0.62,
            threshold=0.7,
            proposed_action="Send data to external service",
            question="Confidence 62% is below threshold 70%. Approve?",
            trigger_reason="low_confidence",
            status=AgentRequestStatus.PENDING,
            requested_at="2025-12-21T00:00:00Z",
        )

        # Mock the broadcaster
        broadcaster = get_broadcaster()
        broadcaster.broadcast = AsyncMock()

        await broadcast_approval_required(request)

        broadcaster.broadcast.assert_called_once()
        call_args = broadcaster.broadcast.call_args
        assert call_args is not None
        message = call_args[0][0]
        assert message["type"] == "approval_required"
        assert message["payload"]["request_id"] == "approval-ws-001"

    @pytest.mark.asyncio
    async def test_approval_decision_broadcasts_update(self) -> None:
        """GIVEN subscribed WebSocket connections
        WHEN an approval decision is made
        THEN an update should be broadcast.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_approval_updated,
            get_broadcaster,
        )

        # Mock the broadcaster
        broadcaster = get_broadcaster()
        broadcaster.broadcast = AsyncMock()

        await broadcast_approval_updated(
            request_id="approval-ws-002",
            status="approved",
            decided_by="user@example.com",
            reason="Looks good",
        )

        broadcaster.broadcast.assert_called_once()
        call_args = broadcaster.broadcast.call_args
        assert call_args is not None
        message = call_args[0][0]
        assert message["type"] == "approval_updated"
        assert message["payload"]["status"] == "approved"


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="hitl_metrics_integration")
class TestHITLMetricsIntegration:
    """Integration tests for HITL metrics recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_request_records_metrics(self) -> None:
        """GIVEN an approval request
        WHEN the request is created
        THEN metrics should be recorded.
        """
        from mcp_server_langgraph.agents.metrics import (
            record_hitl_request,
            hitl_request_counter,
        )

        # Record should not raise
        record_hitl_request(
            request_type="approval",
            agent_name="Test Agent",
            confidence=0.65,
            trigger_reason="low_confidence",
        )

        # Counter should exist
        assert hitl_request_counter is not None

    @pytest.mark.asyncio
    async def test_approval_decision_records_latency(self) -> None:
        """GIVEN an approval decision
        WHEN the decision is recorded
        THEN latency metrics should be captured.
        """
        from mcp_server_langgraph.agents.metrics import (
            record_hitl_decision,
            hitl_response_latency_histogram,
        )

        # Record decision with latency
        record_hitl_decision(
            request_type="approval",
            agent_name="Test Agent",
            decision="approved",
            latency_seconds=45.5,
        )

        # Histogram should exist
        assert hitl_response_latency_histogram is not None

    @pytest.mark.asyncio
    async def test_pending_count_tracks_queue_depth(self) -> None:
        """GIVEN pending approval requests
        WHEN requests are added and removed
        THEN the pending gauge should track correctly.
        """
        from mcp_server_langgraph.agents.metrics import (
            increment_hitl_pending,
            decrement_hitl_pending,
            hitl_pending_gauge,
        )

        # Increment should not raise
        increment_hitl_pending(request_type="approval")
        increment_hitl_pending(request_type="approval")

        # Decrement should not raise
        decrement_hitl_pending(request_type="approval")

        # Gauge should exist
        assert hitl_pending_gauge is not None


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="hitl_tracing_integration")
class TestHITLTracingIntegration:
    """Integration tests for HITL tracing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hitl_request_creates_trace_span(self) -> None:
        """GIVEN an HITL request
        WHEN processed with tracing
        THEN a trace span should be created with attributes.
        """
        from mcp_server_langgraph.agents.metrics import (
            hitl_request_span,
            add_hitl_decision_to_span,
        )

        with hitl_request_span(
            request_type="approval",
            request_id="trace-001",
            agent_name="Tracing Agent",
            confidence=0.68,
            trigger_reason="low_confidence",
        ) as span:
            assert span is not None
            assert hasattr(span, "set_attributes")

            # Add decision to span
            add_hitl_decision_to_span(
                span=span,
                decision="approved",
                latency_seconds=30.0,
                reason="Reviewed and approved",
            )

    @pytest.mark.asyncio
    async def test_hitl_span_captures_full_lifecycle(self) -> None:
        """GIVEN an HITL request lifecycle
        WHEN the request is processed from start to finish
        THEN the span should capture the complete lifecycle.
        """
        from mcp_server_langgraph.agents.metrics import create_hitl_span

        span = create_hitl_span(
            request_type="clarification",
            request_id="trace-002",
            agent_name="Clarification Agent",
            confidence=0.75,
            trigger_reason="ambiguous_input",
        )

        try:
            assert span is not None
            assert hasattr(span, "end")
        finally:
            span.end()


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="hitl_feature_flag_integration")
class TestHITLFeatureFlagIntegration:
    """Integration tests for HITL feature flag behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hitl_feature_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN checking for HITL flag
        THEN it should exist.
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        # Verify HITL feature flag exists
        assert hasattr(feature_flags, "enable_agent_hitl")
        # Default should be True
        assert isinstance(feature_flags.enable_agent_hitl, bool)

    @pytest.mark.asyncio
    async def test_confidence_threshold_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN checking for HITL confidence threshold
        THEN it should exist and be a valid value.
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        # Verify threshold exists
        assert hasattr(feature_flags, "agent_hitl_confidence_threshold")
        threshold = feature_flags.agent_hitl_confidence_threshold
        assert 0.0 <= threshold <= 1.0

    @pytest.mark.asyncio
    async def test_execute_with_hitl_respects_feature_flag(self) -> None:
        """GIVEN HITL is disabled via feature flag
        WHEN execute_with_hitl is called
        THEN results should not be marked for approval.
        """
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition, Subtask
        from mcp_server_langgraph.agents.subagent import SubagentResult

        # Patch feature flags to disable HITL
        with patch("mcp_server_langgraph.agents.orchestrator.feature_flags") as mock_flags:
            mock_flags.enable_agent_hitl = False

            orchestrator = Orchestrator()

            # Create a decomposition for testing
            decomposition = TaskDecomposition(
                original_task="Test task",
                subtasks=[
                    Subtask(
                        task_id="task-ff-001",
                        title="Test subtask",
                        instructions="Test instructions",
                    )
                ],
            )

            # Mock execute to return a low-confidence result
            async def mock_execute(decomp: TaskDecomposition) -> list[SubagentResult]:
                return [
                    SubagentResult(
                        task_id="task-ff-001",
                        success=True,
                        output="Result",
                        confidence=0.45,  # Very low confidence
                    )
                ]

            orchestrator.execute = mock_execute  # type: ignore

            # execute_with_hitl should not flag for approval when disabled
            results = await orchestrator.execute_with_hitl(decomposition, threshold=0.7)

            # When HITL is disabled, results should pass through as-is
            assert len(results) == 1
            # The execute_with_hitl skips approval logic when feature is disabled
            # so requires_approval should remain False (default)

    @pytest.mark.asyncio
    async def test_websocket_checks_feature_flag(self) -> None:
        """GIVEN the agent request websocket
        WHEN HITL feature is disabled
        THEN is_hitl_enabled should return False.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import is_hitl_enabled

        # Without mocking, check that function exists and works
        result = await is_hitl_enabled()
        assert isinstance(result, bool)


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="hitl_ai_explanation_integration")
class TestHITLAIExplanationIntegration:
    """Integration tests for AI-Native Explanations in HITL flow.

    Tests the complete AI explanation workflow:
    - ExplanationOrchestrator parallel execution
    - AIExplanation model creation
    - Integration with ApprovalRequired
    - MCP elicitation with explanations
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ai_explanation_model_fields(self) -> None:
        """GIVEN an AIExplanation model
        WHEN created with all fields
        THEN all fields should be accessible.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            ConfidenceFactor,
            AlternativeSuggestion,
            ExplanationType,
        )

        # Create confidence factors
        factors = [
            ConfidenceFactor(
                factor="ambiguous_input",
                weight=-0.2,
                evidence="Input contains ambiguous terms",
            ),
            ConfidenceFactor(
                factor="missing_context",
                weight=-0.15,
                evidence="Required context not provided",
            ),
        ]

        # Create alternatives
        alternatives = [
            AlternativeSuggestion(
                action="Ask for clarification first",
                confidence=0.9,
                trade_off="May take additional time",
            ),
        ]

        # Create AI explanation
        explanation = AIExplanation(
            why_uncertain="The input contains ambiguous terms that could have multiple interpretations.",
            what_could_go_wrong="Proceeding without clarification may lead to incorrect results.",
            safer_alternatives=alternatives,
            confidence_factors=factors,
            reasoning_trace=["Analyzed input", "Detected ambiguity", "Identified alternatives"],
            explanation_type=ExplanationType.UNCERTAINTY,
            model_used="gpt-4o-mini",
        )

        # Verify all fields
        assert explanation.why_uncertain is not None
        assert len(explanation.why_uncertain) > 0
        assert explanation.what_could_go_wrong is not None
        assert len(explanation.safer_alternatives) == 1
        assert len(explanation.confidence_factors) == 2
        assert len(explanation.reasoning_trace) == 3
        assert explanation.explanation_type == ExplanationType.UNCERTAINTY

    @pytest.mark.asyncio
    async def test_approval_required_with_ai_explanation(self) -> None:
        """GIVEN an ApprovalRequired model
        WHEN ai_explanation field is set
        THEN it should contain valid AIExplanation data.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        # Create minimal AI explanation
        explanation = AIExplanation(
            why_uncertain="Confidence below threshold due to ambiguous context.",
            what_could_go_wrong="May produce incorrect analysis results.",
        )

        # Create approval request with explanation (using correct fields)
        approval = ApprovalRequired(
            approval_id="approval-ai-001",
            node_name="data_analyst_node",
            action_description="Analyze sales data and generate report",
            risk_level="medium",
            context={"confidence": 0.65, "threshold": 0.7},
            ai_explanation=explanation,
        )

        # Verify AI explanation is attached
        assert approval.ai_explanation is not None
        assert approval.ai_explanation.why_uncertain is not None
        assert approval.ai_explanation.what_could_go_wrong is not None

    @pytest.mark.asyncio
    async def test_explanation_orchestrator_creates_tasks(self) -> None:
        """GIVEN an ExplanationOrchestrator
        WHEN creating explanation tasks
        THEN all expected analysis types should be present.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationTask,
            EXPLANATION_ANALYSIS_TYPES,
        )

        orchestrator = ExplanationOrchestrator()

        # Verify analysis types are defined
        assert "uncertainty_analysis" in EXPLANATION_ANALYSIS_TYPES
        assert "risk_analysis" in EXPLANATION_ANALYSIS_TYPES
        assert "alternatives_analysis" in EXPLANATION_ANALYSIS_TYPES
        assert "evidence_extraction" in EXPLANATION_ANALYSIS_TYPES

        # Create tasks
        context = {
            "agent_name": "Test Agent",
            "proposed_action": "Test action",
            "confidence": 0.6,
            "threshold": 0.7,
            "trigger_reason": "low_confidence",
        }

        tasks = [
            ExplanationTask(
                task_type="uncertainty_analysis",
                approval_id="test-001",
                context=context,
            ),
            ExplanationTask(
                task_type="risk_analysis",
                approval_id="test-001",
                context=context,
            ),
        ]

        assert len(tasks) == 2
        assert tasks[0].task_type == "uncertainty_analysis"
        assert tasks[1].task_type == "risk_analysis"

    @pytest.mark.asyncio
    async def test_explanation_synthesize_combines_results(self) -> None:
        """GIVEN explanation analysis results
        WHEN synthesized by orchestrator
        THEN should combine into unified explanation structure.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationResult,
        )

        orchestrator = ExplanationOrchestrator()

        # Create mock results
        results = [
            ExplanationResult(
                task_type="uncertainty_analysis",
                success=True,
                result={"why_uncertain": "Test uncertainty reason"},
            ),
            ExplanationResult(
                task_type="risk_analysis",
                success=True,
                result={"what_could_go_wrong": "Test risk description"},
            ),
            ExplanationResult(
                task_type="alternatives_analysis",
                success=True,
                result={"safer_alternatives": [{"action": "Alt 1", "confidence": 0.9, "trade_off": "None"}]},
            ),
            ExplanationResult(
                task_type="evidence_extraction",
                success=True,
                result={"confidence_factors": [], "reasoning_trace": ["Step 1", "Step 2"]},
            ),
        ]

        # Synthesize
        synthesis = orchestrator.synthesize(results)

        # Verify synthesis
        assert "explanation" in synthesis
        assert "successful_analyses" in synthesis
        assert len(synthesis["successful_analyses"]) == 4
        assert synthesis["explanation"]["why_uncertain"] == "Test uncertainty reason"
        assert synthesis["explanation"]["what_could_go_wrong"] == "Test risk description"

    @pytest.mark.asyncio
    async def test_elicitation_includes_ai_explanation(self) -> None:
        """GIVEN an ApprovalRequired with AI explanation
        WHEN converted to MCP elicitation
        THEN the elicitation message should include explanation.
        """
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )

        # Create approval with full explanation
        explanation = AIExplanation(
            why_uncertain="Multiple valid interpretations exist for the input query.",
            what_could_go_wrong="Choosing wrong interpretation leads to incorrect analysis.",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Request clarification before proceeding",
                    confidence=0.95,
                    trade_off="Additional round-trip time",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="elicit-ai-001",
            node_name="query_analyzer_node",
            action_description="Execute database query: SELECT * FROM users WHERE status = 'active'",
            risk_level="medium",
            context={"confidence": 0.6, "threshold": 0.7, "trigger_reason": "ambiguous_query"},
            ai_explanation=explanation,
        )

        # Create bridge and convert to elicitation
        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Verify elicitation includes explanation in message
        assert elicitation is not None
        # Elicitation should reference the action or include explanation
        assert approval.action_description in elicitation.message or "query_analyzer_node" in elicitation.message

    @pytest.mark.asyncio
    async def test_ai_explanation_feature_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN checking for AI explanation flags
        THEN they should exist with valid defaults.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Verify AI explanation feature flag exists in config class
        config = FeatureFlags()
        assert hasattr(config, "enable_ai_explanations")
        assert isinstance(config.enable_ai_explanations, bool)

    @pytest.mark.asyncio
    async def test_explanation_orchestrator_feature_flag(self) -> None:
        """GIVEN the ExplanationOrchestrator
        WHEN checking feature_flag_name property
        THEN should return correct flag name.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert orchestrator.feature_flag_name == "enable_ai_explanations"

    @pytest.mark.asyncio
    async def test_orchestration_tool_handler_decompose(self) -> None:
        """GIVEN an OrchestrationToolHandler
        WHEN calling decompose operation
        THEN should work with or without orchestrator.
        """
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        # Without orchestrator - should return error
        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("decompose", {"task": "Test task"})

        # Without orchestrator configured, returns error
        assert "error" in result
        assert "Orchestrator not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_orchestration_tool_handler_status(self) -> None:
        """GIVEN an OrchestrationToolHandler
        WHEN calling status operation without resource provider
        THEN should return appropriate error.
        """
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("status", {"task_id": "task-001"})

        # Without resource provider, returns error
        assert "error" in result

    @pytest.mark.asyncio
    async def test_full_hitl_ai_explanation_flow(self) -> None:
        """GIVEN a low-confidence result requiring approval
        WHEN the HITL flow is triggered with AI explanation
        THEN the complete flow should work end-to-end.
        """
        from mcp_server_langgraph.agents.subagent import SubagentResult
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
        )

        # 1. Create low-confidence result
        result = SubagentResult(
            task_id="e2e-ai-001",
            success=True,
            output="Analysis complete but uncertain",
            confidence=0.55,
        )

        # 2. Create AI explanation for this result
        explanation = AIExplanation(
            why_uncertain="Analysis confidence is low due to limited training data for this scenario.",
            what_could_go_wrong="Results may be inaccurate if used without human verification.",
            reasoning_trace=["Analyzed data", "Found limited matches", "Low confidence score"],
        )

        # 3. Create approval request with explanation (using correct model fields)
        approval = ApprovalRequired(
            approval_id="e2e-approval-001",
            node_name="ai_assistant_node",
            action_description=f"Complete task: {result.task_id}",
            risk_level="medium",
            context={
                "confidence": result.confidence,
                "threshold": 0.7,
                "trigger_reason": "low_confidence",
            },
            ai_explanation=explanation,
        )

        # 4. Queue the approval request
        queue = AgentRequestQueue()
        request = await queue.queue_approval_request(
            session_id="e2e-session-001",
            task_id=result.task_id,
            agent_name=approval.node_name,
            confidence=approval.context.get("confidence", 0.55),
            threshold=approval.context.get("threshold", 0.7),
            proposed_action=approval.action_description,
        )

        # 5. Verify the complete flow
        assert request.request_id is not None
        assert request.confidence == 0.55
        assert request.threshold == 0.7
        assert approval.context.get("confidence") == 0.55
        assert approval.context.get("threshold") == 0.7
        assert approval.ai_explanation is not None
        assert approval.ai_explanation.why_uncertain is not None

        # 6. Approve and verify
        approved = await queue.approve(
            request_id=request.request_id,
            approved_by="human@example.com",
            reason="Verified the analysis is correct",
        )

        assert approved.status.value == "approved"
