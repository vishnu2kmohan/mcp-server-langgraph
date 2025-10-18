"""
Unit tests for conversation metadata store

Tests in-memory backend for conversation tracking.
"""

import pytest

from mcp_server_langgraph.storage.conversation_store import ConversationMetadata, ConversationStore


@pytest.mark.unit
class TestConversationStore:
    """Test suite for ConversationStore"""

    @pytest.fixture
    def store(self):
        """Create in-memory conversation store"""
        return ConversationStore(backend="memory")

    @pytest.mark.asyncio
    async def test_record_conversation(self, store):
        """Test recording conversation metadata"""
        await store.record_conversation(thread_id="test_thread", user_id="user:alice", message_count=5, title="Test Conv")

        metadata = await store.get_conversation("test_thread")
        assert metadata is not None
        assert metadata.thread_id == "test_thread"
        assert metadata.user_id == "user:alice"
        assert metadata.message_count == 5
        assert metadata.title == "Test Conv"

    @pytest.mark.asyncio
    async def test_update_conversation(self, store):
        """Test updating existing conversation"""
        # Create
        await store.record_conversation(thread_id="test_thread", user_id="user:alice", message_count=5)

        # Update
        await store.record_conversation(thread_id="test_thread", user_id="user:alice", message_count=10, title="Updated")

        metadata = await store.get_conversation("test_thread")
        assert metadata.message_count == 10
        assert metadata.title == "Updated"

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, store):
        """Test getting nonexistent conversation returns None"""
        metadata = await store.get_conversation("nonexistent")
        assert metadata is None

    @pytest.mark.asyncio
    async def test_list_user_conversations(self, store):
        """Test listing all conversations for a user"""
        # Create conversations for different users
        await store.record_conversation(thread_id="alice_1", user_id="user:alice", message_count=5)
        await store.record_conversation(thread_id="alice_2", user_id="user:alice", message_count=3)
        await store.record_conversation(thread_id="bob_1", user_id="user:bob", message_count=7)

        alice_convs = await store.list_user_conversations("user:alice")
        assert len(alice_convs) == 2
        assert all(c.user_id == "user:alice" for c in alice_convs)

        bob_convs = await store.list_user_conversations("user:bob")
        assert len(bob_convs) == 1
        assert bob_convs[0].user_id == "user:bob"

    @pytest.mark.asyncio
    async def test_list_conversations_sorted_by_activity(self, store):
        """Test conversations are sorted by last activity"""
        import time

        # Create conversations with delays to ensure different timestamps
        await store.record_conversation(thread_id="old", user_id="user:alice", message_count=1)
        time.sleep(0.01)
        await store.record_conversation(thread_id="recent", user_id="user:alice", message_count=1)

        convs = await store.list_user_conversations("user:alice")
        assert len(convs) == 2
        # Most recent should be first
        assert convs[0].thread_id == "recent"
        assert convs[1].thread_id == "old"

    @pytest.mark.asyncio
    async def test_search_conversations_by_query(self, store):
        """Test searching conversations by query"""
        await store.record_conversation(thread_id="project_alpha", user_id="user:alice", message_count=5, title="Alpha Project")
        await store.record_conversation(thread_id="project_beta", user_id="user:alice", message_count=3, title="Beta Release")
        await store.record_conversation(thread_id="other", user_id="user:alice", message_count=2, title="Something Else")

        # Search for "alpha"
        results = await store.search_conversations("user:alice", query="alpha", limit=10)
        assert len(results) == 1
        assert results[0].thread_id == "project_alpha"

        # Search for "project"
        results = await store.search_conversations("user:alice", query="project", limit=10)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_conversations_no_query(self, store):
        """Test search with no query returns most recent"""
        await store.record_conversation(thread_id="conv1", user_id="user:alice", message_count=5)
        await store.record_conversation(thread_id="conv2", user_id="user:alice", message_count=3)

        results = await store.search_conversations("user:alice", query="", limit=10)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_conversations_limit(self, store):
        """Test search respects limit"""
        for i in range(10):
            await store.record_conversation(thread_id=f"conv{i}", user_id="user:alice", message_count=1)

        results = await store.search_conversations("user:alice", query="", limit=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_delete_conversation(self, store):
        """Test deleting conversation"""
        await store.record_conversation(thread_id="test", user_id="user:alice", message_count=5)

        # Delete
        deleted = await store.delete_conversation("test")
        assert deleted is True

        # Verify deleted
        metadata = await store.get_conversation("test")
        assert metadata is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, store):
        """Test deleting nonexistent conversation"""
        deleted = await store.delete_conversation("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_stats(self, store):
        """Test getting store statistics"""
        await store.record_conversation(thread_id="conv1", user_id="user:alice", message_count=5)
        await store.record_conversation(thread_id="conv2", user_id="user:bob", message_count=3)

        stats = await store.get_stats()
        assert stats["backend"] == "memory"
        assert stats["conversation_count"] == 2

    @pytest.mark.asyncio
    async def test_search_by_tags(self, store):
        """Test searching conversations by tags"""
        await store.record_conversation(thread_id="tagged", user_id="user:alice", message_count=5, tags=["important", "project"])
        await store.record_conversation(thread_id="untagged", user_id="user:alice", message_count=3)

        results = await store.search_conversations("user:alice", query="important", limit=10)
        assert len(results) == 1
        assert results[0].thread_id == "tagged"


@pytest.mark.unit
class TestConversationMetadata:
    """Test ConversationMetadata dataclass"""

    def test_metadata_creation(self):
        """Test creating metadata"""
        metadata = ConversationMetadata(
            thread_id="test", user_id="user:alice", created_at=1000.0, last_activity=1001.0, message_count=5
        )

        assert metadata.thread_id == "test"
        assert metadata.user_id == "user:alice"
        assert metadata.message_count == 5
        assert metadata.tags == []  # Default empty list

    def test_metadata_with_tags(self):
        """Test metadata with tags"""
        metadata = ConversationMetadata(
            thread_id="test",
            user_id="user:alice",
            created_at=1000.0,
            last_activity=1001.0,
            message_count=5,
            tags=["tag1", "tag2"],
        )

        assert len(metadata.tags) == 2
        assert "tag1" in metadata.tags
