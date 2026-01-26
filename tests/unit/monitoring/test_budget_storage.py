"""
Unit tests for BudgetStorage service.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify the BudgetStorage service for loading, saving, and managing
budget configurations from the database.
"""

import gc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
]


@pytest.mark.xdist_group(name="test_budget_storage")
class TestBudgetStorageProtocol:
    """Test suite for BudgetStorage protocol definition."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_storage_protocol_exists(self):
        """
        GIVEN the budget storage module
        WHEN importing BudgetStorageProtocol
        THEN it should be importable without error
        """
        from mcp_server_langgraph.monitoring.budget_storage import BudgetStorageProtocol

        assert BudgetStorageProtocol is not None

    def test_budget_storage_protocol_has_get_budget_method(self):
        """
        GIVEN the BudgetStorageProtocol
        WHEN checking its methods
        THEN it should define get_budget
        """
        from mcp_server_langgraph.monitoring.budget_storage import BudgetStorageProtocol

        # Protocol should have get_budget method
        assert hasattr(BudgetStorageProtocol, "get_budget")

    def test_budget_storage_protocol_has_save_budget_method(self):
        """
        GIVEN the BudgetStorageProtocol
        WHEN checking its methods
        THEN it should define save_budget
        """
        from mcp_server_langgraph.monitoring.budget_storage import BudgetStorageProtocol

        assert hasattr(BudgetStorageProtocol, "save_budget")

    def test_budget_storage_protocol_has_list_budgets_method(self):
        """
        GIVEN the BudgetStorageProtocol
        WHEN checking its methods
        THEN it should define list_budgets
        """
        from mcp_server_langgraph.monitoring.budget_storage import BudgetStorageProtocol

        assert hasattr(BudgetStorageProtocol, "list_budgets")


@pytest.mark.xdist_group(name="test_budget_storage")
class TestMemoryBudgetStorage:
    """Test suite for in-memory BudgetStorage implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_memory_budget_storage_exists(self):
        """
        GIVEN the budget storage module
        WHEN importing MemoryBudgetStorage
        THEN it should be importable without error
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage

        storage = MemoryBudgetStorage()
        assert storage is not None

    @pytest.mark.asyncio
    async def test_get_budget_returns_none_for_nonexistent(self):
        """
        GIVEN an empty MemoryBudgetStorage
        WHEN getting a budget that doesn't exist
        THEN it should return None
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage

        storage = MemoryBudgetStorage()

        result = await storage.get_budget(
            entity_type="organization",
            entity_id="organization:nonexistent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_get_budget(self):
        """
        GIVEN MemoryBudgetStorage
        WHEN saving a budget and then retrieving it
        THEN the budget should be returned correctly
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        storage = MemoryBudgetStorage()

        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.75,
            critical_threshold=0.95,
            name="ACME Budget",
        )

        await storage.save_budget(budget)

        result = await storage.get_budget(
            entity_type="organization",
            entity_id="organization:acme",
        )

        assert result is not None
        assert result.entity_type == "organization"
        assert result.entity_id == "organization:acme"
        assert result.monthly_limit_usd == Decimal("1000.00")
        assert result.warning_threshold == 0.75
        assert result.critical_threshold == 0.95
        assert result.name == "ACME Budget"

    @pytest.mark.asyncio
    async def test_update_existing_budget(self):
        """
        GIVEN MemoryBudgetStorage with an existing budget
        WHEN saving a budget with the same entity
        THEN the budget should be updated
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        storage = MemoryBudgetStorage()

        # Save initial budget
        budget1 = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("500.00"),
        )
        await storage.save_budget(budget1)

        # Update with new limit
        budget2 = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("750.00"),
        )
        await storage.save_budget(budget2)

        result = await storage.get_budget(
            entity_type="project",
            entity_id="project:backend",
        )

        assert result is not None
        assert result.monthly_limit_usd == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_list_budgets_returns_all(self):
        """
        GIVEN MemoryBudgetStorage with multiple budgets
        WHEN listing all budgets
        THEN all budgets should be returned
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        storage = MemoryBudgetStorage()

        # Save multiple budgets
        for i in range(5):
            budget = Budget(
                entity_type="user",
                entity_id=f"user:user{i}",
                monthly_limit_usd=Decimal(f"{100 + i * 10}.00"),
            )
            await storage.save_budget(budget)

        result = await storage.list_budgets()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_budgets_filter_by_entity_type(self):
        """
        GIVEN MemoryBudgetStorage with mixed entity types
        WHEN listing budgets filtered by entity_type
        THEN only matching budgets should be returned
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        storage = MemoryBudgetStorage()

        # Save budgets of different types
        await storage.save_budget(
            Budget(
                entity_type="organization",
                entity_id="organization:acme",
                monthly_limit_usd=Decimal("10000.00"),
            )
        )
        await storage.save_budget(
            Budget(
                entity_type="project",
                entity_id="project:backend",
                monthly_limit_usd=Decimal("2000.00"),
            )
        )
        await storage.save_budget(
            Budget(
                entity_type="project",
                entity_id="project:frontend",
                monthly_limit_usd=Decimal("1500.00"),
            )
        )
        await storage.save_budget(
            Budget(
                entity_type="user",
                entity_id="user:alice",
                monthly_limit_usd=Decimal("100.00"),
            )
        )

        # Filter by project
        result = await storage.list_budgets(entity_type="project")

        assert len(result) == 2
        assert all(b.entity_type == "project" for b in result)

    @pytest.mark.asyncio
    async def test_delete_budget(self):
        """
        GIVEN MemoryBudgetStorage with a budget
        WHEN deleting the budget
        THEN it should no longer be retrievable
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        storage = MemoryBudgetStorage()

        # Save a budget
        budget = Budget(
            entity_type="team",
            entity_id="team:platform",
            monthly_limit_usd=Decimal("500.00"),
        )
        await storage.save_budget(budget)

        # Verify it exists
        assert await storage.get_budget("team", "team:platform") is not None

        # Delete it
        deleted = await storage.delete_budget("team", "team:platform")
        assert deleted is True

        # Verify it's gone
        assert await storage.get_budget("team", "team:platform") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_budget_returns_false(self):
        """
        GIVEN MemoryBudgetStorage
        WHEN deleting a budget that doesn't exist
        THEN it should return False
        """
        from mcp_server_langgraph.monitoring.budget_storage import MemoryBudgetStorage

        storage = MemoryBudgetStorage()

        result = await storage.delete_budget("user", "user:nonexistent")

        assert result is False


@pytest.mark.xdist_group(name="test_budget_storage")
class TestGetBudgetStorageFunction:
    """Test suite for get_budget_storage() factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_budget_storage_function_exists(self):
        """
        GIVEN the budget storage module
        WHEN importing get_budget_storage
        THEN it should be importable without error
        """
        from mcp_server_langgraph.monitoring.budget_storage import get_budget_storage

        assert get_budget_storage is not None
        assert callable(get_budget_storage)

    def test_get_budget_storage_returns_storage_instance(self):
        """
        GIVEN the get_budget_storage function
        WHEN called
        THEN it should return a BudgetStorage instance
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            get_budget_storage,
        )

        storage = get_budget_storage()

        assert storage is not None
        # Should implement the protocol
        assert hasattr(storage, "get_budget")
        assert hasattr(storage, "save_budget")
        assert hasattr(storage, "list_budgets")

    def test_get_budget_storage_returns_singleton(self):
        """
        GIVEN the get_budget_storage function
        WHEN called multiple times
        THEN it should return the same instance
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            _reset_budget_storage,
            get_budget_storage,
        )

        _reset_budget_storage()  # Reset for test isolation

        storage1 = get_budget_storage()
        storage2 = get_budget_storage()

        assert storage1 is storage2

        _reset_budget_storage()  # Cleanup


