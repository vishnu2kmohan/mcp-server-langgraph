"""
Tests for SessionGoalRepository Dependency Injection.

TDD: Tests written first to define expected behavior of get_session_goal_repository.
"""

import pytest
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.repositories.session_goal import (
    PostgresSessionGoalRepository,
    SessionGoalRepository,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestGetSessionGoalRepository:
    """Tests for get_session_goal_repository dependency."""

    def test_returns_session_goal_repository_instance(self) -> None:
        """Verify dependency returns a SessionGoalRepository instance."""
        from mcp_server_langgraph.core.dependencies import get_session_goal_repository

        # Create mock session
        mock_session = MagicMock(spec=AsyncSession)

        # Get repository
        repo = get_session_goal_repository(session=mock_session)

        # Verify it's a SessionGoalRepository
        assert isinstance(repo, SessionGoalRepository)

    def test_returns_postgres_repository_implementation(self) -> None:
        """Verify dependency returns PostgresSessionGoalRepository."""
        from mcp_server_langgraph.core.dependencies import get_session_goal_repository

        # Create mock session
        mock_session = MagicMock(spec=AsyncSession)

        # Get repository
        repo = get_session_goal_repository(session=mock_session)

        # Verify specific implementation
        assert isinstance(repo, PostgresSessionGoalRepository)

    def test_repository_has_session_injected(self) -> None:
        """Verify the database session is properly injected."""
        from mcp_server_langgraph.core.dependencies import get_session_goal_repository

        # Create mock session
        mock_session = MagicMock(spec=AsyncSession)

        # Get repository
        repo = get_session_goal_repository(session=mock_session)

        # Verify session is set (access internal attribute)
        assert repo._session is mock_session

    def test_dependency_signature_compatible_with_fastapi(self) -> None:
        """Verify function signature is compatible with FastAPI Depends."""
        import inspect
        from mcp_server_langgraph.core.dependencies import get_session_goal_repository

        # Get function signature
        sig = inspect.signature(get_session_goal_repository)

        # Verify it has session parameter
        assert "session" in sig.parameters

        # Verify session parameter has default (for Depends injection)
        session_param = sig.parameters["session"]
        assert session_param.default is not inspect.Parameter.empty

    def test_each_call_returns_new_instance(self) -> None:
        """Verify each call creates a new repository (not singleton)."""
        from mcp_server_langgraph.core.dependencies import get_session_goal_repository

        mock_session1 = MagicMock(spec=AsyncSession)
        mock_session2 = MagicMock(spec=AsyncSession)

        repo1 = get_session_goal_repository(session=mock_session1)
        repo2 = get_session_goal_repository(session=mock_session2)

        # Should be different instances
        assert repo1 is not repo2

        # Should have different sessions
        assert repo1._session is not repo2._session

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
