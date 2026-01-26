"""
Message Embedding Metrics for Observability.

Provides OpenTelemetry metrics for message embedding operations:
- Message embedding success/failure rates
- Embedding latency histogram
- Session lifecycle (archive, restore, delete)
- Similarity search performance

These metrics integrate with the existing observability stack.

Reference: v8 Plan - Phase 5 Message Embedding & Session Similarity
"""

from opentelemetry import metrics

# Get meter from observability stack
meter = metrics.get_meter(__name__)


# ==============================================================================
# Message Embedding Metrics
# ==============================================================================

embedding_message_counter = meter.create_counter(
    name="embedding.message.total",
    description="Total message embedding attempts",
    unit="1",
)

embedding_message_success_counter = meter.create_counter(
    name="embedding.message.success",
    description="Successful message embeddings",
    unit="1",
)

embedding_message_failure_counter = meter.create_counter(
    name="embedding.message.failure",
    description="Failed message embeddings",
    unit="1",
)

embedding_latency_histogram = meter.create_histogram(
    name="embedding.message.latency_ms",
    description="Message embedding latency in milliseconds",
    unit="ms",
)


# ==============================================================================
# Session Lifecycle Metrics
# ==============================================================================

session_archive_counter = meter.create_counter(
    name="embedding.session.archive",
    description="Session archive operations in embedding service",
    unit="1",
)

session_restore_counter = meter.create_counter(
    name="embedding.session.restore",
    description="Session restore operations in embedding service",
    unit="1",
)

session_delete_counter = meter.create_counter(
    name="embedding.session.delete",
    description="Session delete operations in embedding service",
    unit="1",
)


# ==============================================================================
# Similarity Search Metrics
# ==============================================================================

similarity_search_counter = meter.create_counter(
    name="similarity.session.search.total",
    description="Total session similarity search operations",
    unit="1",
)

similarity_search_latency_histogram = meter.create_histogram(
    name="similarity.session.search.latency_ms",
    description="Session similarity search latency in milliseconds",
    unit="ms",
)

similarity_search_results_histogram = meter.create_histogram(
    name="similarity.session.search.results_count",
    description="Number of results returned by similarity search",
    unit="1",
)


# ==============================================================================
# Helper Functions
# ==============================================================================


def record_embedding_attempt(
    session_id: str,
    success: bool,
    latency_ms: float,
    reason: str | None = None,
) -> None:
    """
    Record a message embedding attempt.

    Args:
        session_id: The session the message belongs to.
        success: Whether the embedding was successful.
        latency_ms: Time taken to embed the message in milliseconds.
        reason: Reason for failure (if success=False).
    """
    labels: dict[str, str] = {
        "session_id": session_id[:8],  # Truncate for cardinality control
        "status": "success" if success else "failure",
    }
    if not success and reason:
        labels["reason"] = reason

    embedding_message_counter.add(1, labels)

    if success:
        embedding_message_success_counter.add(1, labels)
        embedding_latency_histogram.record(latency_ms, labels)
    else:
        embedding_message_failure_counter.add(1, labels)


def record_session_archive(session_id: str, success: bool) -> None:
    """
    Record a session archive operation.

    Args:
        session_id: The session being archived.
        success: Whether the operation was successful.
    """
    session_archive_counter.add(
        1,
        {
            "session_id": session_id[:8],
            "status": "success" if success else "failure",
        },
    )


def record_session_restore(session_id: str, success: bool) -> None:
    """
    Record a session restore operation.

    Args:
        session_id: The session being restored.
        success: Whether the operation was successful.
    """
    session_restore_counter.add(
        1,
        {
            "session_id": session_id[:8],
            "status": "success" if success else "failure",
        },
    )


def record_session_delete(session_id: str, success: bool) -> None:
    """
    Record a session delete operation.

    Args:
        session_id: The session being deleted.
        success: Whether the operation was successful.
    """
    session_delete_counter.add(
        1,
        {
            "session_id": session_id[:8],
            "status": "success" if success else "failure",
        },
    )


def record_similarity_search(
    user_id: str,
    results_count: int,
    latency_ms: float,
) -> None:
    """
    Record a session similarity search operation.

    Args:
        user_id: The user performing the search.
        results_count: Number of results returned.
        latency_ms: Time taken for the search in milliseconds.
    """
    labels = {"user_id": user_id[:8]}
    similarity_search_counter.add(1, labels)
    similarity_search_latency_histogram.record(latency_ms, labels)
    similarity_search_results_histogram.record(results_count, labels)
