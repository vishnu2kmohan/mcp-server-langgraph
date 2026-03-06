"""
Infrastructure test fixtures for E2E testing.

Extracted from conftest.py as part of P1.3 Test Fixture Optimization.
Contains fixtures for test infrastructure ports, app settings, and clients.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Get the repository root directory.

    Use this fixture instead of manual Path(__file__).parents[N] navigation
    to prevent path resolution bugs in tests. The conftest.py is always in
    tests/, so parent.parent gets us to the repo root.

    Returns:
        Path to repository root directory
    """
    # This plugin is in tests/plugins/, so parent.parent.parent gets us to the repo root
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def deployments_dir(repo_root: Path) -> Path:
    """Get the deployments directory.

    Args:
        repo_root: Repository root path (injected by pytest)

    Returns:
        Path to deployments/ directory
    """
    return repo_root / "deployments"


@pytest.fixture(scope="session")
def test_infrastructure_ports():
    """
    Return fixed infrastructure service ports for ALL pytest-xdist workers.

    Single Shared Infrastructure Architecture:
    =========================================
    - ONE docker-compose instance runs on FIXED base ports (9432, 9379, etc.)
    - ALL xdist workers (gw0, gw1, gw2, ...) connect to the SAME ports
    - Isolation is achieved via logical separation, NOT port offsets:
      * PostgreSQL: Separate schemas per worker (test_worker_gw0, test_worker_gw1)
      * Redis: Separate DB indices per worker (DB 1, 2, 3, ...)
      * OpenFGA: Separate stores per worker (test_store_gw0, test_store_gw1)
      * Qdrant: Separate collections per worker
      * Keycloak: Separate realms per worker

    Port Mappings (from docker-compose.test.yml):
    ==============================================
    - postgres: 9432 -> 5432 (container port)
    - redis_checkpoints: 9379 -> 6379 (consolidated Redis instance)
    - redis_sessions: 9379 -> 6379 (consolidated Redis instance, same as checkpoints)
    - qdrant: 9333 -> 6333
    - qdrant_grpc: 9334 -> 6334
    - openfga_http: 9080 -> 8080
    - openfga_grpc: 9081 -> 8081
    - keycloak: 9082 -> 8080
    - keycloak_management: 9900 -> 9000

    Returns:
        Dict[str, int]: Fixed port mappings for all infrastructure services
    """
    return {
        "postgres": 9432,
        "redis_checkpoints": 9379,
        "redis_sessions": 9379,  # Same port as checkpoints (consolidated in test)
        "qdrant": 9333,
        "qdrant_grpc": 9334,
        "openfga_http": 9080,
        "openfga_grpc": 9081,
        "keycloak": 9082,
        "keycloak_management": 9900,
    }


@pytest.fixture
def test_app_settings(test_infrastructure_ports):
    """
    Create test settings configured to use test infrastructure services.

    Returns Settings object pointing to test ports (offset by 1000).
    """
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        environment="test",
        service_name="test-mcp-server",
        # Database settings - use gdpr_postgres_url (individual postgres_* fields removed)
        gdpr_postgres_url=f"postgresql://postgres:postgres@localhost:{test_infrastructure_ports['postgres']}/gdpr",
        # Redis settings (use same port for both sessions and checkpoints in tests)
        redis_host="localhost",
        redis_port=test_infrastructure_ports["redis_checkpoints"],
        # Redis URLs are constructed from host/port
        redis_url=f"redis://localhost:{test_infrastructure_ports['redis_sessions']}/0",
        checkpoint_redis_url=f"redis://localhost:{test_infrastructure_ports['redis_checkpoints']}/1",
        # OpenFGA settings
        openfga_api_url=f"http://localhost:{test_infrastructure_ports['openfga_http']}",
        openfga_store_id=None,  # Will be created dynamically in tests
        openfga_model_id=None,
        # Keycloak settings
        keycloak_server_url=f"http://localhost:{test_infrastructure_ports['keycloak']}",
        keycloak_realm="default",  # Use default realm for tests
        keycloak_client_id="admin-cli",
        keycloak_admin_username="admin",
        keycloak_admin_password="admin",
        # Qdrant settings
        qdrant_url="localhost",
        qdrant_port=test_infrastructure_ports["qdrant"],
        # Security settings
        jwt_secret_key="agent-studio-jwt-secret-key-for-e2e-tests",
        hipaa_integrity_secret="test-hipaa-secret-for-e2e-testing-only",
        # Test-specific settings
        log_level="DEBUG",
        log_format="text",
        enable_file_logging=False,
        langsmith_tracing=False,
        observability_backend="opentelemetry",
    )


@pytest.fixture
async def test_fastapi_app(test_infrastructure, test_app_settings):
    """
    Create FastAPI app instance configured for E2E testing.

    This fixture:
    1. Waits for test infrastructure to be ready
    2. Creates app with test settings
    3. Yields app for testing
    4. Cleans up after tests

    Usage:
        @pytest.mark.e2e
        async def test_api_endpoint(test_fastapi_app):
            from fastapi.testclient import TestClient
            client = TestClient(test_fastapi_app)
            response = client.get("/health")
            assert response.status_code == 200
    """
    # Ensure infrastructure is ready
    assert test_infrastructure["ready"], "Test infrastructure not ready"

    # Override settings with test configuration
    with patch("mcp_server_langgraph.core.config.settings", test_app_settings):
        # Import and create app with patched settings
        # Use server_streamable app to match production transport
        from mcp_server_langgraph.mcp.server_streamable import app

        yield app

        # Cleanup: No explicit cleanup needed as infrastructure handles it


@pytest.fixture
def test_client(test_fastapi_app):
    """
    Create FastAPI TestClient for synchronous E2E testing.

    Usage:
        @pytest.mark.e2e
        def test_endpoint(test_client):
            response = test_client.get("/api/v1/health")
            assert response.status_code == 200
    """
    from fastapi.testclient import TestClient

    return TestClient(test_fastapi_app)


@pytest.fixture
async def test_async_client(test_fastapi_app):
    """
    Create httpx AsyncClient for asynchronous E2E testing.

    Usage:
        @pytest.mark.e2e
        async def test_async_endpoint(test_async_client):
            response = await test_async_client.get("/api/v1/health")
            assert response.status_code == 200
    """
    import httpx
    from httpx import ASGITransport

    # Create transport with the app
    transport = ASGITransport(app=test_fastapi_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        yield client


@pytest.fixture(scope="session")
def integration_test_env(test_infrastructure):
    """
    Check if running in integration test environment (Docker).

    DEPRECATED: Use test_infrastructure fixture directly for new tests.
    This fixture is kept for backward compatibility with existing tests.

    The test_infrastructure fixture now automatically manages the full
    docker-compose lifecycle, so this fixture will always return True
    when test_infrastructure is active.

    Scope: session - Must match the scope of dependent fixtures
    """
    return test_infrastructure["ready"]


@pytest.fixture
def temp_checkpoint_dir(tmp_path):
    """Create temporary directory for checkpoints"""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return str(checkpoint_dir)


@pytest.fixture(scope="session")
def async_context_manager():
    """Helper to create async context managers for mocking (session-scoped for performance)"""

    def _create(return_value):
        class AsyncContextManager:
            async def __aenter__(self):
                return return_value

            async def __aexit__(self, *args):
                pass

        return AsyncContextManager()

    return _create
