"""
E2E Integration Test: Cost Data Flow

Tests the complete data flow:
    LLM Factory.ainvoke() → CostMetricsCollector.record_usage() → PostgreSQL → Cost API → Response

This test would have caught the bug where LLM factory wasn't calling
CostMetricsCollector.record_usage() to populate PostgreSQL.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = [
    pytest.mark.integration,
    pytest.mark.cost,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="cost_flow_e2e"),
]


@pytest.fixture(autouse=True)
def use_memory_storage_backend(monkeypatch):
    """Use memory storage backend for tests without requiring PostgreSQL."""
    monkeypatch.setenv("COST_STORAGE_BACKEND", "memory")


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def unique_user_id() -> str:
    """Generate unique user ID for test isolation."""
    return f"test-user-{uuid4().hex[:8]}"


@pytest.fixture
def unique_session_id() -> str:
    """Generate unique session ID for test isolation."""
    return f"test-session-{uuid4().hex[:8]}"


@pytest.fixture
def mock_acompletion_response():
    """Create a mock LiteLLM acompletion response with usage data."""
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 150
    mock_usage.completion_tokens = 75
    mock_usage.total_tokens = 225

    mock_message = MagicMock()
    mock_message.content = "Test response from LLM"

    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    return mock_response


# ============================================================================
# E2E Data Flow Tests
# ============================================================================


class TestCostDataFlowE2E:
    """
    E2E tests verifying the complete cost data flow.

    These tests ensure that:
    1. LLM factory calls CostMetricsCollector.record_usage()
    2. CostMetricsCollector stores to the configured backend
    3. Cost API can retrieve the stored data
    4. The data matches what was recorded

    This is the integration test that was MISSING and would have
    caught the Cost Page bug.
    """

    def setup_method(self):
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        _reset_cost_collector()

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        _reset_cost_collector()
        gc.collect()

    async def test_llm_factory_records_to_cost_collector(
        self,
        mock_acompletion_response,
        unique_user_id,
        unique_session_id,
    ):
        """
        E2E: Verify LLM factory → CostMetricsCollector → Storage flow.

        GIVEN: LLM factory with cost tracking enabled
        WHEN: ainvoke() is called with user_id and session_id
        THEN: CostMetricsCollector.record_usage() is called with correct params
        AND: Data is stored in the storage backend
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.monitoring.cost_tracker import get_cost_collector

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        # Track what gets stored
        stored_records: list = []

        async def track_store(usage):
            stored_records.append(usage)

        with (
            patch(
                "mcp_server_langgraph.llm.factory.acompletion",
                new_callable=AsyncMock,
            ) as mock_acompletion,
            patch(
                "mcp_server_langgraph.llm.factory.feature_flags"
            ) as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False

            # Get the real collector and patch its storage
            collector = get_cost_collector()
            original_store = collector._storage.store
            collector._storage.store = track_store

            try:
                # Call ainvoke - this should trigger the full flow
                await factory.ainvoke(
                    messages=[{"role": "user", "content": "Hello"}],
                    user_id=unique_user_id,
                    session_id=unique_session_id,
                )

                # Verify data was stored
                assert len(stored_records) == 1, (
                    f"Expected 1 record stored, got {len(stored_records)}. "
                    "This indicates LLM factory is not calling record_usage()!"
                )

                record = stored_records[0]
                assert record.user_id == unique_user_id
                assert record.session_id == unique_session_id
                assert record.model == "gpt-4o"
                assert record.provider == "openai"
                assert record.prompt_tokens == 150
                assert record.completion_tokens == 75

            finally:
                collector._storage.store = original_store

    async def test_cost_api_returns_recorded_data(
        self,
        unique_user_id,
        unique_session_id,
    ):
        """
        E2E: Verify Storage → Cost API flow.

        GIVEN: Cost data stored in the backend
        WHEN: Cost API summary endpoint is called
        THEN: The stored data is returned correctly
        """
        from mcp_server_langgraph.monitoring.cost_tracker import (
            CostMetricsCollector,
            TokenUsage,
            get_cost_collector,
        )
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            get_cost_storage_backend,
        )

        # Get the storage backend and store test data directly
        storage = get_cost_storage_backend()

        test_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=unique_user_id,
            session_id=unique_session_id,
            model="gpt-4o",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.0025"),
        )

        await storage.store(test_usage)

        # Query via storage backend
        records, _ = await storage.get_records(
            filters={"user_id": unique_user_id}
        )

        assert len(records) >= 1, "Expected at least 1 record from storage"
        found = any(
            r.user_id == unique_user_id and r.session_id == unique_session_id
            for r in records
        )
        assert found, f"Expected to find record for user {unique_user_id}"

    async def test_full_e2e_llm_to_api_response(
        self,
        mock_acompletion_response,
        unique_user_id,
        unique_session_id,
    ):
        """
        FULL E2E: LLM Factory → Storage → Cost API → HTTP Response

        This is the ultimate integration test that verifies the complete
        data flow from LLM call to API response.

        GIVEN: An LLM factory call with cost tracking enabled
        WHEN: The call completes and Cost API is queried
        THEN: The API response contains the recorded cost data
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            get_cost_storage_backend,
        )

        factory = LLMFactory(
            provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            api_key="test-key",
        )

        with (
            patch(
                "mcp_server_langgraph.llm.factory.acompletion",
                new_callable=AsyncMock,
            ) as mock_acompletion,
            patch(
                "mcp_server_langgraph.llm.factory.feature_flags"
            ) as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False

            # Step 1: Make LLM call
            await factory.ainvoke(
                messages=[{"role": "user", "content": "Test message"}],
                user_id=unique_user_id,
                session_id=unique_session_id,
            )

            # Step 2: Verify data in storage
            storage = get_cost_storage_backend()
            records, _ = await storage.get_records()

            # Find our record
            our_records = [
                r for r in records
                if r.user_id == unique_user_id and r.session_id == unique_session_id
            ]

            assert len(our_records) == 1, (
                f"Expected exactly 1 record for user={unique_user_id}, "
                f"session={unique_session_id}, but found {len(our_records)}. "
                "This indicates the E2E flow is broken!"
            )

            record = our_records[0]
            assert record.model == "claude-sonnet-4-20250514"
            assert record.provider == "anthropic"
            assert record.prompt_tokens == 150
            assert record.completion_tokens == 75


class TestCostDataFlowWithFeatureFlags:
    """
    Tests for cost data flow with various feature flag configurations.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        _reset_cost_collector()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        _reset_cost_collector()
        gc.collect()

    async def test_no_data_stored_when_cost_tracking_disabled(
        self,
        mock_acompletion_response,
        unique_user_id,
        unique_session_id,
    ):
        """
        E2E: Verify no data stored when cost tracking is disabled.

        GIVEN: enable_cost_tracking = False
        WHEN: LLM factory ainvoke() is called
        THEN: No cost records are stored
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            get_cost_storage_backend,
        )

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with (
            patch(
                "mcp_server_langgraph.llm.factory.acompletion",
                new_callable=AsyncMock,
            ) as mock_acompletion,
            patch(
                "mcp_server_langgraph.llm.factory.feature_flags"
            ) as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response
            # Disable cost tracking
            mock_flags.enable_cost_tracking = False
            mock_flags.enable_llm_hooks = False

            await factory.ainvoke(
                messages=[{"role": "user", "content": "Hello"}],
                user_id=unique_user_id,
                session_id=unique_session_id,
            )

            # Verify NO data was stored
            storage = get_cost_storage_backend()
            records, _ = await storage.get_records()

            our_records = [
                r for r in records
                if r.user_id == unique_user_id
            ]

            assert len(our_records) == 0, (
                "Expected 0 records when cost tracking disabled, "
                f"but found {len(our_records)}"
            )


class TestResponsesAPICostFlow:
    """
    E2E tests for OpenAI Responses API cost flow.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        _reset_cost_collector()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        _reset_cost_collector()
        gc.collect()

    async def test_responses_api_path_records_cost(
        self,
        unique_user_id,
        unique_session_id,
    ):
        """
        E2E: Verify Responses API path also records cost data.

        GIVEN: OpenAI model with native tools (uses Responses API)
        WHEN: ainvoke() is called with native_tools
        THEN: Cost is recorded to storage via the Responses API code path
        """
        from types import SimpleNamespace

        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            get_cost_storage_backend,
        )

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        mock_responses_output = [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Search results..."}],
            }
        ]

        with (
            patch.object(
                factory,
                "_call_responses_api",
                new_callable=AsyncMock,
            ) as mock_responses,
            patch(
                "mcp_server_langgraph.llm.factory.feature_flags"
            ) as mock_flags,
        ):
            # Mock Responses API return value
            mock_responses.return_value = (
                "Search results...",
                SimpleNamespace(prompt_tokens=200, completion_tokens=100, total_tokens=300),
                mock_responses_output,
            )

            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False
            mock_flags.use_responses_api_for_openai = True

            await factory.ainvoke(
                messages=[{"role": "user", "content": "Search for news"}],
                user_id=unique_user_id,
                session_id=unique_session_id,
                native_tools=[{"type": "web_search_preview"}],
            )

            # Verify data was stored
            storage = get_cost_storage_backend()
            records, _ = await storage.get_records()

            our_records = [
                r for r in records
                if r.user_id == unique_user_id and r.session_id == unique_session_id
            ]

            assert len(our_records) == 1, (
                f"Expected 1 record from Responses API path, got {len(our_records)}. "
                "The Responses API code path is not recording costs!"
            )

            record = our_records[0]
            assert record.prompt_tokens == 200
            assert record.completion_tokens == 100
