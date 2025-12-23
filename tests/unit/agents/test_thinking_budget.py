"""
Tests for Thinking Budget (Hybrid Approach).

Phase 6 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Hybrid Approach:
- Claude Opus 4.5: Uses native `effort` parameter (low, medium, high)
- Other models: Uses `thinking_budget` token count

Tests cover:
1. ThinkingLevel enum
2. Feature flags for thinking budget
3. ThinkingBudgetManager class
4. Hybrid approach (effort vs thinking_budget)
5. Integration with ModelRegistry
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="thinking_level")
class TestThinkingLevel:
    """Test ThinkingLevel enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_thinking_level_enum_exists(self) -> None:
        """ThinkingLevel enum should exist."""
        from mcp_server_langgraph.agents.thinking_budget import ThinkingLevel

        assert ThinkingLevel is not None

    def test_thinking_level_has_four_values(self) -> None:
        """ThinkingLevel should have LOW, MEDIUM, HIGH, ULTRA."""
        from mcp_server_langgraph.agents.thinking_budget import ThinkingLevel

        assert ThinkingLevel.LOW is not None
        assert ThinkingLevel.MEDIUM is not None
        assert ThinkingLevel.HIGH is not None
        assert ThinkingLevel.ULTRA is not None

    def test_thinking_level_values(self) -> None:
        """ThinkingLevel should have string values."""
        from mcp_server_langgraph.agents.thinking_budget import ThinkingLevel

        assert ThinkingLevel.LOW.value == "low"
        assert ThinkingLevel.MEDIUM.value == "medium"
        assert ThinkingLevel.HIGH.value == "high"
        assert ThinkingLevel.ULTRA.value == "ultra"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="thinking_feature_flags")
