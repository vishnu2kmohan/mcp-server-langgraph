"""
Integration tests for audit chain integrity.

TDD RED phase: These tests verify end-to-end hash chain integrity.

The integrity system should:
- Maintain HMAC-SHA256 hash chain across events
- Detect gaps in sequence numbers
- Detect tampered events
- Support verification over time ranges
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.audit.integrity import (
    ChainVerificationResult,
    HashChainBuilder,
    verify_chain,
)
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_chain_integrity")
class TestHashChainE2E:
    """End-to-end tests for hash chain integrity."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chain_maintains_integrity_across_multiple_events(self) -> None:
        """GIVEN multiple events WHEN chained THEN integrity verifiable."""
        builder = HashChainBuilder(secret="test-secret-key")

        events = []
        for i in range(10):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id=f"user:test-{i}", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read document",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        # Verify chain integrity
        result = verify_chain(events, secret="test-secret-key")

        assert result.valid is True
        assert result.events_verified == 10
        assert len(result.errors) == 0

    def test_chain_detects_sequence_gap(self) -> None:
        """GIVEN events with sequence gap WHEN verified THEN error detected."""
        builder = HashChainBuilder(secret="test-secret-key")

        events = []
        for i in range(5):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.AUTHENTICATION,
                event_type=AuditEventType.LOGIN_SUCCESS,
                actor=AuditActor(actor_id="user:test", actor_type="user"),
                resource_type="session",
                resource_id=f"sess-{i}",
                action="Login",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        # Remove middle event to create gap
        events_with_gap = events[:2] + events[3:]

        result = verify_chain(events_with_gap, secret="test-secret-key")

        assert result.valid is False
        assert any("sequence" in e.lower() or "gap" in e.lower() for e in result.errors)

    def test_chain_detects_tampered_event(self) -> None:
        """GIVEN tampered event WHEN verified THEN error detected."""
        builder = HashChainBuilder(secret="test-secret-key")

        events = []
        for i in range(5):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:test", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read document",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        # Tamper with middle event
        tampered_idx = 2
        tampered_event = events[tampered_idx].model_copy()
        # Modify the action (tampering)
        tampered_event.action = "TAMPERED ACTION"
        events[tampered_idx] = tampered_event

        result = verify_chain(events, secret="test-secret-key")

        assert result.valid is False
        assert any("hash" in e.lower() or "mismatch" in e.lower() for e in result.errors)

    def test_chain_detects_wrong_secret(self) -> None:
        """GIVEN events verified with wrong secret WHEN checked THEN error."""
        builder = HashChainBuilder(secret="correct-secret")

        events = []
        for i in range(3):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.SYSTEM,
                event_type=AuditEventType.CONFIG_CHANGE,
                actor=AuditActor(actor_id="user:admin", actor_type="user"),
                resource_type="config",
                resource_id=f"cfg-{i}",
                action="Update config",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        # Verify with wrong secret
        result = verify_chain(events, secret="wrong-secret")

        assert result.valid is False


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_chain_integrity")
class TestHashChainWithService:
    """Integration tests for hash chain with UnifiedAuditService."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_maintains_chain_across_log_events(self) -> None:
        """GIVEN audit service WHEN logging events THEN chain maintained."""
        mock_repo = AsyncMock(return_value=None)  # async-mock-configured
        mock_repo.create = AsyncMock(return_value=None)
        mock_repo.bulk_create = AsyncMock(return_value=None)
        mock_repo.get_events_in_range = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-integrity-secret",
        )

        # Log multiple events
        for i in range(5):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:test", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            await service.log_event(event)

        # Verify create was called with chained events
        assert mock_repo.create.call_count == 5

        # Check that events have sequence numbers and hashes
        logged_events = [call.args[0] for call in mock_repo.create.call_args_list]
        for i, event in enumerate(logged_events):
            assert event.sequence_number == i + 1
            assert event.event_hash is not None

    @pytest.mark.asyncio
    async def test_service_batch_maintains_chain(self) -> None:
        """GIVEN batch of events WHEN logged THEN chain maintained."""
        mock_repo = AsyncMock(return_value=None)  # async-mock-configured
        mock_repo.bulk_create = AsyncMock(return_value=None)

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-integrity-secret",
        )

        events = [
            UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:test", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            for i in range(10)
        ]

        await service.batch_log_events(events)

        # Verify bulk_create was called
        assert mock_repo.bulk_create.call_count == 1

        # Check that events have sequential numbers
        logged_events = mock_repo.bulk_create.call_args.args[0]
        for i, event in enumerate(logged_events):
            assert event.sequence_number == i + 1


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_chain_integrity")
class TestHashChainVerificationReport:
    """Tests for integrity verification reporting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verification_result_includes_details(self) -> None:
        """GIVEN verification WHEN completed THEN result has full details."""
        builder = HashChainBuilder(secret="test-secret")

        events = []
        for i in range(5):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:test", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        result = verify_chain(events, secret="test-secret")

        assert isinstance(result, ChainVerificationResult)
        assert result.valid is True
        assert result.events_verified == 5
        assert result.first_sequence == 1
        assert result.last_sequence == 5
        assert isinstance(result.errors, list)

    def test_empty_chain_verification(self) -> None:
        """GIVEN empty event list WHEN verified THEN valid result."""
        result = verify_chain([], secret="test-secret")

        assert result.valid is True
        assert result.events_verified == 0
