"""
Tests for ComplianceService resilience and graceful degradation.

The ComplianceService should:
1. Work normally when audit service is available
2. Return valid (empty) reports when audit service is unavailable
3. Handle errors from audit service gracefully

TDD: These tests define expected behavior for graceful degradation.
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestComplianceServiceResilience:
    """Test ComplianceService graceful degradation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def time_range(self):
        """Standard time range for tests."""
        return {
            "start_time": datetime(2024, 1, 1, tzinfo=UTC),
            "end_time": datetime(2024, 12, 31, tzinfo=UTC),
        }

    @pytest.fixture
    def mock_audit_service(self):
        """Create a mock audit service that returns data."""
        mock = MagicMock()

        # Use explicit async functions to avoid recursion issues
        async def mock_query(*args, **kwargs):
            return ([], 0)

        async def mock_integrity(*args, **kwargs):
            return {"chain_valid": True, "events_verified": 0, "errors": []}

        mock.query_events = mock_query
        mock.get_integrity_report = mock_integrity
        mock._query_called = False
        # Track calls manually
        original_query = mock.query_events

        async def tracked_query(*args, **kwargs):
            mock._query_called = True
            return await original_query(*args, **kwargs)

        mock.query_events = tracked_query
        return mock

    @pytest.fixture
    def mock_failing_audit_service(self):
        """Create a mock audit service that raises errors."""
        mock = MagicMock()
        mock.query_events = AsyncMock(side_effect=Exception("Database unavailable"))
        mock.get_integrity_report = AsyncMock(side_effect=Exception("Database unavailable"))
        return mock

    async def test_compliance_service_works_without_audit_service(self, time_range) -> None:
        """
        ComplianceService should work when audit service is None.

        GIVEN: A ComplianceService with audit_service=None
        WHEN: generate_compliance_summary is called
        THEN: Should return valid report structure with empty data
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        # Create service with None audit service
        service = ComplianceService(audit_service=None)

        result = await service.generate_compliance_summary(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        # Should return valid structure
        assert isinstance(result, dict)
        assert "period" in result
        assert "by_regulation" in result or "frameworks" in result
        # Should indicate service unavailable or empty data
        assert result.get("total_events", 0) == 0 or result.get("status") == "unavailable"

    async def test_gdpr_report_works_without_audit_service(self, time_range) -> None:
        """
        GDPR report should return valid structure when audit service is None.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=None)

        result = await service.generate_gdpr_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result or "framework" in result
        assert result.get("regulation") == "GDPR" or result.get("framework") == "gdpr"

    async def test_hipaa_report_works_without_audit_service(self, time_range) -> None:
        """
        HIPAA report should return valid structure when audit service is None.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=None)

        result = await service.generate_hipaa_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result or "framework" in result

    async def test_soc2_report_works_without_audit_service(self, time_range) -> None:
        """
        SOC2 report should return valid structure when audit service is None.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=None)

        result = await service.generate_soc2_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result or "framework" in result

    async def test_fedramp_report_works_without_audit_service(self, time_range) -> None:
        """
        FedRAMP report should return valid structure when audit service is None.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=None)

        result = await service.generate_fedramp_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result or "framework" in result

    async def test_eu_ai_act_report_works_without_audit_service(self, time_range) -> None:
        """
        EU AI Act report should return valid structure when audit service is None.
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=None)

        result = await service.generate_eu_ai_act_report(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "regulation" in result or "framework" in result

    async def test_compliance_service_handles_audit_errors_gracefully(self, time_range, mock_failing_audit_service) -> None:
        """
        ComplianceService should handle audit service errors gracefully.

        GIVEN: A ComplianceService with a failing audit service
        WHEN: generate_compliance_summary is called
        THEN: Should return valid report structure without raising exception
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=mock_failing_audit_service)

        # Should not raise, should return degraded report
        result = await service.generate_compliance_summary(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        # Should indicate an issue or have empty data
        assert result.get("total_events", 0) == 0 or result.get("status") == "error" or "error" in result

    async def test_compliance_service_works_with_valid_audit_service(self, time_range, mock_audit_service) -> None:
        """
        ComplianceService should work normally with valid audit service.

        GIVEN: A ComplianceService with working audit service
        WHEN: generate_compliance_summary is called
        THEN: Should return normal report from audit data
        """
        from mcp_server_langgraph.audit.compliance_service import ComplianceService

        service = ComplianceService(audit_service=mock_audit_service)

        result = await service.generate_compliance_summary(
            start_time=time_range["start_time"],
            end_time=time_range["end_time"],
        )

        assert isinstance(result, dict)
        assert "period" in result
        # Audit service was called
        assert mock_audit_service._query_called
