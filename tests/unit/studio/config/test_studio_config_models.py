"""Tests for StudioConfig Pydantic models.

TDD: These tests define the contract for STUDIO.md configuration models
that represent hierarchical capability configuration.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_config_models")
class TestStudioToolsConfig:
    """Tests for StudioToolsConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_tools_config_exists(self) -> None:
        """Test StudioToolsConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioToolsConfig

        assert StudioToolsConfig is not None

    def test_studio_tools_config_has_enabled_field(self) -> None:
        """Test StudioToolsConfig has enabled list."""
        from mcp_server_langgraph.studio.config.models import StudioToolsConfig

        config = StudioToolsConfig(enabled=["file_reader", "web_search"])
        assert config.enabled == ["file_reader", "web_search"]

    def test_studio_tools_config_has_disabled_field(self) -> None:
        """Test StudioToolsConfig has disabled list."""
        from mcp_server_langgraph.studio.config.models import StudioToolsConfig

        config = StudioToolsConfig(disabled=["dangerous_tool"])
        assert config.disabled == ["dangerous_tool"]

    def test_studio_tools_config_enabled_defaults_to_empty(self) -> None:
        """Test enabled defaults to empty list."""
        from mcp_server_langgraph.studio.config.models import StudioToolsConfig

        config = StudioToolsConfig()
        assert config.enabled == []

    def test_studio_tools_config_disabled_defaults_to_empty(self) -> None:
        """Test disabled defaults to empty list."""
        from mcp_server_langgraph.studio.config.models import StudioToolsConfig

        config = StudioToolsConfig()
        assert config.disabled == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_config_models")
class TestStudioSkillsConfig:
    """Tests for StudioSkillsConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_skills_config_exists(self) -> None:
        """Test StudioSkillsConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioSkillsConfig

        assert StudioSkillsConfig is not None

    def test_studio_skills_config_has_enabled_field(self) -> None:
        """Test StudioSkillsConfig has enabled list."""
        from mcp_server_langgraph.studio.config.models import StudioSkillsConfig

        config = StudioSkillsConfig(enabled=["summarize", "translate"])
        assert config.enabled == ["summarize", "translate"]

    def test_studio_skills_config_has_disabled_field(self) -> None:
        """Test StudioSkillsConfig has disabled list."""
        from mcp_server_langgraph.studio.config.models import StudioSkillsConfig

        config = StudioSkillsConfig(disabled=["code_execution"])
        assert config.disabled == ["code_execution"]

    def test_studio_skills_config_has_categories_field(self) -> None:
        """Test StudioSkillsConfig has categories list."""
        from mcp_server_langgraph.studio.config.models import StudioSkillsConfig

        config = StudioSkillsConfig(categories=["text", "code"])
        assert config.categories == ["text", "code"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_config_models")
class TestStudioMemoryConfig:
    """Tests for StudioMemoryConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_memory_config_exists(self) -> None:
        """Test StudioMemoryConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioMemoryConfig

        assert StudioMemoryConfig is not None

    def test_studio_memory_config_has_enabled_field(self) -> None:
        """Test StudioMemoryConfig has enabled flag."""
        from mcp_server_langgraph.studio.config.models import StudioMemoryConfig

        config = StudioMemoryConfig(enabled=True)
        assert config.enabled is True

    def test_studio_memory_config_has_tiers_field(self) -> None:
        """Test StudioMemoryConfig has tiers list."""
        from mcp_server_langgraph.studio.config.models import StudioMemoryConfig

        config = StudioMemoryConfig(tiers=["working", "session", "durable"])
        assert config.tiers == ["working", "session", "durable"]

    def test_studio_memory_config_has_max_items_field(self) -> None:
        """Test StudioMemoryConfig has max_items limit."""
        from mcp_server_langgraph.studio.config.models import StudioMemoryConfig

        config = StudioMemoryConfig(max_items=100)
        assert config.max_items == 100


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_config_models")
class TestStudioCostConfig:
    """Tests for StudioCostConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_cost_config_exists(self) -> None:
        """Test StudioCostConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioCostConfig

        assert StudioCostConfig is not None

    def test_studio_cost_config_has_max_tokens_field(self) -> None:
        """Test StudioCostConfig has max_tokens limit."""
        from mcp_server_langgraph.studio.config.models import StudioCostConfig

        config = StudioCostConfig(max_tokens=10000)
        assert config.max_tokens == 10000

    def test_studio_cost_config_has_max_cost_field(self) -> None:
        """Test StudioCostConfig has max_cost limit."""
        from mcp_server_langgraph.studio.config.models import StudioCostConfig

        config = StudioCostConfig(max_cost=5.0)
        assert config.max_cost == 5.0

    def test_studio_cost_config_has_budget_alert_threshold_field(self) -> None:
        """Test StudioCostConfig has budget_alert_threshold."""
        from mcp_server_langgraph.studio.config.models import StudioCostConfig

        config = StudioCostConfig(budget_alert_threshold=0.8)
        assert config.budget_alert_threshold == 0.8


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_config_models")
class TestStudioModelsConfig:
    """Tests for StudioModelsConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_models_config_exists(self) -> None:
        """Test StudioModelsConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioModelsConfig

        assert StudioModelsConfig is not None

    def test_studio_models_config_has_default_model_field(self) -> None:
        """Test StudioModelsConfig has default_model."""
        from mcp_server_langgraph.studio.config.models import StudioModelsConfig

        config = StudioModelsConfig(default_model="claude-sonnet-4")
        assert config.default_model == "claude-sonnet-4"

    def test_studio_models_config_has_allowed_models_field(self) -> None:
        """Test StudioModelsConfig has allowed_models list."""
        from mcp_server_langgraph.studio.config.models import StudioModelsConfig

        config = StudioModelsConfig(allowed_models=["claude-haiku-4", "gpt-4"])
        assert "claude-haiku-4" in config.allowed_models

    def test_studio_models_config_has_blocked_models_field(self) -> None:
        """Test StudioModelsConfig has blocked_models list."""
        from mcp_server_langgraph.studio.config.models import StudioModelsConfig

        config = StudioModelsConfig(blocked_models=["expensive-model"])
        assert "expensive-model" in config.blocked_models


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_config_models")
class TestStudioRule:
    """Tests for StudioRule model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_rule_exists(self) -> None:
        """Test StudioRule model exists."""
        from mcp_server_langgraph.studio.config.models import StudioRule

        assert StudioRule is not None

    def test_studio_rule_has_name_field(self) -> None:
        """Test StudioRule has name field."""
        from mcp_server_langgraph.studio.config.models import StudioRule

        rule = StudioRule(name="no-secrets", description="Don't expose secrets")
        assert rule.name == "no-secrets"

    def test_studio_rule_has_description_field(self) -> None:
        """Test StudioRule has description field."""
        from mcp_server_langgraph.studio.config.models import StudioRule

        rule = StudioRule(name="no-secrets", description="Don't expose secrets")
        assert rule.description == "Don't expose secrets"

    def test_studio_rule_has_severity_field(self) -> None:
        """Test StudioRule has severity field."""
        from mcp_server_langgraph.studio.config.models import StudioRule

        rule = StudioRule(name="no-secrets", description="Don't expose secrets", severity="error")
        assert rule.severity == "error"


