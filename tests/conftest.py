"""Pytest configuration and shared fixtures"""

import asyncio
import logging
import os
import socket
import sys
import time
import warnings
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from hypothesis import settings
from langchain_core.messages import HumanMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Set minimal test environment variables
# With container pattern, we no longer need to set all these before imports!
# The container handles test mode configuration automatically.
# We only set critical ones that can't be overridden:
os.environ.setdefault("ENVIRONMENT", "test")  # Trigger test mode
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("HIPAA_INTEGRITY_SECRET", "test-hipaa-secret-key-for-testing-only")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")  # Disable OpenTelemetry SDK

# Suppress gRPC logging noise in tests
warnings.filterwarnings("ignore", message=".*failed to connect to all addresses.*")
warnings.filterwarnings("ignore", message=".*Connection refused.*")

# Also suppress grpc library logs
logging.getLogger("grpc").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.CRITICAL)


# Configure Hypothesis profiles for property-based testing
# Register CI profile with comprehensive testing (100 examples)
settings.register_profile(
    "ci",
    max_examples=100,
    deadline=None,  # No deadline in CI for comprehensive testing
    print_blob=True,  # Print failing examples for debugging
    derandomize=True,  # Deterministic test execution in CI
)

# Register dev profile for fast iteration (25 examples)
settings.register_profile(
    "dev",
    max_examples=25,
    deadline=2000,  # 2 second deadline for fast feedback
    print_blob=False,  # No blob printing in dev for clean output
    derandomize=False,  # Randomized for better coverage
)

