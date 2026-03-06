"""
Unified Tools Router Unit Tests.

Tests for GET /api/v1/tools endpoint per TDD methodology.
Validates the unified listing of built-in and MCP tools.

This endpoint supports manual tool selection in the chat input,
replacing semantic search with explicit user selection.
"""

# Import MCP SDK mocks first to avoid import errors
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
from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.model_registry import ModelCapabilities

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
def mock_builtin_tools() -> list[MagicMock]:
    """Mock built-in tools from get_all_tools()."""
    # Create mock LangChain tools with required attributes
    tools = []

    calculator = MagicMock()
    calculator.name = "calculator"
    calculator.description = "Perform mathematical calculations"
    calculator.args_schema = None
    tools.append(calculator)

    search_kb = MagicMock()
    search_kb.name = "search_knowledge_base"
    search_kb.description = "Search the knowledge base for relevant information"
    search_kb.args_schema = None
    tools.append(search_kb)

    web_search = MagicMock()
    web_search.name = "web_search"
    web_search.description = "Search the web for current information"
    web_search.args_schema = None
    tools.append(web_search)

    read_file = MagicMock()
    read_file.name = "read_file"
    read_file.description = "Read contents of a file"
    read_file.args_schema = None
    tools.append(read_file)

    return tools


@pytest.fixture
def mock_mcp_tools() -> list[dict[str, Any]]:
    """Mock MCP tools from CachedUnifiedRegistry."""
    return [
        {
            "qualified_name": "github:create_issue",
            "server_name": "github",
            "name": "create_issue",
            "description": "Create a new GitHub issue",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
        },
        {
            "qualified_name": "github:list_repos",
            "server_name": "github",
            "name": "list_repos",
            "description": "List repositories",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "qualified_name": "slack:send_message",
            "server_name": "slack",
            "name": "send_message",
            "description": "Send a Slack message",
            "input_schema": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string"},
                    "message": {"type": "string"},
                },
            },
        },
    ]


@pytest.fixture
def mock_cached_registry(mock_mcp_tools: list[dict[str, Any]]) -> MagicMock:
    """Create a mock CachedUnifiedRegistry."""
    mock = MagicMock()
    mock.get_tools = AsyncMock(return_value=mock_mcp_tools)
    return mock


@pytest.fixture
def test_app(
    mock_user: dict[str, Any],
    mock_builtin_tools: list[MagicMock],
    mock_cached_registry: MagicMock,
) -> Generator[FastAPI, None, None]:
    """Create a test app with the tools router and mock authentication."""
    from mcp_server_langgraph.api.v1.tools import tools_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(tools_router, prefix="/api/v1")

    async def override_get_current_user() -> dict[str, Any]:
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


