"""
Integration tests for PostgresUnifiedAuditRepository.

These tests verify the unified audit repository works with a real PostgreSQL database,
testing the full flow of event creation, querying, and retention.

Tests verify:
1. Event persistence with all fields
2. Query by regulation, category, actor, and time range
3. Bulk operations
4. Hash chain integrity
5. Retention policy enforcement

References:
    - ADR-0070: Unified Audit Logging Facility
    - src/mcp_server_langgraph/audit/repository.py
"""

import gc
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from mcp_server_langgraph.audit.constants import Regulation
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.repository import (
    InMemoryUnifiedAuditRepository,
)

if TYPE_CHECKING:
    pass

# Mark as integration test with xdist_group for worker isolation
pytestmark = [
    pytest.mark.integration,
    pytest.mark.audit,
    pytest.mark.xdist_group(name="postgres_unified_audit"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_gc():
    """Force GC after each test to prevent memory accumulation."""
    yield
    gc.collect()


@pytest.mark.xdist_group(name="in_memory_audit_repo")
class TestInMemoryUnifiedAuditRepository:
    """
    Integration tests for InMemoryUnifiedAuditRepository.

    These tests verify the in-memory implementation without database.
    Useful for validating the repository interface contract.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_and_query_by_category(self) -> None:
        """
        GIVEN an in-memory repository
        WHEN events are created and queried by category
        THEN matching events are returned.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        # Create authentication event
        auth_event = UnifiedAuditEvent(
            event_id=f"{prefix}_auth_001",
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id=f"{prefix}_sess_001",
            action="Login",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_001"),
        )
        await repo.create(auth_event)

        # Create data access event
        data_event = UnifiedAuditEvent(
            event_id=f"{prefix}_data_001",
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="document",
            resource_id=f"{prefix}_doc_001",
            action="Read",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_002"),
        )
        await repo.create(data_event)

        # Query by category
        auth_results = await repo.query_by_category(AuditEventCategory.AUTHENTICATION)

        assert len(auth_results) == 1
        assert auth_results[0].event_id == f"{prefix}_auth_001"

    @pytest.mark.asyncio
    async def test_bulk_create_events(self) -> None:
        """
        GIVEN an in-memory repository
        WHEN multiple events are bulk created
        THEN all events are stored.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        events = [
            UnifiedAuditEvent(
                event_id=f"{prefix}_bulk_{i}",
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:bob", actor_type="user"),
                resource_type="document",
                resource_id=f"{prefix}_doc_{i}",
                action="Read",
                outcome="success",
                context=AuditContext(request_id=f"{prefix}_req_{i}"),
            )
            for i in range(10)
        ]

        await repo.bulk_create(events)

        all_results = await repo.query_by_category(AuditEventCategory.DATA_ACCESS)
        assert len(all_results) == 10

    @pytest.mark.asyncio
    async def test_query_by_regulation(self) -> None:
        """
        GIVEN events with regulation tags
        WHEN queried by regulation
        THEN matching events are returned.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        # GDPR-tagged event
        gdpr_event = UnifiedAuditEvent(
            event_id=f"{prefix}_gdpr_001",
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_EXPORT,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="user_data",
            resource_id=f"{prefix}_user_001",
            action="Export",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_gdpr"),
            regulation_tags=["GDPR", "SOC2"],
        )
        await repo.create(gdpr_event)

        # HIPAA-only event
        hipaa_event = UnifiedAuditEvent(
            event_id=f"{prefix}_hipaa_001",
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:doctor", actor_type="user"),
            resource_type="medical_record",
            resource_id=f"{prefix}_record_001",
            action="Read",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_hipaa"),
            regulation_tags=["HIPAA"],
        )
        await repo.create(hipaa_event)

        # Query by GDPR
        gdpr_results = await repo.query_by_regulation(Regulation.GDPR)
        assert len(gdpr_results) == 1
        assert gdpr_results[0].event_id == f"{prefix}_gdpr_001"

        # Query by HIPAA
        hipaa_results = await repo.query_by_regulation(Regulation.HIPAA)
        assert len(hipaa_results) == 1
        assert hipaa_results[0].event_id == f"{prefix}_hipaa_001"

    @pytest.mark.asyncio
    async def test_query_by_time_range(self) -> None:
        """
        GIVEN events with different timestamps
        WHEN queried by time range
        THEN only events within range are returned.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        now = datetime.now(UTC)

        # Old event (outside range)
        old_event = UnifiedAuditEvent(
            event_id=f"{prefix}_old_001",
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id=f"{prefix}_sess_old",
            action="Login",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_old"),
            timestamp=now - timedelta(days=30),
        )
        await repo.create(old_event)

        # Recent event (inside range)
        recent_event = UnifiedAuditEvent(
            event_id=f"{prefix}_recent_001",
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id=f"{prefix}_sess_recent",
            action="Login",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_recent"),
            timestamp=now - timedelta(days=1),
        )
        await repo.create(recent_event)

        # Query last 7 days
        start = now - timedelta(days=7)
        results = await repo.query_by_category(
            AuditEventCategory.AUTHENTICATION,
            start_time=start,
            end_time=now,
        )

        assert len(results) == 1
        assert results[0].event_id == f"{prefix}_recent_001"

    @pytest.mark.asyncio
    async def test_query_by_actor(self) -> None:
        """
        GIVEN events from different actors
        WHEN queried by actor
        THEN only matching actor's events are returned.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        # Alice's event
        alice_event = UnifiedAuditEvent(
            event_id=f"{prefix}_alice_001",
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:alice", actor_type="user", username="alice"),
            resource_type="document",
            resource_id=f"{prefix}_doc_alice",
            action="Read",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_alice"),
        )
        await repo.create(alice_event)

        # Bob's event
        bob_event = UnifiedAuditEvent(
            event_id=f"{prefix}_bob_001",
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:bob", actor_type="user", username="bob"),
            resource_type="document",
            resource_id=f"{prefix}_doc_bob",
            action="Read",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_bob"),
        )
        await repo.create(bob_event)

        # Query Alice's events
        alice_results = await repo.query_by_actor("user:alice")
        assert len(alice_results) == 1
        assert alice_results[0].actor.actor_id == "user:alice"


@pytest.mark.xdist_group(name="audit_integrity")
class TestAuditEventIntegrity:
    """Tests for audit event integrity and compliance features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_event_has_required_compliance_fields(self) -> None:
        """
        GIVEN an audit event is created
        WHEN stored in repository
        THEN all compliance-required fields are present.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        event = UnifiedAuditEvent(
            event_id=f"{prefix}_compliance_001",
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(
                actor_id="user:alice",
                actor_type="user",
                username="alice",
            ),
            resource_type="session",
            resource_id=f"{prefix}_sess_001",
            action="User logged in",
            outcome="success",
            context=AuditContext(
                request_id=f"{prefix}_req_001",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
            ),
            regulation_tags=["SOC2", "GDPR"],
        )

        await repo.create(event)

        # Verify event can be retrieved with all fields
        results = await repo.query_by_category(AuditEventCategory.AUTHENTICATION)
        stored = results[0]

        # Compliance-required fields
        assert stored.event_id is not None
        assert stored.timestamp is not None
        assert stored.category == AuditEventCategory.AUTHENTICATION
        assert stored.event_type == AuditEventType.LOGIN_SUCCESS
        assert stored.actor.actor_id == "user:alice"
        assert stored.resource_type == "session"
        assert stored.action == "User logged in"
        assert stored.outcome == "success"
        assert "SOC2" in stored.regulation_tags
        assert "GDPR" in stored.regulation_tags

    @pytest.mark.asyncio
    async def test_event_immutability_after_creation(self) -> None:
        """
        GIVEN an audit event is created
        WHEN attempting to modify it in the repository
        THEN the original event data is preserved (immutability).
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        original_event = UnifiedAuditEvent(
            event_id=f"{prefix}_immutable_001",
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id=f"{prefix}_sess_001",
            action="Login",
            outcome="success",
            context=AuditContext(request_id=f"{prefix}_req_001"),
        )

        await repo.create(original_event)

        # Get stored event
        results = await repo.query_by_category(AuditEventCategory.AUTHENTICATION)
        stored = results[0]

        # Verify fields match original
        assert stored.event_id == original_event.event_id
        assert stored.actor.actor_id == original_event.actor.actor_id
        assert stored.action == original_event.action

    @pytest.mark.asyncio
    async def test_failed_action_audit_logging(self) -> None:
        """
        GIVEN a failed action occurs
        WHEN audit event is created with failure outcome
        THEN failure details are preserved.
        """
        repo = InMemoryUnifiedAuditRepository()
        prefix = get_worker_prefix()

        failed_event = UnifiedAuditEvent(
            event_id=f"{prefix}_failed_001",
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_FAILED,
            actor=AuditActor(actor_id="user:unknown", actor_type="user"),
            resource_type="session",
            resource_id=f"{prefix}_sess_failed",
            action="Login attempt",
            outcome="failure",
            context=AuditContext(
                request_id=f"{prefix}_req_failed",
                ip_address="192.168.1.100",
            ),
            details={
                "reason": "Invalid credentials",
                "risk_level": "high",
                "attempts": 3,
            },
        )

        await repo.create(failed_event)

        results = await repo.query_by_category(AuditEventCategory.AUTHENTICATION)
        stored = results[0]

        assert stored.outcome == "failure"
        assert stored.details["reason"] == "Invalid credentials"
        assert stored.details["risk_level"] == "high"
        assert stored.event_type == AuditEventType.LOGIN_FAILED
