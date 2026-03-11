"""
Semantic Tools Search API Unit Tests (TDD).

Tests for POST /api/v1/tools/semantic-search endpoint.
Validates vector-based semantic tool discovery for reference autocomplete.

Follows TDD methodology: Write tests FIRST, then implementation.
Feature Flag: enable_semantic_tool_search (FF_ENABLE_SEMANTIC_TOOL_SEARCH)
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
from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.semantic_search,
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
def mock_semantic_search_results() -> list[dict[str, Any]]:
    """Mock semantic search results from vector provider."""
    return [
        {
            "id": "tool-calculator-001",
            "score": 0.95,
            "metadata": {
                "name": "calculator",
                "description": "Perform mathematical calculations",
                "category": "calculator",
            },
        },
        {
            "id": "tool-add-002",
            "score": 0.88,
            "metadata": {
                "name": "add",
                "description": "Add two numbers together",
                "category": "calculator",
            },
        },
        {
            "id": "tool-multiply-003",
            "score": 0.82,
            "metadata": {
                "name": "multiply",
                "description": "Multiply numbers",
                "category": "calculator",
            },
        },
    ]


@pytest.fixture
def mock_skill_search_results() -> list[dict[str, Any]]:
    """Mock semantic search results for skills."""
    return [
        {
            "id": "skill-code-review-001",
            "score": 0.92,
            "metadata": {
                "name": "code-review",
                "description": "Review code for quality and issues",
                "tags": ["development", "quality"],
            },
        },
        {
            "id": "skill-debugging-002",
            "score": 0.85,
            "metadata": {
                "name": "debugging",
                "description": "Debug and fix code issues",
                "tags": ["development", "debugging"],
            },
        },
    ]


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Mock embedding service."""
    service = MagicMock()
    service.embed = AsyncMock(return_value=[0.1] * 1536)  # OpenAI-style embedding
    return service


@pytest.fixture
def mock_vector_provider(mock_semantic_search_results: list[dict[str, Any]]) -> MagicMock:
    """Mock vector provider for semantic search."""
    provider = MagicMock()
    provider.search = AsyncMock(return_value=mock_semantic_search_results)
    return provider


@pytest.fixture
def test_app_with_semantic_search(
    mock_user: dict[str, Any],
) -> Generator[FastAPI, None, None]:
    """Create a test app with semantic search enabled."""
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
def client(test_app_with_semantic_search: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app_with_semantic_search)


# =============================================================================
# Semantic Tool Search Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_tools_semantic_search")
class TestSemanticToolSearchEndpoint:
    """Tests for POST /api/v1/tools/semantic-search endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_search_returns_200_when_enabled(
        self,
        client: TestClient,
        mock_vector_provider: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """
        GIVEN semantic tool search is enabled
        WHEN POST request with query is made
        THEN response should be 200 OK with search results
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "calculate numbers", "limit": 10},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) > 0

    def test_semantic_search_returns_404_when_disabled(
        self,
        client: TestClient,
    ) -> None:
        """
        GIVEN semantic tool search is disabled (default)
        WHEN POST request is made
        THEN response should be 404 Not Found
        """
        with patch(
            "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
            False,
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "calculate numbers"},
            )

            assert response.status_code == 404
            assert "not enabled" in response.json()["detail"].lower()

    def test_semantic_search_validates_query_required(
        self,
        client: TestClient,
    ) -> None:
        """
        GIVEN semantic search is enabled
        WHEN request without query is made
        THEN response should be 422 Validation Error
        """
        with patch(
            "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
            True,
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={},
            )

            assert response.status_code == 422

    def test_semantic_search_returns_scored_results(
        self,
        client: TestClient,
        mock_vector_provider: MagicMock,
        mock_embedding_service: MagicMock,
        mock_semantic_search_results: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN semantic search returns results
        WHEN POST request is made
        THEN results should include score and metadata
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "math operations"},
            )

            data = response.json()
            assert len(data["results"]) == 3

            # Check first result has expected fields
            first_result = data["results"][0]
            assert "tool_id" in first_result
            assert "name" in first_result
            assert "description" in first_result
            assert "score" in first_result
            assert first_result["score"] == 0.95

    def test_semantic_search_respects_limit(
        self,
        client: TestClient,
        mock_vector_provider: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """
        GIVEN limit parameter is provided
        WHEN POST request is made
        THEN vector provider should be called with limit
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "file operations", "limit": 5},
            )

            assert response.status_code == 200
            # Verify vector provider was called with limit
            mock_vector_provider.search.assert_called_once()
            call_kwargs = mock_vector_provider.search.call_args.kwargs
            assert call_kwargs.get("limit") == 5

    def test_semantic_search_respects_min_score(
        self,
        client: TestClient,
        mock_vector_provider: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """
        GIVEN min_score parameter is provided
        WHEN POST request is made
        THEN vector provider should filter by min_score
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "search tools", "min_score": 0.8},
            )

            assert response.status_code == 200
            # Verify min_score was passed
            call_kwargs = mock_vector_provider.search.call_args.kwargs
            assert call_kwargs.get("min_score") == 0.8

    def test_semantic_search_requires_authentication(
        self,
    ) -> None:
        """
        GIVEN no authentication
        WHEN semantic search is requested
        THEN response should be 401 Unauthorized
        """
        from mcp_server_langgraph.api.v1.tools import tools_router

        app = FastAPI()
        app.include_router(tools_router, prefix="/api/v1")
        unauthenticated_client = TestClient(app)

        with patch(
            "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
            True,
        ):
            response = unauthenticated_client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "test"},
            )
            assert response.status_code in (401, 403)


