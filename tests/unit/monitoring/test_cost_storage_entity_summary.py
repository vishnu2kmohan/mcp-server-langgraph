"""
Unit tests for entity-specific get_cost_summary filtering.

TDD RED Phase: Tests for extending get_cost_summary to accept
organization_id, project_id, and team_id filters.

This enables the budget alert system's get_current_spend_for_entity()
to get accurate per-entity spend, not just total spend.

Reference: Plan - Phase 5: Enhanced Cost API Endpoints
"""

import gc
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
from tests.conftest import get_user_id

pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
    pytest.mark.cost,
]


@pytest.mark.xdist_group(name="test_cost_storage_entity_summary")
class TestGetCostSummaryOrganizationFilter:
    """Tests for get_cost_summary with organization_id filter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_cost_summary_filters_by_organization_id(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for multiple organizations
        WHEN: Calling get_cost_summary with organization_id filter
        THEN: Should return only cost for that organization
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records for organization:acme
        for i in range(3):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-acme-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("10.00"),
                organization_id="organization:acme",
            )
            await storage.store(usage)

        # Store records for organization:globex
        for i in range(2):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-globex-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=200,
                completion_tokens=100,
                estimated_cost_usd=Decimal("20.00"),
                organization_id="organization:globex",
            )
            await storage.store(usage)

        # Get cost summary filtered by organization:acme
        summary = await storage.get_cost_summary(organization_id="organization:acme")

        # Should only include acme's 3 records ($10 each = $30)
        assert summary.request_count == 3
        assert summary.total_cost == Decimal("30.00")
        assert summary.total_prompt_tokens == 300
        assert summary.total_completion_tokens == 150

    @pytest.mark.asyncio
    async def test_get_cost_summary_org_filter_with_date_range(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for organization at different dates
        WHEN: Calling get_cost_summary with organization_id and date filters
        THEN: Should return only cost for that org within date range
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Recent record for acme
        usage1 = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=get_user_id("alice"),
            session_id="session-recent",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("10.00"),
            organization_id="organization:acme",
        )
        await storage.store(usage1)

        # Old record for acme
        usage2 = TokenUsage(
            timestamp=now - timedelta(days=30),
            user_id=get_user_id("bob"),
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("15.00"),
            organization_id="organization:acme",
        )
        await storage.store(usage2)

        # Get cost summary for acme in last 7 days only
        start_date = now - timedelta(days=7)
        summary = await storage.get_cost_summary(
            organization_id="organization:acme",
            start_date=start_date,
        )

        # Should only include recent record
        assert summary.request_count == 1
        assert summary.total_cost == Decimal("10.00")


@pytest.mark.xdist_group(name="test_cost_storage_entity_summary")
class TestGetCostSummaryProjectFilter:
    """Tests for get_cost_summary with project_id filter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_cost_summary_filters_by_project_id(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for multiple projects
        WHEN: Calling get_cost_summary with project_id filter
        THEN: Should return only cost for that project
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records for project:backend
        for i in range(2):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-backend-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("5.00"),
                project_id="project:backend",
            )
            await storage.store(usage)

        # Store records for project:frontend
        for i in range(3):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-frontend-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=200,
                completion_tokens=100,
                estimated_cost_usd=Decimal("10.00"),
                project_id="project:frontend",
            )
            await storage.store(usage)

        # Get cost summary filtered by project:backend
        summary = await storage.get_cost_summary(project_id="project:backend")

        # Should only include backend's 2 records ($5 each = $10)
        assert summary.request_count == 2
        assert summary.total_cost == Decimal("10.00")


@pytest.mark.xdist_group(name="test_cost_storage_entity_summary")
class TestGetCostSummaryTeamFilter:
    """Tests for get_cost_summary with team_id filter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_cost_summary_filters_by_team_id(self) -> None:
        """
        GIVEN: MemoryCostStorage with records for multiple teams
        WHEN: Calling get_cost_summary with team_id filter
        THEN: Should return only cost for that team
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Store records for team:platform
        for i in range(4):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-platform-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("2.50"),
                team_id="team:platform",
            )
            await storage.store(usage)

        # Store records for team:ml
        for i in range(2):
            usage = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=get_user_id(f"user{i}"),
                session_id=f"session-ml-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=500,
                completion_tokens=250,
                estimated_cost_usd=Decimal("25.00"),
                team_id="team:ml",
            )
            await storage.store(usage)

        # Get cost summary filtered by team:platform
        summary = await storage.get_cost_summary(team_id="team:platform")

        # Should only include platform's 4 records ($2.50 each = $10)
        assert summary.request_count == 4
        assert summary.total_cost == Decimal("10.00")


