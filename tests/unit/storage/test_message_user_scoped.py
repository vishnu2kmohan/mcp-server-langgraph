"""
Message User-Scoped Storage Tests

TDD tests for Phase 0: User-scoped message storage and session lifecycle management.
Tests written FIRST before implementation (RED phase).

This test file validates:
- Finding 29: ORM model user_id non-nullable
- Finding 48: metadata_json dict access (no json.loads/dumps)
- Finding 49: Middleware dict access for user extraction
- Finding 53: Pydantic models require user_id
- Finding 55: get_session_storage usage
- Finding 56: Redis Session model requires user_id
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="test_message_user_scoped"),
]


class TestMessageModelUserIdColumn:
    """Tests for MessageModel.user_id column (Task 0.1)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_model_has_user_id_column(self) -> None:
        """
        GIVEN MessageModel SQLAlchemy model
        WHEN checking column definitions
        THEN user_id column should exist and be non-nullable
        """
        from mcp_server_langgraph.storage.session.postgres_models import MessageModel

        # Check column exists
        assert hasattr(MessageModel, "user_id"), "MessageModel should have user_id column"

        # Check column is defined
        columns = {c.name: c for c in MessageModel.__table__.columns}
        assert "user_id" in columns, "user_id should be a table column"

        # Check nullable=False per Finding 29
        user_id_col = columns["user_id"]
        assert user_id_col.nullable is False, "user_id should be NOT NULL"

    def test_session_model_user_id_non_nullable(self) -> None:
        """
        GIVEN SessionModel SQLAlchemy model
        WHEN checking user_id column
        THEN user_id should be non-nullable (Finding 29)
        """
        from mcp_server_langgraph.storage.session.postgres_models import SessionModel

        columns = {c.name: c for c in SessionModel.__table__.columns}
        user_id_col = columns["user_id"]
        assert user_id_col.nullable is False, "SessionModel.user_id should be NOT NULL"


class TestRedisMessageModel:
    """Tests for Redis Message model with user_id (Task 0.1)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_redis_message_has_user_id_field(self) -> None:
        """
        GIVEN Message Pydantic model
        WHEN creating a message
        THEN user_id field should be required
        """
        from mcp_server_langgraph.storage.session.models import Message

        # Check field exists in model
        assert "user_id" in Message.model_fields, "Message should have user_id field"

        # Create message with user_id
        message = Message(
            message_id=str(uuid4()),
            role="user",
            content="test content",
            user_id="user-123",
        )
        assert message.user_id == "user-123"

    def test_redis_message_user_id_required(self) -> None:
        """
        GIVEN Message Pydantic model
        WHEN creating without user_id
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.storage.session.models import Message

        with pytest.raises(ValidationError) as exc_info:
            Message(
                message_id=str(uuid4()),
                role="user",
                content="test content",
                # No user_id - should fail
            )
        assert "user_id" in str(exc_info.value)

    def test_redis_session_user_id_required(self) -> None:
        """
        GIVEN Session Pydantic model
        WHEN creating without user_id
        THEN should raise validation error (Finding 56)
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.storage.session.models import Session

        with pytest.raises(ValidationError) as exc_info:
            Session(
                session_id=str(uuid4()),
                name="Test Session",
                # No user_id - should fail per Finding 56
            )
        assert "user_id" in str(exc_info.value)


class TestContextvarStorageAdapter:
    """Tests for contextvar-based storage adapter (Task 0.5)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adapter_reads_user_id_from_contextvar(self) -> None:
        """
        GIVEN ContextvarSessionStorageAdapter
        WHEN getting messages
        THEN should read user_id from contextvar, not constructor
        """
        from mcp_server_langgraph.storage.session.adapter import (
            ContextvarSessionStorageAdapter,
            get_current_user_id,
            set_current_user_id,
        )

        # Create mock session service
        mock_service = AsyncMock(return_value=None)
        mock_service.get_session_messages = AsyncMock(return_value=[])

        ContextvarSessionStorageAdapter(session_service=mock_service)

        # Set contextvar
        set_current_user_id("test-user-123")

        # Verify contextvar is set
        assert get_current_user_id() == "test-user-123"

    @pytest.mark.asyncio
    async def test_adapter_get_messages_with_ownership(self) -> None:
        """
        GIVEN adapter with user_id set in contextvar
        WHEN calling get_messages
        THEN should pass user_id to session service
        """
        from mcp_server_langgraph.storage.session.adapter import (
            ContextvarSessionStorageAdapter,
            set_current_user_id,
        )

        mock_service = AsyncMock(return_value=None)
        mock_service.get_session_messages = AsyncMock(return_value=[{"content": "test"}])

        adapter = ContextvarSessionStorageAdapter(session_service=mock_service)
        set_current_user_id("user-456")

        result = await adapter.get_messages("session-123")

        mock_service.get_session_messages.assert_called_once_with("session-123", "user-456")
        assert result == [{"content": "test"}]

    @pytest.mark.asyncio
    async def test_adapter_returns_none_without_user_context(self) -> None:
        """
        GIVEN adapter with no user_id in contextvar
        WHEN calling get_messages
        THEN should return None (unauthorized)
        """
        from mcp_server_langgraph.storage.session.adapter import (
            ContextvarSessionStorageAdapter,
            _current_user_id,
        )

        # Reset contextvar
        token = _current_user_id.set("")

        try:
            mock_service = AsyncMock(return_value=None)
            adapter = ContextvarSessionStorageAdapter(session_service=mock_service)

            result = await adapter.get_messages("session-123")

            assert result is None
            mock_service.get_session_messages.assert_not_called()
        finally:
            _current_user_id.reset(token)

    @pytest.mark.asyncio
    async def test_adapter_add_message_with_ownership(self) -> None:
        """
        GIVEN adapter with user_id set in contextvar
        WHEN calling add_message
        THEN should pass user_id to session service
        """
        from mcp_server_langgraph.storage.session.adapter import (
            ContextvarSessionStorageAdapter,
            set_current_user_id,
        )

        mock_service = AsyncMock(return_value=None)
        mock_service.add_message = AsyncMock(return_value={"message_id": "msg-123", "content": "test"})

        adapter = ContextvarSessionStorageAdapter(session_service=mock_service)
        set_current_user_id("user-789")

        message_data = {"role": "user", "content": "Hello"}
        result = await adapter.add_message("session-123", message_data)

        mock_service.add_message.assert_called_once_with("session-123", "user-789", message_data)
        assert result == {"message_id": "msg-123", "content": "test"}


