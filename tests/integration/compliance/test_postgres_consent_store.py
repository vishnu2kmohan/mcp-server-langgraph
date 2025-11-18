"""
Integration tests for PostgreSQL ConsentStore implementation

Tests GDPR Article 7 (Consent) - 7-year retention requirement
"""

import gc
import os
from datetime import datetime, timezone
from typing import AsyncGenerator

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresConsentStore, PostgresUserProfileStore
from mcp_server_langgraph.compliance.gdpr.storage import ConsentRecord, UserProfile

# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="integration_compliance_postgres_consent_tests")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_consent_store():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """
    Create test database pool with environment-based configuration.

    Supports both local development and CI/CD environments by using
    environment variables with sensible defaults.
    """
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "9432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "gdpr_test"),
        min_size=1,
        max_size=5,
    )

    # Clean up test data
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM consent_records WHERE user_id LIKE 'test_%'")
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    yield pool

    # Clean up after test
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM consent_records WHERE user_id LIKE 'test_%'")
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    await pool.close()


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
    """Create test user"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile = UserProfile(
        user_id="test_consent_user",
        username="consentuser",
        email="consent@example.com",
        created_at=now,
        last_updated=now,
    )
    await profile_store.create(profile)
    return "test_consent_user"


# ============================================================================
# CREATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_consent_record(store: PostgresConsentStore, test_user: str):
    """Test creating consent record"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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
    new_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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
    withdraw_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