# Load appropriate profile based on environment
# CI sets HYPOTHESIS_PROFILE=ci, defaults to dev otherwise
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# ==============================================================================
# Docker Infrastructure Fixtures (Automated Lifecycle Management)
# ==============================================================================


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    """
    Wait for a TCP port to become available.

    Returns True if port is available, False if timeout is reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except socket.error:
            pass
        time.sleep(0.5)
    return False


def _check_http_health(url: str, timeout: float = 2.0) -> bool:
    """Check if HTTP endpoint is healthy."""
    try:
        import httpx
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def docker_compose_file():
    """
    Provide path to docker-compose.test.yml for pytest-docker-compose-v2.

    This enables automated docker-compose lifecycle management:
    - Services start automatically before test session
    - Services stop automatically after test session
    - No manual docker-compose commands needed
    """
    return os.path.join(os.path.dirname(__file__), "..", "docker-compose.test.yml")


@pytest.fixture(scope="session")
def docker_services_available(docker_compose_file):
    """
    Check if Docker is available and docker-compose.test.yml exists.

    This is a lightweight check that runs before attempting to start services.
    """
    # Check if docker-compose file exists
    if not os.path.exists(docker_compose_file):
        pytest.skip(f"Docker compose file not found: {docker_compose_file}")

    # Check if Docker is available
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Docker daemon not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker not installed or not responding")

    return True


@pytest.fixture(scope="session")
def test_infrastructure_ports():
    """
    Define test infrastructure ports (offset by 1000 from production).

    These match the ports defined in docker-compose.test.yml.
    """
    return {
        "postgres": 9432,
        "redis_checkpoints": 9379,
        "redis_sessions": 9380,
        "qdrant": 9333,
        "qdrant_grpc": 9334,
        "openfga_http": 9080,
        "openfga_grpc": 9081,
        "keycloak": 9082,
    }


@pytest.fixture(scope="session")
def test_infrastructure(docker_services_available, docker_compose_file, test_infrastructure_ports):
    """
    Automated test infrastructure lifecycle management.

    This fixture:
    1. Starts all services via docker-compose.test.yml
    2. Waits for health checks to pass
    3. Yields control to tests
    4. Automatically tears down services after session

    Replaces manual:
        docker compose -f docker-compose.test.yml up -d
        docker compose -f docker-compose.test.yml down -v

    Usage:
        @pytest.mark.e2e
        def test_with_infrastructure(test_infrastructure):
            # All services are running and healthy
            ...
    """
    # Set TESTING environment variable for services
    os.environ["TESTING"] = "true"

    try:
        # Start services using python-on-whales (used by pytest-docker-compose-v2)
        from python_on_whales import DockerClient

        docker = DockerClient(compose_files=[docker_compose_file])

        # Start services
        logging.info("Starting test infrastructure via docker-compose...")
        docker.compose.up(detach=True, wait=False)

        # Wait for critical services to be ready
        logging.info("Waiting for test infrastructure health checks...")

        # PostgreSQL
        if not _wait_for_port("localhost", test_infrastructure_ports["postgres"], timeout=30):
            pytest.fail("PostgreSQL test service did not become ready in time")
        logging.info("✓ PostgreSQL ready")

        # Redis (checkpoints)
        if not _wait_for_port("localhost", test_infrastructure_ports["redis_checkpoints"], timeout=20):
            pytest.fail("Redis checkpoints test service did not become ready in time")
        logging.info("✓ Redis (checkpoints) ready")

        # Redis (sessions)
        if not _wait_for_port("localhost", test_infrastructure_ports["redis_sessions"], timeout=20):
            pytest.fail("Redis sessions test service did not become ready in time")
        logging.info("✓ Redis (sessions) ready")

        # OpenFGA HTTP
        if not _wait_for_port("localhost", test_infrastructure_ports["openfga_http"], timeout=40):
            pytest.fail("OpenFGA test service did not become ready in time")
        # Additional check for OpenFGA
        if not _check_http_health("http://localhost:9080/healthz", timeout=5):
            pytest.fail("OpenFGA health check failed")
        logging.info("✓ OpenFGA ready")

        # Keycloak (takes longer to start)
        if not _wait_for_port("localhost", test_infrastructure_ports["keycloak"], timeout=90):
            pytest.fail("Keycloak test service did not become ready in time")
        # Additional check for Keycloak
        if not _check_http_health("http://localhost:9082/health/ready", timeout=10):
            pytest.fail("Keycloak health check failed")
        logging.info("✓ Keycloak ready")

        # Qdrant
        if not _wait_for_port("localhost", test_infrastructure_ports["qdrant"], timeout=30):
            pytest.fail("Qdrant test service did not become ready in time")
        logging.info("✓ Qdrant ready")

        logging.info("✅ All test infrastructure services ready")

        # Return infrastructure info
        yield {
            "ports": test_infrastructure_ports,
            "docker": docker,
            "ready": True
        }

    finally:
        # Cleanup: Stop and remove services
        logging.info("Tearing down test infrastructure...")
        try:
            docker.compose.down(volumes=True, remove_orphans=True, timeout=30)
            logging.info("✅ Test infrastructure cleaned up")
        except Exception as e:
            logging.error(f"Error during infrastructure cleanup: {e}")


# ==============================================================================
# Fixed Time Fixture for Deterministic Tests
# ==============================================================================


@pytest.fixture
def frozen_time():
    """
    Freeze time for deterministic timestamp testing.

    All datetime.now(), time.time(), etc. calls will return the fixed time.
    This eliminates test flakiness caused by time-dependent assertions.

    Usage:
        @pytest.mark.usefixtures("frozen_time")
        def test_timestamps():
            # datetime.now() will always return 2024-01-01T00:00:00Z
            assert datetime.now(timezone.utc).isoformat() == "2024-01-01T00:00:00+00:00"
    """
    with freeze_time("2024-01-01 00:00:00", tz_offset=0):
        yield


# ==============================================================================
# E2E FastAPI App Fixtures
# ==============================================================================


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
        # Database settings
        postgres_host="localhost",
        postgres_port=test_infrastructure_ports["postgres"],
        postgres_db="openfga_test",
        postgres_user="postgres",
        postgres_password="postgres",
        # Redis settings
        redis_host="localhost",
        redis_port=test_infrastructure_ports["redis_checkpoints"],
        redis_sessions_port=test_infrastructure_ports["redis_sessions"],
        # OpenFGA settings
        openfga_api_url=f"http://localhost:{test_infrastructure_ports['openfga_http']}",
        openfga_store_id=None,  # Will be created dynamically in tests
        openfga_model_id=None,
        # Keycloak settings
        keycloak_url=f"http://localhost:{test_infrastructure_ports['keycloak']}",
        keycloak_realm="master",  # Use master realm for tests
        keycloak_client_id="admin-cli",
        keycloak_admin_username="admin",
        keycloak_admin_password="admin",
        # Qdrant settings
        qdrant_url="localhost",
        qdrant_port=test_infrastructure_ports["qdrant"],
        # Security settings
        jwt_secret_key="test-jwt-secret-key-for-e2e-testing-only",
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
        from mcp_server_langgraph.app import create_app

        app = create_app()

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

    async with httpx.AsyncClient(app=test_fastapi_app, base_url="http://test") as client:
        yield client


# Container-based test fixtures (NEW APPROACH)
# These replace the old global initialization pattern


@pytest.fixture(scope="session")
def test_container():
    """
    Create test container for the session.

    This container:
    - Uses no-op telemetry (no output)
    - Uses no-op auth (accepts any token)
    - Uses in-memory storage
    - Has NO global side effects

    Replaces: pytest_configure(), init_observability_for_workers()
    """
    from mcp_server_langgraph.core.container import create_test_container

    container = create_test_container()
    yield container
    # No cleanup needed - container has no global state


@pytest.fixture
def container(test_container):
    """
    Per-test container fixture.

    Use this when you need a fresh container for each test.
    For most tests, use test_container (session-scoped) instead.
    """
    from mcp_server_langgraph.core.container import create_test_container

    return create_test_container()


# ==============================================================================
# Shared Authentication Fixtures
# ==============================================================================


@pytest.fixture
def mock_current_user():
    """
    Shared mock current user fixture for API endpoint tests.

    Provides a consistent user identity with both OpenFGA and Keycloak formats:
    - user_id: OpenFGA format (user:{username})
    - keycloak_id: Keycloak UUID format
    - username: Plain username
    - email: User email

    This fixture ensures consistency across all API tests and matches the
    actual identity model used in production.
    """
    return {
        "user_id": "user:alice",  # OpenFGA format
        "keycloak_id": "8c7b4e5d-1234-5678-abcd-ef1234567890",  # Keycloak UUID
        "username": "alice",
        "email": "alice@example.com",
    }


# Legacy observability initialization (DEPRECATED - will be removed after migration)
# Kept temporarily for backward compatibility with existing tests
def pytest_configure(config):
    """
    DEPRECATED: Use container fixtures instead.

    Initialize observability system for tests (legacy approach).
    New tests should use the container fixture.
    """
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    # Only initialize if not already done
    if not is_initialized():
        test_settings = Settings(
            environment="test",
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)


# Mock MCP server initialization at session level to prevent event loop issues
@pytest.fixture(scope="session")
def mock_mcp_modules():
    """Mock MCP server modules to prevent async initialization at import time"""
    # Create mock MCP SDK Server
    mock_mcp_sdk_server = MagicMock()
    mock_tool_manager = MagicMock()
    mock_resource_manager = MagicMock()

    # Mock the managers
    type(mock_mcp_sdk_server)._tool_manager = property(lambda self: mock_tool_manager)
    type(mock_mcp_sdk_server)._resource_manager = property(lambda self: mock_resource_manager)

    # Create mock server instance
    mock_server_instance = MagicMock()
    mock_server_instance.server = mock_mcp_sdk_server
    mock_server_instance.auth = MagicMock()

    # Patch the class before any imports
    with patch("mcp_server_langgraph.mcp.server_streamable.MCPAgentStreamableServer", return_value=mock_server_instance):
        # Return dict with all mocks for test access
        yield {
            "server_instance": mock_server_instance,
            "tool_manager": mock_tool_manager,
            "resource_manager": mock_resource_manager,
        }


@pytest.fixture(scope="session")
def mock_settings(test_container):
    """
    Mock settings for testing (session-scoped for performance).

    Now uses container.settings instead of creating settings directly.
    This ensures consistency with the container pattern.
    """
    # You can still create custom settings for specific tests
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        environment="test",
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        jwt_secret_key="test-secret-key",
        anthropic_api_key="test-anthropic-key",
        model_name="claude-3-5-sonnet-20241022",
        log_level="DEBUG",
        openfga_api_url="http://localhost:8080",
        openfga_store_id="test-store-id",
        openfga_model_id="test-model-id",
    )


@pytest.fixture(scope="session")
def mock_openfga_response():
    """Mock OpenFGA API responses (session-scoped for performance)"""
    return {
        "check": {"allowed": True},
        "list_objects": {"objects": ["tool:chat", "tool:search"]},
        "write": {"writes": []},
        "read": {"tuples": [{"key": {"user": "user:alice", "relation": "executor", "object": "tool:chat"}}]},
    }


@pytest.fixture
def integration_test_env(test_infrastructure):
    """
    Check if running in integration test environment (Docker).

    DEPRECATED: Use test_infrastructure fixture directly for new tests.
    This fixture is kept for backward compatibility with existing tests.

    The test_infrastructure fixture now automatically manages the full
    docker-compose lifecycle, so this fixture will always return True
    when test_infrastructure is active.
    """
    return test_infrastructure["ready"]


@pytest.fixture(scope="session")
async def postgres_connection_real(integration_test_env):
    """Real PostgreSQL connection for integration tests"""
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    # Connection params from environment (set in docker-compose.test.yml)
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "testdb"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "test"),
    )

    yield conn

    await conn.close()


@pytest.fixture(scope="session")
async def redis_client_real(integration_test_env):
    """Real Redis client for integration tests"""
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import redis.asyncio as redis
    except ImportError:
        pytest.skip("redis not installed")

    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )

    # Test connection
    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup test data
    await client.flushdb()
    await client.aclose()


@pytest.fixture(scope="session")
async def openfga_client_real(integration_test_env):
    """Real OpenFGA client for integration tests"""
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient

    # OpenFGA URL from environment
    api_url = os.getenv("OPENFGA_API_URL", "http://localhost:8080")

    client = OpenFGAClient(api_url=api_url, store_id=None, model_id=None)

    # TODO: Create test store and model if needed
    # For now, tests should handle store/model creation themselves

    yield client

    # Cleanup happens per-test


@pytest.fixture(scope="session")
def qdrant_available():
    """Check if Qdrant is available for testing."""
    qdrant_url = os.getenv("QDRANT_URL", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    try:
        import httpx

        # Quick check if Qdrant is accessible
        response = httpx.get(f"http://{qdrant_url}:{qdrant_port}/", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def qdrant_client():
    """Qdrant client for integration tests with vector search."""
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        pytest.skip("Qdrant client not installed")

    qdrant_url = os.getenv("QDRANT_URL", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    # Check if Qdrant is available
    try:
        import httpx

        response = httpx.get(f"http://{qdrant_url}:{qdrant_port}/", timeout=2.0)
        if response.status_code != 200:
            pytest.skip("Qdrant instance not available")
    except Exception as e:
        pytest.skip(f"Qdrant instance not available: {e}")

    # Create client
    client = QdrantClient(url=qdrant_url, port=qdrant_port)

    # Test connection
    try:
        client.get_collections()
    except Exception as e:
        pytest.skip(f"Cannot connect to Qdrant: {e}")

    yield client

    # Cleanup: Delete test collections
    try:
        collections = client.get_collections().collections
        test_collections = [c.name for c in collections if c.name.startswith("test_")]
        for collection_name in test_collections:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass  # Best effort cleanup
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture(scope="session")
def mock_infisical_response():
    """Mock Infisical API responses (session-scoped for performance)"""
    return {
        "secrets": [
            {"secretKey": "JWT_SECRET_KEY", "secretValue": "test-jwt-secret", "version": 1},
            {"secretKey": "ANTHROPIC_API_KEY", "secretValue": "sk-ant-test-key", "version": 1},
        ]
    }


@pytest.fixture
def mock_jwt_token():
    """
    Generate a mock JWT token with deterministic timestamps.

    Uses fixed time: 2024-01-01T00:00:00Z
    """
    import jwt

    FIXED_TIME = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    payload = {
        "sub": "alice",
        "exp": FIXED_TIME + timedelta(hours=1),
        "iat": FIXED_TIME,
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture(scope="session")
def mock_user_alice():
    """Mock user alice (session-scoped for performance)"""
    return {"username": "alice", "tier": "premium", "organization": "acme", "roles": ["admin", "user"]}


@pytest.fixture(scope="session")
def mock_user_bob():
    """Mock user bob (session-scoped for performance)"""
    return {"username": "bob", "tier": "standard", "organization": "acme", "roles": ["user"]}


@pytest.fixture
def mock_agent_state():
    """Mock LangGraph agent state"""
    return {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "next_action": "respond",
        "user_id": "alice",
        "request_id": "test-request-123",
    }


@pytest.fixture
def in_memory_span_exporter():
    """Create in-memory span exporter for testing traces"""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    # Clear spans after test
    exporter.clear()


@pytest.fixture
async def mock_httpx_client():
    """Mock httpx async client"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="I am Claude, an AI assistant.")]
    mock_message.stop_reason = "end_turn"

    mock_client.messages.create.return_value = mock_message

    return mock_client


