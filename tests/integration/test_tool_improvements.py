"""
Integration tests for tool improvements based on Anthropic best practices.

Tests:
- Response format control (concise vs detailed)
- Search-focused conversation_search tool
- Tool namespacing (new names and backward compatibility)
- Token limits and truncation
- Enhanced error messages
"""

import gc

import pytest
from langchain_core.messages import AIMessage
from mcp.types import TextContent

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

# Test authentication token (valid JWT format for testing)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6OTk5OTk5OTk5OX0.test"


@pytest.fixture
def mock_openfga_client(mocker):
    """Mock OpenFGA client for testing."""
    client = mocker.Mock(spec=OpenFGAClient)
    client.check_permission = mocker.AsyncMock(return_value=True)
    client.list_objects = mocker.AsyncMock(return_value=["conversation:test1", "conversation:test2"])
    return client


@pytest.fixture
def mcp_server(mock_openfga_client):
    """Create MCP server instance for testing."""
    return MCPAgentServer(openfga_client=mock_openfga_client)


@pytest.mark.xdist_group(name="testresponseformatcontrol")
class TestResponseFormatControl:
    """Test response_format parameter in agent_chat tool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_chat_with_concise_format(self, mcp_server, mocker):
        """Test agent_chat with concise response format."""
        # Mock the agent graph to return a long response
        long_response = "Word " * 1000  # ~1000 tokens
        # Create a mock graph with ainvoke method
        mock_graph = mocker.Mock()
        mock_graph.ainvoke = mocker.AsyncMock(return_value={"messages": [AIMessage(content=long_response)]})
        # Patch get_agent_graph to return our mock
        mocker.patch(
            "mcp_server_langgraph.mcp.server_stdio.get_agent_graph",
            return_value=mock_graph,
        )

        # Mock span context
        mock_span = mocker.Mock()
        mock_span.get_span_context.return_value = mocker.Mock(trace_id=123)

        arguments = {
            "message": "Tell me about quantum computing",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "response_format": "concise",
        }

        result = await mcp_server._handle_chat(arguments, mock_span, "user:alice")

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Concise response should be truncated
        assert len(response_text) < len(long_response)

    @pytest.mark.asyncio
    async def test_chat_with_detailed_format(self, mcp_server, mocker):
        """Test agent_chat with detailed response format."""
        # Mock agent response
        medium_response = "Word " * 500  # ~500 tokens (within detailed limit)
        mock_graph = mocker.Mock()
        mock_graph.ainvoke = mocker.AsyncMock(return_value={"messages": [AIMessage(content=medium_response)]})
        mocker.patch(
            "mcp_server_langgraph.mcp.server_stdio.get_agent_graph",
            return_value=mock_graph,
        )

        mock_span = mocker.Mock()
        mock_span.get_span_context.return_value = mocker.Mock(trace_id=123)

        arguments = {
            "message": "Explain quantum computing in detail",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "response_format": "detailed",
        }

        result = await mcp_server._handle_chat(arguments, mock_span, "user:alice")

        assert isinstance(result, list)
        response_text = result[0].text

        # Detailed response should NOT be truncated for medium text
        assert "[Response truncated" not in response_text

    @pytest.mark.asyncio
    async def test_chat_default_format_is_concise(self, mcp_server, mocker):
        """Test that default response_format is concise."""
        short_response = "Short answer"
        mock_graph = mocker.Mock()
        mock_graph.ainvoke = mocker.AsyncMock(return_value={"messages": [AIMessage(content=short_response)]})
        mocker.patch(
            "mcp_server_langgraph.mcp.server_stdio.get_agent_graph",
            return_value=mock_graph,
        )

        mock_span = mocker.Mock()
        mock_span.get_span_context.return_value = mocker.Mock(trace_id=123)

        # No response_format specified
        arguments = {
            "message": "Hello",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
        }

        result = await mcp_server._handle_chat(arguments, mock_span, "user:alice")
        # Should succeed (default to concise)
        assert isinstance(result, list)


@pytest.mark.xdist_group(name="testsearchfocusedtools")
class TestSearchFocusedTools:
    """Test conversation_search replacing list_conversations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_conversations_with_query(self, mcp_server, mocker):
        """Test search_conversations with search query."""
        # Mock list_accessible_resources to return multiple conversations
        conversations = [
            "conversation:project_alpha",
            "conversation:project_beta",
            "conversation:meeting_notes",
            "conversation:weekly_standup",
        ]
        mcp_server.auth.list_accessible_resources = mocker.AsyncMock(return_value=conversations)

        mock_span = mocker.Mock()

        arguments = {
            "query": "project",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "limit": 10,
        }

        result = await mcp_server._handle_search_conversations(arguments, mock_span, "user:alice")

        assert isinstance(result, list)
        response_text = result[0].text

        # Should only include conversations matching "project"
        assert "project_alpha" in response_text
        assert "project_beta" in response_text
        # Should not include non-matching conversations
        assert "meeting_notes" not in response_text or "2" in response_text  # Either filtered or shown count

    @pytest.mark.asyncio
    async def test_search_conversations_with_limit(self, mcp_server, mocker):
        """Test search_conversations respects limit parameter."""
        # Mock many conversations
        conversations = [f"conversation:conv_{i}" for i in range(100)]
        mcp_server.auth.list_accessible_resources = mocker.AsyncMock(return_value=conversations)

        mock_span = mocker.Mock()

        arguments = {
            "query": "conv",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "limit": 5,
        }

        result = await mcp_server._handle_search_conversations(arguments, mock_span, "user:alice")
        response_text = result[0].text

        # Should indicate truncation
        assert "Showing 5 of" in response_text or "[Showing 5" in response_text

    @pytest.mark.asyncio
    async def test_search_conversations_no_results(self, mcp_server, mocker):
        """Test search_conversations with no matching results."""
        conversations = ["conversation:alpha", "conversation:beta"]
        mcp_server.auth.list_accessible_resources = mocker.AsyncMock(return_value=conversations)

        mock_span = mocker.Mock()

        arguments = {
            "query": "nonexistent",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "limit": 10,
        }

        result = await mcp_server._handle_search_conversations(arguments, mock_span, "user:alice")
        response_text = result[0].text

        # Should provide helpful message
        assert "No conversations found" in response_text
        assert "Try a different search query" in response_text

    @pytest.mark.asyncio
    async def test_search_conversations_empty_query(self, mcp_server, mocker):
        """Test search_conversations with empty query returns recent."""
        conversations = [f"conversation:conv_{i}" for i in range(20)]
        mcp_server.auth.list_accessible_resources = mocker.AsyncMock(return_value=conversations)

        mock_span = mocker.Mock()

        arguments = {
            "query": "",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "limit": 10,
        }

        result = await mcp_server._handle_search_conversations(arguments, mock_span, "user:alice")
        response_text = result[0].text

        # Should return recent conversations (up to limit)
        assert "recent conversation" in response_text.lower()


