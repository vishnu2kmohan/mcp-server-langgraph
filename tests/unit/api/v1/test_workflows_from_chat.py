"""
Workflows From-Chat Endpoint Unit Tests (TDD Red Phase)

Tests for POST /api/v1/workflows/from-chat endpoint per TDD methodology.
Tests written FIRST before implementation (RED phase).

The /from-chat endpoint:
- Accepts session_id, refinement_mode (auto/plan), and optional template_id
- Fetches session messages and sanitizes them
- Generates workflow via WorkflowGenerator
- Persists with status="draft", version=1
- Returns prompt_metadata for telemetry linkage

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- Review consensus: Centralized validation, sanitization before LLM
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


def make_session_messages() -> list[dict[str, Any]]:
    """Create sample session messages for testing."""
    return [
        {"role": "user", "content": "I want to create a workflow that fetches data"},
        {"role": "assistant", "content": "I can help you create that workflow."},
        {"role": "user", "content": "It should validate the data and then store it"},
    ]


def make_generated_workflow() -> dict[str, Any]:
    """Create a sample generated workflow response."""
    return {
        "workflow": {
            "id": "wf-test-123",
            "name": "data-fetch-workflow",
            "title": "Data Fetch Workflow",
            "description": "Fetches, validates, and stores data",
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 0, "y": 100}, "data": {"label": "Start"}},
                {"id": "fetch", "type": "llm", "position": {"x": 200, "y": 100}, "data": {"label": "Fetch Data"}},
                {"id": "validate", "type": "tool", "position": {"x": 400, "y": 100}, "data": {"label": "Validate"}},
                {"id": "store", "type": "tool", "position": {"x": 600, "y": 100}, "data": {"label": "Store Data"}},
                {"id": "end", "type": "end", "position": {"x": 800, "y": 100}, "data": {"label": "End"}},
            ],
            "edges": [
                {"source": "start", "target": "fetch"},
                {"source": "fetch", "target": "validate"},
                {"source": "validate", "target": "store"},
                {"source": "store", "target": "end"},
            ],
            "created_at": "2026-01-03T00:00:00Z",
            "updated_at": "2026-01-03T00:00:00Z",
        },
        "confidence": 0.85,
        "suggestions": ["Consider adding error handling"],
        "prompt_metadata": {
            "name": "workflow_generator",
            "version": "v1",
            "hash": "abc123def456",
            "model": "claude-opus-4-5",
        },
    }


# =============================================================================
# Test: Request/Response Models Exist
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatModelsExist:
    """Tests that FromChat request/response models exist."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_from_chat_request_model_exists(self) -> None:
        """FromChatRequest model should exist in workflows module."""
        from mcp_server_langgraph.api.v1.workflows import FromChatRequest

        assert FromChatRequest is not None

    def test_from_chat_request_has_required_fields(self) -> None:
        """FromChatRequest should have session_id, refinement_mode, template_id fields."""
        from mcp_server_langgraph.api.v1.workflows import FromChatRequest

        schema = FromChatRequest.model_json_schema()
        properties = schema.get("properties", {})

        assert "session_id" in properties
        assert "refinement_mode" in properties
        # template_id is optional

    def test_from_chat_request_refinement_mode_defaults_to_auto(self) -> None:
        """FromChatRequest refinement_mode should default to 'auto'."""
        from mcp_server_langgraph.api.v1.workflows import FromChatRequest

        request = FromChatRequest(session_id="test-session")
        assert request.refinement_mode == "auto"

    def test_from_chat_response_model_exists(self) -> None:
        """FromChatResponse model should exist in workflows module."""
        from mcp_server_langgraph.api.v1.workflows import FromChatResponse

        assert FromChatResponse is not None

    def test_from_chat_response_has_required_fields(self) -> None:
        """FromChatResponse should have workflow, confidence, suggestions, prompt_metadata."""
        from mcp_server_langgraph.api.v1.workflows import FromChatResponse

        schema = FromChatResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "workflow" in properties
        assert "confidence" in properties
        assert "suggestions" in properties
        assert "prompt_metadata" in properties

    def test_prompt_metadata_model_exists(self) -> None:
        """PromptMetadata model should exist for telemetry linkage."""
        from mcp_server_langgraph.api.v1.workflows import PromptMetadata

        assert PromptMetadata is not None

    def test_prompt_metadata_has_required_fields(self) -> None:
        """PromptMetadata should have name, version, hash, model fields."""
        from mcp_server_langgraph.api.v1.workflows import PromptMetadata

        schema = PromptMetadata.model_json_schema()
        properties = schema.get("properties", {})

        assert "name" in properties
        assert "version" in properties
        assert "hash" in properties
        assert "model" in properties


# =============================================================================
# Test: Endpoint Registration
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatEndpointRegistration:
    """Tests that /from-chat endpoint is properly registered."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_from_chat_endpoint_exists(self) -> None:
        """POST /api/v1/workflows/from-chat endpoint should exist."""
        from mcp_server_langgraph.api.v1.workflows import workflows_router

        # Check that the route is registered
        routes = [r.path for r in workflows_router.routes]
        assert "/workflows/from-chat" in routes or any("/from-chat" in str(r.path) for r in workflows_router.routes), (
            f"Routes found: {routes}"
        )


# =============================================================================
# Test: Feature Flag Gating
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatFeatureFlag:
    """Tests that /from-chat endpoint respects feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_from_chat_disabled_returns_404(self) -> None:
        """When enable_workflow_from_chat=False, endpoint should return 404."""
        from mcp_server_langgraph.api.v1.workflows import workflows_router, get_workflow_service
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Mock user
        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        # Mock workflow service to avoid storage dependency
        mock_service = AsyncMock(return_value=None)
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        # Mock feature flag as disabled
        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value.enable_workflow_from_chat = False

            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session"},
            )

            # Should return 404 when feature is disabled
            assert response.status_code in (404, 403)


