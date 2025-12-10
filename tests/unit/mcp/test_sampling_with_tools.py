"""
Tests for MCP Sampling with Tools (SEP-1577).

MCP 2025-11-25 adds tools and toolChoice parameters to sampling requests,
enabling servers to request LLM completions with tool definitions.

TDD: RED phase - Define expected behavior for SEP-1577 implementation.
"""

import pytest

pytestmark = pytest.mark.unit


class TestSamplingToolTypes:
    """Test SamplingTool and ToolChoice type definitions."""

    def test_sampling_tool_model_with_all_fields(self) -> None:
        """SamplingTool should accept all fields per SEP-1577."""
        from mcp_server_langgraph.mcp.sampling import SamplingTool

        tool = SamplingTool(
            name="calculator",
            description="Perform arithmetic calculations",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                },
                "required": ["expression"],
            },
        )

        assert tool.name == "calculator"
        assert tool.description == "Perform arithmetic calculations"
        assert tool.inputSchema["type"] == "object"

    def test_sampling_tool_model_minimal_fields(self) -> None:
        """SamplingTool should work with only required fields."""
        from mcp_server_langgraph.mcp.sampling import SamplingTool

        tool = SamplingTool(
            name="simple_tool",
            inputSchema={"type": "object"},
        )

        assert tool.name == "simple_tool"
        assert tool.description is None
        assert tool.inputSchema == {"type": "object"}

    def test_tool_choice_auto_mode(self) -> None:
        """ToolChoice with type='auto' should not require name."""
        from mcp_server_langgraph.mcp.sampling import ToolChoice

        choice = ToolChoice(type="auto")

        assert choice.type == "auto"
        assert choice.name is None

    def test_tool_choice_none_mode(self) -> None:
        """ToolChoice with type='none' should not require name."""
        from mcp_server_langgraph.mcp.sampling import ToolChoice

        choice = ToolChoice(type="none")

        assert choice.type == "none"
        assert choice.name is None

    def test_tool_choice_tool_mode_requires_name(self) -> None:
        """ToolChoice with type='tool' should include tool name."""
        from mcp_server_langgraph.mcp.sampling import ToolChoice

        choice = ToolChoice(type="tool", name="calculator")

        assert choice.type == "tool"
        assert choice.name == "calculator"


class TestSamplingRequestWithTools:
    """Test SamplingRequest with tools and toolChoice parameters."""

    def test_sampling_request_with_tools(self) -> None:
        """SamplingRequest should accept tools parameter."""
        from mcp_server_langgraph.mcp.sampling import (
            SamplingMessage,
            SamplingMessageContent,
            SamplingRequest,
            SamplingTool,
        )

        tools = [
            SamplingTool(
                name="search",
                description="Search the web",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}},
            ),
        ]

        message = SamplingMessage(
            role="user",
            content=SamplingMessageContent(type="text", text="Find info about MCP"),
        )

        request = SamplingRequest(
            messages=[message],
            tools=tools,
            maxTokens=1000,
        )

        assert request.tools is not None
        assert len(request.tools) == 1
        assert request.tools[0].name == "search"

    def test_sampling_request_with_tool_choice(self) -> None:
        """SamplingRequest should accept toolChoice parameter."""
        from mcp_server_langgraph.mcp.sampling import (
            SamplingMessage,
            SamplingMessageContent,
            SamplingRequest,
            SamplingTool,
            ToolChoice,
        )

        tools = [
            SamplingTool(
                name="calculator",
                inputSchema={"type": "object"},
            ),
        ]

        message = SamplingMessage(
            role="user",
            content=SamplingMessageContent(type="text", text="Calculate 2+2"),
        )

        request = SamplingRequest(
            messages=[message],
            tools=tools,
            toolChoice=ToolChoice(type="tool", name="calculator"),
            maxTokens=500,
        )

        assert request.toolChoice is not None
        assert request.toolChoice.type == "tool"
        assert request.toolChoice.name == "calculator"

    def test_sampling_request_to_jsonrpc_includes_tools(self) -> None:
        """to_jsonrpc should include tools and toolChoice in params."""
        from mcp_server_langgraph.mcp.sampling import (
            SamplingMessage,
            SamplingMessageContent,
            SamplingRequest,
            SamplingTool,
            ToolChoice,
        )

        tools = [
            SamplingTool(
                name="test_tool",
                description="A test tool",
                inputSchema={"type": "object"},
            ),
        ]

        request = SamplingRequest(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
            tools=tools,
            toolChoice=ToolChoice(type="auto"),
            maxTokens=100,
        )

        jsonrpc = request.to_jsonrpc()

        assert "params" in jsonrpc
        params = jsonrpc["params"]
        assert "tools" in params
        assert len(params["tools"]) == 1
        assert params["tools"][0]["name"] == "test_tool"
        assert "toolChoice" in params
        assert params["toolChoice"]["type"] == "auto"


class TestSamplingHandlerWithTools:
    """Test SamplingHandler methods with tools support."""

    def test_create_request_with_tools(self) -> None:
        """create_request should accept tools parameter."""
        from mcp_server_langgraph.mcp.sampling import (
            SamplingHandler,
            SamplingMessage,
            SamplingMessageContent,
            SamplingTool,
            ToolChoice,
        )

        handler = SamplingHandler()

        tools = [
            SamplingTool(
                name="web_search",
                description="Search the web",
                inputSchema={"type": "object", "properties": {"q": {"type": "string"}}},
            ),
        ]

        message = SamplingMessage(
            role="user",
            content=SamplingMessageContent(type="text", text="Search for MCP"),
        )

        request = handler.create_request(
            messages=[message],
            tools=tools,
            tool_choice=ToolChoice(type="auto"),
            max_tokens=500,
        )

        assert request.tools is not None
        assert len(request.tools) == 1
        assert request.tools[0].name == "web_search"
        assert request.toolChoice is not None
        assert request.toolChoice.type == "auto"