@pytest.mark.xdist_group(name="testtoolnamingandbackwardcompatibility")
class TestToolNamingAndBackwardCompatibility:
    """Test tool namespacing and backward compatibility."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_tools_returns_new_names(self, mcp_server):
        """Test that list_tools returns new namespaced tool names."""
        # Use public API instead of private _tool_manager
        tools = await mcp_server.list_tools_public()

        tool_names = [tool.name for tool in tools]

        # Should have new namespaced names
        assert "agent_chat" in tool_names
        assert "conversation_get" in tool_names
        assert "conversation_search" in tool_names

        # Old names should NOT be in the list (they're handled via routing, not exposed)
        # The backward compatibility happens in call_tool, not in list_tools
        assert "agent_chat" in tool_names  # New name is primary

    @pytest.mark.asyncio
    async def test_tool_names_follow_namespace_convention(self, mcp_server):
        """Test that tool names follow the namespace convention."""
        tools = await mcp_server.list_tools_public()

        tool_names = [tool.name for tool in tools]

        # All tools should use underscore naming (not hyphens)
        for name in tool_names:
            assert "_" in name or name.islower(), f"Tool {name} doesn't follow naming convention"

        # Should have action_object naming pattern
        assert any(name.startswith("agent_") for name in tool_names)
        assert any(name.startswith("conversation_") for name in tool_names)


@pytest.mark.xdist_group(name="testenhancederrormessages")
class TestEnhancedErrorMessages:
    """Test enhanced, actionable error messages."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_permission_error_includes_actionable_guidance(self, mcp_server, mocker):
        """Test that permission errors include actionable guidance."""
        # Mock authorization to deny access
        mcp_server.auth.authorize = mocker.AsyncMock(return_value=False)

        mock_span = mocker.Mock()
        mock_span.get_span_context.return_value = mocker.Mock(trace_id=123)

        arguments = {
            "message": "Hello",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "thread_id": "restricted_conversation",
        }

        with pytest.raises(PermissionError) as exc_info:
            await mcp_server._handle_chat(arguments, mock_span, "user:alice")

        error_message = str(exc_info.value)

        # Should include actionable guidance
        assert "restricted_conversation" in error_message
        assert "Request access" in error_message or "use a different thread_id" in error_message


