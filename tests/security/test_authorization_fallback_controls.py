"""
Security tests for authorization fallback controls (OpenAI Codex Finding #1)

SECURITY FINDING:
Authorization silently degrades to coarse role checks whenever OpenFGA is unset.
This test suite validates that:
1. Production deployments fail-fast when OpenFGA is not configured and fallback is disabled
2. Tool execution is properly controlled when fallback is disabled
3. Fallback mode requires explicit opt-in via allow_auth_fallback configuration
4. Security warnings are logged when fallback is enabled

References:
- src/mcp_server_langgraph/core/dependencies.py:44-73 (get_openfga_client)
- src/mcp_server_langgraph/auth/middleware.py:242-314 (authorize fallback logic)
- CWE-862: Missing Authorization
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider
from mcp_server_langgraph.core.config import Settings


@pytest.mark.security
@pytest.mark.auth
class TestAuthorizationFallbackControls:
    """Test suite for authorization fallback security controls"""

    @pytest.mark.asyncio
    async def test_tool_execution_blocked_without_openfga_when_fallback_disabled(self):
        """
        SECURITY TEST: Tool execution must be blocked when OpenFGA is unavailable
        and allow_auth_fallback=False (production mode)

        Expected behavior:
        - When OpenFGA client is None and allow_auth_fallback=False
        - Tool execution authorization should DENY access
        - This prevents the blanket "any user/premium role can execute any tool" vulnerability
        """
        # Create middleware without OpenFGA (client=None) and fallback disabled
        settings = Settings(allow_auth_fallback=False)
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=None,  # OpenFGA not configured
            settings=settings,
        )

        # Attempt to authorize tool execution as a regular user
        authorized = await middleware.authorize(user_id="user:alice", relation="executor", resource="tool:code_execution")

        # SECURITY ASSERTION: Must deny access when OpenFGA unavailable and fallback disabled
        assert authorized is False, (
            "SECURITY FAILURE: Tool execution should be denied when OpenFGA is unavailable "
            "and allow_auth_fallback=False, but authorization was granted!"
        )

    @pytest.mark.asyncio
    async def test_tool_execution_allowed_with_fallback_when_explicitly_enabled(self):
        """
        Test that fallback authorization works when explicitly enabled via allow_auth_fallback=True

        This validates that the opt-in mechanism works correctly for development/testing
        environments that explicitly choose to operate with degraded security.
        """
        # Create middleware with fallback explicitly enabled
        settings = Settings(allow_auth_fallback=True)
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=None,  # OpenFGA not configured
            settings=settings,
        )

        # Need to set users_db for fallback to work
        middleware.users_db = {
            "alice": {
                "user_id": "user:alice",
                "email": "alice@example.com",
                "roles": ["user", "premium"],
                "active": True,
            }
        }

        # Attempt to authorize tool execution
        authorized = await middleware.authorize(user_id="user:alice", relation="executor", resource="tool:code_execution")

        # Should be allowed when fallback is explicitly enabled
        assert authorized is True, (
            "Tool execution should be allowed when allow_auth_fallback=True " "and user has appropriate roles"
        )

    @pytest.mark.asyncio
    async def test_fallback_denial_logged_when_openfga_unavailable_and_fallback_disabled(self, caplog):
        """
        Test that authorization denials are properly logged when OpenFGA is unavailable
        and fallback is disabled
        """
        settings = Settings(allow_auth_fallback=False)
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=None,
            settings=settings,
        )

        with caplog.at_level(logging.WARNING):
            authorized = await middleware.authorize(
                user_id="user:alice", relation="executor", resource="tool:sensitive_operation"
            )

        # Check authorization was denied
        assert authorized is False

        # Check that appropriate warning was logged
        assert any(
            "fallback" in record.message.lower() and "disabled" in record.message.lower() for record in caplog.records
        ), "Expected warning about disabled fallback authorization not found in logs"

    @pytest.mark.asyncio
    async def test_fallback_warning_logged_when_enabled(self, caplog):
        """
        Test that a security warning is logged when fallback authorization is enabled

        This helps operators understand they're running with degraded security.
        """
        settings = Settings(allow_auth_fallback=True)
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=None,
            settings=settings,
        )

        middleware.users_db = {
            "alice": {
                "user_id": "user:alice",
                "email": "alice@example.com",
                "roles": ["user"],
                "active": True,
            }
        }

        with caplog.at_level(logging.WARNING):
            await middleware.authorize(user_id="user:alice", relation="executor", resource="tool:test")

        # Should log warning about using fallback authorization
        assert any(
            "fallback authorization" in record.message.lower() for record in caplog.records
        ), "Expected warning about fallback authorization not found in logs"

    @pytest.mark.asyncio
    async def test_admin_users_denied_when_fallback_disabled(self):
        """
        SECURITY TEST: Even admin users should be denied when OpenFGA is unavailable
        and fallback is disabled

        This ensures fail-closed behavior regardless of role.
        """
        settings = Settings(allow_auth_fallback=False)
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=None,
            settings=settings,
        )

        # Admin user should also be denied when fallback disabled
        authorized = await middleware.authorize(user_id="user:admin", relation="executor", resource="tool:admin_operation")

        assert authorized is False, (
            "SECURITY FAILURE: Even admin users must be denied when OpenFGA is unavailable "
            "and allow_auth_fallback=False (fail-closed security)"
        )

    @pytest.mark.asyncio
    async def test_openfga_available_bypasses_fallback_check(self):
        """
        Test that when OpenFGA is available, the fallback configuration is ignored
        and proper authorization is used
        """
        # Mock OpenFGA client that denies access
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = False

        settings = Settings(allow_auth_fallback=True)  # Even with fallback enabled
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=mock_openfga,  # OpenFGA is available
            settings=settings,
        )

        authorized = await middleware.authorize(user_id="user:alice", relation="executor", resource="tool:test")

        # OpenFGA decision should be used (False in this case)
        assert authorized is False

        # Verify OpenFGA was called
        mock_openfga.check_permission.assert_called_once()

    def test_config_defaults_to_fallback_disabled(self):
        """
        SECURITY TEST: Verify that allow_auth_fallback defaults to False (secure by default)

        This ensures production deployments are secure by default unless explicitly opted out.
        """
        settings = Settings()

        assert (
            settings.allow_auth_fallback is False
        ), "SECURITY FAILURE: allow_auth_fallback must default to False for secure-by-default behavior"

    def test_config_fallback_can_be_explicitly_enabled(self):
        """
        Test that allow_auth_fallback can be explicitly enabled for dev/test environments
        """
        settings = Settings(allow_auth_fallback=True)

        assert settings.allow_auth_fallback is True

    @pytest.mark.asyncio
    async def test_production_environment_blocks_fallback_even_when_enabled(self):
        """
        SECURITY TEST: Production environment should block fallback authorization
        even if allow_auth_fallback=True (defense in depth)

        This provides an additional safety layer to prevent accidental production deployment
        with degraded security.
        """
        # Production environment with fallback enabled (misconfiguration)
        # Need to bypass production validation for this test by using different settings
        settings = Settings(
            environment="production",
            allow_auth_fallback=True,  # Should be blocked in production
            auth_provider="keycloak",  # Bypass production validation
            gdpr_storage_backend="postgres",  # Bypass production validation
        )
        user_provider = InMemoryUserProvider(use_password_hashing=False)

        middleware = AuthMiddleware(
            secret_key="test-secret",
            user_provider=user_provider,
            openfga_client=None,
            settings=settings,
        )

        # Should deny access in production even with fallback enabled
        authorized = await middleware.authorize(user_id="user:alice", relation="executor", resource="tool:test")

        assert authorized is False, (
            "SECURITY FAILURE: Production environment must deny fallback authorization "
            "even if allow_auth_fallback=True (defense in depth)"
        )


@pytest.mark.security
@pytest.mark.integration
class TestOpenFGAClientInitialization:
    """Test suite for OpenFGA client initialization and configuration validation"""

    def test_get_openfga_client_returns_none_when_config_incomplete(self):
        """
        Test that get_openfga_client() returns None when OpenFGA config is incomplete

        This validates the current behavior documented in the security finding.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Create settings without OpenFGA configuration
        settings = Settings(
            openfga_store_id=None,  # Missing
            openfga_model_id=None,  # Missing
        )

        # Patch the global settings used by get_openfga_client()
        with patch("mcp_server_langgraph.core.dependencies.settings", settings):
            # Reset the singleton
            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            client = get_openfga_client()

            assert client is None, "get_openfga_client should return None when config is incomplete"

    def test_production_startup_fails_when_openfga_missing_and_fallback_enabled(self):
        """
        SECURITY TEST: Production deployment should fail to start when OpenFGA is not
        configured and allow_auth_fallback=True (misconfiguration)

        This test validates that we reject insecure production configurations.
        """
        from mcp_server_langgraph.core.dependencies import validate_production_auth_config

        settings = Settings(
            environment="production",
            openfga_store_id=None,  # Missing OpenFGA config
            openfga_model_id=None,
            allow_auth_fallback=True,  # Fallback enabled (INSECURE in production)
            auth_provider="keycloak",  # Bypass production validation
            gdpr_storage_backend="postgres",  # Bypass production validation
        )

        # Should raise RuntimeError because fallback is enabled without OpenFGA
        with pytest.raises(RuntimeError, match="OpenFGA.*required.*production|SECURITY ERROR"):
            validate_production_auth_config(settings)

    def test_development_startup_succeeds_when_openfga_missing_and_fallback_enabled(self):
        """
        Test that development environment can start without OpenFGA when fallback is enabled
        """
        from mcp_server_langgraph.core.dependencies import validate_production_auth_config

        settings = Settings(
            environment="development",
            openfga_store_id=None,
            openfga_model_id=None,
            allow_auth_fallback=True,
        )

        # Should not raise in development with fallback enabled
        try:
            validate_production_auth_config(settings)
        except RuntimeError:
            pytest.fail("Development environment should allow missing OpenFGA when fallback enabled")
