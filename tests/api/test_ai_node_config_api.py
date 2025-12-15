"""
Tests for AI Node Configuration API

TDD: Tests written for the node config help endpoints.

Follows memory safety patterns for pytest-xdist.
"""

import gc

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.fixture
def app():
    """Create a test FastAPI app with the AI router."""
    from mcp_server_langgraph.api.v1.ai import ai_router

    app = FastAPI()
    app.include_router(ai_router, prefix="/api/v1/ai")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.mark.xdist_group(name="ai_api")
class TestNodeConfigHelp:
    """Tests for POST /api/v1/ai/node-config/help"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_help_for_llm_node_returns_guidance(self, client):
        """Should return configuration help for LLM node type."""
        response = client.post(
            "/api/v1/ai/node-config/help",
            json={
                "node_type": "llm",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "help_text" in data
        assert "suggested_config" in data
        assert "examples" in data
        assert "llm" in data["help_text"].lower() or "model" in data["help_text"].lower()

    def test_get_help_for_tool_node_returns_guidance(self, client):
        """Should return configuration help for tool node type."""
        response = client.post(
            "/api/v1/ai/node-config/help",
            json={
                "node_type": "tool",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "help_text" in data
        assert "suggested_config" in data

    def test_get_help_with_context_includes_suggestions(self, client):
        """Should include connection suggestions when context has existing nodes."""
        response = client.post(
            "/api/v1/ai/node-config/help",
            json={
                "node_type": "llm",
                "context": {
                    "existing_nodes": [
                        {"id": "input-1", "type": "input"},
                        {"id": "output-1", "type": "output"},
                    ],
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggested_connections" in data

    def test_get_help_for_input_node(self, client):
        """Should return configuration help for input node type."""
        response = client.post(
            "/api/v1/ai/node-config/help",
            json={"node_type": "input"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "help_text" in data

    def test_get_help_for_output_node(self, client):
        """Should return configuration help for output node type."""
        response = client.post(
            "/api/v1/ai/node-config/help",
            json={"node_type": "output"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "help_text" in data

    def test_get_help_for_unknown_node_type_returns_default(self, client):
        """Should return generic help for unknown node types."""
        response = client.post(
            "/api/v1/ai/node-config/help",
            json={"node_type": "unknown_type"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "help_text" in data


@pytest.mark.xdist_group(name="ai_api")
class TestNodeConfigValidate:
    """Tests for POST /api/v1/ai/node-config/validate"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_valid_llm_config(self, client):
        """Should validate a complete LLM configuration."""
        response = client.post(
            "/api/v1/ai/node-config/validate",
            json={
                "node_type": "llm",
                "config": {
                    "model": "gpt-4",
                    "temperature": 0.7,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_invalid_llm_config_missing_model(self, client):
        """Should return errors for LLM config missing required model."""
        response = client.post(
            "/api/v1/ai/node-config/validate",
            json={
                "node_type": "llm",
                "config": {
                    "temperature": 0.7,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("model" in err.lower() for err in data["errors"])

    def test_validate_config_with_wrong_type(self, client):
        """Should return errors for config with wrong field types."""
        response = client.post(
            "/api/v1/ai/node-config/validate",
            json={
                "node_type": "llm",
                "config": {
                    "model": "gpt-4",
                    "temperature": "not-a-number",  # Should be number
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_config_with_unknown_fields(self, client):
        """Should return warnings for unknown fields."""
        response = client.post(
            "/api/v1/ai/node-config/validate",
            json={
                "node_type": "llm",
                "config": {
                    "model": "gpt-4",
                    "unknown_field": "value",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Valid because required fields are present
        assert data["valid"] is True
        # But should have warnings about unknown fields
        assert len(data["warnings"]) > 0

    def test_validate_unknown_node_type(self, client):
        """Should return invalid for unknown node types."""
        response = client.post(
            "/api/v1/ai/node-config/validate",
            json={
                "node_type": "unknown_type",
                "config": {"foo": "bar"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("unknown" in err.lower() for err in data["errors"])


@pytest.mark.xdist_group(name="ai_api")
class TestNodeTypes:
    """Tests for GET /api/v1/ai/node-types"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_all_node_types(self, client):
        """Should return all available node types."""
        response = client.get("/api/v1/ai/node-types")
        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data
        assert "llm" in data["node_types"]
        assert "tool" in data["node_types"]
        assert "input" in data["node_types"]
        assert "output" in data["node_types"]

    def test_get_node_type_schema(self, client):
        """Should return schema for a specific node type."""
        response = client.get("/api/v1/ai/node-types/llm/schema")
        assert response.status_code == 200
        data = response.json()
        assert "type" in data
        assert "properties" in data
        assert "model" in data["properties"]

    def test_get_schema_for_unknown_type_returns_404(self, client):
        """Should return 404 for unknown node type."""
        response = client.get("/api/v1/ai/node-types/unknown_type/schema")
        assert response.status_code == 404
