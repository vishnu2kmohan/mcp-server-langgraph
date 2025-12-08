"""
Integration tests for Builder API endpoints.

Tests the builder API server against real infrastructure:
- Code generation from workflows
- Workflow validation
- Template listing
- Node type listing

Requires: docker-compose.test.yml services running

Run with:
    make test-infra-up
    pytest tests/integration/builder/test_builder_api_integration.py -v
"""

import gc

import pytest

from tests.constants import TEST_BUILDER_API_PORT

pytestmark = [
    pytest.mark.integration,
    pytest.mark.builder,
    pytest.mark.api,
    pytest.mark.xdist_group(name="builder_integration_tests"),
]


@pytest.fixture
def builder_url() -> str:
    """Get Builder API URL for testing."""
    return f"http://localhost:{TEST_BUILDER_API_PORT}"


@pytest.fixture
def api_client(builder_url: str):
    """Create HTTP client for Builder API."""
    import httpx

    return httpx.AsyncClient(base_url=builder_url, timeout=30.0)


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderHealth:
    """Test Builder health endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self, api_client) -> None:
        """Test health endpoint is accessible."""
        response = await api_client.get("/api/builder/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_root_returns_api_info(self, api_client) -> None:
        """Test root path returns API info (or HTML if frontend is built)."""
        response = await api_client.get("/")

        # Should return 200 with either JSON API info or HTML SPA
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        # Accept either HTML (frontend built) or JSON (API-only mode)
        assert "text/html" in content_type or "application/json" in content_type


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderTemplatesAPI:
    """Test template API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_templates(self, api_client) -> None:
        """Test listing workflow templates."""
        response = await api_client.get("/api/builder/templates")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) > 0

    @pytest.mark.asyncio
    async def test_get_template_research_agent(self, api_client) -> None:
        """Test getting a specific template."""
        response = await api_client.get("/api/builder/templates/research_agent")

        assert response.status_code == 200
        data = response.json()
        assert "template" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, api_client) -> None:
        """Test getting nonexistent template returns 404."""
        response = await api_client.get("/api/builder/templates/nonexistent-template")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_node_types(self, api_client) -> None:
        """Test listing available node types."""
        response = await api_client.get("/api/builder/node-types")

        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data
        assert isinstance(data["node_types"], list)
        assert len(data["node_types"]) > 0


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderValidation:
    """Test workflow validation endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def valid_workflow(self) -> dict:
        """
        A valid workflow for testing.

        Must match WorkflowDefinition schema:
        - name: str
        - nodes: list of NodeDefinition
        - edges: list of EdgeDefinition (from_node, to_node)
        - entry_point: str (defaults to first node id)
        """
        return {
            "workflow": {
                "name": "test_workflow",
                "description": "Test workflow",
                "nodes": [
                    {"id": "node1", "type": "llm", "config": {"model": "gpt-4"}},
                ],
                "edges": [],
                "entry_point": "node1",
            }
        }

    @pytest.fixture
    def invalid_workflow(self) -> dict:
        """An invalid workflow (missing entry point)."""
        return {
            "workflow": {
                "name": "invalid_workflow",
                "nodes": [
                    {"id": "node1", "type": "llm", "config": {}},
                ],
                "edges": [],
                "entry_point": "nonexistent",  # Invalid - doesn't exist
            }
        }

    @pytest.mark.asyncio
    async def test_validate_valid_workflow(self, api_client, valid_workflow) -> None:
        """Test validating a valid workflow."""
        response = await api_client.post(
            "/api/builder/validate",
            json=valid_workflow,
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_invalid_workflow(self, api_client, invalid_workflow) -> None:
        """Test validating an invalid workflow returns errors."""
        response = await api_client.post(
            "/api/builder/validate",
            json=invalid_workflow,
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert data["valid"] is False
        assert len(data.get("errors", [])) > 0


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderCodeGeneration:
    """Test code generation endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.fixture
    def simple_workflow(self) -> dict:
        """
        Simple workflow for code generation.

        Must match WorkflowDefinition schema for /api/builder/generate.
        """
        return {
            "workflow": {
                "name": "simple_agent",
                "description": "A simple test agent",
                "nodes": [
                    {"id": "agent", "type": "llm", "config": {"model": "gpt-4"}},
                ],
                "edges": [],
                "entry_point": "agent",
            }
        }

    @pytest.mark.asyncio
    async def test_generate_code_endpoint_exists(self, api_client, auth_headers, simple_workflow) -> None:
        """Test code generation endpoint is accessible."""
        response = await api_client.post(
            "/api/builder/generate",
            json=simple_workflow,
            headers=auth_headers,
        )

        # Should exist (may require auth or return error for incomplete workflow)
        assert response.status_code in [200, 400, 401, 403, 422]

        if response.status_code == 200:
            data = response.json()
            # Should contain generated code
            assert "code" in data


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderImportExport:
    """Test import/export functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.mark.asyncio
    async def test_import_endpoint_exists(self, api_client, auth_headers) -> None:
        """Test that import endpoint is accessible."""
        # Simple LangGraph code to import
        code = """
from langgraph.graph import StateGraph, END

def agent(state):
    return state

graph = StateGraph(dict)
graph.add_node("agent", agent)
graph.set_entry_point("agent")
graph.add_edge("agent", END)
"""
        response = await api_client.post(
            "/api/builder/import",
            json={"code": code, "layout": "hierarchical"},
            headers=auth_headers,
        )

        # Endpoint should exist and accept valid code
        # May return 200, 400 (parse error), or auth errors
        assert response.status_code in [200, 400, 401, 403, 500]


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderAPIInfo:
    """Test API info and root endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_root_returns_api_info_or_spa(self, api_client) -> None:
        """Test root returns API info when frontend not built."""
        response = await api_client.get("/")

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")

        # Accept either JSON (API info) or HTML (frontend SPA)
        if "application/json" in content_type:
            data = response.json()
            # Should have API name
            assert "name" in data or "version" in data
        else:
            # Frontend is built, should serve HTML
            assert "text/html" in content_type
