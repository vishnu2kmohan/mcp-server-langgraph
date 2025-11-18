"""
Integration tests for PostgreSQL ConversationStore implementation

Tests GDPR Article 5(1)(e) - 90-day retention with auto-cleanup
"""

import gc
import os
from datetime import datetime, timezone
from typing import AsyncGenerator

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresConversationStore, PostgresUserProfileStore
from mcp_server_langgraph.compliance.gdpr.storage import Conversation, UserProfile

# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="integration_compliance_postgres_conversation_tests")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_conversation_store():
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
        await conn.execute("DELETE FROM conversations WHERE user_id LIKE 'test_%'")
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    yield pool

    # Clean up after test
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM conversations WHERE user_id LIKE 'test_%'")
        await conn.execute("DELETE FROM user_profiles WHERE user_id LIKE 'test_%'")

    await pool.close()


@pytest.fixture
async def profile_store(db_pool: asyncpg.Pool) -> PostgresUserProfileStore:
    """Create user profile store"""
    return PostgresUserProfileStore(db_pool)


@pytest.fixture
async def store(db_pool: asyncpg.Pool) -> PostgresConversationStore:
    """Create PostgreSQL conversation store"""
    return PostgresConversationStore(db_pool)


@pytest.fixture
async def test_user(profile_store: PostgresUserProfileStore) -> str:
    """Create test user"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile = UserProfile(
        user_id="test_conv_user",
        username="convuser",
        email="conv@example.com",
        created_at=now,
        last_updated=now,
    )
    await profile_store.create(profile)
    return "test_conv_user"


# ============================================================================
# CREATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_conversation(store: PostgresConversationStore, test_user: str):
    """Test creating a conversation"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_conv_123",
        user_id=test_user,
        title="Test Conversation",
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        created_at=now,
        last_message_at=now,
    )

    conv_id = await store.create(conversation)
    assert conv_id == "test_conv_123"

    # Verify stored
    retrieved = await store.get("test_conv_123")
    assert retrieved is not None
    assert retrieved.title == "Test Conversation"
    assert len(retrieved.messages) == 2


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_create_conversation_with_empty_messages(store: PostgresConversationStore, test_user: str):
    """Test creating conversation with no messages yet"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_empty",
        user_id=test_user,
        title="Empty Conversation",
        messages=[],
        created_at=now,
        last_message_at=now,
    )

    conv_id = await store.create(conversation)
    assert conv_id == "test_empty"


# ============================================================================
# GET Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_conversation(store: PostgresConversationStore, test_user: str):
    """Test retrieving conversation"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_get",
        user_id=test_user,
        title="Get Test",
        messages=[{"role": "user", "content": "Test"}],
        created_at=now,
        last_message_at=now,
    )
    await store.create(conversation)

    # Get conversation
    retrieved = await store.get("test_get")
    assert retrieved is not None
    assert retrieved.conversation_id == "test_get"
    assert retrieved.user_id == test_user


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_get_nonexistent_conversation(store: PostgresConversationStore):
    """Test getting non-existent conversation returns None"""
    retrieved = await store.get("nonexistent")
    assert retrieved is None


# ============================================================================
# LIST Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_list_user_conversations(store: PostgresConversationStore, test_user: str):
    """Test listing all conversations for a user"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create multiple conversations
    for i in range(3):
        conversation = Conversation(
            conversation_id=f"test_list_{i}",
            user_id=test_user,
            title=f"Conversation {i}",
            messages=[],
            created_at=now,
            last_message_at=now,
        )
        await store.create(conversation)

    # List conversations
    conversations = await store.list_user_conversations(test_user)
    assert len(conversations) == 3


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_list_archived_conversations(store: PostgresConversationStore, test_user: str):
    """Test listing only archived conversations"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create archived conversation
    archived = Conversation(
        conversation_id="test_archived",
        user_id=test_user,
        title="Archived",
        messages=[],
        created_at=now,
        last_message_at=now,
        archived=True,
    )
    await store.create(archived)

    # Create active conversation
    active = Conversation(
        conversation_id="test_active",
        user_id=test_user,
        title="Active",
        messages=[],
        created_at=now,
        last_message_at=now,
        archived=False,
    )
    await store.create(active)

    # List only archived
    archived_convs = await store.list_user_conversations(test_user, archived=True)
    assert len(archived_convs) == 1
    assert archived_convs[0].conversation_id == "test_archived"

    # List only active
    active_convs = await store.list_user_conversations(test_user, archived=False)
    assert len(active_convs) == 1
    assert active_convs[0].conversation_id == "test_active"


