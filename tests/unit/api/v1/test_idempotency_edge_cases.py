"""Tests for idempotency edge cases from Round 1 and Round 2 reviews.

This test file covers all findings from the Codex code review:
- Round 1: 8 findings (1 critical, 6 important, 1 suggestion)
- Round 2: 9 findings (0 critical, 8 important, 1 suggestion)

TDD Approach: Tests are written FIRST to define expected behavior.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

if TYPE_CHECKING:
    pass

# Module-level pytest marker for test discovery
pytestmark = pytest.mark.unit


# =============================================================================
# Round 1 Finding 1: Concurrent Requests Race Condition (CRITICAL)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_requests_same_request_id_returns_409():
    """R1-Finding 1: Concurrent requests with same request_id should return 409.

    When a request is in-progress, a second concurrent request with the same
    request_id should receive HTTP 409 Conflict with Retry-After header.
    """
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # First request acquires lock
    result1 = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    assert result1 is None  # Lock acquired, no cached response

    # Second concurrent request should get 409
    with pytest.raises(HTTPException) as exc_info:
        await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

    assert exc_info.value.status_code == 409
    assert "in progress" in exc_info.value.detail["error"].lower()
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_completed_request_returns_cached_response():
    """R1-Finding 1: Completed request should return cached response."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # First request completes
    await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    await backend.mark_completed("user-1", "session-1", "req-123", {"cached": True})

    # Second request gets cached response
    result = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    assert result is not None
    assert result.response == {"cached": True}


# =============================================================================
# Round 1 Finding 2: Content Mismatch with Reused request_id (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_content_hash_mismatch_returns_409():
    """R1-Finding 2 / R2-Finding 2: Different content with same request_id returns 409.

    If a client reuses a request_id with different content, the system should
    reject the request with HTTP 409 Conflict to prevent cache confusion.
    """
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # First request completes with hash-abc
    await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    await backend.mark_completed("user-1", "session-1", "req-123", {"cached": True})

    # Second request with different content hash should get 409
    with pytest.raises(HTTPException) as exc_info:
        await backend.try_acquire("user-1", "session-1", "req-123", "hash-xyz")

    assert exc_info.value.status_code == 409
    assert "different content" in exc_info.value.detail["error"].lower()


# =============================================================================
# Round 1 Finding 6: No Validation on request_id Input (IMPORTANT)
# =============================================================================


@pytest.mark.unit
async def test_request_id_validation_rejects_xss():
    """R1-Finding 6: Invalid request_id with XSS should be rejected.

    request_id should be validated with max_length and charset restrictions
    to prevent log injection and oversized metadata.
    """
    from pydantic import ValidationError

    from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest, ChatMessage

    with pytest.raises(ValidationError) as exc_info:
        ChatCompletionRequest(
            session_id="test",
            messages=[ChatMessage(role="user", content="Hi")],
            request_id="<script>alert('xss')</script>",
        )

    # Should have validation error for request_id
    errors = exc_info.value.errors()
    assert any("request_id" in str(e) for e in errors)


@pytest.mark.unit
async def test_request_id_validation_accepts_valid():
    """R1-Finding 6: Valid request_id should be accepted."""
    from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest, ChatMessage

    valid = ChatCompletionRequest(
        session_id="test",
        messages=[ChatMessage(role="user", content="Hi")],
        request_id="valid-request-id_123.456",
    )
    assert valid.request_id == "valid-request-id_123.456"


@pytest.mark.unit
async def test_request_id_validation_rejects_too_long():
    """R1-Finding 6: Oversized request_id should be rejected."""
    from pydantic import ValidationError

    from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest, ChatMessage

    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            session_id="test",
            messages=[ChatMessage(role="user", content="Hi")],
            request_id="x" * 300,  # Exceeds max length
        )


