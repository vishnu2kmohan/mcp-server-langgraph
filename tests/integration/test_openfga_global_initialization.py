"""
Integration tests for OpenFGA global client initialization.

TDD: These tests verify that set_global_openfga_client() is called during
application lifespan for both app.py and server_streamable.py entry points.

This test was added to catch the bug where WebSocket authorization failed
because get_openfga_client() returned None - the global was never set
during application initialization.

Related files:
- src/mcp_server_langgraph/bootstrap/security.py (app.py path)
- src/mcp_server_langgraph/mcp/server_streamable.py (docker-compose path)
- src/mcp_server_langgraph/websocket/authz.py (uses get_openfga_client)
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="openfga_init")
class TestOpenFGAGlobalInitialization:
    """Tests to verify OpenFGA global client is set during app lifespan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_security_sets_global_openfga_client(self) -> None:
        """
        GIVEN: OpenFGA is configured with store_id
        WHEN: init_auth() is called from bootstrap
        THEN: set_global_openfga_client() is called with the initialized client
        """
        # GIVEN: Mock settings with OpenFGA configured
        mock_settings = MagicMock()
        mock_settings.openfga_store_id = "test-store-id"
        mock_settings.openfga_store_name = None
        mock_settings.openfga_model_id = "test-model-id"
        mock_settings.openfga_api_url = "http://localhost:9080"
        mock_settings.openfga_oidc_client_id = None
        mock_settings.openfga_oidc_client_secret = None
        mock_settings.openfga_oidc_issuer = None
        mock_settings.openfga_preshared_key = None
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.auth_provider = "inmemory"
        mock_settings.keycloak_server_url = "http://localhost/authn"
        mock_settings.keycloak_realm = "default"

        # Mock OpenFGA client
        mock_openfga_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
        mock_openfga_client.store_id = "test-store-id"
        mock_openfga_client.model_id = "test-model-id"
        mock_openfga_client._ensure_initialized = AsyncMock(return_value=None)

        # Patch at the source module where the classes/functions are defined
        with (
            patch(
                "mcp_server_langgraph.auth.openfga.OpenFGAClient",
                return_value=mock_openfga_client,
            ),
            patch("mcp_server_langgraph.auth.openfga.set_global_openfga_client") as mock_set_global,
            patch("mcp_server_langgraph.auth.factory.create_user_provider") as mock_create_provider,
        ):
            mock_create_provider.return_value = MagicMock()

            # WHEN: init_auth is called
            from mcp_server_langgraph.bootstrap.security import init_auth

            await init_auth(mock_settings)

            # THEN: set_global_openfga_client was called
            mock_set_global.assert_called_once_with(mock_openfga_client)

    @pytest.mark.asyncio
    async def test_bootstrap_security_does_not_set_global_when_not_configured(self) -> None:
        """
        GIVEN: OpenFGA is not configured (no store_id or store_name)
        WHEN: init_auth() is called from bootstrap
        THEN: set_global_openfga_client() is NOT called
        """
        # GIVEN: Mock settings without OpenFGA configured
        mock_settings = MagicMock()
        mock_settings.openfga_store_id = None
        mock_settings.openfga_store_name = None
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.auth_provider = "inmemory"

        with (
            patch("mcp_server_langgraph.auth.openfga.set_global_openfga_client") as mock_set_global,
            patch("mcp_server_langgraph.auth.factory.create_user_provider") as mock_create_provider,
        ):
            mock_create_provider.return_value = MagicMock()

            # WHEN: init_auth is called
            from mcp_server_langgraph.bootstrap.security import init_auth

            await init_auth(mock_settings)

            # THEN: set_global_openfga_client was NOT called
            mock_set_global.assert_not_called()

    @pytest.mark.asyncio
    async def test_server_streamable_lifespan_sets_global_openfga_client(self) -> None:
        """
        GIVEN: server_streamable.py is started with OpenFGA configured
        WHEN: The lifespan context manager runs
        THEN: set_global_openfga_client() is called

        This test specifically verifies the docker-compose entry point
        (mcp_server_langgraph.mcp.server_streamable:app) properly initializes
        the global OpenFGA client for WebSocket authorization.
        """
        # GIVEN: Mock the OpenFGA client creation
        mock_openfga_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
        mock_openfga_client.store_id = "test-store-id"
        mock_openfga_client.model_id = "test-model-id"
        mock_openfga_client._ensure_initialized = AsyncMock(return_value=None)
        mock_openfga_client.close = AsyncMock(return_value=None)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openfga_store_id = "test-store-id"
        mock_settings.openfga_store_name = None
        mock_settings.openfga_model_id = "test-model-id"
        mock_settings.openfga_api_url = "http://localhost:9080"
        mock_settings.openfga_oidc_client_id = "test-client"
        mock_settings.openfga_oidc_client_secret = "test-secret"
        mock_settings.openfga_oidc_issuer = None
        mock_settings.openfga_preshared_key = None
        mock_settings.keycloak_server_url = "http://localhost/authn"
        mock_settings.keycloak_realm = "default"
        mock_settings.enable_file_logging = False

        # Patch where the imports are used (server_streamable imports at module level)
        # Also patch function-level imports in lifespan for init_storage, query clients, cleanup
        mock_storage_state = AsyncMock()  # noqa: async-mock-config (configured on next line)
        mock_storage_state.cleanup = AsyncMock(return_value=None)

        with (
            patch("mcp_server_langgraph.mcp.server_streamable.settings", mock_settings),
            patch(
                "mcp_server_langgraph.mcp.server_streamable.OpenFGAClient",
                return_value=mock_openfga_client,
            ),
            patch("mcp_server_langgraph.mcp.server_streamable.set_global_openfga_client") as mock_set_global,
            patch("mcp_server_langgraph.mcp.server_streamable.clear_global_openfga_client") as mock_clear_global,
            patch("mcp_server_langgraph.mcp.server_streamable.get_mcp_server") as mock_get_server,
            patch(
                "mcp_server_langgraph.observability.telemetry.is_initialized",
                return_value=True,
            ),
            patch("mcp_server_langgraph.observability.telemetry.instrument_fastapi_app"),
            patch(
                "mcp_server_langgraph.api.v1.sessions.initialize_session_service",
                new_callable=AsyncMock,
            ),
            patch("mcp_server_langgraph.observability.telemetry.shutdown_observability"),
            # Function-level imports in lifespan that perform real I/O
            patch(
                "mcp_server_langgraph.bootstrap.storage.init_storage",
                new_callable=AsyncMock,
                return_value=mock_storage_state,
            ),
            patch(
                "mcp_server_langgraph.observability.query.factory.init_query_clients",
                new_callable=AsyncMock,
            ),
            patch(
                "mcp_server_langgraph.observability.query.factory.get_tracing_client",
                return_value=MagicMock(),
            ),
            patch(
                "mcp_server_langgraph.observability.query.factory.close_query_clients",
                new_callable=AsyncMock,
            ),
            patch(
                "mcp_server_langgraph.lifecycle.cleanup.cleanup_all_clients",
                new_callable=AsyncMock,
            ),
            patch(
                "mcp_server_langgraph.auth.middleware.set_global_auth_middleware",
            ),
        ):
            mock_get_server.return_value = MagicMock(auth=MagicMock())

            # WHEN: lifespan context is entered and exited
            from mcp_server_langgraph.mcp.server_streamable import lifespan
            from fastapi import FastAPI

            app = FastAPI()
            async with lifespan(app):
                # THEN: set_global_openfga_client was called during startup
                mock_set_global.assert_called_once_with(mock_openfga_client)

            # AND: clear_global_openfga_client was called during shutdown
            mock_clear_global.assert_called_once()


