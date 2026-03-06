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

    @pytest.mark.asyncio
    async def test_get_records_pagination_with_cost_sorting(self):
        """
        GIVEN: MemoryCostStorage with records having different costs
        WHEN: Paginating with sort_by=estimated_cost_usd
        THEN: Should correctly paginate through records sorted by cost
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        costs = [Decimal("0.10"), Decimal("0.05"), Decimal("0.30"), Decimal("0.15"), Decimal("0.20")]
        for i, cost in enumerate(costs):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id("alice"),
                session_id=f"session-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=cost,
            )
            await storage.store(usage)

        # Act - Get first page sorted by cost DESC
        page1, cursor1 = await storage.get_records(limit=2, sort_by="estimated_cost_usd", sort_order="desc")

        # Assert page 1 - highest costs first
        assert len(page1) == 2
        assert page1[0].estimated_cost_usd == Decimal("0.30")
        assert page1[1].estimated_cost_usd == Decimal("0.20")
        assert cursor1 is not None

        # Act - Get second page
        page2, cursor2 = await storage.get_records(cursor=cursor1, limit=2, sort_by="estimated_cost_usd", sort_order="desc")

        # Assert page 2 - next highest costs
        assert len(page2) == 2
        assert page2[0].estimated_cost_usd == Decimal("0.15")
        assert page2[1].estimated_cost_usd == Decimal("0.10")
        assert cursor2 is not None

        # Act - Get third page (last)
        page3, cursor3 = await storage.get_records(cursor=cursor2, limit=2, sort_by="estimated_cost_usd", sort_order="desc")

        # Assert page 3 - remaining record
        assert len(page3) == 1
        assert page3[0].estimated_cost_usd == Decimal("0.05")
        assert cursor3 is None  # No more pages


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


@pytest.mark.xdist_group(name="test_cost_storage")
class TestCostStorageConsistency:
    """
    Test that CostMetricsCollector and CostServiceImpl use the same storage backend.

    This addresses a critical bug where cost recording in chat.py used a different
    storage instance than the cost API endpoints, resulting in zero cost metrics.
    """

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        import os
        from mcp_server_langgraph.api.v1.cost import reset_cost_service
        from mcp_server_langgraph.monitoring.cost_storage_factory import reset_cost_storage_backend
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        # Use memory backend for tests (no DATABASE_URL required)
        os.environ["COST_STORAGE_BACKEND"] = "memory"

        reset_cost_service()
        reset_cost_storage_backend()
        _reset_cost_collector()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent test interference."""
        import os
        from mcp_server_langgraph.api.v1.cost import reset_cost_service
        from mcp_server_langgraph.monitoring.cost_storage_factory import reset_cost_storage_backend
        from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

        reset_cost_service()
        reset_cost_storage_backend()
        _reset_cost_collector()

        # Clean up environment
        if "COST_STORAGE_BACKEND" in os.environ:
            del os.environ["COST_STORAGE_BACKEND"]

        gc.collect()

    @pytest.mark.asyncio
    async def test_collector_and_api_use_same_storage_instance(self):
        """
        GIVEN: CostMetricsCollector and CostServiceImpl
        WHEN: Comparing their storage backends
        THEN: They should use the same storage instance

        This test verifies the fix for the bug where:
        - chat.py calls get_cost_collector().record_usage() -> writes to storage A
        - Cost API calls CostServiceImpl.get_summary() -> reads from storage B
        - Result: Cost page shows 0 because storage B is empty
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl
        from mcp_server_langgraph.monitoring.cost_storage_factory import get_cost_storage_backend
        from mcp_server_langgraph.monitoring.cost_tracker import get_cost_collector

        # Get the collector (used by chat.py)
        collector = get_cost_collector()

        # Get the service (used by cost API)
        service = CostServiceImpl()

        # Get the factory storage (should be the same for both)
        factory_storage = get_cost_storage_backend()

        # Assert - collector's internal storage should be the factory singleton
        assert collector._storage is factory_storage, (
            "CostMetricsCollector should use the shared storage from get_cost_storage_backend(), "
            "not create its own instance. This ensures cost recordings are visible to the API."
        )

        # Assert - service's storage should also be the factory singleton
        assert service.storage is factory_storage, (
            "CostServiceImpl should use the shared storage from get_cost_storage_backend()."
        )

    @pytest.mark.asyncio
    async def test_recorded_costs_visible_in_api(self):
        """
        GIVEN: Cost recorded via CostMetricsCollector
        WHEN: Querying via CostServiceImpl
        THEN: The recorded cost should be visible

        This is an end-to-end test of the fix.
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl
        from mcp_server_langgraph.monitoring.cost_tracker import get_cost_collector

        # Record a cost via collector (as chat.py does)
        collector = get_cost_collector()
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("test-user"),
            session_id="test-session",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Query via service (as cost API does)
        service = CostServiceImpl()
        summary = await service.get_summary()

        # Assert - the recorded cost should be visible
        assert summary["total_tokens"] == 1500, (
            "Cost recorded via get_cost_collector() should be visible via CostServiceImpl.get_summary(). "
            f"Expected 1500 tokens, got {summary['total_tokens']}."
        )
        assert summary["prompt_tokens"] == 1000
        assert summary["completion_tokens"] == 500


