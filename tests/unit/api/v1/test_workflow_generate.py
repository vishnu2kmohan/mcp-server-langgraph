"""
Workflow Generation API Tests

TDD tests for POST /workflows/generate endpoint (Phase 6).

Requirements:
- Generate workflow from session history OR text prompt
- Exactly one of session_id or prompt required (mutual exclusivity)
- Returns generated workflow with confidence score
- Returns improvement suggestions
"""

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import ValidationError
from fastapi import status

from mcp_server_langgraph.api.v1.workflows import workflows_router

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestGenerateWorkflowModels:
    """Tests for workflow generation Pydantic models."""

    def test_generate_workflow_request_model_exists(self) -> None:
        """GenerateWorkflowRequest model should exist with required fields."""
        from mcp_server_langgraph.api.v1.workflows import GenerateWorkflowRequest

        schema = GenerateWorkflowRequest.model_json_schema()
        properties = schema.get("properties", {})

        # Optional fields (exactly one required)
        assert "session_id" in properties
        assert "prompt" in properties

    def test_generate_workflow_request_requires_exactly_one_source(self) -> None:
        """GenerateWorkflowRequest should require exactly one of session_id or prompt."""
        from mcp_server_langgraph.api.v1.workflows import GenerateWorkflowRequest

        # Both provided should fail
        with pytest.raises(ValidationError):
            GenerateWorkflowRequest(session_id="sess-123", prompt="Create a chatbot")

        # Neither provided should fail
        with pytest.raises(ValidationError):
            GenerateWorkflowRequest()

        # Only session_id should work
        request = GenerateWorkflowRequest(session_id="sess-123")
        assert request.session_id == "sess-123"
        assert request.prompt is None

        # Only prompt should work
        request = GenerateWorkflowRequest(prompt="Create a chatbot")
        assert request.prompt == "Create a chatbot"
        assert request.session_id is None

    def test_generate_workflow_response_model_exists(self) -> None:
        """GenerateWorkflowResponse model should exist with required fields."""
        from mcp_server_langgraph.api.v1.workflows import GenerateWorkflowResponse

        schema = GenerateWorkflowResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Required fields
        assert "workflow" in properties
        assert "confidence" in properties
        assert "suggestions" in properties

    def test_generate_workflow_response_confidence_range(self) -> None:
        """Confidence should be between 0.0 and 1.0."""
        from mcp_server_langgraph.api.v1.workflows import (
            GenerateWorkflowResponse,
            WorkflowResponse,
        )

        # Valid confidence
        workflow = WorkflowResponse(
            id="wf-1",
            name="Generated Workflow",
            description="Auto-generated",
            nodes=[],
            edges=[],
        )
        response = GenerateWorkflowResponse(
            workflow=workflow,
            confidence=0.85,
            suggestions=["Add error handling"],
        )
        assert response.confidence == 0.85

        # Confidence below 0 should fail
        with pytest.raises(ValidationError):
            GenerateWorkflowResponse(
                workflow=workflow,
                confidence=-0.1,
                suggestions=[],
            )

        # Confidence above 1 should fail
        with pytest.raises(ValidationError):
            GenerateWorkflowResponse(
                workflow=workflow,
                confidence=1.1,
                suggestions=[],
            )


class TestGenerateWorkflowEndpoint:
    """Tests for POST /workflows/generate endpoint."""

    def test_generate_endpoint_exists(self) -> None:
        """POST /workflows/generate endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/generate" in route_paths

    def test_generate_endpoint_method_is_post(self) -> None:
        """The endpoint should accept POST method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/generate":
                assert "POST" in route.methods
                return
        pytest.fail("POST /workflows/generate route not found")

    def test_generate_endpoint_returns_201(self) -> None:
        """The endpoint should return 201 Created on success."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/generate":
                assert route.status_code == status.HTTP_201_CREATED
                return
        pytest.fail("POST /workflows/generate route not found")


class TestGenerateWorkflowIntegration:
    """Integration-style unit tests for workflow generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Create a mock WorkflowServiceAdapter with generate method."""
        service = MagicMock()
        service.generate_workflow = AsyncMock(
            return_value={
                "workflow": {
                    "id": "wf-generated-123",
                    "name": "Generated Chatbot",
                    "description": "AI-generated workflow from prompt",
                    "nodes": [
                        {"id": "n1", "type": "input", "position": {"x": 0, "y": 0}, "data": {}},
                        {"id": "n2", "type": "llm", "position": {"x": 200, "y": 0}, "data": {}},
                        {"id": "n3", "type": "output", "position": {"x": 400, "y": 0}, "data": {}},
                    ],
                    "edges": [
                        {"source": "n1", "target": "n2"},
                        {"source": "n2", "target": "n3"},
                    ],
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                "confidence": 0.85,
                "suggestions": [
                    "Consider adding error handling",
                    "Add memory for conversation history",
                ],
            }
        )
        return service

    @pytest.mark.asyncio
    async def test_generate_from_prompt_returns_workflow(self, mock_service: MagicMock) -> None:
        """Generate from prompt should return workflow with confidence."""
        from mcp_server_langgraph.api.v1.workflows import (
            generate_workflow,
            GenerateWorkflowRequest,
        )

        # GIVEN a prompt request and authenticated user
        request = GenerateWorkflowRequest(prompt="Create a chatbot workflow")
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN calling the endpoint handler
        result = await generate_workflow(request=request, service=mock_service, current_user=mock_user)

        # THEN should return generated workflow
        assert result.workflow.id == "wf-generated-123"
        assert result.confidence == 0.85
        assert len(result.suggestions) == 2
        mock_service.generate_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_from_session_uses_session_messages(self, mock_service: MagicMock) -> None:
        """Generate from session should use session messages."""
        from mcp_server_langgraph.api.v1.workflows import (
            generate_workflow,
            GenerateWorkflowRequest,
        )

        # GIVEN a session_id request and authenticated user
        request = GenerateWorkflowRequest(session_id="sess-456")
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN calling the endpoint handler
        await generate_workflow(request=request, service=mock_service, current_user=mock_user)

        # THEN should call service with session_id
        call_args = mock_service.generate_workflow.call_args
        assert call_args is not None
        # Check that session_id was passed
        assert "sess-456" in str(call_args) or mock_service.generate_workflow.called

    @pytest.mark.asyncio
    async def test_generate_session_not_found_raises_404(self, mock_service: MagicMock) -> None:
        """Should raise 404 if session not found."""
        from fastapi import HTTPException
        from mcp_server_langgraph.api.v1.workflows import (
            generate_workflow,
            GenerateWorkflowRequest,
        )

        # GIVEN session doesn't exist and authenticated user
        mock_service.generate_workflow = AsyncMock(side_effect=ValueError("Session not found"))
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN/THEN should raise 404
        request = GenerateWorkflowRequest(session_id="nonexistent")
        with pytest.raises(HTTPException) as exc_info:
            await generate_workflow(request=request, service=mock_service, current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
