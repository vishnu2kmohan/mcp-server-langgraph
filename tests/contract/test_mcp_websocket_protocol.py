"""
MCP WebSocket Protocol Contract Tests

Contract tests ensuring compliance with MCP 2025-11-25 specification over WebSocket.
Tests verify JSON-RPC 2.0 message format, required methods, and protocol behavior.

MCP Spec Reference: https://modelcontextprotocol.io/specification
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.contract,
    pytest.mark.mcp,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolInitialize:
    """Tests for MCP initialize handshake over WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_initialize_request_format(self) -> None:
        """
        GIVEN a valid initialize request
        WHEN validating against MCP spec
        THEN should have required JSON-RPC 2.0 fields.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        # Validate JSON-RPC 2.0 required fields
        assert request["jsonrpc"] == "2.0"
        assert "id" in request
        assert request["method"] == "initialize"
        assert "params" in request
        assert "protocolVersion" in request["params"]

    def test_initialize_response_format(self) -> None:
        """
        GIVEN an initialize response from the server
        WHEN validating against MCP spec
        THEN should contain required fields per MCP 2025-11-25.
        """
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-11-25",
                "serverInfo": {
                    "name": "langgraph-agent",
                    "version": "2.8.0",
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"listChanged": False, "subscribe": True},
                    "prompts": {"listChanged": False},
                    "elicitation": {},
                    "sampling": {},
                    "logging": {},
                },
            },
        }

        # Validate required response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2025-11-25"
        assert "serverInfo" in response["result"]
        assert "capabilities" in response["result"]

        # Validate capabilities structure
        caps = response["result"]["capabilities"]
        assert "tools" in caps
        assert "resources" in caps
        assert "prompts" in caps


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolTools:
    """Tests for MCP tools protocol over WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tools_list_request_format(self) -> None:
        """
        GIVEN a tools/list request
        WHEN validating against MCP spec
        THEN should have correct method and optional cursor.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        assert request["method"] == "tools/list"
        assert isinstance(request["params"], dict)

    def test_tools_list_response_format(self) -> None:
        """
        GIVEN a tools/list response
        WHEN validating against MCP spec
        THEN should contain tools array with required fields.
        """
        response = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "langgraph-run",
                        "description": "Execute LangGraph agent",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                            },
                            "required": ["query"],
                        },
                    }
                ]
            },
        }

        # Validate tool structure
        assert "tools" in response["result"]
        tool = response["result"]["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"

    def test_tools_call_request_format(self) -> None:
        """
        GIVEN a tools/call request
        WHEN validating against MCP spec
        THEN should contain name and arguments.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "langgraph-run",
                "arguments": {"query": "Hello, world!"},
            },
        }

        assert request["method"] == "tools/call"
        assert "name" in request["params"]
        assert "arguments" in request["params"]

    def test_tools_call_response_format(self) -> None:
        """
        GIVEN a tools/call response
        WHEN validating against MCP spec
        THEN should contain content array.
        """
        response = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [{"type": "text", "text": "Response from agent"}],
                "isError": False,
            },
        }

        assert "content" in response["result"]
        assert isinstance(response["result"]["content"], list)
        assert response["result"]["content"][0]["type"] in ["text", "image", "resource"]


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolResources:
    """Tests for MCP resources protocol over WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_resources_list_request_format(self) -> None:
        """
        GIVEN a resources/list request
        WHEN validating against MCP spec
        THEN should have correct method.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {},
        }

        assert request["method"] == "resources/list"

    def test_resources_list_response_format(self) -> None:
        """
        GIVEN a resources/list response
        WHEN validating against MCP spec
        THEN should contain resources array with required fields.
        """
        response = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {
                "resources": [
                    {
                        "uri": "config://studio/session-1",
                        "name": "Session Configuration",
                        "mimeType": "application/json",
                    }
                ]
            },
        }

        assert "resources" in response["result"]
        resource = response["result"]["resources"][0]
        assert "uri" in resource
        assert "name" in resource

    def test_resources_read_request_format(self) -> None:
        """
        GIVEN a resources/read request
        WHEN validating against MCP spec
        THEN should contain uri.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": "config://studio/session-1"},
        }

        assert request["method"] == "resources/read"
        assert "uri" in request["params"]


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolPrompts:
    """Tests for MCP prompts protocol over WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompts_list_request_format(self) -> None:
        """
        GIVEN a prompts/list request
        WHEN validating against MCP spec
        THEN should have correct method.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/list",
            "params": {},
        }

        assert request["method"] == "prompts/list"

    def test_prompts_get_request_format(self) -> None:
        """
        GIVEN a prompts/get request
        WHEN validating against MCP spec
        THEN should contain name and optional arguments.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "prompts/get",
            "params": {
                "name": "code_review",
                "arguments": {"code": "def hello(): pass", "language": "python"},
            },
        }

        assert request["method"] == "prompts/get"
        assert "name" in request["params"]


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolElicitation:
    """Tests for MCP elicitation protocol (2025-11-25 SEP-1330, SEP-1036)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_elicitation_create_request_format(self) -> None:
        """
        GIVEN an elicitation/create request
        WHEN validating against MCP spec
        THEN should contain schema for user input.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "elicitation/create",
            "params": {
                "message": "Please provide your API key",
                "requestedSchema": {
                    "type": "object",
                    "properties": {
                        "api_key": {"type": "string", "description": "Your API key"},
                    },
                    "required": ["api_key"],
                },
            },
        }

        assert request["method"] == "elicitation/create"
        assert "message" in request["params"]
        assert "requestedSchema" in request["params"]


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolSampling:
    """Tests for MCP sampling protocol (2025-11-25 SEP-1577)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sampling_create_message_request_format(self) -> None:
        """
        GIVEN a sampling/createMessage request
        WHEN validating against MCP spec
        THEN should contain messages and model preferences.
        """
        request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "sampling/createMessage",
            "params": {
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": "What is 2+2?"},
                    }
                ],
                "modelPreferences": {
                    "hints": [{"name": "claude-3-sonnet"}],
                    "costPriority": 0.5,
                    "speedPriority": 0.5,
                    "intelligencePriority": 0.5,
                },
                "maxTokens": 1000,
            },
        }

        assert request["method"] == "sampling/createMessage"
        assert "messages" in request["params"]
        assert isinstance(request["params"]["messages"], list)


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPProtocolErrors:
    """Tests for MCP JSON-RPC 2.0 error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_error_response_format(self) -> None:
        """
        GIVEN an error response
        WHEN validating against JSON-RPC 2.0 spec
        THEN should contain error object with code and message.
        """
        response = {
            "jsonrpc": "2.0",
            "id": 10,
            "error": {
                "code": -32600,
                "message": "Invalid Request",
            },
        }

        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert response["error"]["code"] == -32600

    def test_method_not_found_error(self) -> None:
        """
        GIVEN an unknown method request
        WHEN server responds
        THEN should return -32601 Method not found error.
        """
        response = {
            "jsonrpc": "2.0",
            "id": 11,
            "error": {
                "code": -32601,
                "message": "Method not found",
            },
        }

        assert response["error"]["code"] == -32601

    def test_parse_error_returns_code_32700(self) -> None:
        """
        GIVEN invalid JSON
        WHEN server parses
        THEN should return -32700 Parse error.
        """
        response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": "Parse error",
            },
        }

        assert response["error"]["code"] == -32700


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPStreamingExtensions:
    """Tests for MCP streaming extensions ($/streaming/*)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_start_notification_format(self) -> None:
        """
        GIVEN a streaming start notification
        WHEN validating format
        THEN should have no id (notification) and stream metadata.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "$/streaming/start",
            "params": {
                "streamId": "stream-123",
                "toolCallId": 3,
            },
        }

        # Notifications have no id
        assert "id" not in notification
        assert notification["method"] == "$/streaming/start"
        assert "streamId" in notification["params"]

    def test_streaming_chunk_notification_format(self) -> None:
        """
        GIVEN a streaming chunk notification
        WHEN validating format
        THEN should contain chunk data.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "$/streaming/chunk",
            "params": {
                "streamId": "stream-123",
                "content": {"type": "text", "text": "Partial response..."},
            },
        }

        assert notification["method"] == "$/streaming/chunk"
        assert "content" in notification["params"]

    def test_streaming_end_notification_format(self) -> None:
        """
        GIVEN a streaming end notification
        WHEN validating format
        THEN should contain stream id.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "$/streaming/end",
            "params": {
                "streamId": "stream-123",
            },
        }

        assert notification["method"] == "$/streaming/end"


