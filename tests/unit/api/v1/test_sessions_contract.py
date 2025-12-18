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


@pytest.mark.xdist_group(name="test_session_create_request_contract")
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


@pytest.mark.xdist_group(name="test_session_response_contract")
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


@pytest.mark.xdist_group(name="test_message_response_contract")
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


@pytest.mark.xdist_group(name="test_session_service_contract")
class TestSessionServiceContract:
    """Tests for session service response contract."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_returns_name_field(self) -> None:
        """Created session should have 'name' field in response."""
        # GIVEN an in-memory session service
        service = InMemorySessionService()

        # WHEN creating a session
        session = await service.create_session({"title": "My Session"})

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
        created = await service.create_session({"title": "Test Session"})

        # WHEN getting the session
        session = await service.get_session(created["id"])

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
        session = await service.create_session({"title": "Test"})

        # WHEN adding a message
        message = await service.add_message(
            session["id"],
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
        session = await service.create_session({"title": "Test"})
        await service.add_message(session["id"], {"role": "user", "content": "Hi"})
        await service.add_message(session["id"], {"role": "assistant", "content": "Hello"})

        # WHEN getting messages
        messages = await service.get_session_messages(session["id"])

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
        session = await service.create_session({"title": "Test"})

        # Add 5 messages
        for i in range(5):
            await service.add_message(
                session["id"],
                {"role": "user", "content": f"Message {i}"},
            )

        # WHEN getting messages
        messages = await service.get_session_messages(session["id"])

        # THEN all message_ids should be unique
        assert messages is not None
        message_ids = [msg["message_id"] for msg in messages]
        assert len(message_ids) == len(set(message_ids))  # All unique


@pytest.mark.xdist_group(name="test_session_response_serialization")
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
