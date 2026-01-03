"""
Workflows Validate Endpoint Unit Tests (TDD Red Phase)

Tests for POST /api/v1/workflows/{id}/validate endpoint per TDD methodology.
Tests written FIRST before implementation (RED phase).

The /validate endpoint:
- Validates workflow graph structure using centralized WorkflowValidator
- Returns validation result with errors and warnings
- Does NOT duplicate validation logic in frontend (review consensus)
- Enables real-time validation feedback for Monaco/React Flow editors

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- Review consensus: Centralized validation endpoint - NO JS DUPLICATION
- ADR-0089: Prompt Architecture Centralization
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


# =============================================================================
# Test Fixtures
# =============================================================================


def make_valid_workflow() -> dict[str, Any]:
    """Create a valid workflow dict for testing."""
    return {
        "id": "wf-test-123",
        "name": "test-workflow",
        "description": "Test workflow",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "llm1", "type": "llm", "label": "Process"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"source": "start", "target": "llm1"},
            {"source": "llm1", "target": "end"},
        ],
    }


def make_invalid_workflow() -> dict[str, Any]:
    """Create an invalid workflow dict for testing (missing start node)."""
    return {
        "id": "wf-invalid-123",
        "name": "invalid-workflow",
        "description": "Invalid workflow - no start node",
        "nodes": [
            {"id": "llm1", "type": "llm", "label": "Process"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"source": "llm1", "target": "end"},
        ],
    }


# =============================================================================
# Test: Request/Response Models Exist
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_validate")
class TestValidateModelsExist:
    """Tests that Validate request/response models exist."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_request_model_exists(self) -> None:
        """ValidateWorkflowRequest model should exist in workflows module."""
        from mcp_server_langgraph.api.v1.workflows import ValidateWorkflowRequest

        assert ValidateWorkflowRequest is not None

    def test_validate_response_model_exists(self) -> None:
        """ValidateWorkflowResponse model should exist in workflows module."""
        from mcp_server_langgraph.api.v1.workflows import ValidateWorkflowResponse

        assert ValidateWorkflowResponse is not None

    def test_validate_response_has_required_fields(self) -> None:
        """ValidateWorkflowResponse should have valid, errors, warnings fields."""
        from mcp_server_langgraph.api.v1.workflows import ValidateWorkflowResponse

        schema = ValidateWorkflowResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "valid" in properties
        assert "errors" in properties
        assert "warnings" in properties


# =============================================================================
# Test: Endpoint Registration
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_validate")
class TestValidateEndpointRegistration:
    """Tests that /validate endpoint is properly registered."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_endpoint_exists(self) -> None:
        """POST /api/v1/workflows/{id}/validate endpoint should exist."""
        from mcp_server_langgraph.api.v1.workflows import workflows_router

        routes = [r.path for r in workflows_router.routes]
        assert any("/validate" in str(r) for r in routes), f"Routes found: {routes}"


# =============================================================================
# Test: Valid Workflow Passes
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_validate")
class TestValidateValidWorkflow:
    """Tests for validation of valid workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_valid_workflow_returns_valid_true(self) -> None:
        """Valid workflow should return valid=True with no errors."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = make_valid_workflow()
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            return_value=mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/wf-test-123/validate",
                json={},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["valid"] is True
            assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validation_returns_warnings_for_unknown_types(self) -> None:
        """Valid workflow with unknown node types should return warnings."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        # Workflow with unknown node type
        workflow = make_valid_workflow()
        workflow["nodes"].insert(1, {"id": "custom", "type": "custom_unknown", "label": "Custom"})
        workflow["edges"][0]["target"] = "custom"
        workflow["edges"].insert(1, {"source": "custom", "target": "llm1"})

        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = workflow
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            return_value=mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/wf-test-123/validate",
                json={},
            )

            assert response.status_code == 200
            data = response.json()

            # Should pass but have warnings
            assert data["valid"] is True
            assert len(data["warnings"]) > 0


# =============================================================================
# Test: Invalid Workflow Fails
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_validate")
class TestValidateInvalidWorkflow:
    """Tests for validation of invalid workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_missing_start_node_fails_validation(self) -> None:
        """Workflow without start node should fail validation."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = make_invalid_workflow()
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            return_value=mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/wf-invalid-123/validate",
                json={},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["valid"] is False
            assert len(data["errors"]) > 0
            assert any("start" in e.lower() for e in data["errors"])

    @pytest.mark.asyncio
    async def test_orphan_node_fails_validation(self) -> None:
        """Workflow with orphan nodes should fail validation."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        # Workflow with orphan node
        workflow = make_valid_workflow()
        workflow["nodes"].append({"id": "orphan", "type": "llm", "label": "Orphan"})
        # No edges to orphan

        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = workflow
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            return_value=mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/wf-test-123/validate",
                json={},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["valid"] is False
            assert len(data["errors"]) > 0


# =============================================================================
# Test: Workflow Not Found
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_validate")
class TestValidateWorkflowNotFound:
    """Tests for validation when workflow doesn't exist."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_nonexistent_workflow_returns_404(self) -> None:
        """Validating non-existent workflow should return 404."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = None  # Not found
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            return_value=mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/nonexistent-id/validate",
                json={},
            )

            assert response.status_code == 404


# =============================================================================
# Test: Uses Centralized Validator
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_validate")
class TestValidateUsesCentralizedValidator:
    """Tests that endpoint uses the centralized WorkflowValidator service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_uses_workflow_validator_service(self) -> None:
        """Endpoint should use WorkflowValidator service for validation."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = make_valid_workflow()
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        # Mock the validator
        with (
            patch(
                "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
                return_value=mock_flags_obj,
            ),
            patch("mcp_server_langgraph.api.v1.workflows.WorkflowValidator") as mock_validator_cls,
        ):
            mock_validator = AsyncMock()
            mock_validator.validate.return_value = MagicMock(
                valid=True,
                errors=[],
                warnings=[],
            )
            mock_validator_cls.return_value = mock_validator

            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/wf-test-123/validate",
                json={},
            )

            assert response.status_code == 200
            # Verify validator was called
            mock_validator.validate.assert_called_once()
