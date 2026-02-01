"""
Message Embedding Service.

v8 Phase 1: Service for embedding messages on persistence for session similarity.

This service is called by SessionService.add_message() to asynchronously
embed messages for later similarity search.

Reference: Message Embedding & Session Lifecycle Plan v8, Task 1.5
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.services.embedding_metrics import (
    record_embedding_attempt,
    record_session_archive,
    record_session_delete,
    record_session_restore,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.core.message_semantic_index import (
        MessageSemanticIndexManager,
    )


class MessageSummarizer:
    """Context-efficient summarization for embedding.

    Creates brief summaries of messages for embedding.
    Keeps embeddings focused on key content.

    v8 Task 1.4: MessageSummarizer with BaseMessage Conversion
    """

    MAX_SUMMARY_LENGTH = 200

    @staticmethod
    def summarize_for_embedding(content: str, role: str) -> str:
        """Create brief summary for embedding.

        For now, uses simple truncation. Could be enhanced with
        LLM-based summarization for longer messages.

        Args:
            content: Full message content
            role: Message role (user, assistant, system)

        Returns:
            Truncated summary for embedding
        """
        if len(content) <= MessageSummarizer.MAX_SUMMARY_LENGTH:
            return content

        # Simple truncation with ellipsis
        return content[: MessageSummarizer.MAX_SUMMARY_LENGTH - 3] + "..."


class MessageEmbeddingService:
    """Service for embedding messages on persistence.

    Called asynchronously after message persistence to embed messages
    for session similarity search.

    v8 Phase 1: Fire-and-forget embedding with fail-open semantics.
    """

    def __init__(
        self,
        message_index_manager: MessageSemanticIndexManager | None,
        enabled: bool = True,
    ) -> None:
        """Initialize message embedding service.

        Args:
            message_index_manager: Manager for message embeddings (may be None if disabled)
            enabled: Whether embedding is enabled
        """
        self._manager = message_index_manager
        self._enabled = enabled and message_index_manager is not None
        self._summarizer = MessageSummarizer()

    @property
    def is_enabled(self) -> bool:
        """Check if embedding is enabled."""
        return self._enabled

    async def on_message_persisted(
        self,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Embed message after persistence.

        Called by SessionService.add_message() after successful persistence.
        Runs asynchronously and fails open (logs warning, doesn't raise).

        Args:
            session_id: Session the message belongs to
            message: Message dict with message_id, user_id, role, content, etc.
        """
        if not self._enabled:
            return

        start_time = time.perf_counter()
        try:
            from mcp_server_langgraph.core.message_semantic_index import (
                MessageIndexEntry,
            )

            # user_id must be in message payload (added by v8 Phase 0)
            user_id = message.get("user_id", "")
            if not user_id:
                logger.warning(f"Message missing user_id, skipping embedding: {session_id}")
                record_embedding_attempt(
                    session_id=session_id,
                    success=False,
                    latency_ms=0,
                    reason="missing_user_id",
                )
                return

            # Create summary for embedding
            content = message.get("content", "")
            role = message.get("role", "user")
            summary = self._summarizer.summarize_for_embedding(content, role)

            # Create index entry
            entry = MessageIndexEntry.from_message_dict(message, session_id)
            entry.summary = summary

            # Index the message
            await self._manager.index_message(entry)  # type: ignore[union-attr]

            latency_ms = (time.perf_counter() - start_time) * 1000
            record_embedding_attempt(
                session_id=session_id,
                success=True,
                latency_ms=latency_ms,
            )

            logger.debug(f"Embedded message {message.get('message_id')} for session {session_id}")
        except Exception as e:
            # Fail open - log warning but don't raise
            latency_ms = (time.perf_counter() - start_time) * 1000
            record_embedding_attempt(
                session_id=session_id,
                success=False,
                latency_ms=latency_ms,
                reason=type(e).__name__,
            )
            logger.warning(f"Failed to embed message for session {session_id}: {e}")

    async def on_session_archived(self, session_id: str) -> None:
        """Mark all session messages as archived.

        Called when a session is archived. Updates embeddings to be
        excluded from similarity search by default.

        Args:
            session_id: Session being archived
        """
        if not self._enabled or self._manager is None:
            return

        try:
            await self._manager.mark_session_archived(session_id, archived=True)
            record_session_archive(session_id, success=True)
            logger.debug(f"Marked session {session_id} embeddings as archived")
        except Exception as e:
            record_session_archive(session_id, success=False)
            logger.warning(f"Failed to mark session {session_id} as archived: {e}")

    async def on_session_restored(self, session_id: str) -> None:
        """Mark all session messages as not archived.

        Called when a session is restored from archive.

        Args:
            session_id: Session being restored
        """
        if not self._enabled or self._manager is None:
            return

        try:
            await self._manager.mark_session_archived(session_id, archived=False)
            record_session_restore(session_id, success=True)
            logger.debug(f"Marked session {session_id} embeddings as restored")
        except Exception as e:
            record_session_restore(session_id, success=False)
            logger.warning(f"Failed to mark session {session_id} as restored: {e}")

    async def on_session_deleted(self, session_id: str) -> None:
        """Delete all session message embeddings.

        Called when a session is permanently deleted.

        Args:
            session_id: Session being deleted
        """
        if not self._enabled or self._manager is None:
            return

        try:
            await self._manager.delete_session_messages(session_id)
            record_session_delete(session_id, success=True)
            logger.debug(f"Deleted session {session_id} embeddings")
        except Exception as e:
            record_session_delete(session_id, success=False)
            logger.warning(f"Failed to delete session {session_id} embeddings: {e}")


__all__ = [
    "MessageEmbeddingService",
    "MessageSummarizer",
]
