"""
Unit tests for CostStorageBackend extracted from CostMetricsCollector.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.2 SRP decomposition - Testing storage backends separately
from cost collection and retention logic.

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector
"""

import gc
from datetime import datetime, UTC
from decimal import Decimal

import pytest

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
from tests.conftest import get_user_id


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
]


@pytest.mark.xdist_group(name="test_cost_storage")
class TestMemoryCostStorage:
    """Test MemoryCostStorage in-memory backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_record(self):
        """
        GIVEN: MemoryCostStorage instance
        WHEN: Storing a token usage record
        THEN: Record should be stored successfully
        """
        # Import here to trigger RED phase initially
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("alice"),
            session_id="session-123",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.015"),
        )

        # Act
        await storage.store(usage)

        # Assert
        assert storage.total_records == 1

    @pytest.mark.asyncio
    async def test_get_records_returns_all(self):
        """
        GIVEN: MemoryCostStorage with multiple records
        WHEN: Getting records without filters
        THEN: Should return all records
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        for i in range(3):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(str(i)),
                session_id=f"session-{i}",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        # Act
        records, _ = await storage.get_records()

        # Assert
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_get_records_filter_by_user(self):
        """
        GIVEN: MemoryCostStorage with records from different users
        WHEN: Getting records filtered by user_id
        THEN: Should return only matching records
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        alice_id = get_user_id("alice")
        bob_id = get_user_id("bob")
        users = [alice_id, bob_id, alice_id]  # Two alice, one bob
        for i, user_id in enumerate(users):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=user_id,
                session_id=f"session-{i}",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        # Act
        records, _ = await storage.get_records(filters={"user_id": alice_id})

        # Assert
        assert len(records) == 2
        assert all(r.user_id == alice_id for r in records)

    @pytest.mark.asyncio
    async def test_get_records_filter_by_model(self):
        """
        GIVEN: MemoryCostStorage with records from different models
        WHEN: Getting records filtered by model
        THEN: Should return only matching records
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        models = ["gpt-4", "claude-3", "gpt-4"]
        user_id = get_user_id("alice")
        for i, model in enumerate(models):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=user_id,
                session_id=f"session-{i}",
                model=model,
                provider="openai" if model.startswith("gpt") else "anthropic",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        # Act
        records, _ = await storage.get_records(filters={"model": "gpt-4"})

        # Assert
        assert len(records) == 2
        assert all(r.model == "gpt-4" for r in records)

    @pytest.mark.asyncio
    async def test_delete_records_before_cutoff(self):
        """
        GIVEN: MemoryCostStorage with old and new records
        WHEN: Deleting records before a cutoff time
        THEN: Should delete only old records
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)
        old_time = now - timedelta(days=100)
        new_time = now - timedelta(days=10)

        # Old record
        old_usage = TokenUsage(
            timestamp=old_time,
            user_id=get_user_id("alice"),
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(old_usage)

        # New record
        new_usage = TokenUsage(
            timestamp=new_time,
            user_id=get_user_id("bob"),
            session_id="session-new",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(new_usage)

        # Act
        cutoff = now - timedelta(days=90)
        deleted = await storage.delete_records_before(cutoff)

        # Assert
        assert deleted == 1
        remaining, _ = await storage.get_records()
        assert len(remaining) == 1
        assert remaining[0].session_id == "session-new"

    @pytest.mark.asyncio
    async def test_get_latest_record(self):
        """
        GIVEN: MemoryCostStorage with multiple records
        WHEN: Getting the latest record
        THEN: Should return the most recently stored record
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        for i in range(3):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(str(i)),
                session_id=f"session-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        # Act
        latest = await storage.get_latest_record()

        # Assert
        assert latest is not None
        assert latest.session_id == "session-2"

    @pytest.mark.asyncio
    async def test_get_latest_record_empty_storage(self):
        """
        GIVEN: Empty MemoryCostStorage
        WHEN: Getting the latest record
        THEN: Should return None
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()

        # Act
        latest = await storage.get_latest_record()

        # Assert
        assert latest is None


@pytest.mark.xdist_group(name="test_cost_storage")
class TestCostStorageBackendProtocol:
    """Test CostStorageBackend protocol compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_storage_implements_protocol(self):
        """
        GIVEN: MemoryCostStorage class
        WHEN: Checking protocol compliance
        THEN: Should be a valid CostStorageBackend implementation
        """
        from mcp_server_langgraph.monitoring.cost_storage import (
            CostStorageBackend,
            MemoryCostStorage,
        )

        # Assert - MemoryCostStorage should implement CostStorageBackend
        storage = MemoryCostStorage()
        assert isinstance(storage, CostStorageBackend)

    def test_protocol_is_runtime_checkable(self):
        """
        GIVEN: CostStorageBackend protocol
        WHEN: Checking if it's runtime checkable
        THEN: Should be usable with isinstance()
        """

        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        # Assert - protocol should be runtime checkable
        assert hasattr(CostStorageBackend, "__protocol_attrs__") or hasattr(CostStorageBackend, "_is_protocol")