class TestUserContextMiddleware:
    """Tests for UserContextMiddleware (Task 0.6, Finding 49)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_extracts_user_id_from_dict(self) -> None:
        """
        GIVEN request.state.user is a dict
        WHEN middleware extracts user_id
        THEN should use dict.get() not getattr() (Finding 49)
        """
        from mcp_server_langgraph.middleware.user_context import UserContextMiddleware

        middleware = UserContextMiddleware(app=MagicMock())

        # Mock request with user as dict (set by AuthRequestMiddleware)
        mock_request = MagicMock()
        mock_request.state.user = {"sub": "user-123", "email": "test@example.com"}

        user_id = middleware._extract_user_id(mock_request)

        assert user_id == "user-123"

    def test_middleware_tries_multiple_user_id_keys(self) -> None:
        """
        GIVEN request.state.user dict with different key names
        WHEN middleware extracts user_id
        THEN should try sub, then user_id, then id
        """
        from mcp_server_langgraph.middleware.user_context import UserContextMiddleware

        middleware = UserContextMiddleware(app=MagicMock())

        # Test with user_id key
        mock_request = MagicMock()
        mock_request.state.user = {"user_id": "uid-456"}
        assert middleware._extract_user_id(mock_request) == "uid-456"

        # Test with id key
        mock_request.state.user = {"id": "id-789"}
        assert middleware._extract_user_id(mock_request) == "id-789"

    def test_middleware_returns_none_without_user(self) -> None:
        """
        GIVEN request.state.user is None
        WHEN middleware extracts user_id
        THEN should return None
        """
        from mcp_server_langgraph.middleware.user_context import UserContextMiddleware

        middleware = UserContextMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.state.user = None

        assert middleware._extract_user_id(mock_request) is None


class TestSessionServiceInterfaceUserScoped:
    """Tests for user_id in SessionService interface (Task 0.3)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_session_messages_has_user_id_param(self) -> None:
        """
        GIVEN SessionService ABC
        WHEN checking get_session_messages signature
        THEN should have user_id parameter
        """
        import inspect

        from mcp_server_langgraph.api.v1.sessions import SessionService

        sig = inspect.signature(SessionService.get_session_messages)
        params = list(sig.parameters.keys())

        assert "user_id" in params, "get_session_messages should have user_id parameter"

    def test_add_message_has_user_id_param(self) -> None:
        """
        GIVEN SessionService ABC
        WHEN checking add_message signature
        THEN should have user_id parameter
        """
        import inspect

        from mcp_server_langgraph.api.v1.sessions import SessionService

        sig = inspect.signature(SessionService.add_message)
        params = list(sig.parameters.keys())

        assert "user_id" in params, "add_message should have user_id parameter"


