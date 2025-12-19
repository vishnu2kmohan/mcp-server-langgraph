"""
Tests for UnifiedAuditService.

TDD RED phase: These tests define expected behavior for the audit service.

The service should:
- Log events with automatic hash chain
- Support batch logging for performance
- Query by regulation tag
- Verify hash chain integrity
- Handle audit failures gracefully (FedRAMP AU-5)
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_service")
class TestUnifiedAuditServiceLogEvent:
    """Tests for log_event method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_log_event_persists_to_repository(self) -> None:
        """GIVEN audit event WHEN logging THEN event is persisted."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured
        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User login",
            outcome="success",
            context=AuditContext(request_id="req-123"),
        )

        await service.log_event(event)

        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_adds_hash_chain(self) -> None:
        """GIVEN audit event WHEN logging THEN hash chain is added."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        captured_event = None

        async def mock_create(event):
            nonlocal captured_event
            captured_event = event

        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.create = mock_create

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:bob", actor_type="user"),
            resource_type="document",
            resource_id="doc-123",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-456"),
        )

        await service.log_event(event)

        assert captured_event is not None
        assert captured_event.sequence_number == 1
        assert captured_event.event_hash is not None
        assert len(captured_event.event_hash) == 64  # HMAC-SHA256

    @pytest.mark.asyncio
    async def test_log_event_links_to_previous(self) -> None:
        """GIVEN multiple events WHEN logging THEN linked by hash."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        captured_events = []

        async def mock_create(event):
            captured_events.append(event)

        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.create = mock_create

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        event1 = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="Login",
            outcome="success",
            context=AuditContext(request_id="req-1"),
        )

        event2 = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="workflow",
            resource_id="wf-001",
            action="Read workflow",
            outcome="success",
            context=AuditContext(request_id="req-2"),
        )

        await service.log_event(event1)
        await service.log_event(event2)

        assert len(captured_events) == 2
        assert captured_events[0].sequence_number == 1
        assert captured_events[1].sequence_number == 2
        assert captured_events[0].previous_hash is None
        assert captured_events[1].previous_hash == captured_events[0].event_hash

    @pytest.mark.asyncio
    async def test_log_event_handles_repository_failure(self) -> None:
        """GIVEN repository failure WHEN logging THEN logs error but doesn't raise."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.create.side_effect = Exception("Database connection lost")

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(actor_id="system", actor_type="system"),
            resource_type="config",
            resource_id="settings",
            action="Update config",
            outcome="success",
            context=AuditContext(request_id="req-789"),
        )

        # Should not raise - FedRAMP AU-5 requires graceful handling
        with patch("mcp_server_langgraph.audit.service.logger") as mock_logger:
            await service.log_event(event)
            mock_logger.exception.assert_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_service")