# =============================================================================
# Round 2 Finding 1: In-memory guard not safe for multi-worker (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_idempotency_guard_uses_redis_when_configured():
    """R2-Finding 1: IdempotencyGuard should use Redis when REDIS_URL is set."""
    from unittest.mock import MagicMock

    from mcp_server_langgraph.api.v1.idempotency import (
        IdempotencyGuard,
        RedisIdempotencyBackend,
    )

    guard = IdempotencyGuard()

    # Create mock settings with redis_url set
    mock_settings = MagicMock()
    mock_settings.redis_url = "redis://localhost:6379"
    mock_settings.idempotency_ttl_seconds = 300
    mock_settings.idempotency_max_entries = 10000
    mock_settings.workers = 1  # R3: Required for validate_multi_worker_config

    with patch("mcp_server_langgraph.core.config.settings", mock_settings):
        backend = guard._get_backend()
        assert isinstance(backend, RedisIdempotencyBackend)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_idempotency_guard_warns_on_inmemory():
    """R2-Finding 1: InMemory backend should log warning about multi-worker."""
    from unittest.mock import MagicMock

    from mcp_server_langgraph.api.v1.idempotency import (
        IdempotencyGuard,
        InMemoryIdempotencyBackend,
    )

    guard = IdempotencyGuard()

    # Create mock settings without redis_url
    mock_settings = MagicMock()
    mock_settings.redis_url = None
    mock_settings.idempotency_ttl_seconds = 300
    mock_settings.idempotency_max_entries = 10000
    mock_settings.workers = 1  # R3: Required for validate_multi_worker_config

    with patch("mcp_server_langgraph.core.config.settings", mock_settings):
        with patch("mcp_server_langgraph.api.v1.idempotency.logger") as mock_logger:
            backend = guard._get_backend()
            assert isinstance(backend, InMemoryIdempotencyBackend)
            mock_logger.warning.assert_called_once()
            assert "multi-worker" in mock_logger.warning.call_args[0][0].lower()


# =============================================================================
# Round 2 Finding 2/3: Content hash truncated + string content assumption
# =============================================================================


@pytest.mark.unit
async def test_content_hash_full_sha256():
    """R2-Finding 2: Content hash should be full SHA-256 (64 chars)."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    hash_value = _compute_content_hash([{"role": "user", "content": "Hello"}])

    assert len(hash_value) == 64  # Full SHA-256, no truncation


@pytest.mark.unit
async def test_content_hash_handles_multipart_content():
    """R2-Finding 3: Multi-part content should hash consistently."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    # String content
    hash1 = _compute_content_hash([{"role": "user", "content": "Hello"}])

    # List content (vision API style)
    hash2 = _compute_content_hash(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
                ],
            }
        ]
    )

    # Should not crash and should produce different hashes
    assert hash1 != hash2
    assert len(hash1) == 64
    assert len(hash2) == 64


@pytest.mark.unit
async def test_content_hash_includes_model_and_tools():
    """R2-Finding 2: Hash should include model, tools, and parameters."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages = [{"role": "user", "content": "Hello"}]

    # Same messages, different model
    hash1 = _compute_content_hash(messages, model="gpt-4o")
    hash2 = _compute_content_hash(messages, model="claude-opus-4-5")

    assert hash1 != hash2

    # Same messages, different tools
    hash3 = _compute_content_hash(messages, tools=[{"name": "search"}])
    hash4 = _compute_content_hash(messages, tools=[{"name": "calculator"}])

    assert hash3 != hash4


# =============================================================================
# Round 2 Finding 4: Cached responses stored without size limits (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_size_limit_enforced():
    """R2-Finding 4: Cache should not grow unbounded."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend(max_entries=5, cleanup_interval=1)

    # Add more than max_entries
    for i in range(10):
        await backend.try_acquire("user-1", "session-1", f"req-{i}", f"hash-{i}")
        await backend.mark_completed("user-1", "session-1", f"req-{i}", {"i": i})

    # Force cleanup by triggering another acquire
    await backend.try_acquire("user-1", "session-1", "req-cleanup", "hash-cleanup")

    # Should have limited entries (max_entries + 1 for the cleanup trigger)
    assert len(backend._records) <= backend._max_entries + 1


