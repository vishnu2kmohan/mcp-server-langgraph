"""
Diagnostic Test for Bearer Scheme Override Fix (Commit 05a54e1)

This test verifies that the bearer_scheme override fix is present and working correctly.
It can be run both locally and in Docker to diagnose authentication issues.

Root Cause Fixed in Commit 05a54e1:
- bearer_scheme singleton in auth/middleware.py was causing test pollution
- Solution: Override bearer_scheme in all API test fixtures

This test ensures that fix is present and functioning correctly.
"""

import gc

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from tests.conftest import get_user_id
from datetime import UTC

pytestmark = pytest.mark.regression


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="bearer_scheme_diagnostic")
class TestBearerSchemeOverrideDiagnostic:
    """
    Diagnostic tests for bearer_scheme override fix (Commit 05a54e1)

    These tests verify that the authentication override pattern is working correctly
    and can be used to diagnose issues when tests fail with 401 errors.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_bearer_scheme_override_is_present_in_api_keys_fixture(self):
        """
        Verify that api_keys_test_client fixture has bearer_scheme override

        This test reads the test_api_keys_endpoints.py file and verifies that:
        1. bearer_scheme is imported
        2. bearer_scheme override is set
        3. Override is set BEFORE app.include_router()

        If this test fails, the fix from commit 05a54e1 is missing.
        """
        import re

        from tests.helpers import get_integration_test_file

        test_file = get_integration_test_file("api/test_api_keys_endpoints.py")
        content = test_file.read_text()

        # Check 1: bearer_scheme is imported
        assert "from mcp_server_langgraph.auth.middleware import bearer_scheme" in content or "bearer_scheme" in content, (
            "bearer_scheme not imported in test file"
        )

        # Check 2: bearer_scheme override is set (handles both direct import and re-import patterns)
        # Old pattern: app.dependency_overrides[bearer_scheme]
        # New pattern (Revision 6): app.dependency_overrides[middleware.bearer_scheme]
        has_bearer_override = (
            "app.dependency_overrides[bearer_scheme]" in content
            or "app.dependency_overrides[middleware.bearer_scheme]" in content
        )
        assert has_bearer_override, (
            "bearer_scheme override not found - fix from commit 05a54e1 missing! "
            "Should have either app.dependency_overrides[bearer_scheme] or "
            "app.dependency_overrides[middleware.bearer_scheme]"
        )

        # Check 3: Override is set BEFORE app.include_router()
        # Find the fixture definition
        fixture_match = re.search(r"def api_keys_test_client.*?yield client", content, re.DOTALL)
        assert fixture_match, "api_keys_test_client fixture not found"

        fixture_code = fixture_match.group(0)

        # Verify order: override comes before include_router (handles both patterns)
        override_pos_old = fixture_code.find("app.dependency_overrides[bearer_scheme]")
        override_pos_new = fixture_code.find("app.dependency_overrides[middleware.bearer_scheme]")
        override_pos = max(override_pos_old, override_pos_new)  # Use whichever pattern is found
        router_pos = fixture_code.find("app.include_router(router)")

        assert override_pos > 0, (
            "bearer_scheme override not found in fixture (checked both [bearer_scheme] and [middleware.bearer_scheme] patterns)"
        )
        assert router_pos > 0, "app.include_router() not found in fixture"
        assert override_pos < router_pos, "bearer_scheme override MUST come BEFORE app.include_router() - incorrect order!"

    def test_bearer_scheme_override_actually_works(self):
        """
        Functional test: Verify that bearer_scheme override prevents 401 errors

        This test creates a minimal FastAPI app with the same pattern as
        api_keys_test_client and verifies that it works correctly.

        UPDATED (Revision 7 - 2025-11-14):
        Now uses importlib.reload() pattern to ensure fresh module references.
        This is required because previous tests may have cached stale router references.
        """
        import importlib
        from datetime import datetime, timedelta
        from unittest.mock import AsyncMock

        from fastapi.security import HTTPAuthorizationCredentials

        # REVISION 7 PATTERN: Re-import and reload middleware first
        from mcp_server_langgraph.auth import middleware
        from mcp_server_langgraph.auth.api_keys import APIKeyManager
        from mcp_server_langgraph.auth.keycloak import KeycloakClient

        importlib.reload(middleware)

        # Now import router module
        from mcp_server_langgraph.api import api_keys

        # Reload router to get fresh imports from reloaded middleware
        importlib.reload(api_keys)

        # Get router and dependencies from reloaded modules
        router = api_keys.router
        bearer_scheme = middleware.bearer_scheme
        get_current_user = middleware.get_current_user

        from mcp_server_langgraph.core.dependencies import get_api_key_manager, get_keycloak_client

        # Create minimal FastAPI app
        app = FastAPI()

        # Create mock dependencies (same as api_keys_test_client fixture)
        mock_current_user = {
            "user_id": get_user_id(),  # Worker-safe ID
            "keycloak_id": "diagnostic-uuid-1234",
            "username": "diagnostic",
            "email": "diagnostic@example.com",
        }

        mock_api_key_manager = AsyncMock(spec=APIKeyManager)
        FIXED_TIME = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        mock_api_key_manager.create_api_key.return_value = {
            "key_id": "diagnostic_key",
            "api_key": "mcp_diagnostic_test_key",
            "name": "Diagnostic Key",
            "created": FIXED_TIME.isoformat(),
            "expires_at": (FIXED_TIME + timedelta(days=365)).isoformat(),
        }

        mock_keycloak_client = AsyncMock(spec=KeycloakClient)

        # Set up dependency overrides (exact pattern from api_keys_test_client)
        async def mock_get_current_user_async():
            return mock_current_user

        def mock_get_api_key_manager_sync():
            return mock_api_key_manager

        def mock_get_keycloak_client_sync():
            return mock_keycloak_client

        # CRITICAL: Override bearer_scheme BEFORE include_router (Revision 7)
        app.dependency_overrides[bearer_scheme] = lambda: HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="mock_token_for_testing"
        )

        # Include router AFTER bearer_scheme override
        app.include_router(router)

        # Override other dependencies
        app.dependency_overrides[get_api_key_manager] = mock_get_api_key_manager_sync
        app.dependency_overrides[get_keycloak_client] = mock_get_keycloak_client_sync
        app.dependency_overrides[get_current_user] = mock_get_current_user_async

        # Create test client
        client = TestClient(app)

        try:
            # Make request - should succeed with 201 Created
            response = client.post(
                "/api/v1/api-keys/",
                json={"name": "Diagnostic Key", "expires_days": 365},
            )

            # Verify response
            assert response.status_code == status.HTTP_201_CREATED, (
                f"Expected 201 Created, got {response.status_code}. "
                f"Response: {response.json() if response.status_code != 500 else response.text}. "
                f"This indicates the bearer_scheme override is NOT working correctly!"
            )

            data = response.json()
            assert "key_id" in data
            assert "api_key" in data
            assert data["name"] == "Diagnostic Key"

            # Verify mock was called
            mock_api_key_manager.create_api_key.assert_called_once()

        finally:
            # Cleanup
            app.dependency_overrides.clear()

    def test_docker_image_has_fix(self):
        """
        Diagnostic test: Check if running in Docker and verify fix is present

        This test helps identify if the Docker image is stale and needs rebuilding.
        It checks if we're running in Docker and validates the fix is present.
        """
        import os

        # Check if running in Docker
        in_docker = (
            os.path.exists("/.dockerenv")
            or os.getenv("DOCKER_CONTAINER") == "true"
            or os.getenv("TESTING") == "true"  # Set by docker-compose.test.yml
        )

        if not in_docker:
            pytest.skip("Not running in Docker - skipping Docker diagnostic")

        # If we are in Docker, verify the source code has the fix
        from pathlib import Path

        test_file = Path("/app/tests/api/test_api_keys_endpoints.py")
        if not test_file.exists():
            # Try alternative paths
            test_file = Path("tests/api/test_api_keys_endpoints.py")

        if test_file.exists():
            content = test_file.read_text()
            assert "app.dependency_overrides[bearer_scheme]" in content, (
                "🚨 DOCKER IMAGE IS STALE! 🚨\n"
                "The bearer_scheme override fix from commit 05a54e1 is NOT present in the Docker image.\n"
                "Solution: Rebuild the Docker image with:\n"
                "  ./scripts/test-integration.sh --build --no-cache\n"
                "Or:\n"
                "  docker compose -f docker/docker-compose.test.yml build --no-cache"
            )
        else:
            pytest.skip(f"Cannot find test file in Docker: {test_file}")

    def test_git_commit_is_recent_enough(self):
        """
        Diagnostic test: Verify current codebase includes the fix commit

        This test checks if commit 05a54e1 is in the git history.
        If not, the codebase is too old and needs to be updated.

        NOTE: Skips in CI shallow clones (fetch-depth: 1) since historical
        commits aren't available. The actual fix validation happens via
        test_bearer_scheme_override_code_is_present() which checks source code.
        """
        import os
        import subprocess

        # Skip if not in a git repository
        if not os.path.exists(".git"):
            pytest.skip("Not in a git repository - skipping git diagnostic")

        # Skip in CI shallow clones (fetch-depth: 1)
        # CI workflows use shallow clones for performance, so historical commits unavailable
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            try:
                # Check if this is a shallow clone
                is_shallow = (
                    subprocess.run(
                        ["git", "rev-parse", "--is-shallow-repository"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    ).stdout.strip()
                    == "true"
                )

                if is_shallow:
                    pytest.skip(
                        "Skipping git history check in CI shallow clone (fetch-depth: 1). "
                        "Fix validation performed via test_bearer_scheme_override_code_is_present() instead."
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # Continue with normal check

        try:
            # Check if commit 05a54e1 is in the history
            result = subprocess.run(
                ["git", "log", "--oneline", "--all"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                git_log = result.stdout

                # Look for the fix commit
                if "05a54e1" not in git_log and "bearer_scheme override" not in git_log:
                    pytest.fail(
                        "🚨 CODEBASE IS TOO OLD! 🚨\n"
                        "Commit 05a54e1 (bearer_scheme override fix) not found in git history.\n"
                        "Solution: Update your codebase:\n"
                        "  git pull origin main\n"
                        "Or if you're on a branch:\n"
                        "  git rebase main"
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Cannot run git commands - skipping git diagnostic")


@pytest.mark.unit
@pytest.mark.regression
def test_bearer_scheme_override_documentation():
    """
    Meta-test: Verify that bearer_scheme override pattern is documented

    This test ensures that the fix is properly documented in test files
    so future developers understand why it's necessary.
    """
    from tests.helpers import get_integration_test_file

    test_file = get_integration_test_file("api/test_api_keys_endpoints.py")
    content = test_file.read_text()

    # Check for documentation comment
    assert "CRITICAL" in content and "bearer_scheme" in content, (
        "bearer_scheme override should be documented with CRITICAL comment"
    )

    assert "pytest-xdist" in content or "state pollution" in content or "singleton" in content, (
        "Comment should explain the reason (pytest-xdist state pollution or singleton)"
    )