@pytest.mark.xdist_group(name="test_postgres_budget_storage")
class TestPostgresBudgetStorage:
    """Test suite for PostgreSQL BudgetStorage implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_postgres_budget_storage_exists(self):
        """
        GIVEN the budget storage module
        WHEN importing PostgresBudgetStorage
        THEN it should be importable without error
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage

        assert PostgresBudgetStorage is not None

    def test_postgres_budget_storage_implements_protocol(self):
        """
        GIVEN PostgresBudgetStorage class
        WHEN checking its interface
        THEN it should have all required methods
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage

        # Should have all protocol methods
        assert hasattr(PostgresBudgetStorage, "get_budget")
        assert hasattr(PostgresBudgetStorage, "save_budget")
        assert hasattr(PostgresBudgetStorage, "list_budgets")
        assert hasattr(PostgresBudgetStorage, "delete_budget")

    @pytest.mark.asyncio
    async def test_postgres_budget_storage_get_budget_returns_none_when_not_found(self):
        """
        GIVEN PostgresBudgetStorage with mocked session
        WHEN getting a budget that doesn't exist
        THEN it should return None
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage

        # Mock the session maker
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        storage = PostgresBudgetStorage(session_maker=mock_session_maker)

        result = await storage.get_budget("organization", "organization:nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_postgres_budget_storage_get_budget_converts_record_to_budget(self):
        """
        GIVEN PostgresBudgetStorage with mocked session containing a record
        WHEN getting a budget
        THEN it should convert BudgetRecord to Budget
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage
        from mcp_server_langgraph.database.models import BudgetRecord

        # Create mock record
        mock_record = MagicMock(spec=BudgetRecord)
        mock_record.entity_type = "organization"
        mock_record.entity_id = "organization:acme"
        mock_record.monthly_limit_usd = Decimal("1000.00")
        mock_record.warning_threshold = 0.80
        mock_record.critical_threshold = 1.0
        mock_record.name = "ACME Budget"
        mock_record.description = "Monthly budget for ACME"
        mock_record.enabled = True

        # Mock the session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_record)

        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        storage = PostgresBudgetStorage(session_maker=mock_session_maker)

        result = await storage.get_budget("organization", "organization:acme")

        assert result is not None
        assert result.entity_type == "organization"
        assert result.entity_id == "organization:acme"
        assert result.monthly_limit_usd == Decimal("1000.00")
        assert result.warning_threshold == 0.80
        assert result.name == "ACME Budget"

    @pytest.mark.asyncio
    async def test_postgres_budget_storage_save_budget_creates_new_record(self):
        """
        GIVEN PostgresBudgetStorage with mocked session
        WHEN saving a new budget
        THEN it should call session.merge and commit
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        # Mock the session
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.merge = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.commit = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        storage = PostgresBudgetStorage(session_maker=mock_session_maker)

        budget = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("500.00"),
        )

        await storage.save_budget(budget)

        # Should have called merge and commit
        mock_session.merge.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_budget_storage_list_budgets_returns_all(self):
        """
        GIVEN PostgresBudgetStorage with mocked session
        WHEN listing all budgets
        THEN it should return all budgets as Budget objects
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage
        from mcp_server_langgraph.database.models import BudgetRecord

        # Create mock records
        mock_records = []
        for i in range(3):
            record = MagicMock(spec=BudgetRecord)
            record.entity_type = "user"
            record.entity_id = f"user:user{i}"
            record.monthly_limit_usd = Decimal(f"{100 + i * 10}.00")
            record.warning_threshold = 0.80
            record.critical_threshold = 1.0
            record.name = None
            record.description = None
            record.enabled = True
            mock_records.append(record)

        # Mock session result
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_records)))

        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        storage = PostgresBudgetStorage(session_maker=mock_session_maker)

        result = await storage.list_budgets()

        assert len(result) == 3
        assert all(b.entity_type == "user" for b in result)

    @pytest.mark.asyncio
    async def test_postgres_budget_storage_delete_budget_returns_true_when_deleted(self):
        """
        GIVEN PostgresBudgetStorage with existing budget
        WHEN deleting the budget
        THEN it should return True and call delete
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage
        from mcp_server_langgraph.database.models import BudgetRecord

        # Mock existing record
        mock_record = MagicMock(spec=BudgetRecord)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_record)

        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.commit = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        storage = PostgresBudgetStorage(session_maker=mock_session_maker)

        result = await storage.delete_budget("team", "team:platform")

        assert result is True
        mock_session.delete.assert_called_once_with(mock_record)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_budget_storage_delete_budget_returns_false_when_not_found(self):
        """
        GIVEN PostgresBudgetStorage
        WHEN deleting a budget that doesn't exist
        THEN it should return False
        """
        from mcp_server_langgraph.monitoring.budget_storage import PostgresBudgetStorage

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)

        storage = PostgresBudgetStorage(session_maker=mock_session_maker)

        result = await storage.delete_budget("user", "user:nonexistent")

        assert result is False


