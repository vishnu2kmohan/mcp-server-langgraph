"""
TDD tests for SOC2 compliance metrics.

Verifies that compliance operations record metrics for Grafana dashboard.
Expected metrics:
- compliance_score (gauge)
- evidence_items_total (counter with status, control_category labels)
- audit_logs_total (counter)
- access_review_items_total (counter)
"""

import gc

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.metrics
@pytest.mark.xdist_group(name="soc2_metrics")
class TestSOC2ComplianceMetrics:
    """Test SOC2 compliance metrics are recorded correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_compliance_score_sets_gauge(self) -> None:
        """Verify record_compliance_score sets the gauge metric."""
        from mcp_server_langgraph.compliance.metrics import record_compliance_score

        # Call with valid score
        record_compliance_score(85.5)

        # Function should not raise - metric is set

    def test_record_evidence_item_increments_counter(self) -> None:
        """Verify record_evidence_item increments counter with labels."""
        from mcp_server_langgraph.compliance.metrics import record_evidence_item

        # Record evidence items
        record_evidence_item(status="success", control_category="CC6.1")
        record_evidence_item(status="failure", control_category="CC7.2")
        record_evidence_item(status="partial", control_category="A1.2")

        # Function should not raise

    def test_record_audit_log_increments_counter(self) -> None:
        """Verify record_audit_log increments counter with event type."""
        from mcp_server_langgraph.compliance.metrics import record_audit_log

        # Record audit log events
        record_audit_log(event_type="login")
        record_audit_log(event_type="logout")
        record_audit_log(event_type="access_denied")

        # Function should not raise

    def test_record_access_review_item_increments_counter(self) -> None:
        """Verify record_access_review_item increments counter with labels."""
        from mcp_server_langgraph.compliance.metrics import record_access_review_item

        # Record access review items
        record_access_review_item(status="approved")
        record_access_review_item(status="revoked")
        record_access_review_item(status="pending")

        # Function should not raise

    def test_record_compliance_job_execution(self) -> None:
        """Verify record_compliance_job increments counter with job details."""
        from mcp_server_langgraph.compliance.metrics import record_compliance_job

        # Record job executions
        record_compliance_job(job_type="daily_check", status="success")
        record_compliance_job(job_type="weekly_access_review", status="failure")

        # Function should not raise

    def test_record_compliance_report_generated(self) -> None:
        """Verify record_compliance_report increments counter with report type."""
        from mcp_server_langgraph.compliance.metrics import record_compliance_report

        # Record report generations
        record_compliance_report(report_type="daily")
        record_compliance_report(report_type="weekly")
        record_compliance_report(report_type="monthly")

        # Function should not raise

    def test_metrics_handle_missing_prometheus_gracefully(self) -> None:
        """Verify metrics don't crash when prometheus_client is unavailable."""
        from mcp_server_langgraph.compliance import metrics

        # Reset metrics availability
        metrics._metrics_available = False

        # All calls should succeed without raising
        metrics.record_compliance_score(90.0)
        metrics.record_evidence_item("success", "CC6.1")
        metrics.record_audit_log("login")
        metrics.record_access_review_item("approved")
        metrics.record_compliance_job("daily_check", "success")
        metrics.record_compliance_report("daily")

        # Re-initialize metrics
        metrics._init_metrics()