@pytest.mark.xdist_group(name="test_cost_storage_entity_summary")
class TestGetCostSummaryCombinedFilters:
    """Tests for get_cost_summary with combined organizational filters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_cost_summary_org_and_project_filter(self) -> None:
        """
        GIVEN: MemoryCostStorage with hierarchical org structure
        WHEN: Calling get_cost_summary with org and project filters
        THEN: Should return only cost matching both filters
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()

        # Acme / backend
        usage1 = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("user1"),
            session_id="session-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("10.00"),
            organization_id="organization:acme",
            project_id="project:backend",
        )
        await storage.store(usage1)

        # Acme / frontend
        usage2 = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("user2"),
            session_id="session-2",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("15.00"),
            organization_id="organization:acme",
            project_id="project:frontend",
        )
        await storage.store(usage2)

        # Globex / backend
        usage3 = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id=get_user_id("user3"),
            session_id="session-3",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("20.00"),
            organization_id="organization:globex",
            project_id="project:backend",
        )
        await storage.store(usage3)

        # Filter by acme + backend
        summary = await storage.get_cost_summary(
            organization_id="organization:acme",
            project_id="project:backend",
        )

        # Should only include acme/backend ($10)
        assert summary.request_count == 1
        assert summary.total_cost == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_get_cost_summary_all_filters(self) -> None:
        """
        GIVEN: MemoryCostStorage with records using full hierarchy
        WHEN: Calling get_cost_summary with all filters
        THEN: Should return only cost matching all filters
        """
        from datetime import timedelta

        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Target record: acme/backend/platform/alice/recent
        usage1 = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=get_user_id("alice"),
            session_id="session-target",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("10.00"),
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
        )
        await storage.store(usage1)

        # Same org/project/team but different user
        usage2 = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=get_user_id("bob"),
            session_id="session-bob",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("15.00"),
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
        )
        await storage.store(usage2)

        # Different team
        usage3 = TokenUsage(
            timestamp=now - timedelta(days=1),
            user_id=get_user_id("alice"),
            session_id="session-ml",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("20.00"),
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:ml",
        )
        await storage.store(usage3)

        # Filter by acme/backend/platform/alice
        summary = await storage.get_cost_summary(
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
            user_id=get_user_id("alice"),
            start_date=now - timedelta(days=7),
        )

        # Should only include alice's platform record ($10)
        assert summary.request_count == 1
        assert summary.total_cost == Decimal("10.00")


@pytest.mark.xdist_group(name="test_cost_storage_entity_summary_postgres")
class TestPostgresCostStorageEntitySummary:
    """Tests for PostgresCostStorage.get_cost_summary with entity filters.

    These are interface tests - they verify the method signature accepts
    the new parameters. Full integration tests require a real database.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_cost_summary_accepts_organization_id_parameter(self) -> None:
        """
        GIVEN: PostgresCostStorage class
        WHEN: Checking get_cost_summary signature
        THEN: Should accept organization_id parameter
        """
        import inspect

        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        sig = inspect.signature(PostgresCostStorage.get_cost_summary)
        param_names = list(sig.parameters.keys())

        assert "organization_id" in param_names, "PostgresCostStorage.get_cost_summary should accept organization_id parameter"

    def test_get_cost_summary_accepts_project_id_parameter(self) -> None:
        """
        GIVEN: PostgresCostStorage class
        WHEN: Checking get_cost_summary signature
        THEN: Should accept project_id parameter
        """
        import inspect

        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        sig = inspect.signature(PostgresCostStorage.get_cost_summary)
        param_names = list(sig.parameters.keys())

        assert "project_id" in param_names, "PostgresCostStorage.get_cost_summary should accept project_id parameter"

    def test_get_cost_summary_accepts_team_id_parameter(self) -> None:
        """
        GIVEN: PostgresCostStorage class
        WHEN: Checking get_cost_summary signature
        THEN: Should accept team_id parameter
        """
        import inspect

        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        sig = inspect.signature(PostgresCostStorage.get_cost_summary)
        param_names = list(sig.parameters.keys())

        assert "team_id" in param_names, "PostgresCostStorage.get_cost_summary should accept team_id parameter"


@pytest.mark.xdist_group(name="test_cost_storage_entity_summary_protocol")
class TestCostStorageProtocolEntitySummary:
    """Tests for CostStorageBackend protocol entity filter parameters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_get_cost_summary_accepts_organization_id(self) -> None:
        """
        GIVEN: CostStorageBackend protocol
        WHEN: Checking get_cost_summary signature
        THEN: Should include organization_id parameter
        """
        import inspect

        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        # Get the protocol method
        method = getattr(CostStorageBackend, "get_cost_summary", None)
        assert method is not None, "Protocol should have get_cost_summary method"

        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())

        assert "organization_id" in param_names, (
            "CostStorageBackend.get_cost_summary should include organization_id in protocol"
        )

    def test_protocol_get_cost_summary_accepts_project_id(self) -> None:
        """
        GIVEN: CostStorageBackend protocol
        WHEN: Checking get_cost_summary signature
        THEN: Should include project_id parameter
        """
        import inspect

        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        method = getattr(CostStorageBackend, "get_cost_summary", None)
        assert method is not None

        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())

        assert "project_id" in param_names, "CostStorageBackend.get_cost_summary should include project_id in protocol"

    def test_protocol_get_cost_summary_accepts_team_id(self) -> None:
        """
        GIVEN: CostStorageBackend protocol
        WHEN: Checking get_cost_summary signature
        THEN: Should include team_id parameter
        """
        import inspect

        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        method = getattr(CostStorageBackend, "get_cost_summary", None)
        assert method is not None

        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())

        assert "team_id" in param_names, "CostStorageBackend.get_cost_summary should include team_id in protocol"
