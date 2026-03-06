"""
Session API Contract Tests

TDD tests for validating the session and message response contracts.
These tests define the expected API contract before implementation.

Contract Requirements:
- SessionResponse uses 'name' (not 'title')
- SessionResponse.status is a constrained enum
- MessageResponse includes 'message_id'
- MessageResponse.role is a constrained enum
"""

import gc

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.api.v1.sessions import (
    InMemorySessionService,
    MessageResponse,
    SessionResponse,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestSessionCreateRequestContract:
    """Tests for SessionCreateRequest model contract."""

    @pytest.mark.unit
    def test_session_create_request_uses_name_field(self) -> None:
        """SessionCreateRequest should have 'name' field (not just 'title')."""
        from mcp_server_langgraph.api.v1.sessions import SessionCreateRequest

        schema = SessionCreateRequest.model_json_schema()
        properties = schema.get("properties", {})

        # 'name' should be in properties
        assert "name" in properties, "SessionCreateRequest should have 'name' field"

    @pytest.mark.unit
    def test_session_create_request_accepts_name(self) -> None:
        """SessionCreateRequest should accept 'name' parameter."""
        from mcp_server_langgraph.api.v1.sessions import SessionCreateRequest

        # GIVEN a request with 'name'
        request = SessionCreateRequest(name="My New Session")

        # THEN name should be accessible
        assert request.name == "My New Session"


class TestSessionResponseContract:
    """Tests for SessionResponse model contract."""

    @pytest.mark.unit
    def test_session_response_uses_name_field(self) -> None:
        """SessionResponse should use 'name' field, not 'title'.

        The field should be called 'name' to match frontend expectations
        and storage layer naming convention.
        """
        # GIVEN a valid session data with 'name' field
        session_data = {
            "id": "session-123",
            "name": "My Session",
            "workflow_id": None,
            "messages": [],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "status": "active",
        }

        # WHEN creating a SessionResponse
        response = SessionResponse(**session_data)

        # THEN the 'name' field should be accessible
        assert response.name == "My Session"
        assert hasattr(response, "name")

    @pytest.mark.unit
    def test_session_response_name_field_in_schema(self) -> None:
        """SessionResponse schema should include 'name', not 'title'."""
        # GIVEN the SessionResponse model
        schema = SessionResponse.model_json_schema()

        # THEN 'name' should be in properties
        assert "name" in schema["properties"]
        # AND 'title' should NOT be in properties (it's the old field name)
        assert "title" not in schema["properties"]

    @pytest.mark.unit
    def test_session_status_is_constrained_enum(self) -> None:
        """Session status must be one of: active, archived, deleted."""
        # GIVEN valid session data
        session_data = {
            "id": "session-123",
            "name": "Test Session",
            "workflow_id": None,
            "messages": [],
            "status": "active",
        }

        # WHEN creating a SessionResponse with valid status
        response = SessionResponse(**session_data)

        # THEN status should be the enum value
        assert response.status.value == "active"  # type: ignore[union-attr]

    @pytest.mark.unit
    def test_session_status_rejects_invalid_values(self) -> None:
        """Session status should reject invalid values."""
        # GIVEN session data with invalid status
        session_data = {
            "id": "session-123",
            "name": "Test Session",
            "status": "invalid_status",  # Invalid value
        }

        # WHEN/THEN creating SessionResponse should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            SessionResponse(**session_data)

        # AND error should mention the status field
        errors = exc_info.value.errors()
        assert any("status" in str(e) for e in errors)

    @pytest.mark.unit
    def test_session_status_valid_values(self) -> None:
        """Session status should accept all valid enum values."""
        valid_statuses = ["active", "archived", "deleted"]

        for status_value in valid_statuses:
            session_data = {
                "id": "session-123",
                "name": "Test Session",
                "status": status_value,
            }

            # WHEN creating SessionResponse
            response = SessionResponse(**session_data)

            # THEN it should succeed with correct status
            assert response.status.value == status_value  # type: ignore[union-attr]


class TestMessageResponseContract:
    """Tests for MessageResponse model contract."""

    @pytest.mark.unit
    def test_message_response_includes_message_id(self) -> None:
        """MessageResponse must include message_id field."""
        # GIVEN valid message data with message_id
        message_data = {
            "message_id": "msg-456",
            "role": "user",
            "content": "Hello, world!",
            "timestamp": "2025-01-01T00:00:00Z",
        }

        # WHEN creating a MessageResponse
        response = MessageResponse(**message_data)

        # THEN message_id should be accessible
        assert response.message_id == "msg-456"
        assert hasattr(response, "message_id")

    @pytest.mark.unit
    def test_message_response_message_id_in_schema(self) -> None:
        """MessageResponse schema should include 'message_id'."""
        # GIVEN the MessageResponse model
        schema = MessageResponse.model_json_schema()

        # THEN 'message_id' should be in properties
        assert "message_id" in schema["properties"]

    @pytest.mark.unit
    def test_message_response_message_id_required(self) -> None:
        """MessageResponse.message_id should be required."""
        # GIVEN message data without message_id
        message_data = {
            "role": "user",
            "content": "Hello, world!",
        }

        # WHEN/THEN creating MessageResponse should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            MessageResponse(**message_data)

        # AND error should mention message_id
        errors = exc_info.value.errors()
        assert any("message_id" in str(e) for e in errors)

    @pytest.mark.unit
    def test_message_role_is_constrained_enum(self) -> None:
        """Message role must be one of: user, assistant, system."""
        # GIVEN valid message data
        message_data = {
            "message_id": "msg-123",
            "role": "user",
            "content": "Hello",
        }

        # WHEN creating a MessageResponse
        response = MessageResponse(**message_data)

        # THEN role should be the enum value
        assert response.role.value == "user"  # type: ignore[union-attr]

    @pytest.mark.unit
    def test_message_role_rejects_invalid_values(self) -> None:
        """Message role should reject invalid values."""
        # GIVEN message data with invalid role
        message_data = {
            "message_id": "msg-123",
            "role": "invalid_role",  # Invalid value
            "content": "Hello",
        }

        # WHEN/THEN creating MessageResponse should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            MessageResponse(**message_data)

        # AND error should mention role field
        errors = exc_info.value.errors()
        assert any("role" in str(e) for e in errors)

    @pytest.mark.unit
    def test_message_role_valid_values(self) -> None:
        """Message role should accept all valid enum values."""
        valid_roles = ["user", "assistant", "system"]

        for role_value in valid_roles:
            message_data = {
                "message_id": "msg-123",
                "role": role_value,
                "content": "Test content",
            }

            # WHEN creating MessageResponse
            response = MessageResponse(**message_data)

            # THEN it should succeed with correct role
            assert response.role.value == role_value  # type: ignore[union-attr]

    # =========================================================================
    # v8: ThinkingResponse object tests (Q14, Q18, Finding 54)
    # =========================================================================

    @pytest.mark.unit
    def test_thinking_response_model_exists(self) -> None:
        """ThinkingResponse model should exist for thinking object structure.

        v8 Q14: Extend API with thinking object for cleaner structure.
        """
        # WHEN importing ThinkingResponse
        from mcp_server_langgraph.api.v1.sessions import ThinkingResponse

        # THEN it should be a Pydantic model
        from pydantic import BaseModel

        assert issubclass(ThinkingResponse, BaseModel)

    @pytest.mark.unit
    def test_thinking_response_has_content_and_tokens_fields(self) -> None:
        """ThinkingResponse should have content and tokens fields.

        v8 Finding 54: Use "tokens" not "budget_tokens" to match ThinkingContent model.
        """
        from mcp_server_langgraph.api.v1.sessions import ThinkingResponse

        # GIVEN the ThinkingResponse schema
        schema = ThinkingResponse.model_json_schema()
        properties = schema.get("properties", {})

        # THEN it should have 'content' field
        assert "content" in properties, "ThinkingResponse should have 'content' field"

        # AND it should have 'tokens' field (not 'budget_tokens' - Finding 54)
        assert "tokens" in properties, "ThinkingResponse should have 'tokens' field"
        assert "budget_tokens" not in properties, "Use 'tokens' not 'budget_tokens' (Finding 54)"

    @pytest.mark.unit
    def test_thinking_response_accepts_values(self) -> None:
        """ThinkingResponse should accept content and tokens values."""
        from mcp_server_langgraph.api.v1.sessions import ThinkingResponse

        # GIVEN valid thinking data
        thinking = ThinkingResponse(content="Reasoning about the problem...", tokens=150)

        # THEN values should be accessible
        assert thinking.content == "Reasoning about the problem..."
        assert thinking.tokens == 150

    @pytest.mark.unit
    def test_thinking_response_fields_optional(self) -> None:
        """ThinkingResponse fields should be optional (nullable)."""
        from mcp_server_langgraph.api.v1.sessions import ThinkingResponse

        # WHEN creating ThinkingResponse with no fields
        thinking = ThinkingResponse()

        # THEN it should succeed with None values
        assert thinking.content is None
        assert thinking.tokens is None

    @pytest.mark.unit
    def test_message_response_has_thinking_object_field(self) -> None:
        """MessageResponse should have thinking field of type ThinkingResponse.

        v8 Q14: Thinking as object for cleaner structure.
        """
        # GIVEN the MessageResponse schema
        schema = MessageResponse.model_json_schema()
        properties = schema.get("properties", {})

        # THEN 'thinking' should be in properties
        assert "thinking" in properties, "MessageResponse should have 'thinking' field"

    @pytest.mark.unit
    def test_message_response_thinking_field_accepts_object(self) -> None:
        """MessageResponse.thinking should accept ThinkingResponse object."""
        from mcp_server_langgraph.api.v1.sessions import ThinkingResponse

        # GIVEN message data with thinking object
        message_data = {
            "message_id": "msg-123",
            "role": "assistant",
            "content": "Here is my response.",
            "thinking": ThinkingResponse(content="Let me think...", tokens=100),
        }

        # WHEN creating MessageResponse
        response = MessageResponse(**message_data)

        # THEN thinking should be accessible
        assert response.thinking is not None
        assert response.thinking.content == "Let me think..."
        assert response.thinking.tokens == 100

    @pytest.mark.unit
    def test_message_response_no_legacy_thinking_fields(self) -> None:
        """MessageResponse should NOT have legacy thinking fields.

        Legacy fields (thinking_content, thinking_tokens) have been deprecated
        in favor of the thinking object with content and tokens fields.
        """
        # GIVEN the MessageResponse schema
        schema = MessageResponse.model_json_schema()
        properties = schema.get("properties", {})

        # THEN legacy fields should NOT exist (deprecated)
        assert "thinking_content" not in properties, "Legacy thinking_content should be removed"
        assert "thinking_tokens" not in properties, "Legacy thinking_tokens should be removed"

        # AND the thinking object should be the only way to access thinking data
        assert "thinking" in properties, "thinking object should exist"

    @pytest.mark.unit
    def test_message_response_thinking_object_only(self) -> None:
        """MessageResponse should only use thinking object, not legacy fields.

        The thinking object provides a cleaner structure with content and tokens.
        """
        from mcp_server_langgraph.api.v1.sessions import ThinkingResponse

        # GIVEN message data with thinking object only
        message_data = {
            "message_id": "msg-123",
            "role": "assistant",
            "content": "Response content",
            "thinking": ThinkingResponse(content="Deep reasoning...", tokens=200),
        }

        # WHEN creating MessageResponse
        response = MessageResponse(**message_data)

        # THEN thinking object should be accessible
        assert response.thinking is not None
        assert response.thinking.content == "Deep reasoning..."
        assert response.thinking.tokens == 200

        # AND legacy attributes should not exist
        assert not hasattr(response, "thinking_content") or response.thinking_content is None
        assert not hasattr(response, "thinking_tokens") or response.thinking_tokens is None


class TestSessionServiceContract:
    """Tests for session service response contract."""

    # Test user ID for session ownership
    TEST_USER_ID = "test-user-123"

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_returns_name_field(self) -> None:
        """Created session should have 'name' field in response."""
        # GIVEN an in-memory session service
        service = InMemorySessionService()

        # WHEN creating a session (user_id is now required for security)
        session = await service.create_session({"title": "My Session"}, self.TEST_USER_ID)

        # THEN response should have 'name' field (not 'title')
        assert "name" in session
        assert session["name"] == "My Session"
        # AND 'title' should NOT be present
        assert "title" not in session

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_returns_name_field(self) -> None:
        """Retrieved session should have 'name' field in response."""
        # GIVEN an in-memory session service with a session
        service = InMemorySessionService()
        created = await service.create_session({"title": "Test Session"}, self.TEST_USER_ID)

        # WHEN getting the session (user_id is now required for security)
        session = await service.get_session(created["id"], self.TEST_USER_ID)

        # THEN response should have 'name' field
        assert session is not None
        assert "name" in session
        assert session["name"] == "Test Session"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_message_returns_message_id(self) -> None:
        """Added message should include message_id in response."""
        # GIVEN an in-memory session service with a session
        service = InMemorySessionService()
        session = await service.create_session({"title": "Test"}, self.TEST_USER_ID)

        # WHEN adding a message - v8: add_message now requires user_id
        message = await service.add_message(
            session["id"],
            self.TEST_USER_ID,
            {"role": "user", "content": "Hello"},
        )

        # THEN response should include message_id
        assert message is not None
        assert "message_id" in message
        assert message["message_id"] is not None
        assert len(message["message_id"]) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_messages_include_message_id(self) -> None:
        """Retrieved messages should include message_id."""
        # GIVEN a session with messages
        service = InMemorySessionService()
        session = await service.create_session({"title": "Test"}, self.TEST_USER_ID)
        # v8: add_message now requires user_id
        await service.add_message(session["id"], self.TEST_USER_ID, {"role": "user", "content": "Hi"})
        await service.add_message(session["id"], self.TEST_USER_ID, {"role": "assistant", "content": "Hello"})

        # WHEN getting messages - v8: now requires user_id
        messages = await service.get_session_messages(session["id"], self.TEST_USER_ID)

        # THEN all messages should have message_id
        assert messages is not None
        assert len(messages) == 2
        for msg in messages:
            assert "message_id" in msg
            assert msg["message_id"] is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_messages_have_unique_ids(self) -> None:
        """Each message should have a unique message_id."""
        # GIVEN a session with multiple messages
        service = InMemorySessionService()
        session = await service.create_session({"title": "Test"}, self.TEST_USER_ID)

        # Add 5 messages - v8: add_message now requires user_id
        for i in range(5):
            await service.add_message(
                session["id"],
                self.TEST_USER_ID,
                {"role": "user", "content": f"Message {i}"},
            )

        # WHEN getting messages - v8: now requires user_id
        messages = await service.get_session_messages(session["id"], self.TEST_USER_ID)

        # THEN all message_ids should be unique
        assert messages is not None
        message_ids = [msg["message_id"] for msg in messages]
        assert len(message_ids) == len(set(message_ids))  # All unique


class TestSessionResponseSerialization:
    """Tests for proper JSON serialization of session responses."""

    @pytest.mark.unit
    def test_session_response_serializes_with_name(self) -> None:
        """SessionResponse JSON should use 'name', not 'title'."""
        # GIVEN a valid SessionResponse
        response = SessionResponse(
            id="session-123",
            name="My Session",
            status="active",  # type: ignore[arg-type]
        )

        # WHEN serializing to dict
        data = response.model_dump()

        # THEN 'name' should be in output
        assert "name" in data
        assert data["name"] == "My Session"
        # AND 'title' should NOT be present
        assert "title" not in data

    @pytest.mark.unit
    def test_message_response_serializes_with_message_id(self) -> None:
        """MessageResponse JSON should include 'message_id'."""
        # GIVEN a valid MessageResponse
        response = MessageResponse(
            message_id="msg-456",
            role="user",  # type: ignore[arg-type]
            content="Hello",
        )

        # WHEN serializing to dict
        data = response.model_dump()

        # THEN 'message_id' should be in output
        assert "message_id" in data
        assert data["message_id"] == "msg-456"


class TestSessionConfigResponseContract:
    """Tests for SessionConfigResponse model contract.

    TDD tests ensuring session responses include config with model information.
    This enables the frontend StatusBar to display the actual model being used.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_config_response_exists(self) -> None:
        """SessionConfigResponse model should exist in sessions module."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        # Model should be importable
        assert SessionConfigResponse is not None

    @pytest.mark.unit
    def test_session_config_response_has_model_field(self) -> None:
        """SessionConfigResponse should have 'model' field."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        schema = SessionConfigResponse.model_json_schema()
        properties = schema.get("properties", {})

        # 'model' should be in properties
        assert "model" in properties, "SessionConfigResponse should have 'model' field"

    @pytest.mark.unit
    def test_session_config_response_has_temperature_field(self) -> None:
        """SessionConfigResponse should have 'temperature' field."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        schema = SessionConfigResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "temperature" in properties, "SessionConfigResponse should have 'temperature' field"

    @pytest.mark.unit
    def test_session_config_response_has_max_tokens_field(self) -> None:
        """SessionConfigResponse should have 'max_tokens' field."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        schema = SessionConfigResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "max_tokens" in properties, "SessionConfigResponse should have 'max_tokens' field"

    @pytest.mark.unit
    def test_session_config_response_defaults(self) -> None:
        """SessionConfigResponse should have sensible defaults from settings."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse
        from mcp_server_langgraph.core.config import settings

        # WHEN creating with no arguments (uses defaults)
        config = SessionConfigResponse()

        # THEN defaults should match backend configuration from settings
        # Note: Defaults come from environment settings, not hardcoded values
        assert config.model == settings.model_name
        assert config.temperature == 0.7
        assert config.max_tokens == settings.model_max_tokens

    @pytest.mark.unit
    def test_session_config_response_accepts_custom_values(self) -> None:
        """SessionConfigResponse should accept custom values."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        # GIVEN custom config values
        config = SessionConfigResponse(
            model="claude-3-opus",
            temperature=0.5,
            max_tokens=8192,
        )

        # THEN values should be accessible
        assert config.model == "claude-3-opus"
        assert config.temperature == 0.5
        assert config.max_tokens == 8192


class TestSessionResponseConfigField:
    """Tests for SessionResponse.config field integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_response_has_config_field(self) -> None:
        """SessionResponse should have 'config' field."""
        schema = SessionResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "config" in properties, "SessionResponse should have 'config' field"

    @pytest.mark.unit
    def test_session_response_config_is_optional(self) -> None:
        """SessionResponse.config should be optional."""
        # GIVEN session data without config
        session_data = {
            "id": "session-123",
            "name": "Test Session",
            "status": "active",
        }

        # WHEN creating SessionResponse
        response = SessionResponse(**session_data)

        # THEN config should be None (optional field)
        assert response.config is None

    @pytest.mark.unit
    def test_session_response_accepts_config(self) -> None:
        """SessionResponse should accept config field."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        # GIVEN session data with config
        config = SessionConfigResponse(model="gpt-4o-mini")
        session_data = {
            "id": "session-123",
            "name": "Test Session",
            "status": "active",
            "config": config,
        }

        # WHEN creating SessionResponse
        response = SessionResponse(**session_data)

        # THEN config should be accessible
        assert response.config is not None
        assert response.config.model == "gpt-4o-mini"

    @pytest.mark.unit
    def test_session_response_config_in_serialization(self) -> None:
        """SessionResponse JSON should include config when present."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigResponse

        # GIVEN a SessionResponse with config
        config = SessionConfigResponse(
            model="claude-3-sonnet",
            temperature=0.8,
            max_tokens=4096,
        )
        response = SessionResponse(
            id="session-123",
            name="Test Session",
            status="active",  # type: ignore[arg-type]
            config=config,
        )

        # WHEN serializing to dict
        data = response.model_dump()

        # THEN config should be in output with correct values
        assert "config" in data
        assert data["config"]["model"] == "claude-3-sonnet"
        assert data["config"]["temperature"] == 0.8
        assert data["config"]["max_tokens"] == 4096


class TestSessionConfigUpdateContract:
    """Tests for SessionConfigUpdateRequest model contract.

    TDD tests ensuring users can update session config (model selection feature).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_config_update_request_exists(self) -> None:
        """SessionConfigUpdateRequest model should exist in sessions module."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigUpdateRequest

        # Model should be importable
        assert SessionConfigUpdateRequest is not None

    @pytest.mark.unit
    def test_session_config_update_request_has_model_field(self) -> None:
        """SessionConfigUpdateRequest should have optional 'model' field."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigUpdateRequest

        schema = SessionConfigUpdateRequest.model_json_schema()
        properties = schema.get("properties", {})

        assert "model" in properties, "SessionConfigUpdateRequest should have 'model' field"

    @pytest.mark.unit
    def test_session_config_update_request_all_fields_optional(self) -> None:
        """SessionConfigUpdateRequest should allow partial updates."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigUpdateRequest

        # WHEN creating with no arguments
        request = SessionConfigUpdateRequest()

        # THEN all fields should be None (optional)
        assert request.model is None
        assert request.temperature is None
        assert request.max_tokens is None

    @pytest.mark.unit
    def test_session_config_update_request_accepts_model_only(self) -> None:
        """SessionConfigUpdateRequest should accept model-only update."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigUpdateRequest

        # GIVEN a request with only model
        request = SessionConfigUpdateRequest(model="claude-3-opus")

        # THEN only model should be set
        assert request.model == "claude-3-opus"
        assert request.temperature is None
        assert request.max_tokens is None

    @pytest.mark.unit
    def test_session_config_update_request_accepts_all_fields(self) -> None:
        """SessionConfigUpdateRequest should accept all config fields."""
        from mcp_server_langgraph.api.v1.sessions import SessionConfigUpdateRequest

        # GIVEN a request with all fields
        request = SessionConfigUpdateRequest(
            model="gpt-4-turbo",
            temperature=0.9,
            max_tokens=16384,
        )

        # THEN all fields should be accessible
        assert request.model == "gpt-4-turbo"
        assert request.temperature == 0.9
        assert request.max_tokens == 16384


class TestInMemorySessionConfigUpdate:
    """Tests for InMemorySessionService.update_config method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_method_exists(self) -> None:
        """InMemorySessionService should have update_config method."""
        service = InMemorySessionService()
        assert hasattr(service, "update_config")
        assert callable(service.update_config)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_changes_model(self) -> None:
        """update_config should change session's model."""
        service = InMemorySessionService()
        user_id = "test-user"

        # GIVEN a session exists (note: signature is session_data, user_id)
        session = await service.create_session({"name": "Test"}, user_id)
        session_id = session["id"]

        # WHEN updating the model
        updated = await service.update_config(session_id, user_id, {"model": "claude-3-sonnet"})

        # THEN the model should be updated
        assert updated is not None
        assert updated["config"]["model"] == "claude-3-sonnet"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_partial_update(self) -> None:
        """update_config should support partial updates."""
        service = InMemorySessionService()
        user_id = "test-user"

        # GIVEN a session with default config
        session = await service.create_session({"name": "Test"}, user_id)
        session_id = session["id"]
        original_temp = session["config"]["temperature"]

        # WHEN updating only the model
        updated = await service.update_config(session_id, user_id, {"model": "gpt-4-turbo"})

        # THEN model should change but temperature should remain
        assert updated is not None
        assert updated["config"]["model"] == "gpt-4-turbo"
        assert updated["config"]["temperature"] == original_temp

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_returns_none_for_nonexistent_session(self) -> None:
        """update_config should return None for non-existent session."""
        service = InMemorySessionService()

        # WHEN updating config for non-existent session
        result = await service.update_config("nonexistent", "user", {"model": "gpt-4"})

        # THEN result should be None
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_enforces_user_ownership(self) -> None:
        """update_config should not allow updating another user's session."""
        service = InMemorySessionService()

        # GIVEN a session owned by user1
        session = await service.create_session({"name": "Test"}, "user1")
        session_id = session["id"]

        # WHEN user2 tries to update config
        result = await service.update_config(session_id, "user2", {"model": "gpt-4"})

        # THEN result should be None (access denied)
        assert result is None


class TestRedisSessionConfigPersistence:
    """Tests for Redis session service config persistence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_calls_manager_update_session(self) -> None:
        """update_config should call manager.update_session for persistence."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.api.v1.sessions import RedisSessionService
        from mcp_server_langgraph.storage.session.models import Session, SessionConfig

        # GIVEN a mocked manager with a session
        mock_manager = MagicMock()
        mock_session = Session(
            session_id="test-session",
            name="Test",
            user_id="user1",
            config=SessionConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=1000),
        )
        mock_manager.get_session = AsyncMock(return_value=mock_session)
        mock_manager.update_session = AsyncMock(return_value=mock_session)

        service = RedisSessionService(mock_manager)

        # WHEN updating config
        await service.update_config("test-session", "user1", {"model": "claude-3-sonnet", "temperature": 0.9})

        # THEN manager.update_session should be called with new config
        mock_manager.update_session.assert_called_once()
        call_args = mock_manager.update_session.call_args
        assert call_args[1]["session_id"] == "test-session"
        assert call_args[1]["config"].model == "claude-3-sonnet"
        assert call_args[1]["config"].temperature == 0.9

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_preserves_unchanged_fields(self) -> None:
        """update_config should preserve config fields not being updated."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.api.v1.sessions import RedisSessionService
        from mcp_server_langgraph.storage.session.models import Session, SessionConfig

        # GIVEN a session with specific config
        mock_manager = MagicMock()
        mock_session = Session(
            session_id="test-session",
            name="Test",
            user_id="user1",
            config=SessionConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=2000),
        )
        mock_manager.get_session = AsyncMock(return_value=mock_session)
        mock_manager.update_session = AsyncMock(return_value=mock_session)

        service = RedisSessionService(mock_manager)

        # WHEN updating only model
        await service.update_config("test-session", "user1", {"model": "gpt-4-turbo"})

        # THEN max_tokens should remain unchanged
        call_args = mock_manager.update_session.call_args
        config = call_args[1]["config"]
        assert config.model == "gpt-4-turbo"
        assert config.max_tokens == 2000  # preserved


class TestPostgresSessionConfigPersistence:
    """Tests for PostgreSQL session service config persistence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_config_calls_manager_update_session(self) -> None:
        """update_config should call manager.update_session for persistence."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.api.v1.sessions import PostgresSessionService
        from mcp_server_langgraph.storage.session.models import Session, SessionConfig

        # GIVEN a mocked manager with a session
        mock_manager = MagicMock()
        mock_session = Session(
            session_id="test-session",
            name="Test",
            user_id="user1",
            config=SessionConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=1000),
        )
        mock_manager.get_session = AsyncMock(return_value=mock_session)
        mock_manager.update_session = AsyncMock(return_value=mock_session)

        service = PostgresSessionService(mock_manager)

        # WHEN updating config
        await service.update_config("test-session", "user1", {"model": "claude-3-opus", "max_tokens": 4000})

        # THEN manager.update_session should be called with new config
        mock_manager.update_session.assert_called_once()
        call_args = mock_manager.update_session.call_args
        assert call_args[1]["session_id"] == "test-session"
        assert call_args[1]["config"].model == "claude-3-opus"
        assert call_args[1]["config"].max_tokens == 4000


class TestSessionTraceResponseContract:
    """Tests for SessionTraceResponse model contract (GET /sessions/{id}/trace)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_trace_response_model_exists(self) -> None:
        """SessionTraceResponse model should exist."""
        from mcp_server_langgraph.api.v1.sessions import SessionTraceResponse

        # GIVEN the model exists
        # THEN it should be importable
        assert SessionTraceResponse is not None

    @pytest.mark.unit
    def test_session_trace_response_has_expected_fields(self) -> None:
        """SessionTraceResponse should have expected trace fields."""
        from mcp_server_langgraph.api.v1.sessions import SessionTraceResponse

        schema = SessionTraceResponse.model_json_schema()
        properties = schema.get("properties", {})

        # THEN it should have all expected trace fields
        expected_fields = ["steps", "tokens", "raw_output", "start_time", "end_time"]
        for field in expected_fields:
            assert field in properties, f"Missing field: {field}"

    @pytest.mark.unit
    def test_session_trace_response_allows_empty_trace(self) -> None:
        """SessionTraceResponse should allow empty/minimal trace data."""
        from mcp_server_langgraph.api.v1.sessions import SessionTraceResponse

        # GIVEN empty trace data
        trace_data: dict = {}

        # WHEN creating a SessionTraceResponse
        response = SessionTraceResponse(**trace_data)

        # THEN it should succeed with default empty values
        assert response.steps == []
        assert response.raw_output is None


