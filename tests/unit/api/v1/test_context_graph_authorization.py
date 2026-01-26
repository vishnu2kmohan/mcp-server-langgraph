"""Context Graph API Authorization Tests (ADR-0101).

TDD: Tests written FIRST to define authorization behavior.

Authorization model:
- Decision traces belong to sessions
- Users need viewer access to the session to view traces
- Users need viewer access to the session to search precedents
- Organization-scoped precedent search requires org membership

Reference: ADR-0101 Context Graphs, ADR-0068 Gateway-Level Authentication
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from starlette.requests import Request

from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

if TYPE_CHECKING:
    pass

# Memory safety for pytest-xdist
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.context_graph,
    pytest.mark.xdist_group(name="context_graph_auth"),
]


def _create_mock_request(auth_service: Any = None) -> MagicMock:
    """Create a mock FastAPI request with app state."""
    mock_request = MagicMock(spec=Request)
    mock_request.app = MagicMock()
    mock_request.app.state = MagicMock()
    mock_request.app.state.auth_middleware = auth_service
    mock_request.app.state.decision_emitter = MagicMock()
    return mock_request


class TestContextGraphTraceAuthorization:
    """Test authorization for individual trace retrieval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_trace_requires_session_viewer_access(self) -> None:
        """User must have viewer access to the session to view a trace."""
        from mcp_server_langgraph.api.v1.context_graph import get_trace

        # GIVEN a trace that belongs to session-123
        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(
            return_value=MagicMock(
                trace_id="trace-001",
                session_id="session-123",
                user_id="user-alice",
                organization_id="org-001",
            )
        )

        # AND a user who has viewer access to session-123
        mock_user = {"sub": "user-alice", "organization_id": "org-001"}

        # AND authorization is granted
        mock_auth_service = AsyncMock(return_value=None)
        mock_auth_service.authorize = AsyncMock(return_value=True)

        mock_request = _create_mock_request(mock_auth_service)

        # WHEN getting the trace with authorization check
        trace = await get_trace(
            trace_id="trace-001",
            request=mock_request,
            repo=mock_repo,
            current_user=mock_user,
        )

        # THEN the trace is returned
        assert trace.trace_id == "trace-001"

        # AND authorization was checked for session viewer access
        mock_auth_service.authorize.assert_called_once()
        call_args = mock_auth_service.authorize.call_args
        assert call_args.kwargs["relation"] == "viewer"
        assert call_args.kwargs["resource"] == "session:session-123"

    @pytest.mark.asyncio
    async def test_get_trace_denies_unauthorized_user(self) -> None:
        """User without session access should get 403 Forbidden."""
        from mcp_server_langgraph.api.v1.context_graph import get_trace

        # GIVEN a trace that belongs to session-123
        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(
            return_value=MagicMock(
                trace_id="trace-001",
                session_id="session-123",
                user_id="user-alice",
                organization_id="org-001",
            )
        )

        # AND a user who does NOT have viewer access
        mock_user = {"sub": "user-bob", "organization_id": "org-002"}

        # AND authorization is denied
        mock_auth_service = AsyncMock(return_value=None)
        mock_auth_service.authorize = AsyncMock(return_value=False)

        mock_request = _create_mock_request(mock_auth_service)

        # WHEN getting the trace
        # THEN should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await get_trace(
                trace_id="trace-001",
                request=mock_request,
                repo=mock_repo,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_trace_returns_404_before_auth_check_if_not_found(self) -> None:
        """Non-existent trace should return 404 (info leak prevention)."""
        from mcp_server_langgraph.api.v1.context_graph import get_trace

        # GIVEN a trace that doesn't exist
        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(return_value=None)

        mock_user = {"sub": "user-alice", "organization_id": "org-001"}
        mock_request = _create_mock_request()

        # WHEN getting the trace
        # THEN should raise 404 (before any auth check)
        with pytest.raises(HTTPException) as exc_info:
            await get_trace(
                trace_id="nonexistent",
                request=mock_request,
                repo=mock_repo,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestContextGraphSessionTracesAuthorization:
    """Test authorization for session trace listing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_traces_requires_session_viewer_access(self) -> None:
        """User must have viewer access to the session to list traces."""
        from mcp_server_langgraph.api.v1.context_graph import get_session_traces

        # GIVEN a mock repository with traces
        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_session = AsyncMock(return_value=[])

        # AND a user who has viewer access
        mock_user = {"sub": "user-alice", "organization_id": "org-001"}

        # AND authorization is granted
        mock_auth_service = AsyncMock(return_value=None)
        mock_auth_service.authorize = AsyncMock(return_value=True)

        mock_request = _create_mock_request(mock_auth_service)

        # WHEN listing session traces
        traces = await get_session_traces(
            session_id="session-123",
            request=mock_request,
            limit=100,
            offset=0,
            repo=mock_repo,
            current_user=mock_user,
        )

        # THEN authorization was checked
        mock_auth_service.authorize.assert_called_once()
        call_args = mock_auth_service.authorize.call_args
        assert call_args.kwargs["relation"] == "viewer"
        assert call_args.kwargs["resource"] == "session:session-123"

    @pytest.mark.asyncio
    async def test_get_session_traces_denies_unauthorized_user(self) -> None:
        """User without session access should get 403 Forbidden."""
        from mcp_server_langgraph.api.v1.context_graph import get_session_traces

        mock_repo = AsyncMock(return_value=None)
        mock_user = {"sub": "user-bob", "organization_id": "org-002"}

        # AND authorization is denied
        mock_auth_service = AsyncMock(return_value=None)
        mock_auth_service.authorize = AsyncMock(return_value=False)

        mock_request = _create_mock_request(mock_auth_service)

        # WHEN listing session traces
        # THEN should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await get_session_traces(
                session_id="session-123",
                request=mock_request,
                limit=100,
                offset=0,
                repo=mock_repo,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestContextGraphPrecedentSearchAuthorization:
    """Test authorization for precedent search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_precedent_search_scoped_to_user_organization(self) -> None:
        """Precedent search should only return results from user's organization."""
        from mcp_server_langgraph.api.v1.context_graph import search_precedents
        from mcp_server_langgraph.storage.models import PrecedentSearchRequest

        # GIVEN a user in org-001
        mock_user = {"sub": "user-alice", "organization_id": "org-001"}

        # AND a mock semantic index manager
        mock_manager = MagicMock()
        mock_manager.search_precedents = AsyncMock(return_value=[])

        # AND feature flags enabled
        mock_flags = MockFeatureFlags(
            enable_context_graph=True,
            enable_precedent_search=True,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_request = _create_mock_request()

        request_body = PrecedentSearchRequest(query="test query", limit=10)

        # WHEN searching for precedents
        with patch(
            "mcp_server_langgraph.api.v1.context_graph.feature_flags", mock_flags
        ), patch(
            "mcp_server_langgraph.core.dependencies.get_semantic_index_manager",
            return_value=mock_manager,
        ):
            await search_precedents(
                body=request_body,
                request=mock_request,
                repo=mock_repo,
                current_user=mock_user,
            )

        # THEN search should be scoped to user's organization
        mock_manager.search_precedents.assert_called_once()
        call_kwargs = mock_manager.search_precedents.call_args.kwargs
        assert call_kwargs["organization_id"] == "org-001"
        assert call_kwargs["user_id"] == "user-alice"

    @pytest.mark.asyncio
    async def test_precedent_search_disabled_returns_503(self) -> None:
        """Precedent search should return 503 when feature disabled."""
        from mcp_server_langgraph.api.v1.context_graph import search_precedents
        from mcp_server_langgraph.storage.models import PrecedentSearchRequest

        mock_user = {"sub": "user-alice", "organization_id": "org-001"}
        mock_repo = AsyncMock(return_value=None)
        mock_request = _create_mock_request()

        # AND precedent search is disabled
        mock_flags = MockFeatureFlags(
            enable_context_graph=True,
            enable_precedent_search=False,
        )

        request_body = PrecedentSearchRequest(query="test query", limit=10)

        # WHEN searching for precedents
        with patch(
            "mcp_server_langgraph.api.v1.context_graph.feature_flags", mock_flags
        ):
            # THEN should raise 503
            with pytest.raises(HTTPException) as exc_info:
                await search_precedents(
                    body=request_body,
                    request=mock_request,
                    repo=mock_repo,
                    current_user=mock_user,
                )

        assert exc_info.value.status_code == 503
        assert "not enabled" in exc_info.value.detail.lower()


class TestContextGraphAuthorizationMetrics:
    """Test that authorization denials are logged for audit."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorization_denial_is_logged(self) -> None:
        """Authorization denial should be logged for audit compliance."""
        from mcp_server_langgraph.api.v1.context_graph import get_trace

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(
            return_value=MagicMock(
                trace_id="trace-001",
                session_id="session-123",
                user_id="user-alice",
                organization_id="org-001",
            )
        )

        mock_user = {"sub": "user-bob", "organization_id": "org-002"}

        mock_auth_service = AsyncMock(return_value=None)
        mock_auth_service.authorize = AsyncMock(return_value=False)

        mock_request = _create_mock_request(mock_auth_service)

        # WHEN authorization is denied
        with patch(
            "mcp_server_langgraph.api.v1.context_graph.log_authorization_denied"
        ) as mock_log:
            with pytest.raises(HTTPException):
                await get_trace(
                    trace_id="trace-001",
                    request=mock_request,
                    repo=mock_repo,
                    current_user=mock_user,
                )

            # THEN denial is logged for audit
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["user_id"] == "user:user-bob"
            assert call_kwargs["relation"] == "viewer"
            assert "session:session-123" in call_kwargs["resource"]
