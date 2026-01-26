"""
Session Repository Unit Tests

Tests for session storage operations per TDD methodology.
Tests written FIRST before implementation (RED phase).
"""

import gc
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mcp_server_langgraph.storage.models import (
    Message,
    Session,
    SessionConfig,
    SessionSummary,
)


pytestmark = [
    pytest.mark.unit,
]


@pytest.mark.xdist_group(name="test_session_repository")
class TestMessageModel:
    """Tests for Message model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_create_with_required_fields(self) -> None:
        """
        GIVEN valid message data
        WHEN Message is created
        THEN model should have all required fields
        """
        message = Message(
            message_id=str(uuid4()),
            role="user",
            content="Hello, world!",
            user_id="test-user-123",  # v8: Required field
        )

        assert message.message_id is not None
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.user_id == "test-user-123"
        assert message.timestamp is not None
        assert message.metadata == {}

    def test_message_roles_accepts_all_valid_values(self) -> None:
        """
        GIVEN different role values
        WHEN Messages are created
        THEN all roles should be valid
        """
        for role in ["user", "assistant", "system"]:
            message = Message(
                message_id=str(uuid4()),
                role=role,
                content="Test content",
                user_id="test-user-123",  # v8: Required field
            )
            assert message.role == role


@pytest.mark.xdist_group(name="test_session_repository")
class TestSessionConfigModel:
    """Tests for SessionConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_config_defaults_sets_expected_values(self) -> None:
        """
        GIVEN no config values
        WHEN SessionConfig is created
        THEN should use values from settings (12-Factor App Principle III)
        """
        from mcp_server_langgraph.core.config import settings

        config = SessionConfig()

        # v8: Use settings values, not hardcoded (12-Factor App)
        assert config.model == settings.model_name
        assert config.temperature == 0.7
        assert config.max_tokens == settings.model_max_tokens

    def test_config_custom_values(self) -> None:
        """
        GIVEN custom config values
        WHEN SessionConfig is created
        THEN should have custom values
        """
        config = SessionConfig(
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
        )

        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000


@pytest.mark.xdist_group(name="test_session_repository")
class TestSessionModel:
    """Tests for Session model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_create_with_required_fields(self) -> None:
        """
        GIVEN valid session data
        WHEN Session is created
        THEN model should have all required fields
        """
        session = Session(
            session_id=str(uuid4()),
            name="Test Session",
            user_id="test-user-123",  # v8: Required field
        )

        assert session.session_id is not None
        assert session.name == "Test Session"
        assert session.user_id == "test-user-123"
        assert session.messages == []
        assert session.status == "active"
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_session_with_messages(self) -> None:
        """
        GIVEN session with messages
        WHEN Session is created
        THEN should contain messages
        """
        messages = [
            Message(message_id="1", role="user", content="Hello", user_id="test-user-123"),
            Message(message_id="2", role="assistant", content="Hi there!", user_id="test-user-123"),
        ]

        session = Session(
            session_id=str(uuid4()),
            name="Chat Session",
            user_id="test-user-123",  # v8: Required field
            messages=messages,
        )

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_session_to_summary(self) -> None:
        """
        GIVEN a Session model with messages
        WHEN to_summary is called
        THEN should return SessionSummary with message count
        """
        messages = [
            Message(message_id="1", role="user", content="Hello", user_id="test-user-123"),
            Message(message_id="2", role="assistant", content="Hi!", user_id="test-user-123"),
            Message(message_id="3", role="user", content="How are you?", user_id="test-user-123"),
        ]

        session = Session(
            session_id=str(uuid4()),
            name="Test Session",
            user_id="test-user-123",  # v8: Required field
            workflow_id="workflow123",
            messages=messages,
        )

        summary = session.to_summary()

        assert isinstance(summary, SessionSummary)
        assert summary.session_id == session.session_id
        assert summary.name == session.name
        assert summary.message_count == 3
        assert summary.workflow_id == "workflow123"


@pytest.mark.xdist_group(name="test_session_repository")
class TestSessionSummaryModel:
    """Tests for SessionSummary model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_summary_create_with_valid_data_has_all_fields(self) -> None:
        """
        GIVEN valid summary data
        WHEN SessionSummary is created
        THEN model should have all fields
        """
        now = datetime.now(UTC)
        summary = SessionSummary(
            session_id=str(uuid4()),
            name="Test Session",
            workflow_id="workflow123",
            message_count=10,
            status="active",
            created_at=now,
            updated_at=now,
        )

        assert summary.name == "Test Session"
        assert summary.message_count == 10
        assert summary.status == "active"