@pytest.mark.xdist_group(name="test_budget_storage_di")
class TestSetBudgetStorageFunction:
    """Test suite for set_budget_storage() dependency injection function."""

    def teardown_method(self) -> None:
        """Force GC and reset storage."""
        from mcp_server_langgraph.monitoring.budget_storage import _reset_budget_storage

        _reset_budget_storage()
        gc.collect()

    def test_set_budget_storage_function_exists(self):
        """
        GIVEN the budget storage module
        WHEN importing set_budget_storage
        THEN it should be importable without error
        """
        from mcp_server_langgraph.monitoring.budget_storage import set_budget_storage

        assert set_budget_storage is not None
        assert callable(set_budget_storage)

    def test_set_budget_storage_sets_singleton(self):
        """
        GIVEN a custom BudgetStorage implementation
        WHEN calling set_budget_storage
        THEN get_budget_storage should return that instance
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            get_budget_storage,
            set_budget_storage,
            _reset_budget_storage,
        )

        _reset_budget_storage()

        custom_storage = MemoryBudgetStorage()
        set_budget_storage(custom_storage)

        retrieved = get_budget_storage()
        assert retrieved is custom_storage

    def test_set_budget_storage_with_none_resets(self):
        """
        GIVEN a budget storage is set
        WHEN calling set_budget_storage with None
        THEN get_budget_storage should create a new instance
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            get_budget_storage,
            set_budget_storage,
            _reset_budget_storage,
        )

        _reset_budget_storage()

        custom_storage = MemoryBudgetStorage()
        set_budget_storage(custom_storage)
        set_budget_storage(None)

        # Should create a new default instance
        retrieved = get_budget_storage()
        assert retrieved is not custom_storage
        assert isinstance(retrieved, MemoryBudgetStorage)


