"""
LiteLLM Cost Fallback Tests

TDD tests for replacing pricing.py fallback with LiteLLM's cost lookup.
Tests cover:
- get_model_cost_from_litellm() function
- Fallback behavior when CostTrackingCallback doesn't fire
- Graceful handling of unknown models
"""

import gc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.monitoring]


@pytest.mark.xdist_group(name="test_litellm_cost_fallback")
class TestLiteLLMCostFallback:
    """Tests for LiteLLM cost lookup as fallback."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_model_cost_returns_decimal(self) -> None:
        """
        GIVEN a model name and token counts
        WHEN calling get_model_cost_from_litellm()
        THEN it should return a Decimal cost
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_model_cost_from_litellm,
        )

        cost = get_model_cost_from_litellm(
            model="gpt-4",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert isinstance(cost, Decimal)
        assert cost >= Decimal("0")

    def test_get_model_cost_uses_litellm_pricing(self) -> None:
        """
        GIVEN a known model
        WHEN calling get_model_cost_from_litellm()
        THEN it should use LiteLLM's pricing data
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_model_cost_from_litellm,
        )

        # GPT-4 is well-known and should have pricing
        cost = get_model_cost_from_litellm(
            model="gpt-4",
            prompt_tokens=1000,
            completion_tokens=1000,
        )

        # GPT-4 costs approximately $0.03/1k input + $0.06/1k output
        # Should be roughly $0.09 for 1k input + 1k output
        assert cost > Decimal("0")
        assert cost < Decimal("1")  # Sanity check - not absurdly high

    def test_get_model_cost_handles_unknown_model(self) -> None:
        """
        GIVEN an unknown model name
        WHEN calling get_model_cost_from_litellm()
        THEN it should return Decimal(0) without raising
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_model_cost_from_litellm,
        )

        cost = get_model_cost_from_litellm(
            model="unknown-model-xyz-123",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Unknown models should return 0 instead of raising
        assert cost == Decimal("0")

    def test_get_model_cost_handles_zero_tokens(self) -> None:
        """
        GIVEN zero token counts
        WHEN calling get_model_cost_from_litellm()
        THEN it should return Decimal(0)
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_model_cost_from_litellm,
        )

        cost = get_model_cost_from_litellm(
            model="gpt-4",
            prompt_tokens=0,
            completion_tokens=0,
        )

        assert cost == Decimal("0")

    def test_get_model_cost_supports_claude_models(self) -> None:
        """
        GIVEN a Claude model name
        WHEN calling get_model_cost_from_litellm()
        THEN it should return appropriate cost
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_model_cost_from_litellm,
        )

        cost = get_model_cost_from_litellm(
            model="claude-3-5-sonnet-20241022",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert cost > Decimal("0")


@pytest.mark.xdist_group(name="test_cost_tracker_fallback")
class TestCostTrackerFallback:
    """Tests for cost_tracker.py using LiteLLM fallback instead of pricing.py."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_usage_uses_litellm_when_cost_not_provided(self) -> None:
        """
        GIVEN a record_usage call without estimated_cost_usd
        WHEN recording usage
        THEN it should use LiteLLM for cost calculation
        """
        from datetime import UTC, datetime
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        with (
            patch("mcp_server_langgraph.monitoring.cost_tracker.get_model_cost_from_litellm") as mock_get_cost,
            patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_get_storage,
        ):
            mock_get_cost.return_value = Decimal("0.05")

            # Mock storage backend with AsyncMock for async methods
            mock_storage = MagicMock()
            mock_storage.store = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_get_storage.return_value = mock_storage

            collector = CostMetricsCollector()

            # Call record_usage without estimated_cost_usd
            import asyncio

            asyncio.run(
                collector.record_usage(
                    timestamp=datetime.now(UTC),
                    user_id="user:test",
                    session_id="session-123",
                    model="gpt-4",
                    provider="openai",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    # estimated_cost_usd NOT provided
                )
            )

            # Verify LiteLLM cost lookup was called
            mock_get_cost.assert_called_once_with(
                model="gpt-4",
                prompt_tokens=1000,
                completion_tokens=500,
            )

    def test_record_usage_skips_fallback_when_cost_provided(self) -> None:
        """
        GIVEN a record_usage call with estimated_cost_usd
        WHEN recording usage
        THEN it should NOT call LiteLLM fallback
        """
        from datetime import UTC, datetime
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        with (
            patch("mcp_server_langgraph.monitoring.cost_tracker.get_model_cost_from_litellm") as mock_get_cost,
            patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_get_storage,
        ):
            # Mock storage backend with AsyncMock for async methods
            mock_storage = MagicMock()
            mock_storage.store = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_get_storage.return_value = mock_storage

            collector = CostMetricsCollector()

            # Call record_usage WITH estimated_cost_usd
            import asyncio

            asyncio.run(
                collector.record_usage(
                    timestamp=datetime.now(UTC),
                    user_id="user:test",
                    session_id="session-123",
                    model="gpt-4",
                    provider="openai",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    estimated_cost_usd=Decimal("0.10"),  # Provided!
                )
            )

            # Verify LiteLLM cost lookup was NOT called
            mock_get_cost.assert_not_called()


@pytest.mark.xdist_group(name="test_no_deprecation_warning")
class TestNoDeprecationWarning:
    """Tests ensuring no deprecation warnings after migration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_usage_no_deprecation_warning(self) -> None:
        """
        GIVEN cost_tracker using LiteLLM fallback
        WHEN recording usage
        THEN no DeprecationWarning should be raised
        """
        import warnings
        from datetime import UTC, datetime
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        with patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_get_storage:
            # Mock storage backend with AsyncMock for async methods
            mock_storage = MagicMock()
            mock_storage.store = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_get_storage.return_value = mock_storage

            collector = CostMetricsCollector()

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                import asyncio

                asyncio.run(
                    collector.record_usage(
                        timestamp=datetime.now(UTC),
                        user_id="user:test",
                        session_id="session-123",
                        model="gpt-4",
                        provider="openai",
                        prompt_tokens=1000,
                        completion_tokens=500,
                    )
                )

                # Check no deprecation warnings from pricing.py
                deprecation_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, DeprecationWarning) and "calculate_cost" in str(warning.message)
                ]
                assert len(deprecation_warnings) == 0, (
                    f"Found deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
                )
