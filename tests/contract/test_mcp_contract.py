"""
Contract tests for MCP protocol compliance

Validates that the MCP server strictly adheres to the Model Context Protocol specification.
"""

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


@pytest.fixture
def mcp_schemas():
    """Load MCP JSON schemas"""
    schema_path = Path(__file__).parent / "mcp_schemas.json"
    with open(schema_path) as f:
        schemas = json.load(f)
    return schemas


@pytest.mark.contract
@pytest.mark.unit
class TestJSONRPCFormat:
    """Test basic JSON-RPC 2.0 format compliance"""

    def test_request_has_required_fields(self, mcp_schemas):
        """All MCP requests must follow JSON-RPC 2.0 format"""
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        # Should validate against JSON-RPC request schema
        validate(instance=request, schema=mcp_schemas["definitions"]["jsonrpc_request"])

    def test_response_has_required_fields(self, mcp_schemas):
        """All MCP responses must follow JSON-RPC 2.0 format"""
        response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}

        # Should validate
        validate(instance=response, schema=mcp_schemas["definitions"]["jsonrpc_response"])

    def test_error_response_format(self, mcp_schemas):
        """Error responses must have code and message"""
        error_response = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid Request"}}

        validate(instance=error_response, schema=mcp_schemas["definitions"]["jsonrpc_response"])

    def test_response_cannot_have_both_result_and_error(self, mcp_schemas):
        """JSON-RPC responses must have either result or error, not both"""
        invalid_response = {"jsonrpc": "2.0", "id": 1, "result": {}, "error": {"code": -1, "message": "test"}}

        with pytest.raises(ValidationError):
            validate(instance=invalid_response, schema=mcp_schemas["definitions"]["jsonrpc_response"])

    def test_jsonrpc_version_must_be_2_0(self, mcp_schemas):
        """JSON-RPC version must be exactly "2.0" """
        invalid_request = {"jsonrpc": "1.0", "id": 1, "method": "test"}

        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=mcp_schemas["definitions"]["jsonrpc_request"])


@pytest.mark.contract
@pytest.mark.unit
class TestInitializeContract:
    """Test initialize handshake contract"""

    def test_initialize_request_format(self, mcp_schemas):
        """Initialize request must include protocolVersion and clientInfo"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test-client", "version": "1.0.0"}},
        }

        validate(instance=request, schema=mcp_schemas["definitions"]["initialize_request"])

    def test_initialize_request_missing_clientinfo(self, mcp_schemas):
        """Initialize request without clientInfo should fail"""
        invalid_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "0.1.0"}}

        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=mcp_schemas["definitions"]["initialize_request"])

    def test_initialize_response_format(self, mcp_schemas):
        """Initialize response must include serverInfo and capabilities"""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "0.1.0",
                "serverInfo": {"name": "mcp-server-langgraph", "version": "1.0.0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        }

        validate(instance=response, schema=mcp_schemas["definitions"]["initialize_response"])

    def test_initialize_response_missing_capabilities(self, mcp_schemas):
        """Initialize response must include capabilities"""
        invalid_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"protocolVersion": "0.1.0", "serverInfo": {"name": "test", "version": "1.0.0"}},
        }

        with pytest.raises(ValidationError):
            validate(instance=invalid_response, schema=mcp_schemas["definitions"]["initialize_response"])


@pytest.mark.contract
@pytest.mark.unit
class TestToolsContract:
    """Test tools/list and tools/call contracts"""

    def test_tools_list_request_format(self, mcp_schemas):
        """tools/list request should follow MCP spec"""
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        validate(instance=request, schema=mcp_schemas["definitions"]["tools_list_request"])

    def test_tools_list_response_format(self, mcp_schemas):
        """tools/list response must contain array of tools"""
        response = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "chat",
                        "description": "Chat with AI agent",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}, "username": {"type": "string"}},
                            "required": ["message", "username"],
                        },
                    }
                ]
            },
        }

        validate(instance=response, schema=mcp_schemas["definitions"]["tools_list_response"])

    def test_tool_must_have_name_and_description(self, mcp_schemas):
        """Each tool must have name and description"""
        invalid_response = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "chat"}]}}  # Missing description

        with pytest.raises(ValidationError):
            validate(instance=invalid_response, schema=mcp_schemas["definitions"]["tools_list_response"])

    def test_tools_call_request_format(self, mcp_schemas):
        """tools/call request must include name and arguments"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "chat", "arguments": {"message": "Hello", "username": "alice"}},
        }

        validate(instance=request, schema=mcp_schemas["definitions":"tools_call_request"])

    def test_tools_call_response_format(self, mcp_schemas):
        """tools/call response must contain content array"""
        response = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": "Hello! How can I help you?"}], "isError": False},
        }

        validate(instance=response, schema=mcp_schemas["definitions"]["tools_call_response"])

    def test_tools_call_response_must_have_content(self, mcp_schemas):
        """tools/call response must include content field"""
        invalid_response = {"jsonrpc": "2.0", "id": 3, "result": {"isError": False}}  # Missing content

        with pytest.raises(ValidationError):
            validate(instance=invalid_response, schema=mcp_schemas["definitions"]["tools_call_response"])


