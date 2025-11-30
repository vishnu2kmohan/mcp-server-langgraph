"""
Lightweight conversation metadata store

Tracks conversation metadata for search functionality without requiring OpenFGA.
Provides a fallback for development environments where OpenFGA isn't running.
"""

import json
import time
from dataclasses import asdict, dataclass

try:
    import redis
    from redis import Redis

    REDIS_AVAILABLE = True
    # Note: types-redis >= 4.6.0.20241115 requires generic parameters
    # Using Redis[str] for decode_responses=True
    RedisType = Redis
except ImportError:
    REDIS_AVAILABLE = False
    RedisType = None  # type: ignore[assignment,misc]


@dataclass
class ConversationMetadata:
    """Metadata for a conversation"""

    thread_id: str
    user_id: str
    created_at: float  # Unix timestamp
    last_activity: float  # Unix timestamp
    message_count: int
    title: str | None = None
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


class ConversationStore:
    """
    Store for conversation metadata.

    Supports both in-memory and Redis backends for flexibility.
    Used as fallback when OpenFGA is not available.
    """

    def __init__(
        self, backend: str = "memory", redis_url: str = "redis://localhost:6379/2", ttl_seconds: int = 604800
    ) -> None:
        """
        Initialize conversation store.

        Args:
            backend: "memory" or "redis"
            redis_url: Redis connection URL (for redis backend)
            ttl_seconds: TTL for conversation metadata (default: 7 days)
        """
        self.backend = backend.lower()
        self.ttl_seconds = ttl_seconds
        self._memory_store: dict[str, ConversationMetadata] = {}
        self._redis_client: Redis[str] | None = None  # type: ignore[type-arg]

        if self.backend == "redis":
            if not REDIS_AVAILABLE:
                msg = "Redis backend requires redis-py. Add 'redis' to pyproject.toml dependencies, then run: uv sync"
                raise ImportError(msg)

            try:
                self._redis_client = redis.from_url(redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
                # Test connection
                self._redis_client.ping()
            except Exception as e:
                msg = f"Failed to connect to Redis at {redis_url}: {e}"
                raise ConnectionError(msg) from e

    def _redis_key(self, thread_id: str) -> str:
        """Generate Redis key for conversation"""
        return f"conversation:metadata:{thread_id}"

    async def record_conversation(
        self,
        thread_id: str,
        user_id: str,
        message_count: int = 1,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """
        Record or update conversation metadata.

        Args:
            thread_id: Conversation thread ID
            user_id: User who owns the conversation
            message_count: Number of messages in conversation
            title: Optional conversation title
            tags: Optional tags for categorization
        """
        now = time.time()

        # Get existing metadata or create new
        existing = await self.get_conversation(thread_id)

        if existing:
            # Update existing
            metadata = existing
            metadata.last_activity = now
            metadata.message_count = message_count
            if title:
                metadata.title = title
            if tags:
                metadata.tags = tags
        else:
            # Create new
            metadata = ConversationMetadata(
                thread_id=thread_id,
                user_id=user_id,
                created_at=now,
                last_activity=now,
                message_count=message_count,
                title=title,
                tags=tags or [],
            )

        # Store based on backend
        if self.backend == "redis" and self._redis_client:
            key = self._redis_key(thread_id)
            data = json.dumps(asdict(metadata))
            self._redis_client.setex(key, self.ttl_seconds, data)
        else:
            self._memory_store[thread_id] = metadata

    async def get_conversation(self, thread_id: str) -> ConversationMetadata | None:
        """
        Get conversation metadata.

        Args:
            thread_id: Conversation thread ID

        Returns:
            ConversationMetadata or None if not found
        """
        if self.backend == "redis" and self._redis_client:
            key = self._redis_key(thread_id)
            data = self._redis_client.get(key)
            if data:
                data_str = data if isinstance(data, str) else (data.decode("utf-8") if hasattr(data, "decode") else str(data))
                return ConversationMetadata(**json.loads(data_str))
            return None
        else:
            return self._memory_store.get(thread_id)

    async def list_user_conversations(self, user_id: str, limit: int = 50) -> list[ConversationMetadata]:
        """
        List all conversations for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return

        Returns:
            List of conversation metadata, sorted by last_activity (descending)
        """
        if self.backend == "redis" and self._redis_client:
            # Scan all conversation keys
            pattern = self._redis_key("*")
            conversations = []

            for key in self._redis_client.scan_iter(match=pattern, count=100):
                data = self._redis_client.get(key)
                if data:
                    data_str = (
                        data if isinstance(data, str) else (data.decode("utf-8") if hasattr(data, "decode") else str(data))
                    )
                    metadata = ConversationMetadata(**json.loads(data_str))
                    if metadata.user_id == user_id:
                        conversations.append(metadata)

            # Sort by last activity
            conversations.sort(key=lambda c: c.last_activity, reverse=True)
            return conversations[:limit]

        else:
            # In-memory: filter and sort
            user_conversations = [c for c in self._memory_store.values() if c.user_id == user_id]
            user_conversations.sort(key=lambda c: c.last_activity, reverse=True)
            return user_conversations[:limit]

    async def search_conversations(self, user_id: str, query: str, limit: int = 10) -> list[ConversationMetadata]:
        """
        Search conversations for a user.

        Args:
            user_id: User identifier
            query: Search query (searches in thread_id and title)
            limit: Maximum number of results

        Returns:
            List of matching conversations, sorted by relevance/recency
        """
        # Get all user conversations
        all_conversations = await self.list_user_conversations(user_id, limit=1000)

        if not query:
            # No query: return most recent
            return all_conversations[:limit]

        # Simple text matching (in production, use proper search index)
        query_lower = query.lower()
        matches = []

        for conv in all_conversations:
            # Search in thread_id and title
            if (
                query_lower in conv.thread_id.lower()
                or (conv.title and query_lower in conv.title.lower())
                or (conv.tags and any(query_lower in tag.lower() for tag in conv.tags))
            ):
                matches.append(conv)

        return matches[:limit]

    async def delete_conversation(self, thread_id: str) -> bool:
        """
        Delete conversation metadata.

        Args:
            thread_id: Conversation thread ID

        Returns:
            True if deleted, False if not found
        """
        if self.backend == "redis" and self._redis_client:
            key = self._redis_key(thread_id)
            deleted = self._redis_client.delete(key)
            return int(deleted) > 0  # type: ignore[arg-type]
        else:
            if thread_id in self._memory_store:
                del self._memory_store[thread_id]
                return True
            return False

    async def get_stats(self) -> dict[str, object]:
        """
        Get store statistics.

        Returns:
            Dictionary with store stats
        """
        if self.backend == "redis" and self._redis_client:
            pattern = self._redis_key("*")
            count = sum(1 for _ in self._redis_client.scan_iter(match=pattern, count=100))
            return {"backend": "redis", "conversation_count": count, "ttl_seconds": self.ttl_seconds}
        else:
            return {"backend": "memory", "conversation_count": len(self._memory_store), "ttl_seconds": None}


# Singleton instance
_conversation_store: ConversationStore | None = None


def get_conversation_store(
    backend: str = "memory", redis_url: str = "redis://localhost:6379/2", ttl_seconds: int = 604800
) -> ConversationStore:
    """
    Get or create the conversation store singleton.

    Args:
        backend: "memory" or "redis"
        redis_url: Redis connection URL
        ttl_seconds: TTL for conversation metadata

    Returns:
        ConversationStore instance
    """
    global _conversation_store

    if _conversation_store is None:
        _conversation_store = ConversationStore(backend=backend, redis_url=redis_url, ttl_seconds=ttl_seconds)

    return _conversation_store
