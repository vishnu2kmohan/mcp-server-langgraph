"""
Tests for Compliance Report API endpoints.

TDD RED phase: These tests define expected behavior for compliance reports.

API endpoints should:
- GET /api/v1/compliance/reports/gdpr - GDPR Article 30 Records
- GET /api/v1/compliance/reports/hipaa - HIPAA 164.312(b) Audit Controls
- GET /api/v1/compliance/reports/soc2 - SOC 2 Type II Evidence
- GET /api/v1/compliance/reports/fedramp - FedRAMP AU Controls
- GET /api/v1/compliance/reports/eu-ai-act - EU AI Act Articles 12/19/72
"""

import gc
from typing import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api


@pytest.fixture
def compliance_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked compliance service."""
    from mcp_server_langgraph.api.v1.compliance_reports import (
        router,
        set_compliance_service,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/compliance")

    mock_service = AsyncMock()  # async-mock-configured
    set_compliance_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_compliance_service(None)


@pytest.mark.api
@pytest.mark.xdist_group(name="compliance_reports")
class TestGDPRComplianceReport:
    """Tests for GDPR compliance report endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_gdpr_report_returns_article_30_records(self, compliance_app: tuple) -> None:
        """GIVEN audit data WHEN requesting GDPR report THEN returns Article 30 format."""
        app, mock_service = compliance_app

        mock_report = {
            "regulation": "GDPR",
            "report_type": "Article 30 Records of Processing Activities",
            "generated_at": "2025-01-15T10:30:00Z",
            "organization": "Test Org",
            "processing_activities": [
                {
                    "name": "User Authentication",
                    "purpose": "Access Control",
                    "categories_of_data": ["User credentials", "Session data"],
                    "recipients": ["Internal systems"],
                    "retention_period": "7 years",
                    "access_count": 1500,
                }
            ],
            "data_subject_requests": {
                "access_requests": 10,
                "erasure_requests": 5,
                "rectification_requests": 2,
            },
        }

        mock_service.generate_gdpr_report.return_value = mock_report

        client = TestClient(app)
        response = client.get("/api/v1/compliance/reports/gdpr?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        data = response.json()
        assert data["regulation"] == "GDPR"
        assert "processing_activities" in data
        assert "data_subject_requests" in data


@pytest.mark.api
@pytest.mark.xdist_group(name="compliance_reports")
class TestHIPAAComplianceReport:
    """Tests for HIPAA compliance report endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hipaa_report_returns_audit_controls(self, compliance_app: tuple) -> None:
        """GIVEN audit data WHEN requesting HIPAA report THEN returns 164.312(b) format."""
        app, mock_service = compliance_app

        mock_report = {
            "regulation": "HIPAA",
            "report_type": "164.312(b) Audit Controls",
            "generated_at": "2025-01-15T10:30:00Z",
            "phi_access_summary": {
                "total_access_events": 500,
                "unique_users": 25,
                "unique_records": 150,
            },
            "access_by_user": [
                {
                    "user_id": "user:dr_smith",
                    "access_count": 50,
                    "last_access": "2025-01-15T09:00:00Z",
                }
            ],
            "emergency_access_events": [],
            "failed_access_attempts": 10,
        }

        mock_service.generate_hipaa_report.return_value = mock_report

        client = TestClient(app)
        response = client.get("/api/v1/compliance/reports/hipaa?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        data = response.json()
        assert data["regulation"] == "HIPAA"
        assert "phi_access_summary" in data
        assert "access_by_user" in data


@pytest.mark.api
@pytest.mark.xdist_group(name="compliance_reports")
class TestSOC2ComplianceReport:
    """Tests for SOC 2 Type II compliance report endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_soc2_report_returns_evidence(self, compliance_app: tuple) -> None:
        """GIVEN audit data WHEN requesting SOC 2 report THEN returns CC evidence."""
        app, mock_service = compliance_app

        mock_report = {
            "regulation": "SOC2",
            "report_type": "Type II Evidence Report",
            "generated_at": "2025-01-15T10:30:00Z",
            "criteria_coverage": {
                "CC6.1": {
                    "description": "Logical and Physical Access Controls",
                    "evidence_count": 1500,
                    "status": "compliant",
                },
                "CC6.2": {
                    "description": "User Registration and Authorization",
                    "evidence_count": 500,
                    "status": "compliant",
                },
                "CC7.1": {
                    "description": "System Operations",
                    "evidence_count": 2000,
                    "status": "compliant",
                },
            },
            "total_events": 4000,
            "integrity_verified": True,
        }

        mock_service.generate_soc2_report.return_value = mock_report

        client = TestClient(app)
        response = client.get("/api/v1/compliance/reports/soc2?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        data = response.json()
        assert data["regulation"] == "SOC2"
        assert "criteria_coverage" in data
        assert data["integrity_verified"] is True


@pytest.mark.api
@pytest.mark.xdist_group(name="compliance_reports")
class TestFedRAMPComplianceReport:
    """Tests for FedRAMP compliance report endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fedramp_report_returns_au_controls(self, compliance_app: tuple) -> None:
        """GIVEN audit data WHEN requesting FedRAMP report THEN returns AU controls."""
        app, mock_service = compliance_app

        mock_report = {
            "regulation": "FedRAMP",
            "report_type": "NIST 800-53 AU Controls",
            "generated_at": "2025-01-15T10:30:00Z",
            "au_controls": {
                "AU-2": {
                    "description": "Audit Events",
                    "event_types_logged": 25,
                    "status": "compliant",
                },
                "AU-3": {
                    "description": "Content of Audit Records",
                    "fields_captured": ["who", "what", "when", "where", "outcome"],
                    "status": "compliant",
                },
                "AU-9": {
                    "description": "Protection of Audit Information",
                    "integrity_verified": True,
                    "chain_valid": True,
                    "status": "compliant",
                },
                "AU-11": {
                    "description": "Audit Record Retention",
                    "retention_policy": "7 years",
                    "oldest_record": "2024-01-15T00:00:00Z",
                    "status": "compliant",
                },
            },
            "total_events": 10000,
        }

        mock_service.generate_fedramp_report.return_value = mock_report

        client = TestClient(app)
        response = client.get(
            "/api/v1/compliance/reports/fedramp?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["regulation"] == "FedRAMP"
        assert "au_controls" in data
        assert data["au_controls"]["AU-9"]["chain_valid"] is True


@pytest.mark.api
@pytest.mark.xdist_group(name="compliance_reports")
class TestEUAIActComplianceReport:
    """Tests for EU AI Act compliance report endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_eu_ai_act_report_returns_ai_operations(self, compliance_app: tuple) -> None:
        """GIVEN AI operations WHEN requesting EU AI Act report THEN returns Article 12/19/72."""
        app, mock_service = compliance_app

        mock_report = {
            "regulation": "EU_AI_ACT",
            "report_type": "Articles 12, 19, 72 Compliance",
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_operations_summary": {
                "total_operations": 5000,
                "unique_models": 3,
                "unique_providers": 2,
            },
            "operations_by_model": [
                {
                    "model_id": "gpt-4o",
                    "provider": "openai",
                    "invocation_count": 3000,
                    "decision_types": ["generation", "classification"],
                    "avg_latency_ms": 250,
                },
                {
                    "model_id": "claude-3-opus",
                    "provider": "anthropic",
                    "invocation_count": 2000,
                    "decision_types": ["generation"],
                    "avg_latency_ms": 350,
                },
            ],
            "high_risk_decisions": 0,
            "logging_completeness": 100.0,
        }

        mock_service.generate_eu_ai_act_report.return_value = mock_report

        client = TestClient(app)
        response = client.get(
            "/api/v1/compliance/reports/eu-ai-act?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["regulation"] == "EU_AI_ACT"
        assert "ai_operations_summary" in data
        assert "operations_by_model" in data


@pytest.mark.api
@pytest.mark.xdist_group(name="compliance_reports")
class TestComplianceReportValidation:
    """Tests for compliance report validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_report_requires_time_range(self, compliance_app: tuple) -> None:
        """GIVEN no time range WHEN requesting report THEN returns 422."""
        app, mock_service = compliance_app

        client = TestClient(app)
        response = client.get("/api/v1/compliance/reports/gdpr")

        assert response.status_code == 422

    def test_all_reports_summary(self, compliance_app: tuple) -> None:
        """GIVEN audit data WHEN requesting summary THEN returns all regulations."""
        app, mock_service = compliance_app

        mock_summary = {
            "generated_at": "2025-01-15T10:30:00Z",
            "regulations": {
                "GDPR": {"status": "compliant", "event_count": 1000},
                "HIPAA": {"status": "compliant", "event_count": 500},
                "SOC2": {"status": "compliant", "event_count": 2000},
                "FedRAMP": {"status": "compliant", "event_count": 3000},
                "EU_AI_ACT": {"status": "compliant", "event_count": 1500},
            },
            "overall_status": "compliant",
        }

        mock_service.generate_compliance_summary.return_value = mock_summary

        client = TestClient(app)
        response = client.get(
            "/api/v1/compliance/reports/summary?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z"
        )

        assert response.status_code == 200
        data = response.json()
        assert "regulations" in data
        assert "overall_status" in data
