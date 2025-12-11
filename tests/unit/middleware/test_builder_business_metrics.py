"""
Tests for Builder service business metrics.

Verifies that Builder properly emits business-level metrics:
- builder_code_generation_total (Counter) - Code generation requests
- builder_code_generation_duration_seconds (Histogram) - Code gen latency
- builder_validation_total (Counter) - Workflow validations
- builder_import_total (Counter) - Code imports
- builder_workflow_node_count (Gauge) - Nodes in workflow

These metrics are scraped by Alloy and displayed in the Builder Grafana dashboard.

Follows TDD principles (RED phase - these tests define expected behavior).
"""

import gc
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.observability, pytest.mark.metrics]


@pytest.mark.xdist_group(name="builder_business_metrics")
class TestBuilderBusinessMetrics:
    """Test Builder service business metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_builder_code_generation_metric_exists(self) -> None:
        """Test that builder_code_generation_total metric is defined."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Make a code generation request
            client.post(
                "/api/builder/generate",
                json={
                    "workflow": {
                        "name": "test",
                        "description": "Test workflow",
                        "nodes": [{"id": "start", "type": "llm", "label": "Start", "config": {}}],
                        "edges": [],
                        "entry_point": "start",
                    }
                },
            )

            # Check metrics endpoint for builder metrics
            response = client.get("/metrics")
            assert response.status_code == 200

            metrics_text = response.text
            assert "builder_code_generation" in metrics_text, "Builder should emit builder_code_generation metrics"

    @pytest.mark.unit
    def test_builder_validation_metric_exists(self) -> None:
        """Test that builder_validation_total metric is defined."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Make a validation request
            client.post(
                "/api/builder/validate",
                json={
                    "workflow": {
                        "name": "test",
                        "nodes": [{"id": "start", "type": "llm", "label": "Start", "config": {}}],
                        "edges": [],
                        "entry_point": "start",
                    }
                },
            )

            # Check metrics endpoint
            response = client.get("/metrics")
            assert response.status_code == 200

            metrics_text = response.text
            assert "builder_validation" in metrics_text, "Builder should emit builder_validation metrics"

    @pytest.mark.unit
    def test_builder_import_metric_exists(self) -> None:
        """Test that builder_import_total metric is defined."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Make an import request (will fail, but metric should still be recorded)
            client.post(
                "/api/builder/import",
                json={
                    "code": "from langgraph.graph import StateGraph\ngraph = StateGraph()",
                    "layout": "hierarchical",
                },
            )

            # Check metrics endpoint
            response = client.get("/metrics")
            assert response.status_code == 200

            metrics_text = response.text
            assert "builder_import" in metrics_text, "Builder should emit builder_import metrics"
