"""
Tests for Message model sources field and session storage source persistence.

TDD tests to ensure source citations are properly stored and retrieved
from session messages in all storage backends.
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="session_message_sources")
class TestMessageModelSources:
    """Tests for Message model sources field."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_has_sources_field(self) -> None:
        """Message model should have a sources field."""
        from mcp_server_langgraph.storage.session.models import Message

        message = Message(
            message_id="test-123",
            role="assistant",
            content="Test content",
            user_id="test-user-123",  # v8: Required field
        )

        assert hasattr(message, "sources")
        assert message.sources == []

    def test_message_sources_default_empty_list(self) -> None:
        """Message sources should default to an empty list."""
        from mcp_server_langgraph.storage.session.models import Message

        message = Message(
            message_id="msg-1",
            role="assistant",
            content="Hello",
            user_id="test-user-123",  # v8: Required field
        )

        assert message.sources == []
        assert isinstance(message.sources, list)

    def test_message_sources_accepts_source_citations(self) -> None:
        """Message should accept source citation dictionaries."""
        from mcp_server_langgraph.storage.session.models import Message

        sources = [
            {
                "title": "Python Docs",
                "url": "https://docs.python.org",
                "snippet": "Python documentation.",
            },
            {
                "title": "Real Python",
                "url": "https://realpython.com",
                "snippet": "Tutorials.",
                "relevance_score": 0.85,
            },
        ]

        message = Message(
            message_id="msg-2",
            role="assistant",
            content="Here are the search results.",
            user_id="test-user-123",  # v8: Required field
            sources=sources,
        )

        assert len(message.sources) == 2
        assert message.sources[0]["title"] == "Python Docs"
        assert message.sources[1]["relevance_score"] == 0.85

    def test_message_serialization_includes_sources(self) -> None:
        """Message serialization should include sources field."""
        from mcp_server_langgraph.storage.session.models import Message

        sources = [{"title": "Test", "url": "https://example.com"}]

        message = Message(
            message_id="msg-3",
            role="assistant",
            content="Content",
            user_id="test-user-123",  # v8: Required field
            sources=sources,
        )

        data = message.model_dump()

        assert "sources" in data
        assert data["sources"] == sources


@pytest.mark.xdist_group(name="session_message_sources")
class TestInMemorySessionStorageSources:
    """Tests for InMemorySessionService source persistence."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_add_message_stores_sources(self) -> None:
        """add_message should store sources in the message."""
        from mcp_server_langgraph.api.v1.sessions import InMemorySessionService

        service = InMemorySessionService()
        user_id = "user-1"

        # Create a session
        session = await service.create_session({"name": "Test Session"}, user_id=user_id)
        session_id = session["id"]

        # Add a message with sources
        sources = [
            {"title": "Source 1", "url": "https://source1.com", "snippet": "Snippet 1"},
        ]
        message_data = {
            "role": "assistant",
            "content": "Test response",
            "sources": sources,
        }

        # v8: add_message now requires user_id
        result = await service.add_message(session_id, user_id, message_data)

        assert result is not None
        assert result["sources"] == sources

    @pytest.mark.asyncio
    async def test_get_session_messages_includes_sources(self) -> None:
        """get_session_messages should return messages with sources."""
        from mcp_server_langgraph.api.v1.sessions import InMemorySessionService

        service = InMemorySessionService()
        user_id = "user-1"

        # Create session and add message with sources
        session = await service.create_session({"name": "Test"}, user_id=user_id)
        session_id = session["id"]

        sources = [{"title": "Test", "url": "https://test.com"}]
        # v8: add_message now requires user_id
        await service.add_message(session_id, user_id, {"role": "assistant", "content": "Response", "sources": sources})

        # Get messages - v8: now requires user_id
        messages = await service.get_session_messages(session_id, user_id)

        assert messages is not None
        assert len(messages) == 1
        assert messages[0]["sources"] == sources

    @pytest.mark.asyncio
    async def test_add_message_without_sources(self) -> None:
        """add_message should handle messages without sources."""
        from mcp_server_langgraph.api.v1.sessions import InMemorySessionService

        service = InMemorySessionService()
        user_id = "user-1"

        session = await service.create_session({"name": "Test"}, user_id=user_id)
        session_id = session["id"]

        # Add message without sources - v8: add_message now requires user_id
        result = await service.add_message(session_id, user_id, {"role": "user", "content": "Hello"})

        assert result is not None
        assert result["sources"] == []


@pytest.mark.xdist_group(name="session_message_sources")
class TestRedisSessionManagerSources:
    """Tests for Redis session manager source persistence."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_add_message_signature_accepts_sources(self) -> None:
        """Redis manager add_message should accept sources parameter."""
        import inspect

        from mcp_server_langgraph.storage.session.manager import RedisSessionManager

        sig = inspect.signature(RedisSessionManager.add_message)
        params = list(sig.parameters.keys())

        assert "sources" in params

    def test_add_message_sources_default_none(self) -> None:
        """sources parameter should default to None."""
        import inspect

        from mcp_server_langgraph.storage.session.manager import RedisSessionManager

        sig = inspect.signature(RedisSessionManager.add_message)
        sources_param = sig.parameters.get("sources")

        assert sources_param is not None
        assert sources_param.default is None


@pytest.mark.xdist_group(name="session_message_sources")
class TestPostgresSessionManagerSources:
    """Tests for Postgres session manager source persistence."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_add_message_signature_accepts_sources(self) -> None:
        """Postgres manager add_message should accept sources parameter."""
        import inspect

        from mcp_server_langgraph.storage.session.postgres_manager import (
            PostgresSessionManager,
        )

        sig = inspect.signature(PostgresSessionManager.add_message)
        params = list(sig.parameters.keys())

        assert "sources" in params

    def test_model_to_message_extracts_sources_from_metadata(self) -> None:
        """_model_to_message should extract sources from metadata_json."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.storage.session.postgres_manager import (
            PostgresSessionManager,
        )

        # Create mock message model
        mock_model = MagicMock()
        mock_model.id = "msg-123"
        mock_model.role = "assistant"
        mock_model.content = "Test content"
        mock_model.user_id = "test-user-123"  # v8: Must be string, not MagicMock
        mock_model.timestamp = datetime.now(UTC)
        mock_model.metadata_json = {
            "sources": [{"title": "Test", "url": "https://test.com"}],
            "other_field": "value",
        }

        # Create manager with mock session maker
        manager = PostgresSessionManager.__new__(PostgresSessionManager)

        # Call the method
        message = manager._model_to_message(mock_model)

        assert message.sources == [{"title": "Test", "url": "https://test.com"}]
        assert message.user_id == "test-user-123"

    def test_model_to_message_handles_empty_metadata(self) -> None:
        """_model_to_message should handle empty metadata gracefully."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.storage.session.postgres_manager import (
            PostgresSessionManager,
        )

        mock_model = MagicMock()
        mock_model.id = "msg-456"
        mock_model.role = "user"
        mock_model.content = "Hello"
        mock_model.user_id = "test-user-123"  # v8: Must be string, not MagicMock
        mock_model.timestamp = datetime.now(UTC)
        mock_model.metadata_json = {}

        manager = PostgresSessionManager.__new__(PostgresSessionManager)
        message = manager._model_to_message(mock_model)

        assert message.sources == []
        assert message.metadata == {}
        assert message.user_id == "test-user-123"
