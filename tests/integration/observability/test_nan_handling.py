"""
Integration tests for NaN/Inf handling in observability endpoints.

These tests verify that NaN and Inf values from Prometheus (or other metrics
sources) don't break JSON serialization in API responses.

Problem Context:
    Prometheus histogram_quantile() returns NaN when there's no data in
    histogram buckets. Python's json encoder raises ValueError for NaN/Inf:
        ValueError: Out of range float values are not JSON compliant

Solution:
    Use safe_* functions from mcp_server_langgraph.core.numeric at data
    boundaries to convert NaN/Inf to safe defaults before JSON serialization.

Reference:
    - mcp_server_langgraph.core.numeric (safe_float, safe_average, etc.)
    - ADR-0026 - Cost Tracking Enhancements
"""

from __future__ import annotations

import gc
import json
import math
from decimal import Decimal

import pytest

from mcp_server_langgraph.core.numeric import (
    safe_average,
    safe_divide,
    safe_float,
    safe_round,
    safe_sum,
)

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.observability
@pytest.mark.xdist_group(name="nan_handling")
class TestNaNHandlingIntegration:
    """Integration tests for NaN handling in observability data flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Direct Numeric Utility Tests
    # =========================================================================

    def test_safe_float_handles_nan(self) -> None:
        """Verify safe_float converts NaN to default."""
        result = safe_float(float("nan"))
        assert result == 0.0
        assert math.isfinite(result)

    def test_safe_float_handles_inf(self) -> None:
        """Verify safe_float converts Inf to default."""
        assert safe_float(float("inf")) == 0.0
        assert safe_float(float("-inf")) == 0.0

    def test_safe_float_handles_none(self) -> None:
        """Verify safe_float converts None to default."""
        assert safe_float(None) == 0.0

    def test_safe_float_preserves_valid_values(self) -> None:
        """Verify safe_float passes through valid floats."""
        assert safe_float(1.5) == 1.5
        assert safe_float(-42.0) == -42.0
        assert safe_float(0.0) == 0.0

    def test_safe_average_with_nan_values(self) -> None:
        """Verify safe_average filters NaN from list."""
        values = [1.0, float("nan"), 2.0, float("inf"), 3.0]
        result = safe_average(values)
        assert result == 2.0  # (1+2+3)/3
        assert math.isfinite(result)

    def test_safe_average_empty_list(self) -> None:
        """Verify safe_average returns default for empty list."""
        assert safe_average([]) == 0.0
        assert safe_average([], default=42.0) == 42.0

    def test_safe_average_all_nan(self) -> None:
        """Verify safe_average returns default when all values are NaN."""
        values = [float("nan"), float("inf"), float("-inf")]
        assert safe_average(values) == 0.0

    def test_safe_divide_by_zero(self) -> None:
        """Verify safe_divide handles division by zero."""
        assert safe_divide(10.0, 0.0) == 0.0
        assert safe_divide(1.0, 0.0, default=-1.0) == -1.0

    def test_safe_divide_nan_inputs(self) -> None:
        """Verify safe_divide handles NaN inputs."""
        assert safe_divide(float("nan"), 2.0) == 0.0
        assert safe_divide(1.0, float("nan")) == 0.0

    def test_safe_divide_valid(self) -> None:
        """Verify safe_divide works for valid inputs."""
        assert safe_divide(10.0, 2.0) == 5.0
        assert safe_divide(100.0, 4.0) == 25.0

    def test_safe_round_nan(self) -> None:
        """Verify safe_round handles NaN."""
        assert safe_round(float("nan"), 2) == 0.0
        assert safe_round(float("inf"), 2) == 0.0

    def test_safe_round_valid(self) -> None:
        """Verify safe_round works for valid inputs."""
        assert safe_round(1.567, 2) == 1.57
        assert safe_round(42.999, 1) == 43.0

    def test_safe_sum_with_nan(self) -> None:
        """Verify safe_sum filters NaN values."""
        values = [1.0, float("nan"), 2.0, 3.0]
        assert safe_sum(values) == 6.0

    # =========================================================================
    # JSON Serialization Tests
    # =========================================================================

    def test_json_serialization_after_safe_float(self) -> None:
        """Verify values can be serialized after safe_float conversion."""
        dangerous_values = [float("nan"), float("inf"), float("-inf"), None]

        for value in dangerous_values:
            safe_value = safe_float(value)
            # This would raise ValueError if NaN/Inf were present
            result = json.dumps({"value": safe_value})
            assert isinstance(result, str)
            parsed = json.loads(result)
            assert parsed["value"] == 0.0

    def test_response_dict_with_safe_values(self) -> None:
        """Verify a response-like dict serializes correctly after safe conversion."""
        # Simulate raw metrics with NaN
        raw_metrics = {
            "latency_p50": float("nan"),
            "latency_p95": float("inf"),
            "error_rate": None,
            "success_rate": 0.95,
        }

        # Apply safe conversion (as our API endpoints do)
        safe_metrics = {
            "latency_p50": safe_float(raw_metrics["latency_p50"]),
            "latency_p95": safe_float(raw_metrics["latency_p95"]),
            "error_rate": safe_float(raw_metrics["error_rate"]),
            "success_rate": safe_float(raw_metrics["success_rate"]),
        }

        # This should not raise
        json_str = json.dumps(safe_metrics)
        parsed = json.loads(json_str)

        assert parsed["latency_p50"] == 0.0
        assert parsed["latency_p95"] == 0.0
        assert parsed["error_rate"] == 0.0
        assert parsed["success_rate"] == 0.95

    # =========================================================================
    # Budget Calculation Tests (Decimal-based)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_budget_percentage_calculation_safety(self) -> None:
        """Verify budget percentage calculations don't produce NaN."""
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budget = Budget(
            entity_type="organization",
            entity_id="test-org",
            monthly_limit_usd=Decimal("1000.00"),
        )

        checker = BudgetChecker()

        # Normal case
        status = await checker.check(budget, Decimal("500.00"))
        assert math.isfinite(status.percent_used)
        assert status.percent_used == 50.0

        # Zero spend case
        status = await checker.check(budget, Decimal("0.00"))
        assert math.isfinite(status.percent_used)
        assert status.percent_used == 0.0

    # =========================================================================
    # Pydantic Model Validation Tests
    # =========================================================================

    def test_budget_alert_payload_nan_validation(self) -> None:
        """Verify BudgetAlertPayload validates NaN values."""
        from mcp_server_langgraph.websocket.protocols import (
            BudgetAlertPayload,
            BudgetAlertStatus,
            BudgetEntityType,
        )

        # Create payload with NaN percent_used
        payload = BudgetAlertPayload(
            entity_type=BudgetEntityType.ORGANIZATION,
            entity_id="test-org",
            status=BudgetAlertStatus.WARNING,
            percent_used=float("nan"),  # Should be converted to 0.0
            current_spend="500.00",
            remaining="500.00",
            monthly_limit_usd="1000.00",
            message="Test message",
        )

        # Verify NaN was converted to 0.0 by field validator
        assert payload.percent_used == 0.0
        assert math.isfinite(payload.percent_used)

        # Verify JSON serialization works
        json_str = payload.model_dump_json()
        assert isinstance(json_str, str)

    def test_budget_status_response_nan_validation(self) -> None:
        """Verify BudgetStatusResponse validates NaN values."""
        from mcp_server_langgraph.api.v1.cost import BudgetStatusResponse

        # Create response with NaN values
        response = BudgetStatusResponse(
            status="warning",
            percent_used=float("nan"),
            current_spend=float("inf"),
            remaining=float("-inf"),
            monthly_limit=1000.0,
            entity_type="organization",
            entity_id="test-org",
            message="Test",
        )

        # Verify NaN/Inf values were converted
        assert response.percent_used == 0.0
        assert response.current_spend == 0.0
        assert response.remaining == 0.0
        assert response.monthly_limit == 1000.0

        # Verify JSON serialization works
        json_str = response.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["percent_used"] == 0.0

    # =========================================================================
    # SLA Calculation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_sla_compliance_percentage_safety(self) -> None:
        """Verify SLA compliance calculations produce finite values."""
        from mcp_server_langgraph.monitoring.sla import (
            SLAMeasurement,
            SLAMetric,
            SLAStatus,
        )

        # Create measurement with calculated compliance
        measurement = SLAMeasurement(
            metric=SLAMetric.UPTIME,
            measured_value=99.5,
            target_value=99.9,
            unit="%",
            status=SLAStatus.AT_RISK,
            compliance_percentage=safe_divide(99.5, 99.9) * 100,
            timestamp="2025-01-07T00:00:00Z",
            period_start="2025-01-01T00:00:00Z",
            period_end="2025-01-07T00:00:00Z",
        )

        assert math.isfinite(measurement.compliance_percentage)
        # Verify JSON serialization
        json_str = measurement.model_dump_json()
        assert isinstance(json_str, str)


