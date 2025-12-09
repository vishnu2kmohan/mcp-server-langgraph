"""
Tests for MCP Elicitation Protocol (2025-06-18 Spec).

Tests the elicitation/create endpoint that allows servers to request
user input via JSON schema forms. Clients respond with accept/decline/cancel.
"""

import gc
import uuid
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.mcp.elicitation import (
    ElicitationAction,
    ElicitationHandler,
    ElicitationRequest,
    ElicitationResponse,
    ElicitationSchema,
)

# Module-level marker for test categorization
pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="mcp_elicitation")
@pytest.mark.unit
class TestElicitationModels:
    """Test elicitation data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_elicitation_schema_string_type(self) -> None:
        """Test string type schema validation."""
        schema = ElicitationSchema(
            type="object",
            properties={
                "name": {
                    "type": "string",
                    "description": "User name",
                    "minLength": 1,
                    "maxLength": 100,
                }
            },
            required=["name"],
        )
        assert schema.type == "object"
        assert "name" in schema.properties
        assert schema.required == ["name"]

    def test_elicitation_schema_boolean_type(self) -> None:
        """Test boolean type schema for approval."""
        schema = ElicitationSchema(
            type="object",
            properties={
                "approved": {
                    "type": "boolean",
                    "description": "Approve this action?",
                }
            },
            required=["approved"],
        )
        assert schema.properties["approved"]["type"] == "boolean"

    def test_elicitation_schema_enum_type(self) -> None:
        """Test enum type schema for dropdown select."""
        schema = ElicitationSchema(
            type="object",
            properties={
                "choice": {
                    "type": "string",
                    "enum": ["option1", "option2", "option3"],
                    "enumNames": ["Option 1", "Option 2", "Option 3"],
                }
            },
            required=["choice"],
        )
        assert "enum" in schema.properties["choice"]
        assert len(schema.properties["choice"]["enum"]) == 3

    def test_elicitation_schema_number_with_constraints(self) -> None:
        """Test number type with min/max constraints."""
        schema = ElicitationSchema(
            type="object",
            properties={
                "age": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 150,
                }
            },
            required=["age"],
        )
        assert schema.properties["age"]["minimum"] == 0
        assert schema.properties["age"]["maximum"] == 150

    def test_elicitation_request_creation(self) -> None:
        """Test elicitation request model."""
        request = ElicitationRequest(
            id=str(uuid.uuid4()),
            message="Please provide your name",
            requestedSchema=ElicitationSchema(
                type="object",
                properties={"name": {"type": "string"}},
                required=["name"],
            ),
        )
        assert request.message == "Please provide your name"
        assert request.requestedSchema.type == "object"

    def test_elicitation_response_accept(self) -> None:
        """Test accept response with content."""
        response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content={"name": "John Doe"},
        )
        assert response.action == ElicitationAction.ACCEPT
        assert response.content["name"] == "John Doe"

    def test_elicitation_response_decline(self) -> None:
        """Test decline response (no content)."""
        response = ElicitationResponse(action=ElicitationAction.DECLINE)
        assert response.action == ElicitationAction.DECLINE
        assert response.content is None

    def test_elicitation_response_cancel(self) -> None:
        """Test cancel response (user dismissed)."""
        response = ElicitationResponse(action=ElicitationAction.CANCEL)
        assert response.action == ElicitationAction.CANCEL


@pytest.mark.xdist_group(name="mcp_elicitation")
@pytest.mark.unit
class TestElicitationHandler:
    """Test ElicitationHandler for managing elicitation requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> ElicitationHandler:
        """Create a fresh elicitation handler."""
        return ElicitationHandler()

    def test_create_elicitation_with_schema_returns_pending_status(self, handler: ElicitationHandler) -> None:
        """Test creating a new elicitation request."""
        elicitation = handler.create_elicitation(
            message="Approve this action?",
            schema=ElicitationSchema(
                type="object",
                properties={"approved": {"type": "boolean"}},
                required=["approved"],
            ),
        )
        assert elicitation.id is not None
        assert elicitation.message == "Approve this action?"
        assert elicitation.status == "pending"

    def test_get_pending_elicitation(self, handler: ElicitationHandler) -> None:
        """Test retrieving pending elicitation."""
        elicitation = handler.create_elicitation(
            message="Test",
            schema=ElicitationSchema(
                type="object",
                properties={"test": {"type": "string"}},
                required=[],
            ),
        )
        pending = handler.get_pending_elicitation(elicitation.id)
        assert pending is not None
        assert pending.id == elicitation.id

    def test_respond_with_accept(self, handler: ElicitationHandler) -> None:
        """Test responding to elicitation with accept."""
        elicitation = handler.create_elicitation(
            message="Enter name",
            schema=ElicitationSchema(
                type="object",
                properties={"name": {"type": "string"}},
                required=["name"],
            ),
        )

        response = handler.respond(
            elicitation_id=elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={"name": "Test User"},
        )

        assert response.action == ElicitationAction.ACCEPT
        assert response.content["name"] == "Test User"
        assert handler.get_pending_elicitation(elicitation.id) is None

    def test_respond_with_decline(self, handler: ElicitationHandler) -> None:
        """Test responding to elicitation with decline."""
        elicitation = handler.create_elicitation(
            message="Approve?",
            schema=ElicitationSchema(
                type="object",
                properties={"approved": {"type": "boolean"}},
                required=["approved"],
            ),
        )

        response = handler.respond(
            elicitation_id=elicitation.id,
            action=ElicitationAction.DECLINE,
        )

        assert response.action == ElicitationAction.DECLINE

    def test_respond_with_cancel(self, handler: ElicitationHandler) -> None:
        """Test responding to elicitation with cancel (user dismissed)."""
        elicitation = handler.create_elicitation(
            message="Test",
            schema=ElicitationSchema(
                type="object",
                properties={},
                required=[],
            ),
        )

        response = handler.respond(
            elicitation_id=elicitation.id,
            action=ElicitationAction.CANCEL,
        )

        assert response.action == ElicitationAction.CANCEL

    def test_respond_to_nonexistent_elicitation(self, handler: ElicitationHandler) -> None:
        """Test error when responding to nonexistent elicitation."""
        with pytest.raises(ValueError, match="not found"):
            handler.respond(
                elicitation_id="nonexistent-id",
                action=ElicitationAction.ACCEPT,
                content={},
            )

    def test_validate_response_against_schema(self, handler: ElicitationHandler) -> None:
        """Test that response content is validated against schema."""
        elicitation = handler.create_elicitation(
            message="Enter age",
            schema=ElicitationSchema(
                type="object",
                properties={
                    "age": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 150,
                    }
                },
                required=["age"],
            ),
        )

        # Valid response
        response = handler.respond(
            elicitation_id=elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={"age": 25},
        )
        assert response.content["age"] == 25

    def test_list_pending_elicitations(self, handler: ElicitationHandler) -> None:
        """Test listing all pending elicitations."""
        handler.create_elicitation(
            message="First",
            schema=ElicitationSchema(type="object", properties={}, required=[]),
        )
        handler.create_elicitation(
            message="Second",
            schema=ElicitationSchema(type="object", properties={}, required=[]),
        )

        pending = handler.list_pending()
        assert len(pending) == 2


