"""
Unit tests for the references resolution API.

Tests the /api/v1/references/resolve endpoint with various
reference types and authorization scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.references import references_router
from mcp_server_langgraph.storage.models import MCPConnection

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_feature_flags():
    """Mock feature flags with markdown references enabled."""
    with patch("mcp_server_langgraph.api.v1.references.feature_flags") as mock_flags:
        mock_flags.enable_markdown_references = True
        yield mock_flags


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "sub": "user-123",
        "user_id": "user-123",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_auth_middleware():
    """Mock OpenFGA auth middleware."""
    mock = AsyncMock()
    mock.authorize = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_connection():
    """Mock MCP connection."""
    return MCPConnection(
        id="conn-uuid-123",
        name="Test Connection",
        url="https://example.com",
        transport="streamable_http",
        auth_type="none",
        status="connected",
        server_name="filesystem",
        owner_id="user-123",
    )


@pytest.fixture
def mock_connection_repo(mock_connection):
    """Mock connection repository."""
    mock = AsyncMock()
    mock.get_by_server_name = AsyncMock(return_value=mock_connection)
    return mock


@pytest.fixture
def app(mock_feature_flags, mock_user, mock_auth_middleware, mock_connection_repo):
    """Create test FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(references_router, prefix="/api/v1")

    # Override dependencies
    async def mock_require_reference_viewer_global():
        return mock_user

    async def mock_get_connection_repository():
        return mock_connection_repo

    app.dependency_overrides["mcp_server_langgraph.api.v1.references.require_reference_viewer_global"] = (
        mock_require_reference_viewer_global
    )

    # Patch auth middleware getter
    with patch(
        "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
        return_value=mock_auth_middleware,
    ):
        with patch(
            "mcp_server_langgraph.api.v1.references.require_reference_viewer_global",
            return_value=mock_user,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.references.get_connection_repository",
                return_value=mock_connection_repo,
            ):
                yield app


@pytest.fixture
def client(app):
    """Test client for the app."""
    return TestClient(app)


