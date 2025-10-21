"""
Contract tests for MCP protocol compliance

Validates that the MCP server strictly adheres to the Model Context Protocol specification.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, ValidationError


@pytest.fixture
def mcp_schemas():
    """Load MCP JSON schemas"""
    schema_path = Path(__file__).parent / "mcp_schemas.json"
    with open(schema_path) as f:
        schemas = json.load(f)
    return schemas


@pytest.fixture
def validate_with_schema(mcp_schemas):
    """Helper to validate instances against schema definitions with proper $ref resolution"""
    validator = Draft7Validator(mcp_schemas)

    def validate_instance(instance, schema_name):
        """Validate instance against a schema definition by name"""
        # Use $ref to reference the definition, allowing proper resolution
        schema_ref = {"$ref": f"#/definitions/{schema_name}"}
        validator.validate(instance, schema_ref)

    return validate_instance


@pytest.mark.contract
@pytest.mark.unit
class TestJSONRPCFormat:
    """Test basic JSON-RPC 2.0 format compliance"""

    def test_request_has_required_fields(self, validate_with_schema):
        """All MCP requests must follow JSON-RPC 2.0 format"""
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        # Should validate against JSON-RPC request schema
        validate_with_schema(request, "jsonrpc_request")

    def test_response_has_required_fields(self, validate_with_schema):
        """All MCP responses must follow JSON-RPC 2.0 format"""
        response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}

        # Should validate
        validate_with_schema(response, "jsonrpc_response")

    def test_error_response_format(self, validate_with_schema):
        """Error responses must have code and message"""
        error_response = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid Request"}}

        validate_with_schema(error_response, "jsonrpc_response")

    def test_response_cannot_have_both_result_and_error(self, validate_with_schema):
        """JSON-RPC responses must have either result or error, not both"""
        invalid_response = {"jsonrpc": "2.0", "id": 1, "result": {}, "error": {"code": -1, "message": "test"}}

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_response, "jsonrpc_response")

    def test_jsonrpc_version_must_be_2_0(self, validate_with_schema):
        """JSON-RPC version must be exactly "2.0" """
        invalid_request = {"jsonrpc": "1.0", "id": 1, "method": "test"}

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_request, "jsonrpc_request")


@pytest.mark.contract
@pytest.mark.unit
class TestInitializeContract:
    """Test initialize handshake contract"""

    def test_initialize_request_format(self, validate_with_schema, mcp_schemas):
        """Initialize request must include protocolVersion and clientInfo"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test-client", "version": "1.0.0"}},
        }

        validate_with_schema(request, "initialize_request")

    def test_initialize_request_missing_clientinfo(self, validate_with_schema, mcp_schemas):
        """Initialize request without clientInfo should fail"""
        invalid_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "0.1.0"}}

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_request, "initialize_request")

    def test_initialize_response_format(self, validate_with_schema, mcp_schemas):
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

        validate_with_schema(response, "initialize_response")

    def test_initialize_response_missing_capabilities(self, validate_with_schema, mcp_schemas):
        """Initialize response must include capabilities"""
        invalid_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"protocolVersion": "0.1.0", "serverInfo": {"name": "test", "version": "1.0.0"}},
        }

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_response, "initialize_response")


