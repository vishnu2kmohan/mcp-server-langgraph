"""
Tests for PATCH /api/v1/agents/config/thinking-budget endpoint.

TDD tests for editable thinking budget functionality.
Tests cover:
- Updating default thinking level
- Validation of thinking level values
- Feature flag configuration update
- Error handling for invalid inputs
"""

import pytest
from unittest.mock import patch

from mcp_server_langgraph.api.v1.agents import (
    ThinkingBudgetUpdateRequest,
    update_thinking_budget,
)

pytestmark = pytest.mark.unit


class TestThinkingBudgetUpdateRequestModel:
    """Tests for ThinkingBudgetUpdateRequest Pydantic model."""

    def test_valid_request_with_default_level(self) -> None:
        """Should accept valid thinking level values."""
        request = ThinkingBudgetUpdateRequest(default_level="high")
        assert request.default_level == "high"

    def test_valid_request_with_enabled(self) -> None:
        """Should accept enabled flag."""
        request = ThinkingBudgetUpdateRequest(enabled=False)
        assert request.enabled is False

    def test_valid_request_with_both_fields(self) -> None:
        """Should accept both fields."""
        request = ThinkingBudgetUpdateRequest(default_level="ultra", enabled=True)
        assert request.default_level == "ultra"
        assert request.enabled is True

    def test_valid_thinking_levels(self) -> None:
        """Should accept all valid thinking levels."""
        valid_levels = ["low", "medium", "high", "ultra"]
        for level in valid_levels:
            request = ThinkingBudgetUpdateRequest(default_level=level)
            assert request.default_level == level

    def test_invalid_thinking_level_rejected(self) -> None:
        """Should reject invalid thinking level values."""
        with pytest.raises(ValueError):
            ThinkingBudgetUpdateRequest(default_level="invalid")

    def test_empty_request_allowed(self) -> None:
        """Should allow empty request (no updates)."""
        request = ThinkingBudgetUpdateRequest()
        assert request.default_level is None
        assert request.enabled is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestUpdateThinkingBudget:
    """Tests for the PATCH endpoint handler."""

    @pytest.mark.asyncio
    async def test_update_default_level(self) -> None:
        """Should update default thinking level."""
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_flags:
            mock_flags.default_thinking_level = "medium"
            mock_flags.enable_thinking_budget = True

            request = ThinkingBudgetUpdateRequest(default_level="high")
            result = await update_thinking_budget(request)

            assert result.success is True
            assert result.updated_fields == ["default_level"]

    @pytest.mark.asyncio
    async def test_update_enabled_flag(self) -> None:
        """Should update enabled flag."""
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_flags:
            mock_flags.enable_thinking_budget = True
            mock_flags.default_thinking_level = "medium"

            request = ThinkingBudgetUpdateRequest(enabled=False)
            result = await update_thinking_budget(request)

            assert result.success is True
            assert result.updated_fields == ["enabled"]

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self) -> None:
        """Should update multiple fields at once."""
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_flags:
            mock_flags.enable_thinking_budget = True
            mock_flags.default_thinking_level = "medium"

            request = ThinkingBudgetUpdateRequest(default_level="ultra", enabled=True)
            result = await update_thinking_budget(request)

            assert result.success is True
            assert set(result.updated_fields) == {"default_level", "enabled"}

    @pytest.mark.asyncio
    async def test_empty_request_returns_no_changes(self) -> None:
        """Should return success with no changes for empty request."""
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_flags:
            mock_flags.enable_thinking_budget = True
            mock_flags.default_thinking_level = "medium"

            request = ThinkingBudgetUpdateRequest()
            result = await update_thinking_budget(request)

            assert result.success is True
            assert result.updated_fields == []

    @pytest.mark.asyncio
    async def test_returns_current_config_after_update(self) -> None:
        """Should return current configuration after update."""
        with patch("mcp_server_langgraph.api.v1.agents.feature_flags") as mock_flags:
            mock_flags.enable_thinking_budget = True
            mock_flags.default_thinking_level = "high"

            request = ThinkingBudgetUpdateRequest(default_level="high")
            result = await update_thinking_budget(request)

            assert result.current_config is not None
            assert result.current_config.default_level == "high"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