@pytest.mark.xdist_group(name="test_budget_storage_app_factory")
class TestBudgetStorageAppFactoryIntegration:
    """Test suite for budget storage integration with app_factory."""

    def teardown_method(self) -> None:
        """Force GC and reset storage."""
        from mcp_server_langgraph.monitoring.budget_storage import set_budget_storage

        set_budget_storage(None)
        gc.collect()

    @pytest.mark.asyncio
    async def test_app_factory_initializes_budget_storage_in_production(self):
        """
        GIVEN a production environment with database configured
        WHEN app lifespan starts
        THEN PostgresBudgetStorage should be initialized
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            PostgresBudgetStorage,
            get_budget_storage,
            set_budget_storage,
        )

        # Reset to ensure clean state
        set_budget_storage(None)

        # Mock session_maker
        mock_session_maker = MagicMock()

        # Create PostgresBudgetStorage and set it
        postgres_storage = PostgresBudgetStorage(session_maker=mock_session_maker)
        set_budget_storage(postgres_storage)

        # Verify it's returned
        storage = get_budget_storage()
        assert isinstance(storage, PostgresBudgetStorage)

    @pytest.mark.asyncio
    async def test_budget_storage_reset_on_shutdown(self):
        """
        GIVEN budget storage is set
        WHEN app lifespan shuts down (set_budget_storage(None) called)
        THEN storage should be reset
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            get_budget_storage,
            set_budget_storage,
        )

        # Set custom storage
        custom_storage = MemoryBudgetStorage()
        set_budget_storage(custom_storage)

        # Simulate shutdown
        set_budget_storage(None)

        # Should create new instance
        storage = get_budget_storage()
        assert storage is not custom_storage
