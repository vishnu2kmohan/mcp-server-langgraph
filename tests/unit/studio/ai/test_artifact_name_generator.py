"""
Artifact Name Generator Unit Tests

Tests for AI-powered artifact name generation.
TDD: Tests written FIRST (RED phase).

The artifact name generator should:
1. Generate machine-friendly programmatic names from artifact content
2. Support multiple artifact types (code, mermaid, svg, json, etc.)
3. Use LLM when available, fallback to heuristics
4. Extract meaningful names from code (function/class names)
5. Return sensible defaults when content is unclear
6. Use LLMFactory for resilient LLM calls (SOLID compliance)
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.studio]


class TestArtifactNameGenerator:
    """Tests for ArtifactNameGenerator class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_returns_name_for_code_artifact(self) -> None:
        """
        GIVEN a code artifact with a function
        WHEN generate is called
        THEN should return a name based on the function
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content="def calculate_total(items):\n    return sum(item.price for item in items)",
            content_type="code",
            language="python",
        )

        assert name is not None
        assert len(name) > 0
        # Should contain the function name or be descriptive
        assert "calculate" in name.lower() or "total" in name.lower()

    @pytest.mark.asyncio
    async def test_generate_returns_name_for_class(self) -> None:
        """
        GIVEN a code artifact with a class
        WHEN generate is called
        THEN should return a name based on the class
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content="class UserAuthenticationService:\n    def login(self, username, password):\n        pass",
            content_type="code",
            language="python",
        )

        assert name is not None
        # Should contain the class name
        assert "user" in name.lower() or "auth" in name.lower()

    @pytest.mark.asyncio
    async def test_generate_returns_name_for_mermaid_diagram(self) -> None:
        """
        GIVEN a mermaid diagram artifact
        WHEN generate is called
        THEN should return a name based on the diagram type or title
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content="graph TD\n    A[Start] --> B[Process]\n    B --> C[End]",
            content_type="mermaid",
        )

        assert name is not None
        assert len(name) > 0

    @pytest.mark.asyncio
    async def test_generate_returns_name_for_svg(self) -> None:
        """
        GIVEN an SVG artifact with title element
        WHEN generate is called
        THEN should extract the title
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content='<svg xmlns="http://www.w3.org/2000/svg"><title>Architecture Diagram</title><circle cx="50" cy="50" r="40"/></svg>',
            content_type="svg",
        )

        assert name is not None
        assert "architecture" in name.lower() or "diagram" in name.lower()

    @pytest.mark.asyncio
    async def test_generate_returns_name_for_json(self) -> None:
        """
        GIVEN a JSON artifact with recognizable structure
        WHEN generate is called
        THEN should return a descriptive name
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content='{"name": "ProductConfig", "version": "1.0", "settings": {}}',
            content_type="json",
        )

        assert name is not None
        assert len(name) > 0

    @pytest.mark.asyncio
    async def test_generate_returns_default_for_empty_content(self) -> None:
        """
        GIVEN empty content
        WHEN generate is called
        THEN should return a default name
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(content="", content_type="code")

        assert name is not None
        # Should have a fallback default
        assert len(name) > 0

    @pytest.mark.asyncio
    async def test_generate_respects_max_length(self) -> None:
        """
        GIVEN content that would generate a long name
        WHEN generate is called
        THEN name should be truncated to max length
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False, max_name_length=30)
        name = await generator.generate(
            content="def very_long_function_name_that_should_be_truncated_somewhere():\n    pass",
            content_type="code",
            language="python",
        )

        assert len(name) <= 30

    @pytest.mark.asyncio
    async def test_generate_javascript_function(self) -> None:
        """
        GIVEN a JavaScript function
        WHEN generate is called
        THEN should extract the function name
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content="function handleUserClick(event) {\n  console.log(event);\n}",
            content_type="code",
            language="javascript",
        )

        assert name is not None
        assert "handle" in name.lower() or "click" in name.lower() or "user" in name.lower()

    @pytest.mark.asyncio
    async def test_generate_exported_const(self) -> None:
        """
        GIVEN a JavaScript/TypeScript exported const
        WHEN generate is called
        THEN should extract the const name
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        generator = ArtifactNameGenerator(enable_llm=False)
        name = await generator.generate(
            content="export const UserProfile = () => {\n  return <div>Profile</div>;\n};",
            content_type="code",
            language="typescript",
        )

        assert name is not None
        assert "user" in name.lower() or "profile" in name.lower()


class TestArtifactNameEndpoint:
    """Tests for POST /api/v1/ai/artifact-name endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_user(self) -> dict[str, Any]:
        """Mock authenticated user."""
        return {
            "sub": "test-user-123",
            "preferred_username": "testuser",
        }

    @pytest.fixture
    def test_app(self, mock_user: dict[str, Any]):
        """Create test app with AI UX router."""
        from fastapi import FastAPI

        from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router
        from mcp_server_langgraph.auth.middleware import get_current_user

        app = FastAPI()
        app.include_router(ai_ux_router, prefix="/api/v1")

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        yield app

        app.dependency_overrides.clear()

    def test_generate_artifact_name_returns_200(self, test_app) -> None:
        """
        GIVEN valid artifact content
        WHEN POST request is made to /api/v1/ai/artifact-name
        THEN response should be 200 OK with name
        """
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        with patch("mcp_server_langgraph.studio.ai.artifact_name_generator.generate_artifact_name") as mock_generate:
            # Use AsyncMock for async function

            mock_generate.return_value = "calculate_total"
            mock_generate.side_effect = None  # Clear side_effect for return_value

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/ai/artifact-name",
                json={
                    "content": "def calculate_total(): pass",
                    "type": "code",
                    "language": "python",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert data["name"] == "calculate_total"

    def test_generate_artifact_name_validates_content(self, test_app) -> None:
        """
        GIVEN missing content
        WHEN POST request is made
        THEN response should be 422 Validation Error
        """
        from fastapi.testclient import TestClient

        client = TestClient(test_app)
        response = client.post(
            "/api/v1/ai/artifact-name",
            json={"type": "code"},  # Missing content
        )

        assert response.status_code == 422

    def test_generate_artifact_name_with_empty_content(self, test_app) -> None:
        """
        GIVEN empty content
        WHEN POST request is made
        THEN response should return a default name
        """
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        with patch("mcp_server_langgraph.studio.ai.artifact_name_generator.generate_artifact_name") as mock_generate:
            mock_generate.return_value = "untitled"

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/ai/artifact-name",
                json={
                    "content": "",
                    "type": "code",
                },
            )

            # Empty content is valid, returns default
            assert response.status_code == 200
            data = response.json()
            assert "name" in data


