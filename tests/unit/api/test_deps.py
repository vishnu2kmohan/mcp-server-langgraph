"""
Tests for consolidated FastAPI dependency providers.

TDD: These tests define the expected behavior for api/deps.py
which consolidates all Depends() providers using request-state pattern.
"""

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_module_imports")
class TestDepsModuleImports:
    """Test that all dependency providers can be imported."""

    def test_import_get_settings(self):
        """get_settings should be importable."""
        from mcp_server_langgraph.api.deps import get_settings

        assert callable(get_settings)

    def test_import_get_openfga_client(self):
        """get_openfga_client should be importable."""
        from mcp_server_langgraph.api.deps import get_openfga_client

        assert callable(get_openfga_client)

    def test_import_get_http_client(self):
        """get_http_client should be importable."""
        from mcp_server_langgraph.api.deps import get_http_client

        assert callable(get_http_client)

    def test_import_get_db_session(self):
        """get_db_session should be importable."""
        from mcp_server_langgraph.api.deps import get_db_session

        assert callable(get_db_session)

    def test_import_get_audit_service(self):
        """get_audit_service should be importable."""
        from mcp_server_langgraph.api.deps import get_audit_service

        assert callable(get_audit_service)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_get_settings")
class TestGetSettings:
    """Test get_settings dependency provider."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_settings_instance(self):
        """get_settings should return a Settings instance."""
        from mcp_server_langgraph.api.deps import get_settings
        from mcp_server_langgraph.core.config import Settings

        result = get_settings()
        assert isinstance(result, Settings)

    def test_get_settings_is_cached_returns_same_instance(self):
        """get_settings should return the same instance (lru_cache)."""
        from mcp_server_langgraph.api.deps import get_settings

        # Clear cache to ensure clean state
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_openfga_client")
class TestGetOpenfgaClient:
    """Test get_openfga_client from request state."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_client_from_state(self):
        """Should return OpenFGA client from request.app.state."""
        from mcp_server_langgraph.api.deps import get_openfga_client

        mock_client = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.openfga_client = mock_client

        result = get_openfga_client(mock_request)
        assert result is mock_client

    def test_returns_none_when_not_configured(self):
        """Should return None when openfga_client not in state."""
        from mcp_server_langgraph.api.deps import get_openfga_client

        mock_request = MagicMock(spec=Request)
        # Simulate missing attribute
        del mock_request.app.state.openfga_client

        result = get_openfga_client(mock_request)
        assert result is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_http_client")
class TestGetHttpClient:
    """Test get_http_client from request state."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_client_from_manager(self):
        """Should return httpx client from http_client_manager."""
        from mcp_server_langgraph.api.deps import get_http_client

        mock_client = MagicMock()
        mock_manager = AsyncMock()  # async-mock-configured (return_value set below)
        mock_manager.get_client.return_value = mock_client

        mock_request = MagicMock(spec=Request)
        mock_request.app.state.http_client_manager = mock_manager

        result = await get_http_client(mock_request)
        assert result is mock_client
        mock_manager.get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_not_initialized(self):
        """Should raise RuntimeError when http_client_manager not initialized."""
        from mcp_server_langgraph.api.deps import get_http_client

        mock_request = MagicMock(spec=Request)
        mock_request.app.state.http_client_manager = None

        with pytest.raises(RuntimeError, match="HTTP client manager not initialized"):
            await get_http_client(mock_request)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_audit_service")
class TestGetAuditService:
    """Test get_audit_service from request state."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_service_from_state(self):
        """Should return audit service from request.app.state."""
        from mcp_server_langgraph.api.deps import get_audit_service

        mock_service = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.audit_service = mock_service

        result = get_audit_service(mock_request)
        assert result is mock_service

    def test_returns_none_when_not_configured(self):
        """Should return None when audit_service not in state."""
        from mcp_server_langgraph.api.deps import get_audit_service

        mock_request = MagicMock(spec=Request)
        # Simulate missing attribute
        del mock_request.app.state.audit_service

        result = get_audit_service(mock_request)
        assert result is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_db_session")
class TestGetDbSession:
    """Test get_db_session generator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_yields_session(self):
        """Should yield an AsyncSession."""
        from mcp_server_langgraph.api.deps import get_db_session

        # This test will be expanded when we have proper DB fixtures
        # For now, test that it's a generator function
        import inspect

        assert inspect.isasyncgenfunction(get_db_session)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_deps_cache_management")
class TestDepsCacheManagement:
    """Test cache clearing for clean test isolation."""

    def test_clear_deps_cache_clears_settings(self):
        """clear_deps_cache should reset settings cache."""
        from mcp_server_langgraph.api.deps import get_settings, clear_deps_cache

        # Ensure cache is populated
        get_settings()
        assert get_settings.cache_info().currsize > 0

        # Clear cache
        clear_deps_cache()

        # Cache should be empty
        assert get_settings.cache_info().currsize == 0
