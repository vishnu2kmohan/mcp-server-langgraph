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
    init_database,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global engine and session maker state before each test."""
    # Store original values
    original_engine = session_module._engine
    original_session_maker = session_module._async_session_maker

    # Reset to None for test isolation
    session_module._engine = None
    session_module._async_session_maker = None

    yield

    # Restore original values
    session_module._engine = original_engine
    session_module._async_session_maker = original_session_maker


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

            assert result == mock_engine
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

            assert result == mock_session_maker
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
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

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
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

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
    async def test_init_database_creates_tables(self) -> None:
        """Test that init_database creates all tables."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = MagicMock(return_value=mock_context)

        with patch(
            "mcp_server_langgraph.database.session.create_async_engine",
            return_value=mock_engine,
        ):
            await init_database("postgresql+asyncpg://localhost/testdb")

            mock_engine.begin.assert_called_once()
            mock_conn.run_sync.assert_called_once()


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
        mock_engine.dispose = AsyncMock()

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
