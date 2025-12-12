"""
Node Configuration Assistance Module

Provides AI-powered help for node configuration.
"""

from typing import Any


# Node type schemas
NODE_TYPE_SCHEMAS = {
    "llm": {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "The LLM model to use"},
            "temperature": {
                "type": "number",
                "minimum": 0,
                "maximum": 2,
                "description": "Sampling temperature",
            },
            "max_tokens": {"type": "integer", "description": "Maximum tokens to generate"},
            "system_prompt": {"type": "string", "description": "System prompt for the LLM"},
        },
        "required": ["model"],
    },
    "tool": {
        "type": "object",
        "properties": {
            "tool": {"type": "string", "description": "The tool to use"},
            "config": {"type": "object", "description": "Tool-specific configuration"},
        },
        "required": ["tool"],
    },
    "input": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "Input label"},
            "schema": {"type": "object", "description": "Input data schema"},
        },
    },
    "output": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "Output label"},
            "format": {
                "type": "string",
                "enum": ["json", "text", "markdown"],
                "description": "Output format",
            },
        },
    },
    "code": {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "enum": ["python", "javascript"],
                "description": "Programming language",
            },
            "code": {"type": "string", "description": "Code to execute"},
        },
        "required": ["language"],
    },
    "condition": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Condition expression"},
            "true_branch": {"type": "string", "description": "Node ID for true branch"},
            "false_branch": {"type": "string", "description": "Node ID for false branch"},
        },
        "required": ["expression"],
    },
}


class NodeTypeRegistry:
    """Registry of available node types and their schemas.

    Provides metadata about node types for configuration assistance.

    Example:
        registry = NodeTypeRegistry()
        schema = registry.get_schema("llm")
    """

    def __init__(self) -> None:
        """Initialize the node type registry."""
        self._schemas = dict(NODE_TYPE_SCHEMAS)

    def get_all_types(self) -> list[str]:
        """Get all available node types.

        Returns:
            List of node type names
        """
        return list(self._schemas.keys())

    def get_schema(self, node_type: str) -> dict[str, Any] | None:
        """Get the schema for a node type.

        Args:
            node_type: The type of node

        Returns:
            JSON Schema for the node configuration, or None if not found
        """
        return self._schemas.get(node_type)

    def register_type(self, node_type: str, schema: dict[str, Any]) -> None:
        """Register a new node type.

        Args:
            node_type: The type name
            schema: JSON Schema for the node configuration
        """
        self._schemas[node_type] = schema


class NodeConfigAssistant:
    """AI assistant for node configuration.

    Provides help, examples, and validation for node configuration.

    Example:
        assistant = NodeConfigAssistant()
        help_info = await assistant.get_help("llm", {"workflow_goal": "chatbot"})
    """

    def __init__(self) -> None:
        """Initialize the node configuration assistant."""
        self._registry = NodeTypeRegistry()

    async def get_help(
        self,
        node_type: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get configuration help for a node type.

        Args:
            node_type: The type of node
            context: Additional context (existing nodes, workflow goal, etc.)

        Returns:
            Help information including text, suggested config, and examples
        """
        context = context or {}
        return await self._invoke_llm(node_type, context)

    async def validate_config(
        self,
        node_type: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate node configuration.

        Args:
            node_type: The type of node
            config: The configuration to validate

        Returns:
            Validation result with valid flag and any errors/warnings
        """
        schema = self._registry.get_schema(node_type)

        if schema is None:
            return {
                "valid": False,
                "errors": [f"Unknown node type: {node_type}"],
                "warnings": [],
            }

        errors = []
        warnings = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Check property types (basic validation)
        properties = schema.get("properties", {})
        for key, value in config.items():
            if key in properties:
                prop_schema = properties[key]
                expected_type = prop_schema.get("type")

                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{key}' should be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field '{key}' should be a number")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field '{key}' should be an integer")
                elif expected_type == "object" and not isinstance(value, dict):
                    errors.append(f"Field '{key}' should be an object")
            else:
                warnings.append(f"Unknown field: {key}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def _invoke_llm(
        self,
        node_type: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke the LLM to generate help.

        Args:
            node_type: The type of node
            context: Additional context

        Returns:
            Help information
        """
        # Generate help based on node type
        help_info = {
            "help_text": f"Configure the {node_type} node.",
            "suggested_config": {},
            "examples": [],
        }

        if node_type == "llm":
            help_info["help_text"] = (
                "Configure the LLM node with a model and optional parameters. "
                "The model is required. Temperature controls randomness (0-2). "
                "Lower temperature = more focused, higher = more creative."
            )
            help_info["suggested_config"] = {
                "model": "gpt-4",
                "temperature": 0.7,
            }
            help_info["examples"] = [
                {
                    "name": "Creative Writing",
                    "config": {"model": "gpt-4", "temperature": 1.0},
                },
                {
                    "name": "Code Generation",
                    "config": {"model": "gpt-4", "temperature": 0.2},
                },
            ]

        elif node_type == "tool":
            help_info["help_text"] = (
                "Configure the tool node to use external capabilities. Select a tool and provide any required configuration."
            )
            help_info["suggested_config"] = {"tool": "web_search"}
            help_info["examples"] = [
                {"name": "Web Search", "config": {"tool": "web_search"}},
                {"name": "Calculator", "config": {"tool": "calculator"}},
            ]

        elif node_type == "input":
            help_info["help_text"] = (
                "Configure the input node to receive data into the workflow. Optionally specify a label and data schema."
            )
            help_info["suggested_config"] = {"label": "User Input"}

        elif node_type == "output":
            help_info["help_text"] = (
                "Configure the output node to return results from the workflow. Optionally specify a label and output format."
            )
            help_info["suggested_config"] = {"label": "Result", "format": "json"}

        # Add suggested connections if context has existing nodes
        existing_nodes = context.get("existing_nodes", [])
        if existing_nodes:
            help_info["suggested_connections"] = self._suggest_connections(node_type, existing_nodes)

        return help_info

    def _suggest_connections(
        self,
        node_type: str,
        existing_nodes: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """Suggest connections based on existing nodes.

        Args:
            node_type: The type of new node
            existing_nodes: Existing nodes in the workflow

        Returns:
            List of suggested connections
        """
        suggestions = []

        # Find potential source/target nodes
        for node in existing_nodes:
            node_id = node.get("id", "")
            existing_type = node.get("type", "")

            # Suggest connecting from input to new node
            if existing_type == "input" and node_type in ["llm", "tool", "code"]:
                suggestions.append({"from": node_id, "to": "new-node"})

            # Suggest connecting new node to output
            if existing_type == "output" and node_type in ["llm", "tool", "code"]:
                suggestions.append({"from": "new-node", "to": node_id})

        return suggestions
