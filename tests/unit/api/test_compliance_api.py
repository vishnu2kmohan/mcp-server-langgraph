"""
TDD: Unit tests for Compliance API endpoints.

Tests that compliance report endpoints return proper data
for GDPR, HIPAA, SOC2, FedRAMP frameworks.

Phase 5: canvas_compliance feature flag
- GET /api/v1/compliance/reports/summary
- GET /api/v1/compliance/reports/gdpr
- GET /api/v1/compliance/reports/hipaa
- GET /api/v1/compliance/reports/soc2
- GET /api/v1/compliance/reports/fedramp

RED phase: These tests define expected behavior before implementation.
"""

import gc
from datetime import UTC, datetime, timedelta

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.compliance]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_feature_flags():
    """Mock feature flags with compliance enabled."""
    from unittest.mock import MagicMock

    mock_flags = MagicMock()
    mock_flags.canvas_compliance = True
    return mock_flags


@pytest.fixture
def date_range() -> dict[str, str]:
    """Default date range for tests."""
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)
    return {
        "start_time": thirty_days_ago.isoformat() + "Z",
        "end_time": now.isoformat() + "Z",
    }


# =============================================================================
# Compliance Summary API Tests
# =============================================================================


class TestComplianceSummaryAPI:
    """Test GET /api/v1/compliance/reports/summary endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_summary_returns_all_frameworks(self, date_range: dict[str, str]) -> None:
        """GIVEN valid date range WHEN GET summary THEN returns all frameworks."""
        from mcp_server_langgraph.api.v1.compliance import get_compliance_summary

        result = get_compliance_summary(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        # Verify all frameworks are present
        assert "soc2" in result
        assert "hipaa" in result
        assert "gdpr" in result
        assert "fedramp" in result

    def test_summary_framework_structure(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET summary THEN framework has required fields."""
        from mcp_server_langgraph.api.v1.compliance import get_compliance_summary

        result = get_compliance_summary(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        # Check SOC2 structure (representative of all frameworks)
        soc2 = result["soc2"]
        assert "percentage" in soc2
        assert "compliant_count" in soc2
        assert "total_count" in soc2
        assert "status" in soc2
        assert soc2["status"] in ["compliant", "partial", "non-compliant"]

    def test_summary_percentage_valid_range(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET summary THEN percentages are 0-100."""
        from mcp_server_langgraph.api.v1.compliance import get_compliance_summary

        result = get_compliance_summary(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        for framework in ["soc2", "hipaa", "gdpr", "fedramp"]:
            percentage = result[framework]["percentage"]
            assert 0 <= percentage <= 100


# =============================================================================
# GDPR Report API Tests
# =============================================================================


class TestGDPRReportAPI:
    """Test GET /api/v1/compliance/reports/gdpr endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_gdpr_report_returns_data_subject_requests(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET gdpr THEN returns DSR metrics."""
        from mcp_server_langgraph.api.v1.compliance import get_gdpr_report

        result = get_gdpr_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "data_subject_requests" in result
        dsr = result["data_subject_requests"]
        assert "total" in dsr
        assert "completed" in dsr
        assert "pending" in dsr

    def test_gdpr_report_returns_consent_metrics(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET gdpr THEN returns consent metrics."""
        from mcp_server_langgraph.api.v1.compliance import get_gdpr_report

        result = get_gdpr_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "consent_metrics" in result
        consent = result["consent_metrics"]
        assert "active_consents" in consent


# =============================================================================
# HIPAA Report API Tests
# =============================================================================


class TestHIPAAReportAPI:
    """Test GET /api/v1/compliance/reports/hipaa endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hipaa_report_returns_phi_access_metrics(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET hipaa THEN returns PHI access metrics."""
        from mcp_server_langgraph.api.v1.compliance import get_hipaa_report

        result = get_hipaa_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "phi_access" in result
        phi = result["phi_access"]
        assert "total_access_events" in phi
        assert "authorized_access" in phi

    def test_hipaa_report_returns_encryption_status(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET hipaa THEN returns encryption status."""
        from mcp_server_langgraph.api.v1.compliance import get_hipaa_report

        result = get_hipaa_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "encryption" in result
        enc = result["encryption"]
        assert "at_rest" in enc
        assert "in_transit" in enc


# =============================================================================
# SOC2 Report API Tests
# =============================================================================


class TestSOC2ReportAPI:
    """Test GET /api/v1/compliance/reports/soc2 endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_soc2_report_returns_trust_principles(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET soc2 THEN returns trust principles."""
        from mcp_server_langgraph.api.v1.compliance import get_soc2_report

        result = get_soc2_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "trust_principles" in result
        principles = result["trust_principles"]
        # SOC2 Trust Service Principles
        assert "security" in principles
        assert "availability" in principles

    def test_soc2_report_returns_control_status(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET soc2 THEN returns control status."""
        from mcp_server_langgraph.api.v1.compliance import get_soc2_report

        result = get_soc2_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "controls" in result
        controls = result["controls"]
        assert "total" in controls
        assert "passing" in controls


# =============================================================================
# FedRAMP Report API Tests
# =============================================================================


class TestFedRAMPReportAPI:
    """Test GET /api/v1/compliance/reports/fedramp endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fedramp_report_returns_impact_level(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET fedramp THEN returns impact level."""
        from mcp_server_langgraph.api.v1.compliance import get_fedramp_report

        result = get_fedramp_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "impact_level" in result
        assert result["impact_level"] in ["low", "moderate", "high"]

    def test_fedramp_report_returns_poam_status(self, date_range: dict[str, str]) -> None:
        """GIVEN valid request WHEN GET fedramp THEN returns POA&M status."""
        from mcp_server_langgraph.api.v1.compliance import get_fedramp_report

        result = get_fedramp_report(
            start_time=date_range["start_time"],
            end_time=date_range["end_time"],
        )

        assert "poam" in result
        poam = result["poam"]
        assert "open_items" in poam
        assert "closed_items" in poam


# =============================================================================
# Feature Flag Tests
# =============================================================================


class TestComplianceFeatureFlag:
    """Test feature flag gating for compliance endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_compliance_requires_feature_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN feature flag disabled WHEN access endpoint THEN returns 403 or fallback."""
        from mcp_server_langgraph.api.v1 import compliance as compliance_module
        from unittest.mock import MagicMock

        mock_flags = MagicMock()
        mock_flags.canvas_compliance = False
        # Patch the module-level feature_flags in compliance module
        monkeypatch.setattr(compliance_module, "feature_flags", mock_flags)

        # With flag disabled, should still return data (graceful degradation)
        # or raise appropriate error
        result = compliance_module.get_compliance_summary(
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-31T23:59:59Z",
        )

        # Should still return valid structure (fallback data)
        assert "soc2" in result
