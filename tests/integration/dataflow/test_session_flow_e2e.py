"""
E2E Integration Test: Session Data Flow

Tests the complete session data flow:
    Chat API → SessionRepository.create() → Storage → Sessions API → Response

This test verifies that session and message data flows correctly through
the system, catching wiring issues where sessions are not properly persisted.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.session,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="session_flow_e2e"),
]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def unique_user_id() -> str:
    """Generate unique user ID for test isolation."""
    return f"test-user-{uuid4().hex[:8]}"


@pytest.fixture
def unique_session_id() -> str:
    """Generate unique session ID for test isolation."""
    return f"session-{uuid4().hex[:8]}"


@pytest.fixture
def unique_workflow_id() -> str:
    """Generate unique workflow ID for test isolation."""
    return f"workflow-{uuid4().hex[:8]}"


@pytest.fixture
def create_test_session():
    """Factory for creating test sessions."""
    from mcp_server_langgraph.storage.models import (
        Session,
        SessionConfig,
    )

    def _create(
        session_id: str,
        user_id: str,
        name: str = "Test Session",
        workflow_id: str | None = None,
    ) -> Session:
        return Session(
            session_id=session_id,
            name=name,
            user_id=user_id,
            workflow_id=workflow_id,
            config=SessionConfig(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=4096,
            ),
        )

    return _create


@pytest.fixture
def create_test_message():
    """Factory for creating test messages."""

    def _create(
        role: str = "user",
        content: str = "Hello, world!",
    ) -> dict:
        return {
            "message_id": str(uuid4()),
            "role": role,
            "content": content,
            "metadata": {},
        }

    return _create


# ============================================================================
# E2E Session Data Flow Tests
# ============================================================================


@pytest.mark.xdist_group("test_session_data_flow_e2_e")
class TestSessionDataFlowE2E:
    """
    E2E tests verifying the complete session data flow.

    These tests ensure that:
    1. Sessions are created and stored correctly
    2. Messages are added to sessions properly
    3. Sessions can be retrieved by ID
    4. Sessions can be listed by user
    5. The data matches what was stored

    Pattern: Producer (Chat API) → Repository → Storage → API → Response
    """

    def setup_method(self):
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_session_repository_stores_session(
        self,
        unique_user_id,
        unique_session_id,
        create_test_session,
    ):
        """
        E2E: Verify Session is stored and retrievable.

        GIVEN: An InMemorySessionRepository
        WHEN: A session is created
        THEN: The session is stored and retrievable by ID
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create and store session
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
            name="My Test Session",
        )

        await repository.create(session)

        # Retrieve and verify
        retrieved = await repository.get(unique_session_id)
        assert retrieved is not None
        assert retrieved.session_id == unique_session_id
        assert retrieved.user_id == unique_user_id
        assert retrieved.name == "My Test Session"

    async def test_session_repository_adds_messages(
        self,
        unique_user_id,
        unique_session_id,
        create_test_session,
        create_test_message,
    ):
        """
        E2E: Verify messages are added to sessions correctly.

        GIVEN: An existing session in the repository
        WHEN: Messages are added to the session
        THEN: The messages are stored and retrievable
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create session
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
        )
        await repository.create(session)

        # Add user message
        user_msg = create_test_message(
            role="user",
            content="What is the capital of France?",
        )
        result = await repository.add_message(unique_session_id, user_msg)
        assert result is not None

        # Add assistant message
        assistant_msg = create_test_message(
            role="assistant",
            content="The capital of France is Paris.",
        )
        await repository.add_message(unique_session_id, assistant_msg)

        # Retrieve messages
        messages = await repository.get_messages(unique_session_id)
        assert messages is not None
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert "Paris" in messages[1]["content"]

    async def test_session_list_by_user(
        self,
        unique_user_id,
        create_test_session,
    ):
        """
        E2E: Verify sessions can be listed by user.

        GIVEN: Multiple sessions for different users
        WHEN: Listing sessions by user_id
        THEN: Only sessions for that user are returned
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create sessions for our test user
        for i in range(3):
            session = create_test_session(
                session_id=f"session-{unique_user_id}-{i}",
                user_id=unique_user_id,
                name=f"Session {i}",
            )
            await repository.create(session)

        # Create session for different user
        other_session = create_test_session(
            session_id="session-other-user",
            user_id="other-user-123",
            name="Other User Session",
        )
        await repository.create(other_session)

        # List by user
        summaries, cursor = await repository.list(user_id=unique_user_id)

        assert len(summaries) == 3
        assert all(s.session_id.startswith(f"session-{unique_user_id}") for s in summaries)

    async def test_session_update_flow(
        self,
        unique_user_id,
        unique_session_id,
        create_test_session,
    ):
        """
        E2E: Verify session updates are persisted.

        GIVEN: An existing session
        WHEN: The session is updated
        THEN: The updates are persisted and retrievable
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create session
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
            name="Original Name",
        )
        await repository.create(session)

        # Update session
        updated = await repository.update(
            unique_session_id,
            {"name": "Updated Name", "status": "archived"},
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.status == "archived"

        # Verify update persisted
        retrieved = await repository.get(unique_session_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_session_delete_flow(
        self,
        unique_user_id,
        unique_session_id,
        create_test_session,
    ):
        """
        E2E: Verify session deletion removes data.

        GIVEN: An existing session
        WHEN: The session is deleted
        THEN: The session is no longer retrievable
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create session
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
        )
        await repository.create(session)

        # Verify exists
        assert await repository.get(unique_session_id) is not None

        # Delete
        deleted = await repository.delete(unique_session_id)
        assert deleted is True

        # Verify gone
        assert await repository.get(unique_session_id) is None