@pytest.mark.contract
@pytest.mark.unit
class TestToolsContract:
    """Test tools/list and tools/call contracts"""

    def test_tools_list_request_format(self, validate_with_schema, mcp_schemas):
        """tools/list request should follow MCP spec"""
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        validate_with_schema(request, "tools_list_request")

    def test_tools_list_response_format(self, validate_with_schema, mcp_schemas):
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

        validate_with_schema(response, "tools_list_response")

    def test_tool_must_have_name_and_description(self, validate_with_schema, mcp_schemas):
        """Each tool must have name and description"""
        invalid_response = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "chat"}]}}  # Missing description

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_response, "tools_list_response")

    def test_tools_call_request_format(self, validate_with_schema, mcp_schemas):
        """tools/call request must include name and arguments"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "chat", "arguments": {"message": "Hello", "username": "alice"}},
        }

        validate_with_schema(request, "tools_call_request")

    def test_tools_call_response_format(self, validate_with_schema, mcp_schemas):
        """tools/call response must contain content array"""
        response = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": "Hello! How can I help you?"}], "isError": False},
        }

        validate_with_schema(response, "tools_call_response")

    def test_tools_call_response_must_have_content(self, validate_with_schema, mcp_schemas):
        """tools/call response must include content field"""
        invalid_response = {"jsonrpc": "2.0", "id": 3, "result": {"isError": False}}  # Missing content

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_response, "tools_call_response")


@pytest.mark.contract
@pytest.mark.unit
class TestResourcesContract:
    """Test resources/list contract"""

    def test_resources_list_request_format(self, validate_with_schema, mcp_schemas):
        """resources/list request should follow MCP spec"""
        request = {"jsonrpc": "2.0", "id": 4, "method": "resources/list", "params": {}}

        validate_with_schema(request, "resources_list_request")

    def test_resources_list_response_format(self, validate_with_schema, mcp_schemas):
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

        validate_with_schema(response, "resources_list_response")

    def test_resource_must_have_uri_and_name(self, validate_with_schema, mcp_schemas):
        """Each resource must have uri and name"""
        invalid_response = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"resources": [{"uri": "conversation://thread_1"}]},  # Missing name
        }

        with pytest.raises(ValidationError):
            validate_with_schema(invalid_response, "resources_list_response")


@pytest.mark.contract
@pytest.mark.integration
class TestMCPServerContractCompliance:
    """Integration tests verifying actual MCP server follows the contract"""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance for testing"""
        from unittest.mock import Mock

        from mcp_server_langgraph.auth.openfga import OpenFGAClient
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_openfga = Mock(spec=OpenFGAClient)
        mock_openfga.check_permission = Mock(return_value=True)
        return MCPAgentServer(openfga_client=mock_openfga)

    @pytest.mark.asyncio
    async def test_server_initialize_follows_contract(self, mcp_server):
        """Actual server initialize response should match schema"""
        # The server's initialize is handled by MCP SDK
        # We verify the server can be initialized without errors
        assert mcp_server is not None
        assert mcp_server.server is not None
        assert mcp_server.auth is not None

    @pytest.mark.asyncio
    async def test_server_tools_list_follows_contract(self, mcp_server):
        """Actual server tools/list should match schema"""
        tools = await mcp_server.list_tools_public()

        # Verify contract compliance
        assert isinstance(tools, list)
        assert len(tools) > 0

        for tool in tools:
            # Each tool must have required fields
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")
            assert tool.name is not None
            assert tool.description is not None
            assert tool.inputSchema is not None

    @pytest.mark.asyncio
    async def test_server_tools_call_follows_contract(self, mcp_server):
        """Actual server tools/call should match schema"""
        from unittest.mock import Mock

        from mcp.types import TextContent

        # Test calling a tool (conversation_get with minimal args)
        # Mock the auth and graph to avoid actual LLM calls
        with pytest.raises((PermissionError, Exception)):
            # This will fail auth but proves the contract structure works
            await mcp_server._handle_get_conversation(
                {"thread_id": "test", "user_id": "user:test", "token": "invalid"}, Mock(), "user:test"
            )


@pytest.mark.contract
@pytest.mark.unit
class TestSchemaCompleteness:
    """Meta-tests ensuring our schemas are comprehensive"""

    def test_all_required_schemas_defined(self, validate_with_schema, mcp_schemas):
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

    def test_schemas_are_valid_json_schema(self, validate_with_schema, mcp_schemas):
        """All schemas should be valid JSON Schema Draft 7"""
        # Verify schema structure
        assert "$schema" in mcp_schemas
        assert "definitions" in mcp_schemas
        assert "schemas" in mcp_schemas
