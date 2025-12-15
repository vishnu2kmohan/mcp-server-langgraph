"""
Tests for ComplianceService.

TDD RED phase: These tests define expected behavior for the ComplianceService
that generates regulation-specific compliance reports.

The service should:
- Generate GDPR Article 30 Records of Processing
- Generate HIPAA 164.312(b) Audit Controls reports
- Generate SOC 2 Type II Evidence reports
- Generate FedRAMP NIST 800-53 AU reports
- Generate EU AI Act compliance reports
- Query the UnifiedAuditService for underlying data
"""

import gc
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


def _create_mock_audit_service() -> AsyncMock:
    """Create a mock UnifiedAuditService."""
    mock = AsyncMock()  # async-mock-configured
    mock.query_events = AsyncMock(return_value=([], 0))
    mock.get_event_count = AsyncMock(return_value=0)
    return mock


def _create_sample_events(
    category: str,
    event_type: str,
    count: int,
    regulation: str,
) -> list[dict[str, Any]]:
    """Create sample audit events for testing."""
    return [
        {
            "event_id": f"evt-{i:03d}",
            "timestamp": (datetime.now(UTC) - timedelta(hours=i)).isoformat(),
            "category": category,
            "event_type": event_type,
            "actor": {"actor_id": f"user-{i % 5}", "actor_type": "user"},
            "resource_type": "data",
            "resource_id": f"resource-{i}",
            "action": f"Test action {i}",
            "outcome": "success",
            "regulation_tags": [regulation],
        }
        for i in range(count)
    ]


@pytest.mark.unit
@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceServiceGDPR:
    """Tests for GDPR compliance report generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_gdpr_report_structure(self) -> None:
        """
        GIVEN audit events with GDPR tag
        WHEN generating GDPR report
        THEN returns Article 30 format with required fields.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("data_access", "data_read", 10, "GDPR")
        mock_audit.query_events.return_value = (events, 10)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_gdpr_report(start, end)

        assert report["regulation"] == "GDPR"
        assert "Article 30" in report["report_type"]
        assert "generated_at" in report
        assert "processing_activities" in report
        assert "data_subject_requests" in report

    @pytest.mark.asyncio
    async def test_generate_gdpr_report_aggregates_processing_activities(self) -> None:
        """
        GIVEN data access events
        WHEN generating GDPR report
        THEN aggregates by resource type.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("data_access", "data_read", 5, "GDPR")
        mock_audit.query_events.return_value = (events, 5)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_gdpr_report(start, end)

        assert len(report["processing_activities"]) > 0
        activity = report["processing_activities"][0]
        assert "name" in activity
        assert "access_count" in activity

    @pytest.mark.asyncio
    async def test_generate_gdpr_report_counts_data_subject_requests(self) -> None:
        """
        GIVEN data export/deletion events
        WHEN generating GDPR report
        THEN counts by request type.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()

        # Multiple calls for different event types
        # First call is for all GDPR events, then export, deletion, rectification
        mock_audit.query_events.side_effect = [
            (_create_sample_events("data_access", "data_read", 10, "GDPR"), 10),
            (_create_sample_events("compliance", "data_export", 3, "GDPR"), 3),
            (_create_sample_events("compliance", "data_deletion", 2, "GDPR"), 2),
            (_create_sample_events("compliance", "data_rectification", 1, "GDPR"), 1),
        ]

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_gdpr_report(start, end)

        dsr = report["data_subject_requests"]
        assert "access_requests" in dsr or "export_requests" in dsr
        assert "erasure_requests" in dsr or "deletion_requests" in dsr