@pytest.mark.xdist_group(name="test_tools_semantic_search")
class TestSemanticSkillSearchEndpoint:
    """Tests for POST /api/v1/admin/skills/semantic-search endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_skill_search_returns_200_when_enabled(
        self,
        mock_user: dict[str, Any],
        mock_skill_search_results: list[dict[str, Any]],
        mock_embedding_service: MagicMock,
    ) -> None:
        """
        GIVEN semantic skill search is enabled
        WHEN POST request with query is made
        THEN response should be 200 OK with skill results
        """
        from mcp_server_langgraph.api.v1.skills import router as skills_router
        from mcp_server_langgraph.auth.dependencies import require_skill_viewer_global

        app = FastAPI()
        app.include_router(skills_router, prefix="/api/v1")

        async def override_require_skill_viewer() -> dict[str, Any]:
            return mock_user

        app.dependency_overrides[require_skill_viewer_global] = override_require_skill_viewer

        skill_client = TestClient(app)

        mock_vector_provider = MagicMock()
        mock_vector_provider.search = AsyncMock(return_value=mock_skill_search_results)

        with (
            patch(
                "mcp_server_langgraph.api.v1.skills.feature_flags.enable_semantic_skill_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.skills.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.skills.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = skill_client.post(
                "/api/v1/admin/skills/semantic-search",
                json={"query": "code quality review"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2

    def test_semantic_skill_search_returns_404_when_disabled(
        self,
        mock_user: dict[str, Any],
    ) -> None:
        """
        GIVEN semantic skill search is disabled (default)
        WHEN POST request is made
        THEN response should be 404 Not Found
        """
        from mcp_server_langgraph.api.v1.skills import router as skills_router
        from mcp_server_langgraph.auth.dependencies import require_skill_viewer_global

        app = FastAPI()
        app.include_router(skills_router, prefix="/api/v1")

        async def override_require_skill_viewer() -> dict[str, Any]:
            return mock_user

        app.dependency_overrides[require_skill_viewer_global] = override_require_skill_viewer

        skill_client = TestClient(app)

        with patch(
            "mcp_server_langgraph.api.v1.skills.feature_flags.enable_semantic_skill_search",
            False,
        ):
            response = skill_client.post(
                "/api/v1/admin/skills/semantic-search",
                json={"query": "code review"},
            )

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_tools_semantic_search")
class TestSemanticSearchResponseSchema:
    """Tests for semantic search response schema validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_search_result_has_required_fields(
        self,
        client: TestClient,
        mock_vector_provider: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """
        GIVEN semantic search returns results
        WHEN response is parsed
        THEN each result should have required fields
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "calculator"},
            )

            data = response.json()
            for result in data["results"]:
                # Required fields for autocomplete
                assert "tool_id" in result
                assert "name" in result
                assert "description" in result
                assert "score" in result
                # Score should be between 0 and 1
                assert 0 <= result["score"] <= 1

    def test_response_includes_query_in_metadata(
        self,
        client: TestClient,
        mock_vector_provider: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """
        GIVEN semantic search is performed
        WHEN response is returned
        THEN response should include query metadata
        """
        with (
            patch(
                "mcp_server_langgraph.api.v1.tools.feature_flags.enable_semantic_tool_search",
                True,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_vector_provider",
                side_effect=lambda *a, **kw: mock_vector_provider,
            ),
            patch(
                "mcp_server_langgraph.api.v1.tools.get_embedding_service",
                side_effect=lambda *a, **kw: mock_embedding_service,
            ),
        ):
            response = client.post(
                "/api/v1/tools/semantic-search",
                json={"query": "file operations"},
            )

            data = response.json()
            assert "query" in data
            assert data["query"] == "file operations"
            assert "total_results" in data