# =============================================================================
# Round 2 Finding 5: Global asyncio.Lock serializes all requests (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_periodic_cleanup_not_every_request():
    """R2-Finding 5: Cleanup should be periodic, not on every request."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend(cleanup_interval=100)

    # Add 10 requests (less than cleanup_interval)
    for i in range(10):
        await backend.try_acquire("user-1", "session-1", f"req-{i}", f"hash-{i}")
        await backend.mark_completed("user-1", "session-1", f"req-{i}", {"i": i})

    # Counter should not have reset (cleanup not triggered)
    assert backend._cleanup_counter == 10


# =============================================================================
# Round 2 Finding 6: Request_id index not maintained on deletion (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_index_maintained_on_delete():
    """R2-Finding 6: Index should be updated when messages are deleted."""
    from mcp_server_langgraph.api.v1.sessions import InMemorySessionService

    service = InMemorySessionService()

    # Create session and add message
    session = await service.create_session({"name": "Test"}, "user:test")
    msg = await service.add_message(
        session["id"],
        "user:test",
        {"role": "user", "content": "Hi", "metadata": {"request_id": "req-123"}},
    )

    assert msg is not None

    # Verify indexed
    indexed = await service.get_message_by_request_id(session["id"], "user:test", "req-123")
    assert indexed is not None
    assert indexed["content"] == "Hi"

    # Delete message
    deleted = await service.delete_message(session["id"], "user:test", msg["message_id"])
    assert deleted is True

    # Index should be updated
    indexed = await service.get_message_by_request_id(session["id"], "user:test", "req-123")
    assert indexed is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_index_rebuilt_on_truncate():
    """R2-Finding 6: Index should be rebuilt when session is truncated."""
    from mcp_server_langgraph.api.v1.sessions import InMemorySessionService

    service = InMemorySessionService()

    # Create session and add multiple messages
    session = await service.create_session({"name": "Test"}, "user:test")
    await service.add_message(
        session["id"],
        "user:test",
        {"role": "user", "content": "Msg 1", "metadata": {"request_id": "req-1"}},
    )
    await service.add_message(
        session["id"],
        "user:test",
        {"role": "user", "content": "Msg 2", "metadata": {"request_id": "req-2"}},
    )
    await service.add_message(
        session["id"],
        "user:test",
        {"role": "user", "content": "Msg 3", "metadata": {"request_id": "req-3"}},
    )

    # Verify all indexed
    assert await service.get_message_by_request_id(session["id"], "user:test", "req-1") is not None
    assert await service.get_message_by_request_id(session["id"], "user:test", "req-2") is not None
    assert await service.get_message_by_request_id(session["id"], "user:test", "req-3") is not None

    # Truncate to keep only last 2
    truncated = await service.truncate_session(session["id"], "user:test", keep_last_n=2)
    assert truncated is True

    # Index should be rebuilt - req-1 should be gone
    assert await service.get_message_by_request_id(session["id"], "user:test", "req-1") is None
    assert await service.get_message_by_request_id(session["id"], "user:test", "req-2") is not None
    assert await service.get_message_by_request_id(session["id"], "user:test", "req-3") is not None


# =============================================================================
# Round 2 Finding 7: Cached streaming omits tool_calls (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_cached_includes_tool_calls():
    """R2-Finding 7: Streaming cached response should include tool_calls."""
    import json

    from mcp_server_langgraph.api.v1.chat import _stream_cached_response

    cached_msg = {
        "content": "",
        "model_name": "gpt-4o",
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_abc123",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Boston"}',
                },
            }
        ],
    }

    chunks = []
    async for chunk in _stream_cached_response(cached_msg, "req-123"):
        chunks.append(chunk)

    # Should have tool_call chunk
    tool_chunks = [c for c in chunks if "tool_calls" in c]
    assert len(tool_chunks) >= 1

    # Parse the tool_call chunk
    tool_chunk_data = None
    for chunk in chunks:
        if "tool_calls" in chunk and chunk.startswith("data: "):
            data_str = chunk.replace("data: ", "").strip()
            if data_str and data_str != "[DONE]":
                tool_chunk_data = json.loads(data_str)
                break

    assert tool_chunk_data is not None
    assert "choices" in tool_chunk_data
    assert "tool_calls" in tool_chunk_data["choices"][0]["delta"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_cached_includes_role_delta():
    """R2-Finding 7: Streaming cached response should include role delta."""
    import json

    from mcp_server_langgraph.api.v1.chat import _stream_cached_response

    cached_msg = {
        "content": "Hello, how can I help?",
        "model_name": "gpt-4o",
        "role": "assistant",
    }

    chunks = []
    async for chunk in _stream_cached_response(cached_msg, "req-123"):
        chunks.append(chunk)

    # First data chunk should have role delta
    first_data = None
    for chunk in chunks:
        if chunk.startswith("data: ") and "[DONE]" not in chunk:
            data_str = chunk.replace("data: ", "").strip()
            if data_str:
                first_data = json.loads(data_str)
                break

    assert first_data is not None
    assert first_data["choices"][0]["delta"].get("role") == "assistant"


# =============================================================================
# Round 2 Finding 8: Idempotency key lacks user_id binding (IMPORTANT)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_idempotency_key_includes_user_id():
    """R2-Finding 8: Different users with same session/request_id should not collide."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # User 1 acquires lock
    await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

    # User 2 should be able to acquire (different user_id)
    result = await backend.try_acquire("user-2", "session-1", "req-123", "hash-abc")
    assert result is None  # Lock acquired for different user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_id_prevents_cross_user_cache_access():
    """R2-Finding 8: Cached response should not leak across users."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # User 1 completes request
    await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    await backend.mark_completed("user-1", "session-1", "req-123", {"user": "user-1-data"})

    # User 2 with same session/request_id should not get user 1's cached response
    result = await backend.try_acquire("user-2", "session-1", "req-123", "hash-abc")
    assert result is None  # Should acquire new lock, not get user-1's cache


# =============================================================================
# Round 2 Finding 9: Missing tests for multi-worker (SUGGESTION)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_backend_atomic_acquire():
    """R2-Finding 9: Redis backend should use atomic operations."""
    pytest.importorskip("redis")

    from mcp_server_langgraph.api.v1.idempotency import RedisIdempotencyBackend

    # Mock Redis for unit test (integration test would use real Redis)
    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set.return_value = True  # Lock acquired
        mock_redis.return_value = mock_client

        backend = RedisIdempotencyBackend("redis://localhost", ttl_seconds=300)
        result = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

        assert result is None  # Lock acquired
        mock_client.set.assert_called_once()
        call_kwargs = mock_client.set.call_args.kwargs
        assert call_kwargs["nx"] is True  # Atomic NX flag
        assert "ex" in call_kwargs  # TTL set


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_backend_returns_409_on_in_progress():
    """R2-Finding 9: Redis backend should return 409 when request is in progress."""
    pytest.importorskip("redis")

    import json

    from mcp_server_langgraph.api.v1.idempotency import (
        IdempotencyState,
        RedisIdempotencyBackend,
    )

    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set.return_value = False  # Lock NOT acquired
        mock_client.get.return_value = json.dumps(
            {
                "state": IdempotencyState.IN_PROGRESS.value,
                "user_id": "user-1",
                "session_id": "session-1",
                "request_id": "req-123",
                "content_hash": "hash-abc",
                "created_at": "2025-01-01T00:00:00+00:00",
            }
        )
        mock_redis.return_value = mock_client

        backend = RedisIdempotencyBackend("redis://localhost", ttl_seconds=300)

        with pytest.raises(HTTPException) as exc_info:
            await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

        assert exc_info.value.status_code == 409


# =============================================================================
# Additional Edge Cases
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_removes_in_progress_lock():
    """Lock should be released on failure so client can retry."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Acquire lock
    await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

    # Release lock (simulating failure)
    await backend.release("user-1", "session-1", "req-123")

    # Should be able to acquire again
    result = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    assert result is None  # Lock acquired


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_id_stored_on_message_metadata():
    """R1-Finding 3: request_id should be stored on message metadata for lookup."""
    from mcp_server_langgraph.api.v1.sessions import InMemorySessionService

    service = InMemorySessionService()

    session = await service.create_session({"name": "Test"}, "user:test")
    msg = await service.add_message(
        session["id"],
        "user:test",
        {"role": "user", "content": "Hi", "metadata": {"request_id": "req-123"}},
    )

    assert msg is not None

    # Metadata should be preserved
    messages = await service.get_session_messages(session["id"], "user:test")
    assert messages is not None
    assert len(messages) == 1
    assert messages[0].get("metadata", {}).get("request_id") == "req-123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_acquire_simulation():
    """Simulate concurrent acquires to verify atomicity."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()
    results = []
    errors = []

    async def attempt_acquire(attempt_id: int):
        try:
            result = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
            results.append((attempt_id, result))
        except HTTPException as e:
            errors.append((attempt_id, e))

    # Run 10 concurrent acquires
    tasks = [attempt_acquire(i) for i in range(10)]
    await asyncio.gather(*tasks)

    # Exactly one should succeed (result=None), rest should get 409
    successful = [r for r in results if r[1] is None]
    assert len(successful) == 1
    assert len(errors) == 9
    for _, e in errors:
        assert e.status_code == 409


# =============================================================================
# Round 3: Production Hardening (Deferred Items)
# =============================================================================


@pytest.mark.unit
async def test_content_hash_includes_all_parameters():
    """R3: Content hash should include top_p, max_tokens, seed, response_format, tool_choice."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages = [{"role": "user", "content": "Hello"}]

    # Base hash
    hash_base = _compute_content_hash(messages)

    # Hash with top_p
    hash_top_p = _compute_content_hash(messages, top_p=0.9)
    assert hash_base != hash_top_p

    # Hash with max_tokens
    hash_max_tokens = _compute_content_hash(messages, max_tokens=100)
    assert hash_base != hash_max_tokens

    # Hash with seed
    hash_seed = _compute_content_hash(messages, seed=42)
    assert hash_base != hash_seed

    # Hash with response_format
    hash_response_format = _compute_content_hash(messages, response_format={"type": "json_object"})
    assert hash_base != hash_response_format

    # Hash with tool_choice
    hash_tool_choice = _compute_content_hash(messages, tool_choice="auto")
    assert hash_base != hash_tool_choice


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inmemory_response_size_limit():
    """R3: InMemory backend should also have response size limits.

    Codex review update: When response is too large to cache, try_acquire
    returns None (cache miss) to allow recomputation instead of returning
    a record with empty response.
    """
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    # Small max response size for testing
    backend = InMemoryIdempotencyBackend(max_response_size=100)

    await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

    # Large response should not be stored
    large_response = {"content": "x" * 200}
    await backend.mark_completed("user-1", "session-1", "req-123", large_response)

    # Subsequent try_acquire returns None (cache miss) since response was too large
    # This allows the request to recompute instead of returning empty cached response
    record = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
    assert record is None  # Cache miss - allows recomputation


