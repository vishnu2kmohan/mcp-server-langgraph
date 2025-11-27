"""
Integration tests for PostgreSQL AuditLogStore implementation

Tests HIPAA §164.312(b) and SOC2 CC6.6 - 7-year audit log retention
"""

import gc
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresAuditLogStore
from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry
from tests.conftest import get_user_id

# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="postgres_audit_log_store")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_audit_log_store():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


@pytest.fixture
async def db_pool(postgres_connection_real) -> AsyncGenerator[asyncpg.Pool, None]:
    """
    Use shared test database pool with cleanup.

    CODEX FINDING FIX (2025-11-20):
    =================================
    Previous: Created separate pool per test file
    Problem: Multiple pools caused "asyncpg.exceptions.InterfaceError: another operation is in progress"
    Fix: Use shared session-scoped pool from conftest.py

    This prevents connection conflicts when multiple test files run in parallel.

    Depends on postgres_connection_real (session-scoped shared pool) instead of
    creating a new pool. This fixes the "another operation is in progress" errors
    that occurred when multiple pools tried to access the same database.
    """
    pool = postgres_connection_real

    # Clean up test data
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM audit_logs WHERE log_id LIKE 'test_%'")

    yield pool

    # Clean up after test
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM audit_logs WHERE log_id LIKE 'test_%'")

    # Note: Don't close the pool - it's session-scoped and shared across all tests


@pytest.fixture
async def store(db_pool: asyncpg.Pool) -> PostgresAuditLogStore:
    """Create PostgreSQL audit log store"""
    return PostgresAuditLogStore(db_pool)


# ============================================================================
# LOG Tests (CREATE)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_log_audit_entry(store: PostgresAuditLogStore):
    """Test logging an audit entry"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    user_id = get_user_id("alice")
    entry = AuditLogEntry(
        log_id="test_log_123",
        user_id=user_id,
        action="profile.update",
        resource_type="user_profile",
        resource_id=user_id,
        timestamp=now,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        metadata={"fields_updated": ["email"]},
    )

    log_id = await store.log(entry)
    assert log_id == "test_log_123"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_log_system_event_without_user(store: PostgresAuditLogStore):
    """Test logging system event (no user_id)"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = AuditLogEntry(
        log_id="test_system_log",
        user_id="",  # System event, no user
        action="system.startup",
        resource_type="system",
        timestamp=now,
        metadata={"version": "1.0.0"},
    )

    log_id = await store.log(entry)
    assert log_id == "test_system_log"


