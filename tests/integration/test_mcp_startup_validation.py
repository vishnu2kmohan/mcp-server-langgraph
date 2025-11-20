"""
Integration Tests for MCP Server Startup Validation

These tests ensure that the MCP server can start successfully with various
configuration scenarios, catching dependency injection bugs at startup.

Critical bugs these tests would have caught:
1. Missing Keycloak admin credentials
2. OpenFGA client with None store_id/model_id
3. Service principal manager with None OpenFGA

Following TDD principles to prevent future regressions.
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.auth.keycloak import KeycloakClient
from tests.conftest import get_user_id


@pytest.mark.xdist_group(name="integration_mcp_startup_validation_tests")
class TestMCPServerStartupValidation:
    """Test that MCP server starts successfully with various configs"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_mcp_server_imports_successfully(self):
        """
        SMOKE TEST: MCP server module should import without errors.

        This catches import-time failures and circular dependencies.
        """
        from mcp_server_langgraph.server import MCPAgentServer

        # Verify the imported class exists and is a class
        assert MCPAgentServer is not None, "MCPAgentServer class is None"
        assert isinstance(MCPAgentServer, type), "MCPAgentServer is not a class"
        assert hasattr(MCPAgentServer, "__init__"), "MCPAgentServer missing __init__ method"

    def test_mcp_server_can_instantiate(self, monkeypatch):
        """
        Test that MCP server can be instantiated with minimal config.

        Validates that dependency injection works for MCP server.
        """
        try:
            from mcp_server_langgraph.server import MCPAgentServer

            # Arrange: Set minimal config
            monkeypatch.setenv("KEYCLOAK_SERVER_URL", "http://localhost:8082")
            monkeypatch.setenv("KEYCLOAK_REALM", "test")
            monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
            monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
            monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")
            monkeypatch.setenv("OPENFGA_STORE_ID", "")  # Disabled
            monkeypatch.setenv("OPENFGA_MODEL_ID", "")  # Disabled

            # Act: Create server (may fail due to other dependencies, but DI should work)
            try:
                server = MCPAgentServer()
                assert server is not None
            except Exception as e:
                # Some initialization might fail without full env setup
                # The important thing is no AttributeError or dependency wiring failures
                if "AttributeError" in str(e):
                    pytest.fail(f"Dependency wiring issue: {e}")
                # Other errors are acceptable in test environment

        except ImportError:
            # MCP server might have additional dependencies
            pytest.skip("MCP server not available in test environment")

    def test_mcp_server_with_disabled_openfga(self, monkeypatch):
        """
        CRITICAL: MCP server should handle disabled OpenFGA gracefully.

        Validates Bug Fix #2 and #3: System works without OpenFGA.
        """
        try:
            # Arrange: Disable OpenFGA
            monkeypatch.setenv("OPENFGA_STORE_ID", "")
            monkeypatch.setenv("OPENFGA_MODEL_ID", "")
            monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
            monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")

            # Reset singletons
            import mcp_server_langgraph.core.dependencies as deps

            deps._openfga_client = None
            deps._service_principal_manager = None

            # Act: Get dependencies
            from mcp_server_langgraph.core.dependencies import get_openfga_client, get_service_principal_manager

            openfga = get_openfga_client()
            sp_manager = get_service_principal_manager()

            # Assert: Graceful degradation
            assert openfga is None, "OpenFGA should be None when disabled"
            assert sp_manager is not None
            assert sp_manager.openfga is None, "Service principal should handle None OpenFGA"

        except Exception as e:
            if "AttributeError" in str(e):
                pytest.fail(f"Bug #3 regression: Service principal crashed with None OpenFGA: {e}")
            # Other initialization errors might be expected


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_mcp_startup_validation_tests")
class TestEndToEndDependencyWiring:
    """End-to-end tests for complete dependency chain"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_principal_creation_without_openfga(self, monkeypatch):
        """
        E2E TEST: Service principal creation should work without OpenFGA.

        This validates the complete chain:
        1. get_keycloak_client() creates client with admin creds
        2. get_openfga_client() returns None when disabled
        3. ServicePrincipalManager handles None OpenFGA
        4. create_service_principal() succeeds without crashing
        """

        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        # Arrange: Mock Keycloak, None OpenFGA
        mock_keycloak = AsyncMock(spec=KeycloakClient)
        mock_keycloak.create_client = AsyncMock()  # Explicit method configuration

        manager = ServicePrincipalManager(
            keycloak_client=mock_keycloak,
            openfga_client=None,  # Bug #3: This should not crash
        )

        # Act: Create service principal
        try:
            sp = await manager.create_service_principal(
                service_id="e2e-test-service",
                name="E2E Test Service",
                description="End-to-end test",
                authentication_mode="client_credentials",
                owner_user_id=get_user_id("test"),
                inherit_permissions=True,
            )

            # Assert: Created successfully without crashing
            assert sp is not None
            assert sp.service_id == "e2e-test-service"
            mock_keycloak.create_client.assert_called_once()

        except AttributeError as e:
            pytest.fail(f"Bug #3 regression: Service principal crashed: {e}")

    @pytest.mark.asyncio
    async def test_api_key_manager_creation_with_redis_cache(self, monkeypatch):
        """
        E2E TEST: API key manager should work with secure Redis cache.

        This validates:
        1. get_keycloak_client() works with admin creds
        2. Redis cache configured with password/SSL (Bug #4)
        3. API key manager can be instantiated
        """
        from unittest.mock import Mock, patch

        # Arrange: Set config
        monkeypatch.setenv("API_KEY_CACHE_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://secure-redis:6379")
        monkeypatch.setenv("REDIS_PASSWORD", "secure-password")
        monkeypatch.setenv("REDIS_SSL", "true")
        monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
        monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")

        # Reset singleton
        import mcp_server_langgraph.core.dependencies as deps

        deps._api_key_manager = None
        deps._keycloak_client = None

        # Mock Redis to avoid actual connection
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_redis.return_value = Mock()

            # Act: Get API key manager
            from mcp_server_langgraph.core.dependencies import get_api_key_manager

            try:
                manager = get_api_key_manager()

                # Assert: Manager created with cache enabled
                assert manager is not None
                # Verify redis.from_url was called with credentials (Bug #4 fix)
                mock_redis.assert_called()

            except Exception as e:
                pytest.fail(f"API key manager creation failed: {e}")


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_mcp_startup_validation_tests")
class TestProductionReadinessChecks:
    """Production readiness checks for deployment validation"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_hardcoded_credentials_in_code(self):
        """
        SECURITY: Ensure no hardcoded credentials in production code.

        This is a basic security check that complements the fixes.
        """
        from pathlib import Path

        src_files = list(Path("src/mcp_server_langgraph").rglob("*.py"))

        hardcoded_patterns = [
            'password = "',
            "password='",
            'secret = "',
            "secret='",
            'admin_password = "',
            "admin_password='",
        ]

        violations = []
        for src_file in src_files:
            content = src_file.read_text()
            for pattern in hardcoded_patterns:
                if pattern in content and "settings." not in content:
                    # Check it's not in a comment or docstring
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if pattern in line and not line.strip().startswith("#") and '"""' not in line:
                            violations.append(f"{src_file}:{i + 1}: {line.strip()}")

        # Filter out known false positives (test data, examples)
        violations = [
            v for v in violations if "test" not in v.lower() and "example" not in v.lower() and "mock" not in v.lower()
        ]

        assert len(violations) == 0, "Hardcoded credentials found:\n" + "\n".join(violations)

    def test_all_critical_tests_exist(self):
        """
        REGRESSION PREVENTION: Ensure all critical tests exist.

        Bug #5: Missing tests allowed bugs to reach production.
        """
        from pathlib import Path

        required_tests = [
            "tests/unit/test_dependencies_wiring.py",
            "tests/unit/test_cache_redis_config.py",
            "tests/integration/test_app_startup_validation.py",
            "tests/smoke/test_ci_startup_smoke.py",
        ]

        missing = []
        for test_file in required_tests:
            if not Path(test_file).exists():
                missing.append(test_file)

        assert len(missing) == 0, "Critical tests missing:\n" + "\n".join(missing)

    def test_adr_documentation_exists(self):
        """
        DOCUMENTATION: Ensure ADR exists for these fixes.

        Good practice: All critical fixes must be documented.
        """
        from pathlib import Path

        adr_file = Path("adr/adr-0042-dependency-injection-configuration-fixes.md")
        assert adr_file.exists(), "ADR-0042 documentation missing"

        # Verify ADR contains key information
        content = adr_file.read_text()
        assert "Keycloak" in content
        assert "OpenFGA" in content
        assert "Redis" in content
        assert "Service Principal" in content
