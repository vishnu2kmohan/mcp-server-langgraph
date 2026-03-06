"""
Message Semantic Index Manager.

v8 Phase 1: Dedicated manager for message embeddings used for session similarity.

Uses separate 'message_index' collection to prevent leakage into knowledge-base search.
This addresses Finding 7 from the plan review.

Reference: Message Embedding & Session Lifecycle Plan v8
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from qdrant_client import AsyncQdrantClient


def string_to_qdrant_id(string_id: str) -> str:
    """Convert string ID to Qdrant-compatible UUID format.

    Qdrant requires UUIDs for point IDs. We hash the string ID
    to create a deterministic UUID.

    Args:
        string_id: Original string identifier

    Returns:
        UUID string format for Qdrant
    """
    # Create a deterministic hash from the string ID
    hash_bytes = hashlib.md5(string_id.encode(), usedforsecurity=False).hexdigest()  # noqa: S324
    # Format as UUID: 8-4-4-4-12
    return f"{hash_bytes[:8]}-{hash_bytes[8:12]}-{hash_bytes[12:16]}-{hash_bytes[16:20]}-{hash_bytes[20:32]}"


@dataclass
class MessageIndexEntry:
    """Index entry for conversation message.

    Stores message metadata for semantic similarity search.
    Summary is used for embedding, not full content (context efficiency).
    """

    message_id: str  # Use message_id to match service response
    session_id: str
    user_id: str
    role: str
    summary: str  # < 200 chars for efficient embedding
    embedding: list[float] | None = None
    timestamp: float = 0.0  # Unix timestamp (converted from ISO)
    token_count: int = 0
    archived: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_message_dict(cls, message: dict[str, Any], session_id: str) -> MessageIndexEntry:
        """Create entry from SessionService message response.

        Handles ISO timestamp conversion and token count estimation.

        Args:
            message: Message dict from SessionService
            session_id: Session this message belongs to

        Returns:
            MessageIndexEntry ready for indexing
        """
        # Handle ISO timestamp from service
        timestamp_str = message.get("timestamp", "")
        timestamp: float
        if isinstance(timestamp_str, str) and timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
            except ValueError:
                timestamp = 0.0
        else:
            timestamp = float(timestamp_str) if timestamp_str else 0.0

        content = message.get("content", "")

        return cls(
            message_id=message.get("message_id", ""),
            session_id=session_id,
            user_id=message.get("user_id", ""),
            role=message.get("role", "user"),
            summary=content[:200],  # Truncate for embedding efficiency
            timestamp=timestamp,
            token_count=len(content) // 4,  # Rough estimate
        )

    def to_payload(self) -> dict[str, Any]:
        """Convert to Qdrant payload format.

        Returns:
            Dict suitable for Qdrant point payload
        """
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": self.role,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "token_count": self.token_count,
            "archived": self.archived,
        }


class MessageSemanticIndexManager:
    """Dedicated manager for message embeddings.

    v8 Phase 1: Uses separate 'message_index' collection to prevent leakage
    into knowledge-base search (Finding 7 from plan review).

    Features:
    - Index messages on persistence
    - Search for similar sessions by query
    - Mark sessions as archived (soft filter)
    - Delete session messages on session deletion
    """

    COLLECTION_NAME = "message_index"

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embedder: Embeddings,
        vector_size: int = 768,
    ) -> None:
        """Initialize message semantic index manager.

        Args:
            qdrant_client: Async Qdrant client instance
            embedder: LangChain Embeddings interface
            vector_size: Embedding vector dimension (from settings.embedding_dimensions)
        """
        self._client = qdrant_client
        self._embedder = embedder
        self._vector_size = vector_size

    async def ensure_collection(self) -> None:
        """Create collection if not exists.

        Called during bootstrap to ensure message_index collection is ready.
        """
        from qdrant_client.models import Distance, VectorParams

        try:
            collections = await self._client.get_collections()
            if self.COLLECTION_NAME not in [c.name for c in collections.collections]:
                await self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self._vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.warning(f"Failed to ensure collection {self.COLLECTION_NAME}: {e}")
            raise

    async def index_message(self, entry: MessageIndexEntry) -> None:
        """Index a single message.

        Generates embedding from summary and stores in Qdrant.

        Args:
            entry: MessageIndexEntry to index
        """
        from qdrant_client.models import PointStruct

        try:
            # Generate embedding if not provided
            embedding = entry.embedding
            if embedding is None:
                embedding = await asyncio.to_thread(self._embedder.embed_query, entry.summary)

            payload = entry.to_payload()
            payload["_original_id"] = entry.message_id

            qdrant_id = string_to_qdrant_id(entry.message_id)
            point = PointStruct(id=qdrant_id, vector=embedding, payload=payload)

            await self._client.upsert(collection_name=self.COLLECTION_NAME, points=[point])

            logger.debug(f"Indexed message {entry.message_id} in session {entry.session_id}")
        except Exception as e:
            logger.warning(f"Failed to index message {entry.message_id}: {e}")
            raise

    async def search_similar_sessions(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        min_score: float = 0.6,
        exclude_session_id: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Find sessions similar to query, grouped by session_id.

        Uses vector similarity to find messages matching the query,
        then aggregates by session_id and returns unique sessions.

        Args:
            query: Search query text
            user_id: Filter to user's own sessions
            limit: Maximum number of sessions to return
            min_score: Minimum similarity score threshold
            exclude_session_id: Session to exclude (e.g., current session)
            include_archived: Include archived sessions in results

        Returns:
            List of dicts with session_id and similarity_score
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(self._embedder.embed_query, query)

            # Build filter: user_id + archive status
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            ]
            if not include_archived:
                must_conditions.append(FieldCondition(key="archived", match=MatchValue(value=False)))

            # Exclude specified session and system-owned sessions (Q10)
            must_not_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value="system")),
            ]
            if exclude_session_id:
                must_not_conditions.append(FieldCondition(key="session_id", match=MatchValue(value=exclude_session_id)))

            query_filter = Filter(must=must_conditions, must_not=must_not_conditions)  # type: ignore[arg-type]

            results = await self._client.search(  # type: ignore[attr-defined]
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit * 5,  # Get more results for aggregation
                score_threshold=min_score,
            )

            # Aggregate by session_id (take highest score per session)
            session_scores: dict[str, float] = {}
            for r in results:
                sid = r.payload.get("session_id")
                if sid and (sid not in session_scores or r.score > session_scores[sid]):
                    session_scores[sid] = r.score

            # Sort by score and return top sessions
            sorted_sessions = sorted(session_scores.items(), key=lambda x: x[1], reverse=True)
            return [{"session_id": sid, "similarity_score": score} for sid, score in sorted_sessions[:limit]]
        except Exception as e:
            logger.warning(f"Failed to search similar sessions: {e}")
            return []

    async def delete_session_messages(self, session_id: str) -> None:
        """Delete all message embeddings for a session.

        Called when a session is permanently deleted.

        Args:
            session_id: Session ID to delete messages for
        """
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        try:
            await self._client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=FilterSelector(
                    filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])
                ),
            )
            logger.debug(f"Deleted message embeddings for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to delete session messages {session_id}: {e}")

    async def mark_session_archived(self, session_id: str, archived: bool) -> None:
        """Update archived status for all messages in a session.

        Used when archiving/restoring a session to filter from similarity search.

        Args:
            session_id: Session ID to update
            archived: New archived status
        """
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        try:
            await self._client.set_payload(
                collection_name=self.COLLECTION_NAME,
                payload={"archived": archived},
                points=FilterSelector(
                    filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])
                ),
            )
            logger.debug(f"Marked session {session_id} archived={archived}")
        except Exception as e:
            logger.warning(f"Failed to mark session {session_id} archived: {e}")


__all__ = [
    "MessageIndexEntry",
    "MessageSemanticIndexManager",
    "string_to_qdrant_id",
]