class TestUnifiedAuditServiceBatchLog:
    """Tests for batch_log_events method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_batch_log_events_persists_all(self) -> None:
        """GIVEN multiple events WHEN batch logging THEN all persisted."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured
        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        events = [
            UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id=f"user:test-{i}", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action=f"Read document {i}",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            for i in range(5)
        ]

        await service.batch_log_events(events)

        mock_repo.bulk_create.assert_called_once()
        call_args = mock_repo.bulk_create.call_args[0][0]
        assert len(call_args) == 5

    @pytest.mark.asyncio
    async def test_batch_log_events_maintains_chain(self) -> None:
        """GIVEN batch events WHEN logging THEN hash chain is maintained."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        captured_events = None

        async def mock_bulk_create(events):
            nonlocal captured_events
            captured_events = events

        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.bulk_create = mock_bulk_create

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        events = [
            UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id=f"user:test-{i}", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action=f"Read document {i}",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            for i in range(3)
        ]

        await service.batch_log_events(events)

        assert captured_events is not None
        assert len(captured_events) == 3
        # Verify chain integrity
        assert captured_events[0].sequence_number == 1
        assert captured_events[1].sequence_number == 2
        assert captured_events[2].sequence_number == 3
        assert captured_events[0].previous_hash is None
        assert captured_events[1].previous_hash == captured_events[0].event_hash
        assert captured_events[2].previous_hash == captured_events[1].event_hash


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_service")
class TestUnifiedAuditServiceQuery:
    """Tests for query methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_regulation(self) -> None:
        """GIVEN events with regulation tags WHEN querying THEN filters correctly."""
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.query_by_regulation.return_value = []

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_regulation(Regulation.HIPAA)

        mock_repo.query_by_regulation.assert_called_once_with(Regulation.HIPAA, None, None)

    @pytest.mark.asyncio
    async def test_query_by_regulation_with_time_range(self) -> None:
        """GIVEN time range WHEN querying THEN passes time range to repo."""
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.query_by_regulation.return_value = []

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 31, tzinfo=UTC)

        await service.query_by_regulation(Regulation.GDPR, start_time=start, end_time=end)

        mock_repo.query_by_regulation.assert_called_once_with(Regulation.GDPR, start, end)

    @pytest.mark.asyncio
    async def test_query_by_category(self) -> None:
        """GIVEN category WHEN querying THEN filters by category."""
        from mcp_server_langgraph.audit.models import AuditEventCategory
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.query_by_category.return_value = []

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_category(AuditEventCategory.AI_OPERATION)

        mock_repo.query_by_category.assert_called_once_with(AuditEventCategory.AI_OPERATION, None, None)

    @pytest.mark.asyncio
    async def test_query_by_actor(self) -> None:
        """GIVEN actor_id WHEN querying THEN filters by actor."""
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.query_by_actor.return_value = []

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_actor("user:alice")

        mock_repo.query_by_actor.assert_called_once_with("user:alice", None, None)


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_service")
class TestUnifiedAuditServiceIntegrity:
    """Tests for integrity verification methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_integrity_valid_chain(self) -> None:
        """GIVEN valid chain WHEN verifying THEN returns success."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        # Build valid chain
        secret = "test-secret"
        builder = HashChainBuilder(secret=secret)

        events = []
        for i in range(3):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id=f"user:test-{i}", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action=f"Read document {i}",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            events.append(builder.add_to_chain(event))

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.get_events_in_range.return_value = events

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret=secret,
        )

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 31, tzinfo=UTC)

        result = await service.verify_integrity(start, end)

        assert result.valid is True
        assert result.events_verified == 3
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_verify_integrity_tampered_chain(self) -> None:
        """GIVEN tampered chain WHEN verifying THEN detects tampering."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        # Build valid chain
        secret = "test-secret"
        builder = HashChainBuilder(secret=secret)

        events = []
        for i in range(3):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id=f"user:test-{i}", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action=f"Read document {i}",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            events.append(builder.add_to_chain(event))

        # Tamper with an event
        events[1] = events[1].model_copy(update={"action": "TAMPERED ACTION"})

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.get_events_in_range.return_value = events

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret=secret,
        )

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 31, tzinfo=UTC)

        result = await service.verify_integrity(start, end)

        assert result.valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_get_integrity_report(self) -> None:
        """GIVEN time range WHEN getting report THEN returns full report."""
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.get_events_in_range.return_value = []
        mock_repo.get_event_count.return_value = 0

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 31, tzinfo=UTC)

        report = await service.get_integrity_report(start, end)

        assert "start_time" in report
        assert "end_time" in report
        assert "events_verified" in report
        assert "chain_valid" in report
        assert "verification_time" in report


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_service")
class TestUnifiedAuditServiceRetention:
    """Tests for retention-related methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_apply_retention_policy(self) -> None:
        """GIVEN retention policy WHEN applying THEN deletes expired events."""
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.delete_expired_by_regulation.return_value = 100

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        deleted = await service.apply_retention_policy(Regulation.EU_AI_ACT)

        assert deleted == 100
        mock_repo.delete_expired_by_regulation.assert_called_once_with(Regulation.EU_AI_ACT)

    @pytest.mark.asyncio
    async def test_get_retention_status(self) -> None:
        """GIVEN audit events WHEN checking status THEN returns per-regulation counts."""
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured (return_value/side_effect set below)
        mock_repo.get_retention_status.return_value = {
            "GDPR": {"total": 1000, "expiring_soon": 50},
            "HIPAA": {"total": 500, "expiring_soon": 10},
        }

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        status = await service.get_retention_status()

        assert "GDPR" in status
        assert "HIPAA" in status
        assert status["GDPR"]["total"] == 1000


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_service")
class TestUnifiedAuditServiceAlertDetector:
    """Tests for alert detector integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_log_event_calls_alert_detector(self) -> None:
        """GIVEN alert detector configured WHEN logging event THEN detector is called."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured
        mock_detector = MagicMock(spec=AuditAlertDetector)
        mock_detector.process_event_async = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
            alert_detector=mock_detector,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_FAILED,
            actor=AuditActor(actor_id="user:eve", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="Failed login attempt",
            outcome="failure",
            context=AuditContext(request_id="req-123", ip_address="192.168.1.100"),
        )

        await service.log_event(event)

        # Alert detector should be called with the chained event
        mock_detector.process_event_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_event_without_alert_detector_works(self) -> None:
        """GIVEN no alert detector WHEN logging event THEN no errors."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
            # No alert_detector provided
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User login",
            outcome="success",
            context=AuditContext(request_id="req-123"),
        )

        # Should not raise
        await service.log_event(event)

        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_handles_alert_detector_failure(self) -> None:
        """GIVEN alert detector failure WHEN logging event THEN logs warning but persists event."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = AsyncMock()  # async-mock-configured
        mock_detector = MagicMock(spec=AuditAlertDetector)
        mock_detector.process_event_async = AsyncMock(side_effect=Exception("Alert detection failed"))

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
            alert_detector=mock_detector,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_FAILED,
            actor=AuditActor(actor_id="user:eve", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="Failed login",
            outcome="failure",
            context=AuditContext(request_id="req-123"),
        )

        with patch("mcp_server_langgraph.audit.service.logger") as mock_logger:
            await service.log_event(event)
            mock_logger.warning.assert_called()

        # Event should still be persisted even if alert detection failed
        mock_repo.create.assert_called_once()