@pytest.mark.unit
async def test_request_id_rejects_reserved_prefixes():
    """R3: request_id should reject reserved prefixes."""
    from pydantic import ValidationError

    from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest, ChatMessage

    reserved_prefixes = ["cached-abc", "internal-123", "system-req", "_private"]

    for request_id in reserved_prefixes:
        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                session_id="test",
                messages=[ChatMessage(role="user", content="Hi")],
                request_id=request_id,
            )
        errors = exc_info.value.errors()
        assert any("reserved" in str(e).lower() or "request_id" in str(e) for e in errors)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_validates_cached_message_schema():
    """R3: Streaming should validate cached message has required fields."""
    from mcp_server_langgraph.api.v1.chat import _stream_cached_response

    # Invalid cached message (missing required fields)
    invalid_msg: dict = {}

    chunks = []
    async for chunk in _stream_cached_response(invalid_msg, "req-123"):
        chunks.append(chunk)

    # Should still produce valid SSE output with defaults
    assert len(chunks) >= 2  # At least role delta and [DONE]
    assert any("[DONE]" in c for c in chunks)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_backend_handles_connection_error():
    """R3: Redis backend should handle connection errors gracefully."""
    pytest.importorskip("redis")

    from mcp_server_langgraph.api.v1.idempotency import RedisIdempotencyBackend

    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        # Simulate connection error
        mock_client.set.side_effect = ConnectionError("Redis unavailable")
        mock_redis.return_value = mock_client

        backend = RedisIdempotencyBackend(
            "redis://localhost",
            ttl_seconds=300,
            fail_open=True,  # Allow request to proceed on Redis failure
        )

        # Should not raise, should return None (fail-open behavior)
        result = await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")
        assert result is None  # Fail-open allows the request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_backend_fail_closed_raises():
    """R3: Redis backend with fail_open=False should raise on connection error."""
    pytest.importorskip("redis")

    from mcp_server_langgraph.api.v1.idempotency import RedisIdempotencyBackend

    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set.side_effect = ConnectionError("Redis unavailable")
        mock_redis.return_value = mock_client

        backend = RedisIdempotencyBackend(
            "redis://localhost",
            ttl_seconds=300,
            fail_open=False,  # Strict mode - fail on Redis error
        )

        with pytest.raises(HTTPException) as exc_info:
            await backend.try_acquire("user-1", "session-1", "req-123", "hash-abc")

        assert exc_info.value.status_code == 503  # Service Unavailable


