"""
Tests for connection scope-based authorization.

Tests the can_use_connection function which implements scope-aware access control:
- user scope: only owner can use
- project scope: project members can use
- session scope: only within the same session
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp_server_langgraph.auth.connection_scope import ConnectionScope, can_use_connection

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client for testing."""
    client = AsyncMock(return_value=None)
    client.check_permission = AsyncMock(return_value=True)
    return client


@pytest.fixture
def user_scoped_connection() -> MagicMock:
    """Create a user-scoped connection mock."""
    conn = MagicMock()
    conn.id = "conn-123"
    conn.owner_id = "user:alice"
    conn.scope = ConnectionScope.USER.value
    conn.project_id = None
    return conn


@pytest.fixture
def project_scoped_connection() -> MagicMock:
    """Create a project-scoped connection mock."""
    conn = MagicMock()
    conn.id = "conn-456"
    conn.owner_id = "user:alice"
    conn.scope = ConnectionScope.PROJECT.value
    conn.project_id = "project-789"
    return conn


@pytest.fixture
def session_scoped_connection() -> MagicMock:
    """Create a session-scoped connection mock."""
    conn = MagicMock()
    conn.id = "conn-789"
    conn.owner_id = "user:alice"
    conn.scope = ConnectionScope.SESSION.value
    conn.project_id = None
    return conn


class TestUserScopedConnection:
    """Tests for user-scoped connections (only owner can use)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_owner_can_use_user_scoped_connection(
        self, user_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Owner should always be able to use their own connection."""
        result = await can_use_connection(
            connection=user_scoped_connection,
            user_id="user:alice",
            project_id=None,
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is True
        # OpenFGA should not be called for owner access
        mock_openfga_client.check_permission.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_non_owner_cannot_use_user_scoped_connection(
        self, user_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Non-owner should not be able to use user-scoped connection."""
        result = await can_use_connection(
            connection=user_scoped_connection,
            user_id="user:bob",
            project_id=None,
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestProjectScopedConnection:
    """Tests for project-scoped connections (project members can use)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_owner_can_use_project_scoped_connection(
        self, project_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Owner should always be able to use their connection."""
        result = await can_use_connection(
            connection=project_scoped_connection,
            user_id="user:alice",
            project_id="project-789",
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is True
        # OpenFGA should not be called for owner access
        mock_openfga_client.check_permission.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_project_member_can_use_project_scoped_connection(
        self, project_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Project member should be able to use project-scoped connection."""
        # Mock OpenFGA to return True for project membership
        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        result = await can_use_connection(
            connection=project_scoped_connection,
            user_id="user:bob",
            project_id="project-789",
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is True
        # OpenFGA should be called to check project membership
        mock_openfga_client.check_permission.assert_called_once_with(
            user="user:bob",
            relation="member",
            object="project:project-789",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_non_member_cannot_use_project_scoped_connection(
        self, project_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Non-member should not be able to use project-scoped connection."""
        # Mock OpenFGA to return False for project membership
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        result = await can_use_connection(
            connection=project_scoped_connection,
            user_id="user:charlie",
            project_id="project-789",
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_with_wrong_project_cannot_use_connection(
        self, project_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """User in different project cannot use project-scoped connection."""
        result = await can_use_connection(
            connection=project_scoped_connection,
            user_id="user:bob",
            project_id="other-project",  # Different project
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestSessionScopedConnection:
    """Tests for session-scoped connections (ephemeral, session-only)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_owner_can_use_session_scoped_connection(
        self, session_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Owner should always be able to use their connection."""
        result = await can_use_connection(
            connection=session_scoped_connection,
            user_id="user:alice",
            project_id=None,
            session_id="session-abc",
            openfga_client=mock_openfga_client,
        )
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_same_session_can_use_session_scoped_connection(
        self, session_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """User in same session can use session-scoped connection."""
        # Set the session ID on the connection
        session_scoped_connection.session_id = "session-abc"

        result = await can_use_connection(
            connection=session_scoped_connection,
            user_id="user:bob",  # Different user
            project_id=None,
            session_id="session-abc",  # Same session
            openfga_client=mock_openfga_client,
        )
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_different_session_cannot_use_session_scoped_connection(
        self, session_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """User in different session cannot use session-scoped connection."""
        session_scoped_connection.session_id = "session-abc"

        result = await can_use_connection(
            connection=session_scoped_connection,
            user_id="user:bob",
            project_id=None,
            session_id="session-xyz",  # Different session
            openfga_client=mock_openfga_client,
        )
        assert result is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_none_openfga_client_allows_owner_access(self, user_scoped_connection: MagicMock) -> None:
        """Owner access should work even without OpenFGA client."""
        result = await can_use_connection(
            connection=user_scoped_connection,
            user_id="user:alice",
            project_id=None,
            session_id=None,
            openfga_client=None,
        )
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_none_openfga_client_denies_non_owner_project_access(self, project_scoped_connection: MagicMock) -> None:
        """Non-owner project access should be denied without OpenFGA client."""
        result = await can_use_connection(
            connection=project_scoped_connection,
            user_id="user:bob",
            project_id="project-789",
            session_id=None,
            openfga_client=None,  # No OpenFGA client
        )
        # Without OpenFGA, we can't verify project membership, so deny
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_missing_project_id_denies_project_scoped_access(
        self, project_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Project-scoped connection requires project_id context."""
        result = await can_use_connection(
            connection=project_scoped_connection,
            user_id="user:bob",
            project_id=None,  # No project context
            session_id=None,
            openfga_client=mock_openfga_client,
        )
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_missing_session_id_denies_session_scoped_access(
        self, session_scoped_connection: MagicMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Session-scoped connection requires session_id context."""
        session_scoped_connection.session_id = "session-abc"

        result = await can_use_connection(
            connection=session_scoped_connection,
            user_id="user:bob",
            project_id=None,
            session_id=None,  # No session context
            openfga_client=mock_openfga_client,
        )
        assert result is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