# =============================================================================
# List Unified Tools Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_tools_router")
class TestListUnifiedToolsEndpoint:
    """Tests for GET /api/v1/tools endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_tools_returns_200(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a request to /api/v1/tools
        WHEN GET request is made
        THEN response should be 200 OK with unified tools list
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")

            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
            assert "builtin_count" in data
            assert "mcp_count" in data
            assert "total_count" in data

    def test_list_tools_includes_builtin_tools(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN built-in tools are available
        WHEN tools are listed
        THEN builtin tools should be included with source="builtin"
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            data = response.json()

            builtin_tools = [t for t in data["tools"] if t["source"] == "builtin"]
            assert len(builtin_tools) == 4
            assert data["builtin_count"] == 4

            # Check tool names
            builtin_names = {t["name"] for t in builtin_tools}
            assert "calculator" in builtin_names
            assert "search_knowledge_base" in builtin_names
            assert "web_search" in builtin_names
            assert "read_file" in builtin_names

    def test_list_tools_includes_mcp_tools(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN MCP tools are registered
        WHEN tools are listed
        THEN MCP tools should be included with source="mcp"
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            data = response.json()

            mcp_tools = [t for t in data["tools"] if t["source"] == "mcp"]
            assert len(mcp_tools) == 3
            assert data["mcp_count"] == 3

            # Check tool names
            mcp_names = {t["name"] for t in mcp_tools}
            assert "github:create_issue" in mcp_names
            assert "github:list_repos" in mcp_names
            assert "slack:send_message" in mcp_names

    def test_list_tools_filter_by_source_builtin(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN source=builtin filter is specified
        WHEN tools are listed
        THEN only built-in tools should be returned
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools?source=builtin")
            data = response.json()

            assert all(t["source"] == "builtin" for t in data["tools"])
            assert data["mcp_count"] == 0
            assert data["builtin_count"] == 4

    def test_list_tools_filter_by_source_mcp(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN source=mcp filter is specified
        WHEN tools are listed
        THEN only MCP tools should be returned
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools?source=mcp")
            data = response.json()

            assert all(t["source"] == "mcp" for t in data["tools"])
            assert data["builtin_count"] == 0
            assert data["mcp_count"] == 3

    def test_list_tools_filter_by_search(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a search term is provided
        WHEN tools are listed
        THEN only tools matching the search should be returned
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools?search=search")
            data = response.json()

            # Should match search_knowledge_base and web_search
            tool_names = [t["name"] for t in data["tools"]]
            assert "search_knowledge_base" in tool_names
            assert "web_search" in tool_names
            # calculator should not match
            assert "calculator" not in tool_names

    def test_list_tools_filter_by_category(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN a category filter is provided
        WHEN tools are listed
        THEN only tools in that category should be returned
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools?category=search")
            data = response.json()

            # Should match search tools only
            for tool in data["tools"]:
                assert tool["category"] == "search"

    def test_list_tools_response_schema(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN tools are available
        WHEN tools are listed
        THEN response should match UnifiedToolResponse schema
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            data = response.json()

            # Check first tool has all required fields
            tool = data["tools"][0]
            assert "name" in tool
            assert "display_name" in tool
            assert "description" in tool
            assert "source" in tool
            assert "server_name" in tool  # Can be null for builtin
            assert "category" in tool
            assert "input_schema" in tool
            assert "requires_sandbox" in tool

    def test_list_tools_requires_authentication(
        self,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN no authentication
        WHEN tools are requested
        THEN response should be 401 Unauthorized
        """
        from mcp_server_langgraph.api.v1.tools import tools_router

        app = FastAPI()
        app.include_router(tools_router, prefix="/api/v1")
        client = TestClient(app)

        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            # Should fail without auth override
            assert response.status_code in (401, 403)


