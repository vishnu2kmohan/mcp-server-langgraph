"""
Tests for MCP Enhanced Enum Schema (SEP-1330).

MCP 2025-11-25 adds enumNames and default values to elicitation schemas,
enabling better UI rendering with human-readable labels and default selections.

TDD: RED phase - Define expected behavior for SEP-1330 implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_elicitation_enum")
class TestEnhancedEnumSchema:
    """Test enhanced enum schema with enumNames and defaults."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_elicitation_schema_with_enum_names(self) -> None:
        """ElicitationSchema should support enumNames for human-readable labels."""
        from mcp_server_langgraph.mcp.elicitation import ElicitationSchema

        schema = ElicitationSchema(
            type="object",
            properties={
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "enumNames": ["Low Priority", "Medium Priority", "High Priority", "Critical - Urgent"],
                    "description": "Select task priority",
                },
            },
            required=["priority"],
        )

        assert "enumNames" in schema.properties["priority"]
        assert schema.properties["priority"]["enumNames"] == [
            "Low Priority",
            "Medium Priority",
            "High Priority",
            "Critical - Urgent",
        ]

    def test_elicitation_schema_with_default_value(self) -> None:
        """ElicitationSchema should support default values."""
        from mcp_server_langgraph.mcp.elicitation import ElicitationSchema

        schema = ElicitationSchema(
            type="object",
            properties={
                "notify": {
                    "type": "boolean",
                    "default": True,
                    "description": "Send notification?",
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "csv", "xml"],
                    "default": "json",
                    "description": "Output format",
                },
            },
        )

        assert schema.properties["notify"]["default"] is True
        assert schema.properties["format"]["default"] == "json"

    def test_elicitation_schema_to_jsonrpc_preserves_enum_names(self) -> None:
        """to_jsonrpc should preserve enumNames in schema."""
        from mcp_server_langgraph.mcp.elicitation import (
            Elicitation,
            ElicitationSchema,
        )

        schema = ElicitationSchema(
            type="object",
            properties={
                "action": {
                    "type": "string",
                    "enum": ["approve", "reject", "defer"],
                    "enumNames": ["Approve Request", "Reject Request", "Defer for Later"],
                    "default": "approve",
                },
            },
            required=["action"],
        )

        elicitation = Elicitation(
            id="test-123",
            request_id=1,
            message="Please select an action",
            requestedSchema=schema,
        )

        jsonrpc = elicitation.to_jsonrpc()

        # Verify enumNames are preserved in the JSON-RPC output
        action_prop = jsonrpc["params"]["requestedSchema"]["properties"]["action"]
        assert "enumNames" in action_prop
        assert action_prop["enumNames"] == ["Approve Request", "Reject Request", "Defer for Later"]
        assert action_prop["default"] == "approve"


@pytest.mark.xdist_group(name="mcp_elicitation_enum")
class TestEnumSchemaModel:
    """Test dedicated EnumSchema model for complex enums."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_enum_schema_with_all_fields(self) -> None:
        """EnumSchema should accept all SEP-1330 fields."""
        from mcp_server_langgraph.mcp.elicitation import EnumSchema

        enum_schema = EnumSchema(
            type="string",
            enum=["draft", "pending", "approved", "rejected"],
            enumNames=["Draft", "Pending Review", "Approved", "Rejected"],
            default="draft",
            title="Document Status",
            description="Current status of the document",
        )

        assert enum_schema.type == "string"
        assert len(enum_schema.enum) == 4
        assert len(enum_schema.enumNames) == 4
        assert enum_schema.default == "draft"
        assert enum_schema.title == "Document Status"

    def test_enum_schema_minimal(self) -> None:
        """EnumSchema should work with just required fields."""
        from mcp_server_langgraph.mcp.elicitation import EnumSchema

        enum_schema = EnumSchema(
            enum=["yes", "no"],
        )

        assert enum_schema.type == "string"  # Default type
        assert enum_schema.enum == ["yes", "no"]
        assert enum_schema.enumNames is None
        assert enum_schema.default is None

    def test_enum_schema_to_dict(self) -> None:
        """EnumSchema should serialize correctly."""
        from mcp_server_langgraph.mcp.elicitation import EnumSchema

        enum_schema = EnumSchema(
            enum=["a", "b", "c"],
            enumNames=["Option A", "Option B", "Option C"],
            default="b",
        )

        data = enum_schema.model_dump()

        assert data["enum"] == ["a", "b", "c"]
        assert data["enumNames"] == ["Option A", "Option B", "Option C"]
        assert data["default"] == "b"
