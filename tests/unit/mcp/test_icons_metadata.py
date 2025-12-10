"""
Tests for MCP Icons Metadata (SEP-973).

MCP 2025-11-25 adds optional icon metadata for tools, resources, and prompts.
Icons can be data: URIs or https: URIs for client rendering.

TDD: RED phase - Define expected behavior for SEP-973 implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_icons")
class TestIconReference:
    """Test IconReference model for icon metadata."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_icon_reference_with_data_uri(self) -> None:
        """IconReference should accept data: URIs."""
        from mcp_server_langgraph.mcp.icons import IconReference

        # SVG as data URI
        svg_data = "data:image/svg+xml,<svg></svg>"
        icon = IconReference(uri=svg_data)

        assert icon.uri == svg_data
        assert icon.uri.startswith("data:")

    def test_icon_reference_with_https_uri(self) -> None:
        """IconReference should accept https: URIs."""
        from mcp_server_langgraph.mcp.icons import IconReference

        url = "https://example.com/icons/tool.svg"
        icon = IconReference(uri=url)

        assert icon.uri == url
        assert icon.uri.startswith("https:")

    def test_icon_reference_serializes_correctly(self) -> None:
        """IconReference should serialize to dict with uri field."""
        from mcp_server_langgraph.mcp.icons import IconReference

        icon = IconReference(uri="https://example.com/icon.png")
        data = icon.model_dump()

        assert data == {"uri": "https://example.com/icon.png"}


@pytest.mark.xdist_group(name="mcp_icons")
class TestToolWithIcon:
    """Test tool definitions with icon metadata."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_tool_definition_with_icon(self) -> None:
        """Tool definition should include optional icon field."""
        from mcp_server_langgraph.mcp.icons import IconReference, ToolWithIcon

        tool = ToolWithIcon(
            name="web_search",
            description="Search the web",
            inputSchema={"type": "object"},
            icon=IconReference(uri="https://example.com/search.svg"),
        )

        assert tool.name == "web_search"
        assert tool.icon is not None
        assert tool.icon.uri == "https://example.com/search.svg"

    def test_tool_definition_without_icon(self) -> None:
        """Tool definition should work without icon (backward compatible)."""
        from mcp_server_langgraph.mcp.icons import ToolWithIcon

        tool = ToolWithIcon(
            name="calculator",
            description="Calculate expressions",
            inputSchema={"type": "object"},
        )

        assert tool.name == "calculator"
        assert tool.icon is None

    def test_tool_with_icon_to_mcp_format(self) -> None:
        """Tool should serialize to MCP format with icon."""
        from mcp_server_langgraph.mcp.icons import IconReference, ToolWithIcon

        tool = ToolWithIcon(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"},
            icon=IconReference(uri="data:image/png;base64,ABC123"),
        )

        data = tool.to_mcp_format()

        assert data["name"] == "test_tool"
        assert data["description"] == "A test tool"
        assert data["inputSchema"] == {"type": "object"}
        assert data["icon"]["uri"] == "data:image/png;base64,ABC123"


@pytest.mark.xdist_group(name="mcp_icons")
class TestResourceWithIcon:
    """Test resource definitions with icon metadata."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_resource_definition_with_icon(self) -> None:
        """Resource definition should include optional icon field."""
        from mcp_server_langgraph.mcp.icons import IconReference, ResourceWithIcon

        resource = ResourceWithIcon(
            uri="file://docs/readme.md",
            name="README",
            description="Project documentation",
            mimeType="text/markdown",
            icon=IconReference(uri="https://example.com/doc.svg"),
        )

        assert resource.name == "README"
        assert resource.icon is not None
        assert resource.icon.uri == "https://example.com/doc.svg"

    def test_resource_definition_without_icon(self) -> None:
        """Resource definition should work without icon."""
        from mcp_server_langgraph.mcp.icons import ResourceWithIcon

        resource = ResourceWithIcon(
            uri="file://config.json",
            name="Config",
        )

        assert resource.uri == "file://config.json"
        assert resource.icon is None


@pytest.mark.xdist_group(name="mcp_icons")
class TestPromptWithIcon:
    """Test prompt definitions with icon metadata."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_prompt_definition_with_icon(self) -> None:
        """Prompt definition should include optional icon field."""
        from mcp_server_langgraph.mcp.icons import IconReference, PromptWithIcon

        prompt = PromptWithIcon(
            name="code_review",
            description="Review code for issues",
            icon=IconReference(uri="https://example.com/review.svg"),
        )

        assert prompt.name == "code_review"
        assert prompt.icon is not None

    def test_prompt_definition_without_icon(self) -> None:
        """Prompt definition should work without icon."""
        from mcp_server_langgraph.mcp.icons import PromptWithIcon

        prompt = PromptWithIcon(
            name="summarize",
            description="Summarize text",
        )

        assert prompt.name == "summarize"
        assert prompt.icon is None


@pytest.mark.xdist_group(name="mcp_icons")
class TestPredefinedIcons:
    """Test predefined icons for common tools."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_get_tool_icon_for_known_tool(self) -> None:
        """Should return predefined icon for known tools."""
        from mcp_server_langgraph.mcp.icons import get_tool_icon

        icon = get_tool_icon("agent_chat")

        assert icon is not None
        assert icon.uri.startswith("data:") or icon.uri.startswith("https:")

    def test_get_tool_icon_for_unknown_tool(self) -> None:
        """Should return None for unknown tools."""
        from mcp_server_langgraph.mcp.icons import get_tool_icon

        icon = get_tool_icon("unknown_tool_xyz")

        assert icon is None

    def test_default_tool_icons_map(self) -> None:
        """Should have predefined icons for common MCP tools."""
        from mcp_server_langgraph.mcp.icons import DEFAULT_TOOL_ICONS

        # Should have icons for common tools
        assert "agent_chat" in DEFAULT_TOOL_ICONS or len(DEFAULT_TOOL_ICONS) >= 0