@pytest.mark.integration
@pytest.mark.observability
@pytest.mark.xdist_group(name="nan_handling_api")
class TestNaNHandlingAPIFlow:
    """Tests for NaN handling in API response flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prometheus_query_result_with_empty_values(self) -> None:
        """Verify Prometheus query results handle empty values correctly."""
        from mcp_server_langgraph.monitoring.prometheus_client import QueryResult

        # Create a query result with no values (would produce NaN in naive impl)
        result = QueryResult(
            metric={"job": "test"},
            values=[],  # Empty values that might produce NaN average
        )

        # get_average() should return None for empty, not NaN
        avg = result.get_average()
        assert avg is None  # Empty returns None

    def test_prometheus_query_result_with_valid_values(self) -> None:
        """Verify Prometheus query results work with valid values."""
        from datetime import datetime

        from mcp_server_langgraph.monitoring.prometheus_client import (
            MetricValue,
            QueryResult,
        )

        # Create query result with values
        result = QueryResult(
            metric={"job": "test"},
            values=[
                MetricValue(timestamp=datetime.now(), value=10.0),
                MetricValue(timestamp=datetime.now(), value=20.0),
            ],
        )

        avg = result.get_average()
        assert avg is not None
        assert avg == 15.0  # (10+20)/2
        assert math.isfinite(avg)

    def test_heart_metrics_score_serialization(self) -> None:
        """Verify heart metrics scores are JSON-serializable after safe conversion."""
        # Simulate the pattern used in heart_metrics.py
        # The service applies safe_round before building payloads
        score = float("nan")
        safe_score = safe_round(score, 1)

        payload_data = {
            "score": safe_score,
            "status": "warning",
            "timestamp": "2025-01-07T00:00:00Z",
            "components": [],
        }

        # Verify the data is JSON-serializable
        json_str = json.dumps(payload_data)
        parsed = json.loads(json_str)
        assert parsed["score"] == 0.0
        assert math.isfinite(parsed["score"])


@pytest.mark.integration
@pytest.mark.observability
@pytest.mark.xdist_group(name="nan_high_priority")
class TestHighPriorityNaNValidation:
    """Tests for HIGH priority NaN validators (TDD - write tests first)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_anomaly_detection_response_nan_z_score(self) -> None:
        """Verify AnomalyDetectionResponse validates NaN z_score."""
        from mcp_server_langgraph.api.v1.cost import AnomalyDetectionResponse

        response = AnomalyDetectionResponse(
            is_anomaly=True,
            severity="critical",
            z_score=float("nan"),
            mean=100.0,
            std_dev=10.0,
            message="Test",
        )
        assert response.z_score == 0.0
        assert math.isfinite(response.z_score)

    def test_anomaly_detection_response_nan_mean(self) -> None:
        """Verify AnomalyDetectionResponse validates NaN mean."""
        from mcp_server_langgraph.api.v1.cost import AnomalyDetectionResponse

        response = AnomalyDetectionResponse(
            is_anomaly=False,
            severity="none",
            z_score=1.5,
            mean=float("nan"),
            std_dev=float("inf"),
            message="Test",
        )
        assert response.mean == 0.0
        assert response.std_dev == 0.0
        assert math.isfinite(response.mean)
        assert math.isfinite(response.std_dev)

    def test_anomaly_detection_response_json_serialization(self) -> None:
        """Verify AnomalyDetectionResponse serializes with NaN inputs."""
        from mcp_server_langgraph.api.v1.cost import AnomalyDetectionResponse

        response = AnomalyDetectionResponse(
            is_anomaly=True,
            severity="warning",
            z_score=float("inf"),
            mean=float("-inf"),
            std_dev=float("nan"),
            message="Test",
        )
        json_str = response.model_dump_json()
        assert "NaN" not in json_str
        assert "Infinity" not in json_str

    def test_forecast_response_nan_projected_total(self) -> None:
        """Verify ForecastResponse validates NaN projected_total."""
        from mcp_server_langgraph.api.v1.cost import ForecastResponse

        response = ForecastResponse(
            projected_total=float("nan"),
            confidence_low=float("inf"),
            confidence_high=float("-inf"),
            trend="stable",
            days_analyzed=7,
            message="Test",
        )
        assert response.projected_total == 0.0
        assert response.confidence_low == 0.0
        assert response.confidence_high == 0.0

    def test_forecast_response_json_serialization(self) -> None:
        """Verify ForecastResponse serializes with NaN inputs."""
        from mcp_server_langgraph.api.v1.cost import ForecastResponse

        response = ForecastResponse(
            projected_total=float("nan"),
            confidence_low=100.0,
            confidence_high=float("inf"),
            trend="increasing",
            days_analyzed=30,
            message="Test",
        )
        json_str = response.model_dump_json()
        assert "NaN" not in json_str
        assert "Infinity" not in json_str

    def test_suggestion_response_nan_confidence(self) -> None:
        """Verify SuggestionResponsePayload validates NaN confidence."""
        from mcp_server_langgraph.websocket.protocols import SuggestionResponsePayload

        payload = SuggestionResponsePayload(
            suggestion_id="test-123",
            text="Test suggestion",
            confidence=float("nan"),
        )
        assert payload.confidence == 0.0
        assert math.isfinite(payload.confidence)

    def test_suggestion_response_json_serialization(self) -> None:
        """Verify SuggestionResponsePayload serializes with NaN inputs."""
        from mcp_server_langgraph.websocket.protocols import SuggestionResponsePayload

        payload = SuggestionResponsePayload(
            suggestion_id="test-456",
            text="Test suggestion",
            confidence=float("inf"),
        )
        json_str = payload.model_dump_json()
        assert "Infinity" not in json_str


