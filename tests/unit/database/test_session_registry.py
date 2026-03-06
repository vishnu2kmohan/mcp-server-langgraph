"""
Tests for PostgreSQL URL-keyed engine registry.

Tests the URL-keyed engine registry pattern which allows multiple database URLs
to be used without collision (e.g., main database vs compliance database).

TDD Phase: RED - Tests written before implementation.
"""

import gc
import threading

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestSessionRegistry:
    """Tests for URL-keyed engine registry in database/session.py."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_engine_same_url_returns_same_engine(self, reset_engine_registry):
        """Same URL should return the same engine instance (singleton per URL)."""
        from mcp_server_langgraph.database import session as session_module

        url = "postgresql+asyncpg://user:pass@localhost/db1"

        engine1 = session_module.get_engine(url)
        engine2 = session_module.get_engine(url)

        assert engine1 is engine2, "Same URL should return same engine"

    def test_get_engine_different_url_returns_different_engine(self, reset_engine_registry):
        """Different URLs should return different engine instances."""
        from mcp_server_langgraph.database import session as session_module

        url1 = "postgresql+asyncpg://user:pass@localhost/db1"
        url2 = "postgresql+asyncpg://user:pass@localhost/db2"

        engine1 = session_module.get_engine(url1)
        engine2 = session_module.get_engine(url2)

        assert engine1 is not engine2, "Different URLs should return different engines"

    @pytest.mark.asyncio
    async def test_dispose_all_engines_clears_registry(self, reset_engine_registry):
        """dispose_all_engines should dispose all engines and clear the registry."""
        from mcp_server_langgraph.database import session as session_module

        url1 = "postgresql+asyncpg://user:pass@localhost/db1"
        url2 = "postgresql+asyncpg://user:pass@localhost/db2"

        # Create engines (we don't use the return values, just registering them)
        session_module.get_engine(url1)
        session_module.get_engine(url2)

        # Verify engines are in registry
        assert len(session_module._engines) == 2

        # Dispose all
        await session_module.dispose_all_engines()

        # Verify registry is empty
        assert len(session_module._engines) == 0
        assert len(session_module._session_makers) == 0

    @pytest.mark.asyncio
    async def test_dispose_all_engines_safe_when_empty(self, reset_engine_registry):
        """dispose_all_engines should be safe to call with empty registry."""
        from mcp_server_langgraph.database import session as session_module

        # Ensure registry is empty
        assert len(session_module._engines) == 0

        # Should not raise
        await session_module.dispose_all_engines()

        # Still empty
        assert len(session_module._engines) == 0

    def test_concurrent_get_engine_creates_single_engine(self, reset_engine_registry):
        """Concurrent calls with same URL should create only one engine (thread safety)."""
        from mcp_server_langgraph.database import session as session_module

        url = "postgresql+asyncpg://user:pass@localhost/concurrent_db"
        engines: list = []
        errors: list = []

        def get_engine_thread():
            try:
                engine = session_module.get_engine(url)
                engines.append(engine)
            except Exception as e:
                errors.append(e)

        # Create multiple threads that call get_engine simultaneously
        threads = [threading.Thread(target=get_engine_thread) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All engines should be the same instance
        assert len(engines) == 10
        first_engine = engines[0]
        for engine in engines[1:]:
            assert engine is first_engine, "All concurrent calls should return same engine"

        # Registry should have only one engine
        assert len(session_module._engines) == 1

    def test_get_session_maker_same_url_returns_same_maker(self, reset_engine_registry):
        """Same URL should return the same session maker instance."""
        from mcp_server_langgraph.database import session as session_module

        url = "postgresql+asyncpg://user:pass@localhost/db1"

        maker1 = session_module.get_session_maker(url)
        maker2 = session_module.get_session_maker(url)

        assert maker1 is maker2, "Same URL should return same session maker"

    def test_get_session_maker_different_url_returns_different_maker(self, reset_engine_registry):
        """Different URLs should return different session maker instances."""
        from mcp_server_langgraph.database import session as session_module

        url1 = "postgresql+asyncpg://user:pass@localhost/db1"
        url2 = "postgresql+asyncpg://user:pass@localhost/db2"

        maker1 = session_module.get_session_maker(url1)
        maker2 = session_module.get_session_maker(url2)

        assert maker1 is not maker2, "Different URLs should return different session makers"


@pytest.fixture
def reset_engine_registry():
    """Reset database engine registry for tests that need isolation.

    USAGE: Only request this fixture in tests that specifically need
    clean engine state. Not autouse to avoid breaking tests that rely
    on long-lived engines.
    """
    from mcp_server_langgraph.database import session as session_module

    # Store original state (used for restoration in cleanup, but not asserted in tests)
    _original_engines = session_module._engines.copy() if hasattr(session_module, "_engines") else {}
    _original_makers = session_module._session_makers.copy() if hasattr(session_module, "_session_makers") else {}

    # Clear before test
    if hasattr(session_module, "_engines"):
        session_module._engines.clear()
    if hasattr(session_module, "_session_makers"):
        session_module._session_makers.clear()
    # Also clear legacy globals if they exist
    if hasattr(session_module, "_engine"):
        session_module._engine = None
    if hasattr(session_module, "_async_session_maker"):
        session_module._async_session_maker = None

    yield

    # Cleanup after test - clear new state
    if hasattr(session_module, "_engines"):
        session_module._engines.clear()
    if hasattr(session_module, "_session_makers"):
        session_module._session_makers.clear()
    if hasattr(session_module, "_engine"):
        session_module._engine = None
    if hasattr(session_module, "_async_session_maker"):
        session_module._async_session_maker = None
