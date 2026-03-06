"""
Tests for Agents Config Router

TDD tests for GET /api/v1/agents/config endpoint.
This endpoint returns the current agent configuration including:
- Model name and provider
- Temperature settings
- Verification settings
- Registered tools
"""

import gc
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_router")
class TestAgentsConfigEndpoint:
    """Tests for GET /api/v1/agents/config endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_app(self) -> FastAPI:
        """Create a FastAPI app with the agents router."""
        from mcp_server_langgraph.api.v1.agents import agents_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(agents_router, prefix="/api/v1")

        # Mock authentication
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "email": "testuser@example.com",
            "roles": ["user"],
            "realm_access": {"roles": ["user"]},
        }

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        return app

    def _create_client(self) -> TestClient:
        """Create a test client for the agents API."""
        return TestClient(self._create_app())

    @pytest.mark.asyncio
    async def test_get_agents_config_returns_200(self) -> None:
        """GET /api/v1/agents/config should return 200 with config data."""
        client = self._create_client()

        response = client.get("/api/v1/agents/config")

        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert "provider" in data
        assert "temperature" in data
        assert "verification_enabled" in data
        assert "tools" in data

    @pytest.mark.asyncio
    async def test_get_agents_config_returns_model_settings(self) -> None:
        """GET /api/v1/agents/config should return model settings from config."""
        with patch("mcp_server_langgraph.api.v1.agents.settings") as mock_settings:
            mock_settings.model_name = "claude-sonnet-4-5-20250929"
            mock_settings.llm_provider = "anthropic"
            mock_settings.model_temperature = 0.5

            client = self._create_client()
            response = client.get("/api/v1/agents/config")

            assert response.status_code == 200
            data = response.json()
            assert data["model"] == "claude-sonnet-4-5-20250929"
            assert data["provider"] == "anthropic"
            assert data["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_get_agents_config_returns_verification_settings(self) -> None:
        """GET /api/v1/agents/config should return verification settings."""
        with patch("mcp_server_langgraph.api.v1.agents.settings") as mock_settings:
            mock_settings.model_name = "gemini-2.5-flash"
            mock_settings.llm_provider = "google"
            mock_settings.model_temperature = 0.7
            mock_settings.enable_verification = True

            client = self._create_client()
            response = client.get("/api/v1/agents/config")

            assert response.status_code == 200
            data = response.json()
            assert data["verification_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_agents_config_returns_tools_list(self) -> None:
        """GET /api/v1/agents/config should return list of available tools."""
        client = self._create_client()

        response = client.get("/api/v1/agents/config")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["tools"], list)

    @pytest.mark.asyncio
    async def test_get_agents_config_tools_have_name_and_description(self) -> None:
        """Each tool should have a name and description."""
        with patch("mcp_server_langgraph.api.v1.agents.get_registered_tools") as mock_tools:
            mock_tools.return_value = [
                {"name": "search", "description": "Search the web"},
                {"name": "calculator", "description": "Perform calculations"},
            ]

            client = self._create_client()
            response = client.get("/api/v1/agents/config")

            assert response.status_code == 200
            data = response.json()
            assert len(data["tools"]) == 2
            assert data["tools"][0]["name"] == "search"
            assert data["tools"][0]["description"] == "Search the web"
            assert data["tools"][1]["name"] == "calculator"
            assert data["tools"][1]["description"] == "Perform calculations"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_router")
class TestAgentConfigResponseModel:
    """Tests for AgentConfig response model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_config_model_validation(self) -> None:
        """AgentConfig model should validate required fields."""
        from mcp_server_langgraph.api.v1.agents import AgentConfigResponse, ToolInfo

        # Valid config
        config = AgentConfigResponse(
            model="gemini-2.5-flash",
            provider="google",
            temperature=0.7,
            verification_enabled=True,
            tools=[ToolInfo(name="search", description="Search the web")],
        )

        assert config.model == "gemini-2.5-flash"
        assert config.provider == "google"
        assert config.temperature == 0.7
        assert config.verification_enabled is True
        assert len(config.tools) == 1

    def test_agent_config_temperature_bounds(self) -> None:
        """Temperature should be between 0 and 2."""

        from mcp_server_langgraph.api.v1.agents import AgentConfigResponse

        # Valid temperature
        config = AgentConfigResponse(
            model="test",
            provider="test",
            temperature=1.5,
            verification_enabled=False,
            tools=[],
        )
        assert config.temperature == 1.5

        # Temperature at bounds
        config_zero = AgentConfigResponse(
            model="test",
            provider="test",
            temperature=0.0,
            verification_enabled=False,
            tools=[],
        )
        assert config_zero.temperature == 0.0

        config_max = AgentConfigResponse(
            model="test",
            provider="test",
            temperature=2.0,
            verification_enabled=False,
            tools=[],
        )
        assert config_max.temperature == 2.0

    def test_tool_info_model(self) -> None:
        """ToolInfo model should validate name and description."""
        from mcp_server_langgraph.api.v1.agents import ToolInfo

        tool = ToolInfo(name="search_web", description="Search the web for information")
        assert tool.name == "search_web"
        assert tool.description == "Search the web for information"

    def test_tool_info_with_empty_description(self) -> None:
        """ToolInfo should allow empty description."""
        from mcp_server_langgraph.api.v1.agents import ToolInfo

        tool = ToolInfo(name="tool_name", description="")
        assert tool.name == "tool_name"
        assert tool.description == ""