@pytest.mark.unit
class TestStudioConfig:
    """Tests for main StudioConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_config_exists(self) -> None:
        """Test StudioConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        assert StudioConfig is not None

    def test_studio_config_has_name_field(self) -> None:
        """Test StudioConfig has name field."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        config = StudioConfig(name="My Project")
        assert config.name == "My Project"

    def test_studio_config_has_description_field(self) -> None:
        """Test StudioConfig has description field."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        config = StudioConfig(name="My Project", description="A test project")
        assert config.description == "A test project"

    def test_studio_config_has_version_field(self) -> None:
        """Test StudioConfig has version field."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        config = StudioConfig(name="My Project", version="1.0.0")
        assert config.version == "1.0.0"

    def test_studio_config_has_tools_section(self) -> None:
        """Test StudioConfig has tools section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioToolsConfig,
        )

        config = StudioConfig(name="My Project", tools=StudioToolsConfig(enabled=["file_reader"]))
        assert config.tools is not None
        assert "file_reader" in config.tools.enabled

    def test_studio_config_has_skills_section(self) -> None:
        """Test StudioConfig has skills section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioSkillsConfig,
        )

        config = StudioConfig(name="My Project", skills=StudioSkillsConfig(enabled=["summarize"]))
        assert config.skills is not None
        assert "summarize" in config.skills.enabled

    def test_studio_config_has_memory_section(self) -> None:
        """Test StudioConfig has memory section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioMemoryConfig,
        )

        config = StudioConfig(name="My Project", memory=StudioMemoryConfig(enabled=True))
        assert config.memory is not None
        assert config.memory.enabled is True

    def test_studio_config_has_cost_section(self) -> None:
        """Test StudioConfig has cost section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioCostConfig,
        )

        config = StudioConfig(name="My Project", cost=StudioCostConfig(max_tokens=5000))
        assert config.cost is not None
        assert config.cost.max_tokens == 5000

    def test_studio_config_has_models_section(self) -> None:
        """Test StudioConfig has models section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioModelsConfig,
        )

        config = StudioConfig(
            name="My Project",
            models=StudioModelsConfig(default_model="claude-haiku-4"),
        )
        assert config.models is not None
        assert config.models.default_model == "claude-haiku-4"

    def test_studio_config_has_rules_section(self) -> None:
        """Test StudioConfig has rules section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioRule,
        )

        config = StudioConfig(
            name="My Project",
            rules=[StudioRule(name="no-secrets", description="No secrets in output")],
        )
        assert config.rules is not None
        assert len(config.rules) == 1
        assert config.rules[0].name == "no-secrets"

    def test_studio_config_has_instructions_field(self) -> None:
        """Test StudioConfig has instructions markdown field."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        config = StudioConfig(
            name="My Project",
            instructions="# Instructions\n\nFollow these guidelines...",
        )
        assert config.instructions is not None
        assert "# Instructions" in config.instructions

    def test_studio_config_has_scope_field(self) -> None:
        """Test StudioConfig has scope field."""
        from mcp_server_langgraph.studio.config.models import StudioConfig
        from mcp_server_langgraph.core.scopes import CapabilityScope

        config = StudioConfig(name="My Project", scope=CapabilityScope.PROJECT)
        assert config.scope == CapabilityScope.PROJECT

    def test_studio_config_scope_defaults_to_project(self) -> None:
        """Test StudioConfig.scope defaults to PROJECT."""
        from mcp_server_langgraph.studio.config.models import StudioConfig
        from mcp_server_langgraph.core.scopes import CapabilityScope

        config = StudioConfig(name="My Project")
        assert config.scope == CapabilityScope.PROJECT


@pytest.mark.unit
class TestStudioConfigValidation:
    """Tests for StudioConfig validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_config_requires_name(self) -> None:
        """Test StudioConfig requires name field."""
        from pydantic import ValidationError

        from mcp_server_langgraph.studio.config.models import StudioConfig

        with pytest.raises(ValidationError):
            StudioConfig()  # type: ignore[call-arg]

    def test_studio_config_extra_fields_ignored(self) -> None:
        """Test StudioConfig ignores unknown fields (forward compat)."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        # Should not raise even with unknown fields
        config = StudioConfig.model_validate({"name": "Test", "unknown_field": "ignored"})
        assert config.name == "Test"

    def test_studio_config_to_dict(self) -> None:
        """Test StudioConfig can be converted to dict."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        config = StudioConfig(name="My Project", version="1.0.0")
        data = config.model_dump()
        assert data["name"] == "My Project"
        assert data["version"] == "1.0.0"
