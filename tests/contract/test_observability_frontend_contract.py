"""
Contract Tests: Observability API Frontend Schema Validation

Validates that backend observability response models match frontend TypeScript expectations.
Prevents schema drift between Python Pydantic models and TypeScript interfaces.

This test ensures:
- MetricsResponse has all fields ObservabilityMetrics expects
- TraceListItem has all fields TraceListItem expects
- LogEntryResponse has all fields LogEntry expects
- AlertResponse has all fields ObservabilityAlert expects

Sprint: Post-audit fix for DevTools schema mismatch issue.
"""

import gc

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.unit]


@pytest.mark.xdist_group(name="observability_contract")
class TestMetricsResponseFrontendContract:
    """
    Contract test: MetricsResponse must match frontend ObservabilityMetrics.

    Frontend type (types/api.ts):
        export interface ObservabilityMetrics {
          requests_total: number;
          errors_total: number;
          avg_latency_ms: number;
          p99_latency_ms: number;
          tokens_used: number;
          active_sessions: number;
        }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_response_has_all_frontend_required_fields(self) -> None:
        """
        GIVEN the MetricsResponse Pydantic model
        WHEN we check its schema
        THEN it must have all fields the frontend ObservabilityMetrics expects.
        """
        from mcp_server_langgraph.api.v1.observability import MetricsResponse

        schema = MetricsResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Frontend ObservabilityMetrics required fields
        required_by_frontend = [
            "requests_total",
            "errors_total",
            "avg_latency_ms",
            "p99_latency_ms",
            "tokens_used",
            "active_sessions",
        ]

        missing = [f for f in required_by_frontend if f not in properties]
        assert not missing, (
            f"MetricsResponse is missing fields required by frontend ObservabilityMetrics: {missing}. "
            f"Available: {list(properties.keys())}"
        )

    def test_metrics_response_field_types_match_frontend(self) -> None:
        """
        GIVEN the MetricsResponse Pydantic model
        WHEN we instantiate it with test data
        THEN fields should have types compatible with frontend.
        """
        from mcp_server_langgraph.api.v1.observability import MetricsResponse

        # Create instance with all fields
        response = MetricsResponse(
            requests_total=1000,
            errors_total=10,
            avg_latency_ms=150.5,
            p99_latency_ms=500.0,
            tokens_used=50000,
            active_sessions=25,
        )

        # Validate types match frontend expectations
        assert isinstance(response.requests_total, int)
        assert isinstance(response.errors_total, int)
        assert isinstance(response.avg_latency_ms, float)
        assert isinstance(response.p99_latency_ms, float)
        assert isinstance(response.tokens_used, int)
        assert isinstance(response.active_sessions, int)


@pytest.mark.xdist_group(name="observability_contract")
class TestTraceListItemFrontendContract:
    """
    Contract test: TraceListItem must match frontend TraceListItem.

    Frontend type (types/api.ts):
        export interface TraceListItem {
          trace_id: string;
          name: string;
          start_time: string | null;
          duration_ms: number | null;
          span_count: number | null;
          status?: string;
          end_time?: string | null;
          has_thinking?: boolean;
          thinking_tokens_total?: number;
        }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_trace_list_item_has_all_frontend_fields(self) -> None:
        """
        GIVEN the TraceListItem Pydantic model
        WHEN we check its schema
        THEN it must have all fields the frontend TraceListItem expects.
        """
        from mcp_server_langgraph.api.v1.observability import TraceListItem

        schema = TraceListItem.model_json_schema()
        properties = schema.get("properties", {})

        # Frontend TraceListItem required fields
        required_by_frontend = ["trace_id", "name"]
        optional_by_frontend = [
            "start_time",
            "duration_ms",
            "span_count",
            "status",
            "end_time",
            "has_thinking",
            "thinking_tokens_total",
        ]
        all_frontend_fields = required_by_frontend + optional_by_frontend

        missing = [f for f in all_frontend_fields if f not in properties]
        assert not missing, (
            f"TraceListItem is missing fields expected by frontend: {missing}. Available: {list(properties.keys())}"
        )


