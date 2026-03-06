"""
Tests for OTEL Session Lifecycle Events.

TDD tests to ensure session operations emit proper OTEL span events:
- session.start event when a session is created
- session.end event when a session is deleted/revoked

Reference: OpenTelemetry Session Semantic Conventions
"""

import gc
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="session_lifecycle_events"),
]


class TestSessionLifecycleEvents:
    """Test suite for session lifecycle span events."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def captured_events(self) -> list[dict]:
        """Container for captured span events."""
        return []

    @pytest.fixture
    def captured_attributes(self) -> dict[str, str | int | float]:
        """Container for captured span attributes."""
        return {}

    @pytest.fixture
    def mock_span(self, captured_events: list[dict], captured_attributes: dict[str, str | int | float]) -> MagicMock:
        """Create a mock span that captures events and attributes."""
        mock_span = MagicMock()
        mock_span.add_event = lambda name, attributes=None: captured_events.append(
            {"name": name, "attributes": attributes or {}}
        )
        mock_span.set_attribute = lambda k, v: captured_attributes.update({k: v})
        return mock_span

    @pytest.fixture
    def mock_tracer(self, mock_span: MagicMock) -> MagicMock:
        """Create a mock tracer that returns the mock span."""

        @contextmanager
        def _start_span_context(name: str):
            yield mock_span

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span = _start_span_context
        return mock_tracer

    @pytest.mark.asyncio
    async def test_session_create_emits_session_start_event(
        self,
        mock_tracer: MagicMock,
        captured_events: list[dict],
    ) -> None:
        """
        GIVEN an InMemorySessionStore
        WHEN create() is called to create a new session
        THEN a 'session.start' event should be added to the span
        """
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        with patch("mcp_server_langgraph.auth.session.tracer", mock_tracer):
            store = InMemorySessionStore()

            session_id = await store.create(
                user_id="user-123",
                username="testuser",
                roles=["user"],
            )

        # Find the session.start event
        start_events = [e for e in captured_events if e["name"] == "session.start"]
        assert len(start_events) == 1, f"Expected session.start event, got: {captured_events}"
        assert start_events[0]["attributes"].get("session.id") == session_id

    @pytest.mark.asyncio
    async def test_session_delete_emits_session_end_event(
        self,
        mock_tracer: MagicMock,
        captured_events: list[dict],
    ) -> None:
        """
        GIVEN an InMemorySessionStore with an existing session
        WHEN delete() is called to revoke the session
        THEN a 'session.end' event should be added to the span
        """
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        with patch("mcp_server_langgraph.auth.session.tracer", mock_tracer):
            store = InMemorySessionStore()

            # Create a session first
            session_id = await store.create(
                user_id="user-123",
                username="testuser",
                roles=["user"],
            )

            # Clear events from create
            captured_events.clear()

            # Delete the session
            await store.delete(session_id)

        # Find the session.end event
        end_events = [e for e in captured_events if e["name"] == "session.end"]
        assert len(end_events) == 1, f"Expected session.end event, got: {captured_events}"
        assert end_events[0]["attributes"].get("session.id") == session_id

    @pytest.mark.asyncio
    async def test_session_start_event_includes_user_id(
        self,
        mock_tracer: MagicMock,
        captured_events: list[dict],
    ) -> None:
        """
        GIVEN an InMemorySessionStore
        WHEN create() is called
        THEN the session.start event should include user_id attribute
        """
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        with patch("mcp_server_langgraph.auth.session.tracer", mock_tracer):
            store = InMemorySessionStore()

            await store.create(
                user_id="user-456",
                username="anotheruser",
                roles=["admin"],
            )

        start_events = [e for e in captured_events if e["name"] == "session.start"]
        assert len(start_events) == 1
        assert start_events[0]["attributes"].get("user.id") == "user-456"

    @pytest.mark.asyncio
    async def test_session_end_event_includes_reason(
        self,
        mock_tracer: MagicMock,
        captured_events: list[dict],
    ) -> None:
        """
        GIVEN an InMemorySessionStore with an existing session
        WHEN delete() is called
        THEN the session.end event should include a reason attribute
        """
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        with patch("mcp_server_langgraph.auth.session.tracer", mock_tracer):
            store = InMemorySessionStore()

            session_id = await store.create(
                user_id="user-789",
                username="testuser",
                roles=["user"],
            )
            captured_events.clear()

            await store.delete(session_id)

        end_events = [e for e in captured_events if e["name"] == "session.end"]
        assert len(end_events) == 1
        # Reason should be "revoked" for explicit deletion
        assert end_events[0]["attributes"].get("session.end.reason") == "revoked"