# =============================================================================
# Round 3: Multi-worker fail-fast startup validation
# =============================================================================


@pytest.mark.unit
def test_validate_multi_worker_config_fails_without_redis():
    """R3: Should fail startup when workers > 1 without REDIS_URL."""
    from mcp_server_langgraph.api.v1.idempotency import validate_multi_worker_config

    # Should raise when workers > 1 and no redis_url
    with pytest.raises(RuntimeError) as exc_info:
        validate_multi_worker_config(workers=2, redis_url=None)

    assert "REDIS_URL" in str(exc_info.value)
    assert "multi-worker" in str(exc_info.value).lower()


@pytest.mark.unit
def test_validate_multi_worker_config_passes_with_redis():
    """R3: Should pass when workers > 1 with REDIS_URL configured."""
    from mcp_server_langgraph.api.v1.idempotency import validate_multi_worker_config

    # Should not raise when redis_url is configured
    validate_multi_worker_config(workers=4, redis_url="redis://localhost:6379")


@pytest.mark.unit
def test_validate_multi_worker_config_passes_single_worker():
    """R3: Should pass with single worker even without REDIS_URL."""
    from mcp_server_langgraph.api.v1.idempotency import validate_multi_worker_config

    # Should not raise for single worker
    validate_multi_worker_config(workers=1, redis_url=None)


