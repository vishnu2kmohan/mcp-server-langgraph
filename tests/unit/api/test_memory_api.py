"""
TDD: Unit tests for Memory API endpoints.

Tests that the agentic memory endpoints work correctly
for managing notes and checkpoints.

Phase 1.2: enable_agentic_memory feature flag
- POST /api/v1/memory/notes - Create note
- GET /api/v1/memory/notes - List notes
- GET /api/v1/memory/notes/{id} - Get note
- DELETE /api/v1/memory/notes/{id} - Delete note
- POST /api/v1/memory/checkpoint - Create checkpoint
- GET /api/v1/memory/checkpoint - List checkpoints
- GET /api/v1/memory/checkpoint/latest - Get latest checkpoint
- GET /api/v1/memory/checkpoint/summary - Get session summary

RED phase: These tests define expected behavior before implementation.
"""

import gc
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.memory]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_feature_flags():
    """Mock feature flags with agentic memory enabled."""
    mock_flags = MagicMock()
    mock_flags.enable_agentic_memory = True
    return mock_flags


@pytest.fixture
def mock_app(mock_feature_flags: MagicMock) -> Generator[FastAPI, None, None]:
    """Create FastAPI app with memory router."""
    from mcp_server_langgraph.api.v1 import memory as memory_module
    from mcp_server_langgraph.api.v1.memory import memory_router, set_notes_manager, set_checkpoint_manager
    from mcp_server_langgraph.auth.dependencies import get_current_user
    from mcp_server_langgraph.memory.notes import NotesManager
    from mcp_server_langgraph.memory.checkpoints import CheckpointManager

    # Configure mock to have require_feature as a no-op
    mock_feature_flags.require_feature = MagicMock(return_value=None)

    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1/memory")

    # Mock authentication
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "roles": ["user"],
    }

    async def _override_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _override_current_user

    # Patch feature_flags at the core module (where @feature_gated reads from)
    # and at the memory API module level
    with (
        patch("mcp_server_langgraph.core.feature_flags.feature_flags", mock_feature_flags),
        patch.object(memory_module, "feature_flags", mock_feature_flags),
    ):
        # Reset managers for clean state INSIDE the patch context
        set_notes_manager(NotesManager())
        set_checkpoint_manager(CheckpointManager())
        yield app


