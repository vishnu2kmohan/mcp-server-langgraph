"""
Unit tests for database session management.

Tests SQLAlchemy async engine and session lifecycle management.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.database import session as session_module
from mcp_server_langgraph.database.session import (
    cleanup_database,
    get_async_session,
    get_engine,
    get_session_maker,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global engine and session maker state before each test.

    Note: We always reset to None after yield (not restore original) to avoid
    xdist contamination where "original" values from other workers leak.
    """
    # Reset to None for test isolation
    session_module._engine = None
    session_module._async_session_maker = None

    yield

    # Always reset to None after test (don't restore potentially contaminated state)
    session_module._engine = None
    session_module._async_session_maker = None


@pytest.mark.xdist_group(name="test_database_session")
class TestGetEngine:
    """Tests for get_engine function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_engine_creates_engine_with_correct_config(self) -> None:
        """Test that get_engine creates async engine with expected parameters."""
        mock_engine = MagicMock()

        with patch(
            "mcp_server_langgraph.database.session.create_async_engine",
            return_value=mock_engine,
        ) as mock_create:
            result = get_engine("postgresql+asyncpg://user:pass@localhost/testdb")

            # Use 'is' for identity comparison to avoid xdist MagicMock comparison issues
            assert result is mock_create.return_value
            mock_create.assert_called_once()

            # Verify call arguments
            call_args = mock_create.call_args
            assert call_args[0][0] == "postgresql+asyncpg://user:pass@localhost/testdb"
            assert call_args[1]["echo"] is False
            assert call_args[1]["pool_size"] == 10
            assert call_args[1]["max_overflow"] == 20
            assert call_args[1]["pool_pre_ping"] is True
            assert call_args[1]["pool_recycle"] == 3600

    def test_get_engine_with_echo_enabled(self) -> None:
        """Test that get_engine passes echo parameter correctly."""
        mock_engine = MagicMock()

        with patch(
            "mcp_server_langgraph.database.session.create_async_engine",
            return_value=mock_engine,
        ) as mock_create:
            result = get_engine("postgresql+asyncpg://localhost/testdb", echo=True)

            # Use mock_create.return_value for identity check to avoid xdist isolation issues
            assert result is mock_create.return_value
            call_args = mock_create.call_args
            assert call_args[1]["echo"] is True

    def test_get_engine_reuses_existing_engine(self) -> None:
        """Test that get_engine returns cached engine on subsequent calls."""
        mock_engine = MagicMock()

        with patch(
            "mcp_server_langgraph.database.session.create_async_engine",
            return_value=mock_engine,
        ) as mock_create:
            # First call creates engine
            result1 = get_engine("postgresql+asyncpg://localhost/testdb")
            # Second call should reuse cached engine
            result2 = get_engine("postgresql+asyncpg://localhost/testdb")

            assert result1 == result2
            assert mock_create.call_count == 1  # Only called once


@pytest.mark.xdist_group(name="test_database_session")
class TestGetSessionMaker:
    """Tests for get_session_maker function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_session_maker_creates_session_maker(self) -> None:
        """Test that get_session_maker creates async session maker."""
        mock_engine = MagicMock()
        mock_session_maker = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.database.session.create_async_engine",
                return_value=mock_engine,
            ),
            patch(
                "mcp_server_langgraph.database.session.async_sessionmaker",
                return_value=mock_session_maker,
            ) as mock_sm_class,
        ):
            result = get_session_maker("postgresql+asyncpg://localhost/testdb")

            # Use 'is' with return_value for identity check to avoid xdist MagicMock comparison issues
            assert result is mock_sm_class.return_value
            mock_sm_class.assert_called_once()

            # Verify session maker configuration
            call_kwargs = mock_sm_class.call_args[1]
            assert call_kwargs["expire_on_commit"] is False
            assert call_kwargs["autoflush"] is False
            assert call_kwargs["autocommit"] is False

    def test_get_session_maker_reuses_existing(self) -> None:
        """Test that get_session_maker returns cached instance."""
        mock_engine = MagicMock()
        mock_session_maker = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.database.session.create_async_engine",
                return_value=mock_engine,
            ),
            patch(
                "mcp_server_langgraph.database.session.async_sessionmaker",
                return_value=mock_session_maker,
            ) as mock_sm_class,
        ):
            result1 = get_session_maker("postgresql+asyncpg://localhost/testdb")
            result2 = get_session_maker("postgresql+asyncpg://localhost/testdb")

            assert result1 == result2
            assert mock_sm_class.call_count == 1


@pytest.mark.xdist_group(name="test_database_session")
class TestGetAsyncSession:
    """Tests for get_async_session context manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_async_session_yields_session(self) -> None:
        """Test that get_async_session yields a session and commits on success."""
        mock_engine = MagicMock()
        mock_session = AsyncMock(return_value=None)  # Container for session methods
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.rollback = AsyncMock(return_value=None)
        mock_session.close = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.database.session.create_async_engine",
                return_value=mock_engine,
            ),
            patch(
                "mcp_server_langgraph.database.session.async_sessionmaker",
                return_value=mock_session_maker,
            ),
        ):
            async with get_async_session("postgresql+asyncpg://localhost/testdb") as session:
                assert session == mock_session

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_session_rollback_on_exception(self) -> None:
        """Test that get_async_session rolls back on exception."""
        mock_engine = MagicMock()
        mock_session = AsyncMock(return_value=None)  # Container for session methods
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.rollback = AsyncMock(return_value=None)
        mock_session.close = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.database.session.create_async_engine",
                return_value=mock_engine,
            ),
            patch(
                "mcp_server_langgraph.database.session.async_sessionmaker",
                return_value=mock_session_maker,
            ),
        ):
            with pytest.raises(ValueError, match="Test error"):
                async with get_async_session("postgresql+asyncpg://localhost/testdb") as session:
                    assert session == mock_session
                    raise ValueError("Test error")

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


@pytest.mark.xdist_group(name="test_database_session")
class TestInitDatabase:
    """Tests for init_database function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_database_is_callable(self) -> None:
        """Test that init_database is an async function.

        This is a minimal test to verify the function exists and has the
        expected signature. Full behavioral testing of init_database (verifying
        tables are created) is done in integration tests with a real database.

        Note: Mocking internal details of init_database is unreliable under
        pytest-xdist due to global _engine caching. Integration tests provide
        proper coverage for the actual table creation behavior.
        """
        import inspect

        # Verify init_database is an async function with expected signature
        assert inspect.iscoroutinefunction(session_module.init_database)

        # Verify the function has the expected parameters
        sig = inspect.signature(session_module.init_database)
        param_names = list(sig.parameters.keys())
        assert "database_url" in param_names
        assert "echo" in param_names


@pytest.mark.xdist_group(name="test_database_session")
class TestCleanupDatabase:
    """Tests for cleanup_database function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_database_disposes_engine(self) -> None:
        """Test that cleanup_database disposes the engine."""
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock(return_value=None)

        # Set up the global engine
        session_module._engine = mock_engine
        session_module._async_session_maker = MagicMock()

        await cleanup_database()

        mock_engine.dispose.assert_called_once()
        assert session_module._engine is None
        assert session_module._async_session_maker is None

    @pytest.mark.asyncio
    async def test_cleanup_database_does_nothing_when_no_engine(self) -> None:
        """Test that cleanup_database handles no engine gracefully."""
        # Ensure no engine is set
        session_module._engine = None
        session_module._async_session_maker = None

        # Should not raise
        await cleanup_database()

        assert session_module._engine is None
        assert session_module._async_session_maker is None