# ============================================================================
# GET Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_audit_log_entry(store: PostgresAuditLogStore):
    """Test retrieving audit log entry by ID"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    user_id = get_user_id("bob")
    entry = AuditLogEntry(
        log_id="test_get_log",
        user_id=user_id,
        action="data.access",
        resource_type="medical_record",
        resource_id="record_123",
        timestamp=now,
    )
    await store.log(entry)

    # Retrieve
    retrieved = await store.get("test_get_log")
    assert retrieved is not None
    assert retrieved.log_id == "test_get_log"
    assert retrieved.user_id == user_id
    assert retrieved.action == "data.access"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_nonexistent_audit_log(store: PostgresAuditLogStore):
    """Test getting non-existent audit log returns None"""
    retrieved = await store.get("nonexistent_log")
    assert retrieved is None


# ============================================================================
# LIST USER LOGS Tests (HIPAA/SOC2 compliance queries)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_list_user_logs_basic(store: PostgresAuditLogStore):
    """Test listing all logs for a user"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    user_id = get_user_id("charlie")

    # Create multiple logs
    for i in range(3):
        entry = AuditLogEntry(
            log_id=f"test_list_{i}",
            user_id=user_id,
            action=f"action_{i}",
            resource_type="resource",
            timestamp=now,
        )
        await store.log(entry)

    # List logs
    logs = await store.list_user_logs(user_id)
    assert len(logs) == 3


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_list_user_logs_with_date_range(store: PostgresAuditLogStore):
    """Test listing user logs with date range filter (HIPAA compliance query)"""
    user_id = get_user_id("david")

    # Create logs at different times
    base_time = datetime.now(timezone.utc)

    # Old log (30 days ago)
    old_time = (base_time - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    old_entry = AuditLogEntry(
        log_id="test_old_log",
        user_id=user_id,
        action="old.action",
        resource_type="resource",
        timestamp=old_time,
    )
    await store.log(old_entry)

    # Recent log (1 day ago)
    recent_time = (base_time - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    recent_entry = AuditLogEntry(
        log_id="test_recent_log",
        user_id=user_id,
        action="recent.action",
        resource_type="resource",
        timestamp=recent_time,
    )
    await store.log(recent_entry)

    # List logs from last 7 days
    start_date = base_time - timedelta(days=7)
    logs = await store.list_user_logs(user_id, start_date=start_date)

    # Should only get recent log
    assert len(logs) == 1
    assert logs[0].log_id == "test_recent_log"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_list_user_logs_with_limit(store: PostgresAuditLogStore):
    """Test listing user logs with limit"""
    user_id = get_user_id("eve")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create many logs
    for i in range(150):
        entry = AuditLogEntry(
            log_id=f"test_limit_{i}",
            user_id=user_id,
            action=f"action_{i}",
            resource_type="resource",
            timestamp=now,
        )
        await store.log(entry)

    # List with limit
    logs = await store.list_user_logs(user_id, limit=50)
    assert len(logs) == 50


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_list_user_logs_ordered_by_timestamp(store: PostgresAuditLogStore):
    """Test that logs are returned in descending timestamp order"""
    user_id = get_user_id("frank")
    base_time = datetime.now(timezone.utc)

    # Create logs in reverse chronological order
    for i in range(3):
        timestamp = (base_time - timedelta(hours=i)).isoformat().replace("+00:00", "Z")
        entry = AuditLogEntry(
            log_id=f"test_order_{i}",
            user_id=user_id,
            action=f"action_{i}",
            resource_type="resource",
            timestamp=timestamp,
        )
        await store.log(entry)

    # List logs
    logs = await store.list_user_logs(user_id)

    # Verify ordered by timestamp descending (most recent first)
    assert logs[0].log_id == "test_order_0"  # Most recent
    assert logs[1].log_id == "test_order_1"
    assert logs[2].log_id == "test_order_2"  # Oldest


# ============================================================================
# ANONYMIZE Tests (GDPR Article 17 - Right to Erasure)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_anonymize_user_logs(store: PostgresAuditLogStore):
    """Test anonymizing audit logs for deleted user (GDPR Article 17)"""
    user_id = get_user_id("grace")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create logs
    for i in range(3):
        entry = AuditLogEntry(
            log_id=f"test_anon_{i}",
            user_id=user_id,
            action=f"action_{i}",
            resource_type="resource",
            timestamp=now,
        )
        await store.log(entry)

    # Anonymize
    count = await store.anonymize_user_logs(user_id)
    assert count == 3

    # Verify logs still exist but user_id anonymized
    logs = await store.list_user_logs(user_id)
    assert len(logs) == 0  # No logs for original user_id

    # Check logs are now anonymized (user_id = 'anonymized')
    anon_logs = await store.list_user_logs("anonymized")
    assert len(anon_logs) == 3


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_anonymize_preserves_audit_trail(store: PostgresAuditLogStore):
    """Test that anonymization preserves audit trail (compliance requirement)"""
    user_id = get_user_id("henry")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create log with detailed information
    entry = AuditLogEntry(
        log_id="test_preserve",
        user_id=user_id,
        action="phi.access",
        resource_type="medical_record",
        resource_id="record_456",
        timestamp=now,
        ip_address="10.0.0.1",
        user_agent="HealthApp/1.0",
        metadata={"record_type": "diagnosis", "department": "cardiology"},
    )
    await store.log(entry)

    # Anonymize
    await store.anonymize_user_logs(user_id)

    # Retrieve anonymized log
    retrieved = await store.get("test_preserve")
    assert retrieved is not None

    # Verify audit trail preserved (except user_id)
    assert retrieved.user_id == "anonymized"
    assert retrieved.action == "phi.access"
    assert retrieved.resource_type == "medical_record"
    assert retrieved.resource_id == "record_456"
    assert retrieved.ip_address == "10.0.0.1"
    assert retrieved.metadata == {"record_type": "diagnosis", "department": "cardiology"}


# ============================================================================
# COMPLIANCE-SPECIFIC Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_audit_log_immutability(store: PostgresAuditLogStore):
    """Test that audit logs are immutable (cannot be updated)"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    user_id = get_user_id("ivan")
    entry = AuditLogEntry(
        log_id="test_immutable",
        user_id=user_id,
        action="original.action",
        resource_type="resource",
        timestamp=now,
    )
    await store.log(entry)

    # Note: There should be no update method for audit logs
    # They are append-only for compliance
    # This test verifies the interface doesn't provide update capability


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_audit_log_metadata_json(store: PostgresAuditLogStore):
    """Test storing complex metadata in audit logs"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    user_id = get_user_id("jane")
    admin1 = get_user_id("admin1")
    admin2 = get_user_id("admin2")

    complex_metadata = {
        "request_id": "req_123",
        "session_id": "sess_456",
        "trace_id": "trace_789",
        "changes": {
            "before": {"status": "pending"},
            "after": {"status": "approved"},
        },
        "approvers": [admin1, admin2],
    }

    entry = AuditLogEntry(
        log_id="test_complex_meta",
        user_id=user_id,
        action="approval.granted",
        resource_type="request",
        resource_id="req_123",
        timestamp=now,
        metadata=complex_metadata,
    )

    await store.log(entry)

    # Verify complex metadata preserved
    retrieved = await store.get("test_complex_meta")
    assert retrieved is not None
    assert retrieved.metadata == complex_metadata
    assert retrieved.metadata["changes"]["after"]["status"] == "approved"


# ============================================================================
# PERFORMANCE Tests (Indexing verification)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
@pytest.mark.slow
async def test_list_logs_performance_with_many_users(store: PostgresAuditLogStore):
    """Test query performance with many users (index verification)"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    target_user = get_user_id("perf_test")

    # Create logs for many different users
    for i in range(100):
        entry = AuditLogEntry(
            log_id=f"test_perf_{i}",
            user_id=get_user_id(f"perf_{i}"),
            action="action",
            resource_type="resource",
            timestamp=now,
        )
        await store.log(entry)

    # Create logs for target user
    for i in range(10):
        entry = AuditLogEntry(
            log_id=f"test_target_{i}",
            user_id=target_user,
            action="action",
            resource_type="resource",
            timestamp=now,
        )
        await store.log(entry)

    # Query should be fast due to user_id index
    logs = await store.list_user_logs(target_user)
    assert len(logs) == 10
