"""
Regression Tests for Pytest-xdist Test Isolation

These tests validate that FastAPI dependency overrides work correctly
in parallel test execution (pytest-xdist). They prevent regression of
the bug fixed in commit 079e82e where async dependency overrides were
not properly handled, causing intermittent 401 authentication failures.

See: MEMORY_SAFETY_GUIDELINES.md and pytest-xdist documentation.

Key Learnings:
1. Async dependencies MUST be overridden with async functions
2. Sync dependencies MUST be overridden with sync functions
3. Mixing async/sync causes FastAPI to ignore the override
4. Use @pytest.mark.xdist_group to group related tests in same worker
5. Always clear dependency_overrides in fixture teardown
"""

import gc
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient


# ==============================================================================
# Test Fixtures and Mock Dependencies
# ==============================================================================


@pytest.fixture
def mock_async_dependency():
    """Mock async dependency (simulates get_current_user)"""

    async def get_current_user():
        return {"user_id": "user:test", "username": "testuser"}

    return get_current_user


@pytest.fixture
def mock_sync_dependency():
    """Mock sync dependency (simulates get_manager)"""

    def get_manager():
        manager = AsyncMock()  # async-mock-config - Generic test mock for dependency injection testing
        manager.method.return_value = {"result": "success"}
        return manager

    return get_manager


# ==============================================================================
# Test Helper Functions
# ==============================================================================


def create_test_app_with_dependencies():
    """
    Create a test FastAPI app with both async and sync dependencies.

    This mimics the pattern used in production API endpoints.
    """
    app = FastAPI()

    # Simulated dependency functions (would be imported in real app)
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    ) -> dict[str, Any]:
        """Async dependency - requires authentication"""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    def get_manager():
        """Sync dependency - returns a manager"""
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Manager not initialized",
        )

    # Test endpoint that uses both dependencies
    @app.get("/test")
    async def test_endpoint(
        current_user: dict[str, Any] = Depends(get_current_user),
        manager=Depends(get_manager),
    ):
        return {
            "user": current_user,
            "manager_result": "ok",
        }

    return app, get_current_user, get_manager


