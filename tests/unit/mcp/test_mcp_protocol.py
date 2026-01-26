"""
TDD Tests for MCP Protocol Messages (v2025-11-25)

These tests verify compliance with the MCP Protocol Specification version 2025-11-25.
Written FIRST before implementation (RED phase) per ADR-0082.

Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

import gc
import json

import pytest


MCP_PROTOCOL_VERSION = "2025-11-25"


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_protocol")
class TestMCPProtocolMessages:
    """Test suite for MCP JSON-RPC 2.0 message formatting."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_request_message_format(self):
        """GIVEN a method and params
        WHEN creating an MCP request
        THEN it follows JSON-RPC 2.0 format"""
        from mcp_server_langgraph.mcp.client.protocol import MCPRequest

        request = MCPRequest(
            method="tools/list",
            params={"cursor": None},
        )

        msg = request.to_dict()

        assert msg["jsonrpc"] == "2.0"
        assert "id" in msg  # Auto-generated
        assert msg["method"] == "tools/list"
        assert msg["params"] == {"cursor": None}

    @pytest.mark.unit
    def test_request_message_serialization(self):
        """GIVEN an MCPRequest
        WHEN serializing to JSON
        THEN it produces valid JSON string"""
        from mcp_server_langgraph.mcp.client.protocol import MCPRequest

        request = MCPRequest(
            method="initialize",
            params={"protocolVersion": MCP_PROTOCOL_VERSION},
        )

        json_str = request.to_json()
        parsed = json.loads(json_str)

        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "initialize"

    @pytest.mark.unit
    def test_notification_has_no_id(self):
        """GIVEN a notification
        WHEN creating the message
        THEN it has no 'id' field"""
        from mcp_server_langgraph.mcp.client.protocol import MCPNotification

        notification = MCPNotification(method="notifications/initialized")

        msg = notification.to_dict()

        assert msg["jsonrpc"] == "2.0"
        assert "id" not in msg
        assert msg["method"] == "notifications/initialized"

    @pytest.mark.unit
    def test_response_parsing_success(self):
        """GIVEN a successful JSON-RPC response
        WHEN parsing
        THEN result is extracted correctly"""
        from mcp_server_langgraph.mcp.client.protocol import MCPResponse

        raw = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
            },
        }

        response = MCPResponse.from_dict(raw)

        assert response.id == 1
        assert response.result["protocolVersion"] == MCP_PROTOCOL_VERSION
        assert response.error is None
        assert response.is_success is True

    @pytest.mark.unit
    def test_response_parsing_error(self):
        """GIVEN an error JSON-RPC response
        WHEN parsing
        THEN error is extracted correctly"""
        from mcp_server_langgraph.mcp.client.protocol import MCPResponse

        raw = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Unknown tool: invalid_tool",
            },
        }

        response = MCPResponse.from_dict(raw)

        assert response.id == 1
        assert response.result is None
        assert response.error["code"] == -32602
        assert response.is_success is False

    @pytest.mark.unit
    def test_unique_request_ids(self):
        """GIVEN multiple requests
        WHEN created
        THEN each has a unique ID"""
        from mcp_server_langgraph.mcp.client.protocol import MCPRequest

        requests = [MCPRequest(method="tools/list") for _ in range(100)]
        ids = [r.id for r in requests]

        assert len(set(ids)) == 100  # All unique


