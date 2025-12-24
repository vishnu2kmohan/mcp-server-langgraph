"""
Tests for Extended AgentConfigResponse (Sprint 1)

TDD tests for the extended agent configuration response that adds:
- thinking_budget_defaults: Optional thinking level configuration
- feature_flags_snapshot: Optional agent-related feature flags

These extensions are backward compatible - all new fields are optional.

Test Coverage:
- ThinkingBudgetDefaults model validation
- ThinkingLevelInfo model validation
- Extended AgentConfigResponse with optional fields
- API endpoint returns extended fields when available
- Backward compatibility: existing fields remain unchanged
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_config_extended")
class TestThinkingLevelInfoModel:
    """Tests for ThinkingLevelInfo model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_thinking_level_info_valid(self) -> None:
        """ThinkingLevelInfo should accept valid level data."""
        from mcp_server_langgraph.api.v1.agents import ThinkingLevelInfo

        info = ThinkingLevelInfo(
            level="medium",
            claude_opus_effort="medium",
            other_models_tokens=8192,
            description="Standard thinking for most tasks",
        )

        assert info.level == "medium"
        assert info.claude_opus_effort == "medium"
        assert info.other_models_tokens == 8192
        assert info.description == "Standard thinking for most tasks"

    def test_thinking_level_info_all_levels(self) -> None:
        """ThinkingLevelInfo should support all thinking levels."""
        from mcp_server_langgraph.api.v1.agents import ThinkingLevelInfo

        levels = [
            ("low", "low", 1024),
            ("medium", "medium", 8192),
            ("high", "high", 32768),
            ("ultra", "high", 65536),  # ULTRA maps to high for Opus
        ]

        for level, opus_effort, tokens in levels:
            info = ThinkingLevelInfo(
                level=level,
                claude_opus_effort=opus_effort,
                other_models_tokens=tokens,
                description=f"Thinking level: {level}",
            )
            assert info.level == level
            assert info.claude_opus_effort == opus_effort
            assert info.other_models_tokens == tokens


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_config_extended")
class TestThinkingBudgetDefaultsModel:
    """Tests for ThinkingBudgetDefaults model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_thinking_budget_defaults_valid(self) -> None:
        """ThinkingBudgetDefaults should accept valid configuration."""
        from mcp_server_langgraph.api.v1.agents import (
            ThinkingBudgetDefaults,
            ThinkingLevelInfo,
        )

        defaults = ThinkingBudgetDefaults(
            enabled=True,
            default_level="medium",
            levels=[
                ThinkingLevelInfo(
                    level="low",
                    claude_opus_effort="low",
                    other_models_tokens=1024,
                    description="Quick thinking for simple tasks",
                ),
                ThinkingLevelInfo(
                    level="medium",
                    claude_opus_effort="medium",
                    other_models_tokens=8192,
                    description="Standard thinking for most tasks",
                ),
            ],
            complexity_mapping={"simple": "low", "complicated": "medium", "complex": "high"},
        )

        assert defaults.enabled is True
        assert defaults.default_level == "medium"
        assert len(defaults.levels) == 2
        assert defaults.complexity_mapping == {"simple": "low", "complicated": "medium", "complex": "high"}

    def test_thinking_budget_defaults_disabled(self) -> None:
        """ThinkingBudgetDefaults should support disabled state."""
        from mcp_server_langgraph.api.v1.agents import ThinkingBudgetDefaults

        defaults = ThinkingBudgetDefaults(
            enabled=False,
            default_level="medium",
            levels=[],
            complexity_mapping={},
        )

        assert defaults.enabled is False
        assert defaults.levels == []

    def test_thinking_budget_defaults_from_feature_flags(self) -> None:
        """ThinkingBudgetDefaults should be constructable from feature flags."""
        from mcp_server_langgraph.api.v1.agents import get_thinking_budget_defaults

        # Mock feature flags to control the output
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_ff:
            mock_ff.enable_thinking_budget = True
            mock_ff.default_thinking_level = "high"

            defaults = get_thinking_budget_defaults()

            assert defaults is not None
            assert defaults.enabled is True
            assert defaults.default_level == "high"
            assert len(defaults.levels) == 4  # low, medium, high, ultra


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_config_extended")
class TestExtendedAgentConfigResponse:
    """Tests for extended AgentConfigResponse model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_config_response_backward_compatible(self) -> None:
        """AgentConfigResponse should work without new optional fields."""
        from mcp_server_langgraph.api.v1.agents import AgentConfigResponse, ToolInfo

        # Create config without new fields - should work
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
        # New fields should be None by default
        assert config.thinking_budget_defaults is None
        assert config.feature_flags_snapshot is None

    def test_agent_config_response_with_thinking_budget(self) -> None:
        """AgentConfigResponse should accept optional thinking_budget_defaults."""
        from mcp_server_langgraph.api.v1.agents import (
            AgentConfigResponse,
            ThinkingBudgetDefaults,
            ThinkingLevelInfo,
        )

        thinking_defaults = ThinkingBudgetDefaults(
            enabled=True,
            default_level="medium",
            levels=[
                ThinkingLevelInfo(
                    level="medium",
                    claude_opus_effort="medium",
                    other_models_tokens=8192,
                    description="Standard thinking",
                ),
            ],
            complexity_mapping={"simple": "low"},
        )

        config = AgentConfigResponse(
            model="claude-opus-4-5-20251101",
            provider="anthropic",
            temperature=0.5,
            verification_enabled=False,
            tools=[],
            thinking_budget_defaults=thinking_defaults,
        )

        assert config.thinking_budget_defaults is not None
        assert config.thinking_budget_defaults.enabled is True
        assert config.thinking_budget_defaults.default_level == "medium"

    def test_agent_config_response_with_feature_flags_snapshot(self) -> None:
        """AgentConfigResponse should accept optional feature_flags_snapshot."""
        from mcp_server_langgraph.api.v1.agents import AgentConfigResponse

        config = AgentConfigResponse(
            model="gemini-2.5-flash",
            provider="google",
            temperature=0.7,
            verification_enabled=True,
            tools=[],
            feature_flags_snapshot={
                "enable_thinking_budget": True,
                "enable_multi_agent_orchestration": True,
                "enable_loop_agent": False,
                "enable_orchestrator_resilience": True,
            },
        )

        assert config.feature_flags_snapshot is not None
        assert config.feature_flags_snapshot["enable_thinking_budget"] is True
        assert config.feature_flags_snapshot["enable_loop_agent"] is False

    def test_agent_config_response_with_all_optional_fields(self) -> None:
        """AgentConfigResponse should accept all optional extended fields."""
        from mcp_server_langgraph.api.v1.agents import (
            AgentConfigResponse,
            ThinkingBudgetDefaults,
            ThinkingLevelInfo,
            ToolInfo,
        )

        config = AgentConfigResponse(
            model="claude-opus-4-5-20251101",
            provider="anthropic",
            temperature=0.3,
            verification_enabled=True,
            tools=[ToolInfo(name="calculator", description="Math calculations")],
            thinking_budget_defaults=ThinkingBudgetDefaults(
                enabled=True,
                default_level="high",
                levels=[
                    ThinkingLevelInfo(
                        level="high",
                        claude_opus_effort="high",
                        other_models_tokens=32768,
                        description="Deep thinking",
                    ),
                ],
                complexity_mapping={"complex": "high"},
            ),
            feature_flags_snapshot={
                "enable_thinking_budget": True,
                "enable_orchestrator_resilience": True,
            },
        )

        assert config.model == "claude-opus-4-5-20251101"
        assert config.thinking_budget_defaults is not None
        assert config.feature_flags_snapshot is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_config_extended")
