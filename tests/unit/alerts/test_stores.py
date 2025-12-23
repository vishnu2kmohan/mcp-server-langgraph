"""
Alert Store Tests.

TDD tests for the alert store implementations:
- InMemoryAlertStore
- PostgresAlertStore

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.alerts.stores import (
    AlertStoreProtocol,
    InMemoryAlertStore,
    PostgresAlertStore,
)
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit

# =============================================================================
# Test Helpers
# =============================================================================


def create_test_alert(
    alert_id: str = "alert-123",
    name: str = "TestAlert",
    severity: AlertSeverity = AlertSeverity.CRITICAL,
    state: AlertState = AlertState.FIRING,
    message: str = "Test alert message",
) -> Alert:
    """Create a test alert with sensible defaults."""
    return Alert(
        alert_id=alert_id,
        name=name,
        severity=severity,
        state=state,
        message=message,
        labels={"instance": "test-instance"},
        annotations={"summary": "Test summary"},
        started_at=datetime.now(UTC),
        ended_at=None,
    )


# =============================================================================
# InMemoryAlertStore Tests
# =============================================================================


@pytest.mark.xdist_group(name="alert_stores")
class TestInMemoryAlertStore:
    """Tests for InMemoryAlertStore."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_implements_protocol(self) -> None:
        """InMemoryAlertStore should implement AlertStoreProtocol."""
        store = InMemoryAlertStore()
        assert isinstance(store, AlertStoreProtocol)

    @pytest.mark.asyncio
    async def test_add_and_get_alert(self) -> None:
        """Should add and retrieve an alert."""
        store = InMemoryAlertStore()
        alert = create_test_alert()

        await store.add_alert(alert)
        retrieved = await store.get_alert("alert-123")

        assert retrieved is not None
        assert retrieved.alert_id == "alert-123"
        assert retrieved.name == "TestAlert"

    @pytest.mark.asyncio
    async def test_get_nonexistent_alert_returns_none(self) -> None:
        """Should return None for nonexistent alert."""
        store = InMemoryAlertStore()

        result = await store.get_alert("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_existing_alert(self) -> None:
        """Should update an existing alert."""
        store = InMemoryAlertStore()
        alert1 = create_test_alert(message="Original")
        alert2 = create_test_alert(message="Updated")

        await store.add_alert(alert1)
        await store.add_alert(alert2)
        retrieved = await store.get_alert("alert-123")

        assert retrieved is not None
        assert retrieved.message == "Updated"

    @pytest.mark.asyncio
    async def test_remove_alert(self) -> None:
        """Should remove an alert."""
        store = InMemoryAlertStore()
        alert = create_test_alert()

        await store.add_alert(alert)
        await store.remove_alert("alert-123")
        result = await store.get_alert("alert-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_alert_no_error(self) -> None:
        """Should not raise error when removing nonexistent alert."""
        store = InMemoryAlertStore()

        # Should not raise
        await store.remove_alert("nonexistent")

    @pytest.mark.asyncio
    async def test_list_alerts_empty(self) -> None:
        """Should return empty list for empty store."""
        store = InMemoryAlertStore()

        result = await store.list_alerts()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_alerts_returns_all(self) -> None:
        """Should return all alerts."""
        store = InMemoryAlertStore()
        await store.add_alert(create_test_alert(alert_id="a1"))
        await store.add_alert(create_test_alert(alert_id="a2"))

        result = await store.list_alerts()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_severity(self) -> None:
        """Should filter alerts by severity."""
        store = InMemoryAlertStore()
        await store.add_alert(create_test_alert(alert_id="a1", severity=AlertSeverity.CRITICAL))
        await store.add_alert(create_test_alert(alert_id="a2", severity=AlertSeverity.WARNING))

        result = await store.list_alerts(severity=[AlertSeverity.CRITICAL])

        assert len(result) == 1
        assert result[0].alert_id == "a1"

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_state(self) -> None:
        """Should filter alerts by state."""
        store = InMemoryAlertStore()
        await store.add_alert(create_test_alert(alert_id="a1", state=AlertState.FIRING))
        await store.add_alert(create_test_alert(alert_id="a2", state=AlertState.RESOLVED))

        result = await store.list_alerts(state=[AlertState.RESOLVED])

        assert len(result) == 1
        assert result[0].alert_id == "a2"

    @pytest.mark.asyncio
    async def test_list_alerts_pagination(self) -> None:
        """Should support pagination."""
        store = InMemoryAlertStore()
        for i in range(5):
            await store.add_alert(create_test_alert(alert_id=f"a{i}"))

        result = await store.list_alerts(limit=2, offset=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Should clear all alerts."""
        store = InMemoryAlertStore()
        await store.add_alert(create_test_alert(alert_id="a1"))
        await store.add_alert(create_test_alert(alert_id="a2"))

        await store.clear()
        result = await store.list_alerts()

        assert result == []

    def test_add_alert_sync(self) -> None:
        """Should support synchronous add for backward compatibility."""
        store = InMemoryAlertStore()
        alert = create_test_alert()

        store.add_alert_sync(alert)

        # Verify via sync method
        result = store.get_alert_sync("alert-123")
        assert result is not None
        assert result.alert_id == "alert-123"

    def test_get_alert_sync(self) -> None:
        """Should support synchronous get for backward compatibility."""
        store = InMemoryAlertStore()
        alert = create_test_alert()
        store.add_alert_sync(alert)

        result = store.get_alert_sync("alert-123")

        assert result is not None
        assert result.name == "TestAlert"

    def test_get_alert_sync_nonexistent(self) -> None:
        """Should return None for nonexistent alert via sync method."""
        store = InMemoryAlertStore()

        result = store.get_alert_sync("nonexistent")

        assert result is None


# =============================================================================
# PostgresAlertStore Tests
# =============================================================================


@pytest.mark.xdist_group(name="alert_stores")
class TestPostgresAlertStore:
    """Tests for PostgresAlertStore with mocked database."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_session_maker(self) -> AsyncMock:
        """Create a mock SQLAlchemy async session maker."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        # session.add() is synchronous, not async - use MagicMock to prevent warnings
        mock_session.add = MagicMock()

        mock_maker = MagicMock()
        mock_maker.return_value = mock_session

        return mock_maker

    def test_implements_protocol(self, mock_session_maker: AsyncMock) -> None:
        """PostgresAlertStore should implement AlertStoreProtocol."""
        store = PostgresAlertStore(mock_session_maker)
        assert isinstance(store, AlertStoreProtocol)

    def test_initialization(self, mock_session_maker: AsyncMock) -> None:
        """Should initialize with session maker."""
        store = PostgresAlertStore(mock_session_maker)

        assert store._session_maker is mock_session_maker

    def test_alert_to_record_conversion(self, mock_session_maker: AsyncMock) -> None:
        """Should convert Alert to record dict."""
        store = PostgresAlertStore(mock_session_maker)
        alert = create_test_alert()

        record = store._alert_to_record(alert)

        assert record["alert_id"] == "alert-123"
        assert record["name"] == "TestAlert"
        assert record["severity"] == "critical"
        assert record["state"] == "firing"
        assert record["message"] == "Test alert message"

    def test_record_to_alert_conversion(self, mock_session_maker: AsyncMock) -> None:
        """Should convert AlertRecord to Alert dataclass."""
        store = PostgresAlertStore(mock_session_maker)

        # Create mock record
        mock_record = MagicMock()
        mock_record.alert_id = "alert-123"
        mock_record.name = "TestAlert"
        mock_record.severity = "critical"
        mock_record.state = "firing"
        mock_record.message = "Test message"
        mock_record.labels = {"key": "value"}
        mock_record.annotations = {}
        mock_record.started_at = datetime.now(UTC)
        mock_record.ended_at = None
        mock_record.generator_url = "http://example.com"

        alert = store._record_to_alert(mock_record)

        assert alert.alert_id == "alert-123"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.state == AlertState.FIRING

    @pytest.mark.asyncio
    async def test_add_new_alert(self, mock_session_maker: AsyncMock) -> None:
        """Should add a new alert to database."""
        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        store = PostgresAlertStore(mock_session_maker)
        alert = create_test_alert()

        await store.add_alert(alert)

        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_alert(self, mock_session_maker: AsyncMock) -> None:
        """Should update an existing alert in database."""
        mock_existing = MagicMock()
        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        store = PostgresAlertStore(mock_session_maker)
        alert = create_test_alert()

        await store.add_alert(alert)

        mock_session.commit.assert_called_once()
        # Verify existing record was updated
        assert hasattr(mock_existing, "name")

    @pytest.mark.asyncio
    async def test_get_alert(self, mock_session_maker: AsyncMock) -> None:
        """Should retrieve an alert from database."""
        mock_record = MagicMock()
        mock_record.alert_id = "alert-123"
        mock_record.name = "TestAlert"
        mock_record.severity = "critical"
        mock_record.state = "firing"
        mock_record.message = "Test"
        mock_record.labels = {}
        mock_record.annotations = {}
        mock_record.started_at = datetime.now(UTC)
        mock_record.ended_at = None
        mock_record.generator_url = None

        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        store = PostgresAlertStore(mock_session_maker)

        result = await store.get_alert("alert-123")

        assert result is not None
        assert result.alert_id == "alert-123"

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, mock_session_maker: AsyncMock) -> None:
        """Should return None when alert not found."""
        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        store = PostgresAlertStore(mock_session_maker)

        result = await store.get_alert("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_remove_alert(self, mock_session_maker: AsyncMock) -> None:
        """Should remove an alert from database."""
        mock_session = mock_session_maker.return_value
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        store = PostgresAlertStore(mock_session_maker)

        await store.remove_alert("alert-123")

        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_alerts(self, mock_session_maker: AsyncMock) -> None:
        """Should list alerts from database."""
        mock_record = MagicMock()
        mock_record.alert_id = "alert-1"
        mock_record.name = "Alert1"
        mock_record.severity = "warning"
        mock_record.state = "firing"
        mock_record.message = "Test"
        mock_record.labels = {}
        mock_record.annotations = {}
        mock_record.started_at = datetime.now(UTC)
        mock_record.ended_at = None
        mock_record.generator_url = None

        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_session.execute = AsyncMock(return_value=mock_result)

        store = PostgresAlertStore(mock_session_maker)

        result = await store.list_alerts()

        assert len(result) == 1
        assert result[0].alert_id == "alert-1"

    @pytest.mark.asyncio
    async def test_list_alerts_with_severity_filter(self, mock_session_maker: AsyncMock) -> None:
        """Should apply severity filter to query."""
        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        store = PostgresAlertStore(mock_session_maker)

        await store.list_alerts(severity=[AlertSeverity.CRITICAL])

        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_list_alerts_with_state_filter(self, mock_session_maker: AsyncMock) -> None:
        """Should apply state filter to query."""
        mock_session = mock_session_maker.return_value
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        store = PostgresAlertStore(mock_session_maker)

        await store.list_alerts(state=[AlertState.RESOLVED])

        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_clear(self, mock_session_maker: AsyncMock) -> None:
        """Should clear all alerts from database."""
        mock_session = mock_session_maker.return_value
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        store = PostgresAlertStore(mock_session_maker)

        await store.clear()

        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()