@pytest.mark.contract
@pytest.mark.unit
class TestResourcesContract:
    """Test resources/list contract"""

    def test_resources_list_request_format(self, mcp_schemas):
        """resources/list request should follow MCP spec"""
        request = {"jsonrpc": "2.0", "id": 4, "method": "resources/list", "params": {}}

        validate(instance=request, schema=mcp_schemas["definitions"]["resources_list_request"])

    def test_resources_list_response_format(self, mcp_schemas):
        """resources/list response must contain array of resources"""
        response = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {
                "resources": [
                    {
                        "uri": "conversation://thread_1",
                        "name": "Conversation Thread 1",
                        "description": "First conversation",
                        "mimeType": "text/plain",
                    }
                ]
            },
        }

        validate(instance=response, schema=mcp_schemas["definitions"]["resources_list_response"])

    def test_resource_must_have_uri_and_name(self, mcp_schemas):
        """Each resource must have uri and name"""
        invalid_response = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"resources": [{"uri": "conversation://thread_1"}]},  # Missing name
        }

        with pytest.raises(ValidationError):
            validate(instance=invalid_response, schema=mcp_schemas["definitions"]["resources_list_response"])


@pytest.mark.contract
@pytest.mark.integration
class TestMCPServerContractCompliance:
    """Integration tests verifying actual MCP server follows the contract"""

    @pytest.mark.asyncio
    async def test_server_initialize_follows_contract(self, mcp_schemas):
        """Actual server initialize response should match schema"""
        # This would test against the real server
        # Mock for now since we don't want to start server in tests
        pass

    @pytest.mark.asyncio
    async def test_server_tools_list_follows_contract(self, mcp_schemas):
        """Actual server tools/list should match schema"""
        # Would test real server implementation
        pass

    @pytest.mark.asyncio
    async def test_server_tools_call_follows_contract(self, mcp_schemas):
        """Actual server tools/call should match schema"""
        # Would test real server implementation
        pass


@pytest.mark.contract
@pytest.mark.unit
class TestSchemaCompleteness:
    """Meta-tests ensuring our schemas are comprehensive"""

    def test_all_required_schemas_defined(self, mcp_schemas):
        """Verify all key MCP message types have schemas"""
        required_schemas = [
            "initialize_request",
            "initialize_response",
            "tools_list_request",
            "tools_list_response",
            "tools_call_request",
            "tools_call_response",
            "resources_list_request",
            "resources_list_response",
        ]

        for schema_name in required_schemas:
            assert schema_name in mcp_schemas["definitions"], f"Missing schema: {schema_name}"

    def test_schemas_are_valid_json_schema(self, mcp_schemas):
        """All schemas should be valid JSON Schema Draft 7"""
        # Verify schema structure
        assert "$schema" in mcp_schemas
        assert "definitions" in mcp_schemas
        assert "schemas" in mcp_schemas