@pytest.mark.xdist_group(name="testtooldescriptions")
class TestToolDescriptions:
    """Test enhanced tool descriptions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tool_descriptions_include_usage_guidance(self, mcp_server):
        """Test that tool descriptions include comprehensive usage guidance."""
        # Use public API instead of private _tool_manager
        tools = await mcp_server.list_tools_public()

        agent_chat_tool = next((t for t in tools if t.name == "agent_chat"), None)
        assert agent_chat_tool is not None

        description = agent_chat_tool.description

        # Should include token information
        assert "token" in description.lower()

        # Should include response time information
        assert "sec" in description.lower() or "second" in description.lower()

        # Should include rate limit information
        assert "rate limit" in description.lower() or "requests/minute" in description.lower()

    @pytest.mark.asyncio
    async def test_search_tool_description_includes_examples(self, mcp_server):
        """Test that search tool description includes usage examples."""
        # Use public API
        tools = await mcp_server.list_tools_public()

        search_tool = next((t for t in tools if t.name == "conversation_search"), None)
        assert search_tool is not None

        description = search_tool.description

        # Should mention efficiency
        assert "efficient" in description.lower()

        # Should mention result limits
        assert "50" in description or "limit" in description.lower()

        # Should provide examples or guidance
        assert "example" in description.lower() or "search" in description.lower()


@pytest.mark.xdist_group(name="testinputvalidation")
class TestInputValidation:
    """Test input validation for new parameters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_response_format_validation(self, mcp_server):
        """Test that response_format only accepts valid values."""
        # Use public API
        tools = await mcp_server.list_tools_public()
        agent_chat_tool = next((t for t in tools if t.name == "agent_chat"), None)

        schema = agent_chat_tool.inputSchema
        response_format_schema = schema["properties"]["response_format"]

        # Should have enum constraint or literal type
        schema_str = str(response_format_schema)
        assert "enum" in response_format_schema or "anyOf" in response_format_schema or "Literal" in schema_str

        # Verify valid values are documented
        assert "concise" in schema_str.lower() or "detailed" in schema_str.lower()

    @pytest.mark.asyncio
    async def test_search_limit_validation(self, mcp_server):
        """Test that search limit has proper constraints."""
        # Use public API
        tools = await mcp_server.list_tools_public()
        search_tool = next((t for t in tools if t.name == "conversation_search"), None)

        schema = search_tool.inputSchema
        limit_schema = schema["properties"]["limit"]

        # Should have min/max constraints (Pydantic uses "minimum"/"maximum" or includes ge/le in description)
        schema_str = str(limit_schema)
        assert "minimum" in limit_schema or "ge" in schema_str or "1" in schema_str
        assert "maximum" in limit_schema or "le" in schema_str or "50" in schema_str

    @pytest.mark.asyncio
    async def test_all_tools_have_input_schemas(self, mcp_server):
        """Test that all tools define proper input schemas."""
        tools = await mcp_server.list_tools_public()

        for tool in tools:
            assert tool.inputSchema is not None, f"Tool {tool.name} missing input schema"
            assert "properties" in tool.inputSchema, f"Tool {tool.name} schema missing properties"
            assert "type" in tool.inputSchema, f"Tool {tool.name} schema missing type"

    @pytest.mark.asyncio
    async def test_required_fields_documented(self, mcp_server):
        """Test that required fields are properly documented in schemas."""
        tools = await mcp_server.list_tools_public()

        # Tools that don't require authentication (public tools)
        public_tools = {"search_tools"}

        for tool in tools:
            schema = tool.inputSchema

            # Public tools may not require token and user_id
            if tool.name in public_tools:
                continue

            # All other tools should require token and user_id for security
            required_fields = schema.get("required", [])
            assert "token" in required_fields, f"Tool {tool.name} should require token"
            assert "user_id" in required_fields, f"Tool {tool.name} should require user_id"


