"""Tests for SpanResponse thinking object format.

TDD: Tests written first to verify SpanResponse uses thinking object format
(consistent with MessageResponse) instead of flat thinking_content/thinking_tokens fields.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.mark.xdist_group(name="span_response_thinking")
class TestSpanResponseThinkingObject:
    """Test SpanResponse uses thinking object format."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_span_response_has_thinking_field(self) -> None:
        """GIVEN SpanResponse model
        WHEN examining schema
        THEN 'thinking' field exists (object format)
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        schema = SpanResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "thinking" in properties, "SpanResponse should have 'thinking' field"

    def test_span_response_no_legacy_thinking_fields(self) -> None:
        """GIVEN SpanResponse model
        WHEN examining schema
        THEN legacy flat fields do NOT exist (deprecated)
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        schema = SpanResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Legacy fields should NOT exist
        assert "thinking_content" not in properties, "SpanResponse should NOT have 'thinking_content' (deprecated)"
        assert "thinking_tokens" not in properties, "SpanResponse should NOT have 'thinking_tokens' (deprecated)"

    def test_span_response_thinking_object_structure(self) -> None:
        """GIVEN SpanResponse with thinking object
        WHEN creating instance
        THEN thinking has content and tokens fields
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        response = SpanResponse(
            span_id="span-123",
            name="llm-call",
            start_time="2024-01-01T00:00:00Z",
            thinking={
                "content": "Analyzing the problem...",
                "tokens": 150,
            },
        )

        assert response.thinking is not None
        assert response.thinking.content == "Analyzing the problem..."
        assert response.thinking.tokens == 150

    def test_span_response_thinking_null_allowed(self) -> None:
        """GIVEN SpanResponse without thinking
        WHEN creating instance
        THEN thinking is None (optional)
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        response = SpanResponse(
            span_id="span-456",
            name="regular-span",
            start_time="2024-01-01T00:00:00Z",
        )

        assert response.thinking is None

    def test_span_response_thinking_partial(self) -> None:
        """GIVEN SpanResponse with thinking content but no tokens
        WHEN creating instance
        THEN thinking.tokens is None
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        response = SpanResponse(
            span_id="span-789",
            name="llm-call",
            start_time="2024-01-01T00:00:00Z",
            thinking={
                "content": "Just content, no tokens",
            },
        )

        assert response.thinking is not None
        assert response.thinking.content == "Just content, no tokens"
        assert response.thinking.tokens is None


@pytest.mark.xdist_group(name="span_response_thinking")
class TestSpanToDict:
    """Test _span_to_dict converts OTEL attributes to SpanResponse format."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_span_to_dict_converts_thinking_attributes(self) -> None:
        """GIVEN span with thinking_content and thinking_tokens attributes
        WHEN converting to dict
        THEN thinking object is created with content and tokens
        """
        from dataclasses import dataclass
        from datetime import datetime, UTC
        from enum import Enum

        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        class StatusCode(Enum):
            OK = "OK"

        @dataclass
        class MockSpan:
            span_id: str = "span-123"
            parent_span_id: str | None = None
            operation_name: str = "llm-call"
            start_time: datetime | None = None
            duration_ms: float = 100.0
            status_code: StatusCode = StatusCode.OK
            attributes: dict | None = None

            def __post_init__(self):
                if self.start_time is None:
                    self.start_time = datetime.now(UTC)
                if self.attributes is None:
                    self.attributes = {}

        service = ObservabilityServiceImpl()
        span = MockSpan(
            attributes={
                "thinking_content": "Analyzing the problem...",
                "thinking_tokens": 150,
                "model_name": "claude-opus-4-5-20250514",
            }
        )

        result = service._span_to_dict(span)

        assert result["thinking"] is not None
        assert result["thinking"]["content"] == "Analyzing the problem..."
        assert result["thinking"]["tokens"] == 150
        assert result["model_name"] == "claude-opus-4-5-20250514"

    def test_span_to_dict_no_thinking_returns_none(self) -> None:
        """GIVEN span without thinking attributes
        WHEN converting to dict
        THEN thinking is None
        """
        from dataclasses import dataclass
        from datetime import datetime, UTC
        from enum import Enum

        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        class StatusCode(Enum):
            OK = "OK"

        @dataclass
        class MockSpan:
            span_id: str = "span-456"
            parent_span_id: str | None = None
            operation_name: str = "regular-span"
            start_time: datetime | None = None
            duration_ms: float = 50.0
            status_code: StatusCode = StatusCode.OK
            attributes: dict | None = None

            def __post_init__(self):
                if self.start_time is None:
                    self.start_time = datetime.now(UTC)
                if self.attributes is None:
                    self.attributes = {}

        service = ObservabilityServiceImpl()
        span = MockSpan(attributes={"some_attr": "value"})

        result = service._span_to_dict(span)

        assert result["thinking"] is None

    def test_span_to_dict_extracts_llm_model_fallback(self) -> None:
        """GIVEN span with llm.model attribute (not model_name)
        WHEN converting to dict
        THEN model_name uses llm.model fallback
        """
        from dataclasses import dataclass
        from datetime import datetime, UTC
        from enum import Enum

        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        class StatusCode(Enum):
            OK = "OK"

        @dataclass
        class MockSpan:
            span_id: str = "span-789"
            parent_span_id: str | None = None
            operation_name: str = "llm-call"
            start_time: datetime | None = None
            duration_ms: float = 75.0
            status_code: StatusCode = StatusCode.OK
            attributes: dict | None = None

            def __post_init__(self):
                if self.start_time is None:
                    self.start_time = datetime.now(UTC)
                if self.attributes is None:
                    self.attributes = {}

        service = ObservabilityServiceImpl()
        span = MockSpan(attributes={"llm.model": "gpt-4-turbo"})

        result = service._span_to_dict(span)

        assert result["model_name"] == "gpt-4-turbo"


@pytest.mark.xdist_group(name="span_response_thinking")
class TestSpanThinkingResponse:
    """Test SpanThinkingResponse model exists and has correct structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_span_thinking_response_exists(self) -> None:
        """GIVEN observability module
        WHEN importing SpanThinkingResponse
        THEN model is available
        """
        from mcp_server_langgraph.api.v1.observability import SpanThinkingResponse

        assert SpanThinkingResponse is not None

    def test_span_thinking_response_has_content_field(self) -> None:
        """GIVEN SpanThinkingResponse model
        WHEN examining schema
        THEN 'content' field exists
        """
        from mcp_server_langgraph.api.v1.observability import SpanThinkingResponse

        schema = SpanThinkingResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "content" in properties

    def test_span_thinking_response_has_tokens_field(self) -> None:
        """GIVEN SpanThinkingResponse model
        WHEN examining schema
        THEN 'tokens' field exists (optional)
        """
        from mcp_server_langgraph.api.v1.observability import SpanThinkingResponse

        schema = SpanThinkingResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "tokens" in properties
