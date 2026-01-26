"""
Tests for message persistence during streaming.

TDD: These tests verify that the streaming endpoint persists both
user messages (before streaming) and assistant messages (after streaming)
to the session repository.

This ensures conversation history is properly tracked on the backend,
regardless of what the frontend sends.

Architecture Note:
- Persistence happens at the ROUTER level (create_stream endpoint)
- History loading happens at the SERVICE level (ChatServiceImpl.create_stream)
- Both use the same storage backend (get_session_repository())
- Progressive loading/compaction only affects what's sent to LLM, not what's stored
"""

from __future__ import annotations

import gc
import json
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.chat]


@pytest.fixture
def mock_session_repository() -> AsyncMock:
    """Create a mock session repository that tracks add_message calls."""
    repo = AsyncMock(return_value=None)
    repo.persisted_messages: list[dict[str, Any]] = []

    async def track_add_message(session_id: str, message: dict[str, Any]) -> None:
        repo.persisted_messages.append({"session_id": session_id, **message})

    repo.add_message = AsyncMock(side_effect=track_add_message)
    repo.get_messages = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_chat_service() -> MagicMock:
    """Create a mock chat service that yields streaming content."""
    service = MagicMock()

    async def mock_create_stream(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        yield {"delta": {"content": "Hello"}}
        yield {"delta": {"content": " world"}}
        yield {"delta": {"content": "!"}}

    service.create_stream = mock_create_stream
    return service


@pytest.mark.xdist_group(name="chat_message_persistence")
class TestStreamingMessagePersistence:
    """Tests for message persistence during the streaming flow.

    These tests verify behavior at the ROUTER level where persistence
    actually happens (create_stream endpoint in chat.py).

    Note: The router endpoint has multiple dependencies (auth, OpenFGA, audit).
    We test the core persistence logic by mocking the dependencies.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_user_message_persisted_during_streaming(
        self,
        mock_session_repository: AsyncMock,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        GIVEN a streaming chat request with a user message
        WHEN the streaming endpoint processes the request
        THEN the user message should be persisted to the session repository.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        request = ChatCompletionRequest(
            session_id="test-session-123",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
        )

        # Mock dependencies
        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=mock_chat_service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )

            # Consume the streaming response
            content_chunks = []
            async for chunk in response.body_iterator:
                chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                if chunk_str.startswith("data: "):
                    try:
                        data = json.loads(chunk_str[6:])
                        if "delta" in data and "content" in data["delta"]:
                            content_chunks.append(data["delta"]["content"])
                    except json.JSONDecodeError:
                        pass

        # Verify user message was persisted
        user_messages = [
            m for m in mock_session_repository.persisted_messages if m["role"] == "user"
        ]
        assert len(user_messages) == 1, (
            f"Expected 1 user message persisted, got {len(user_messages)}"
        )
        assert user_messages[0]["content"] == "Hello, how are you?"
        assert user_messages[0]["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_assistant_message_persisted_after_streaming(
        self,
        mock_session_repository: AsyncMock,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        GIVEN a streaming chat request
        WHEN streaming completes successfully
        THEN the accumulated assistant response should be persisted.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        request = ChatCompletionRequest(
            session_id="test-session-456",
            messages=[{"role": "user", "content": "Hi"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=mock_chat_service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )

            # Consume the streaming response
            async for _ in response.body_iterator:
                pass

        # Verify assistant message was persisted with accumulated content
        assistant_messages = [
            m
            for m in mock_session_repository.persisted_messages
            if m["role"] == "assistant"
        ]
        assert len(assistant_messages) == 1, (
            f"Expected 1 assistant message, got {len(assistant_messages)}"
        )
        assert assistant_messages[0]["content"] == "Hello world!", (
            f"Expected accumulated content 'Hello world!', "
            f"got '{assistant_messages[0]['content']}'"
        )

    @pytest.mark.asyncio
    async def test_both_messages_persisted_in_correct_order(
        self,
        mock_session_repository: AsyncMock,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        GIVEN a streaming chat request
        WHEN the full request-response cycle completes
        THEN both user and assistant messages should be persisted.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        request = ChatCompletionRequest(
            session_id="test-session-789",
            messages=[{"role": "user", "content": "What is 2+2?"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=mock_chat_service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        # Verify both messages were persisted
        roles = [m["role"] for m in mock_session_repository.persisted_messages]
        assert "user" in roles, "User message should be persisted"
        assert "assistant" in roles, "Assistant message should be persisted"

        # Verify order: user first, then assistant
        user_idx = roles.index("user")
        assistant_idx = roles.index("assistant")
        assert user_idx < assistant_idx, (
            "User message should be persisted before assistant message"
        )

    @pytest.mark.asyncio
    async def test_sources_persisted_with_assistant_message(
        self,
        mock_session_repository: AsyncMock,
    ) -> None:
        """
        GIVEN a streaming response that includes sources
        WHEN the response is persisted
        THEN sources should be included in the persisted message.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        # Create mock service that yields sources
        service = MagicMock()

        async def mock_stream_with_sources(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"delta": {"content": "Based on the docs..."}}
            yield {
                "sources": [
                    {"title": "API Docs", "url": "https://example.com/docs"},
                    {"title": "Guide", "url": "https://example.com/guide"},
                ]
            }

        service.create_stream = mock_stream_with_sources

        request = ChatCompletionRequest(
            session_id="test-sources",
            messages=[{"role": "user", "content": "What does the API do?"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        # Verify sources were persisted
        assistant_msg = next(
            (
                m
                for m in mock_session_repository.persisted_messages
                if m["role"] == "assistant"
            ),
            None,
        )
        assert assistant_msg is not None
        assert "sources" in assistant_msg, "Sources should be persisted"
        assert len(assistant_msg["sources"]) == 2
        assert assistant_msg["sources"][0]["title"] == "API Docs"

    @pytest.mark.asyncio
    async def test_persistence_failure_does_not_break_streaming(
        self,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        GIVEN a streaming chat request
        WHEN message persistence fails
        THEN streaming should continue without error.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        # Create mock repository that raises exceptions
        failing_repo = AsyncMock(return_value=None)
        failing_repo.add_message = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        request = ChatCompletionRequest(
            session_id="test-failure",
            messages=[{"role": "user", "content": "Hi"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=failing_repo,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=mock_chat_service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            # Should not raise despite persistence failures
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )

            streamed_content = []
            async for chunk in response.body_iterator:
                chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                if chunk_str.startswith("data: "):
                    try:
                        data = json.loads(chunk_str[6:])
                        if "delta" in data and "content" in data["delta"]:
                            streamed_content.append(data["delta"]["content"])
                    except json.JSONDecodeError:
                        pass

        # Verify streaming completed successfully
        assert streamed_content == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_no_persistence_when_repository_is_none(
        self,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        GIVEN a streaming chat request with no session repository configured
        WHEN streaming completes
        THEN no persistence errors should occur.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        request = ChatCompletionRequest(
            session_id="test-no-repo",
            messages=[{"role": "user", "content": "Hi"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=None,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=mock_chat_service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            # Should complete without error
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )

            streamed_content = []
            async for chunk in response.body_iterator:
                chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                if chunk_str.startswith("data: "):
                    try:
                        data = json.loads(chunk_str[6:])
                        if "delta" in data and "content" in data["delta"]:
                            streamed_content.append(data["delta"]["content"])
                    except json.JSONDecodeError:
                        pass

        # Verify streaming completed
        assert streamed_content == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_empty_response_not_persisted(
        self,
        mock_session_repository: AsyncMock,
    ) -> None:
        """
        GIVEN a streaming response with no content
        WHEN streaming completes
        THEN no assistant message should be persisted.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        # Create mock service that yields no content
        service = MagicMock()

        async def mock_empty_stream(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"delta": {}}
            yield {"status": "complete"}

        service.create_stream = mock_empty_stream

        request = ChatCompletionRequest(
            session_id="test-empty",
            messages=[{"role": "user", "content": "Hi"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        # User message should be persisted, but not empty assistant message
        roles = [m["role"] for m in mock_session_repository.persisted_messages]
        assert "user" in roles, "User message should still be persisted"
        assert "assistant" not in roles, "Empty assistant message should not be persisted"


@pytest.mark.xdist_group(name="chat_message_persistence")
class TestPersistenceAndProgressiveLoadingCompatibility:
    """Tests verifying persistence works correctly with progressive loading.

    Key insight: Storage keeps FULL messages, progressive loading only
    truncates IN-MEMORY before sending to LLM.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_deduplication_prevents_duplicate_persistence(self) -> None:
        """
        GIVEN a message that already exists in history
        WHEN the same message is sent again
        THEN it should not create duplicate entries when loaded.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock storage with existing message
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        )

        captured_messages: list[dict[str, Any]] = []

        async def mock_stream(session_id: str, messages: list[dict[str, Any]], **kwargs: Any):
            captured_messages.extend(messages)
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None
        service._llm_factory = MagicMock()

        # Send the same "Hello" message again
        new_message = [{"role": "user", "content": "Hello"}]

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=new_message,
            ):
                pass

        # Verify deduplication: should NOT have duplicate "Hello"
        user_hellos = [m for m in captured_messages if m["role"] == "user" and m["content"] == "Hello"]
        assert len(user_hellos) == 1, (
            f"Expected 1 'Hello' message (deduplicated), got {len(user_hellos)}"
        )

    @pytest.mark.asyncio
    async def test_history_loading_does_not_affect_storage(self) -> None:
        """
        GIVEN stored history that is loaded for LLM context
        WHEN progressive loading truncates old messages
        THEN the original storage should remain unchanged.

        This verifies that truncation is IN-MEMORY only.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock storage with history
        original_messages = [
            {"role": "user", "content": f"Message {i}"} for i in range(10)
        ]
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(return_value=original_messages.copy())

        async def mock_stream(session_id: str, messages: list[dict[str, Any]], **kwargs: Any):
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None
        service._llm_factory = MagicMock()

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=[{"role": "user", "content": "New message"}],
            ):
                pass

        # Verify storage was NOT modified (only read)
        # get_messages was called but add_message was not called on the storage
        mock_storage.get_messages.assert_called()
        # Storage should not have been modified during history loading
        assert len(original_messages) == 10, "Original storage should remain unchanged"


@pytest.mark.xdist_group(name="chat_message_persistence")
class TestThinkingContentPersistence:
    """Tests for thinking content persistence with dual-write pattern.

    v8 Q11: Full thinking content should be persisted during streaming.
    v8 Q18: Dual-write - both thinking object AND legacy fields.
    v8 Finding 54: Use "tokens" not "budget_tokens".
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_thinking_content_persisted_as_object(
        self,
        mock_session_repository: AsyncMock,
    ) -> None:
        """
        GIVEN a streaming response with thinking content
        WHEN the response is persisted
        THEN thinking should be stored as an object with content and tokens.

        v8 Q14: Thinking as object for cleaner structure.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        # Create mock service that yields thinking content
        service = MagicMock()

        async def mock_stream_with_thinking(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"delta": {"thinking": {"content": "Let me analyze this..."}}}
            yield {"delta": {"thinking": {"content": " The key insight is..."}}}
            yield {"delta": {"thinking": {"tokens": 150}}}  # Token count at end
            yield {"delta": {"content": "Here is my response."}}

        service.create_stream = mock_stream_with_thinking

        request = ChatCompletionRequest(
            session_id="test-thinking",
            messages=[{"role": "user", "content": "Explain quantum computing"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        # Verify thinking object was persisted
        assistant_msg = next(
            (
                m
                for m in mock_session_repository.persisted_messages
                if m["role"] == "assistant"
            ),
            None,
        )
        assert assistant_msg is not None, "Assistant message should be persisted"
        assert "thinking" in assistant_msg, "Thinking object should be persisted"
        thinking = assistant_msg["thinking"]
        assert isinstance(thinking, dict), "Thinking should be a dict object"
        assert thinking.get("content") == "Let me analyze this... The key insight is..."
        assert thinking.get("tokens") == 150

    @pytest.mark.asyncio
    async def test_thinking_only_object_no_legacy_fields(
        self,
        mock_session_repository: AsyncMock,
    ) -> None:
        """
        GIVEN a streaming response with thinking content
        WHEN the response is persisted
        THEN only the thinking object should be stored, NOT legacy fields.

        Legacy fields (thinking_content, thinking_tokens) have been deprecated.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        service = MagicMock()

        async def mock_stream_with_thinking(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"delta": {"thinking": {"content": "Reasoning step 1..."}}}
            yield {"delta": {"thinking": {"tokens": 200}}}
            yield {"delta": {"content": "Final answer."}}

        service.create_stream = mock_stream_with_thinking

        request = ChatCompletionRequest(
            session_id="test-thinking-object",
            messages=[{"role": "user", "content": "What is 2+2?"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        assistant_msg = next(
            (
                m
                for m in mock_session_repository.persisted_messages
                if m["role"] == "assistant"
            ),
            None,
        )
        assert assistant_msg is not None

        # Only thinking object should be present
        assert "thinking" in assistant_msg
        assert assistant_msg["thinking"]["content"] == "Reasoning step 1..."
        assert assistant_msg["thinking"]["tokens"] == 200

        # Legacy flat fields should NOT be present (deprecated)
        assert "thinking_content" not in assistant_msg
        assert "thinking_tokens" not in assistant_msg

    @pytest.mark.asyncio
    async def test_thinking_uses_tokens_not_budget_tokens(
        self,
        mock_session_repository: AsyncMock,
    ) -> None:
        """
        GIVEN a streaming response with thinking tokens
        WHEN the response is persisted
        THEN the field should be 'tokens' not 'budget_tokens'.

        v8 Finding 54: ThinkingContent uses 'tokens' not 'budget_tokens'.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        service = MagicMock()

        async def mock_stream_with_tokens(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"delta": {"thinking": {"content": "Thinking...", "tokens": 500}}}
            yield {"delta": {"content": "Done."}}

        service.create_stream = mock_stream_with_tokens

        request = ChatCompletionRequest(
            session_id="test-tokens",
            messages=[{"role": "user", "content": "Hello"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        assistant_msg = next(
            (
                m
                for m in mock_session_repository.persisted_messages
                if m["role"] == "assistant"
            ),
            None,
        )
        assert assistant_msg is not None

        # Verify 'tokens' field is used, not 'budget_tokens'
        thinking = assistant_msg.get("thinking", {})
        assert "tokens" in thinking, "Should use 'tokens' field"
        assert "budget_tokens" not in thinking, "Should not use 'budget_tokens' (Finding 54)"
        assert thinking["tokens"] == 500

        # Legacy fields should NOT be present (deprecated)
        assert "thinking_tokens" not in assistant_msg
        assert "thinking_content" not in assistant_msg

    @pytest.mark.asyncio
    async def test_model_name_persisted_with_message(
        self,
        mock_session_repository: AsyncMock,
    ) -> None:
        """
        GIVEN a streaming response with model information
        WHEN the response is persisted
        THEN model_name should be stored in the message.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            create_stream,
        )

        service = MagicMock()

        async def mock_stream_with_model(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"model": "claude-3-opus-20240229"}
            yield {"delta": {"content": "Hello!"}}

        service.create_stream = mock_stream_with_model

        request = ChatCompletionRequest(
            session_id="test-model",
            messages=[{"role": "user", "content": "Hi"}],
        )

        mock_current_user = {"user_id": "user:test", "preferred_username": "test"}
        mock_openfga = AsyncMock(return_value=None)
        mock_audit = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.api.v1.chat.get_session_repository",
                return_value=mock_session_repository,
            ),
            patch(
                "mcp_server_langgraph.api.v1.chat.get_chat_service",
                return_value=service,
            ),
            patch(
                "mcp_server_langgraph.execution.bypass_audit.log_bypass_audit_event",
                new_callable=AsyncMock,
            ),
        ):
            response = await create_stream(
                request=request,
                current_user=mock_current_user,
                openfga_client=mock_openfga,
                audit_service=mock_audit,
            )
            async for _ in response.body_iterator:
                pass

        assistant_msg = next(
            (
                m
                for m in mock_session_repository.persisted_messages
                if m["role"] == "assistant"
            ),
            None,
        )
        assert assistant_msg is not None
        assert "model_name" in assistant_msg
        assert assistant_msg["model_name"] == "claude-3-opus-20240229"