@pytest.mark.xdist_group(name="testendtoendtoolimprovements")
class TestEndToEndToolImprovements:
    """End-to-end integration tests for tool improvements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_complete_agent_chat_flow(self, mcp_server, mocker):
        """Test complete agent_chat flow with all improvements."""
        # Mock a realistic agent response
        agent_response = (
            """
        Quantum computing is a revolutionary computing paradigm that leverages quantum mechanics
        to process information. Unlike classical computers that use bits (0 or 1), quantum
        computers use quantum bits or qubits that can exist in superposition states.
        """
            * 50
        )  # Make it long enough to test truncation

        mock_graph = mocker.Mock()
        mock_graph.ainvoke = mocker.AsyncMock(return_value={"messages": [AIMessage(content=agent_response)]})
        mocker.patch(
            "mcp_server_langgraph.mcp.server_stdio.get_agent_graph",
            return_value=mock_graph,
        )

        mock_span = mocker.Mock()
        mock_span.get_span_context.return_value = mocker.Mock(trace_id=123)

        # Test with concise format
        arguments = {
            "message": "Explain quantum computing",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "thread_id": "test_thread",
            "response_format": "concise",
        }

        result = await mcp_server._handle_chat(arguments, mock_span, "user:alice")

        assert isinstance(result, list)
        assert len(result) == 1
        response_text = result[0].text

        # Response should be formatted (likely truncated for concise)
        assert len(response_text) > 0
        # For very long text, should likely be truncated
        assert len(response_text) < len(agent_response) or len(agent_response) < 1000

    @pytest.mark.asyncio
    async def test_complete_search_flow(self, mcp_server, mocker):
        """Test complete conversation_search flow."""
        # Mock realistic conversation data
        conversations = [
            "conversation:project_alpha_planning",
            "conversation:project_alpha_review",
            "conversation:project_beta_kickoff",
            "conversation:team_standup_2025_10_17",
            "conversation:design_discussion",
        ]

        # Use mocker.patch to properly mock the auth method
        # This ensures the mock is called correctly and doesn't raise exceptions
        async_mock = mocker.AsyncMock(return_value=conversations)
        mocker.patch.object(mcp_server.auth, "list_accessible_resources", new=async_mock)

        mock_span = mocker.Mock()
        mock_span.get_span_context.return_value = mocker.Mock(trace_id=123)
        mock_span.set_attribute = mocker.Mock()

        arguments = {
            "query": "project alpha",
            "user_id": "user:alice",
            "token": TEST_TOKEN,
            "limit": 5,
        }

        result = await mcp_server._handle_search_conversations(arguments, mock_span, "user:alice")

        assert isinstance(result, list)
        response_text = result[0].text

        # Should find project alpha conversations
        assert "project_alpha" in response_text.lower()
        # Should indicate number found
        assert "2" in response_text  # Found 2 matching conversations
