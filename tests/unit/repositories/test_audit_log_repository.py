"""
Tests for Audit Log Repository

Following TDD principles - these tests define expected behavior.
Tests cover:
- Event logging with metadata
- Query with filtering (resource, actor, event type, time range)
- Get logs by resource
- Retention policy (delete older than N days)
- Model to dict conversion
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.repositories.audit_log import (
    AuditLogRepository,
    InMemoryAuditLogRepository,
    PostgresAuditLogRepository,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def in_memory_repo():
    """Create an in-memory audit log repository for testing."""
    return InMemoryAuditLogRepository()


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy async session."""
    session = AsyncMock(return_value=None)  # async-mock-configured
    session.add = MagicMock()
    session.flush = AsyncMock(return_value=None)  # async-mock-configured
    session.execute = AsyncMock(return_value=None)  # async-mock-configured
    return session


@pytest.fixture
def postgres_repo(mock_session):
    """Create PostgresAuditLogRepository with mock session."""
    return PostgresAuditLogRepository(session=mock_session)


# ==============================================================================
# InMemoryAuditLogRepository Tests
# ==============================================================================


class TestInMemoryAuditLogRepository:
    """Tests for InMemoryAuditLogRepository."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_log_event_stores_entry(self, in_memory_repo):
        """Test that log_event stores an audit entry."""
        # GIVEN: An empty repository
        assert len(in_memory_repo.logs) == 0

        # WHEN: Logging an event
        result = await in_memory_repo.log_event(
            event_type="connection.created",
            resource_type="connection",
            resource_id="conn-123",
            actor_id="user-456",
            action="create",
            details={"name": "GitHub MCP"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # THEN: Entry is stored with all fields
        assert len(in_memory_repo.logs) == 1
        assert result["event_type"] == "connection.created"
        assert result["resource_type"] == "connection"
        assert result["resource_id"] == "conn-123"
        assert result["actor_id"] == "user-456"
        assert result["action"] == "create"
        assert result["details"] == {"name": "GitHub MCP"}
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0"
        assert "id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_log_event_generates_unique_ids(self, in_memory_repo):
        """Test that each log entry gets a unique ID."""
        # WHEN: Logging multiple events
        result1 = await in_memory_repo.log_event(
            event_type="connection.created",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="user-1",
            action="create",
        )
        result2 = await in_memory_repo.log_event(
            event_type="connection.created",
            resource_type="connection",
            resource_id="conn-2",
            actor_id="user-1",
            action="create",
        )

        # THEN: Each entry has a unique ID
        assert result1["id"] != result2["id"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_returns_all_logs_when_no_filter(self, in_memory_repo):
        """Test that query returns all logs when no filter is applied."""
        # GIVEN: Multiple log entries
        for i in range(5):
            await in_memory_repo.log_event(
                event_type=f"event.{i}",
                resource_type="connection",
                resource_id=f"conn-{i}",
                actor_id="user-1",
                action="create",
            )

        # WHEN: Querying without filters
        logs, total = await in_memory_repo.query()

        # THEN: All logs are returned
        assert len(logs) == 5
        assert total == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_filters_by_resource_type(self, in_memory_repo):
        """Test filtering by resource_type."""
        # GIVEN: Logs with different resource types
        await in_memory_repo.log_event(
            event_type="created",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="user-1",
            action="create",
        )
        await in_memory_repo.log_event(
            event_type="created",
            resource_type="workflow",
            resource_id="wf-1",
            actor_id="user-1",
            action="create",
        )

        # WHEN: Filtering by resource_type
        logs, total = await in_memory_repo.query(resource_type="connection")

        # THEN: Only matching logs are returned
        assert len(logs) == 1
        assert logs[0]["resource_type"] == "connection"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_filters_by_resource_id(self, in_memory_repo):
        """Test filtering by resource_id."""
        # GIVEN: Logs with different resource IDs
        await in_memory_repo.log_event(
            event_type="updated",
            resource_type="connection",
            resource_id="conn-123",
            actor_id="user-1",
            action="update",
        )
        await in_memory_repo.log_event(
            event_type="updated",
            resource_type="connection",
            resource_id="conn-456",
            actor_id="user-1",
            action="update",
        )

        # WHEN: Filtering by resource_id
        logs, total = await in_memory_repo.query(resource_id="conn-123")

        # THEN: Only matching logs are returned
        assert len(logs) == 1
        assert logs[0]["resource_id"] == "conn-123"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_filters_by_actor_id(self, in_memory_repo):
        """Test filtering by actor_id."""
        # GIVEN: Logs from different actors
        await in_memory_repo.log_event(
            event_type="created",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="alice",
            action="create",
        )
        await in_memory_repo.log_event(
            event_type="created",
            resource_type="connection",
            resource_id="conn-2",
            actor_id="bob",
            action="create",
        )

        # WHEN: Filtering by actor_id
        logs, total = await in_memory_repo.query(actor_id="alice")

        # THEN: Only matching logs are returned
        assert len(logs) == 1
        assert logs[0]["actor_id"] == "alice"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_filters_by_event_type(self, in_memory_repo):
        """Test filtering by event_type."""
        # GIVEN: Logs with different event types
        await in_memory_repo.log_event(
            event_type="connection.created",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="user-1",
            action="create",
        )
        await in_memory_repo.log_event(
            event_type="connection.deleted",
            resource_type="connection",
            resource_id="conn-2",
            actor_id="user-1",
            action="delete",
        )

        # WHEN: Filtering by event_type
        logs, total = await in_memory_repo.query(event_type="connection.created")

        # THEN: Only matching logs are returned
        assert len(logs) == 1
        assert logs[0]["event_type"] == "connection.created"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_filters_by_time_range(self, in_memory_repo):
        """Test filtering by time range."""
        # GIVEN: Logs from different times (manually set timestamps)
        await in_memory_repo.log_event(
            event_type="old",
            resource_type="connection",
            resource_id="conn-old",
            actor_id="user-1",
            action="create",
        )
        # Modify the timestamp to be old
        in_memory_repo.logs[0]["timestamp"] = datetime.now(UTC) - timedelta(days=10)

        await in_memory_repo.log_event(
            event_type="new",
            resource_type="connection",
            resource_id="conn-new",
            actor_id="user-1",
            action="create",
        )

        # WHEN: Filtering by time range (last 5 days)
        start_time = datetime.now(UTC) - timedelta(days=5)
        logs, total = await in_memory_repo.query(start_time=start_time)

        # THEN: Only recent logs are returned
        assert len(logs) == 1
        assert logs[0]["resource_id"] == "conn-new"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_pagination_limit(self, in_memory_repo):
        """Test query pagination with limit."""
        # GIVEN: Multiple log entries
        for i in range(10):
            await in_memory_repo.log_event(
                event_type=f"event.{i}",
                resource_type="connection",
                resource_id=f"conn-{i}",
                actor_id="user-1",
                action="create",
            )

        # WHEN: Querying with limit
        logs, total = await in_memory_repo.query(limit=3)

        # THEN: Only limited number of logs returned
        assert len(logs) == 3
        assert total == 10  # Total still reflects all matching

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_pagination_offset(self, in_memory_repo):
        """Test query pagination with offset."""
        # GIVEN: Multiple log entries
        for i in range(10):
            await in_memory_repo.log_event(
                event_type=f"event.{i}",
                resource_type="connection",
                resource_id=f"conn-{i}",
                actor_id="user-1",
                action="create",
            )

        # WHEN: Querying with offset
        logs, total = await in_memory_repo.query(offset=5, limit=10)

        # THEN: Correct subset returned
        assert len(logs) == 5
        assert total == 10

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_orders_by_timestamp_desc(self, in_memory_repo):
        """Test that query results are ordered by timestamp descending."""
        # GIVEN: Logs with different timestamps
        await in_memory_repo.log_event(
            event_type="first",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="user-1",
            action="create",
        )
        in_memory_repo.logs[0]["timestamp"] = datetime.now(UTC) - timedelta(hours=2)

        await in_memory_repo.log_event(
            event_type="second",
            resource_type="connection",
            resource_id="conn-2",
            actor_id="user-1",
            action="create",
        )
        in_memory_repo.logs[1]["timestamp"] = datetime.now(UTC) - timedelta(hours=1)

        await in_memory_repo.log_event(
            event_type="third",
            resource_type="connection",
            resource_id="conn-3",
            actor_id="user-1",
            action="create",
        )

        # WHEN: Querying
        logs, _ = await in_memory_repo.query()

        # THEN: Results ordered by timestamp descending (newest first)
        assert logs[0]["event_type"] == "third"
        assert logs[1]["event_type"] == "second"
        assert logs[2]["event_type"] == "first"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_by_resource_returns_matching_logs(self, in_memory_repo):
        """Test get_by_resource returns logs for specific resource."""
        # GIVEN: Logs for different resources
        await in_memory_repo.log_event(
            event_type="created",
            resource_type="connection",
            resource_id="conn-123",
            actor_id="user-1",
            action="create",
        )
        await in_memory_repo.log_event(
            event_type="updated",
            resource_type="connection",
            resource_id="conn-123",
            actor_id="user-1",
            action="update",
        )
        await in_memory_repo.log_event(
            event_type="created",
            resource_type="connection",
            resource_id="conn-456",
            actor_id="user-1",
            action="create",
        )

        # WHEN: Getting logs for specific resource
        logs = await in_memory_repo.get_by_resource(
            resource_type="connection",
            resource_id="conn-123",
        )

        # THEN: Only logs for that resource are returned
        assert len(logs) == 2
        for log in logs:
            assert log["resource_id"] == "conn-123"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_by_resource_respects_limit(self, in_memory_repo):
        """Test get_by_resource respects limit parameter."""
        # GIVEN: Multiple logs for same resource
        for i in range(10):
            await in_memory_repo.log_event(
                event_type=f"event.{i}",
                resource_type="connection",
                resource_id="conn-123",
                actor_id="user-1",
                action="update",
            )

        # WHEN: Getting with limit
        logs = await in_memory_repo.get_by_resource(
            resource_type="connection",
            resource_id="conn-123",
            limit=5,
        )

        # THEN: Only limited number returned
        assert len(logs) == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_older_than_removes_old_logs(self, in_memory_repo):
        """Test delete_older_than removes logs older than specified days."""
        # GIVEN: Logs from different times
        await in_memory_repo.log_event(
            event_type="old",
            resource_type="connection",
            resource_id="conn-old",
            actor_id="user-1",
            action="create",
        )
        in_memory_repo.logs[0]["timestamp"] = datetime.now(UTC) - timedelta(days=100)

        await in_memory_repo.log_event(
            event_type="recent",
            resource_type="connection",
            resource_id="conn-new",
            actor_id="user-1",
            action="create",
        )

        # WHEN: Deleting logs older than 30 days
        deleted_count = await in_memory_repo.delete_older_than(days=30)

        # THEN: Old logs are removed
        assert deleted_count == 1
        assert len(in_memory_repo.logs) == 1
        assert in_memory_repo.logs[0]["resource_id"] == "conn-new"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_older_than_returns_zero_when_no_old_logs(self, in_memory_repo):
        """Test delete_older_than returns 0 when no old logs exist."""
        # GIVEN: Only recent logs
        await in_memory_repo.log_event(
            event_type="recent",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="user-1",
            action="create",
        )

        # WHEN: Deleting logs older than 30 days
        deleted_count = await in_memory_repo.delete_older_than(days=30)

        # THEN: No logs deleted
        assert deleted_count == 0
        assert len(in_memory_repo.logs) == 1


# ==============================================================================
# PostgresAuditLogRepository Tests
# ==============================================================================


class TestPostgresAuditLogRepository:
    """Tests for PostgresAuditLogRepository with mocked session."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_log_event_adds_to_session(self, postgres_repo, mock_session):
        """Test that log_event adds model to session."""

        # WHEN: Logging an event
        # Create a simple stub that properly returns string when str() is called
        class MockUUID:
            hex = "abc123"

            def __str__(self) -> str:
                return "abc123"

        with patch("mcp_server_langgraph.repositories.audit_log.uuid4") as mock_uuid:
            mock_uuid.return_value = MockUUID()

            result = await postgres_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-123",
                actor_id="user-456",
                action="create",
                details={"name": "GitHub MCP"},
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        # THEN: Model was added to session
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # AND: Result contains expected fields
        assert result["event_type"] == "connection.created"
        assert result["resource_type"] == "connection"
        assert result["resource_id"] == "conn-123"
        assert result["actor_id"] == "user-456"
        assert result["action"] == "create"
        assert result["details"] == {"name": "GitHub MCP"}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_log_event_sets_timestamp(self, postgres_repo, mock_session):
        """Test that log_event sets current timestamp."""
        # WHEN: Logging an event
        before = datetime.now(UTC)
        result = await postgres_repo.log_event(
            event_type="test",
            resource_type="connection",
            resource_id="conn-1",
            actor_id="user-1",
            action="create",
        )
        after = datetime.now(UTC)

        # THEN: Timestamp is within expected range
        assert before <= result["timestamp"] <= after

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_executes_select_statement(self, postgres_repo, mock_session):
        """Test that query executes select with filters."""
        # GIVEN: Mock execute returns empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN: Querying with filters
        logs, total = await postgres_repo.query(
            resource_type="connection",
            resource_id="conn-123",
            event_type="connection.created",
        )

        # THEN: Execute was called (at least twice for count and results)
        assert mock_session.execute.call_count >= 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_by_resource_executes_filtered_query(self, postgres_repo, mock_session):
        """Test that get_by_resource executes filtered query."""
        # GIVEN: Mock execute returns empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN: Getting by resource
        logs = await postgres_repo.get_by_resource(
            resource_type="connection",
            resource_id="conn-123",
        )

        # THEN: Execute was called
        mock_session.execute.assert_called_once()
        assert logs == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_older_than_executes_delete_statement(self, postgres_repo, mock_session):
        """Test that delete_older_than executes delete statement."""
        # GIVEN: Mock execute returns rowcount
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # WHEN: Deleting old logs
        deleted = await postgres_repo.delete_older_than(days=30)

        # THEN: Execute and flush were called
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()
        assert deleted == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_model_to_dict_converts_all_fields(self, postgres_repo):
        """Test that _model_to_dict converts all model fields."""
        # GIVEN: A mock model (using log_id as per UnifiedAuditLog model)
        mock_model = MagicMock()
        mock_model.log_id = "log-123"
        mock_model.event_type = "connection.created"
        mock_model.resource_type = "connection"
        mock_model.resource_id = "conn-456"
        mock_model.actor_id = "user-789"
        mock_model.action = "create"
        mock_model.details = {"key": "value"}
        mock_model.ip_address = "10.0.0.1"
        mock_model.user_agent = "Test Agent"
        mock_model.timestamp = datetime.now(UTC)

        # WHEN: Converting to dict
        result = postgres_repo._model_to_dict(mock_model)

        # THEN: All fields are present
        assert result["id"] == "log-123"
        assert result["event_type"] == "connection.created"
        assert result["resource_type"] == "connection"
        assert result["resource_id"] == "conn-456"
        assert result["actor_id"] == "user-789"
        assert result["action"] == "create"
        assert result["details"] == {"key": "value"}
        assert result["ip_address"] == "10.0.0.1"
        assert result["user_agent"] == "Test Agent"
        assert result["timestamp"] == mock_model.timestamp

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_model_to_dict_handles_null_details(self, postgres_repo):
        """Test that _model_to_dict handles None details."""
        # GIVEN: A model with None details (using log_id as per UnifiedAuditLog model)
        mock_model = MagicMock()
        mock_model.log_id = "log-123"
        mock_model.event_type = "test"
        mock_model.resource_type = "connection"
        mock_model.resource_id = "conn-1"
        mock_model.actor_id = "user-1"
        mock_model.action = "create"
        mock_model.details = None
        mock_model.ip_address = None
        mock_model.user_agent = None
        mock_model.timestamp = datetime.now(UTC)

        # WHEN: Converting to dict
        result = postgres_repo._model_to_dict(mock_model)

        # THEN: Details defaults to empty dict
        assert result["details"] == {}
        assert result["ip_address"] is None
        assert result["user_agent"] is None


# ==============================================================================
# Abstract Base Class Tests
# ==============================================================================


class TestAuditLogRepositoryAbstract:
    """Test the abstract base class contract."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_cannot_instantiate_abstract_class(self):
        """Test that AuditLogRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AuditLogRepository()

    @pytest.mark.unit
    def test_in_memory_implements_interface(self, in_memory_repo):
        """Test that InMemoryAuditLogRepository implements the interface."""
        assert isinstance(in_memory_repo, AuditLogRepository)

    @pytest.mark.unit
    def test_postgres_implements_interface(self, postgres_repo):
        """Test that PostgresAuditLogRepository implements the interface."""
        assert isinstance(postgres_repo, AuditLogRepository)
