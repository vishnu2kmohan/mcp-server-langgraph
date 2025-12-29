"""
MCP Aggregated Router Unit Tests.

Tests for /api/v1/mcp/aggregated/* endpoints per TDD methodology.
Validates the integration with CachedUnifiedRegistry for cache-aside pattern.

Reference: MCP Protocol 2025-11-25 capability aggregation
"""

# Import MCP SDK mocks first to avoid import errors
# ruff: noqa: E402
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Mock MCP SDK modules before any other imports
if "mcp" not in sys.modules:
    mcp_mock = ModuleType("mcp")
    mcp_mock.Server = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp"] = mcp_mock

if "mcp.server" not in sys.modules:
    mock = ModuleType("mcp.server")
    mock.Server = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.server"] = mock

if "mcp.server.stdio" not in sys.modules:
    mock = ModuleType("mcp.server.stdio")
    mock.stdio_server = MagicMock()  # type: ignore[attr-defined]
    mock.StdioServerTransport = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.server.stdio"] = mock

if "mcp.server.sse" not in sys.modules:
    mock = ModuleType("mcp.server.sse")
    mock.SseServerTransport = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.server.sse"] = mock

if "mcp.server.streamable_http" not in sys.modules:
    mock = ModuleType("mcp.server.streamable_http")
    mock.StreamableHTTPServerTransport = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.server.streamable_http"] = mock

if "mcp.types" not in sys.modules:
    mock = ModuleType("mcp.types")
    mock.Tool = MagicMock()  # type: ignore[attr-defined]
    mock.Resource = MagicMock()  # type: ignore[attr-defined]
    mock.Prompt = MagicMock()  # type: ignore[attr-defined]
    mock.TextContent = MagicMock()  # type: ignore[attr-defined]
    mock.ImageContent = MagicMock()  # type: ignore[attr-defined]
    mock.CallToolResult = MagicMock()  # type: ignore[attr-defined]
    mock.GetPromptResult = MagicMock()  # type: ignore[attr-defined]
    mock.ReadResourceResult = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.types"] = mock

if "mcp.client" not in sys.modules:
    mock = ModuleType("mcp.client")
    mock.ClientSession = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.client"] = mock