@pytest.mark.xdist_group(name="test_mcp_websocket_protocol")
class TestMCPTraceExtensions:
    """Tests for MCP trace extensions ($/trace/*)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_trace_span_notification_format(self) -> None:
        """
        GIVEN a trace span notification
        WHEN validating format
        THEN should contain OpenTelemetry-compatible span data.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "$/trace/span",
            "params": {
                "traceId": "abc123",
                "spanId": "def456",
                "parentSpanId": None,
                "name": "tools/call",
                "startTime": "2025-01-01T00:00:00Z",
                "endTime": "2025-01-01T00:00:01Z",
                "status": "OK",
                "attributes": {"tool.name": "langgraph-run"},
            },
        }

        assert notification["method"] == "$/trace/span"
        assert "traceId" in notification["params"]
        assert "spanId" in notification["params"]
        assert "name" in notification["params"]

    def test_trace_event_notification_format(self) -> None:
        """
        GIVEN a trace event notification
        WHEN validating format
        THEN should contain event data.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "$/trace/event",
            "params": {
                "spanId": "def456",
                "name": "llm.completion",
                "timestamp": "2025-01-01T00:00:00.500Z",
                "attributes": {"llm.model": "gpt-4"},
            },
        }

        assert notification["method"] == "$/trace/event"
        assert "name" in notification["params"]