@pytest.mark.xdist_group(name="mcp_protocol")
class TestMCPInitializeHandshake:
    """Test suite for MCP initialize handshake (lifecycle)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_initialize_request_format(self):
        """GIVEN client info and capabilities
        WHEN creating initialize request
        THEN it matches spec format"""
        from mcp_server_langgraph.mcp.client.protocol import create_initialize_request

        request = create_initialize_request(
            client_name="mcp-server-langgraph",
            client_version="1.0.0",
        )

        params = request.params

        assert params["protocolVersion"] == MCP_PROTOCOL_VERSION
        assert params["clientInfo"]["name"] == "mcp-server-langgraph"
        assert params["clientInfo"]["version"] == "1.0.0"
        assert "capabilities" in params

    @pytest.mark.unit
    def test_initialize_response_parsing(self):
        """GIVEN server initialize response
        WHEN parsing
        THEN capabilities and server info are extracted"""
        from mcp_server_langgraph.mcp.client.protocol import parse_initialize_result

        result = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True},
            },
            "serverInfo": {
                "name": "playwright-mcp",
                "version": "1.0.0",
            },
        }

        info = parse_initialize_result(result)

        assert info.protocol_version == MCP_PROTOCOL_VERSION
        assert info.server_name == "playwright-mcp"
        assert info.has_tools is True
        assert info.tools_list_changed is True

    @pytest.mark.unit
    def test_initialized_notification_format(self):
        """GIVEN successful initialization
        WHEN creating initialized notification
        THEN it matches spec format"""
        from mcp_server_langgraph.mcp.client.protocol import (
            create_initialized_notification,
        )

        notification = create_initialized_notification()

        assert notification.method == "notifications/initialized"


@pytest.mark.xdist_group(name="mcp_protocol")
class TestMCPToolsProtocol:
    """Test suite for MCP tools/list and tools/call messages."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_tools_list_request_format(self):
        """GIVEN optional cursor
        WHEN creating tools/list request
        THEN it matches spec format"""
        from mcp_server_langgraph.mcp.client.protocol import create_tools_list_request

        request = create_tools_list_request(cursor=None)

        assert request.method == "tools/list"
        assert request.params.get("cursor") is None

        # With cursor
        request_with_cursor = create_tools_list_request(cursor="page2")
        assert request_with_cursor.params["cursor"] == "page2"

    @pytest.mark.unit
    def test_tools_list_response_parsing(self):
        """GIVEN tools/list response
        WHEN parsing
        THEN tools are extracted with proper schema"""
        from mcp_server_langgraph.mcp.client.protocol import parse_tools_list_result

        result = {
            "tools": [
                {
                    "name": "screenshot",
                    "description": "Take a screenshot",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
                {
                    "name": "click",
                    "description": "Click an element",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"selector": {"type": "string"}},
                    },
                },
            ],
            "nextCursor": None,
        }

        tools, next_cursor = parse_tools_list_result(result)

        assert len(tools) == 2
        assert tools[0]["name"] == "screenshot"
        assert tools[0]["inputSchema"]["type"] == "object"
        assert next_cursor is None

    @pytest.mark.unit
    def test_tools_call_request_format(self):
        """GIVEN tool name and arguments
        WHEN creating tools/call request
        THEN it matches spec format"""
        from mcp_server_langgraph.mcp.client.protocol import create_tools_call_request

        request = create_tools_call_request(
            name="screenshot",
            arguments={"url": "https://example.com"},
        )

        assert request.method == "tools/call"
        assert request.params["name"] == "screenshot"
        assert request.params["arguments"]["url"] == "https://example.com"

    @pytest.mark.unit
    def test_tools_call_response_parsing_success(self):
        """GIVEN successful tools/call response
        WHEN parsing
        THEN content is extracted correctly"""
        from mcp_server_langgraph.mcp.client.protocol import parse_tools_call_result

        result = {
            "content": [
                {
                    "type": "text",
                    "text": "Screenshot saved to /tmp/screenshot.png",
                }
            ],
            "isError": False,
        }

        content, is_error = parse_tools_call_result(result)

        assert is_error is False
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert "Screenshot" in content[0]["text"]

    @pytest.mark.unit
    def test_tools_call_response_parsing_error(self):
        """GIVEN error tools/call response (tool execution error)
        WHEN parsing
        THEN isError is True with error content"""
        from mcp_server_langgraph.mcp.client.protocol import parse_tools_call_result

        result = {
            "content": [
                {
                    "type": "text",
                    "text": "Error: Element not found for selector '.missing'",
                }
            ],
            "isError": True,
        }

        content, is_error = parse_tools_call_result(result)

        assert is_error is True
        assert "Error" in content[0]["text"]


@pytest.mark.xdist_group(name="mcp_protocol")
class TestMCPHTTPHeaders:
    """Test suite for MCP HTTP header requirements."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_required_headers_generation(self):
        """GIVEN protocol version and optional session ID
        WHEN generating headers
        THEN required MCP headers are included"""
        from mcp_server_langgraph.mcp.client.protocol import get_mcp_headers

        headers = get_mcp_headers(session_id=None)

        assert headers["MCP-Protocol-Version"] == MCP_PROTOCOL_VERSION
        assert headers["Accept"] == "application/json, text/event-stream"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.unit
    def test_session_id_header(self):
        """GIVEN a session ID
        WHEN generating headers
        THEN MCP-Session-Id is included"""
        from mcp_server_langgraph.mcp.client.protocol import get_mcp_headers

        headers = get_mcp_headers(session_id="abc123-session-id")

        assert headers["MCP-Session-Id"] == "abc123-session-id"

    @pytest.mark.unit
    def test_headers_without_session(self):
        """GIVEN no session ID
        WHEN generating headers
        THEN MCP-Session-Id is not included"""
        from mcp_server_langgraph.mcp.client.protocol import get_mcp_headers

        headers = get_mcp_headers(session_id=None)

        assert "MCP-Session-Id" not in headers


@pytest.mark.xdist_group(name="mcp_protocol")
class TestMCPSTDIOFraming:
    """Test suite for STDIO transport message framing."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_message_framing_adds_headers(self):
        """GIVEN a JSON-RPC message
        WHEN framing for STDIO
        THEN it is newline-delimited without embedded newlines"""
        from mcp_server_langgraph.mcp.client.protocol import frame_stdio_message

        message = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        framed = frame_stdio_message(message)

        assert framed.endswith("\n")
        assert framed.count("\n") == 1  # Only trailing newline

    @pytest.mark.unit
    def test_message_parsing_extracts_payload(self):
        """GIVEN newline-delimited messages
        WHEN parsing
        THEN individual JSON-RPC messages are extracted"""
        from mcp_server_langgraph.mcp.client.protocol import parse_stdio_messages

        raw = (
            '{"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}\n'
            '{"jsonrpc": "2.0", "method": "notifications/tools/list_changed"}\n'
        )

        messages = parse_stdio_messages(raw)

        assert len(messages) == 2
        assert messages[0]["id"] == 1
        assert messages[1]["method"] == "notifications/tools/list_changed"

    @pytest.mark.unit
    def test_handles_partial_message(self):
        """GIVEN incomplete message buffer
        WHEN parsing
        THEN complete messages are returned, incomplete buffered"""
        from mcp_server_langgraph.mcp.client.protocol import parse_stdio_messages

        raw = '{"jsonrpc": "2.0", "id": 1, "result": {}}\n{"jsonrpc": "2.0"'

        messages = parse_stdio_messages(raw)

        # Only complete message should be parsed
        assert len(messages) == 1
        assert messages[0]["id"] == 1