@pytest.mark.xdist_group(name="test_tools_router")
class TestToolsCategoryMapping:
    """Tests for built-in tools category mapping."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_calculator_tools_have_calculator_category(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN calculator tools are available
        WHEN tools are listed
        THEN calculator tools should have category="calculator"
        """
        # Mock all calculator tools
        calculator_tools = []
        for name in ["calculator", "add", "subtract", "multiply", "divide"]:
            tool = MagicMock()
            tool.name = name
            tool.description = f"Math operation: {name}"
            tool.args_schema = None
            calculator_tools.append(tool)

        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=calculator_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            mock_cached_registry.get_tools = AsyncMock(return_value=[])
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                assert tool["category"] == "calculator"

    def test_search_tools_have_search_category(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN search tools are available
        WHEN tools are listed
        THEN search tools should have category="search"
        """
        search_tools = []
        for name in ["search_knowledge_base", "web_search"]:
            tool = MagicMock()
            tool.name = name
            tool.description = f"Search: {name}"
            tool.args_schema = None
            search_tools.append(tool)

        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=search_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            mock_cached_registry.get_tools = AsyncMock(return_value=[])
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                assert tool["category"] == "search"

    def test_filesystem_tools_have_filesystem_category(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN filesystem tools are available
        WHEN tools are listed
        THEN filesystem tools should have category="filesystem"
        """
        fs_tools = []
        for name in ["read_file", "list_directory", "search_files"]:
            tool = MagicMock()
            tool.name = name
            tool.description = f"Filesystem: {name}"
            tool.args_schema = None
            fs_tools.append(tool)

        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=fs_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            mock_cached_registry.get_tools = AsyncMock(return_value=[])
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                assert tool["category"] == "filesystem"


@pytest.mark.xdist_group(name="test_tools_router")
class TestToolsSandboxFlag:
    """Tests for requires_sandbox flag on tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_code_execution_tools_require_sandbox(
        self,
        client: TestClient,
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN code execution tools are available
        WHEN tools are listed
        THEN code execution tools should have requires_sandbox=true
        """
        sandbox_tools = []
        for name in ["execute_bash", "execute_python", "edit_file", "write_file"]:
            tool = MagicMock()
            tool.name = name
            tool.description = f"Sandbox tool: {name}"
            tool.args_schema = None
            sandbox_tools.append(tool)

        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=sandbox_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            mock_cached_registry.get_tools = AsyncMock(return_value=[])
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                assert tool["requires_sandbox"] is True

    def test_safe_tools_do_not_require_sandbox(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN safe read-only tools are available
        WHEN tools are listed
        THEN safe tools should have requires_sandbox=false
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            mock_cached_registry.get_tools = AsyncMock(return_value=[])
            response = client.get("/api/v1/tools")
            data = response.json()

            # calculator, search_knowledge_base, web_search, read_file are safe
            for tool in data["tools"]:
                assert tool["requires_sandbox"] is False


# =============================================================================
# v7: Native Tools Integration Tests
# =============================================================================


class TestNativeToolsIntegration:
    """Tests for v7 native LLM provider tools in the tools API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_tools_includes_tool_id_field(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN tools are available
        WHEN tools are listed
        THEN each tool should have a tool_id field in format 'source:name'
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                assert "tool_id" in tool
                assert ":" in tool["tool_id"]

                # Verify tool_id format matches source:name
                source = tool["source"]
                if source == "builtin":
                    assert tool["tool_id"].startswith("builtin:")
                elif source == "mcp":
                    assert tool["tool_id"].startswith("mcp:")

    def test_list_tools_includes_native_count(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN tools are available
        WHEN tools are listed
        THEN response should include native_count field
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            data = response.json()

            assert "native_count" in data
            assert isinstance(data["native_count"], int)

    def test_list_tools_includes_native_tools_when_enabled(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN native tools feature is enabled
        WHEN tools are listed
        THEN native tools should be included with source="native"
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_flags,
        ):
            mock_flags.native_tools_enabled = True
            mock_flags.anthropic_native_web_search_enabled = True

            response = client.get("/api/v1/tools")
            data = response.json()

            native_tools = [t for t in data["tools"] if t["source"] == "native"]
            assert len(native_tools) >= 1
            assert data["native_count"] >= 1

            # Check native tool has correct fields
            for native_tool in native_tools:
                assert native_tool["tool_id"].startswith("native:")
                assert "provider" in native_tool

    def test_list_tools_excludes_native_tools_when_disabled(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN native tools feature is disabled
        WHEN tools are listed
        THEN native tools should NOT be included
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_flags,
        ):
            mock_flags.native_tools_enabled = False

            response = client.get("/api/v1/tools")
            data = response.json()

            native_tools = [t for t in data["tools"] if t["source"] == "native"]
            assert len(native_tools) == 0
            assert data["native_count"] == 0

    def test_list_tools_filter_by_source_native(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN source=native filter is specified
        WHEN tools are listed
        THEN only native tools should be returned
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_flags,
        ):
            mock_flags.native_tools_enabled = True
            mock_flags.anthropic_native_web_search_enabled = True

            response = client.get("/api/v1/tools?source=native")
            data = response.json()

            assert all(t["source"] == "native" for t in data["tools"])
            assert data["builtin_count"] == 0
            assert data["mcp_count"] == 0

    def test_native_tools_have_provider_field(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN native tools are enabled
        WHEN tools are listed
        THEN native tools should have a provider field
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_flags,
        ):
            mock_flags.native_tools_enabled = True
            mock_flags.anthropic_native_web_search_enabled = True

            response = client.get("/api/v1/tools?source=native")
            data = response.json()

            for tool in data["tools"]:
                assert "provider" in tool
                assert tool["provider"] in ("anthropic", "google", "openai", None)

    def test_builtin_tool_id_format(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN built-in tools are available
        WHEN tools are listed
        THEN builtin tool_id should be 'builtin:{name}'
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=mock_builtin_tools,
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            mock_cached_registry.get_tools = AsyncMock(return_value=[])
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                if tool["source"] == "builtin":
                    expected_id = f"builtin:{tool['name']}"
                    assert tool["tool_id"] == expected_id

    def test_mcp_tool_id_format(
        self,
        client: TestClient,
        mock_builtin_tools: list[MagicMock],
        mock_mcp_tools: list[dict[str, Any]],
        mock_cached_registry: MagicMock,
    ) -> None:
        """
        GIVEN MCP tools are available
        WHEN tools are listed
        THEN MCP tool_id should be 'mcp:{qualified_name}'
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.get_all_tools",
                return_value=[],
            ),
            patch(
                "mcp_server_langgraph.mcp.client.cached_unified_registry.get_cached_unified_registry",
                return_value=mock_cached_registry,
            ),
        ):
            response = client.get("/api/v1/tools")
            data = response.json()

            for tool in data["tools"]:
                if tool["source"] == "mcp":
                    expected_id = f"mcp:{tool['name']}"
                    assert tool["tool_id"] == expected_id


