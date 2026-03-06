"""
TDD: Integration tests for Agentic Memory API

Tests the REST API endpoints for notes and checkpoints,
following the agentic memory pattern for persistent agent state.

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.agentic_memory]


@pytest.fixture
def mock_notes_manager():
    """Create mock NotesManager."""
    manager = MagicMock()
    manager._notes = {}
    return manager


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock CheckpointManager."""
    manager = MagicMock()
    manager._checkpoints = {}
    return manager


@pytest.fixture
def memory_app(mock_notes_manager, mock_checkpoint_manager):
    """Create test FastAPI app with memory router."""
    from mcp_server_langgraph.api.v1.memory import (
        memory_router,
        set_notes_manager,
        set_checkpoint_manager,
    )
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1/memory")

    # Mock authenticated user
    mock_user = {
        "sub": "user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    set_notes_manager(mock_notes_manager)
    set_checkpoint_manager(mock_checkpoint_manager)

    yield app

    # Cleanup
    set_notes_manager(None)
    set_checkpoint_manager(None)


@pytest.fixture
def client(memory_app):
    """Create test client."""
    return TestClient(memory_app)


class TestNotesAPI:
    """Tests for Notes REST API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_note_success(self, client, mock_notes_manager):
        """GIVEN valid note data WHEN POST /notes THEN creates note."""
        from mcp_server_langgraph.memory.notes import Note

        mock_note = Note(
            id="note-abc123",
            content="Test note content",
            category="research",
            tags=["important"],
        )
        mock_notes_manager.add_note.return_value = mock_note

        response = client.post(
            "/api/v1/memory/notes",
            json={
                "content": "Test note content",
                "category": "research",
                "tags": ["important"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "note-abc123"
        assert data["content"] == "Test note content"
        assert data["category"] == "research"

    def test_list_notes_success(self, client, mock_notes_manager):
        """GIVEN notes exist WHEN GET /notes THEN returns notes list."""
        from mcp_server_langgraph.memory.notes import Note

        mock_notes = [
            Note(id="note-1", content="First note", category="research"),
            Note(id="note-2", content="Second note", category="planning"),
        ]
        mock_notes_manager.list_notes.return_value = mock_notes

        response = client.get("/api/v1/memory/notes")

        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 2
        assert data["notes"][0]["id"] == "note-1"

    def test_get_note_by_id(self, client, mock_notes_manager):
        """GIVEN note exists WHEN GET /notes/{id} THEN returns note."""
        from mcp_server_langgraph.memory.notes import Note

        mock_note = Note(id="note-123", content="Test content", category="general")
        mock_notes_manager.get_note.return_value = mock_note

        response = client.get("/api/v1/memory/notes/note-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "note-123"

    def test_get_note_not_found(self, client, mock_notes_manager):
        """GIVEN note doesn't exist WHEN GET /notes/{id} THEN returns 404."""
        mock_notes_manager.get_note.return_value = None

        response = client.get("/api/v1/memory/notes/nonexistent")

        assert response.status_code == 404

    def test_delete_note_success(self, client, mock_notes_manager):
        """GIVEN note exists WHEN DELETE /notes/{id} THEN deletes note."""
        from mcp_server_langgraph.memory.notes import Note

        mock_note = Note(id="note-123", content="To delete", category="general")
        mock_notes_manager.get_note.return_value = mock_note

        response = client.delete("/api/v1/memory/notes/note-123")

        assert response.status_code == 204
        mock_notes_manager.delete_note.assert_called_once_with("note-123")

    def test_search_notes_with_query_returns_matching_notes(self, client, mock_notes_manager):
        """GIVEN notes exist WHEN GET /notes?query=x THEN searches notes."""
        from mcp_server_langgraph.memory.notes import Note

        mock_notes = [
            Note(id="note-1", content="Contains keyword", category="research"),
        ]
        mock_notes_manager.search.return_value = mock_notes

        response = client.get("/api/v1/memory/notes?query=keyword")

        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 1
        mock_notes_manager.search.assert_called_once_with("keyword")


class TestCheckpointAPI:
    """Tests for Checkpoint REST API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_checkpoint_success(self, client, mock_checkpoint_manager):
        """GIVEN valid checkpoint data WHEN POST /checkpoint THEN creates checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import Checkpoint

        mock_checkpoint = Checkpoint(
            id="checkpoint-abc123",
            phase="research",
            summary="Completed initial research",
            artifacts=["doc1.md", "doc2.md"],
        )
        mock_checkpoint_manager.create_checkpoint.return_value = mock_checkpoint

        response = client.post(
            "/api/v1/memory/checkpoint",
            json={
                "phase": "research",
                "summary": "Completed initial research",
                "artifacts": ["doc1.md", "doc2.md"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "checkpoint-abc123"
        assert data["phase"] == "research"

    def test_list_checkpoints_returns_all_checkpoints(self, client, mock_checkpoint_manager):
        """GIVEN checkpoints exist WHEN GET /checkpoint THEN returns list."""
        from mcp_server_langgraph.memory.checkpoints import Checkpoint

        mock_checkpoints = [
            Checkpoint(id="cp-1", phase="phase1", summary="Summary 1"),
            Checkpoint(id="cp-2", phase="phase2", summary="Summary 2"),
        ]
        mock_checkpoint_manager.list_checkpoints.return_value = mock_checkpoints

        response = client.get("/api/v1/memory/checkpoint")

        assert response.status_code == 200
        data = response.json()
        assert len(data["checkpoints"]) == 2

    def test_get_latest_checkpoint(self, client, mock_checkpoint_manager):
        """GIVEN checkpoints exist WHEN GET /checkpoint/latest THEN returns latest."""
        from mcp_server_langgraph.memory.checkpoints import Checkpoint

        mock_checkpoint = Checkpoint(
            id="cp-latest",
            phase="final",
            summary="Latest summary",
        )
        mock_checkpoint_manager.get_latest_checkpoint.return_value = mock_checkpoint

        response = client.get("/api/v1/memory/checkpoint/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "cp-latest"

    def test_get_session_summary(self, client, mock_checkpoint_manager):
        """GIVEN checkpoints exist WHEN GET /checkpoint/summary THEN returns summary."""
        mock_checkpoint_manager.summarize_session.return_value = "# Session Summary\n\nPhase 1 complete."

        response = client.get("/api/v1/memory/checkpoint/summary")

        assert response.status_code == 200
        data = response.json()
        assert "Session Summary" in data["summary"]


class TestAgenticMemoryFeatureFlag:
    """Tests for feature flag gating."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_notes_manager_respects_feature_flag(self):
        """GIVEN feature flag disabled WHEN adding note THEN raises error."""
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager()

        # Mock require_feature to raise FeatureDisabledError
        def mock_require_feature(feature_name, display_name=None):
            raise FeatureDisabledError(
                feature_name=display_name or feature_name,
                flag_name=f"FF_{feature_name.upper()}",
            )

        with patch(
            "mcp_server_langgraph.core.feature_flags.feature_flags.require_feature",
            side_effect=mock_require_feature,
        ):
            with pytest.raises(FeatureDisabledError):
                manager.add_note(content="Test note")

    def test_checkpoint_manager_respects_feature_flag(self):
        """GIVEN feature flag disabled WHEN creating checkpoint THEN raises error."""
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager()

        # Mock require_feature to raise FeatureDisabledError
        def mock_require_feature(feature_name, display_name=None):
            raise FeatureDisabledError(
                feature_name=display_name or feature_name,
                flag_name=f"FF_{feature_name.upper()}",
            )

        with patch(
            "mcp_server_langgraph.core.feature_flags.feature_flags.require_feature",
            side_effect=mock_require_feature,
        ):
            with pytest.raises(FeatureDisabledError):
                manager.create_checkpoint(phase="test", summary="Test")
