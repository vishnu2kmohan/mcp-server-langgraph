"""
Integration tests for PostgreSQL ConsentStore implementation

Tests GDPR Article 7 (Consent) - 7-year retention requirement
"""

import gc
import os
from collections.abc import AsyncGenerator
from datetime import datetime, UTC

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresConsentStore, PostgresUserProfileStore
from mcp_server_langgraph.compliance.gdpr.storage import ConsentRecord, UserProfile
from tests.conftest import get_user_id

# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="postgres_consent_store")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_consent_store():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


@pytest.fixture
async def db_pool(postgres_connection_real) -> AsyncGenerator[asyncpg.Pool, None]:
    """
    Use shared test database pool with cleanup.

    CODEX FINDING FIX (2025-11-20): Use shared pool to prevent
    "asyncpg.exceptions.InterfaceError: another operation is in progress"

    XDIST ISOLATION FIX (2025-11-30): Use worker-specific cleanup pattern
    to prevent race conditions when multiple xdist workers clean up each
    other's data. Pattern: 'user:test_gw{N}_%' where N is the worker ID.
    """
    pool = postgres_connection_real

    # Get worker-specific pattern for cleanup (prevents xdist race conditions)
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    cleanup_pattern = f"user:test_{worker_id}_%"

    # Clean up THIS WORKER's test data only
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM consent_records WHERE user_id LIKE $1", cleanup_pattern)
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE $1", cleanup_pattern)

    yield pool

    # Clean up THIS WORKER's test data only
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM consent_records WHERE user_id LIKE $1", cleanup_pattern)
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE $1", cleanup_pattern)

    # Note: Don't close the pool - it's session-scoped and shared across all tests


@pytest.fixture
async def profile_store(db_pool: asyncpg.Pool) -> PostgresUserProfileStore:
    """Create user profile store"""
    return PostgresUserProfileStore(db_pool)


@pytest.fixture
async def store(db_pool: asyncpg.Pool) -> PostgresConsentStore:
    """Create PostgreSQL consent store"""
    return PostgresConsentStore(db_pool)


@pytest.fixture
async def test_user(profile_store: PostgresUserProfileStore) -> str:
    """Create test user (worker-safe for pytest-xdist)"""
    user_id = get_user_id("consent_user")  # Worker-safe ID for parallel execution
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    profile = UserProfile(
        user_id=user_id,
        username="consentuser",
        email="consent@example.com",
        created_at=now,
        last_updated=now,
    )
    await profile_store.create(profile)
    return user_id


# ============================================================================
# CREATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_consent_record(store: PostgresConsentStore, test_user: str):
    """Test creating consent record"""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    record = ConsentRecord(
        consent_id="test_consent_123",
        user_id=test_user,
        consent_type="analytics",
        granted=True,
        timestamp=now,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        metadata={"source": "web"},
    )

    consent_id = await store.create(record)
    assert consent_id == "test_consent_123"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_multiple_consent_types(store: PostgresConsentStore, test_user: str):
    """Test creating multiple consent types for same user"""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Create analytics consent
    analytics = ConsentRecord(
        consent_id="test_analytics",
        user_id=test_user,
        consent_type="analytics",
        granted=True,
        timestamp=now,
    )
    await store.create(analytics)

    # Create marketing consent
    marketing = ConsentRecord(
        consent_id="test_marketing",
        user_id=test_user,
        consent_type="marketing",
        granted=False,
        timestamp=now,
    )
    await store.create(marketing)

    # Verify both exist
    consents = await store.get_user_consents(test_user)
    assert len(consents) == 2


# ============================================================================
# GET Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_user_consents(store: PostgresConsentStore, test_user: str):
    """Test getting all consents for a user"""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Create consents
    for i, consent_type in enumerate(["analytics", "marketing", "third_party"]):
        record = ConsentRecord(
            consent_id=f"test_{consent_type}",
            user_id=test_user,
            consent_type=consent_type,
            granted=i % 2 == 0,  # Alternate granted/not granted
            timestamp=now,
        )
        await store.create(record)

    # Get all consents
    consents = await store.get_user_consents(test_user)
    assert len(consents) == 3

    consent_types = {c.consent_type for c in consents}
    assert consent_types == {"analytics", "marketing", "third_party"}


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_latest_consent(store: PostgresConsentStore, test_user: str):
    """Test getting latest consent for a specific type"""
    # Create older consent
    old_time = "2025-01-01T00:00:00Z"
    old_consent = ConsentRecord(
        consent_id="test_old",
        user_id=test_user,
        consent_type="analytics",
        granted=False,
        timestamp=old_time,
    )
    await store.create(old_consent)

    # Create newer consent
    new_time = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    new_consent = ConsentRecord(
        consent_id="test_new",
        user_id=test_user,
        consent_type="analytics",
        granted=True,
        timestamp=new_time,
    )
    await store.create(new_consent)

    # Get latest
    latest = await store.get_latest_consent(test_user, "analytics")
    assert latest is not None
    assert latest.consent_id == "test_new"
    assert latest.granted is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_latest_consent_nonexistent_type(store: PostgresConsentStore, test_user: str):
    """Test getting latest consent for non-existent type returns None"""
    latest = await store.get_latest_consent(test_user, "nonexistent_type")
    assert latest is None


# ============================================================================
# DELETE Tests (GDPR Article 17 - but consents kept 7 years for legal compliance)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_user_consents(store: PostgresConsentStore, test_user: str):
    """Test deleting all consents for a user"""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Create consents
    for consent_type in ["analytics", "marketing"]:
        record = ConsentRecord(
            consent_id=f"test_{consent_type}",
            user_id=test_user,
            consent_type=consent_type,
            granted=True,
            timestamp=now,
        )
        await store.create(record)

    # Delete all
    count = await store.delete_user_consents(test_user)
    assert count == 2

    # Verify deleted
    consents = await store.get_user_consents(test_user)
    assert len(consents) == 0


# ============================================================================
# CASCADE DELETE Test
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_consents_deleted_when_user_deleted(
    profile_store: PostgresUserProfileStore,
    store: PostgresConsentStore,
    test_user: str,
):
    """Test that consents are CASCADE deleted when user is deleted"""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Create consent
    record = ConsentRecord(
        consent_id="test_cascade",
        user_id=test_user,
        consent_type="analytics",
        granted=True,
        timestamp=now,
    )
    await store.create(record)

    # Delete user (should cascade to consents)
    await profile_store.delete(test_user)

    # Verify consents deleted
    consents = await store.get_user_consents(test_user)
    assert len(consents) == 0


# ============================================================================
# CONSENT WITHDRAWAL Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_consent_withdrawal_creates_new_record(store: PostgresConsentStore, test_user: str):
    """Test that withdrawing consent creates a new record (audit trail)"""
    # Grant consent
    grant_time = "2025-01-01T00:00:00Z"
    grant_record = ConsentRecord(
        consent_id="test_grant",
        user_id=test_user,
        consent_type="analytics",
        granted=True,
        timestamp=grant_time,
    )
    await store.create(grant_record)

    # Withdraw consent (new record)
    withdraw_time = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    withdraw_record = ConsentRecord(
        consent_id="test_withdraw",
        user_id=test_user,
        consent_type="analytics",
        granted=False,
        timestamp=withdraw_time,
    )
    await store.create(withdraw_record)

    # Verify both records exist (audit trail)
    consents = await store.get_user_consents(test_user)
    assert len(consents) == 2

    # Latest should be withdrawal
    latest = await store.get_latest_consent(test_user, "analytics")
    assert latest is not None
    assert latest.granted is False
