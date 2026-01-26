"""
Unit tests for PostgresCostStorage.

TDD Cycle: RED -> GREEN -> REFACTOR

Testing PostgreSQL storage backend for cost metrics.

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector
"""

import gc
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend
from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
]


def create_test_usage(
    timestamp: datetime | None = None,
    user_id: str = "user:alice",
    session_id: str = "session-123",
    model: str = "claude-sonnet-4-5-20250929",
    provider: str = "anthropic",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    cost: Decimal | None = None,
) -> TokenUsage:
    """Create a test TokenUsage record."""
    return TokenUsage(
        timestamp=timestamp or datetime.now(UTC),
        user_id=user_id,
        session_id=session_id,
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=cost or Decimal("0.001"),
    )


@pytest.mark.xdist_group(name="test_postgres_cost_storage")
class TestPostgresCostStorageProtocol:
    """Test PostgresCostStorage implements CostStorageBackend protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_compliance_with_valid_instance_returns_true(self):
        """
        GIVEN: PostgresCostStorage class
        WHEN: Checking protocol compliance
        THEN: Should implement CostStorageBackend protocol
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Assert - instance implements protocol (use isinstance for protocols with properties)
        storage = PostgresCostStorage("postgresql://test")
        assert isinstance(storage, CostStorageBackend)

    def test_has_required_methods(self):
        """
        GIVEN: PostgresCostStorage instance
        WHEN: Checking for required methods
        THEN: Should have all protocol methods
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange
        storage = PostgresCostStorage("postgresql://test")

        # Assert - has all required methods
        assert hasattr(storage, "store")
        assert hasattr(storage, "get_records")
        assert hasattr(storage, "delete_records_before")
        assert hasattr(storage, "get_latest_record")
        assert hasattr(storage, "total_records")


@pytest.mark.xdist_group(name="test_postgres_cost_storage")
class TestPostgresCostStorageStore:
    """Test PostgresCostStorage store operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_creates_database_record(self):
        """
        GIVEN: PostgresCostStorage instance
        WHEN: Storing a TokenUsage record
        THEN: Should create database record via session
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange - mock session with async context manager behavior
        mock_session = AsyncMock(return_value=None)  # async-mock-configured (mock for session context)
        mock_session.add = MagicMock(return_value=None)
        mock_session.commit = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.database.get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            storage = PostgresCostStorage("postgresql://test")
            usage = create_test_usage()

            # Act
            await storage.store(usage)

            # Assert
            mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_increments_total_records(self):
        """
        GIVEN: PostgresCostStorage instance
        WHEN: Storing multiple records
        THEN: Should track total record count
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange - mock session with async context manager behavior
        mock_session = AsyncMock(return_value=None)  # async-mock-configured (mock for session context)
        mock_session.add = MagicMock(return_value=None)
        mock_session.commit = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.database.get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            storage = PostgresCostStorage("postgresql://test")

            # Act
            await storage.store(create_test_usage())
            await storage.store(create_test_usage())

            # Assert
            assert storage.total_records >= 2


@pytest.mark.xdist_group(name="test_postgres_cost_storage")
class TestPostgresCostStorageGetRecords:
    """Test PostgresCostStorage get_records operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_records_returns_list(self):
        """
        GIVEN: PostgresCostStorage instance with records
        WHEN: Getting all records
        THEN: Should return list of TokenUsage
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange - mock session with query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock(return_value=None)  # async-mock-configured (mock for session context)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("mcp_server_langgraph.database.get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            storage = PostgresCostStorage("postgresql://test")

            # Act
            # get_records returns (records, next_cursor)
            records, next_cursor = await storage.get_records()

            # Assert
            assert isinstance(records, list)
            assert next_cursor is None or isinstance(next_cursor, str)

    @pytest.mark.asyncio
    async def test_get_records_with_user_filter(self):
        """
        GIVEN: PostgresCostStorage instance
        WHEN: Getting records with user_id filter
        THEN: Should filter by user_id
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange - mock session with query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock(return_value=None)  # async-mock-configured (mock for session context)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("mcp_server_langgraph.database.get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            storage = PostgresCostStorage("postgresql://test")

            # Act
            # get_records returns (records, next_cursor)
            records, _ = await storage.get_records(filters={"user_id": "user:alice"})

            # Assert
            assert isinstance(records, list)
            # Verify execute was called (filter applied in query)
            mock_session.execute.assert_called_once()


@pytest.mark.xdist_group(name="test_postgres_cost_storage")
class TestPostgresCostStorageDeleteRecords:
    """Test PostgresCostStorage delete_records_before operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_records_before_returns_count(self):
        """
        GIVEN: PostgresCostStorage instance
        WHEN: Deleting records before cutoff
        THEN: Should return number of deleted records
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange - mock session with delete result
        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = AsyncMock(return_value=None)  # async-mock-configured (mock for session context)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.database.get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            storage = PostgresCostStorage("postgresql://test")
            cutoff = datetime.now(UTC) - timedelta(days=90)

            # Act
            deleted_count = await storage.delete_records_before(cutoff)

            # Assert
            assert deleted_count == 5


@pytest.mark.xdist_group(name="test_postgres_cost_storage")
class TestPostgresCostStorageGetLatest:
    """Test PostgresCostStorage get_latest_record operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_latest_record_returns_none_when_empty(self):
        """
        GIVEN: Empty PostgresCostStorage
        WHEN: Getting latest record
        THEN: Should return None
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Arrange - mock session with empty query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        mock_session = AsyncMock(return_value=None)  # async-mock-configured (mock for session context)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("mcp_server_langgraph.database.get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            storage = PostgresCostStorage("postgresql://test")

            # Act
            latest = await storage.get_latest_record()

            # Assert
            assert latest is None


@pytest.mark.xdist_group(name="test_postgres_cost_storage")
class TestPostgresCostStorageConfiguration:
    """Test PostgresCostStorage configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_requires_database_url(self):
        """
        GIVEN: PostgresCostStorage initialization
        WHEN: Created without database URL
        THEN: Should raise ValueError
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            PostgresCostStorage(None)  # type: ignore[arg-type]

    def test_accepts_valid_database_url(self):
        """
        GIVEN: Valid PostgreSQL URL
        WHEN: Creating PostgresCostStorage
        THEN: Should initialize successfully
        """
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        # Act
        storage = PostgresCostStorage("postgresql+asyncpg://user:pass@localhost/db")

        # Assert
        assert storage is not None
        assert storage._database_url == "postgresql+asyncpg://user:pass@localhost/db"