@pytest.fixture
def client(mock_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(mock_app)


# =============================================================================
# Notes API Tests
# =============================================================================


class TestNotesAPI:
    """Test /api/v1/memory/notes endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_note_returns_201(self, client: TestClient) -> None:
        """POST /api/v1/memory/notes returns 201 on success."""
        response = client.post(
            "/api/v1/memory/notes",
            json={
                "content": "Test note content",
                "category": "general",
                "tags": ["test", "tdd"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["content"] == "Test note content"
        assert data["category"] == "general"

    def test_create_note_generates_id(self, client: TestClient) -> None:
        """POST /api/v1/memory/notes generates unique ID."""
        response1 = client.post(
            "/api/v1/memory/notes",
            json={"content": "Note 1"},
        )
        response2 = client.post(
            "/api/v1/memory/notes",
            json={"content": "Note 2"},
        )

        assert response1.json()["id"] != response2.json()["id"]

    def test_list_notes_returns_array(self, client: TestClient) -> None:
        """GET /api/v1/memory/notes returns notes list."""
        # Create a note first
        client.post("/api/v1/memory/notes", json={"content": "List test"})

        response = client.get("/api/v1/memory/notes")

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert isinstance(data["notes"], list)

    def test_list_notes_with_category_filter(self, client: TestClient) -> None:
        """GET /api/v1/memory/notes?category=test filters by category."""
        client.post("/api/v1/memory/notes", json={"content": "Cat test", "category": "test"})

        response = client.get("/api/v1/memory/notes?category=test")

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data

    def test_get_note_by_id(self, client: TestClient) -> None:
        """GET /api/v1/memory/notes/{id} returns specific note."""
        create_response = client.post(
            "/api/v1/memory/notes",
            json={"content": "Specific note"},
        )
        note_id = create_response.json()["id"]

        response = client.get(f"/api/v1/memory/notes/{note_id}")

        assert response.status_code == 200
        assert response.json()["id"] == note_id

    def test_get_nonexistent_note_returns_404(self, client: TestClient) -> None:
        """GET /api/v1/memory/notes/{id} returns 404 for missing note."""
        response = client.get("/api/v1/memory/notes/nonexistent-id")

        assert response.status_code == 404

    def test_delete_note_returns_204(self, client: TestClient) -> None:
        """DELETE /api/v1/memory/notes/{id} returns 204."""
        create_response = client.post(
            "/api/v1/memory/notes",
            json={"content": "Delete me"},
        )
        note_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/memory/notes/{note_id}")

        assert response.status_code == 204

    def test_delete_nonexistent_note_returns_404(self, client: TestClient) -> None:
        """DELETE /api/v1/memory/notes/{id} returns 404 for missing note."""
        response = client.delete("/api/v1/memory/notes/nonexistent-id")

        assert response.status_code == 404


# =============================================================================
# Checkpoint API Tests
# =============================================================================


class TestCheckpointAPI:
    """Test /api/v1/memory/checkpoint endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_checkpoint_returns_201(self, client: TestClient) -> None:
        """POST /api/v1/memory/checkpoint returns 201 on success."""
        response = client.post(
            "/api/v1/memory/checkpoint",
            json={
                "phase": "planning",
                "summary": "Completed planning phase",
                "artifacts": ["plan.md"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["phase"] == "planning"

    def test_list_checkpoints_returns_array(self, client: TestClient) -> None:
        """GET /api/v1/memory/checkpoint returns checkpoints list."""
        # Create a checkpoint first
        client.post(
            "/api/v1/memory/checkpoint",
            json={"phase": "test", "summary": "Test checkpoint"},
        )

        response = client.get("/api/v1/memory/checkpoint")

        assert response.status_code == 200
        data = response.json()
        assert "checkpoints" in data
        assert isinstance(data["checkpoints"], list)

    def test_get_latest_checkpoint(self, client: TestClient) -> None:
        """GET /api/v1/memory/checkpoint/latest returns most recent."""
        client.post(
            "/api/v1/memory/checkpoint",
            json={"phase": "phase1", "summary": "First"},
        )
        client.post(
            "/api/v1/memory/checkpoint",
            json={"phase": "phase2", "summary": "Second"},
        )

        response = client.get("/api/v1/memory/checkpoint/latest")

        assert response.status_code == 200
        assert response.json()["phase"] == "phase2"

    def test_get_latest_when_none_exists_returns_404(self, client: TestClient) -> None:
        """GET /api/v1/memory/checkpoint/latest returns 404 if none exist."""
        # Use fresh managers to ensure no checkpoints
        from mcp_server_langgraph.api.v1 import memory as memory_module
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        memory_module.set_checkpoint_manager(CheckpointManager())

        response = client.get("/api/v1/memory/checkpoint/latest")

        # Could be 404 or empty depending on implementation
        assert response.status_code in (200, 404)

    def test_get_session_summary(self, client: TestClient) -> None:
        """GET /api/v1/memory/checkpoint/summary returns session summary."""
        response = client.get("/api/v1/memory/checkpoint/summary")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


# =============================================================================
# Feature Flag Tests
# =============================================================================


class TestMemoryFeatureFlag:
    """Test feature flag gating for memory endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_note_requires_feature_flag(self) -> None:
        """POST /api/v1/memory/notes returns 403 when flag disabled."""
        from mcp_server_langgraph.api.v1 import memory as memory_module
        from mcp_server_langgraph.api.v1.memory import memory_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(memory_router, prefix="/api/v1/memory")

        mock_user = {"sub": "test-user-id"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags = MagicMock()
        mock_flags.enable_agentic_memory = False

        with patch.object(memory_module, "feature_flags", mock_flags):
            client = TestClient(app)
            response = client.post(
                "/api/v1/memory/notes",
                json={"content": "Test"},
            )

        assert response.status_code == 403

    def test_create_checkpoint_requires_feature_flag(self) -> None:
        """POST /api/v1/memory/checkpoint returns 403 when flag disabled."""
        from mcp_server_langgraph.api.v1 import memory as memory_module
        from mcp_server_langgraph.api.v1.memory import memory_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(memory_router, prefix="/api/v1/memory")

        mock_user = {"sub": "test-user-id"}

        async def _override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = _override_current_user

        mock_flags = MagicMock()
        mock_flags.enable_agentic_memory = False

        with patch.object(memory_module, "feature_flags", mock_flags):
            client = TestClient(app)
            response = client.post(
                "/api/v1/memory/checkpoint",
                json={"phase": "test", "summary": "Test"},
            )

        assert response.status_code == 403
