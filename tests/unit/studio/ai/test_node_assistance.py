"""
Node Configuration Assistance Tests

Tests for AI-powered node configuration help.
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_node_assistance")
class TestNodeConfigAssistant:
    """Tests for the node configuration assistant."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_node_config_assistant_init_creates_instance(self) -> None:
        """GIVEN NodeConfigAssistant class
        WHEN instantiated
        THEN should initialize successfully
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeConfigAssistant

        assistant = NodeConfigAssistant()
        assert assistant is not None
        assert hasattr(assistant, "get_help")

    @pytest.mark.asyncio
    async def test_get_help_returns_configuration_guidance(self) -> None:
        """GIVEN node type and context
        WHEN calling get_help()
        THEN should return configuration guidance
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeConfigAssistant

        assistant = NodeConfigAssistant()

        with patch.object(assistant, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "help_text": "Configure the LLM node with a model and temperature.",
                "suggested_config": {"model": "gpt-4", "temperature": 0.7},
            }

            result = await assistant.get_help(
                node_type="llm",
                context={"workflow_goal": "Build a chatbot"},
            )

            assert "help_text" in result
            assert "suggested_config" in result

    @pytest.mark.asyncio
    async def test_get_help_suggests_connections(self) -> None:
        """GIVEN existing workflow context
        WHEN calling get_help()
        THEN should suggest node connections
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeConfigAssistant

        assistant = NodeConfigAssistant()

        with patch.object(assistant, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "help_text": "Connect to the output node.",
                "suggested_connections": [{"from": "llm-1", "to": "output-1"}],
            }

            result = await assistant.get_help(
                node_type="llm",
                context={
                    "existing_nodes": [
                        {"id": "input-1", "type": "input"},
                        {"id": "output-1", "type": "output"},
                    ]
                },
            )

            assert "suggested_connections" in result

    @pytest.mark.asyncio
    async def test_get_help_includes_examples(self) -> None:
        """GIVEN node type
        WHEN calling get_help()
        THEN should include configuration examples
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeConfigAssistant

        assistant = NodeConfigAssistant()

        with patch.object(assistant, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "help_text": "Use tool nodes for external integrations.",
                "examples": [
                    {"name": "Web Search", "config": {"tool": "web_search"}},
                    {"name": "Calculator", "config": {"tool": "calculator"}},
                ],
            }

            result = await assistant.get_help(
                node_type="tool",
                context={},
            )

            assert "examples" in result

    @pytest.mark.asyncio
    async def test_validate_config_checks_requirements(self) -> None:
        """GIVEN node configuration
        WHEN calling validate_config()
        THEN should check required fields
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeConfigAssistant

        assistant = NodeConfigAssistant()

        result = await assistant.validate_config(
            node_type="llm",
            config={"temperature": 0.7},  # Missing model
        )

        assert "valid" in result
        assert "errors" in result or "warnings" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_node_assistance")
class TestNodeTypeRegistry:
    """Tests for the node type registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registry_has_built_in_types(self) -> None:
        """GIVEN NodeTypeRegistry
        WHEN accessing types
        THEN should have built-in node types
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeTypeRegistry

        registry = NodeTypeRegistry()
        types = registry.get_all_types()

        assert "llm" in types
        assert "tool" in types
        assert "input" in types
        assert "output" in types

    def test_registry_provides_schema_for_type(self) -> None:
        """GIVEN node type
        WHEN calling get_schema()
        THEN should return configuration schema
        """
        from mcp_server_langgraph.studio.ai.node_config import NodeTypeRegistry

        registry = NodeTypeRegistry()
        schema = registry.get_schema("llm")

        assert schema is not None
        assert "properties" in schema or hasattr(schema, "properties")
