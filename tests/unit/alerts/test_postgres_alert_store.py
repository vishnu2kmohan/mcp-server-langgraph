"""
PostgreSQL Alert Store Tests.

TDD tests for the PostgreSQL-backed alert store.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
from datetime import datetime, UTC

import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="postgres_alert_store")
class TestPostgresAlertStore:
    """Tests for PostgreSQL-backed alert store."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def sample_alert(self) -> Alert:
        """Create a sample alert."""
        return Alert(
            alert_id="alert-123",
            name="HighCPU",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="CPU usage above 90%",
            labels={"service": "api", "pod": "api-123"},
            annotations={"summary": "High CPU detected"},
            started_at=datetime.now(UTC),
            ended_at=None,
            generator_url="https://grafana.example.com/alert/123",
        )

    def test_alert_record_model_exists(self) -> None:
        """AlertRecord model should be importable."""
        from mcp_server_langgraph.alerts.models import AlertRecord

        assert AlertRecord is not None
        assert AlertRecord.__tablename__ == "alert_records"

    def test_alert_record_has_required_fields(self) -> None:
        """AlertRecord should have all required fields."""
        from mcp_server_langgraph.alerts.models import AlertRecord

        # Check column names exist
        columns = [c.name for c in AlertRecord.__table__.columns]
        required_columns = [
            "id",
            "alert_id",
            "name",
            "severity",
            "state",
            "message",
            "labels",
            "annotations",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
            "generator_url",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_alert_record_has_indexes(self) -> None:
        """AlertRecord should have proper indexes."""
        from mcp_server_langgraph.alerts.models import AlertRecord

        # Check index names
        index_names = [idx.name for idx in AlertRecord.__table__.indexes]
        assert "ix_alerts_severity_state" in index_names
        assert "ix_alerts_started_at_state" in index_names

    def test_postgres_alert_store_exists(self) -> None:
        """PostgresAlertStore class should be importable."""
        from mcp_server_langgraph.alerts.stores import PostgresAlertStore

        assert PostgresAlertStore is not None

    def test_postgres_alert_store_implements_protocol(self) -> None:
        """PostgresAlertStore should implement AlertStoreProtocol."""
        from mcp_server_langgraph.alerts.stores import (
            PostgresAlertStore,
        )

        # Check that PostgresAlertStore has required methods
        required_methods = ["add_alert", "get_alert", "remove_alert", "list_alerts", "clear"]
        for method in required_methods:
            assert hasattr(PostgresAlertStore, method), f"Missing method: {method}"


@pytest.mark.xdist_group(name="postgres_alert_store")
class TestAlertStoreProtocol:
    """Tests for AlertStoreProtocol interface."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_store_protocol_exists(self) -> None:
        """AlertStoreProtocol should be importable."""
        from mcp_server_langgraph.alerts.stores import AlertStoreProtocol

        assert AlertStoreProtocol is not None

    def test_in_memory_alert_store_implements_protocol(self) -> None:
        """InMemoryAlertStore should implement AlertStoreProtocol."""
        from mcp_server_langgraph.alerts.stores import (
            InMemoryAlertStore,
        )

        # Check that InMemoryAlertStore has required methods
        required_methods = ["add_alert", "get_alert", "remove_alert", "list_alerts", "clear"]
        for method in required_methods:
            assert hasattr(InMemoryAlertStore, method), f"Missing method: {method}"


@pytest.mark.xdist_group(name="postgres_alert_store")
class TestInMemoryAlertStore:
    """Tests for in-memory alert store (for testing/dev)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def sample_alert(self) -> Alert:
        """Create a sample alert."""
        return Alert(
            alert_id="alert-123",
            name="HighCPU",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="CPU usage above 90%",
            labels={"service": "api"},
            annotations={},
            started_at=datetime.now(UTC),
            ended_at=None,
        )

    @pytest.mark.asyncio
    async def test_add_and_get_alert(self, sample_alert: Alert) -> None:
        """Should add and retrieve an alert."""
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()
        await store.add_alert(sample_alert)

        retrieved = await store.get_alert(sample_alert.alert_id)
        assert retrieved is not None
        assert retrieved.alert_id == sample_alert.alert_id
        assert retrieved.name == sample_alert.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_alert(self) -> None:
        """Should return None for nonexistent alert."""
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()
        retrieved = await store.get_alert("nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_remove_alert(self, sample_alert: Alert) -> None:
        """Should remove an alert."""
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()
        await store.add_alert(sample_alert)
        await store.remove_alert(sample_alert.alert_id)

        retrieved = await store.get_alert(sample_alert.alert_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_alerts(self, sample_alert: Alert) -> None:
        """Should list all alerts."""
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()
        await store.add_alert(sample_alert)

        alerts = await store.list_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_id == sample_alert.alert_id

    @pytest.mark.asyncio
    async def test_clear_alerts(self, sample_alert: Alert) -> None:
        """Should clear all alerts."""
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()
        await store.add_alert(sample_alert)
        await store.clear()

        alerts = await store.list_alerts()
        assert len(alerts) == 0
