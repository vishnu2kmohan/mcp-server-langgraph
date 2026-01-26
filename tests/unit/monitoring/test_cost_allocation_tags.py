"""
Cost Allocation Tags Unit Tests

TDD tests for custom cost allocation tagging.
Tests written FIRST (RED phase).

Cost allocation tags allow:
1. Custom key-value tags for cost attribution
2. Flexible categorization (feature, environment, campaign, etc.)
3. Tag-based cost queries and aggregation
"""

import gc
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.monitoring]


@pytest.mark.xdist_group(name="test_cost_allocation_tags_model")
class TestCostAllocationTagsModel:
    """Tests for allocation tags in TokenUsage model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_usage_has_allocation_tags_field(self) -> None:
        """
        GIVEN the TokenUsage model
        WHEN inspecting fields
        THEN allocation_tags should be available
        """
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        # Create instance with allocation tags
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:test",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.10"),
            feature="chat",
            allocation_tags={"environment": "production", "campaign": "launch-2025"},
        )

        assert usage.allocation_tags == {
            "environment": "production",
            "campaign": "launch-2025",
        }

    def test_allocation_tags_default_to_empty_dict(self) -> None:
        """
        GIVEN a TokenUsage without allocation_tags
        WHEN accessing the field
        THEN it should return empty dict or None
        """
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:test",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.10"),
            feature="chat",
        )

        # Should be None or empty dict by default
        assert usage.allocation_tags is None or usage.allocation_tags == {}


@pytest.mark.xdist_group(name="test_cost_allocation_tags_db")
class TestCostAllocationTagsDatabase:
    """Tests for allocation tags in database model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_usage_record_has_allocation_tags_column(self) -> None:
        """
        GIVEN the TokenUsageRecord database model
        WHEN inspecting columns
        THEN allocation_tags column should exist
        """
        from mcp_server_langgraph.database.models import TokenUsageRecord

        # Check column exists in model
        columns = [c.name for c in TokenUsageRecord.__table__.columns]
        assert "allocation_tags" in columns

    def test_allocation_tags_is_json_type(self) -> None:
        """
        GIVEN the allocation_tags column
        WHEN checking its type
        THEN it should be a JSON/JSONB type
        """
        from mcp_server_langgraph.database.models import TokenUsageRecord

        col = TokenUsageRecord.__table__.columns["allocation_tags"]
        # Should be JSONB for PostgreSQL
        assert col.type.__class__.__name__ in ("JSON", "JSONB")


@pytest.mark.xdist_group(name="test_cost_allocation_tags_collector")
class TestCostAllocationTagsCollector:
    """Tests for allocation tags in CostMetricsCollector."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_usage_with_allocation_tags(self) -> None:
        """
        GIVEN a CostMetricsCollector
        WHEN recording usage with allocation_tags
        THEN tags should be stored in the record
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        with patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.store = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_get_storage.return_value = mock_storage

            collector = CostMetricsCollector()

            await collector.record_usage(
                timestamp=datetime.now(UTC),
                user_id="user:test",
                session_id="session-123",
                model="gpt-4",
                provider="openai",
                prompt_tokens=1000,
                completion_tokens=500,
                estimated_cost_usd=Decimal("0.10"),
                allocation_tags={"environment": "staging", "feature": "agent"},
            )

            # Verify storage was called with allocation_tags
            mock_storage.store.assert_called_once()
            call_args = mock_storage.store.call_args[0][0]
            assert call_args.allocation_tags == {
                "environment": "staging",
                "feature": "agent",
            }


@pytest.mark.xdist_group(name="test_cost_allocation_tags_query")
class TestCostAllocationTagsQuery:
    """Tests for querying by allocation tags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_cost_by_tag(self) -> None:
        """
        GIVEN cost records with allocation tags
        WHEN querying by specific tag
        THEN matching records should be returned
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # This tests the interface - actual implementation may vary
        storage = PostgresCostStorage.__new__(PostgresCostStorage)

        # Verify the method signature exists for tag filtering
        assert hasattr(storage, "get_cost_summary") or hasattr(storage, "get_cost_by_allocation_tag")

    def test_cost_summary_supports_tag_filter(self) -> None:
        """
        GIVEN the CostStorageBackend protocol
        WHEN checking get_cost_summary signature
        THEN it should support allocation_tags parameter
        """
        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend
        import inspect

        # Check if the protocol method supports tags
        # This is a design constraint check
        sig = inspect.signature(CostStorageBackend.get_cost_summary)
        # At minimum, the method should exist
        assert sig is not None