class TestAgentConfigExtendedEndpoint:
    """Tests for GET /api/v1/agents/config with extended fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_app(self):
        """Create a FastAPI app with the agents router."""
        from fastapi import FastAPI

        from mcp_server_langgraph.api.v1.agents import agents_router

        app = FastAPI()
        app.include_router(agents_router, prefix="/api/v1")
        return app

    def _create_client(self):
        """Create a test client for the agents API."""
        from fastapi.testclient import TestClient

        return TestClient(self._create_app())

    @pytest.mark.asyncio
    async def test_get_agents_config_includes_thinking_budget(self) -> None:
        """GET /api/v1/agents/config should include thinking_budget_defaults when enabled."""
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_ff:
            mock_ff.enable_thinking_budget = True
            mock_ff.default_thinking_level = "medium"
            # Mock other required settings
            with patch("mcp_server_langgraph.api.v1.agents.settings") as mock_settings:
                mock_settings.model_name = "claude-opus-4-5-20251101"
                mock_settings.llm_provider = "anthropic"
                mock_settings.model_temperature = 0.5
                mock_settings.enable_verification = False

                client = self._create_client()
                response = client.get("/api/v1/agents/config")

                assert response.status_code == 200
                data = response.json()
                assert "thinking_budget_defaults" in data
                if data["thinking_budget_defaults"] is not None:
                    assert data["thinking_budget_defaults"]["enabled"] is True
                    assert data["thinking_budget_defaults"]["default_level"] == "medium"

    @pytest.mark.asyncio
    async def test_get_agents_config_includes_feature_flags_snapshot(self) -> None:
        """GET /api/v1/agents/config should include feature_flags_snapshot."""
        with patch("mcp_server_langgraph.api.v1.agents.settings") as mock_settings:
            mock_settings.model_name = "gemini-2.5-flash"
            mock_settings.llm_provider = "google"
            mock_settings.model_temperature = 0.7
            mock_settings.enable_verification = True

            client = self._create_client()
            response = client.get("/api/v1/agents/config")

            assert response.status_code == 200
            data = response.json()
            assert "feature_flags_snapshot" in data
            if data["feature_flags_snapshot"] is not None:
                # Should contain agent-related feature flags
                assert isinstance(data["feature_flags_snapshot"], dict)

    @pytest.mark.asyncio
    async def test_get_agents_config_backward_compatible_response(self) -> None:
        """GET /api/v1/agents/config response should be backward compatible."""
        with patch("mcp_server_langgraph.api.v1.agents.settings") as mock_settings:
            mock_settings.model_name = "gpt-4o"
            mock_settings.llm_provider = "openai"
            mock_settings.model_temperature = 0.8
            mock_settings.enable_verification = False

            client = self._create_client()
            response = client.get("/api/v1/agents/config")

            assert response.status_code == 200
            data = response.json()

            # Original fields must be present
            assert "model" in data
            assert "provider" in data
            assert "temperature" in data
            assert "verification_enabled" in data
            assert "tools" in data

            # Values should match mocked settings
            assert data["model"] == "gpt-4o"
            assert data["provider"] == "openai"
            assert data["temperature"] == 0.8
            assert data["verification_enabled"] is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_config_extended")
class TestGetThinkingBudgetDefaults:
    """Tests for get_thinking_budget_defaults helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_thinking_budget_defaults_when_enabled(self) -> None:
        """get_thinking_budget_defaults should return defaults when feature enabled."""
        from mcp_server_langgraph.api.v1.agents import get_thinking_budget_defaults

        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_ff:
            mock_ff.enable_thinking_budget = True
            mock_ff.default_thinking_level = "high"

            defaults = get_thinking_budget_defaults()

            assert defaults is not None
            assert defaults.enabled is True
            assert defaults.default_level == "high"
            assert len(defaults.levels) == 4  # low, medium, high, ultra
            # Check complexity mapping
            assert "simple" in defaults.complexity_mapping
            assert "complicated" in defaults.complexity_mapping
            assert "complex" in defaults.complexity_mapping

    def test_get_thinking_budget_defaults_when_disabled(self) -> None:
        """get_thinking_budget_defaults should return disabled defaults when feature disabled."""
        from mcp_server_langgraph.api.v1.agents import get_thinking_budget_defaults

        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_ff:
            mock_ff.enable_thinking_budget = False
            mock_ff.default_thinking_level = "medium"

            defaults = get_thinking_budget_defaults()

            assert defaults is not None
            assert defaults.enabled is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agents_config_extended")
