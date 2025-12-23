"""
Unit tests for singleton dependency functions in core/dependencies.py

Tests the get_token_validator() and related singleton pattern functions.

Following TDD best practices (RED-GREEN-REFACTOR):
1. RED: These tests define expected behavior
2. GREEN: Implementation must make these pass
3. REFACTOR: Improve quality while keeping tests green
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

# Mark as unit test for CI filtering
pytestmark = pytest.mark.unit


# ============================================================================
# GET_TOKEN_VALIDATOR TESTS
# ============================================================================


@pytest.mark.xdist_group(name="test_dependencies_singletons")
class TestGetTokenValidator:
    """Tests for get_token_validator() singleton function."""

    def teardown_method(self):
        """Force GC and reset singleton for test isolation."""
        import mcp_server_langgraph.core.dependencies as deps

        # Reset the singleton for test isolation
        deps._token_validator = None
        gc.collect()

    def test_returns_none_when_auth_provider_not_keycloak(self):
        """Should return None when auth_provider is not 'keycloak'."""
        # GIVEN: auth_provider is set to something other than keycloak
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.auth_provider = "jwt"

            # Reset singleton to force re-evaluation
            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called
            result = deps.get_token_validator()

            # THEN: Should return None
            assert result is None

    def test_returns_none_when_auth_provider_is_none_provider(self):
        """Should return None when auth_provider is 'none'."""
        # GIVEN: auth_provider is 'none' (disabled auth)
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.auth_provider = "none"

            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called
            result = deps.get_token_validator()

            # THEN: Should return None
            assert result is None

    def test_returns_token_validator_when_auth_provider_is_keycloak(self):
        """Should return TokenValidator instance when auth_provider is 'keycloak'."""
        # GIVEN: auth_provider is keycloak with valid config
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.TokenValidator") as MockValidator,
        ):
            mock_settings.auth_provider = "keycloak"
            mock_settings.keycloak_server_url = "http://keycloak:8080"
            mock_settings.keycloak_public_url = "http://keycloak:8080"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_admin_realm = "master"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = "test-secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin"

            mock_validator_instance = MagicMock()
            MockValidator.return_value = mock_validator_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called
            result = deps.get_token_validator()

            # THEN: Should return TokenValidator instance
            assert result is mock_validator_instance
            MockValidator.assert_called_once()

    def test_auth_provider_check_is_case_insensitive(self):
        """Should accept 'Keycloak', 'KEYCLOAK', 'keycloak' etc."""
        # GIVEN: auth_provider is 'KEYCLOAK' (uppercase)
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.TokenValidator") as MockValidator,
        ):
            mock_settings.auth_provider = "KEYCLOAK"  # uppercase
            mock_settings.keycloak_server_url = "http://keycloak:8080"
            mock_settings.keycloak_public_url = "http://keycloak:8080"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_admin_realm = "master"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = "test-secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin"

            mock_validator_instance = MagicMock()
            MockValidator.return_value = mock_validator_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called
            result = deps.get_token_validator()

            # THEN: Should return TokenValidator (case-insensitive match)
            assert result is mock_validator_instance

    def test_singleton_returns_cached_instance(self):
        """Should return same instance on subsequent calls (singleton pattern)."""
        # GIVEN: auth_provider is keycloak
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.TokenValidator") as MockValidator,
        ):
            mock_settings.auth_provider = "keycloak"
            mock_settings.keycloak_server_url = "http://keycloak:8080"
            mock_settings.keycloak_public_url = "http://keycloak:8080"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_admin_realm = "master"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = "test-secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin"

            mock_validator_instance = MagicMock()
            MockValidator.return_value = mock_validator_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called multiple times
            result1 = deps.get_token_validator()
            result2 = deps.get_token_validator()
            result3 = deps.get_token_validator()

            # THEN: All results should be the same instance
            assert result1 is result2
            assert result2 is result3
            # TokenValidator should only be constructed once
            assert MockValidator.call_count == 1

    def test_logs_debug_when_not_keycloak(self):
        """Should log debug message when auth_provider is not keycloak."""
        # GIVEN: auth_provider is not keycloak
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.logger") as mock_logger,
        ):
            mock_settings.auth_provider = "jwt"

            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called
            deps.get_token_validator()

            # THEN: Should log debug message
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "jwt" in call_args
            assert "keycloak" in call_args.lower()

    def test_logs_info_when_validator_created(self):
        """Should log info message when TokenValidator is created."""
        # GIVEN: auth_provider is keycloak
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.TokenValidator") as MockValidator,
            patch("mcp_server_langgraph.core.dependencies.logger") as mock_logger,
        ):
            mock_settings.auth_provider = "keycloak"
            mock_settings.keycloak_server_url = "http://keycloak:8080"
            mock_settings.keycloak_public_url = "http://keycloak:8080"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_admin_realm = "master"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = "test-secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin"

            MockValidator.return_value = MagicMock()

            import mcp_server_langgraph.core.dependencies as deps

            deps._token_validator = None

            # WHEN: get_token_validator is called
            deps.get_token_validator()

            # THEN: Should log info message about initialization
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "TokenValidator" in call_args


# ============================================================================
# GET_OPENFGA_CLIENT TESTS
# ============================================================================


@pytest.mark.xdist_group(name="test_dependencies_singletons")
class TestGetOpenfgaClient:
    """Tests for get_openfga_client() singleton function."""

    def teardown_method(self):
        """Force GC and reset singleton for test isolation."""
        import mcp_server_langgraph.core.dependencies as deps

        # Reset the singleton for test isolation
        deps._openfga_client = None
        gc.collect()

    def test_returns_none_when_no_store_config(self):
        """Should return None when neither store_id nor store_name is set."""
        # GIVEN: No store configuration
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_store_id = None
            mock_settings.openfga_store_name = None

            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            # WHEN: get_openfga_client is called
            result = deps.get_openfga_client()

            # THEN: Should return None
            assert result is None

    def test_returns_client_when_store_id_is_set(self):
        """Should return OpenFGAClient when store_id is configured."""
        # GIVEN: store_id is set
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.OpenFGAClient") as MockClient,
        ):
            mock_settings.openfga_store_id = "test-store-id"
            mock_settings.openfga_store_name = None
            mock_settings.openfga_api_url = "http://openfga:8080"
            mock_settings.openfga_model_id = None
            mock_settings.openfga_oidc_client_id = None
            mock_settings.openfga_oidc_client_secret = None
            mock_settings.openfga_oidc_issuer = None
            mock_settings.openfga_preshared_key = None

            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            # WHEN: get_openfga_client is called
            result = deps.get_openfga_client()

            # THEN: Should return OpenFGAClient instance
            assert result is mock_client_instance
            MockClient.assert_called_once()

    def test_returns_client_when_store_name_is_set(self):
        """Should return OpenFGAClient when store_name is configured (dynamic lookup)."""
        # GIVEN: store_name is set (enables dynamic lookup)
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.OpenFGAClient") as MockClient,
        ):
            mock_settings.openfga_store_id = None
            mock_settings.openfga_store_name = "test-store"
            mock_settings.openfga_api_url = "http://openfga:8080"
            mock_settings.openfga_model_id = None
            mock_settings.openfga_oidc_client_id = None
            mock_settings.openfga_oidc_client_secret = None
            mock_settings.openfga_oidc_issuer = None
            mock_settings.openfga_preshared_key = None

            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            # WHEN: get_openfga_client is called
            result = deps.get_openfga_client()

            # THEN: Should return OpenFGAClient instance
            assert result is mock_client_instance
            MockClient.assert_called_once()

    def test_singleton_returns_cached_instance(self):
        """Should return same instance on subsequent calls (singleton pattern)."""
        # GIVEN: Valid store configuration
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.OpenFGAClient") as MockClient,
        ):
            mock_settings.openfga_store_id = "test-store-id"
            mock_settings.openfga_store_name = None
            mock_settings.openfga_api_url = "http://openfga:8080"
            mock_settings.openfga_model_id = None
            mock_settings.openfga_oidc_client_id = None
            mock_settings.openfga_oidc_client_secret = None
            mock_settings.openfga_oidc_issuer = None
            mock_settings.openfga_preshared_key = None

            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            # WHEN: get_openfga_client is called multiple times
            result1 = deps.get_openfga_client()
            result2 = deps.get_openfga_client()
            result3 = deps.get_openfga_client()

            # THEN: All results should be the same instance
            assert result1 is result2
            assert result2 is result3
            # OpenFGAClient should only be constructed once
            assert MockClient.call_count == 1

    def test_logs_warning_when_no_store_config(self):
        """Should log warning when no store configuration."""
        # GIVEN: No store configuration
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_store_id = None
            mock_settings.openfga_store_name = None

            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            # Patch logger inside the function scope
            with patch("mcp_server_langgraph.observability.telemetry.logger") as mock_logger:
                # WHEN: get_openfga_client is called
                deps.get_openfga_client()

                # THEN: Should log warning about incomplete config
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args[0][0]
                assert "OpenFGA configuration incomplete" in call_args

    def test_constructs_oidc_issuer_from_keycloak_settings(self):
        """Should construct OIDC issuer URL from Keycloak settings when not explicit."""
        # GIVEN: OIDC client credentials but no explicit issuer
        with (
            patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings,
            patch("mcp_server_langgraph.core.dependencies.OpenFGAClient") as MockClient,
        ):
            mock_settings.openfga_store_id = "test-store-id"
            mock_settings.openfga_store_name = None
            mock_settings.openfga_api_url = "http://openfga:8080"
            mock_settings.openfga_model_id = None
            mock_settings.openfga_oidc_client_id = "openfga-client"
            mock_settings.openfga_oidc_client_secret = "secret"
            mock_settings.openfga_oidc_issuer = None  # Not set, should be constructed
            mock_settings.openfga_preshared_key = None
            mock_settings.keycloak_server_url = "http://keycloak:8080"
            mock_settings.keycloak_realm = "test-realm"

            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None

            # WHEN: get_openfga_client is called
            deps.get_openfga_client()

            # THEN: OIDC issuer should be constructed from Keycloak settings
            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args
            config = call_kwargs.kwargs.get("config") or call_kwargs.args[0]
            expected_issuer = "http://keycloak:8080/realms/test-realm"
            assert config.oidc_issuer == expected_issuer


# ============================================================================
# GET_MCP_CLIENT TESTS
# ============================================================================


@pytest.mark.xdist_group(name="test_dependencies_singletons")
class TestGetMcpClient:
    """Tests for get_mcp_client() singleton function."""

    def teardown_method(self):
        """Force GC and reset singleton for test isolation."""
        import mcp_server_langgraph.core.dependencies as deps

        # Reset the singleton for test isolation
        deps._mcp_client = None
        gc.collect()

    def test_returns_mcp_client_instance(self):
        """Should return MCPClient instance."""
        # GIVEN: Default state
        with patch("mcp_server_langgraph.core.dependencies.MCPClient") as MockClient:
            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._mcp_client = None

            # WHEN: get_mcp_client is called
            result = deps.get_mcp_client()

            # THEN: Should return MCPClient instance
            assert result is mock_client_instance
            MockClient.assert_called_once()

    def test_singleton_returns_cached_instance(self):
        """Should return same instance on subsequent calls (singleton pattern)."""
        # GIVEN: Default state
        with patch("mcp_server_langgraph.core.dependencies.MCPClient") as MockClient:
            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._mcp_client = None

            # WHEN: get_mcp_client is called multiple times
            result1 = deps.get_mcp_client()
            result2 = deps.get_mcp_client()
            result3 = deps.get_mcp_client()

            # THEN: All results should be the same instance
            assert result1 is result2
            assert result2 is result3
            # MCPClient should only be constructed once
            assert MockClient.call_count == 1


# ============================================================================
# GET_OAUTH2_SERVICE TESTS
# ============================================================================


@pytest.mark.xdist_group(name="test_dependencies_singletons")
class TestGetOauth2Service:
    """Tests for get_oauth2_service() singleton function."""

    def teardown_method(self):
        """Force GC and reset singleton for test isolation."""
        import mcp_server_langgraph.core.dependencies as deps

        # Reset the singleton for test isolation
        deps._oauth2_service = None
        gc.collect()

    def test_returns_oauth2_service_instance(self):
        """Should return OAuth2Service instance."""
        # GIVEN: Default state
        with patch("mcp_server_langgraph.core.dependencies.OAuth2Service") as MockService:
            mock_service_instance = MagicMock()
            MockService.return_value = mock_service_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._oauth2_service = None

            # WHEN: get_oauth2_service is called
            result = deps.get_oauth2_service()

            # THEN: Should return OAuth2Service instance
            assert result is mock_service_instance
            MockService.assert_called_once()

    def test_singleton_returns_cached_instance(self):
        """Should return same instance on subsequent calls (singleton pattern)."""
        # GIVEN: Default state
        with patch("mcp_server_langgraph.core.dependencies.OAuth2Service") as MockService:
            mock_service_instance = MagicMock()
            MockService.return_value = mock_service_instance

            import mcp_server_langgraph.core.dependencies as deps

            deps._oauth2_service = None

            # WHEN: get_oauth2_service is called multiple times
            result1 = deps.get_oauth2_service()
            result2 = deps.get_oauth2_service()
            result3 = deps.get_oauth2_service()

            # THEN: All results should be the same instance
            assert result1 is result2
            assert result2 is result3
            # OAuth2Service should only be constructed once
            assert MockService.call_count == 1