class TestSessionMessagesThinkingContract:
    """Tests for thinking object in get_session_messages endpoint.

    Thinking data is stored and returned as an object with content and tokens.
    Legacy flat fields (thinking_content, thinking_tokens) have been deprecated.
    """

    # Test user ID for session ownership
    TEST_USER_ID = "test-user-123"

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_messages_with_thinking_object(self) -> None:
        """Messages stored with thinking object should return the object."""
        # GIVEN an in-memory session service
        service = InMemorySessionService()
        session = await service.create_session({"title": "Test"}, self.TEST_USER_ID)

        # WHEN adding a message with thinking object format
        await service.add_message(
            session["id"],
            self.TEST_USER_ID,
            {
                "role": "assistant",
                "content": "Response content",
                "thinking": {"content": "Deep reasoning...", "tokens": 150},
            },
        )

        # THEN get_session_messages should return the thinking object
        messages = await service.get_session_messages(session["id"], self.TEST_USER_ID)
        assert messages is not None
        assert len(messages) == 1

        msg = messages[0]
        # Thinking object should be present
        assert "thinking" in msg
        thinking = msg["thinking"]
        assert thinking["content"] == "Deep reasoning..."
        assert thinking["tokens"] == 150

        # Legacy fields should NOT be present
        assert "thinking_content" not in msg
        assert "thinking_tokens" not in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_messages_without_thinking(self) -> None:
        """Messages without thinking should not have thinking field."""
        # GIVEN an in-memory session service
        service = InMemorySessionService()
        session = await service.create_session({"title": "Test"}, self.TEST_USER_ID)

        # WHEN adding a message without thinking
        await service.add_message(
            session["id"],
            self.TEST_USER_ID,
            {
                "role": "user",
                "content": "Hello",
            },
        )

        # THEN get_session_messages should not have thinking
        messages = await service.get_session_messages(session["id"], self.TEST_USER_ID)
        assert messages is not None
        assert len(messages) == 1

        msg = messages[0]
        assert "thinking" not in msg
        assert "thinking_content" not in msg
        assert "thinking_tokens" not in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_messages_model_name_preserved(self) -> None:
        """Messages with model_name should preserve it in response."""
        # GIVEN an in-memory session service
        service = InMemorySessionService()
        session = await service.create_session({"title": "Test"}, self.TEST_USER_ID)

        # WHEN adding a message with model_name
        await service.add_message(
            session["id"],
            self.TEST_USER_ID,
            {
                "role": "assistant",
                "content": "Response",
                "model_name": "claude-3-opus-20240229",
            },
        )

        # THEN get_session_messages should include model_name
        messages = await service.get_session_messages(session["id"], self.TEST_USER_ID)
        assert messages is not None
        assert len(messages) == 1

        msg = messages[0]
        assert msg.get("model_name") == "claude-3-opus-20240229"
