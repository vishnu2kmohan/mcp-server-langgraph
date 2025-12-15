"""
EU AI Act Audit Logging Compliance Tests.

Validates compliance with EU Artificial Intelligence Act:
- Article 12: Record-keeping requirements for high-risk AI
- Article 19: Quality management system
- Article 72: Post-market monitoring
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.audit.constants import Regulation, RetentionDays
from mcp_server_langgraph.audit.models import (
    AIOperationDetails,
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService

pytestmark = pytest.mark.compliance


@pytest.mark.compliance
@pytest.mark.eu_ai_act
@pytest.mark.xdist_group(name="compliance_eu_ai_act")
class TestEUAIActRecordKeeping:
    """Article 12: Record-keeping requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_operation_logged(self) -> None:
        """GIVEN AI operation WHEN executed THEN logged per Article 12."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_INVOKE,
            actor=AuditActor(actor_id="user:analyst", actor_type="user"),
            resource_type="ai_model",
            resource_id="risk-assessment-v2",
            action="AI inference request",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.EU_AI_ACT],
            ai_operation=AIOperationDetails(
                model_id="risk-assessment-v2",
                provider="openai",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=250.0,
                decision_type="high_risk",
            ),
        )

        assert event.category == AuditEventCategory.AI_OPERATION
        assert event.ai_operation is not None
        assert event.ai_operation.model_id == "risk-assessment-v2"

    def test_ai_operation_includes_model_details(self) -> None:
        """GIVEN AI operation THEN model details logged per Article 12."""
        ai_details = AIOperationDetails(
            model_id="gpt-4-turbo",
            provider="openai",
            model_version="2024-01-01",
            input_tokens=500,
            output_tokens=200,
            latency_ms=150.0,
            decision_type="recommendation",
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_INVOKE,
            actor=AuditActor(actor_id="user:analyst", actor_type="user"),
            resource_type="ai_model",
            resource_id="gpt-4-turbo",
            action="Generate recommendation",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            ai_operation=ai_details,
        )

        assert event.ai_operation.provider == "openai"
        assert event.ai_operation.model_version == "2024-01-01"

    def test_high_risk_ai_flagged(self) -> None:
        """GIVEN high-risk AI operation THEN flagged per Article 12."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_INVOKE,
            actor=AuditActor(actor_id="system:hr-screening", actor_type="service"),
            resource_type="ai_model",
            resource_id="candidate-screening-v1",
            action="Screen job candidate",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.EU_AI_ACT],
            ai_operation=AIOperationDetails(
                model_id="candidate-screening-v1",
                provider="anthropic",
                decision_type="high_risk",  # Employment decisions are high-risk
            ),
        )

        assert event.ai_operation.decision_type == "high_risk"


@pytest.mark.compliance
@pytest.mark.eu_ai_act
@pytest.mark.xdist_group(name="compliance_eu_ai_act")
class TestEUAIActQualityManagement:
    """Article 19: Quality management system."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_model_change_logged(self) -> None:
        """GIVEN AI model update WHEN deployed THEN logged per Article 19."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(actor_id="user:ml-engineer", actor_type="user"),
            resource_type="ai_model",
            resource_id="fraud-detection-v3",
            action="Deploy new model version",
            outcome="success",
            context=AuditContext(request_id="deploy-001"),
            regulation_tags=[Regulation.EU_AI_ACT],
            details={
                "previous_version": "v2.5",
                "new_version": "v3.0",
                "deployment_environment": "production",
            },
        )

        assert event.event_type == AuditEventType.CONFIG_CHANGE
        assert event.details is not None
        assert "new_version" in event.details

    def test_ai_error_logged(self) -> None:
        """GIVEN AI system error WHEN detected THEN logged per Article 19."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_ERROR,
            actor=AuditActor(actor_id="system:ai-monitor", actor_type="service"),
            resource_type="ai_model",
            resource_id="translation-model-v2",
            action="AI inference failed",
            outcome="error",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.EU_AI_ACT],
            details={
                "error_type": "timeout",
                "error_message": "Model inference exceeded timeout",
            },
        )

        assert event.event_type == AuditEventType.AI_ERROR
        assert event.outcome == "error"


@pytest.mark.compliance
@pytest.mark.eu_ai_act
@pytest.mark.xdist_group(name="compliance_eu_ai_act")
class TestEUAIActPostMarketMonitoring:
    """Article 72: Post-market monitoring."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_performance_logged(self) -> None:
        """GIVEN AI performance metrics WHEN collected THEN logged."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_INVOKE,
            actor=AuditActor(actor_id="system:monitoring", actor_type="service"),
            resource_type="ai_model",
            resource_id="sentiment-analysis-v1",
            action="Inference completed",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            ai_operation=AIOperationDetails(
                model_id="sentiment-analysis-v1",
                provider="huggingface",
                input_tokens=100,
                output_tokens=5,
                latency_ms=50.0,
            ),
        )

        assert event.ai_operation.latency_ms == 50.0


@pytest.mark.compliance
@pytest.mark.eu_ai_act
@pytest.mark.xdist_group(name="compliance_eu_ai_act")
class TestEUAIActRetention:
    """EU AI Act retention requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_eu_ai_act_retention_period_defined(self) -> None:
        """GIVEN EU AI Act regulation THEN minimum retention defined."""
        # EU AI Act requires minimum 6 months (180 days at 30 days/month)
        assert RetentionDays.EU_AI_ACT >= 180  # At least 6 months


@pytest.mark.compliance
@pytest.mark.eu_ai_act
@pytest.mark.xdist_group(name="compliance_eu_ai_act")
class TestEUAIActQueryCapabilities:
    """EU AI Act compliance query requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_eu_ai_act_regulation(self) -> None:
        """GIVEN audit events WHEN queried by EU AI Act THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_by_regulation = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_regulation(Regulation.EU_AI_ACT)

        mock_repo.query_by_regulation.assert_called_once()
        call_args = mock_repo.query_by_regulation.call_args
        assert call_args[0][0] == Regulation.EU_AI_ACT

    @pytest.mark.asyncio
    async def test_query_ai_operations(self) -> None:
        """GIVEN AI operations WHEN queried by category THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_by_category = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_category(AuditEventCategory.AI_OPERATION)

        mock_repo.query_by_category.assert_called_once()
        call_args = mock_repo.query_by_category.call_args
        assert call_args[0][0] == AuditEventCategory.AI_OPERATION
