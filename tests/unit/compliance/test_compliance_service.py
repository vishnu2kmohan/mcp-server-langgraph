"""
Tests for ComplianceService implementation.

The ComplianceService provides aggregated compliance reports across
multiple regulatory frameworks (GDPR, HIPAA, SOC2, FedRAMP, EU AI Act).

This tests the primary audit-backed ComplianceService which gracefully
degrades when audit service is unavailable.
"""

import gc
from datetime import datetime, UTC

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="compliance_service")
class TestComplianceService:
    """Test ComplianceService implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def service(self):
        """Create a ComplianceService instance (without audit service)."""
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        return ComplianceService(audit_service=None)

    @pytest.fixture
    def time_range(self):
        """Standard time range for tests."""
        return {
            "start_time": datetime(2024, 1, 1, tzinfo=UTC),
            "end_time": datetime(2024, 12, 31, tzinfo=UTC),
        }

    async def test_generate_compliance_summary_returns_dict(self, service, time_range) -> None:
        """
        ComplianceService.generate_compliance_summary should return a dict.

        GIVEN: A ComplianceService instance
        WHEN: generate_compliance_summary is called with a time range
        THEN: A dict with summary data should be returned
        """
        result = await service.generate_compliance_summary(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "by_regulation" in result
        assert "period" in result

    async def test_generate_compliance_summary_includes_all_regulations(self, service, time_range) -> None:
        """
        Summary should include all supported regulatory frameworks.

        GIVEN: A ComplianceService instance
        WHEN: generate_compliance_summary is called
        THEN: All regulations (GDPR, HIPAA, SOC2, FedRAMP, EU_AI_ACT) should be present
        """
        result = await service.generate_compliance_summary(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        expected_regulations = {"GDPR", "HIPAA", "SOC2", "FedRAMP", "EU_AI_ACT"}
        actual_regulations = set(result.get("by_regulation", {}).keys())

        assert expected_regulations == actual_regulations, (
            f"Expected regulations {expected_regulations}, got {actual_regulations}"
        )

    async def test_generate_gdpr_report_returns_dict(self, service, time_range) -> None:
        """
        ComplianceService.generate_gdpr_report should return a dict.

        GIVEN: A ComplianceService instance
        WHEN: generate_gdpr_report is called
        THEN: A dict with GDPR report data should be returned
        """
        result = await service.generate_gdpr_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result
        assert result["regulation"] == "GDPR"

    async def test_generate_hipaa_report_returns_dict(self, service, time_range) -> None:
        """
        ComplianceService.generate_hipaa_report should return a dict.
        """
        result = await service.generate_hipaa_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result
        assert result["regulation"] == "HIPAA"

    async def test_generate_soc2_report_returns_dict(self, service, time_range) -> None:
        """
        ComplianceService.generate_soc2_report should return a dict.
        """
        result = await service.generate_soc2_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result
        assert result["regulation"] == "SOC2"

    async def test_generate_fedramp_report_returns_dict(self, service, time_range) -> None:
        """
        ComplianceService.generate_fedramp_report should return a dict.
        """
        result = await service.generate_fedramp_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result
        assert result["regulation"] == "FedRAMP"

    async def test_generate_eu_ai_act_report_returns_dict(self, service, time_range) -> None:
        """
        ComplianceService.generate_eu_ai_act_report should return a dict.
        """
        result = await service.generate_eu_ai_act_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result
        assert result["regulation"] == "EU_AI_ACT"

    async def test_service_implements_protocol(self, service) -> None:
        """
        ComplianceService should implement ComplianceServiceProtocol.

        GIVEN: A ComplianceService instance
        WHEN: Checking its methods
        THEN: It should have all methods required by ComplianceServiceProtocol
        """
        required_methods = [
            "generate_gdpr_report",
            "generate_hipaa_report",
            "generate_soc2_report",
            "generate_fedramp_report",
            "generate_eu_ai_act_report",
            "generate_compliance_summary",
        ]

        for method_name in required_methods:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(service, method_name)), f"Not callable: {method_name}"