class TestMemoryCostStorageOrganizationalFiltering:
    """Test MemoryCostStorage organizational hierarchy filtering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_and_retrieve_with_organization_id(self) -> None:
        """
        GIVEN: MemoryCostStorage with records containing organization_id
        WHEN: Filtering records by organization_id
        THEN: Should return only matching records
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records with different organizations
        for org in ["organization:acme", "organization:contoso", "organization:acme"]:
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id("alice"),
                session_id="session-1",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
                organization_id=org,
            )
            await storage.store(usage)

        # Filter by organization
        records, _ = await storage.get_records(filters={"organization_id": "organization:acme"})

        assert len(records) == 2
        assert all(r.organization_id == "organization:acme" for r in records)

    @pytest.mark.asyncio
    async def test_store_and_retrieve_with_project_id(self) -> None:
        """
        GIVEN: MemoryCostStorage with records containing project_id
        WHEN: Filtering records by project_id
        THEN: Should return only matching records
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records with different projects
        for proj in ["project:backend", "project:frontend", "project:backend"]:
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id("bob"),
                session_id="session-2",
                model="claude-3",
                provider="anthropic",
                prompt_tokens=200,
                completion_tokens=100,
                estimated_cost_usd=Decimal("0.02"),
                project_id=proj,
            )
            await storage.store(usage)

        # Filter by project
        records, _ = await storage.get_records(filters={"project_id": "project:backend"})

        assert len(records) == 2
        assert all(r.project_id == "project:backend" for r in records)

    @pytest.mark.asyncio
    async def test_store_and_retrieve_with_team_id(self) -> None:
        """
        GIVEN: MemoryCostStorage with records containing team_id
        WHEN: Filtering records by team_id
        THEN: Should return only matching records
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records with different teams
        for team in ["team:platform", "team:ml", "team:platform"]:
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id("charlie"),
                session_id="session-3",
                model="gemini-pro",
                provider="google",
                prompt_tokens=300,
                completion_tokens=150,
                estimated_cost_usd=Decimal("0.03"),
                team_id=team,
            )
            await storage.store(usage)

        # Filter by team
        records, _ = await storage.get_records(filters={"team_id": "team:platform"})

        assert len(records) == 2
        assert all(r.team_id == "team:platform" for r in records)

    @pytest.mark.asyncio
    async def test_store_and_retrieve_with_combined_org_filters(self) -> None:
        """
        GIVEN: MemoryCostStorage with records containing full org hierarchy
        WHEN: Filtering records by multiple org fields
        THEN: Should return only records matching all filters
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store record with full hierarchy
        usage1 = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("alice"),
            session_id="session-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
        )
        await storage.store(usage1)

        # Store record with different project
        usage2 = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("alice"),
            session_id="session-2",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
            organization_id="organization:acme",
            project_id="project:frontend",
            team_id="team:platform",
        )
        await storage.store(usage2)

        # Filter by org + project
        records, _ = await storage.get_records(
            filters={
                "organization_id": "organization:acme",
                "project_id": "project:backend",
            }
        )

        assert len(records) == 1
        assert records[0].project_id == "project:backend"
        assert records[0].organization_id == "organization:acme"


@pytest.mark.cost
class TestMemoryCostStorageOrganizationalAggregation:
    """Tests for database-level organizational cost aggregation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_cost_by_organization_returns_aggregated_data(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for multiple organizations
        WHEN: Calling get_cost_by_organization
        THEN: Should return aggregated costs grouped by organization
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records for different organizations
        for i, org in enumerate(["organization:acme", "organization:acme", "organization:globex"]):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("10.00"),
                organization_id=org,
            )
            await storage.store(usage)

        # Get aggregated costs by organization
        org_costs = await storage.get_cost_by_organization()

        assert len(org_costs) == 2

        # Find acme result
        acme = next((c for c in org_costs if c.organization_id == "organization:acme"), None)
        assert acme is not None
        assert acme.request_count == 2
        assert acme.total_cost == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_get_cost_by_project_returns_aggregated_data(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for multiple projects
        WHEN: Calling get_cost_by_project
        THEN: Should return aggregated costs grouped by project
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records for different projects
        for i, proj in enumerate(["project:backend", "project:backend", "project:frontend"]):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("5.00"),
                organization_id="organization:acme",
                project_id=proj,
            )
            await storage.store(usage)

        # Get aggregated costs by project
        proj_costs = await storage.get_cost_by_project()

        assert len(proj_costs) == 2

        # Find backend result
        backend = next((c for c in proj_costs if c.project_id == "project:backend"), None)
        assert backend is not None
        assert backend.request_count == 2
        assert backend.total_cost == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_get_cost_by_team_returns_aggregated_data(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for multiple teams
        WHEN: Calling get_cost_by_team
        THEN: Should return aggregated costs grouped by team
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records for different teams
        for i, team in enumerate(["team:platform", "team:platform", "team:data"]):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("5.00"),
                organization_id="organization:acme",
                project_id="project:backend",
                team_id=team,
            )
            await storage.store(usage)

        # Get aggregated costs by team
        team_costs = await storage.get_cost_by_team()

        assert len(team_costs) == 2

        # Find platform result
        platform = next((c for c in team_costs if c.team_id == "team:platform"), None)
        assert platform is not None
        assert platform.request_count == 2
        assert platform.total_cost == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_get_cost_by_organization_with_date_filter(self) -> None:
        """
        GIVEN: MemoryCostStorage with records at different dates
        WHEN: Calling get_cost_by_organization with date filters
        THEN: Should return only records within date range
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        now = datetime.now(UTC)
        old_date = now - timedelta(days=30)

        # Store old record
        old_usage = TokenUsage(
            timestamp=old_date,
            user_id=get_user_id("alice"),
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("10.00"),
            organization_id="organization:acme",
        )
        await storage.store(old_usage)

        # Store recent record
        recent_usage = TokenUsage(
            timestamp=now,
            user_id=get_user_id("bob"),
            session_id="session-new",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("5.00"),
            organization_id="organization:acme",
        )
        await storage.store(recent_usage)

        # Get costs for last 7 days only
        start_date = now - timedelta(days=7)
        org_costs = await storage.get_cost_by_organization(start_date=start_date)

        assert len(org_costs) == 1
        assert org_costs[0].total_cost == Decimal("5.00")


class TestMemoryCostStorageDateRangeFiltering:
    """Test MemoryCostStorage.get_records() date range filtering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_records_with_start_date_filter(self) -> None:
        """
        GIVEN: MemoryCostStorage with records at different dates
        WHEN: Filtering records with start_date
        THEN: Should return only records on or after start_date
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Store old record (30 days ago)
        old_usage = TokenUsage(
            timestamp=now - timedelta(days=30),
            user_id=get_user_id("alice"),
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(old_usage)

        # Store recent record (1 day ago)
        recent_usage = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=get_user_id("bob"),
            session_id="session-recent",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(recent_usage)

        # Filter with start_date (last 7 days)
        start_date = now - timedelta(days=7)
        records, _ = await storage.get_records(filters={"start_date": start_date})

        assert len(records) == 1
        assert records[0].session_id == "session-recent"

    @pytest.mark.asyncio
    async def test_get_records_with_end_date_filter(self) -> None:
        """
        GIVEN: MemoryCostStorage with records at different dates
        WHEN: Filtering records with end_date
        THEN: Should return only records on or before end_date
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Store old record (30 days ago)
        old_usage = TokenUsage(
            timestamp=now - timedelta(days=30),
            user_id=get_user_id("alice"),
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(old_usage)

        # Store recent record (1 day ago)
        recent_usage = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=get_user_id("bob"),
            session_id="session-recent",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(recent_usage)

        # Filter with end_date (more than 7 days ago)
        end_date = now - timedelta(days=7)
        records, _ = await storage.get_records(filters={"end_date": end_date})

        assert len(records) == 1
        assert records[0].session_id == "session-old"

    @pytest.mark.asyncio
    async def test_get_records_with_date_range_filter(self) -> None:
        """
        GIVEN: MemoryCostStorage with records at different dates
        WHEN: Filtering records with start_date and end_date
        THEN: Should return only records within the date range
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Store record 30 days ago
        usage1 = TokenUsage(
            timestamp=now - timedelta(days=30),
            user_id=get_user_id("alice"),
            session_id="session-30d",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(usage1)

        # Store record 15 days ago
        usage2 = TokenUsage(
            timestamp=now - timedelta(days=15),
            user_id=get_user_id("bob"),
            session_id="session-15d",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(usage2)

        # Store record 5 days ago
        usage3 = TokenUsage(
            timestamp=now - timedelta(days=5),
            user_id=get_user_id("charlie"),
            session_id="session-5d",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(usage3)

        # Filter to 10-20 days ago
        start_date = now - timedelta(days=20)
        end_date = now - timedelta(days=10)
        records, _ = await storage.get_records(filters={"start_date": start_date, "end_date": end_date})

        assert len(records) == 1
        assert records[0].session_id == "session-15d"

    @pytest.mark.asyncio
    async def test_get_records_date_range_with_other_filters(self) -> None:
        """
        GIVEN: MemoryCostStorage with records at different dates and users
        WHEN: Filtering records with date range and user_id
        THEN: Should return only records matching all filters
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)
        alice_id = get_user_id("alice")
        bob_id = get_user_id("bob")

        # Store recent Alice record
        usage1 = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=alice_id,
            session_id="session-alice-recent",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(usage1)

        # Store recent Bob record
        usage2 = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=bob_id,
            session_id="session-bob-recent",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(usage2)

        # Store old Alice record
        usage3 = TokenUsage(
            timestamp=now - timedelta(days=30),
            user_id=alice_id,
            session_id="session-alice-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.10"),
        )
        await storage.store(usage3)

        # Filter for recent Alice only
        start_date = now - timedelta(days=7)
        records, _ = await storage.get_records(filters={"start_date": start_date, "user_id": alice_id})

        assert len(records) == 1
        assert records[0].session_id == "session-alice-recent"
        assert records[0].user_id == alice_id


