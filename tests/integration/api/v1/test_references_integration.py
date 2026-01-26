"""
Integration tests for the References API.

Tests the full flow: API → OpenFGA authorization → response.
These tests use the actual router but mock external dependencies.

TDD: Tests written first per project guidelines.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException, status

from mcp_server_langgraph.api.v1.references import references_router
from mcp_server_langgraph.auth.dependencies import require_reference_viewer_global
from mcp_server_langgraph.core.dependencies import get_connection_repository


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def create_test_app(user_override=None, repo_override=None):
    """Create a FastAPI app with the references router and optional dependency overrides."""
    app = FastAPI()
    app.include_router(references_router, prefix="/api/v1")

    if user_override is not None:
        app.dependency_overrides[require_reference_viewer_global] = lambda: user_override
    if repo_override is not None:
        app.dependency_overrides[get_connection_repository] = lambda: repo_override

    return app


class TestReferencesAPIIntegration:
    """Integration tests for /api/v1/references/resolve endpoint."""

    async def test_resolve_tool_reference_full_flow(self):
        """
        Test full flow: resolve tool reference with connection lookup and auth.

        Flow:
        1. Client sends POST /references/resolve with tool ref
        2. API looks up connection by server_name
        3. API checks connection:viewer auth via OpenFGA
        4. API returns resolved reference with metadata
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_connection = MagicMock()
        mock_connection.id = "conn-uuid-123"
        mock_connection.name = "Filesystem"
        mock_connection.server_name = "filesystem"

        mock_repo = MagicMock()
        mock_repo.get_by_server_name = AsyncMock(return_value=mock_connection)

        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=True)

        app = create_test_app(user_override=mock_user, repo_override=mock_repo)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            mock_flags.enable_markdown_references = True

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "tool",
                                "qualifier": "filesystem",
                                "id": "read_file",
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"]) == 1
        ref = data["resolved"][0]
        assert ref["type"] == "tool"
        assert ref["qualifier"] == "filesystem"
        assert ref["id"] == "read_file"
        assert ref["status"] == "valid"
        assert ref["metadata"]["connectionId"] == "conn-uuid-123"

    async def test_resolve_unauthorized_returns_403(self):
        """
        Test that unauthorized user gets 403 response.

        The require_reference_viewer_global dependency should raise HTTPException.
        """

        def raise_forbidden():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to resolve references",
            )

        app = FastAPI()
        app.include_router(references_router, prefix="/api/v1")
        app.dependency_overrides[require_reference_viewer_global] = raise_forbidden

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags:
            mock_flags.enable_markdown_references = True

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {"type": "skill", "qualifier": "analyze", "id": "analyze"}
                        ]
                    },
                )

        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    async def test_resolve_batch_references_returns_all(self):
        """
        Test batch resolution returns results for all reference types.

        Verifies the API can handle mixed reference types in a single request.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_connection = MagicMock()
        mock_connection.id = "conn-uuid-456"
        mock_connection.name = "Test Server"
        mock_connection.server_name = "test-server"

        mock_repo = MagicMock()
        mock_repo.get_by_server_name = AsyncMock(return_value=mock_connection)

        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=True)

        mock_skill = MagicMock()
        mock_skill.name = "code-review"
        mock_skill.description = "Reviews code for quality"
        mock_skill.tags = ["review", "quality"]
        mock_skill.version = "1.0.0"

        app = create_test_app(user_override=mock_user, repo_override=mock_repo)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ), patch(
            "mcp_server_langgraph.skills.SkillDiscovery"
        ) as mock_discovery_class:
            mock_flags.enable_markdown_references = True
            mock_discovery = MagicMock()
            mock_discovery.get_skill = MagicMock(return_value=mock_skill)
            mock_discovery.load_from_directory = MagicMock()
            mock_discovery_class.return_value = mock_discovery

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "tool",
                                "qualifier": "test-server",
                                "id": "run_test",
                            },
                            {
                                "type": "skill",
                                "qualifier": "code-review",
                                "id": "code-review",
                            },
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"]) == 2

        # Verify tool reference
        tool_ref = next(r for r in data["resolved"] if r["type"] == "tool")
        assert tool_ref["status"] == "valid"
        assert tool_ref["metadata"]["connectionId"] == "conn-uuid-456"

        # Verify skill reference
        skill_ref = next(r for r in data["resolved"] if r["type"] == "skill")
        assert skill_ref["status"] == "valid"
        assert skill_ref["display_name"] == "code-review"

    async def test_feature_flag_disabled_returns_404(self):
        """
        Test that disabled feature flag returns 404.

        When enable_markdown_references is False, the endpoint should not be available.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}
        app = create_test_app(user_override=mock_user)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags:
            mock_flags.enable_markdown_references = False

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {"type": "skill", "qualifier": "test", "id": "test"}
                        ]
                    },
                )

        assert response.status_code == 404
        assert "not enabled" in response.json()["detail"]

    async def test_connection_not_found_returns_not_found_status(self):
        """
        Test that missing connection returns not_found status (not HTTP error).

        The API should return a resolved reference with status='not_found',
        not an HTTP 404.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_repo = MagicMock()
        mock_repo.get_by_server_name = AsyncMock(return_value=None)

        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=True)

        app = create_test_app(user_override=mock_user, repo_override=mock_repo)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            mock_flags.enable_markdown_references = True

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "tool",
                                "qualifier": "nonexistent",
                                "id": "some_tool",
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"]) == 1
        assert data["resolved"][0]["status"] == "not_found"

    async def test_tool_unauthorized_returns_unauthorized_status(self):
        """
        Test that unauthorized tool access returns unauthorized status.

        When OpenFGA denies connection:viewer, the reference should have
        status='unauthorized'.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_connection = MagicMock()
        mock_connection.id = "conn-uuid-789"
        mock_connection.name = "Private Server"
        mock_connection.server_name = "private"

        mock_repo = MagicMock()
        mock_repo.get_by_server_name = AsyncMock(return_value=mock_connection)

        # Auth middleware that denies access
        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=False)

        app = create_test_app(user_override=mock_user, repo_override=mock_repo)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            mock_flags.enable_markdown_references = True

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "tool",
                                "qualifier": "private",
                                "id": "secret_tool",
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"]) == 1
        assert data["resolved"][0]["status"] == "unauthorized"

    async def test_version_pinned_skill_includes_requested_version(self):
        """
        Test that version-pinned skill refs include requestedVersion in metadata.

        When resolving [[skill:name@version]], the metadata should contain
        the requested version for client-side validation.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=True)

        mock_skill = MagicMock()
        mock_skill.name = "analyzer"
        mock_skill.description = "Analyzes data"
        mock_skill.tags = ["analysis"]
        mock_skill.version = "2.0.0"  # Installed version

        app = create_test_app(user_override=mock_user)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ), patch(
            "mcp_server_langgraph.skills.SkillDiscovery"
        ) as mock_discovery_class:
            mock_flags.enable_markdown_references = True
            mock_discovery = MagicMock()
            mock_discovery.get_skill = MagicMock(return_value=mock_skill)
            mock_discovery.load_from_directory = MagicMock()
            mock_discovery_class.return_value = mock_discovery

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "skill",
                                "qualifier": "analyzer@1.5.0",
                                "id": "analyzer@1.5.0",
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        ref = data["resolved"][0]
        assert ref["status"] == "valid"
        assert ref["metadata"]["version"] == "2.0.0"  # Actual version
        assert ref["metadata"]["requestedVersion"] == "1.5.0"  # Requested version

    async def test_memory_reference_resolves_with_session_auth(self):
        """
        Test memory reference resolution with session-based authorization.

        Memory notes inherit viewer access from their parent session.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=True)

        mock_note = MagicMock()
        mock_note.id = "note-123"
        mock_note.title = "Meeting Notes"
        mock_note.content = "Important discussion about architecture decisions..."
        mock_note.category = "meetings"
        mock_note.tags = ["architecture", "planning"]
        mock_note.session_id = "session-456"
        mock_note.created_at = None

        app = create_test_app(user_override=mock_user)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ), patch(
            "mcp_server_langgraph.api.v1.memory.get_notes_manager"
        ) as mock_manager_fn:
            mock_flags.enable_markdown_references = True
            mock_manager = MagicMock()
            mock_manager.get_note = MagicMock(return_value=mock_note)
            mock_manager_fn.return_value = mock_manager

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "memory",
                                "qualifier": "note-123",
                                "id": "note-123",
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        ref = data["resolved"][0]
        assert ref["status"] == "valid"
        assert ref["display_name"] == "Meeting Notes"
        assert ref["metadata"]["sessionId"] == "session-456"

    async def test_plan_reference_resolves_with_session_auth(self):
        """
        Test plan reference resolution with session-based authorization.

        Execution plans inherit viewer access from their parent session.
        """
        mock_user = {"sub": "user:test-user-123", "user_id": "test-user-123"}

        mock_auth = AsyncMock(return_value=None)
        mock_auth.authorize = AsyncMock(return_value=True)

        mock_plan = MagicMock()
        mock_plan.id = "plan-789"
        mock_plan.task_type = "refactoring"
        mock_plan.complexity = "medium"
        mock_plan.risk_level = "low"
        mock_plan.status = "approved"
        mock_plan.session_id = "session-456"
        mock_plan.tools_needed = ["filesystem:read_file", "filesystem:write_file"]

        app = create_test_app(user_override=mock_user)

        with patch(
            "mcp_server_langgraph.api.v1.references.feature_flags"
        ) as mock_flags, patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ), patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo"
        ) as mock_repo_fn:
            mock_flags.enable_markdown_references = True
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=mock_plan)
            mock_repo_fn.return_value = mock_repo

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/references/resolve",
                    json={
                        "references": [
                            {
                                "type": "plan",
                                "qualifier": "plan-789",
                                "id": "plan-789",
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        data = response.json()
        ref = data["resolved"][0]
        assert ref["status"] == "valid"
        assert "refactoring" in ref["display_name"]
        assert ref["metadata"]["sessionId"] == "session-456"
