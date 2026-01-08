"""
Tests for Chat API selected_tools SSE Event.

TDD tests for Phase 5: Emit selected_tools SSE event when semantic
tool selection is enabled in the LangGraph streaming path.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add selected_tools SSE event handling.
"""

import gc
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_selected_tools_sse")
class TestSelectedToolsSSEEvent:
    """Tests for selected_tools SSE event in chat streaming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stream_via_langgraph_yields_selected_tools_event(self, monkeypatch) -> None:
        """_stream_via_langgraph should yield selected_tools when emitted by agent."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock agent that emits selected_tools custom event
        mock_events = [
            # Node start event
            {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "select_tools"},
            },
            # Custom event for selected_tools
            {
                "event": "on_custom",
                "name": "selected_tools",
                "data": {
                    "selected_tools": ["calculator", "search_knowledge_base"],
                    "selection_scores": {"calculator": 0.95, "search_knowledge_base": 0.87},
                },
            },
            # Node end event
            {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "select_tools"},
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Calculate 2 + 2"}]

        # Collect all yielded events
        events = []
        async for event in service._stream_via_langgraph("test-session", messages):
            events.append(event)

        # Verify selected_tools event was yielded
        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 1
        assert selected_tools_events[0]["selected_tools"] == [
            "calculator",
            "search_knowledge_base",
        ]

    @pytest.mark.asyncio
    async def test_selected_tools_event_includes_scores(self, monkeypatch) -> None:
        """selected_tools SSE event should include selection scores when available."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_events = [
            {
                "event": "on_custom",
                "name": "selected_tools",
                "data": {
                    "selected_tools": ["read_file"],
                    "selection_scores": {"read_file": 0.92},
                },
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Read the file"}]

        events = []
        async for event in service._stream_via_langgraph("test-session", messages):
            events.append(event)

        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 1
        assert "selection_scores" in selected_tools_events[0]
        assert selected_tools_events[0]["selection_scores"] == {"read_file": 0.92}

    @pytest.mark.asyncio
    async def test_selected_tools_event_with_empty_list(self, monkeypatch) -> None:
        """selected_tools SSE event should handle empty tool list."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_events = [
            {
                "event": "on_custom",
                "name": "selected_tools",
                "data": {
                    "selected_tools": [],
                    "selection_scores": {},
                },
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Hello"}]

        events = []
        async for event in service._stream_via_langgraph("test-session", messages):
            events.append(event)

        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 1
        assert selected_tools_events[0]["selected_tools"] == []

    @pytest.mark.asyncio
    async def test_no_selected_tools_event_when_not_emitted(self, monkeypatch) -> None:
        """No selected_tools event should be yielded if agent doesn't emit it."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_events = [
            {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "respond"},
            },
            {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": MagicMock(content="Hello!"),
                },
            },
            {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "respond"},
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Hello"}]

        events = []
        async for event in service._stream_via_langgraph("test-session", messages):
            events.append(event)

        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_selected_tools_stream_integration")
class TestSelectedToolsStreamIntegration:
    """Integration tests for selected_tools in create_stream."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stream_includes_selected_tools_in_sse(self, monkeypatch) -> None:
        """create_stream should include selected_tools SSE event from LangGraph."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_events = [
            {
                "event": "on_custom",
                "name": "selected_tools",
                "data": {
                    "selected_tools": ["calculator"],
                    "selection_scores": {"calculator": 0.9},
                },
            },
            {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": MagicMock(content="The result is 4."),
                },
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Calculate 2 + 2"}]

        events = []
        async for event in service.create_stream("test-session", messages, use_langgraph=True):
            events.append(event)

        # Should have selected_tools event
        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 1

        # Should also have content delta
        delta_events = [e for e in events if "delta" in e]
        assert len(delta_events) >= 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_selected_tools_event_format")
class TestSelectedToolsEventFormat:
    """Tests for selected_tools SSE event format compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_selected_tools_event_is_json_serializable(self, monkeypatch) -> None:
        """selected_tools SSE event should be JSON serializable."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        import json

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_events = [
            {
                "event": "on_custom",
                "name": "selected_tools",
                "data": {
                    "selected_tools": ["tool1", "tool2"],
                    "selection_scores": {"tool1": 0.95, "tool2": 0.88},
                },
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Test"}]

        events = []
        async for event in service._stream_via_langgraph("test-session", messages):
            events.append(event)

        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 1

        # Should be JSON serializable
        json_str = json.dumps(selected_tools_events[0])
        assert "selected_tools" in json_str
        assert "tool1" in json_str

    @pytest.mark.asyncio
    async def test_selected_tools_event_structure(self, monkeypatch) -> None:
        """selected_tools SSE event should have expected structure."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_events = [
            {
                "event": "on_custom",
                "name": "selected_tools",
                "data": {
                    "selected_tools": ["calculator", "read_file"],
                    "selection_scores": {"calculator": 0.95, "read_file": 0.88},
                    "total_available": 50,
                },
            },
        ]

        async def mock_astream_events(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)

        messages = [{"role": "user", "content": "Test"}]

        events = []
        async for event in service._stream_via_langgraph("test-session", messages):
            events.append(event)

        selected_tools_events = [e for e in events if "selected_tools" in e]
        assert len(selected_tools_events) == 1

        event = selected_tools_events[0]
        # Required field
        assert "selected_tools" in event
        assert isinstance(event["selected_tools"], list)

        # Optional field
        if "selection_scores" in event:
            assert isinstance(event["selection_scores"], dict)
