"""
Tests for SOC 2 Evidence Collection

Comprehensive test suite for evidence collection, access reviews,
and compliance reporting.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.compliance.evidence import (
    ComplianceReport,
    ControlCategory,
    Evidence,
    EvidenceCollector,
    EvidenceStatus,
    EvidenceType,
)
from mcp_server_langgraph.schedulers.compliance import (
    AccessReviewItem,
    AccessReviewReport,
    ComplianceScheduler,
)


@pytest.fixture
def mock_session_store():
    """Mock session store"""
    store = MagicMock()
    store.get_user_sessions = AsyncMock(return_value=[])
    return store


@pytest.fixture
def evidence_dir(tmp_path):
    """Temporary evidence directory"""
    return tmp_path / "evidence"


@pytest.fixture
def evidence_collector(mock_session_store, evidence_dir):
    """Evidence collector instance"""
    return EvidenceCollector(
        session_store=mock_session_store, evidence_dir=evidence_dir
    )


@pytest.fixture
def compliance_scheduler(evidence_collector, mock_session_store, evidence_dir):
    """Compliance scheduler instance"""
    return ComplianceScheduler(
        evidence_collector=evidence_collector,
        session_store=mock_session_store,
        evidence_dir=evidence_dir,
        enabled=False,  # Don't start scheduler in tests
    )


# --- Evidence Collection Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.soc2
class TestEvidenceCollector:
    """Test evidence collector service"""

    async def test_collect_all_evidence(self, evidence_collector):
        """Test collecting all evidence"""
        evidence_items = await evidence_collector.collect_all_evidence()

        assert len(evidence_items) > 0
        assert all(isinstance(e, Evidence) for e in evidence_items)

        # Verify all evidence types are covered
        evidence_types = {e.evidence_type for e in evidence_items}
        assert EvidenceType.SECURITY in evidence_types
        assert EvidenceType.AVAILABILITY in evidence_types
        assert EvidenceType.CONFIDENTIALITY in evidence_types
        assert EvidenceType.PROCESSING_INTEGRITY in evidence_types
        assert EvidenceType.PRIVACY in evidence_types

    async def test_collect_security_evidence(self, evidence_collector):
        """Test security evidence collection"""
        evidence_items = await evidence_collector.collect_security_evidence()

        assert len(evidence_items) == 5  # CC6.1, CC6.2, CC6.6, CC7.2, CC8.1
        assert all(e.evidence_type == EvidenceType.SECURITY for e in evidence_items)

        # Verify control categories
        controls = {e.control_category for e in evidence_items}
        assert ControlCategory.CC6_1 in controls
        assert ControlCategory.CC6_2 in controls
        assert ControlCategory.CC6_6 in controls
        assert ControlCategory.CC7_2 in controls
        assert ControlCategory.CC8_1 in controls

    async def test_collect_availability_evidence(self, evidence_collector):
        """Test availability evidence collection"""
        evidence_items = await evidence_collector.collect_availability_evidence()

        assert len(evidence_items) == 2  # SLA + Backup
        assert all(
            e.evidence_type == EvidenceType.AVAILABILITY for e in evidence_items
        )

    async def test_collect_confidentiality_evidence(self, evidence_collector):
        """Test confidentiality evidence collection"""
        evidence_items = await evidence_collector.collect_confidentiality_evidence()

        assert len(evidence_items) == 2  # Encryption + Data Access
        assert all(
            e.evidence_type == EvidenceType.CONFIDENTIALITY for e in evidence_items
        )

    async def test_collect_processing_integrity_evidence(self, evidence_collector):
        """Test processing integrity evidence collection"""
        evidence_items = (
            await evidence_collector.collect_processing_integrity_evidence()
        )

        assert len(evidence_items) == 2  # Data Retention + Input Validation
        assert all(
            e.evidence_type == EvidenceType.PROCESSING_INTEGRITY
            for e in evidence_items
        )

    async def test_collect_privacy_evidence(self, evidence_collector):
        """Test privacy evidence collection"""
        evidence_items = await evidence_collector.collect_privacy_evidence()

        assert len(evidence_items) == 2  # GDPR + Consent
        assert all(e.evidence_type == EvidenceType.PRIVACY for e in evidence_items)

    async def test_access_control_evidence(self, evidence_collector):
        """Test access control evidence (CC6.1)"""
        evidence = await evidence_collector._collect_access_control_evidence()

        assert evidence.evidence_type == EvidenceType.SECURITY
        assert evidence.control_category == ControlCategory.CC6_1
        assert evidence.status in [EvidenceStatus.SUCCESS, EvidenceStatus.PARTIAL]
        assert "active_sessions" in evidence.data
        assert "authentication_method" in evidence.data

    async def test_logical_access_evidence(self, evidence_collector):
        """Test logical access evidence (CC6.2)"""
        evidence = await evidence_collector._collect_logical_access_evidence()

        assert evidence.evidence_type == EvidenceType.SECURITY
        assert evidence.control_category == ControlCategory.CC6_2
        assert evidence.status == EvidenceStatus.SUCCESS
        assert "authentication_providers" in evidence.data
        assert "authorization_system" in evidence.data
        assert evidence.data["authorization_system"] == "OpenFGA (Zanzibar)"

    async def test_audit_log_evidence(self, evidence_collector):
        """Test audit log evidence (CC6.6)"""
        evidence = await evidence_collector._collect_audit_log_evidence()

        assert evidence.evidence_type == EvidenceType.SECURITY
        assert evidence.control_category == ControlCategory.CC6_6
        assert evidence.status == EvidenceStatus.SUCCESS
        assert "logging_system" in evidence.data
        assert evidence.data["log_retention"] == "7 years (SOC 2 compliant)"
        assert evidence.data["tamper_proof"] is True

    async def test_system_monitoring_evidence(self, evidence_collector):
        """Test system monitoring evidence (CC7.2)"""
        evidence = await evidence_collector._collect_system_monitoring_evidence()

        assert evidence.evidence_type == EvidenceType.SECURITY
        assert evidence.control_category == ControlCategory.CC7_2
        assert evidence.status == EvidenceStatus.SUCCESS
        assert "monitoring_system" in evidence.data
        assert "metrics_tracked" in evidence.data
        assert len(evidence.data["metrics_tracked"]) > 0

    async def test_change_management_evidence(self, evidence_collector):
        """Test change management evidence (CC8.1)"""
        evidence = await evidence_collector._collect_change_management_evidence()

        assert evidence.evidence_type == EvidenceType.SECURITY
        assert evidence.control_category == ControlCategory.CC8_1
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["code_review_required"] is True
        assert evidence.data["automated_testing"] is True

    async def test_sla_evidence(self, evidence_collector):
        """Test SLA monitoring evidence (A1.2)"""
        evidence = await evidence_collector._collect_sla_evidence()

        assert evidence.evidence_type == EvidenceType.AVAILABILITY
        assert evidence.control_category == ControlCategory.A1_2
        assert "sla_target" in evidence.data
        assert "current_uptime" in evidence.data

    async def test_backup_evidence(self, evidence_collector):
        """Test backup verification evidence"""
        evidence = await evidence_collector._collect_backup_evidence()

        assert evidence.evidence_type == EvidenceType.AVAILABILITY
        assert evidence.control_category == ControlCategory.A1_2
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["backup_frequency"] == "Daily"
        assert "rto" in evidence.data
        assert "rpo" in evidence.data

    async def test_encryption_evidence(self, evidence_collector):
        """Test encryption verification evidence"""
        evidence = await evidence_collector._collect_encryption_evidence()

        assert evidence.evidence_type == EvidenceType.CONFIDENTIALITY
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["encryption_in_transit"] == "TLS 1.3"
        assert "encryption_at_rest" in evidence.data

    async def test_data_retention_evidence(self, evidence_collector):
        """Test data retention evidence (PI1.4)"""
        evidence = await evidence_collector._collect_data_retention_evidence()

        assert evidence.evidence_type == EvidenceType.PROCESSING_INTEGRITY
        assert evidence.control_category == ControlCategory.PI1_4
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["retention_policy_documented"] is True
        assert evidence.data["automated_cleanup"] is True
        assert "retention_periods" in evidence.data

    async def test_input_validation_evidence(self, evidence_collector):
        """Test input validation evidence"""
        evidence = await evidence_collector._collect_input_validation_evidence()

        assert evidence.evidence_type == EvidenceType.PROCESSING_INTEGRITY
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["validation_framework"] == "Pydantic"

    async def test_gdpr_evidence(self, evidence_collector):
        """Test GDPR compliance evidence"""
        evidence = await evidence_collector._collect_gdpr_evidence()

        assert evidence.evidence_type == EvidenceType.PRIVACY
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["data_subject_rights_implemented"] is True
        assert len(evidence.data["rights_supported"]) == 5

    async def test_consent_evidence(self, evidence_collector):
        """Test consent management evidence"""
        evidence = await evidence_collector._collect_consent_evidence()

        assert evidence.evidence_type == EvidenceType.PRIVACY
        assert evidence.status == EvidenceStatus.SUCCESS
        assert evidence.data["consent_management_implemented"] is True
        assert "consent_types" in evidence.data


# --- Compliance Report Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.soc2
class TestComplianceReport:
    """Test compliance report generation"""

    async def test_generate_daily_report(self, evidence_collector, evidence_dir):
        """Test daily compliance report generation"""
        report = await evidence_collector.generate_compliance_report(
            report_type="daily", period_days=1
        )

        assert isinstance(report, ComplianceReport)
        assert report.report_type == "daily"
        assert report.compliance_score >= 0
        assert report.compliance_score <= 100
        assert report.total_controls > 0
        assert len(report.evidence_items) > 0

        # Verify report file was saved
        report_file = evidence_dir / f"{report.report_id}.json"
        assert report_file.exists()

    async def test_generate_weekly_report(self, evidence_collector):
        """Test weekly compliance report generation"""
        report = await evidence_collector.generate_compliance_report(
            report_type="weekly", period_days=7
        )

        assert report.report_type == "weekly"
        assert report.total_controls > 0

    async def test_generate_monthly_report(self, evidence_collector):
        """Test monthly compliance report generation"""
        report = await evidence_collector.generate_compliance_report(
            report_type="monthly", period_days=30
        )

        assert report.report_type == "monthly"
        assert report.total_controls > 0

    async def test_compliance_score_calculation(self, evidence_collector):
        """Test compliance score calculation"""
        report = await evidence_collector.generate_compliance_report(
            report_type="daily", period_days=1
        )

        # Score should be between 0-100
        assert 0 <= report.compliance_score <= 100

        # Verify calculation
        total = report.total_controls
        passed = report.passed_controls
        partial = report.partial_controls

        expected_score = ((passed + (partial * 0.5)) / total * 100) if total > 0 else 0
        assert abs(report.compliance_score - expected_score) < 0.1

    async def test_report_summary(self, evidence_collector):
        """Test report summary generation"""
        report = await evidence_collector.generate_compliance_report(
            report_type="daily", period_days=1
        )

        assert "evidence_by_type" in report.summary
        assert "evidence_by_control" in report.summary
        assert "findings_summary" in report.summary

        # Verify evidence by type
        evidence_by_type = report.summary["evidence_by_type"]
        assert isinstance(evidence_by_type, dict)

        # Verify evidence by control
        evidence_by_control = report.summary["evidence_by_control"]
        assert isinstance(evidence_by_control, dict)

    async def test_report_persistence(self, evidence_collector, evidence_dir):
        """Test report file persistence"""
        report = await evidence_collector.generate_compliance_report(
            report_type="daily", period_days=1
        )

        # Verify report file exists
        report_file = evidence_dir / f"{report.report_id}.json"
        assert report_file.exists()

        # Verify file content
        with open(report_file) as f:
            saved_data = json.load(f)

        assert saved_data["report_id"] == report.report_id
        assert saved_data["compliance_score"] == report.compliance_score


# --- Compliance Scheduler Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.soc2
class TestComplianceScheduler:
    """Test compliance scheduler"""

    async def test_scheduler_initialization(self, compliance_scheduler):
        """Test scheduler initialization"""
        assert compliance_scheduler is not None
        assert compliance_scheduler.enabled is False
        assert compliance_scheduler.scheduler is not None

    async def test_trigger_daily_check(self, compliance_scheduler):
        """Test manual trigger of daily compliance check"""
        summary = await compliance_scheduler.trigger_daily_check()

        assert "evidence_collected" in summary
        assert "passed_controls" in summary
        assert "failed_controls" in summary
        assert "compliance_score" in summary

    async def test_trigger_weekly_review(self, compliance_scheduler):
        """Test manual trigger of weekly access review"""
        report = await compliance_scheduler.trigger_weekly_review()

        assert isinstance(report, AccessReviewReport)
        assert report.review_id is not None
        assert report.total_users >= 0

    async def test_trigger_monthly_report(self, compliance_scheduler):
        """Test manual trigger of monthly compliance report"""
        summary = await compliance_scheduler.trigger_monthly_report()

        assert "report_id" in summary
        assert "compliance_score" in summary
        assert "total_controls" in summary

    async def test_daily_check_error_handling(self, compliance_scheduler):
        """Test error handling in daily compliance check"""
        # Mock error in evidence collection
        with patch.object(
            compliance_scheduler.evidence_collector,
            "collect_all_evidence",
            side_effect=Exception("Test error"),
        ):
            summary = await compliance_scheduler.trigger_daily_check()

            assert "error" in summary
            assert summary["status"] == "failed"

    async def test_scheduler_start_stop(self, compliance_scheduler):
        """Test scheduler start and stop"""
        # Enable scheduler
        compliance_scheduler.enabled = True

        # Start scheduler
        await compliance_scheduler.start()
        assert compliance_scheduler.scheduler.running

        # Stop scheduler
        await compliance_scheduler.stop()
        assert not compliance_scheduler.scheduler.running


# --- Access Review Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.soc2
class TestAccessReview:
    """Test access review functionality"""

    async def test_access_review_report_structure(self, compliance_scheduler):
        """Test access review report structure"""
        report = await compliance_scheduler.trigger_weekly_review()

        assert isinstance(report, AccessReviewReport)
        assert report.review_id is not None
        assert report.generated_at is not None
        assert report.period_start is not None
        assert report.period_end is not None
        assert isinstance(report.users_reviewed, list)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.actions_required, list)

    async def test_access_review_item_validation(self):
        """Test access review item validation"""
        item = AccessReviewItem(
            user_id="user:alice",
            username="alice",
            roles=["admin", "user"],
            active_sessions=2,
            last_login=datetime.utcnow().isoformat() + "Z",
            account_status="active",
            review_status="approved",
        )

        assert item.user_id == "user:alice"
        assert "admin" in item.roles
        assert item.active_sessions == 2
        assert item.account_status == "active"

    async def test_access_review_report_persistence(
        self, compliance_scheduler, evidence_dir
    ):
        """Test access review report file persistence"""
        report = await compliance_scheduler.trigger_weekly_review()

        # Verify report file exists
        report_file = evidence_dir / f"{report.review_id}.json"
        assert report_file.exists()

        # Verify file content
        with open(report_file) as f:
            saved_data = json.load(f)

        assert saved_data["review_id"] == report.review_id


# --- Edge Cases and Integration Tests ---


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.soc2
class TestSOC2Integration:
    """Integration tests for SOC 2 evidence collection"""

    async def test_full_compliance_cycle(self, evidence_collector):
        """Test full compliance evidence collection cycle"""
        # Collect all evidence
        evidence_items = await evidence_collector.collect_all_evidence()
        assert len(evidence_items) > 0

        # Generate compliance report
        report = await evidence_collector.generate_compliance_report(
            report_type="daily", period_days=1
        )

        assert report.total_controls == len(evidence_items)
        assert report.compliance_score > 0

    async def test_compliance_score_threshold(self, evidence_collector):
        """Test compliance score meets minimum threshold"""
        report = await evidence_collector.generate_compliance_report(
            report_type="daily", period_days=1
        )

        # Compliance score should be >= 80% for production readiness
        assert report.compliance_score >= 80.0

    async def test_evidence_completeness(self, evidence_collector):
        """Test that all required evidence is collected"""
        evidence_items = await evidence_collector.collect_all_evidence()

        # Verify all required controls are present
        required_controls = {
            ControlCategory.CC6_1,  # Access Control
            ControlCategory.CC6_2,  # Logical Access
            ControlCategory.CC6_6,  # Audit Logs
            ControlCategory.CC7_2,  # System Monitoring
            ControlCategory.CC8_1,  # Change Management
            ControlCategory.A1_2,  # SLA Monitoring
            ControlCategory.PI1_4,  # Data Retention
        }

        collected_controls = {e.control_category for e in evidence_items}

        for control in required_controls:
            assert (
                control in collected_controls
            ), f"Missing required control: {control}"
