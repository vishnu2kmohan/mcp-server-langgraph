"""
Legacy Redirects Tests

Tests for 301 redirects from old routes to new Studio routes.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_legacy_redirects")
class TestLegacyRedirectConfiguration:
    """Tests for redirect configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_redirect_config_includes_build_routes(self) -> None:
        """GIVEN redirect configuration
        WHEN accessing build route mappings
        THEN should include /build/* -> /studio/workflows/*
        """
        from mcp_server_langgraph.api.redirects import REDIRECT_MAPPINGS

        assert "/build" in REDIRECT_MAPPINGS or any("/build" in k for k in REDIRECT_MAPPINGS)

    def test_redirect_config_includes_chat_routes(self) -> None:
        """GIVEN redirect configuration
        WHEN accessing chat route mappings
        THEN should include /chat/* -> /studio/chat/*
        """
        from mcp_server_langgraph.api.redirects import REDIRECT_MAPPINGS

        assert "/chat" in REDIRECT_MAPPINGS or any("/chat" in k for k in REDIRECT_MAPPINGS)

    def test_redirect_config_includes_builder_api_routes(self) -> None:
        """GIVEN redirect configuration
        WHEN accessing builder API route mappings
        THEN should include /builder/* -> /api/v1/workflows/*
        """
        from mcp_server_langgraph.api.redirects import REDIRECT_MAPPINGS

        assert "/builder" in REDIRECT_MAPPINGS or any("/builder" in k for k in REDIRECT_MAPPINGS)

    def test_redirect_config_does_not_include_decommissioned_playground(self) -> None:
        """GIVEN redirect configuration
        WHEN accessing route mappings
        THEN should NOT include /playground (decommissioned)
        """
        from mcp_server_langgraph.api.redirects import REDIRECT_MAPPINGS

        assert "/playground" not in REDIRECT_MAPPINGS and not any("/playground" in k for k in REDIRECT_MAPPINGS)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_legacy_redirects")
class TestRedirectRouteTranslation:
    """Tests for translating old routes to new routes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_translate_build_root_to_studio_workflows(self) -> None:
        """GIVEN /build path
        WHEN translating
        THEN should return /studio/workflows
        """
        from mcp_server_langgraph.api.redirects import translate_legacy_path

        result = translate_legacy_path("/build")
        assert result == "/studio/workflows"

    def test_translate_build_subpath_to_studio_workflows(self) -> None:
        """GIVEN /build/some/path
        WHEN translating
        THEN should return /studio/workflows/some/path
        """
        from mcp_server_langgraph.api.redirects import translate_legacy_path

        result = translate_legacy_path("/build/workflow-123")
        assert result == "/studio/workflows/workflow-123"

    def test_translate_chat_root_to_studio_chat(self) -> None:
        """GIVEN /chat path
        WHEN translating
        THEN should return /studio/chat
        """
        from mcp_server_langgraph.api.redirects import translate_legacy_path

        result = translate_legacy_path("/chat")
        assert result == "/studio/chat"

    def test_translate_chat_session_to_studio_chat(self) -> None:
        """GIVEN /chat/session-123
        WHEN translating
        THEN should return /studio/chat/session-123
        """
        from mcp_server_langgraph.api.redirects import translate_legacy_path

        result = translate_legacy_path("/chat/session-123")
        assert result == "/studio/chat/session-123"

    def test_translate_preserves_query_parameters(self) -> None:
        """GIVEN legacy path with query params
        WHEN translating
        THEN should preserve query parameters
        """
        from mcp_server_langgraph.api.redirects import translate_legacy_path

        result = translate_legacy_path("/build?debug=true")
        assert "?debug=true" in result

    def test_translate_returns_none_for_unknown_path(self) -> None:
        """GIVEN unknown path
        WHEN translating
        THEN should return None
        """
        from mcp_server_langgraph.api.redirects import translate_legacy_path

        result = translate_legacy_path("/unknown/path")
        assert result is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_legacy_redirects")
class TestRedirectMiddleware:
    """Tests for redirect middleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_creates_successfully(self) -> None:
        """GIVEN LegacyRedirectMiddleware
        WHEN instantiated
        THEN should create successfully
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.api.redirects import LegacyRedirectMiddleware

        mock_app = MagicMock()
        middleware = LegacyRedirectMiddleware(mock_app)
        assert middleware is not None

    def test_middleware_uses_301_status_code(self) -> None:
        """GIVEN legacy redirect
        WHEN middleware processes request
        THEN should use 301 Moved Permanently status
        """
        from mcp_server_langgraph.api.redirects import LegacyRedirectMiddleware

        assert LegacyRedirectMiddleware.REDIRECT_STATUS_CODE == 301

    def test_middleware_passes_through_non_legacy_routes(self) -> None:
        """GIVEN non-legacy route
        WHEN middleware processes request
        THEN should pass through to app
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.redirects import LegacyRedirectMiddleware

        mock_app = AsyncMock(return_value=None)
        middleware = LegacyRedirectMiddleware(mock_app)

        # Create mock scope for /studio route
        scope = {"type": "http", "path": "/studio/workflows"}

        # Middleware should pass through
        assert middleware._should_redirect(scope) is False