class TestGetAgentFeatureFlagsSnapshot:
    """Tests for get_agent_feature_flags_snapshot helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_agent_feature_flags_snapshot_contains_agent_flags(self) -> None:
        """get_agent_feature_flags_snapshot should return agent-related flags."""
        from mcp_server_langgraph.api.v1.agents import get_agent_feature_flags_snapshot

        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_ff:
            mock_ff.enable_thinking_budget = True
            mock_ff.enable_multi_agent_orchestration = True
            mock_ff.enable_loop_agent = False
            mock_ff.enable_orchestrator_resilience = True
            mock_ff.enable_cost_tracking = True
            mock_ff.enable_sdk_hooks = True
            mock_ff.enable_handoff_pattern = True

            snapshot = get_agent_feature_flags_snapshot()

            assert isinstance(snapshot, dict)
            assert "enable_thinking_budget" in snapshot
            assert "enable_multi_agent_orchestration" in snapshot
            assert "enable_loop_agent" in snapshot
            assert "enable_orchestrator_resilience" in snapshot
            assert snapshot["enable_thinking_budget"] is True
            assert snapshot["enable_loop_agent"] is False

    def test_get_agent_feature_flags_snapshot_excludes_ui_flags(self) -> None:
        """get_agent_feature_flags_snapshot should not include UI-specific flags."""
        from mcp_server_langgraph.api.v1.agents import get_agent_feature_flags_snapshot

        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_ff:
            # Set both agent and UI flags
            mock_ff.enable_thinking_budget = True
            mock_ff.enable_workflows_feature = True  # UI flag
            mock_ff.studio_canvas_shell = True  # UI flag
            mock_ff.enable_multi_agent_orchestration = True

            snapshot = get_agent_feature_flags_snapshot()

            # Agent flags should be present
            assert "enable_thinking_budget" in snapshot
            assert "enable_multi_agent_orchestration" in snapshot

            # UI flags should NOT be present
            assert "enable_workflows_feature" not in snapshot
            assert "studio_canvas_shell" not in snapshot
