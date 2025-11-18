"""
Integration tests for PostgreSQL UserProfileStore implementation

Tests GDPR compliance requirements:
- Article 15: Right to access
- Article 17: Right to erasure
- Article 5(1)(e): Storage limitation

Following TDD principles:
1. RED: Write failing tests
2. GREEN: Implement to pass tests
3. REFACTOR: Improve code quality
"""

import gc
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresUserProfileStore
from mcp_server_langgraph.compliance.gdpr.storage import UserProfile


# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="integration_compliance_postgres_user_profile_tests")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_user_profile_store():
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

    # Clean up test data before each test
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    yield pool

    # Clean up after test
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    await pool.close()


@pytest.fixture
async def store(db_pool: asyncpg.Pool) -> PostgresUserProfileStore:
    """Create PostgreSQL user profile store"""
    return PostgresUserProfileStore(db_pool)


@pytest.fixture
def sample_profile() -> UserProfile:
    """Create sample user profile for testing"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return UserProfile(
        user_id="test_user_123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        created_at=now,
        last_updated=now,
        metadata={"department": "Engineering", "role": "Developer"},
    )


# ============================================================================
# CREATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_user_profile_success(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test creating a new user profile"""
    # Act
    result = await store.create(sample_profile)

    # Assert
    assert result is True

    # Verify stored
    retrieved = await store.get(sample_profile.user_id)
    assert retrieved is not None
    assert retrieved.user_id == sample_profile.user_id
    assert retrieved.username == sample_profile.username
    assert retrieved.email == sample_profile.email
    assert retrieved.full_name == sample_profile.full_name
    assert retrieved.metadata == sample_profile.metadata


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_duplicate_user_profile_fails(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test that creating duplicate user profile fails"""
    # Arrange
    await store.create(sample_profile)

    # Act
    result = await store.create(sample_profile)

    # Assert
    assert result is False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_user_profile_with_minimal_data(store: PostgresUserProfileStore):
    """Test creating user profile with only required fields"""
    # Arrange
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    minimal_profile = UserProfile(
        user_id="test_minimal",
        username="minimal",
        email="minimal@example.com",
        created_at=now,
        last_updated=now,
    )

    # Act
    result = await store.create(minimal_profile)

    # Assert
    assert result is True
    retrieved = await store.get("test_minimal")
    assert retrieved is not None
    assert retrieved.full_name is None
    assert retrieved.metadata == {}


# ============================================================================
# GET Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_existing_user_profile(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test retrieving existing user profile (GDPR Article 15)"""
    # Arrange
    await store.create(sample_profile)

    # Act
    retrieved = await store.get(sample_profile.user_id)

    # Assert
    assert retrieved is not None
    assert retrieved.user_id == sample_profile.user_id
    assert retrieved.username == sample_profile.username
    assert retrieved.email == sample_profile.email


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_nonexistent_user_profile(store: PostgresUserProfileStore):
    """Test retrieving non-existent user profile returns None"""
    # Act
    retrieved = await store.get("nonexistent_user")

    # Assert
    assert retrieved is None


# ============================================================================
# UPDATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_user_profile_email(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test updating user profile email"""
    # Arrange
    await store.create(sample_profile)
    original_updated = sample_profile.last_updated

    # Act
    result = await store.update(sample_profile.user_id, {"email": "newemail@example.com"})

    # Assert
    assert result is True

    # Verify update
    retrieved = await store.get(sample_profile.user_id)
    assert retrieved is not None
    assert retrieved.email == "newemail@example.com"
    # last_updated should be automatically updated by trigger
    assert retrieved.last_updated > original_updated


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_user_profile_metadata(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test updating user profile metadata"""
    # Arrange
    await store.create(sample_profile)

    # Act
    new_metadata = {"department": "Product", "role": "Manager", "location": "Remote"}
    result = await store.update(sample_profile.user_id, {"metadata": new_metadata})

    # Assert
    assert result is True

    # Verify update
    retrieved = await store.get(sample_profile.user_id)
    assert retrieved is not None
    assert retrieved.metadata == new_metadata


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_nonexistent_user_profile(store: PostgresUserProfileStore):
    """Test updating non-existent user profile fails"""
    # Act
    result = await store.update("nonexistent_user", {"email": "test@example.com"})

    # Assert
    assert result is False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_multiple_fields(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test updating multiple fields at once"""
    # Arrange
    await store.create(sample_profile)

    # Act
    updates = {
        "email": "updated@example.com",
        "full_name": "Updated Name",
        "metadata": {"new_field": "value"},
    }
    result = await store.update(sample_profile.user_id, updates)

    # Assert
    assert result is True

    # Verify all updates
    retrieved = await store.get(sample_profile.user_id)
    assert retrieved is not None
    assert retrieved.email == "updated@example.com"
    assert retrieved.full_name == "Updated Name"
    assert retrieved.metadata == {"new_field": "value"}


# ============================================================================
# DELETE Tests (GDPR Article 17 - Right to Erasure)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_user_profile(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test deleting user profile (GDPR Article 17)"""
    # Arrange
    await store.create(sample_profile)

    # Act
    result = await store.delete(sample_profile.user_id)

    # Assert
    assert result is True

    # Verify deletion
    retrieved = await store.get(sample_profile.user_id)
    assert retrieved is None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_nonexistent_user_profile(store: PostgresUserProfileStore):
    """Test deleting non-existent user profile"""
    # Act
    result = await store.delete("nonexistent_user")

    # Assert
    assert result is False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_user_profile_is_permanent(store: PostgresUserProfileStore, sample_profile: UserProfile):
    """Test that deletion is permanent and cannot be retrieved"""
    # Arrange
    await store.create(sample_profile)
    await store.delete(sample_profile.user_id)

    # Act - Try to retrieve after deletion
    retrieved = await store.get(sample_profile.user_id)

    # Assert
    assert retrieved is None


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_profile_with_special_characters(store: PostgresUserProfileStore):
    """Test creating profile with special characters in fields"""
    # Arrange
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    special_profile = UserProfile(
        user_id="test_special_123",
        username="test'user\"<>",
        email="test+tag@example.com",
        full_name="Test O'Brien",
        created_at=now,
        last_updated=now,
        metadata={"description": "User with 'quotes' and \"escapes\""},
    )

    # Act
    result = await store.create(special_profile)

    # Assert
    assert result is True

    # Verify special characters preserved
    retrieved = await store.get("test_special_123")
    assert retrieved is not None
    assert retrieved.username == special_profile.username
    assert retrieved.full_name == special_profile.full_name


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_profile_with_unicode(store: PostgresUserProfileStore):
    """Test creating profile with Unicode characters"""
    # Arrange
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    unicode_profile = UserProfile(
        user_id="test_unicode_123",
        username="用户123",
        email="test@例え.com",
        full_name="李明 (Lǐ Míng)",
        created_at=now,
        last_updated=now,
        metadata={"greeting": "こんにちは"},
    )

    # Act
    result = await store.create(unicode_profile)

    # Assert
    assert result is True

    # Verify Unicode preserved
    retrieved = await store.get("test_unicode_123")
    assert retrieved is not None
    assert retrieved.username == "用户123"
    assert retrieved.full_name == "李明 (Lǐ Míng)"
    assert retrieved.metadata["greeting"] == "こんにちは"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_metadata_nested_json(store: PostgresUserProfileStore):
    """Test storing complex nested JSON in metadata"""
    # Arrange
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    complex_metadata = {
        "preferences": {
            "theme": "dark",
            "notifications": {
                "email": True,
                "sms": False,
                "push": {"enabled": True, "frequency": "daily"},
            },
        },
        "tags": ["vip", "early-adopter"],
        "scores": [95, 87, 92],
    }

    profile = UserProfile(
        user_id="test_complex_json",
        username="complexuser",
        email="complex@example.com",
        created_at=now,
        last_updated=now,
        metadata=complex_metadata,
    )

    # Act
    result = await store.create(profile)

    # Assert
    assert result is True

    # Verify complex JSON preserved
    retrieved = await store.get("test_complex_json")
    assert retrieved is not None
    assert retrieved.metadata == complex_metadata
    assert retrieved.metadata["preferences"]["notifications"]["push"]["frequency"] == "daily"