@pytest.mark.xdist_group(name="websocket_authz_global_client")
class TestWebSocketAuthorizationUsesGlobalClient:
    """Tests to verify WebSocket authz middleware uses the global client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_websocket_authz_calls_get_openfga_client(self) -> None:
        """
        GIVEN: WebSocket authorization middleware
        WHEN: authorize_connection() is called
        THEN: It calls get_openfga_client() to get the global client
        """
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
        mock_client.check_permission = AsyncMock(return_value=True)

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ) as mock_get:
            # GIVEN: Authorization middleware
            authz = WebSocketAuthorizationMiddleware(
                resource_type="chat",
                resource_id="notifications",
                required_relation="viewer",
            )

            # WHEN: authorize_connection is called
            result = await authz.authorize_connection("admin")

            # THEN: get_openfga_client was called
            mock_get.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_websocket_authz_fails_when_global_client_is_none(self) -> None:
        """
        GIVEN: get_openfga_client() returns None (global not set)
        WHEN: authorize_connection() is called with fail_closed=True
        THEN: Authorization fails (returns False)

        This is the exact bug that was occurring before the fix.
        """
        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=None,
        ):
            from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

            # GIVEN: Authorization middleware with fail_closed=True (default)
            authz = WebSocketAuthorizationMiddleware(
                resource_type="chat",
                resource_id="notifications",
                required_relation="viewer",
                fail_closed=True,
            )

            # WHEN: authorize_connection is called
            result = await authz.authorize_connection("admin")

            # THEN: Authorization fails because client is None
            assert result is False, (
                "When get_openfga_client() returns None and fail_closed=True, "
                "authorization should fail. This was the bug: the global client "
                "was never set during server_streamable.py lifespan."
            )