class TestReferencesResolver:
    """Tests for POST /references/resolve endpoint."""

    @pytest.mark.unit
    async def test_resolve_empty_references_returns_empty_list(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Empty references list returns empty resolved list."""
        from mcp_server_langgraph.api.v1.references import (
            ResolveRequest,
            resolve_references,
        )

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            result = await resolve_references(
                body=ResolveRequest(references=[]),
                request=request,
                user=mock_user,
                conn_repo=mock_connection_repo,
            )

        assert result.resolved == []

    @pytest.mark.unit
    async def test_resolve_tool_reference_returns_valid_status(
        self,
        mock_feature_flags,
        mock_user,
        mock_connection,
        mock_connection_repo,
        mock_auth_middleware,
    ):
        """Tool reference with valid connection returns valid status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            result = await resolve_references(
                body=ResolveRequest(references=[ReferenceRequest(type="tool", qualifier="filesystem", id="read_file")]),
                request=request,
                user=mock_user,
                conn_repo=mock_connection_repo,
            )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.type == "tool"
        assert ref.qualifier == "filesystem"
        assert ref.id == "read_file"
        assert ref.status == "valid"
        assert ref.metadata.get("connectionId") == mock_connection.id

    @pytest.mark.unit
    async def test_resolve_tool_reference_not_found(self, mock_feature_flags, mock_user, mock_auth_middleware):
        """Tool reference with missing connection returns not_found status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_server_name = AsyncMock(return_value=None)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            result = await resolve_references(
                body=ResolveRequest(references=[ReferenceRequest(type="tool", qualifier="missing_server", id="some_tool")]),
                request=request,
                user=mock_user,
                conn_repo=mock_repo,
            )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "not_found"

    @pytest.mark.unit
    async def test_resolve_tool_reference_unauthorized(
        self,
        mock_feature_flags,
        mock_user,
        mock_connection,
        mock_connection_repo,
    ):
        """Tool reference without viewer access returns unauthorized status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        # Auth middleware that denies access
        mock_auth = AsyncMock()
        mock_auth.authorize = AsyncMock(return_value=False)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            result = await resolve_references(
                body=ResolveRequest(references=[ReferenceRequest(type="tool", qualifier="filesystem", id="read_file")]),
                request=request,
                user=mock_user,
                conn_repo=mock_connection_repo,
            )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "unauthorized"

    @pytest.mark.unit
    async def test_resolve_skill_reference_valid(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Skill reference with valid skill returns valid status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_skill = MagicMock()
        mock_skill.name = "Code Review"
        mock_skill.description = "Review code for issues"
        mock_skill.tags = ["code", "review"]
        mock_skill.version = "1.0.0"

        mock_discovery = MagicMock()
        mock_discovery.get_skill = MagicMock(return_value=mock_skill)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.skills.SkillDiscovery",
                return_value=mock_discovery,
            ):
                result = await resolve_references(
                    body=ResolveRequest(
                        references=[ReferenceRequest(type="skill", qualifier="code-review", id="code-review")]
                    ),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.type == "skill"
        assert ref.status == "valid"
        assert ref.display_name == "Code Review"
        assert ref.description == "Review code for issues"

    @pytest.mark.unit
    async def test_resolve_skill_reference_not_found(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Skill reference with missing skill returns not_found status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_discovery = MagicMock()
        mock_discovery.get_skill = MagicMock(return_value=None)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.skills.SkillDiscovery",
                return_value=mock_discovery,
            ):
                result = await resolve_references(
                    body=ResolveRequest(
                        references=[
                            ReferenceRequest(
                                type="skill",
                                qualifier="nonexistent",
                                id="nonexistent",
                            )
                        ]
                    ),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "not_found"

    @pytest.mark.unit
    async def test_resolve_artifact_reference_unauthorized(self, mock_feature_flags, mock_user, mock_connection_repo):
        """Artifact reference without viewer access returns unauthorized status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        # Auth middleware that denies artifact access
        mock_auth = AsyncMock()
        mock_auth.authorize = AsyncMock(return_value=False)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            result = await resolve_references(
                body=ResolveRequest(references=[ReferenceRequest(type="artifact", qualifier="chart-123", id="chart-123")]),
                request=request,
                user=mock_user,
                conn_repo=mock_connection_repo,
            )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "unauthorized"

    @pytest.mark.unit
    async def test_resolve_batch_references(
        self,
        mock_feature_flags,
        mock_user,
        mock_connection,
        mock_connection_repo,
        mock_auth_middleware,
    ):
        """Batch resolution handles multiple references."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.description = "A test skill"
        mock_skill.tags = []
        mock_skill.version = "1.0.0"

        mock_discovery = MagicMock()
        mock_discovery.get_skill = MagicMock(return_value=mock_skill)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.skills.SkillDiscovery",
                return_value=mock_discovery,
            ):
                result = await resolve_references(
                    body=ResolveRequest(
                        references=[
                            ReferenceRequest(type="tool", qualifier="filesystem", id="read_file"),
                            ReferenceRequest(type="skill", qualifier="test-skill", id="test-skill"),
                        ]
                    ),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 2
        assert result.resolved[0].type == "tool"
        assert result.resolved[0].status == "valid"
        assert result.resolved[1].type == "skill"
        assert result.resolved[1].status == "valid"

    @pytest.mark.unit
    async def test_feature_flag_disabled_returns_404(self, mock_user, mock_connection_repo):
        """When feature flag is disabled, returns 404."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.references import (
            ResolveRequest,
            resolve_references,
        )

        with patch("mcp_server_langgraph.api.v1.references.feature_flags") as mock_flags:
            mock_flags.enable_markdown_references = False

            request = MagicMock()
            with pytest.raises(HTTPException) as exc_info:
                await resolve_references(
                    body=ResolveRequest(references=[]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

            assert exc_info.value.status_code == 404
            assert "not enabled" in str(exc_info.value.detail).lower()

    @pytest.mark.unit
    async def test_resolve_memory_reference_valid(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Memory reference with valid note returns valid status."""
        from datetime import UTC, datetime

        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )
        from mcp_server_langgraph.memory.notes import Note

        mock_note = Note(
            id="note-abc123",
            content="This is a test note with important information.",
            title="Architecture Decision",
            category="architecture",
            tags=["adr", "decisions"],
            session_id="session-xyz",
            user_id="user-123",
            created_at=datetime.now(UTC),
        )

        mock_manager = MagicMock()
        mock_manager.get_note = MagicMock(return_value=mock_note)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.memory.get_notes_manager",
                return_value=mock_manager,
            ):
                result = await resolve_references(
                    body=ResolveRequest(references=[ReferenceRequest(type="memory", qualifier="note", id="note-abc123")]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.type == "memory"
        assert ref.status == "valid"
        assert ref.display_name == "Architecture Decision"
        assert ref.metadata.get("sessionId") == "session-xyz"
        assert "adr" in ref.metadata.get("tags", [])

    @pytest.mark.unit
    async def test_resolve_memory_reference_not_found(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Memory reference with missing note returns not_found status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_manager = MagicMock()
        mock_manager.get_note = MagicMock(return_value=None)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.memory.get_notes_manager",
                return_value=mock_manager,
            ):
                result = await resolve_references(
                    body=ResolveRequest(references=[ReferenceRequest(type="memory", qualifier="note", id="nonexistent")]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "not_found"

    @pytest.mark.unit
    async def test_resolve_memory_reference_unauthorized(self, mock_feature_flags, mock_user, mock_connection_repo):
        """Memory reference without session viewer access returns unauthorized."""
        from datetime import UTC, datetime

        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )
        from mcp_server_langgraph.memory.notes import Note

        mock_note = Note(
            id="note-abc123",
            content="Test content",
            session_id="session-restricted",
            user_id="user-123",
            created_at=datetime.now(UTC),
        )

        mock_manager = MagicMock()
        mock_manager.get_note = MagicMock(return_value=mock_note)

        # Auth middleware that denies session access
        mock_auth = AsyncMock()
        mock_auth.authorize = AsyncMock(return_value=False)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.memory.get_notes_manager",
                return_value=mock_manager,
            ):
                result = await resolve_references(
                    body=ResolveRequest(references=[ReferenceRequest(type="memory", qualifier="note", id="note-abc123")]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "unauthorized"

    @pytest.mark.unit
    async def test_resolve_plan_reference_valid(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Plan reference with valid plan returns valid status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_plan = MagicMock()
        mock_plan.plan_id = "plan-xyz789"
        mock_plan.session_id = "session-abc"
        mock_plan.task_type = "code_generation"
        mock_plan.complexity = "medium"
        mock_plan.risk_level = "low"
        mock_plan.status = "approved"
        mock_plan.tools_needed = ["filesystem:read", "filesystem:write"]

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_plan)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
                return_value=mock_repo,
            ):
                result = await resolve_references(
                    body=ResolveRequest(references=[ReferenceRequest(type="plan", qualifier="plan", id="plan-xyz789")]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.type == "plan"
        assert ref.status == "valid"
        assert "code_generation" in ref.display_name
        assert "medium complexity" in ref.description
        assert ref.metadata.get("sessionId") == "session-abc"

    @pytest.mark.unit
    async def test_resolve_plan_reference_not_found(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Plan reference with missing plan returns not_found status."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=None)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
                return_value=mock_repo,
            ):
                result = await resolve_references(
                    body=ResolveRequest(references=[ReferenceRequest(type="plan", qualifier="plan", id="nonexistent")]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "not_found"

    @pytest.mark.unit
    async def test_resolve_plan_reference_unauthorized(self, mock_feature_flags, mock_user, mock_connection_repo):
        """Plan reference without session viewer access returns unauthorized."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_plan = MagicMock()
        mock_plan.plan_id = "plan-xyz789"
        mock_plan.session_id = "session-restricted"
        mock_plan.task_type = "code_generation"

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_plan)

        # Auth middleware that denies session access
        mock_auth = AsyncMock()
        mock_auth.authorize = AsyncMock(return_value=False)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
                return_value=mock_repo,
            ):
                result = await resolve_references(
                    body=ResolveRequest(references=[ReferenceRequest(type="plan", qualifier="plan", id="plan-xyz789")]),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.status == "unauthorized"

    @pytest.mark.unit
    async def test_resolve_version_pinned_skill_reference(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Version-pinned skill reference extracts name and version correctly."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_skill = MagicMock()
        mock_skill.name = "Code Review"
        mock_skill.description = "Review code for issues"
        mock_skill.tags = ["code", "review"]
        mock_skill.version = "1.2.0"

        mock_discovery = MagicMock()
        mock_discovery.get_skill = MagicMock(return_value=mock_skill)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.skills.SkillDiscovery",
                return_value=mock_discovery,
            ):
                result = await resolve_references(
                    body=ResolveRequest(
                        references=[
                            ReferenceRequest(
                                type="skill",
                                qualifier="code-review@1.2.0",
                                id="code-review@1.2.0",
                            )
                        ]
                    ),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        assert len(result.resolved) == 1
        ref = result.resolved[0]
        assert ref.type == "skill"
        assert ref.status == "valid"
        assert ref.display_name == "Code Review"
        # Metadata should include requested version
        assert ref.metadata.get("requestedVersion") == "1.2.0"
        assert ref.metadata.get("version") == "1.2.0"

    @pytest.mark.unit
    async def test_resolve_version_pinned_skill_extracts_name(
        self, mock_feature_flags, mock_user, mock_connection_repo, mock_auth_middleware
    ):
        """Version-pinned skill lookup uses skill name without version suffix."""
        from mcp_server_langgraph.api.v1.references import (
            ReferenceRequest,
            ResolveRequest,
            resolve_references,
        )

        mock_skill = MagicMock()
        mock_skill.name = "Analyzer"
        mock_skill.description = "Analyze data"
        mock_skill.tags = []
        mock_skill.version = "2.0.0"

        mock_discovery = MagicMock()
        mock_discovery.get_skill = MagicMock(return_value=mock_skill)

        request = MagicMock()
        with patch(
            "mcp_server_langgraph.api.v1.references.get_auth_middleware_from_request",
            return_value=mock_auth_middleware,
        ):
            with patch(
                "mcp_server_langgraph.skills.SkillDiscovery",
                return_value=mock_discovery,
            ):
                result = await resolve_references(
                    body=ResolveRequest(
                        references=[
                            ReferenceRequest(
                                type="skill",
                                qualifier="analyzer@2.0.0",
                                id="analyzer@2.0.0",
                            )
                        ]
                    ),
                    request=request,
                    user=mock_user,
                    conn_repo=mock_connection_repo,
                )

        # Verify get_skill was called with just the skill name (without version)
        mock_discovery.get_skill.assert_called_with("analyzer")
        assert result.resolved[0].status == "valid"
