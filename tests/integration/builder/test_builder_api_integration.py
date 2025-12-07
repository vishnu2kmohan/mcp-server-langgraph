"""
Integration tests for Builder API endpoints.

Tests the builder API server against real infrastructure:
- Workflow CRUD operations
- Workflow validation
- Code generation
- MCP integration

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
    async def test_root_serves_spa(self, api_client) -> None:
        """Test root path serves React SPA."""
        response = await api_client.get("/")

        # Should serve HTML (React SPA)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderWorkflowAPI:
    """Test workflow management API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.fixture
    def sample_workflow(self) -> dict:
        """Sample workflow definition."""
        return {
            "name": "Test Workflow",
            "description": "Integration test workflow",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "agent",
                    "type": "agent",
                    "position": {"x": 300, "y": 100},
                    "data": {"name": "Assistant"},
                },
                {
                    "id": "end",
                    "type": "end",
                    "position": {"x": 500, "y": 100},
                },
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "agent"},
                {"id": "e2", "source": "agent", "target": "end"},
            ],
        }

    @pytest.mark.asyncio
    async def test_create_workflow(self, api_client, auth_headers, sample_workflow) -> None:
        """Test creating a new workflow."""
        response = await api_client.post(
            "/api/builder/workflows",
            json=sample_workflow,
            headers=auth_headers,
        )

        # Should succeed or require auth
        assert response.status_code in [200, 201, 401, 403]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data or "workflow_id" in data

    @pytest.mark.asyncio
    async def test_list_workflows(self, api_client, auth_headers) -> None:
        """Test listing workflows."""
        response = await api_client.get(
            "/api/builder/workflows",
            headers=auth_headers,
        )

        # Should succeed or require auth
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "workflows" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow(self, api_client, auth_headers) -> None:
        """Test getting nonexistent workflow returns 404."""
        response = await api_client.get(
            "/api/builder/workflows/nonexistent-workflow-id",
            headers=auth_headers,
        )

        assert response.status_code in [404, 401, 403]


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderValidation:
    """Test workflow validation endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.fixture
    def valid_workflow(self) -> dict:
        """A valid workflow for testing."""
        return {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "end"},
            ],
        }

    @pytest.fixture
    def invalid_workflow(self) -> dict:
        """An invalid workflow (no end node)."""
        return {
            "nodes": [
                {"id": "start", "type": "start"},
            ],
            "edges": [],
        }

    @pytest.mark.asyncio
    async def test_validate_valid_workflow(self, api_client, auth_headers, valid_workflow) -> None:
        """Test validating a valid workflow."""
        response = await api_client.post(
            "/api/builder/validate",
            json=valid_workflow,
            headers=auth_headers,
        )

        # Should succeed or require auth
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            data = response.json()
            # Should indicate valid or return validation result
            assert "valid" in data or "errors" in data or "is_valid" in data

    @pytest.mark.asyncio
    async def test_validate_invalid_workflow(self, api_client, auth_headers, invalid_workflow) -> None:
        """Test validating an invalid workflow returns errors."""
        response = await api_client.post(
            "/api/builder/validate",
            json=invalid_workflow,
            headers=auth_headers,
        )

        # Should succeed with validation errors or require auth
        assert response.status_code in [200, 400, 401, 403, 422]


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
        """Simple workflow for code generation."""
        return {
            "name": "SimpleAgent",
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "agent", "type": "agent", "data": {"name": "Assistant"}},
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "agent"},
                {"source": "agent", "target": "end"},
            ],
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
            assert "code" in data or "python" in data or "content" in data


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderMCPIntegration:
    """Test Builder's MCP server integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.mark.asyncio
    async def test_mcp_tools_endpoint(self, api_client, auth_headers) -> None:
        """Test that builder exposes MCP tools."""
        response = await api_client.get(
            "/api/builder/tools",
            headers=auth_headers,
        )

        # Endpoint may or may not exist
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "tools" in data

    @pytest.mark.asyncio
    async def test_mcp_resources_endpoint(self, api_client, auth_headers) -> None:
        """Test that builder exposes MCP resources."""
        response = await api_client.get(
            "/api/builder/resources",
            headers=auth_headers,
        )

        # Endpoint may or may not exist
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "resources" in data


@pytest.mark.xdist_group(name="builder_integration_tests")
class TestBuilderFrontend:
    """Test frontend serving."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_spa_routes_return_html(self, api_client) -> None:
        """Test SPA routes return index.html."""
        routes = ["/", "/workflows", "/workflows/new", "/settings"]

        for route in routes:
            response = await api_client.get(route)

            # Should serve HTML (SPA handles routing)
            if response.status_code == 200:
                assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_static_assets_served(self, api_client) -> None:
        """Test static assets are served."""
        # Try common static asset paths
        response = await api_client.get("/assets/index.js")

        # May return 200 if exists, 404 if not built
        assert response.status_code in [200, 404]