if "mcp.client.session" not in sys.modules:
    mock = ModuleType("mcp.client.session")
    mock.ClientSession = MagicMock()  # type: ignore[attr-defined]
    sys.modules["mcp.client.session"] = mock

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Mock authenticated user for testing."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def sample_tool_data() -> list[dict[str, Any]]:
    """Sample tool data for testing."""
    return [
        {
            "qualified_name": "test-server:search_files",
            "server_name": "test-server",
            "name": "search_files",
            "description": "Search for files in the workspace",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
        {
            "qualified_name": "test-server:read_file",
            "server_name": "test-server",
            "name": "read_file",
            "description": "Read contents of a file",
            "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
    ]


@pytest.fixture
def sample_resource_data() -> list[dict[str, Any]]:
    """Sample resource data for testing."""
    return [
        {
            "qualified_name": "test-server:file:///workspace/README.md",
            "server_name": "test-server",
            "uri": "file:///workspace/README.md",
            "name": "README.md",
            "description": "Project readme file",
            "mime_type": "text/markdown",
        },
    ]


@pytest.fixture
def sample_prompt_data() -> list[dict[str, Any]]:
    """Sample prompt data for testing."""
    return [
        {
            "qualified_name": "test-server:code_review",
            "server_name": "test-server",
            "name": "code_review",
            "description": "Review code for best practices",
            "arguments": [{"name": "code", "type": "string", "required": True}],
        },
    ]


@pytest.fixture
def mock_cached_registry(
    sample_tool_data: list[dict[str, Any]],
    sample_resource_data: list[dict[str, Any]],
    sample_prompt_data: list[dict[str, Any]],
) -> MagicMock:
    """Create a mock CachedUnifiedRegistry."""
    mock = MagicMock()

    # Mock async methods
    mock.get_tools = AsyncMock(return_value=sample_tool_data)
    mock.get_resources = AsyncMock(return_value=sample_resource_data)
    mock.get_prompts = AsyncMock(return_value=sample_prompt_data)
    mock.get_server_names = AsyncMock(return_value=["test-server"])
    mock.get_server_capabilities = AsyncMock(return_value={"tool_count": 2, "resource_count": 1, "prompt_count": 1})

    # Mock sync passthrough methods
    mock.get_tool = MagicMock(return_value=None)
    mock.get_resource = MagicMock(return_value=None)
    mock.get_prompt = MagicMock(return_value=None)

    return mock


@pytest.fixture
def test_app(mock_user: dict[str, Any], mock_cached_registry: MagicMock) -> Generator[FastAPI, None, None]:
    """Create a test app with the aggregated router and mock authentication."""
    from mcp_server_langgraph.api.v1.mcp_aggregated import aggregated_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(aggregated_router, prefix="/api/v1")

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


# =============================================================================
# List Tools Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_mcp_aggregated_router")
class TestListAggregatedToolsEndpoint:
    """Tests for GET /api/v1/mcp/aggregated/tools endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_tools_returns_200(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
        sample_tool_data: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN a request to /api/v1/mcp/aggregated/tools
        WHEN GET request is made
        THEN response should be 200 OK with tools list
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            response = client.get("/api/v1/mcp/aggregated/tools")

            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
            assert "total_count" in data
            assert data["total_count"] == 2

    def test_list_tools_uses_cached_registry(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a cached registry is configured
        WHEN tools are requested
        THEN the cached registry get_tools method should be called
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            client.get("/api/v1/mcp/aggregated/tools")

            mock_cached_registry.get_tools.assert_called_once()

    def test_list_tools_with_server_filter(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a server_name query parameter
        WHEN tools are requested
        THEN the cached registry should be called with the filter
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            client.get("/api/v1/mcp/aggregated/tools?server_name=test-server")

            mock_cached_registry.get_tools.assert_called_once_with("test-server")


# =============================================================================
# List Resources Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_mcp_aggregated_router")
class TestListAggregatedResourcesEndpoint:
    """Tests for GET /api/v1/mcp/aggregated/resources endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_resources_returns_200(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
        sample_resource_data: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN a request to /api/v1/mcp/aggregated/resources
        WHEN GET request is made
        THEN response should be 200 OK with resources list
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            response = client.get("/api/v1/mcp/aggregated/resources")

            assert response.status_code == 200
            data = response.json()
            assert "resources" in data
            assert "total_count" in data
            assert data["total_count"] == 1

    def test_list_resources_uses_cached_registry(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a cached registry is configured
        WHEN resources are requested
        THEN the cached registry get_resources method should be called
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            client.get("/api/v1/mcp/aggregated/resources")

            mock_cached_registry.get_resources.assert_called_once()


# =============================================================================
# List Prompts Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_mcp_aggregated_router")
class TestListAggregatedPromptsEndpoint:
    """Tests for GET /api/v1/mcp/aggregated/prompts endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_prompts_returns_200(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
        sample_prompt_data: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN a request to /api/v1/mcp/aggregated/prompts
        WHEN GET request is made
        THEN response should be 200 OK with prompts list
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            response = client.get("/api/v1/mcp/aggregated/prompts")

            assert response.status_code == 200
            data = response.json()
            assert "prompts" in data
            assert "total_count" in data
            assert data["total_count"] == 1

    def test_list_prompts_uses_cached_registry(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a cached registry is configured
        WHEN prompts are requested
        THEN the cached registry get_prompts method should be called
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            client.get("/api/v1/mcp/aggregated/prompts")

            mock_cached_registry.get_prompts.assert_called_once()


# =============================================================================
# List Servers Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_mcp_aggregated_router")
class TestListAggregatedServersEndpoint:
    """Tests for GET /api/v1/mcp/aggregated/servers endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_servers_returns_200(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a request to /api/v1/mcp/aggregated/servers
        WHEN GET request is made
        THEN response should be 200 OK with servers summary
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            response = client.get("/api/v1/mcp/aggregated/servers")

            assert response.status_code == 200
            data = response.json()
            assert "servers" in data
            assert "total_servers" in data
            assert "total_tools" in data
            assert "total_resources" in data
            assert "total_prompts" in data
            assert data["total_servers"] == 1

    def test_list_servers_uses_cached_registry(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a cached registry is configured
        WHEN servers are requested
        THEN the cached registry methods should be called
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            client.get("/api/v1/mcp/aggregated/servers")

            mock_cached_registry.get_server_names.assert_called_once()
            mock_cached_registry.get_server_capabilities.assert_called_once_with("test-server")


# =============================================================================
# Get Server Capabilities Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_mcp_aggregated_router")
class TestGetServerCapabilitiesEndpoint:
    """Tests for GET /api/v1/mcp/aggregated/servers/{server_name} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_server_capabilities_returns_200(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a request for a specific server's capabilities
        WHEN GET request is made
        THEN response should be 200 OK with capabilities
        """
        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            response = client.get("/api/v1/mcp/aggregated/servers/test-server")

            assert response.status_code == 200
            data = response.json()
            assert data["server_name"] == "test-server"
            assert data["tool_count"] == 2
            assert data["resource_count"] == 1
            assert data["prompt_count"] == 1

    def test_get_server_capabilities_returns_404_for_unknown_server(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a request for an unknown server
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        mock_cached_registry.get_server_names = AsyncMock(return_value=[])

        with patch("mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry") as mock_get_registry:
            mock_get_registry.return_value = mock_cached_registry

            response = client.get("/api/v1/mcp/aggregated/servers/unknown-server")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