class TestPostgresManagerUserIdSupport:
    """Tests for PostgresSessionManager user_id support (Task 0.4b)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_postgres_manager_add_message_accepts_user_id(self) -> None:
        """
        GIVEN PostgresSessionManager
        WHEN checking add_message signature
        THEN should accept user_id parameter
        """
        import inspect

        from mcp_server_langgraph.storage.session.postgres_manager import PostgresSessionManager

        sig = inspect.signature(PostgresSessionManager.add_message)
        params = list(sig.parameters.keys())

        assert "user_id" in params, "PostgresSessionManager.add_message should accept user_id"

    def test_postgres_manager_create_session_requires_user_id(self) -> None:
        """
        GIVEN PostgresSessionManager
        WHEN checking create_session signature
        THEN user_id should be required (not optional)
        """
        import inspect

        from mcp_server_langgraph.storage.session.postgres_manager import PostgresSessionManager

        sig = inspect.signature(PostgresSessionManager.create_session)
        user_id_param = sig.parameters.get("user_id")

        assert user_id_param is not None, "create_session should have user_id param"
        # Check if it has no default (required)
        assert user_id_param.default is inspect.Parameter.empty, "user_id should be required"


class TestMetadataJsonHandling:
    """Tests for metadata_json handling without json.loads/dumps (Finding 48)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_model_to_message_reads_metadata_as_dict(self) -> None:
        """
        GIVEN MessageModel with metadata_json
        WHEN converting to Message
        THEN should access metadata_json directly as dict (no json.loads)
        """
        from mcp_server_langgraph.storage.session.postgres_manager import PostgresSessionManager
        from mcp_server_langgraph.storage.session.postgres_models import MessageModel

        # Create a mock engine
        mock_engine = MagicMock()
        manager = PostgresSessionManager(engine=mock_engine)

        # Create MessageModel with metadata_json as dict (SQLAlchemy JSON column)
        model = MessageModel(
            id="msg-123",
            session_id="sess-456",
            user_id="user-789",
            role="assistant",
            content="Hello",
            metadata_json={"sources": [{"title": "Source 1"}], "thinking": {"content": "thinking..."}},
            timestamp=datetime.now(UTC),
            order_index=0,
        )

        # Convert to Message
        message = manager._model_to_message(model)

        # Verify sources extracted from metadata
        assert message.sources == [{"title": "Source 1"}]
        assert message.user_id == "user-789"


class TestGetSessionStorageUsage:
    """Tests for get_session_storage replacing get_session_repository (Finding 55)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_session_storage_exists(self) -> None:
        """
        GIVEN chat module
        WHEN importing get_session_storage
        THEN function should exist
        """
        from mcp_server_langgraph.api.v1.chat import get_session_storage

        assert callable(get_session_storage)

    def test_get_session_storage_returns_contextvar_adapter(self) -> None:
        """
        GIVEN get_session_storage function
        WHEN called
        THEN should return ContextvarSessionStorageAdapter
        """
        from mcp_server_langgraph.api.v1.chat import get_session_storage
        from mcp_server_langgraph.storage.session.adapter import ContextvarSessionStorageAdapter

        storage = get_session_storage()
        assert isinstance(storage, ContextvarSessionStorageAdapter)


class TestInMemoryModelsUserIdRequired:
    """Tests for in-memory storage models requiring user_id (Finding 53)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_inmemory_session_requires_user_id(self) -> None:
        """
        GIVEN in-memory Session model
        WHEN creating without user_id
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.storage.models import Session

        with pytest.raises(ValidationError) as exc_info:
            Session(
                session_id=str(uuid4()),
                name="Test Session",
                # No user_id - should fail
            )
        assert "user_id" in str(exc_info.value).lower()

    def test_inmemory_message_requires_user_id(self) -> None:
        """
        GIVEN in-memory Message model
        WHEN creating without user_id
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.storage.models import Message

        with pytest.raises(ValidationError) as exc_info:
            Message(
                message_id=str(uuid4()),
                role="user",
                content="test",
                # No user_id - should fail
            )
        assert "user_id" in str(exc_info.value).lower()