# =============================================================================
# Native Capabilities Endpoint Tests
# =============================================================================


class TestNativeCapabilitiesEndpoint:
    """Tests for GET /api/v1/tools/native-capabilities/{model_id} endpoint.

    v7: Auto-detect native tool support based on model capabilities.
    """

    @staticmethod
    def _make_caps(**kwargs: Any) -> "ModelCapabilities":
        """Create ModelCapabilities with sensible defaults for testing."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        defaults = {
            "model_id": "test-model",
            "vendor": "test",
            "context_limit": 128000,
            "max_output_tokens": 8192,
            "input_cost_per_1m": 3.0,
            "output_cost_per_1m": 15.0,
        }
        return ModelCapabilities(**{**defaults, **kwargs})

    @pytest.fixture
    def native_test_app(
        self,
        mock_user: dict[str, Any],
    ) -> Generator[FastAPI, None, None]:
        """Create a test app specifically for native capabilities testing."""
        from mcp_server_langgraph.api.v1.tools import tools_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(tools_router, prefix="/api/v1")

        async def override_get_current_user() -> dict[str, Any]:
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        yield app

        app.dependency_overrides.clear()

    @pytest.fixture
    def native_client(self, native_test_app: FastAPI) -> Generator[TestClient, None, None]:
        """Create a TestClient for native capabilities testing."""
        with TestClient(native_test_app) as c:
            yield c

    def test_anthropic_model_has_native_web_search(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN a direct Anthropic Claude model
        WHEN native capabilities are requested
        THEN web_search should be supported
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        mock_caps = self._make_caps(
            supports_native_web_search=True,
            supports_native_code_execution=True,
            native_provider="anthropic",
        )

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            mock_ff.native_tools_enabled = True
            mock_ff.anthropic_native_web_search_enabled = True
            mock_ff.anthropic_native_code_execution_enabled = True

            response = native_client.get("/api/v1/tools/native-capabilities/claude-opus-4-5-20251101")
            assert response.status_code == 200
            data = response.json()

            assert data["model_id"] == "claude-opus-4-5-20251101"
            assert data["native_provider"] == "anthropic"
            assert data["master_enabled"] is True

            # Find web_search capability
            web_search = next(
                (c for c in data["capabilities"] if c["tool_name"] == "web_search"),
                None,
            )
            assert web_search is not None
            assert web_search["supported"] is True
            assert web_search["provider_type"] == "web_search_20250305"
            assert web_search["enabled"] is True

    def test_vertex_ai_anthropic_no_code_execution(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN an Anthropic model on Vertex AI
        WHEN native capabilities are requested
        THEN code_execution should NOT be supported (per ADR-0102)
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        # Vertex AI Anthropic: web search YES, code execution NO
        mock_caps = self._make_caps(
            supports_native_web_search=True,
            supports_native_code_execution=False,  # Critical limitation
            native_provider="anthropic",
        )

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            mock_ff.native_tools_enabled = True
            mock_ff.anthropic_native_web_search_enabled = True
            mock_ff.anthropic_native_code_execution_enabled = True

            response = native_client.get("/api/v1/tools/native-capabilities/claude-opus-4-5@20251101")
            assert response.status_code == 200
            data = response.json()

            # Code execution should NOT be supported
            code_exec = next(
                (c for c in data["capabilities"] if c["tool_name"] == "code_execution"),
                None,
            )
            assert code_exec is not None
            assert code_exec["supported"] is False
            assert code_exec["provider_type"] is None
            assert code_exec["enabled"] is False

    def test_google_model_has_native_search(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN a Google Gemini model
        WHEN native capabilities are requested
        THEN googleSearch should be available
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        mock_caps = self._make_caps(
            supports_native_web_search=True,
            native_provider="google",
        )

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            mock_ff.native_tools_enabled = True
            mock_ff.google_native_search_enabled = True

            response = native_client.get("/api/v1/tools/native-capabilities/gemini-3-flash")
            assert response.status_code == 200
            data = response.json()

            assert data["native_provider"] == "google"

            web_search = next(
                (c for c in data["capabilities"] if c["tool_name"] == "web_search"),
                None,
            )
            assert web_search is not None
            assert web_search["supported"] is True
            assert web_search["provider_type"] == "googleSearch"
            assert web_search["enabled"] is True

    def test_model_without_native_support(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN a model without native tool support
        WHEN native capabilities are requested
        THEN no capabilities should be marked as supported
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        mock_caps = self._make_caps(
            supports_native_web_search=False,
            supports_native_code_execution=False,
            native_provider=None,
        )

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            mock_ff.native_tools_enabled = True

            response = native_client.get("/api/v1/tools/native-capabilities/some-random-model")
            assert response.status_code == 200
            data = response.json()

            assert data["native_provider"] is None

            for cap in data["capabilities"]:
                assert cap["supported"] is False
                assert cap["enabled"] is False

    def test_native_tools_disabled_globally(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN native tools are disabled globally
        WHEN native capabilities are requested
        THEN all capabilities should show enabled=False
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        mock_caps = self._make_caps(
            supports_native_web_search=True,
            supports_native_code_execution=True,
            native_provider="anthropic",
        )

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            # Master switch is OFF
            mock_ff.native_tools_enabled = False
            mock_ff.anthropic_native_web_search_enabled = True
            mock_ff.anthropic_native_code_execution_enabled = True

            response = native_client.get("/api/v1/tools/native-capabilities/claude-opus-4-5-20251101")
            assert response.status_code == 200
            data = response.json()

            assert data["master_enabled"] is False

            # All capabilities should be disabled even if supported
            for cap in data["capabilities"]:
                if cap["supported"]:
                    assert cap["enabled"] is False

    def test_openai_model_native_capabilities(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN an OpenAI model with native tool support
        WHEN native capabilities are requested
        THEN OpenAI-specific types should be returned
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        mock_caps = self._make_caps(
            supports_native_web_search=True,
            supports_native_code_execution=True,
            native_provider="openai",
        )

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            mock_ff.native_tools_enabled = True
            mock_ff.openai_native_web_search_enabled = True
            mock_ff.openai_native_code_interpreter_enabled = True
            mock_ff.use_responses_api_for_openai = True

            response = native_client.get("/api/v1/tools/native-capabilities/gpt-5.2")
            assert response.status_code == 200
            data = response.json()

            assert data["native_provider"] == "openai"

            web_search = next(
                (c for c in data["capabilities"] if c["tool_name"] == "web_search"),
                None,
            )
            assert web_search is not None
            assert web_search["provider_type"] == "web_search_preview"

            code_exec = next(
                (c for c in data["capabilities"] if c["tool_name"] == "code_execution"),
                None,
            )
            assert code_exec is not None
            assert code_exec["provider_type"] == "code_interpreter"

    def test_path_parameter_with_slash(
        self,
        native_client: TestClient,
    ) -> None:
        """
        GIVEN a model ID with a slash (e.g., vertex_ai/claude-3-opus)
        WHEN native capabilities are requested
        THEN the full model ID should be preserved
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        mock_caps = self._make_caps()

        with (
            patch.object(ModelRegistry, "get", return_value=mock_caps),
            patch("mcp_server_langgraph.api.v1.tools.feature_flags") as mock_ff,
        ):
            mock_ff.native_tools_enabled = False

            response = native_client.get("/api/v1/tools/native-capabilities/vertex_ai/claude-3-opus")
            assert response.status_code == 200
            data = response.json()

            assert data["model_id"] == "vertex_ai/claude-3-opus"
