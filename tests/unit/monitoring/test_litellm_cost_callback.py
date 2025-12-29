"""
Unit tests for LiteLLM CostTrackingCallback.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 1.1: Testing the LiteLLM callback that automatically records costs
on every LLM call using kwargs["response_cost"] as the authoritative source.

Reference: Plan - Phase 1: LiteLLM Cost Integration via Custom Callback
"""

import gc
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import get_user_id


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
]


@pytest.mark.xdist_group(name="test_litellm_cost_callback")
class TestCostTrackingCallback:
    """Test CostTrackingCallback LiteLLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_callback_extends_custom_logger(self):
        """
        GIVEN: CostTrackingCallback class
        WHEN: Checking class hierarchy
        THEN: Should extend litellm.integrations.custom_logger.CustomLogger
        """
        from litellm.integrations.custom_logger import CustomLogger

        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Assert - callback should be a CustomLogger subclass
        callback = CostTrackingCallback()
        assert isinstance(callback, CustomLogger)

    @pytest.mark.asyncio
    async def test_callback_records_cost_from_response(self):
        """
        GIVEN: CostTrackingCallback and a successful LLM response
        WHEN: async_log_success_event is called with response_cost in kwargs
        THEN: Should record the cost via get_cost_collector().record_usage()
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        # Mock response object with usage
        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 1000
        response_obj.usage.completion_tokens = 500

        # Mock kwargs with response_cost (LiteLLM's calculated cost)
        kwargs = {
            "response_cost": 0.015,  # LiteLLM provides this
            "model": "claude-sonnet-4-5-20250929",
            "custom_llm_provider": "anthropic",
            "litellm_params": {
                "metadata": {
                    "user_id": get_user_id("alice"),
                    "session_id": "session-123",
                    "feature": "chat",
                    "organization_id": "organization:acme",
                    "project_id": "project:backend",
                    "team_id": "team:platform",
                }
            },
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        # Mock the cost collector
        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs

            # Verify cost is from LiteLLM (response_cost)
            assert call_kwargs["estimated_cost_usd"] == Decimal("0.015")
            assert call_kwargs["prompt_tokens"] == 1000
            assert call_kwargs["completion_tokens"] == 500
            assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
            assert call_kwargs["provider"] == "anthropic"

            # Verify organizational context is passed
            assert call_kwargs["organization_id"] == "organization:acme"
            assert call_kwargs["project_id"] == "project:backend"
            assert call_kwargs["team_id"] == "team:platform"

            # Verify user context
            assert call_kwargs["user_id"] == get_user_id("alice")
            assert call_kwargs["session_id"] == "session-123"
            assert call_kwargs["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_callback_handles_missing_usage(self):
        """
        GIVEN: CostTrackingCallback and a response without usage data
        WHEN: async_log_success_event is called
        THEN: Should return early without recording (no error)
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        # Response without usage attribute
        response_obj = MagicMock(spec=[])  # No usage attribute

        kwargs = {
            "response_cost": 0.015,
            "model": "claude-sonnet-4-5-20250929",
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act - should not raise
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert - should not record when no usage
            mock_collector.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_handles_zero_cost(self):
        """
        GIVEN: CostTrackingCallback and a response with zero cost
        WHEN: async_log_success_event is called
        THEN: Should still record with Decimal("0")
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {
            "response_cost": 0,  # Zero cost (e.g., cached response)
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "litellm_params": {"metadata": {}},
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert - should still record
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["estimated_cost_usd"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_callback_uses_defaults_for_missing_metadata(self):
        """
        GIVEN: CostTrackingCallback and kwargs without metadata
        WHEN: async_log_success_event is called
        THEN: Should use sensible defaults for missing fields
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        # Minimal kwargs - no metadata
        kwargs = {
            "response_cost": 0.005,
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            # No litellm_params or metadata
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert - should use defaults
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs

            assert call_kwargs["user_id"] == "anonymous"
            assert call_kwargs["session_id"] == "unknown"
            assert call_kwargs["feature"] == "chat"
            assert call_kwargs["organization_id"] is None
            assert call_kwargs["project_id"] is None
            assert call_kwargs["team_id"] is None

    @pytest.mark.asyncio
    async def test_callback_handles_none_metadata(self):
        """
        GIVEN: CostTrackingCallback and kwargs with metadata=None
        WHEN: async_log_success_event is called
        THEN: Should use sensible defaults without raising AttributeError

        Regression test for: AttributeError: 'NoneType' object has no attribute 'get'
        This occurs when LiteLLM passes metadata=None instead of an empty dict.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        # metadata is explicitly None (not missing, but None)
        kwargs = {
            "response_cost": 0.005,
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "litellm_params": {"metadata": None},  # Explicitly None
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act - should not raise AttributeError
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert - should use defaults
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs

            assert call_kwargs["user_id"] == "anonymous"
            assert call_kwargs["session_id"] == "unknown"
            assert call_kwargs["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_callback_handles_none_litellm_params(self):
        """
        GIVEN: CostTrackingCallback and kwargs with litellm_params=None
        WHEN: async_log_success_event is called
        THEN: Should use sensible defaults without raising AttributeError

        Regression test for: AttributeError: 'NoneType' object has no attribute 'get'
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        # litellm_params is explicitly None
        kwargs = {
            "response_cost": 0.005,
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "litellm_params": None,  # Explicitly None
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act - should not raise AttributeError
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert - should use defaults
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs

            assert call_kwargs["user_id"] == "anonymous"
            assert call_kwargs["session_id"] == "unknown"
            assert call_kwargs["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_callback_handles_missing_response_cost(self):
        """
        GIVEN: CostTrackingCallback and kwargs without response_cost
        WHEN: async_log_success_event is called
        THEN: Should record with Decimal("0") as cost
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        # No response_cost in kwargs
        kwargs = {
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "litellm_params": {"metadata": {}},
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert - should use 0 as default cost
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["estimated_cost_usd"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_callback_extracts_trace_and_workflow_ids(self):
        """
        GIVEN: CostTrackingCallback with trace_id and workflow_id in metadata
        WHEN: async_log_success_event is called
        THEN: Should pass trace_id and workflow_id to record_usage
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        response_obj = MagicMock()
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {
            "response_cost": 0.01,
            "model": "claude-sonnet-4-5-20250929",
            "custom_llm_provider": "anthropic",
            "litellm_params": {
                "metadata": {
                    "user_id": get_user_id("alice"),
                    "session_id": "session-123",
                    "trace_id": "trace-abc-123",
                    "workflow_id": "workflow:agent-chat",
                }
            },
        }

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        mock_collector = AsyncMock()  # noqa: async-mock-config
        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            # Act
            await callback.async_log_success_event(kwargs, response_obj, start_time, end_time)

            # Assert
            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["trace_id"] == "trace-abc-123"
            assert call_kwargs["workflow_id"] == "workflow:agent-chat"


@pytest.mark.xdist_group(name="test_litellm_cost_callback")
class TestCostTrackingCallbackRegistration:
    """Test CostTrackingCallback registration with LiteLLM."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_callback_can_be_instantiated(self):
        """
        GIVEN: CostTrackingCallback class
        WHEN: Instantiating the callback
        THEN: Should create instance without errors
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Act
        callback = CostTrackingCallback()

        # Assert
        assert callback is not None

    def test_callback_has_required_async_methods(self):
        """
        GIVEN: CostTrackingCallback instance
        WHEN: Checking for required async callback methods
        THEN: Should have async_log_success_event method
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Arrange
        callback = CostTrackingCallback()

        # Assert - must have async success handler
        assert hasattr(callback, "async_log_success_event")
        assert callable(callback.async_log_success_event)


@pytest.mark.xdist_group(name="test_litellm_cost_callback")
class TestConfigureLiteLLMCostTracking:
    """Test configure_litellm_cost_tracking function."""

    def setup_method(self) -> None:
        """Reset configuration before each test."""
        from mcp_server_langgraph.llm.otel_integration import reset_cost_tracking_configuration

        reset_cost_tracking_configuration()

    def teardown_method(self) -> None:
        """Reset configuration and force GC."""
        from mcp_server_langgraph.llm.otel_integration import reset_cost_tracking_configuration

        reset_cost_tracking_configuration()
        gc.collect()

    def test_configure_cost_tracking_adds_callback(self):
        """
        GIVEN: LiteLLM with no cost tracking callback
        WHEN: configure_litellm_cost_tracking is called
        THEN: CostTrackingCallback should be added to litellm.callbacks
        """
        import litellm

        from mcp_server_langgraph.llm.otel_integration import (
            configure_litellm_cost_tracking,
        )
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Store original callbacks
        original_callbacks = litellm.callbacks.copy() if hasattr(litellm.callbacks, "copy") else list(litellm.callbacks)

        try:
            # Act
            configure_litellm_cost_tracking()

            # Assert - should have CostTrackingCallback in callbacks
            cost_callbacks = [cb for cb in litellm.callbacks if isinstance(cb, CostTrackingCallback)]
            assert len(cost_callbacks) == 1, "Should have exactly one CostTrackingCallback"

        finally:
            # Cleanup
            litellm.callbacks = original_callbacks

    def test_configure_cost_tracking_is_idempotent(self):
        """
        GIVEN: configure_litellm_cost_tracking already called
        WHEN: configure_litellm_cost_tracking is called again
        THEN: Should not add duplicate callback
        """
        import litellm

        from mcp_server_langgraph.llm.otel_integration import (
            configure_litellm_cost_tracking,
        )
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Store original callbacks
        original_callbacks = litellm.callbacks.copy() if hasattr(litellm.callbacks, "copy") else list(litellm.callbacks)

        try:
            # Call twice
            configure_litellm_cost_tracking()
            configure_litellm_cost_tracking()

            # Assert - should still have exactly one CostTrackingCallback
            cost_callbacks = [cb for cb in litellm.callbacks if isinstance(cb, CostTrackingCallback)]
            assert len(cost_callbacks) == 1, "Should have exactly one CostTrackingCallback even after multiple calls"

        finally:
            # Cleanup
            litellm.callbacks = original_callbacks


@pytest.mark.xdist_group(name="test_litellm_cost_callback")
class TestCostTrackingStartupIntegration:
    """Tests for cost tracking callback registration during app startup."""

    def setup_method(self) -> None:
        """Reset configuration before each test."""
        from mcp_server_langgraph.llm.otel_integration import reset_cost_tracking_configuration

        reset_cost_tracking_configuration()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.llm.otel_integration import reset_cost_tracking_configuration

        reset_cost_tracking_configuration()
        gc.collect()

    @pytest.mark.asyncio
    async def test_cost_tracking_registered_during_lifespan(self) -> None:
        """
        GIVEN: An application using create_lifespan
        WHEN: The lifespan context is entered
        THEN: CostTrackingCallback should be registered in litellm.callbacks
        """
        import litellm

        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Store original callbacks
        original_callbacks = litellm.callbacks.copy() if hasattr(litellm.callbacks, "copy") else list(litellm.callbacks)

        try:
            # Enter lifespan context (with no container for simpler test)
            async with create_lifespan(container=None):
                # During lifespan, the callback should be registered
                cost_callbacks = [cb for cb in litellm.callbacks if isinstance(cb, CostTrackingCallback)]
                assert len(cost_callbacks) >= 1, "CostTrackingCallback should be registered during lifespan"

        finally:
            # Cleanup
            litellm.callbacks = original_callbacks
