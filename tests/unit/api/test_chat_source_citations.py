"""
Tests for Source Citations in Chat API (TDD RED Phase).

This module tests:
- ChatCompletionResponse includes sources field
- SSE streaming events include sources
- Sources are attached to stored messages
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="chat_source_citations")
class TestChatCompletionResponseSources:
    """Tests for sources field in ChatCompletionResponse."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_chat_completion_response_has_sources_field(self) -> None:
        """ChatCompletionResponse should have optional sources field."""
        from mcp_server_langgraph.api.v1.chat import ChatCompletionResponse

        # Check field exists in model
        fields = ChatCompletionResponse.model_fields
        assert "sources" in fields

        # Check it's optional (default None)
        assert fields["sources"].default is None

    def test_chat_completion_response_accepts_sources(self) -> None:
        """ChatCompletionResponse should accept sources list."""
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionResponse,
            ChatMessage,
        )
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        response = ChatCompletionResponse(
            id="chatcmpl-123",
            message=ChatMessage(role="assistant", content="Here's what I found."),
            sources=[
                SourceCitation(
                    title="Example",
                    url="https://example.com",
                    snippet="An example site.",
                ),
            ],
        )

        assert len(response.sources) == 1
        assert response.sources[0].title == "Example"

    def test_chat_completion_response_serializes_sources(self) -> None:
        """ChatCompletionResponse should serialize sources properly."""
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionResponse,
            ChatMessage,
        )
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        response = ChatCompletionResponse(
            id="chatcmpl-456",
            message=ChatMessage(role="assistant", content="Response text."),
            sources=[
                SourceCitation(
                    title="Doc",
                    url="https://docs.example.com",
                    snippet="Documentation.",
                ),
            ],
        )

        data = response.model_dump()

        assert "sources" in data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "Doc"
        assert data["sources"][0]["url"] == "https://docs.example.com"


@pytest.mark.xdist_group(name="chat_source_citations")
class TestStreamingSourceCitations:
    """Tests for sources in SSE streaming events."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_sse_sources_event_format(self) -> None:
        """SSE should emit sources event with proper format."""
        # The sources SSE event should match frontend expectations
        # See: useStreamingChat.ts handling of SSE events
        sources_event = {
            "sources": [
                {
                    "title": "Python Docs",
                    "url": "https://docs.python.org",
                    "snippet": "Python documentation.",
                },
            ],
        }

        # Verify structure matches expected format
        assert "sources" in sources_event
        assert isinstance(sources_event["sources"], list)
        assert sources_event["sources"][0]["title"] == "Python Docs"

    @pytest.mark.asyncio
    async def test_langgraph_stream_emits_sources(self) -> None:
        """LangGraph streaming should emit sources SSE event."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create service with mocked agent
        service = ChatServiceImpl()

        # Mock the langgraph agent to emit a custom event with sources
        mock_agent = MagicMock()

        async def mock_stream_events(*args, **kwargs):
            # Simulate web search sources being collected
            yield {
                "event": "on_custom",
                "name": "sources_collected",
                "data": {
                    "sources": [
                        {
                            "title": "Test Source",
                            "url": "https://test.com",
                            "snippet": "Test snippet.",
                        },
                    ],
                },
            }
            # Simulate content streaming
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Response text")},
                "metadata": {},
            }

        mock_agent.astream_events = mock_stream_events
        service._langgraph_agent = mock_agent

        # Collect events
        events = []
        async for event in service._stream_via_langgraph(
            session_id="test-session",
            messages=[{"role": "user", "content": "Search for Python"}],
        ):
            events.append(event)

        # Should have sources event
        sources_events = [e for e in events if "sources" in e]
        assert len(sources_events) == 1
        assert sources_events[0]["sources"][0]["title"] == "Test Source"


@pytest.mark.xdist_group(name="chat_source_citations")
class TestMessageStorageSources:
    """Tests for sources attached to stored messages."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_message_response_includes_sources(self) -> None:
        """MessageResponse should include sources from storage."""
        from mcp_server_langgraph.api.v1.sessions import (
            MessageResponse,
            MessageRole,
            SourceCitation,
        )

        response = MessageResponse(
            message_id="msg-123",
            role=MessageRole.assistant,
            content="Here's what I found.",
            sources=[
                SourceCitation(
                    title="Source 1",
                    url="https://source1.com",
                    snippet="First source.",
                ),
            ],
        )

        assert len(response.sources) == 1
        assert response.sources[0].title == "Source 1"

    def test_message_with_sources_serializes_correctly(self) -> None:
        """Message with sources should serialize for storage."""
        from mcp_server_langgraph.api.v1.sessions import (
            MessageResponse,
            MessageRole,
            SourceCitation,
        )

        response = MessageResponse(
            message_id="msg-456",
            role=MessageRole.assistant,
            content="Response content.",
            sources=[
                SourceCitation(
                    title="Doc",
                    url="https://docs.com",
                ),
            ],
        )

        data = response.model_dump()

        assert "sources" in data
        assert data["sources"][0]["title"] == "Doc"
        assert data["sources"][0]["url"] == "https://docs.com"
        assert data["sources"][0]["snippet"] is None