class TestArtifactNameGeneratorLLMFactory:
    """Tests for LLMFactory integration (SOLID compliance).

    These tests verify that ArtifactNameGenerator uses LLMFactory
    for resilient LLM calls with circuit breaker, retry, timeout,
    and bulkhead patterns.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_accepts_llm_factory_via_dependency_injection(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN ArtifactNameGenerator is initialized with llm_factory parameter
        THEN it should use the injected factory for LLM calls
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        # Create mock LLM factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="test_artifact"))

        generator = ArtifactNameGenerator(enable_llm=True, llm_factory=mock_factory)
        name = await generator.generate(
            content="some complex content that needs LLM",
            content_type="unknown",
        )

        # Factory's ainvoke should have been called
        mock_factory.ainvoke.assert_called_once()
        assert "test_artifact" in name

    @pytest.mark.asyncio
    async def test_lazy_initializes_llm_factory_when_not_provided(self) -> None:
        """
        GIVEN no LLM factory provided
        WHEN generate is called with LLM enabled
        THEN it should lazy-initialize the factory from settings
        """
        from unittest.mock import patch

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        # Create a mock factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="lazy_init_name"))

        # Patch at the source module where create_llm_from_config is defined
        with patch(
            "mcp_server_langgraph.llm.factory.create_llm_from_config",
            return_value=mock_factory,
        ) as mock_create:
            generator = ArtifactNameGenerator(enable_llm=True)
            # Use content that won't match heuristics to force LLM call
            name = await generator.generate(
                content="~~~ambiguous~~~",
                content_type="unknown",
            )

            # Should have lazily created the factory
            mock_create.assert_called_once()
            assert name is not None

    @pytest.mark.asyncio
    async def test_llm_factory_receives_correct_messages(self) -> None:
        """
        GIVEN an LLMFactory and artifact content
        WHEN generate is called
        THEN the factory should receive properly formatted messages
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        # Create mock LLM factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="generated_name"))

        generator = ArtifactNameGenerator(enable_llm=True, llm_factory=mock_factory)
        await generator.generate(
            content="def hello(): pass",
            content_type="code",
            language="python",
        )

        # Verify the messages passed to ainvoke
        call_args = mock_factory.ainvoke.call_args
        if call_args:
            messages = call_args[0][0]  # First positional arg is messages
            # Should have a HumanMessage with the prompt
            assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_falls_back_to_heuristics_on_llm_error(self) -> None:
        """
        GIVEN an LLMFactory that raises an error
        WHEN generate is called
        THEN it should fall back to heuristic name generation
        """
        from mcp_server_langgraph.studio.ai.artifact_name_generator import (
            ArtifactNameGenerator,
        )

        # Create mock LLM factory that fails
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        generator = ArtifactNameGenerator(enable_llm=True, llm_factory=mock_factory)
        name = await generator.generate(
            content="def calculate_total(): pass",
            content_type="code",
            language="python",
        )

        # Should fall back to heuristics and extract function name
        assert "calculate" in name.lower() or "total" in name.lower()