@pytest.mark.xdist_group("test_na_n_edge_cases")
@pytest.mark.integration
@pytest.mark.observability
class TestNaNEdgeCases:
    """Edge case tests for NaN handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chained_safe_operations(self) -> None:
        """Verify chained safe operations work correctly."""
        # Simulate: avg of percentiles, then divide by total, then round
        percentiles = [float("nan"), 100.0, float("inf"), 200.0]
        avg = safe_average(percentiles)  # Should be 150.0 (100+200)/2
        ratio = safe_divide(avg, 300.0)  # 150/300 = 0.5
        result = safe_round(ratio * 100, 1)  # 50.0

        assert result == 50.0
        assert math.isfinite(result)

    def test_all_operations_with_pure_nan_input(self) -> None:
        """Verify all operations handle all-NaN inputs gracefully."""
        nan_list = [float("nan")] * 10

        assert safe_average(nan_list) == 0.0
        assert safe_sum(nan_list) == 0.0
        assert safe_float(float("nan")) == 0.0
        assert safe_divide(float("nan"), float("nan")) == 0.0
        assert safe_round(float("nan"), 2) == 0.0

    def test_numeric_overflow_to_inf(self) -> None:
        """Verify operations handle numeric overflow gracefully."""
        # This can produce Inf
        huge = 1e308
        result = huge * 10  # Overflows to Inf

        assert math.isinf(result)
        assert safe_float(result) == 0.0  # Safely converted