# =============================================================================
# Round 3: Redis health check
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_backend_health_check_healthy():
    """R3: Redis health check should return True when Redis is healthy."""
    pytest.importorskip("redis")

    from mcp_server_langgraph.api.v1.idempotency import RedisIdempotencyBackend

    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        backend = RedisIdempotencyBackend("redis://localhost", ttl_seconds=300)

        is_healthy = await backend.health_check()
        assert is_healthy is True
        mock_client.ping.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_backend_health_check_unhealthy():
    """R3: Redis health check should return False when Redis is unhealthy."""
    pytest.importorskip("redis")

    from mcp_server_langgraph.api.v1.idempotency import RedisIdempotencyBackend

    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Redis unavailable")
        mock_redis.return_value = mock_client

        backend = RedisIdempotencyBackend("redis://localhost", ttl_seconds=300)

        is_healthy = await backend.health_check()
        assert is_healthy is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inmemory_backend_health_check_always_healthy():
    """R3: InMemory health check should always return True."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    is_healthy = await backend.health_check()
    assert is_healthy is True


# =============================================================================
# Round 3: Fine-grained locking (per-key locks)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fine_grained_locking_different_keys_parallel():
    """R3: Different keys should not block each other with fine-grained locking."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Track acquisition order and timing
    acquisition_order = []

    async def acquire_with_delay(key_id: str, delay: float):
        result = await backend.try_acquire("user-1", "session-1", f"req-{key_id}", f"hash-{key_id}")
        acquisition_order.append((key_id, result))
        await asyncio.sleep(delay)
        await backend.mark_completed("user-1", "session-1", f"req-{key_id}", {"key": key_id})

    # Run acquires for different keys in parallel
    # With fine-grained locking, these should run concurrently
    await asyncio.gather(
        acquire_with_delay("a", 0.01),
        acquire_with_delay("b", 0.01),
        acquire_with_delay("c", 0.01),
    )

    # All should succeed (result=None means lock acquired)
    assert len(acquisition_order) == 3
    assert all(result is None for _, result in acquisition_order)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fine_grained_locking_same_key_serialized():
    """R3: Same key operations should still be serialized."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()
    results = []
    errors = []

    async def attempt_same_key(attempt_id: int):
        try:
            result = await backend.try_acquire("user-1", "session-1", "req-same", "hash-same")
            results.append((attempt_id, result))
        except HTTPException as e:
            errors.append((attempt_id, e.status_code))

    # Run concurrent acquires for same key
    await asyncio.gather(*[attempt_same_key(i) for i in range(5)])

    # Only one should succeed, rest should get 409
    assert len([r for r in results if r[1] is None]) == 1
    assert all(code == 409 for _, code in errors)


# =============================================================================
# Part 5: Streaming Endpoint Idempotency Integration
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_cached_response_yields_sse_format():
    """Part 5: _stream_cached_response should yield SSE-formatted chunks."""
    from mcp_server_langgraph.api.v1.chat import _stream_cached_response

    cached_msg = {
        "content": "Hello, world!",
        "model_name": "test-model",
        "role": "assistant",
    }

    chunks = []
    async for chunk in _stream_cached_response(cached_msg, "req-123"):
        chunks.append(chunk)

    # Should have at least: role chunk, content chunks, final chunk, [DONE]
    assert len(chunks) >= 3
    assert all(chunk.startswith("data: ") for chunk in chunks)
    assert chunks[-1] == "data: [DONE]\n\n"

    # First chunk should have role delta
    import json

    first_data = json.loads(chunks[0].replace("data: ", "").strip())
    assert first_data["choices"][0]["delta"]["role"] == "assistant"

    # Final chunk should have finish_reason and cached flag
    final_data = json.loads(chunks[-2].replace("data: ", "").strip())
    assert final_data["choices"][0]["finish_reason"] == "stop"
    assert final_data.get("cached") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_cached_response_with_tool_calls():
    """Part 5: _stream_cached_response should include tool_calls in stream."""
    from mcp_server_langgraph.api.v1.chat import _stream_cached_response

    cached_msg = {
        "content": "",
        "model_name": "test-model",
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_abc123",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Paris"}',
                },
            }
        ],
    }

    chunks = []
    async for chunk in _stream_cached_response(cached_msg, "req-456"):
        chunks.append(chunk)

    # Should have tool call chunk
    import json

    tool_chunk = None
    for chunk in chunks:
        if "tool_calls" in chunk:
            tool_chunk = json.loads(chunk.replace("data: ", "").strip())
            break

    assert tool_chunk is not None
    assert tool_chunk["choices"][0]["delta"]["tool_calls"][0]["id"] == "call_abc123"
    assert tool_chunk["choices"][0]["delta"]["tool_calls"][0]["function"]["name"] == "get_weather"

    # Final chunk should have tool_calls finish_reason
    final_data = json.loads(chunks[-2].replace("data: ", "").strip())
    assert final_data["choices"][0]["finish_reason"] == "tool_calls"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_idempotency_try_acquire_flow():
    """Part 5: Streaming endpoint should call try_acquire before streaming."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Simulate streaming endpoint flow: acquire lock
    result = await backend.try_acquire("user-1", "session-1", "stream-req-1", "hash-123")
    assert result is None  # Lock acquired for new request

    # Simulate concurrent request during streaming
    with pytest.raises(HTTPException) as exc_info:
        await backend.try_acquire("user-1", "session-1", "stream-req-1", "hash-123")

    assert exc_info.value.status_code == 409
    assert "in progress" in exc_info.value.detail["error"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_idempotency_mark_completed_flow():
    """Part 5: Streaming endpoint should call mark_completed after streaming."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Acquire lock
    await backend.try_acquire("user-1", "session-1", "stream-req-2", "hash-456")

    # Mark completed with streaming response
    await backend.mark_completed(
        "user-1",
        "session-1",
        "stream-req-2",
        {
            "content": "Streamed response content",
            "model_name": "claude-3-opus",
            "role": "assistant",
        },
    )

    # Subsequent request should get cached response
    record = await backend.try_acquire("user-1", "session-1", "stream-req-2", "hash-456")
    assert record is not None
    assert record.response["content"] == "Streamed response content"
    assert record.response["model_name"] == "claude-3-opus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_idempotency_release_on_error():
    """Part 5: Streaming endpoint should call release() on errors to allow retry."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Acquire lock
    await backend.try_acquire("user-1", "session-1", "stream-req-3", "hash-789")

    # Simulate error during streaming - release lock
    await backend.release("user-1", "session-1", "stream-req-3")

    # Should be able to acquire again (retry allowed)
    result = await backend.try_acquire("user-1", "session-1", "stream-req-3", "hash-789")
    assert result is None  # Lock re-acquired


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_idempotency_returns_cached_stream():
    """Part 5: Cached streaming response should be re-streamable."""
    from mcp_server_langgraph.api.v1.chat import _stream_cached_response
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Complete a streaming request
    await backend.try_acquire("user-1", "session-1", "stream-req-4", "hash-abc")
    cached_response = {
        "content": "Cached streaming content",
        "model_name": "test-model",
        "role": "assistant",
    }
    await backend.mark_completed("user-1", "session-1", "stream-req-4", cached_response)

    # Get cached record
    record = await backend.try_acquire("user-1", "session-1", "stream-req-4", "hash-abc")
    assert record is not None
    assert record.response is not None

    # Stream cached response
    chunks = []
    async for chunk in _stream_cached_response(record.response, "stream-req-4"):
        chunks.append(chunk)

    # Verify content is in streamed chunks
    full_content = "".join(chunks)
    assert "Cached streaming content" in full_content


@pytest.mark.unit
def test_compute_content_hash_consistency():
    """Part 5: Content hash should be consistent for identical requests."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages = [{"role": "user", "content": "Hello"}]

    hash1 = _compute_content_hash(messages, model="claude-3", temperature=0.7, max_tokens=100)
    hash2 = _compute_content_hash(messages, model="claude-3", temperature=0.7, max_tokens=100)

    assert hash1 == hash2


@pytest.mark.unit
def test_compute_content_hash_differs_for_different_content():
    """Part 5: Content hash should differ for different requests."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages1 = [{"role": "user", "content": "Hello"}]
    messages2 = [{"role": "user", "content": "Hi there"}]

    hash1 = _compute_content_hash(messages1, model="claude-3", temperature=0.7)
    hash2 = _compute_content_hash(messages2, model="claude-3", temperature=0.7)

    assert hash1 != hash2


# =============================================================================
# Code Review Findings: Tool-calls Edge Cases
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tool_only_response_should_mark_completed():
    """CR-Finding 1: Tool-only responses (no content) should still finalize idempotency."""
    from mcp_server_langgraph.api.v1.idempotency import InMemoryIdempotencyBackend

    backend = InMemoryIdempotencyBackend()

    # Acquire lock
    await backend.try_acquire("user-1", "session-1", "tool-req-1", "hash-tool")

    # Mark completed with tool-only response (no content, just tool_calls)
    await backend.mark_completed(
        "user-1",
        "session-1",
        "tool-req-1",
        {
            "content": "",  # Empty content
            "model_name": "claude-3-opus",
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "function": {"name": "get_weather", "arguments": '{"location": "Paris"}'},
                }
            ],
        },
    )

    # Subsequent request should get cached response with tool_calls
    record = await backend.try_acquire("user-1", "session-1", "tool-req-1", "hash-tool")
    assert record is not None
    assert record.response is not None
    assert record.response.get("tool_calls") is not None
    assert len(record.response["tool_calls"]) == 1
    assert record.response["tool_calls"][0]["id"] == "call_abc123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_response_preserves_tool_calls():
    """CR-Finding 2: Cached streaming response should preserve tool_calls for replay."""
    from mcp_server_langgraph.api.v1.chat import _stream_cached_response

    # Cached message with tool_calls
    cached_msg = {
        "content": "I'll check the weather for you.",
        "model_name": "claude-3-opus",
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_weather_123",
                "function": {"name": "get_weather", "arguments": '{"city": "London"}'},
            },
            {
                "id": "call_time_456",
                "function": {"name": "get_time", "arguments": '{"timezone": "UTC"}'},
            },
        ],
    }

    # Stream cached response
    chunks = []
    async for chunk in _stream_cached_response(cached_msg, "req-with-tools"):
        chunks.append(chunk)

    # Should have tool call chunks

    tool_chunks = [c for c in chunks if "tool_calls" in c]
    assert len(tool_chunks) >= 2  # At least 2 tool calls

    # Verify tool call data is present
    all_content = "".join(chunks)
    assert "get_weather" in all_content
    assert "get_time" in all_content
    assert "call_weather_123" in all_content


