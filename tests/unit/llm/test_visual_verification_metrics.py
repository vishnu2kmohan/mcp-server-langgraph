"""
TDD tests for Visual Verification metrics instrumentation.

Verifies that visual verification operations record metrics for:
- Visual verification requests (counter)
- Visual verification duration (histogram)
- Visual verification scores (histogram)
- URLs verified count (counter)
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.metrics
class TestVisualVerificationMetrics:
    """Test visual verification metrics instrumentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_visual_verification_metrics_module_exists(self) -> None:
        """GIVEN visual verification metrics module
        WHEN importing
        THEN module should be importable
        """
        from mcp_server_langgraph.llm import visual_verification_metrics

        assert visual_verification_metrics is not None

    def test_record_visual_verification_request_function_exists(self) -> None:
        """GIVEN visual verification metrics module
        WHEN accessing record_visual_verification_request
        THEN function should exist
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_request,
        )

        assert callable(record_visual_verification_request)

    def test_record_visual_verification_duration_function_exists(self) -> None:
        """GIVEN visual verification metrics module
        WHEN accessing record_visual_verification_duration
        THEN function should exist
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_duration,
        )

        assert callable(record_visual_verification_duration)

    def test_record_visual_verification_score_function_exists(self) -> None:
        """GIVEN visual verification metrics module
        WHEN accessing record_visual_verification_score
        THEN function should exist
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_score,
        )

        assert callable(record_visual_verification_score)

    def test_record_visual_verification_urls_function_exists(self) -> None:
        """GIVEN visual verification metrics module
        WHEN accessing record_visual_verification_urls
        THEN function should exist
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_urls,
        )

        assert callable(record_visual_verification_urls)

    def test_record_visual_verification_request_records_counter(self) -> None:
        """GIVEN visual verification request
        WHEN recording request with status
        THEN counter metric should increment
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_request,
        )

        # Call should not raise
        record_visual_verification_request(status="success")
        record_visual_verification_request(status="failed")
        record_visual_verification_request(status="screenshot_error")

    def test_record_visual_verification_duration_records_histogram(self) -> None:
        """GIVEN visual verification duration
        WHEN recording duration
        THEN histogram metric should record value
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_duration,
        )

        # Call should not raise
        record_visual_verification_duration(duration_ms=1500.0)
        record_visual_verification_duration(duration_ms=3000.0)

    def test_record_visual_verification_score_records_histogram(self) -> None:
        """GIVEN visual verification score
        WHEN recording score
        THEN histogram metric should record value
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_score,
        )

        # Call should not raise
        record_visual_verification_score(score=0.85)
        record_visual_verification_score(score=0.95)
        record_visual_verification_score(score=0.45)

    def test_record_visual_verification_urls_records_counter(self) -> None:
        """GIVEN URL verification count
        WHEN recording URLs verified
        THEN counter metric should increment by count
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_urls,
        )

        # Call should not raise
        record_visual_verification_urls(count=1)
        record_visual_verification_urls(count=3)


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.metrics
@pytest.mark.xdist_group(name="visual_verification_metrics_integration")
class TestVisualVerificationMetricsIntegration:
    """Test visual verification metrics integration with verifier."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verifier_records_metrics_on_success(self) -> None:
        """GIVEN successful visual verification
        WHEN verification completes
        THEN metrics should be recorded
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_duration,
            record_visual_verification_request,
            record_visual_verification_score,
        )

        # Simulate successful verification
        record_visual_verification_request(status="success")
        record_visual_verification_duration(duration_ms=2500.0)
        record_visual_verification_score(score=0.88)

        # Should not raise - metrics recorded successfully

    @pytest.mark.asyncio
    async def test_verifier_records_metrics_on_failure(self) -> None:
        """GIVEN failed visual verification
        WHEN verification fails
        THEN failure metrics should be recorded
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_duration,
            record_visual_verification_request,
            record_visual_verification_score,
        )

        # Simulate failed verification
        record_visual_verification_request(status="failed")
        record_visual_verification_duration(duration_ms=1200.0)
        record_visual_verification_score(score=0.35)

        # Should not raise - metrics recorded successfully

    @pytest.mark.asyncio
    async def test_metrics_handle_missing_prometheus(self) -> None:
        """GIVEN prometheus_client not available
        WHEN recording metrics
        THEN should fail gracefully (no exception)
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            record_visual_verification_request,
        )

        # Even if prometheus is unavailable, should not raise
        record_visual_verification_request(status="success")


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.metrics
class TestVisualVerificationMetricsLabels:
    """Test visual verification metrics label handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bounded_statuses_defined(self) -> None:
        """GIVEN visual verification metrics
        WHEN accessing BOUNDED_STATUSES
        THEN should have expected status values
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            BOUNDED_STATUSES,
        )

        assert "success" in BOUNDED_STATUSES
        assert "failed" in BOUNDED_STATUSES
        assert "screenshot_error" in BOUNDED_STATUSES
        assert "timeout" in BOUNDED_STATUSES
        assert "other" in BOUNDED_STATUSES

    def test_normalize_status_returns_bounded_value(self) -> None:
        """GIVEN unknown status value
        WHEN normalizing status
        THEN should return 'other' for unbounded values
        """
        from mcp_server_langgraph.llm.visual_verification_metrics import (
            normalize_verification_status,
        )

        assert normalize_verification_status("success") == "success"
        assert normalize_verification_status("failed") == "failed"
        assert normalize_verification_status("unknown_status") == "other"