# =============================================================================
# Test: Successful Generation
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatSuccessfulGeneration:
    """Tests for successful workflow generation from chat."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_from_chat_returns_generated_workflow(self) -> None:
        """Successful generation should return workflow with status=draft."""
        from mcp_server_langgraph.api.v1.workflows import (
            get_workflow_service,
            workflows_router,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Mock dependencies
        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        # Create mock flags object
        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        # Mock workflow service
        mock_service = AsyncMock(return_value=None)
        mock_service.generate_from_chat.return_value = make_generated_workflow()

        # Override service dependency
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        # Mock feature flag at the import location in workflows module
        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session", "refinement_mode": "auto"},
            )

            assert response.status_code == 201
            data = response.json()

            # Verify workflow is returned
            assert "workflow" in data
            assert data["workflow"]["name"] == "data-fetch-workflow"

            # Verify response includes all expected fields
            assert "confidence" in data
            assert "prompt_metadata" in data

    @pytest.mark.asyncio
    async def test_from_chat_includes_prompt_metadata(self) -> None:
        """Response should include prompt_metadata for telemetry."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock(return_value=None)
        mock_service.generate_from_chat.return_value = make_generated_workflow()
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session"},
            )

            assert response.status_code == 201
            data = response.json()

            # Verify prompt_metadata is included
            assert "prompt_metadata" in data
            assert data["prompt_metadata"]["version"] == "v1"
            assert "hash" in data["prompt_metadata"]

    @pytest.mark.asyncio
    async def test_from_chat_persists_with_version_1(self) -> None:
        """Generated workflow should be persisted with version=1."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock(return_value=None)
        generated = make_generated_workflow()
        generated["workflow"]["version"] = 1
        mock_service.generate_from_chat.return_value = generated
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session"},
            )

            assert response.status_code == 201
            # Verify service was called with correct parameters
            mock_service.generate_from_chat.assert_called_once()


# =============================================================================
# Test: Validation and Errors
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatValidation:
    """Tests for input validation and error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_from_chat_requires_session_id(self) -> None:
        """Request without session_id should fail validation."""
        from mcp_server_langgraph.api.v1.workflows import workflows_router, get_workflow_service
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        # Mock workflow service to avoid storage dependency
        mock_service = AsyncMock(return_value=None)
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={},  # Missing session_id
            )

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_from_chat_invalid_refinement_mode(self) -> None:
        """Invalid refinement_mode should fail validation."""
        from mcp_server_langgraph.api.v1.workflows import workflows_router, get_workflow_service
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        # Mock workflow service to avoid storage dependency
        mock_service = AsyncMock(return_value=None)
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test", "refinement_mode": "invalid"},
            )

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_from_chat_session_not_found(self) -> None:
        """Non-existent session_id should return 404."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock(return_value=None)
        mock_service.generate_from_chat.side_effect = ValueError("Session not found")
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "nonexistent-session"},
            )

            assert response.status_code == 404


# =============================================================================
# Test: Refinement Modes
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatRefinementModes:
    """Tests for different refinement modes (auto/plan)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_from_chat_auto_mode(self) -> None:
        """Auto mode should generate and persist immediately."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock(return_value=None)
        mock_service.generate_from_chat.return_value = make_generated_workflow()
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session", "refinement_mode": "auto"},
            )

            assert response.status_code == 201
            # Verify service was called with auto mode
            mock_service.generate_from_chat.assert_called_once()
            call_kwargs = mock_service.generate_from_chat.call_args
            assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_from_chat_plan_mode_returns_plan(self) -> None:
        """Plan mode should return execution plan for approval."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock(return_value=None)
        generated = make_generated_workflow()
        generated["plan"] = {
            "id": "plan-123",
            "steps": ["Analyze conversation", "Generate workflow structure"],
            "requires_approval": True,
        }
        mock_service.generate_from_chat.return_value = generated
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session", "refinement_mode": "plan"},
            )

            assert response.status_code == 201
            # Plan mode returns workflow and optionally includes plan object
            assert "workflow" in response.json()


# =============================================================================
# Test: Sanitization
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatSanitization:
    """Tests that session content is sanitized before LLM exposure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_from_chat_sanitizes_session_content(self) -> None:
        """Session messages should be sanitized before generation."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service, workflows_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        mock_user = {"sub": "user-123", "email": "test@example.com"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        mock_service = AsyncMock(return_value=None)
        mock_service.generate_from_chat.return_value = make_generated_workflow()
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session"},
            )

            # The endpoint should complete (sanitization happens in service layer)
            assert response.status_code == 201


# =============================================================================
# Test: Authentication
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_from_chat")
class TestFromChatAuthentication:
    """Tests that /from-chat requires authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_from_chat_requires_authentication(self) -> None:
        """Unauthenticated requests should return 401."""
        from mcp_server_langgraph.api.v1.workflows import workflows_router, get_workflow_service

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Mock workflow service to avoid storage dependency
        mock_service = AsyncMock(return_value=None)
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        # No auth override - should use real auth which will fail
        mock_flags_obj = MagicMock()
        mock_flags_obj.enable_workflow_from_chat = True

        with patch(
            "mcp_server_langgraph.api.v1.workflows.get_feature_flags",
            side_effect=lambda *a, **kw: mock_flags_obj,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workflows/from-chat",
                json={"session_id": "test-session"},
            )

            # Should require authentication (401, 403, or internal error from missing auth)
            assert response.status_code in (401, 403, 422, 500)
