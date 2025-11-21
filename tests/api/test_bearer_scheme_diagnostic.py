"""
Diagnostic Test for Bearer Scheme Override Issues

Investigates why bearer_scheme override is not preventing 401 errors in
service principal tests during pytest-xdist execution.

Run with: pytest tests/api/test_bearer_scheme_diagnostic.py -v -s
"""

import gc

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api


@pytest.mark.diagnostic
@pytest.mark.unit
@pytest.mark.xdist_group(name="bearer_scheme_diagnostic_tests")
class TestBearerSchemeOverrideDiagnostic:
    """Diagnostic tests to understand bearer_scheme override behavior."""

    def setup_method(self):
        """Reset state BEFORE test to prevent cross-test pollution"""
        import mcp_server_langgraph.auth.middleware as middleware_module
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        # Reset auth middleware singleton
        middleware_module._global_auth_middleware = None

        # Reset dependency singletons (KeycloakClient, OpenFGAClient, ServicePrincipalManager, etc.)
        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""

        gc.collect()

    def test_bearer_scheme_identity_check(self):
        """
        Diagnostic: Check if imported bearer_scheme matches module bearer_scheme.

        This test helps us understand if the bearer_scheme object being overridden
        is the same object used by get_current_user.
        """
        # Import bearer_scheme from middleware
        # Import the middleware module itself
        from mcp_server_langgraph.auth import middleware
        from mcp_server_langgraph.auth.middleware import bearer_scheme as imported_bearer

        # Check if they're the same object
        print(f"\nImported bearer_scheme id: {id(imported_bearer)}")
        print(f"Module bearer_scheme id: {id(middleware.bearer_scheme)}")
        print(f"Are they the same object? {imported_bearer is middleware.bearer_scheme}")

        assert imported_bearer is middleware.bearer_scheme, (
            "DIAGNOSTIC FAILURE: Imported bearer_scheme is not the same object as module.bearer_scheme!\n"
            "This could explain why overrides don't work."
        )

    def test_bearer_override_with_direct_import(self):
        """
        Diagnostic: Test if overriding imported bearer_scheme works.

        Tests the current pattern used in service principal tests.
        """

        from mcp_server_langgraph.auth.middleware import bearer_scheme, get_current_user

        app = FastAPI()

        # Current pattern: Override imported bearer_scheme
        # CRITICAL: get_current_user is async, so override MUST be async (not lambda)
        async def override_get_current_user():
            return {"user_id": "test-user"}

        app.dependency_overrides[bearer_scheme] = lambda: None
        app.dependency_overrides[get_current_user] = override_get_current_user

        @app.get("/test")
        async def test_endpoint(user=Depends(get_current_user)):
            return {"user": user}

        client = TestClient(app)
        response = client.get("/test")

        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.json() if response.status_code == 200 else response.text}")

        assert response.status_code == 200, (
            f"DIAGNOSTIC FAILURE: Bearer override with direct import didn't work!\n"
            f"Expected 200, got {response.status_code}\n"
            f"This suggests the override pattern is broken."
        )

    def test_bearer_override_with_module_reference(self):
        """
        Diagnostic: Test if overriding via module reference works better.

        Alternative approach: Use module.bearer_scheme instead of imported name.
        """

        from mcp_server_langgraph.auth import middleware

        app = FastAPI()

        # Alternative pattern: Override via module reference
        # CRITICAL: get_current_user is async, so override MUST be async (not lambda)
        async def override_get_current_user():
            return {"user_id": "test-user-2"}

        app.dependency_overrides[middleware.bearer_scheme] = lambda: None
        app.dependency_overrides[middleware.get_current_user] = override_get_current_user

        @app.get("/test2")
        async def test_endpoint(user=Depends(middleware.get_current_user)):
            return {"user": user}

        client = TestClient(app)
        response = client.get("/test2")

        print("\nModule reference approach:")
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json() if response.status_code == 200 else response.text}")

        assert response.status_code == 200, (
            f"DIAGNOSTIC FAILURE: Bearer override with module reference didn't work!\n"
            f"Expected 200, got {response.status_code}"
        )

    def test_get_current_user_override_without_bearer_override(self):
        """
        Diagnostic: Test if we can skip bearer_scheme override entirely.

        If we override get_current_user, do we even need to override bearer_scheme?
        """

        from mcp_server_langgraph.auth.middleware import get_current_user

        app = FastAPI()

        # Try ONLY overriding get_current_user (not bearer_scheme)
        # CRITICAL: get_current_user is async, so override MUST be async (not lambda)
        async def override_get_current_user():
            return {"user_id": "test-user-3"}

        app.dependency_overrides[get_current_user] = override_get_current_user

        @app.get("/test3")
        async def test_endpoint(user=Depends(get_current_user)):
            return {"user": user}

        client = TestClient(app)
        response = client.get("/test3")

        print("\nNo bearer override approach:")
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json() if response.status_code == 200 else response.text}")

        # This might fail with 401, which would tell us bearer_scheme override IS needed
        # Or it might work, which would tell us we can simplify
        if response.status_code == 200:
            print("✓ SUCCESS: get_current_user override alone is sufficient!")
        else:
            print(f"✗ FAILED: Still need bearer_scheme override (got {response.status_code})")

    def test_actual_service_principal_router_with_diagnostic(self):
        """
        Diagnostic: Test actual service principals router with detailed logging.

        This mimics the actual test setup to identify where the override breaks.
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.service_principals import router
        from mcp_server_langgraph.auth.middleware import bearer_scheme, get_current_user
        from mcp_server_langgraph.core.dependencies import (
            get_keycloak_client,
            get_openfga_client,
            get_service_principal_manager,
        )

        # Create fresh app
        app = FastAPI()

        # Create mocks
        from src.mcp_server_langgraph.auth.keycloak import KeycloakClient
        from src.mcp_server_langgraph.auth.openfga import OpenFGAClient
        from src.mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        mock_sp_manager = AsyncMock(spec=ServicePrincipalManager)
        mock_keycloak = AsyncMock(spec=KeycloakClient)
        mock_current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "email": "alice@example.com",
        }
        mock_openfga = AsyncMock(spec=OpenFGAClient)

        # Mock functions matching async/sync
        async def mock_get_current_user_async():
            print(f"  [DEBUG] mock_get_current_user_async called - returning {mock_current_user}")
            return mock_current_user

        def mock_get_keycloak_sync():
            print("  [DEBUG] mock_get_keycloak_sync called")
            return mock_keycloak

        def mock_get_sp_manager_sync():
            print("  [DEBUG] mock_get_sp_manager_sync called")
            return mock_sp_manager

        def mock_get_openfga_sync():
            print("  [DEBUG] mock_get_openfga_sync called")
            return mock_openfga

        # Print bearer_scheme info
        print(f"\n[DEBUG] bearer_scheme object id: {id(bearer_scheme)}")
        print(f"[DEBUG] bearer_scheme type: {type(bearer_scheme)}")

        # Override dependencies
        print("[DEBUG] Setting dependency overrides...")
        app.dependency_overrides[bearer_scheme] = lambda: None
        app.dependency_overrides[get_keycloak_client] = mock_get_keycloak_sync
        app.dependency_overrides[get_service_principal_manager] = mock_get_sp_manager_sync
        app.dependency_overrides[get_current_user] = mock_get_current_user_async
        app.dependency_overrides[get_openfga_client] = mock_get_openfga_sync

        print(f"[DEBUG] Registered overrides: {list(app.dependency_overrides.keys())}")

        # Include router
        print("[DEBUG] Including router...")
        app.include_router(router)

        # Create client and make request
        client = TestClient(app)
        print("[DEBUG] Making POST request to /api/v1/service-principals/...")

        # Mock the manager's create method
        from dataclasses import dataclass
        from datetime import datetime, timezone

        @dataclass
        class MockSP:
            service_id: str = "test-sp"
            name: str = "Test SP"
            description: str = "Test"
            authentication_mode: str = "client_credentials"
            associated_user_id: str = "user:alice"
            owner_user_id: str = "user:alice"
            inherit_permissions: bool = True
            enabled: bool = True
            created_at: str = datetime.now(timezone.utc).isoformat()
            client_secret: str = "sp_secret_test123"

        mock_sp_manager.create_service_principal.return_value = MockSP()

        response = client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Test Service Principal",
                "description": "Diagnostic test",
            },
        )

        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text[:200]}")

        if response.status_code == 401:
            print("\n❌ DIAGNOSTIC FINDING: Getting 401 even with proper overrides!")
            print("   This confirms the bearer_scheme override is not working.")
            print("   Possible causes:")
            print("   1. FastAPI resolves Depends(bearer_scheme) at router import time")
            print("   2. The override is registered after router is already configured")
            print("   3. Bearer_scheme singleton is shared across workers incorrectly")
        elif response.status_code == 201:
            print("\n✓ DIAGNOSTIC SUCCESS: Overrides are working correctly!")
            print("   The issue might be specific to pytest-xdist worker environment.")

        # For diagnostic purposes, we document the finding but don't fail
        # The actual fix will be in the service principal tests


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