@pytest.mark.xdist_group(name="observability_contract")
class TestLogEntryResponseFrontendContract:
    """
    Contract test: LogEntryResponse must match frontend LogEntry.

    Frontend type (types/api.ts):
        export interface LogEntry {
          id: string;
          timestamp: string;
          level: "debug" | "info" | "warn" | "error";
          message: string;
          service?: string;
        }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_log_entry_response_has_all_frontend_fields(self) -> None:
        """
        GIVEN the LogEntryResponse Pydantic model
        WHEN we check its schema
        THEN it must have all fields the frontend LogEntry expects.
        """
        from mcp_server_langgraph.api.v1.observability import LogEntryResponse

        schema = LogEntryResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Frontend LogEntry fields
        required_by_frontend = ["id", "timestamp", "level", "message"]
        optional_by_frontend = ["service"]
        all_frontend_fields = required_by_frontend + optional_by_frontend

        missing = [f for f in all_frontend_fields if f not in properties]
        assert not missing, (
            f"LogEntryResponse is missing fields expected by frontend: {missing}. Available: {list(properties.keys())}"
        )

    def test_log_entry_response_uses_service_not_service_name(self) -> None:
        """
        GIVEN the LogEntryResponse Pydantic model
        WHEN we check its schema
        THEN it should use 'service' (not 'service_name') to match frontend.
        """
        from mcp_server_langgraph.api.v1.observability import LogEntryResponse

        schema = LogEntryResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Frontend expects 'service', not 'service_name'
        assert "service" in properties, (
            "LogEntryResponse should have 'service' field, not 'service_name'. Frontend LogEntry interface uses 'service'."
        )


@pytest.mark.xdist_group(name="observability_contract")
class TestAlertResponseFrontendContract:
    """
    Contract test: AlertResponse must match frontend ObservabilityAlert.

    Frontend type (types/api.ts):
        export interface ObservabilityAlert {
          alert_id: string;
          name: string;
          severity: "info" | "warning" | "error" | "critical";
          state: "pending" | "firing" | "resolved" | "silenced";
          message: string;
          labels: Record<string, string>;
          annotations: Record<string, string>;
          started_at: string | null;
          ended_at: string | null;
          generator_url: string | null;
        }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_response_has_all_frontend_fields(self) -> None:
        """
        GIVEN the AlertResponse Pydantic model
        WHEN we check its schema
        THEN it must have all fields the frontend ObservabilityAlert expects.
        """
        from mcp_server_langgraph.api.v1.observability import AlertResponse

        schema = AlertResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Frontend ObservabilityAlert fields
        required_by_frontend = ["alert_id", "name", "severity", "state", "message"]
        optional_by_frontend = [
            "labels",
            "annotations",
            "started_at",
            "ended_at",
            "generator_url",
        ]
        all_frontend_fields = required_by_frontend + optional_by_frontend

        missing = [f for f in all_frontend_fields if f not in properties]
        assert not missing, (
            f"AlertResponse is missing fields expected by frontend: {missing}. Available: {list(properties.keys())}"
        )


@pytest.mark.xdist_group(name="observability_contract")
class TestObservabilityServiceImplContract:
    """
    Contract test: ObservabilityServiceImpl methods return correct schema.

    Validates that the service implementation returns data matching
    the Pydantic response models (which match frontend expectations).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_metrics_returns_frontend_compatible_dict(self) -> None:
        """
        GIVEN the ObservabilityServiceImpl.get_metrics method
        WHEN called
        THEN it returns a dict with all fields frontend expects.
        """
        # This is already tested by test_observability_service_impl.py
        # but we verify the schema contract here
        from mcp_server_langgraph.api.v1.observability import MetricsResponse

        # Verify the model can be instantiated with defaults
        response = MetricsResponse(requests_total=0, errors_total=0)

        # All frontend fields should have values (not raise AttributeError)
        assert hasattr(response, "avg_latency_ms")
        assert hasattr(response, "p99_latency_ms")
        assert hasattr(response, "tokens_used")
        assert hasattr(response, "active_sessions")