class TestThinkingFeatureFlags:
    """Test feature flags for thinking budget."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_thinking_budget_flag_exists(self) -> None:
        """Feature flags should include enable_thinking_budget."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_thinking_budget")

    def test_enable_thinking_budget_default_true(self) -> None:
        """enable_thinking_budget should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_thinking_budget is True

    def test_default_thinking_level_flag_exists(self) -> None:
        """Feature flags should include default_thinking_level."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "default_thinking_level")

    def test_default_thinking_level_is_medium(self) -> None:
        """default_thinking_level should default to 'medium'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.default_thinking_level == "medium"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="thinking_budget_manager_basic")
class TestThinkingBudgetManagerBasic:
    """Test ThinkingBudgetManager basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_thinking_budget_manager_exists(self) -> None:
        """ThinkingBudgetManager class should exist."""
        from mcp_server_langgraph.agents.thinking_budget import ThinkingBudgetManager

        assert ThinkingBudgetManager is not None

    def test_thinking_budget_manager_initialization(self) -> None:
        """ThinkingBudgetManager should initialize correctly."""
        from mcp_server_langgraph.agents.thinking_budget import ThinkingBudgetManager

        manager = ThinkingBudgetManager()
        assert manager is not None
        assert manager.model_registry is not None

    def test_thinking_budget_manager_has_token_budgets(self) -> None:
        """ThinkingBudgetManager should have TOKEN_BUDGETS mapping."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()

        assert ThinkingLevel.LOW in manager.TOKEN_BUDGETS
        assert ThinkingLevel.MEDIUM in manager.TOKEN_BUDGETS
        assert ThinkingLevel.HIGH in manager.TOKEN_BUDGETS
        assert ThinkingLevel.ULTRA in manager.TOKEN_BUDGETS

    def test_token_budget_values(self) -> None:
        """TOKEN_BUDGETS should have expected values."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()

        assert manager.TOKEN_BUDGETS[ThinkingLevel.LOW] == 1024
        assert manager.TOKEN_BUDGETS[ThinkingLevel.MEDIUM] == 8192
        assert manager.TOKEN_BUDGETS[ThinkingLevel.HIGH] == 32768
        assert manager.TOKEN_BUDGETS[ThinkingLevel.ULTRA] == 65536


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="thinking_budget_hybrid")
class TestThinkingBudgetHybridApproach:
    """Test hybrid approach - effort param for Opus, thinking_budget for others."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_params_opus_uses_effort(self) -> None:
        """Opus models should use native effort parameter."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("claude-opus-4-5-20251101", ThinkingLevel.MEDIUM)

        assert "effort" in params
        assert params["effort"] == "medium"
        assert "thinking_budget" not in params

    def test_get_params_opus_low_effort(self) -> None:
        """Opus LOW level should use effort: 'low'."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("claude-opus-4-5-20251101", ThinkingLevel.LOW)

        assert params["effort"] == "low"

    def test_get_params_opus_high_effort(self) -> None:
        """Opus HIGH level should use effort: 'high'."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("claude-opus-4-5-20251101", ThinkingLevel.HIGH)

        assert params["effort"] == "high"

    def test_get_params_opus_ultra_uses_high_effort(self) -> None:
        """Opus ULTRA level should use effort: 'high' (max native level)."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("claude-opus-4-5-20251101", ThinkingLevel.ULTRA)

        # ULTRA maps to high for effort param (highest available)
        assert params["effort"] == "high"

    def test_get_params_sonnet_uses_thinking_budget(self) -> None:
        """Sonnet (non-effort model) should use thinking_budget."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("claude-sonnet-4-5-20250929", ThinkingLevel.MEDIUM)

        assert "thinking_budget" in params
        assert params["thinking_budget"] == 8192
        assert "effort" not in params

    def test_get_params_gemini_uses_thinking_budget(self) -> None:
        """Gemini models should use thinking_budget."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("gemini-3-flash", ThinkingLevel.HIGH)

        assert "thinking_budget" in params
        assert params["thinking_budget"] == 32768

    def test_get_params_gpt_uses_thinking_budget(self) -> None:
        """GPT models should use thinking_budget."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("gpt-5.2", ThinkingLevel.LOW)

        assert "thinking_budget" in params
        assert params["thinking_budget"] == 1024

    def test_get_params_unknown_model_uses_thinking_budget(self) -> None:
        """Unknown models should fallback to thinking_budget."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        params = manager.get_params("unknown-model-xyz", ThinkingLevel.MEDIUM)

        assert "thinking_budget" in params
        assert params["thinking_budget"] == 8192


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="thinking_budget_helpers")
class TestThinkingBudgetHelpers:
    """Test helper methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_default_level(self) -> None:
        """get_default_level should return configured default."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()
        level = manager.get_default_level()

        assert level == ThinkingLevel.MEDIUM

    def test_supports_effort_param(self) -> None:
        """supports_effort_param should correctly identify Opus models."""
        from mcp_server_langgraph.agents.thinking_budget import ThinkingBudgetManager

        manager = ThinkingBudgetManager()

        assert manager.supports_effort_param("claude-opus-4-5-20251101") is True
        assert manager.supports_effort_param("claude-sonnet-4-5-20250929") is False
        assert manager.supports_effort_param("gemini-3-flash") is False
        assert manager.supports_effort_param("gpt-5.2") is False

    def test_level_from_string(self) -> None:
        """level_from_string should convert string to ThinkingLevel."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()

        assert manager.level_from_string("low") == ThinkingLevel.LOW
        assert manager.level_from_string("medium") == ThinkingLevel.MEDIUM
        assert manager.level_from_string("high") == ThinkingLevel.HIGH
        assert manager.level_from_string("ultra") == ThinkingLevel.ULTRA
        # Case insensitive
        assert manager.level_from_string("MEDIUM") == ThinkingLevel.MEDIUM
        assert manager.level_from_string("High") == ThinkingLevel.HIGH

    def test_level_from_string_invalid_defaults_to_medium(self) -> None:
        """level_from_string with invalid input should default to MEDIUM."""
        from mcp_server_langgraph.agents.thinking_budget import (
            ThinkingBudgetManager,
            ThinkingLevel,
        )

        manager = ThinkingBudgetManager()

        assert manager.level_from_string("invalid") == ThinkingLevel.MEDIUM
        assert manager.level_from_string("") == ThinkingLevel.MEDIUM