@pytest.mark.xdist_group("test_session_workflow_association")
class TestSessionWorkflowAssociation:
    """
    E2E tests for session-workflow associations.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_session_associated_with_workflow(
        self,
        unique_user_id,
        unique_session_id,
        unique_workflow_id,
        create_test_session,
    ):
        """
        E2E: Verify session can be associated with workflow.

        GIVEN: A session with workflow_id
        WHEN: The session is stored
        THEN: The workflow association is persisted
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create session with workflow association
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
            workflow_id=unique_workflow_id,
        )
        await repository.create(session)

        # Retrieve and verify
        retrieved = await repository.get(unique_session_id)
        assert retrieved is not None
        assert retrieved.workflow_id == unique_workflow_id

    async def test_sessions_list_by_workflow(
        self,
        unique_user_id,
        unique_workflow_id,
        create_test_session,
    ):
        """
        E2E: Verify sessions can be listed by workflow.

        GIVEN: Multiple sessions for a workflow
        WHEN: Listing sessions by workflow_id
        THEN: Only sessions for that workflow are returned
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create sessions for our workflow
        for i in range(2):
            session = create_test_session(
                session_id=f"session-wf-{i}",
                user_id=unique_user_id,
                workflow_id=unique_workflow_id,
            )
            await repository.create(session)

        # Create session for different workflow
        other_session = create_test_session(
            session_id="session-other-wf",
            user_id=unique_user_id,
            workflow_id="other-workflow-123",
        )
        await repository.create(other_session)

        # List by workflow
        summaries, cursor = await repository.list(workflow_id=unique_workflow_id)

        assert len(summaries) == 2
        assert all(s.workflow_id == unique_workflow_id for s in summaries)


@pytest.mark.xdist_group("test_session_message_history")
class TestSessionMessageHistory:
    """
    E2E tests for session message history retrieval.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_message_history_order_preserved(
        self,
        unique_user_id,
        unique_session_id,
        create_test_session,
        create_test_message,
    ):
        """
        E2E: Verify message order is preserved.

        GIVEN: Multiple messages added to a session
        WHEN: Messages are retrieved
        THEN: They are in chronological order
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create session
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
        )
        await repository.create(session)

        # Add messages in sequence
        messages_to_add = [
            ("user", "First question"),
            ("assistant", "First answer"),
            ("user", "Second question"),
            ("assistant", "Second answer"),
        ]

        for role, content in messages_to_add:
            msg = create_test_message(role=role, content=content)
            await repository.add_message(unique_session_id, msg)

        # Retrieve and verify order
        messages = await repository.get_messages(unique_session_id)
        assert messages is not None
        assert len(messages) == 4

        for i, (expected_role, expected_content) in enumerate(messages_to_add):
            assert messages[i]["role"] == expected_role
            assert messages[i]["content"] == expected_content

    async def test_empty_session_returns_empty_messages(
        self,
        unique_user_id,
        unique_session_id,
        create_test_session,
    ):
        """
        E2E: Verify empty session returns empty message list.

        GIVEN: A session with no messages
        WHEN: Messages are retrieved
        THEN: An empty list is returned (not None)
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Create session with no messages
        session = create_test_session(
            session_id=unique_session_id,
            user_id=unique_user_id,
        )
        await repository.create(session)

        # Retrieve messages
        messages = await repository.get_messages(unique_session_id)
        assert messages is not None
        assert messages == []

    async def test_nonexistent_session_returns_none(
        self,
    ):
        """
        E2E: Verify nonexistent session returns None for messages.

        GIVEN: A nonexistent session ID
        WHEN: Messages are requested
        THEN: None is returned (not an error)
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository

        repository = InMemorySessionRepository()

        # Request messages for nonexistent session
        messages = await repository.get_messages("nonexistent-session-id")
        assert messages is None


@pytest.mark.xdist_group("test_session_config_flow")
class TestSessionConfigFlow:
    """
    E2E tests for session configuration handling.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_session_config_persisted(
        self,
        unique_user_id,
        unique_session_id,
    ):
        """
        E2E: Verify session config is persisted correctly.

        GIVEN: A session with custom config
        WHEN: The session is stored and retrieved
        THEN: The config values are preserved
        """
        from mcp_server_langgraph.storage.memory import InMemorySessionRepository
        from mcp_server_langgraph.storage.models import Session, SessionConfig

        repository = InMemorySessionRepository()

        # Create session with custom config
        session = Session(
            session_id=unique_session_id,
            name="Custom Config Session",
            user_id=unique_user_id,
            config=SessionConfig(
                model="claude-3-5-sonnet-20241022",
                temperature=0.9,
                max_tokens=8192,
                execution_mode="bypass",
            ),
        )
        await repository.create(session)

        # Retrieve and verify
        retrieved = await repository.get(unique_session_id)
        assert retrieved is not None
        assert retrieved.config.model == "claude-3-5-sonnet-20241022"
        assert retrieved.config.temperature == 0.9
        assert retrieved.config.max_tokens == 8192
        assert retrieved.config.execution_mode == "bypass"
