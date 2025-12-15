"""
Tests for audit integrity system (FedRAMP AU-9).

TDD RED phase: These tests define expected behavior for hash chain integrity.

The integrity system should:
- Compute HMAC-SHA256 hashes for each event
- Link events with previous_hash (chain)
- Assign sequential sequence_numbers
- Verify hash chain integrity
- Detect tampering
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_integrity")
class TestHashChainComputation:
    """Tests for hash chain computation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_compute_event_hash(self) -> None:
        """GIVEN audit event WHEN computing hash THEN returns HMAC-SHA256."""
        from mcp_server_langgraph.audit.integrity import compute_event_hash
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            event_id="test-event-id",
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User login",
            outcome="success",
            context=AuditContext(request_id="req-123"),
        )

        hash_value = compute_event_hash(event, secret="test-secret")

        # Hash should be 64 hex characters (256 bits)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_event_hash_deterministic(self) -> None:
        """GIVEN same event and secret WHEN computing hash THEN same result."""
        from mcp_server_langgraph.audit.integrity import compute_event_hash
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            event_id="fixed-id",
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:bob", actor_type="user"),
            resource_type="document",
            resource_id="doc-123",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-456"),
        )

        hash1 = compute_event_hash(event, secret="secret-key")
        hash2 = compute_event_hash(event, secret="secret-key")

        assert hash1 == hash2

    def test_compute_event_hash_includes_previous(self) -> None:
        """GIVEN event with previous_hash WHEN computing THEN includes in hash."""
        from mcp_server_langgraph.audit.integrity import compute_event_hash
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event1 = UnifiedAuditEvent(
            event_id="event-1",
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(actor_id="system", actor_type="system"),
            resource_type="config",
            resource_id="settings",
            action="Config update",
            outcome="success",
            context=AuditContext(request_id="req-1"),
            previous_hash=None,
        )

        event2 = UnifiedAuditEvent(
            event_id="event-1",
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(actor_id="system", actor_type="system"),
            resource_type="config",
            resource_id="settings",
            action="Config update",
            outcome="success",
            context=AuditContext(request_id="req-1"),
            previous_hash="abc123",
        )

        hash1 = compute_event_hash(event1, secret="key")
        hash2 = compute_event_hash(event2, secret="key")

        assert hash1 != hash2


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_integrity")
class TestHashChainBuilder:
    """Tests for building hash chains."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chain_first_event(self) -> None:
        """GIVEN first event WHEN chaining THEN previous_hash is None."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder

        builder = HashChainBuilder(secret="test-secret")

        assert builder.get_last_hash() is None
        assert builder.get_next_sequence() == 1

    def test_chain_adds_sequence_number(self) -> None:
        """GIVEN event WHEN adding to chain THEN sequence_number set."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        builder = HashChainBuilder(secret="test-secret")

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="Login",
            outcome="success",
            context=AuditContext(request_id="req-1"),
        )

        chained_event = builder.add_to_chain(event)

        assert chained_event.sequence_number == 1
        assert chained_event.event_hash is not None

    def test_chain_links_events(self) -> None:
        """GIVEN multiple events WHEN adding to chain THEN linked by hash."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        builder = HashChainBuilder(secret="test-secret")

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

        chained1 = builder.add_to_chain(event1)
        chained2 = builder.add_to_chain(event2)

        assert chained1.sequence_number == 1
        assert chained2.sequence_number == 2
        assert chained1.previous_hash is None
        assert chained2.previous_hash == chained1.event_hash


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_integrity")
class TestHashChainVerification:
    """Tests for verifying hash chain integrity."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verify_valid_chain(self) -> None:
        """GIVEN valid chain WHEN verifying THEN returns True."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder, verify_chain
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

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

        result = verify_chain(events, secret=secret)

        assert result.valid is True
        assert result.events_verified == 3
        assert result.errors == []

    def test_verify_detects_tampered_hash(self) -> None:
        """GIVEN tampered event WHEN verifying THEN detects tampering."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder, verify_chain
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

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

        # Tamper with an event's hash
        events[1] = events[1].model_copy(update={"event_hash": "tamperedvalue12345"})

        result = verify_chain(events, secret=secret)

        assert result.valid is False
        assert len(result.errors) > 0

    def test_verify_detects_sequence_gap(self) -> None:
        """GIVEN sequence gap WHEN verifying THEN detects gap."""
        from mcp_server_langgraph.audit.integrity import HashChainBuilder, verify_chain
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

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

        # Remove middle event (creates gap)
        events_with_gap = [events[0], events[2]]

        result = verify_chain(events_with_gap, secret=secret)

        assert result.valid is False
        assert any("sequence" in err.lower() for err in result.errors)