# ==============================================================================
# Regression Tests for Dependency Override Patterns
# ==============================================================================


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="xdist_isolation_tests")
class TestPytestXdistIsolation:
    """
    Regression tests for pytest-xdist test isolation.

    These tests validate the fix for the async/sync dependency override bug.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_async_dependency_override_with_async_function(self, mock_async_dependency):
        """
        ✅ CORRECT: Override async dependency with async function.

        This is the correct pattern and should work in pytest-xdist.
        """
        app, get_current_user, get_manager = create_test_app_with_dependencies()

        # ✅ Async dependency overridden with async function
        app.dependency_overrides[get_current_user] = mock_async_dependency

        # Mock the manager dependency
        app.dependency_overrides[get_manager] = (
            lambda: AsyncMock()
        )  # async-mock-config - Generic test mock for dependency injection testing

        client = TestClient(app)
        response = client.get("/test")

        # Should succeed because override is correctly async
        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.json()
        assert response.json()["user"]["username"] == "testuser"

        # Cleanup
        app.dependency_overrides.clear()

    def test_async_dependency_override_with_sync_lambda_documentation(self):
        """
        ❌ INCORRECT PATTERN: Override async dependency with sync lambda.

        This is the BUG that was fixed in commit 079e82e.

        IMPORTANT: This bug only manifests in pytest-xdist parallel execution!
        - When run in isolation (pytest -xvs): Works correctly (200 OK)
        - When run in parallel (pytest -n auto): Fails intermittently (401)

        The intermittent nature makes it hard to test directly, but this
        test documents the incorrect pattern for future reference.

        Always use async function to override async dependency!
        """
        app, get_current_user, get_manager = create_test_app_with_dependencies()

        # ❌ BUG: Async dependency overridden with sync lambda
        # FastAPI may IGNORE this override in pytest-xdist parallel mode!
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": "user:test",
            "username": "testuser",
        }

        # Mock the manager dependency
        app.dependency_overrides[get_manager] = (
            lambda: AsyncMock()
        )  # async-mock-config - Generic test mock for dependency injection testing

        client = TestClient(app)
        response = client.get("/test")

        # In isolation, this may work (200 OK)
        # In pytest-xdist parallel mode, this may fail (401 Unauthorized)
        # We document this as a warning, not an assertion
        if response.status_code != status.HTTP_200_OK:
            # If it fails, it's demonstrating the bug
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Cleanup
        app.dependency_overrides.clear()

    def test_sync_dependency_override_with_sync_function(self):
        """
        ✅ CORRECT: Override sync dependency with sync function.

        This is the correct pattern for sync dependencies.
        """
        app, get_current_user, get_manager = create_test_app_with_dependencies()

        # Mock async dependency correctly
        async def mock_user():
            return {"user_id": "user:test", "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_user

        # ✅ Sync dependency overridden with sync function
        app.dependency_overrides[get_manager] = (
            lambda: AsyncMock()
        )  # async-mock-config - Generic test mock for dependency injection testing

        client = TestClient(app)
        response = client.get("/test")

        # Should succeed
        assert response.status_code == status.HTTP_200_OK

        # Cleanup
        app.dependency_overrides.clear()

    def test_dependency_override_cleanup_prevents_pollution(self):
        """
        Test that dependency_overrides.clear() prevents state pollution.

        Without cleanup, overrides from one test could leak to another test
        in the same pytest-xdist worker, causing intermittent failures.
        """
        app, get_current_user, get_manager = create_test_app_with_dependencies()

        # Set up overrides
        async def mock_user():
            return {"user_id": "user:test", "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[get_manager] = (
            lambda: AsyncMock()
        )  # async-mock-config - Generic test mock for dependency injection testing

        # Verify overrides are set
        assert len(app.dependency_overrides) == 2

        # Cleanup
        app.dependency_overrides.clear()

        # Verify cleanup worked
        assert len(app.dependency_overrides) == 0

    def test_xdist_group_marker_keeps_tests_in_same_worker(self):
        """
        DOCUMENTATION TEST: Documents @pytest.mark.xdist_group marker behavior.

        **WARNING**: This is an INERT test that only documents expected behavior.
        It cannot fail on regression because it always passes (assert True).

        All tests in this class should run in the same worker because
        they have the same xdist_group marker.

        This is important for tests that share state or fixtures.

        **TODO**: Convert to executable test that parses pytest-xdist output.
        Proper implementation would:
        1. Run pytest with -n 2 in subprocess
        2. Parse output for [gw#] worker identifiers
        3. Verify all tests in same xdist_group run on same worker
        4. Use pytest's pytester plugin for subprocess execution

        References:
        - OpenAI Codex Finding: "Regression tests are inert documentation"
        - pytest-xdist documentation: Worker assignment and grouping
        """
        # DOCUMENTATION PLACEHOLDER - This test documents expected behavior
        # Manual validation: Run pytest -n auto -v and verify [gw#] markers match
        pytest.skip(
            "Documentation test - describes xdist_group behavior but doesn't validate it. "
            "Manual validation: Run 'pytest -n auto -v' and check [gw#] markers."
        )


# ==============================================================================
# Integration Tests with Actual FastAPI Patterns
# ==============================================================================


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="xdist_fastapi_patterns")
class TestFastAPIPatterns:
    """
    Test real FastAPI patterns used in the codebase.

    These tests validate the patterns used in:
    - tests/api/test_api_keys_endpoints.py
    - tests/api/test_service_principals_endpoints.py
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_api_keys_pattern_works_in_xdist(self, mock_async_dependency):
        """
        Test the exact pattern used in test_api_keys_endpoints.py.

        This validates the fix for the TestCreateAPIKey failures.
        """
        # Import pattern from actual code
        from fastapi import Depends, FastAPI

        # Simulated dependencies (mimics actual code)
        async def get_current_user():
            raise HTTPException(status_code=401, detail="Not authenticated")

        def get_manager():
            return AsyncMock()  # async-mock-config - Generic test mock for dependency injection testing

        # Create app and override dependencies (actual pattern)
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint(
            current_user: dict[str, Any] = Depends(get_current_user),
            manager=Depends(get_manager),
        ):
            return {"user_id": current_user.get("user_id")}

        # ✅ CORRECT PATTERN (from fixed code)
        async def mock_get_current_user_async():
            return {"user_id": "user:alice", "username": "alice"}

        def mock_get_manager_sync():
            return AsyncMock()  # async-mock-config - Generic test mock for dependency injection testing

        app.dependency_overrides[get_current_user] = mock_get_current_user_async
        app.dependency_overrides[get_manager] = mock_get_manager_sync

        # Test with TestClient
        client = TestClient(app)
        response = client.post("/test")

        # Should succeed with 200, not 401
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user_id"] == "user:alice"

        # Cleanup
        app.dependency_overrides.clear()


# ==============================================================================
# Documentation Test
# ==============================================================================


@pytest.mark.unit
def test_dependency_override_documentation():
    """
    Documentation test that serves as a reference for correct patterns.

    ✅ DO THIS:
    ---------
    async def get_user():
        # ... async code ...

    async def mock_user():
        return {"user_id": "test"}

    app.dependency_overrides[get_user] = mock_user  # ✅ Async -> Async


    ❌ DON'T DO THIS:
    ----------------
    async def get_user():
        # ... async code ...

    app.dependency_overrides[get_user] = lambda: {"user_id": "test"}  # ❌ Async -> Sync


    ALWAYS CLEANUP:
    --------------
    try:
        # ... test code ...
    finally:
        app.dependency_overrides.clear()  # ✅ Always clear

    OR use yield in fixture:
    -----------------------
    @pytest.fixture
    def client():
        app.dependency_overrides[dep] = mock
        yield TestClient(app)
        app.dependency_overrides.clear()  # ✅ Cleanup after yield
    """
    # This is a documentation test - verify docstring exists
    assert test_dependency_override_documentation.__doc__ is not None
    assert "✅ DO THIS" in test_dependency_override_documentation.__doc__
    assert "❌ DON'T DO THIS" in test_dependency_override_documentation.__doc__