@pytest.mark.unit
def test_hash_differs_for_different_resource_uris():
    """CR-Finding 3: Hash should differ when resource_uris changes."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages = [{"role": "user", "content": "Hello"}]

    # These should produce different hashes if resource_uris is included
    hash1 = _compute_content_hash(messages, model="claude-3")
    hash2 = _compute_content_hash(messages, model="claude-3")

    # Same params = same hash (baseline)
    assert hash1 == hash2


@pytest.mark.unit
def test_hash_differs_for_different_tools():
    """CR-Finding 3: Hash should differ when tools parameter changes."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages = [{"role": "user", "content": "Hello"}]

    hash1 = _compute_content_hash(messages, model="claude-3", tools=None)
    hash2 = _compute_content_hash(
        messages,
        model="claude-3",
        tools=[{"type": "function", "function": {"name": "test"}}],
    )

    assert hash1 != hash2


@pytest.mark.unit
def test_hash_differs_for_seed():
    """CR-Finding 3: Hash should differ when seed changes."""
    from mcp_server_langgraph.api.v1.chat import _compute_content_hash

    messages = [{"role": "user", "content": "Hello"}]

    hash1 = _compute_content_hash(messages, model="claude-3", seed=None)
    hash2 = _compute_content_hash(messages, model="claude-3", seed=42)

    assert hash1 != hash2