@pytest.mark.xdist_group(name="mcp_elicitation")
@pytest.mark.integration
class TestElicitationJSONRPC:
    """Test elicitation via JSON-RPC 2.0 protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> ElicitationHandler:
        """Create handler for JSON-RPC tests."""
        return ElicitationHandler()

    def test_elicitation_create_jsonrpc_format(self, handler: ElicitationHandler) -> None:
        """Test elicitation/create request in JSON-RPC format."""
        elicitation = handler.create_elicitation(
            message="Approve execution of risky action?",
            schema=ElicitationSchema(
                type="object",
                properties={
                    "approved": {"type": "boolean", "description": "Approve?"},
                    "reason": {"type": "string", "description": "Optional reason"},
                },
                required=["approved"],
            ),
        )

        # Verify JSON-RPC format
        jsonrpc_request = elicitation.to_jsonrpc()
        assert jsonrpc_request["jsonrpc"] == "2.0"
        assert jsonrpc_request["method"] == "elicitation/create"
        assert "params" in jsonrpc_request
        assert jsonrpc_request["params"]["message"] == "Approve execution of risky action?"
        assert "requestedSchema" in jsonrpc_request["params"]

    def test_elicitation_response_jsonrpc_format(self, handler: ElicitationHandler) -> None:
        """Test elicitation response in JSON-RPC format."""
        elicitation = handler.create_elicitation(
            message="Test",
            schema=ElicitationSchema(
                type="object",
                properties={"value": {"type": "string"}},
                required=["value"],
            ),
        )

        response = handler.respond(
            elicitation_id=elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={"value": "test"},
        )

        jsonrpc_response = response.to_jsonrpc(elicitation.request_id)
        assert jsonrpc_response["jsonrpc"] == "2.0"
        assert jsonrpc_response["id"] == elicitation.request_id
        assert jsonrpc_response["result"]["action"] == "accept"
        assert jsonrpc_response["result"]["content"] == {"value": "test"}


@pytest.mark.xdist_group(name="mcp_elicitation")
@pytest.mark.integration
class TestElicitationWithApprovalNode:
    """Test integration between Elicitation and ApprovalNode."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_approval_node(self) -> MagicMock:
        """Create mock ApprovalNode."""
        node = MagicMock()
        node.approval_id = str(uuid.uuid4())
        node.action_description = "Execute dangerous command: rm -rf /"
        node.risk_level = "critical"
        return node

    def test_approval_node_to_elicitation(self, mock_approval_node: MagicMock) -> None:
        """Test converting ApprovalNode interrupt to elicitation request."""
        from mcp_server_langgraph.mcp.elicitation import (
            approval_node_to_elicitation,
        )

        elicitation = approval_node_to_elicitation(mock_approval_node)

        # Risk level prefix is added for high/critical risks
        expected_message = f"[CRITICAL] Approve: {mock_approval_node.action_description}"
        assert elicitation.message == expected_message
        assert "approved" in elicitation.requestedSchema.properties
        assert elicitation.requestedSchema.properties["approved"]["type"] == "boolean"

    def test_elicitation_response_to_approval(self) -> None:
        """Test converting elicitation response to ApprovalResponse."""
        from mcp_server_langgraph.mcp.elicitation import (
            elicitation_response_to_approval,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

        response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content={"approved": True, "reason": "Looks safe"},
        )

        approval = elicitation_response_to_approval(response, "approval-123")

        assert approval.approval_id == "approval-123"
        assert approval.status == ApprovalStatus.APPROVED
        assert approval.reason == "Looks safe"

    def test_elicitation_decline_to_rejection(self) -> None:
        """Test converting decline to ApprovalResponse rejection."""
        from mcp_server_langgraph.mcp.elicitation import (
            elicitation_response_to_approval,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

        response = ElicitationResponse(action=ElicitationAction.DECLINE)

        approval = elicitation_response_to_approval(response, "approval-123")

        assert approval.status == ApprovalStatus.REJECTED