# ==============================================================================
# Test Concurrent Operations for MemoryCostStorage
# ==============================================================================


class TestMemoryCostStorageConcurrency:
    """Test suite for concurrent operations on MemoryCostStorage.

    Validates that asyncio.Lock correctly protects shared state when
    multiple coroutines access the same MemoryCostStorage instance concurrently.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_store_records(self):
        """
        GIVEN multiple coroutines storing records concurrently
        WHEN all coroutines complete
        THEN all records should be stored without data loss
        """
        import asyncio
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        async def store_record(i: int):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"concurrent_user_{i}"),
                session_id=f"concurrent_session_{i}",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                prompt_tokens=100 + i,
                completion_tokens=50 + i,
                estimated_cost_usd=Decimal(f"0.0{i + 1}"),
            )
            await storage.store(usage)

        # Act - store 50 records concurrently
        tasks = [store_record(i) for i in range(50)]
        await asyncio.gather(*tasks)

        # Assert - all records stored
        assert storage.total_records == 50

        records, _ = await storage.get_records()
        assert len(records) == 50

    @pytest.mark.asyncio
    async def test_concurrent_read_and_write(self):
        """
        GIVEN concurrent reads and writes on storage
        WHEN operations complete
        THEN no data races occur
        """
        import asyncio
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Pre-populate with some records
        for i in range(10):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"initial_user_{i}"),
                session_id=f"initial_session_{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.10"),
            )
            await storage.store(usage)

        results = {"reads_ok": 0, "writes_ok": 0}

        async def write_record(i: int):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"new_user_{i}"),
                session_id=f"new_session_{i}",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                prompt_tokens=200,
                completion_tokens=100,
                estimated_cost_usd=Decimal("0.05"),
            )
            await storage.store(usage)
            results["writes_ok"] += 1

        async def read_records():
            records, _ = await storage.get_records()
            # Should not fail regardless of concurrent writes
            assert isinstance(records, list)
            results["reads_ok"] += 1

        # Act - interleave reads and writes
        tasks = []
        for i in range(20):
            tasks.append(write_record(i))
            tasks.append(read_records())

        await asyncio.gather(*tasks)

        # Assert - all operations completed
        assert results["writes_ok"] == 20
        assert results["reads_ok"] == 20

        # Total records: 10 initial + 20 new
        assert storage.total_records == 30

    @pytest.mark.asyncio
    async def test_concurrent_delete_while_reading(self):
        """
        GIVEN concurrent deletes and reads
        WHEN operations complete
        THEN no data races or exceptions occur
        """
        import asyncio
        from datetime import timedelta
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Pre-populate with old and new records
        for i in range(20):
            # Half old, half new
            is_old = i < 10
            usage = TokenUsage(
                timestamp=now - timedelta(days=100 if is_old else 1),
                user_id=get_user_id(f"delete_test_user_{i}"),
                session_id=f"delete_test_session_{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.10"),
            )
            await storage.store(usage)

        assert storage.total_records == 20

        results = {"reads_ok": 0, "deletes_done": False}

        async def read_records_loop():
            for _ in range(10):
                records, _ = await storage.get_records()
                assert isinstance(records, list)
                results["reads_ok"] += 1
                await asyncio.sleep(0.001)

        async def delete_old_records():
            cutoff = now - timedelta(days=50)
            await storage.delete_records_before(cutoff)
            results["deletes_done"] = True

        # Act
        await asyncio.gather(read_records_loop(), delete_old_records())

        # Assert
        assert results["reads_ok"] == 10
        assert results["deletes_done"] is True

        # Only 10 new records should remain
        assert storage.total_records == 10

    @pytest.mark.asyncio
    async def test_concurrent_get_cost_summary(self):
        """
        GIVEN concurrent get_cost_summary calls
        WHEN all calls complete
        THEN consistent results returned (no data races)
        """
        import asyncio
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Pre-populate with known data
        total_cost = Decimal("0")
        total_prompt = 0
        total_completion = 0

        for i in range(10):
            cost = Decimal(f"0.{i + 1:02d}")
            total_cost += cost
            total_prompt += 100
            total_completion += 50

            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"summary_user_{i}"),
                session_id=f"summary_session_{i}",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=cost,
            )
            await storage.store(usage)

        # Act - 15 concurrent summary calls
        tasks = [storage.get_cost_summary() for _ in range(15)]
        summaries = await asyncio.gather(*tasks)

        # Assert - all summaries consistent
        assert len(summaries) == 15
        for summary in summaries:
            assert summary.total_cost == total_cost
            assert summary.total_prompt_tokens == total_prompt
            assert summary.total_completion_tokens == total_completion
            assert summary.request_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_get_latest_record(self):
        """
        GIVEN concurrent get_latest_record calls while writing
        WHEN all calls complete
        THEN latest record reflects the most recent write
        """
        import asyncio
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        async def write_and_read(i: int):
            # Write
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"latest_user_{i}"),
                session_id=f"latest_session_{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100 + i,
                completion_tokens=50 + i,
                estimated_cost_usd=Decimal("0.10"),
            )
            await storage.store(usage)

            # Read latest
            latest = await storage.get_latest_record()
            assert latest is not None  # Should never be None after write

        # Act
        tasks = [write_and_read(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Assert - final latest is one of the records written
        final_latest = await storage.get_latest_record()
        assert final_latest is not None
        assert "latest_session_" in final_latest.session_id