@pytest.mark.unit
@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceServiceHIPAA:
    """Tests for HIPAA compliance report generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_hipaa_report_structure(self) -> None:
        """
        GIVEN audit events with HIPAA tag
        WHEN generating HIPAA report
        THEN returns 164.312(b) format.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("data_access", "phi_access", 10, "HIPAA")
        mock_audit.query_events.return_value = (events, 10)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_hipaa_report(start, end)

        assert report["regulation"] == "HIPAA"
        assert "164.312(b)" in report["report_type"]
        assert "generated_at" in report
        assert "phi_access_summary" in report
        assert "security_incidents" in report

    @pytest.mark.asyncio
    async def test_generate_hipaa_report_tracks_phi_access(self) -> None:
        """
        GIVEN PHI access events
        WHEN generating HIPAA report
        THEN summarizes by user and resource.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("data_access", "phi_access", 20, "HIPAA")
        mock_audit.query_events.return_value = (events, 20)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_hipaa_report(start, end)

        assert report["phi_access_summary"]["total_accesses"] >= 0
        assert "by_user" in report["phi_access_summary"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceServiceSOC2:
    """Tests for SOC 2 compliance report generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_soc2_report_structure(self) -> None:
        """
        GIVEN audit events with SOC2 tag
        WHEN generating SOC 2 report
        THEN returns CC6.x/CC7.x format.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("authentication", "login_success", 50, "SOC2")
        mock_audit.query_events.return_value = (events, 50)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_soc2_report(start, end)

        assert report["regulation"] == "SOC2"
        assert "generated_at" in report
        assert "access_controls" in report  # CC6.x
        assert "system_operations" in report  # CC7.x

    @pytest.mark.asyncio
    async def test_generate_soc2_report_access_controls(self) -> None:
        """
        GIVEN authentication events
        WHEN generating SOC 2 report
        THEN includes login success/failure stats.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        mock_audit.query_events.return_value = (
            _create_sample_events("authentication", "login_success", 100, "SOC2"),
            100,
        )

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_soc2_report(start, end)

        ac = report["access_controls"]
        assert "login_attempts" in ac
        assert "successful_logins" in ac or "login_success_rate" in ac


@pytest.mark.unit
@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceServiceFedRAMP:
    """Tests for FedRAMP compliance report generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_fedramp_report_structure(self) -> None:
        """
        GIVEN audit events with FedRAMP tag
        WHEN generating FedRAMP report
        THEN returns NIST 800-53 AU format.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("system", "configuration_change", 10, "FedRAMP")
        mock_audit.query_events.return_value = (events, 10)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_fedramp_report(start, end)

        assert report["regulation"] == "FedRAMP"
        assert "NIST 800-53" in report["report_type"]
        assert "generated_at" in report
        assert "au_controls" in report

    @pytest.mark.asyncio
    async def test_generate_fedramp_report_includes_integrity_status(self) -> None:
        """
        GIVEN audit events with integrity hashes
        WHEN generating FedRAMP report
        THEN includes AU-9 integrity verification status.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        mock_audit.query_events.return_value = ([], 0)
        mock_audit.get_integrity_report = AsyncMock(
            return_value={
                "chain_valid": True,
                "events_verified": 1000,
                "errors": [],
            }
        )

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_fedramp_report(start, end)

        assert "integrity_status" in report["au_controls"]
        assert report["au_controls"]["integrity_status"]["chain_valid"] is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceServiceEUAIAct:
    """Tests for EU AI Act compliance report generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_eu_ai_act_report_structure(self) -> None:
        """
        GIVEN AI operation events
        WHEN generating EU AI Act report
        THEN returns Articles 12/19/72 format.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("ai_operation", "model_inference", 25, "EU_AI_ACT")
        # Add AI operation details
        for event in events:
            event["ai_operation"] = {
                "model_id": "gpt-4",
                "provider": "openai",
                "tokens_used": 1000,
            }
        mock_audit.query_events.return_value = (events, 25)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_eu_ai_act_report(start, end)

        assert report["regulation"] == "EU_AI_ACT"
        assert "generated_at" in report
        assert "ai_systems" in report
        assert "usage_statistics" in report

    @pytest.mark.asyncio
    async def test_generate_eu_ai_act_report_aggregates_by_model(self) -> None:
        """
        GIVEN AI operations from multiple models
        WHEN generating EU AI Act report
        THEN aggregates statistics by model.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        events = _create_sample_events("ai_operation", "model_inference", 10, "EU_AI_ACT")
        for i, event in enumerate(events):
            event["ai_operation"] = {
                "model_id": "gpt-4" if i % 2 == 0 else "claude-3",
                "provider": "openai" if i % 2 == 0 else "anthropic",
                "tokens_used": 500 + i * 100,
            }
        mock_audit.query_events.return_value = (events, 10)

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_eu_ai_act_report(start, end)

        assert len(report["ai_systems"]) >= 1
        for system in report["ai_systems"]:
            assert "model_id" in system
            assert "invocation_count" in system


@pytest.mark.unit
@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceServiceSummary:
    """Tests for compliance summary generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_compliance_summary(self) -> None:
        """
        GIVEN events across multiple regulations
        WHEN generating compliance summary
        THEN returns overview of all regulations.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        mock_audit = _create_mock_audit_service()
        mock_audit.query_events.return_value = ([], 0)
        mock_audit.get_event_count.return_value = 500

        service = ComplianceService(audit_service=mock_audit)

        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)

        report = await service.generate_compliance_summary(start, end)

        assert "generated_at" in report
        assert "period" in report
        assert "total_events" in report
        assert "by_regulation" in report
        assert "GDPR" in report["by_regulation"] or len(report["by_regulation"]) >= 0
