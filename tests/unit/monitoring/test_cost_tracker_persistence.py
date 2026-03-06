"""
Unit tests for CostMetricsCollector database persistence.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify that organizational fields (organization_id, project_id, team_id)
are properly persisted to PostgreSQL when recording token usage.

Reference: Plan - Phase 6 database persistence verification
"""

import gc
import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
]


@pytest.fixture
def reset_singletons():
    """Reset cost storage singleton before/after tests."""
    from mcp_server_langgraph.monitoring.cost_storage_factory import (
        reset_cost_storage_backend,
    )
    from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

    # Use memory backend for unit tests
    original_backend = os.environ.get("COST_STORAGE_BACKEND")
    os.environ["COST_STORAGE_BACKEND"] = "memory"

    reset_cost_storage_backend()
    _reset_cost_collector()

    yield

    # Restore
    if original_backend:
        os.environ["COST_STORAGE_BACKEND"] = original_backend
    else:
        os.environ.pop("COST_STORAGE_BACKEND", None)

    reset_cost_storage_backend()
    _reset_cost_collector()


class TestCostMetricsCollectorPersistenceOrgFields:
    """Tests for organizational field persistence in _persist_to_database."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_persist_to_database_includes_organization_id(self, reset_singletons):
        """
        GIVEN: TokenUsage record with organization_id
        WHEN: _persist_to_database is called
        THEN: TokenUsageRecord should be created with organization_id
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        # Arrange
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.015"),
            organization_id="organization:acme",
        )

        # Create collector with database_url to enable persistence
        collector = CostMetricsCollector(database_url="postgresql://fake:5432/test")

        # Mock the database session - configure with side_effect for add
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.add = MagicMock()

        captured_record = None

        def capture_add(record):
            nonlocal captured_record
            captured_record = record

        mock_session.add.side_effect = capture_add

        # Mock the async context manager with explicit return values
        mock_context = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.database.get_async_session",
            return_value=mock_context,
        ):
            # Act
            await collector._persist_to_database(usage)

        # Assert
        assert captured_record is not None, "TokenUsageRecord should be created"
        assert captured_record.organization_id == "organization:acme", "organization_id should be persisted"

    @pytest.mark.asyncio
    async def test_persist_to_database_includes_project_id(self, reset_singletons):
        """
        GIVEN: TokenUsage record with project_id
        WHEN: _persist_to_database is called
        THEN: TokenUsageRecord should be created with project_id
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        # Arrange
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.015"),
            project_id="project:backend",
        )

        collector = CostMetricsCollector(database_url="postgresql://fake:5432/test")

        # Mock the database session - configure with side_effect for add
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.add = MagicMock()

        captured_record = None

        def capture_add(record):
            nonlocal captured_record
            captured_record = record

        mock_session.add.side_effect = capture_add

        # Mock the async context manager with explicit return values
        mock_context = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.database.get_async_session",
            return_value=mock_context,
        ):
            # Act
            await collector._persist_to_database(usage)

        # Assert
        assert captured_record is not None, "TokenUsageRecord should be created"
        assert captured_record.project_id == "project:backend", "project_id should be persisted"

    @pytest.mark.asyncio
    async def test_persist_to_database_includes_team_id(self, reset_singletons):
        """
        GIVEN: TokenUsage record with team_id
        WHEN: _persist_to_database is called
        THEN: TokenUsageRecord should be created with team_id
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        # Arrange
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.015"),
            team_id="team:platform",
        )

        collector = CostMetricsCollector(database_url="postgresql://fake:5432/test")

        # Mock the database session - configure with side_effect for add
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.add = MagicMock()

        captured_record = None

        def capture_add(record):
            nonlocal captured_record
            captured_record = record

        mock_session.add.side_effect = capture_add

        # Mock the async context manager with explicit return values
        mock_context = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.database.get_async_session",
            return_value=mock_context,
        ):
            # Act
            await collector._persist_to_database(usage)

        # Assert
        assert captured_record is not None, "TokenUsageRecord should be created"
        assert captured_record.team_id == "team:platform", "team_id should be persisted"

    @pytest.mark.asyncio
    async def test_persist_to_database_includes_all_org_fields(self, reset_singletons):
        """
        GIVEN: TokenUsage record with all organizational fields
        WHEN: _persist_to_database is called
        THEN: TokenUsageRecord should be created with all org fields
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        # Arrange
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.015"),
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
        )

        collector = CostMetricsCollector(database_url="postgresql://fake:5432/test")

        # Mock the database session - configure with side_effect for add
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.add = MagicMock()

        captured_record = None

        def capture_add(record):
            nonlocal captured_record
            captured_record = record

        mock_session.add.side_effect = capture_add

        # Mock the async context manager with explicit return values
        mock_context = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.database.get_async_session",
            return_value=mock_context,
        ):
            # Act
            await collector._persist_to_database(usage)

        # Assert
        assert captured_record is not None, "TokenUsageRecord should be created"
        assert captured_record.organization_id == "organization:acme"
        assert captured_record.project_id == "project:backend"
        assert captured_record.team_id == "team:platform"

    @pytest.mark.asyncio
    async def test_persist_to_database_handles_null_org_fields(self, reset_singletons):
        """
        GIVEN: TokenUsage record without organizational fields
        WHEN: _persist_to_database is called
        THEN: TokenUsageRecord should be created with null org fields
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        # Arrange
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.015"),
            # No organizational fields set
        )

        collector = CostMetricsCollector(database_url="postgresql://fake:5432/test")

        # Mock the database session - configure with side_effect for add
        mock_session = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_session.add = MagicMock()

        captured_record = None

        def capture_add(record):
            nonlocal captured_record
            captured_record = record

        mock_session.add.side_effect = capture_add

        # Mock the async context manager with explicit return values
        mock_context = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.database.get_async_session",
            return_value=mock_context,
        ):
            # Act
            await collector._persist_to_database(usage)

        # Assert
        assert captured_record is not None, "TokenUsageRecord should be created"
        assert captured_record.organization_id is None
        assert captured_record.project_id is None
        assert captured_record.team_id is None
