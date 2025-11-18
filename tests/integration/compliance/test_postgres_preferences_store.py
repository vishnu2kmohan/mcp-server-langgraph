"""
Integration tests for PostgreSQL PreferencesStore implementation

Tests GDPR compliance for user preferences storage
"""

import gc
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresPreferencesStore, PostgresUserProfileStore
from mcp_server_langgraph.compliance.gdpr.storage import UserProfile


# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="integration_compliance_postgres_preferences_tests")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_preferences_store():
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
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "gdpr_test"),
        min_size=1,
        max_size=5,
    )

    # Clean up test data
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_preferences WHERE user_id LIKE 'test_%'")
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    yield pool

    # Clean up after test
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_preferences WHERE user_id LIKE 'test_%'")
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    await pool.close()


@pytest.fixture
async def profile_store(db_pool: asyncpg.Pool) -> PostgresUserProfileStore:
    """Create user profile store for test data setup"""
    return PostgresUserProfileStore(db_pool)


@pytest.fixture
async def store(db_pool: asyncpg.Pool) -> PostgresPreferencesStore:
    """Create PostgreSQL preferences store"""
    return PostgresPreferencesStore(db_pool)


@pytest.fixture
async def test_user(profile_store: PostgresUserProfileStore) -> str:
    """Create test user and return user_id"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile = UserProfile(
        user_id="test_pref_user",
        username="prefuser",
        email="pref@example.com",
        created_at=now,
        last_updated=now,
    )
    await profile_store.create(profile)
    return "test_pref_user"


# ============================================================================
# GET/SET Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_nonexistent_preferences(store: PostgresPreferencesStore):
    """Test getting preferences for user without preferences returns None"""
    result = await store.get("nonexistent_user")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_set_preferences_new_user(store: PostgresPreferencesStore, test_user: str):
    """Test setting preferences for user"""
    preferences = {
        "theme": "dark",
        "language": "en",
        "notifications": {"email": True, "sms": False},
    }

    result = await store.set(test_user, preferences)
    assert result is True

    # Verify stored
    retrieved = await store.get(test_user)
    assert retrieved is not None
    assert retrieved.user_id == test_user
    assert retrieved.preferences == preferences


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_set_preferences_overwrites_existing(store: PostgresPreferencesStore, test_user: str):
    """Test that set overwrites existing preferences"""
    # Set initial preferences
    initial_prefs = {"theme": "light"}
    await store.set(test_user, initial_prefs)

    # Overwrite with new preferences
    new_prefs = {"theme": "dark", "language": "fr"}
    result = await store.set(test_user, new_prefs)
    assert result is True

    # Verify overwritten
    retrieved = await store.get(test_user)
    assert retrieved is not None
    assert retrieved.preferences == new_prefs
    assert "language" in retrieved.preferences


# ============================================================================
# UPDATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_preferences_partial(store: PostgresPreferencesStore, test_user: str):
    """Test updating specific preferences without overwriting all"""
    # Set initial preferences
    initial = {"theme": "light", "language": "en", "timezone": "UTC"}
    await store.set(test_user, initial)

    # Update only theme
    updates = {"theme": "dark"}
    result = await store.update(test_user, updates)
    assert result is True

    # Verify partial update
    retrieved = await store.get(test_user)
    assert retrieved is not None
    assert retrieved.preferences["theme"] == "dark"
    assert retrieved.preferences["language"] == "en"  # Unchanged
    assert retrieved.preferences["timezone"] == "UTC"  # Unchanged


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_preferences_nested(store: PostgresPreferencesStore, test_user: str):
    """Test updating nested preferences"""
    # Set initial
    initial = {
        "notifications": {
            "email": True,
            "sms": False,
            "push": True,
        }
    }
    await store.set(test_user, initial)

    # Update nested value
    updates = {"notifications": {"email": False, "sms": True, "push": True}}
    result = await store.update(test_user, updates)
    assert result is True

    # Verify update
    retrieved = await store.get(test_user)
    assert retrieved is not None
    assert retrieved.preferences["notifications"]["email"] is False
    assert retrieved.preferences["notifications"]["sms"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_nonexistent_preferences(store: PostgresPreferencesStore):
    """Test updating non-existent preferences fails"""
    result = await store.update("nonexistent_user", {"theme": "dark"})
    assert result is False


# ============================================================================
# DELETE Tests (GDPR Article 17)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_preferences(store: PostgresPreferencesStore, test_user: str):
    """Test deleting user preferences"""
    # Set preferences
    await store.set(test_user, {"theme": "dark"})

    # Delete
    result = await store.delete(test_user)
    assert result is True

    # Verify deletion
    retrieved = await store.get(test_user)
    assert retrieved is None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_nonexistent_preferences(store: PostgresPreferencesStore):
    """Test deleting non-existent preferences"""
    result = await store.delete("nonexistent_user")
    assert result is False


# ============================================================================
# CASCADE DELETE Test (Foreign Key Constraint)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_preferences_deleted_when_user_deleted(
    profile_store: PostgresUserProfileStore,
    store: PostgresPreferencesStore,
    test_user: str,
):
    """Test that preferences are CASCADE deleted when user is deleted"""
    # Set preferences
    await store.set(test_user, {"theme": "dark"})

    # Delete user profile (should cascade to preferences)
    await profile_store.delete(test_user)

    # Verify preferences also deleted
    retrieved = await store.get(test_user)
    assert retrieved is None