# ============================================================================
# UPDATE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_conversation_title(store: PostgresConversationStore, test_user: str):
    """Test updating conversation title"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_update",
        user_id=test_user,
        title="Original Title",
        messages=[],
        created_at=now,
        last_message_at=now,
    )
    await store.create(conversation)

    # Update title
    result = await store.update("test_update", {"title": "New Title"})
    assert result is True

    # Verify update
    retrieved = await store.get("test_update")
    assert retrieved is not None
    assert retrieved.title == "New Title"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_conversation_messages(store: PostgresConversationStore, test_user: str):
    """Test updating conversation messages"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_msg_update",
        user_id=test_user,
        title="Test",
        messages=[{"role": "user", "content": "Hello"}],
        created_at=now,
        last_message_at=now,
    )
    await store.create(conversation)

    # Add message
    new_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]
    result = await store.update("test_msg_update", {"messages": new_messages})
    assert result is True

    # Verify update
    retrieved = await store.get("test_msg_update")
    assert retrieved is not None
    assert len(retrieved.messages) == 2


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_update_archive_conversation(store: PostgresConversationStore, test_user: str):
    """Test archiving a conversation"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_archive",
        user_id=test_user,
        title="Test",
        messages=[],
        created_at=now,
        last_message_at=now,
        archived=False,
    )
    await store.create(conversation)

    # Archive
    result = await store.update("test_archive", {"archived": True})
    assert result is True

    # Verify archived
    retrieved = await store.get("test_archive")
    assert retrieved is not None
    assert retrieved.archived is True


# ============================================================================
# DELETE Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_conversation(store: PostgresConversationStore, test_user: str):
    """Test deleting a single conversation"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_delete",
        user_id=test_user,
        title="Delete Me",
        messages=[],
        created_at=now,
        last_message_at=now,
    )
    await store.create(conversation)

    # Delete
    result = await store.delete("test_delete")
    assert result is True

    # Verify deleted
    retrieved = await store.get("test_delete")
    assert retrieved is None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_delete_user_conversations(store: PostgresConversationStore, test_user: str):
    """Test deleting all conversations for a user (GDPR Article 17)"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create multiple conversations
    for i in range(3):
        conversation = Conversation(
            conversation_id=f"test_bulk_delete_{i}",
            user_id=test_user,
            title=f"Conversation {i}",
            messages=[],
            created_at=now,
            last_message_at=now,
        )
        await store.create(conversation)

    # Delete all
    count = await store.delete_user_conversations(test_user)
    assert count == 3

    # Verify all deleted
    conversations = await store.list_user_conversations(test_user)
    assert len(conversations) == 0


# ============================================================================
# CASCADE DELETE Test
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gdpr
async def test_conversations_deleted_when_user_deleted(
    profile_store: PostgresUserProfileStore,
    store: PostgresConversationStore,
    test_user: str,
):
    """Test that conversations are CASCADE deleted when user is deleted"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Create conversation
    conversation = Conversation(
        conversation_id="test_cascade",
        user_id=test_user,
        title="Cascade Test",
        messages=[],
        created_at=now,
        last_message_at=now,
    )
    await store.create(conversation)

    # Delete user (should cascade to conversations)
    await profile_store.delete(test_user)

    # Verify conversation deleted
    conversations = await store.list_user_conversations(test_user)
    assert len(conversations) == 0