@pytest.fixture(scope="session")
def mock_mcp_request():
    """Mock MCP JSON-RPC request (session-scoped for performance)"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "chat", "arguments": {"message": "What is 2+2?", "username": "alice"}},
    }


@pytest.fixture(scope="session")
def mock_mcp_initialize_request():
    """Mock MCP initialize request (session-scoped for performance)"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test-client", "version": "1.0.0"}},
    }


@pytest.fixture
async def mock_openfga_client(mock_openfga_response):
    """Mock OpenFGA client"""
    with patch("openfga_client.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openfga_response["check"]
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        yield mock_client


@pytest.fixture
async def mock_infisical_client(mock_infisical_response):
    """Mock Infisical client"""
    # FIXED: Corrected patch path to match actual runtime module location
    # The runtime module is mcp_server_langgraph.secrets.manager, not secrets_manager
    with patch("mcp_server_langgraph.secrets.manager.InfisicalClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_infisical_response["secrets"][0]
        mock_instance.list_secrets.return_value = mock_infisical_response["secrets"]
        mock_client.return_value = mock_instance

        yield mock_client


@pytest.fixture(scope="session")
def sample_openfga_tuples():
    """Sample OpenFGA relationship tuples (session-scoped for performance)"""
    return [
        {"user": "user:alice", "relation": "executor", "object": "tool:chat"},
        {"user": "user:alice", "relation": "admin", "object": "organization:acme"},
        {"user": "user:bob", "relation": "member", "object": "organization:acme"},
        {"user": "organization:acme#member", "relation": "executor", "object": "tool:search"},
    ]


@pytest.fixture
def temp_checkpoint_dir(tmp_path):
    """Create temporary directory for checkpoints"""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return str(checkpoint_dir)


# Async context manager helpers
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


def _reset_circuit_breakers(reset_fn):
    """Helper to reset all known circuit breakers."""
    if not reset_fn:
        return
    known_services = ["llm", "openfga", "redis", "keycloak", "qdrant"]
    for service in known_services:
        try:
            reset_fn(service)
        except Exception:
            pass  # Ignore errors if service not initialized


def _reset_bulkheads(reset_fn):
    """Helper to reset all known bulkheads."""
    if not reset_fn:
        return
    known_bulkheads = ["default", "llm", "openfga", "redis"]
    for bulkhead_name in known_bulkheads:
        try:
            reset_fn(bulkhead_name)
        except Exception:
            pass  # Ignore errors if bulkhead not initialized


@pytest.fixture(autouse=True)
def reset_resilience_state():
    """
    Reset all resilience patterns between tests to prevent state pollution.

    This fixture automatically runs before each test to ensure:
    - Circuit breakers are closed
    - Bulkheads are cleared
    - Retry state is reset

    This prevents test failures caused by resilience state from previous tests.
    """
    # Import resilience modules
    try:
        from mcp_server_langgraph.resilience.circuit_breaker import reset_circuit_breaker
    except ImportError:
        reset_circuit_breaker = None

    try:
        from mcp_server_langgraph.resilience.bulkhead import reset_bulkhead
    except ImportError:
        reset_bulkhead = None

    # Reset before test
    _reset_circuit_breakers(reset_circuit_breaker)
    _reset_bulkheads(reset_bulkhead)

    yield

    # Cleanup after test (helps with test isolation)
    _reset_circuit_breakers(reset_circuit_breaker)
