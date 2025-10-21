"""Pytest configuration and shared fixtures"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import settings
from langchain_core.messages import HumanMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Set test environment variables before importing modules
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("HIPAA_INTEGRITY_SECRET", "test-hipaa-secret-key-for-testing-only")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("OPENFGA_API_URL", "http://localhost:8080")
os.environ.setdefault("OPENFGA_STORE_ID", "")  # Disable OpenFGA for tests
os.environ.setdefault("OPENFGA_MODEL_ID", "")  # Disable OpenFGA for tests
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("OTLP_ENDPOINT", "http://localhost:4317")

# Disable telemetry output during tests for cleaner output
os.environ.setdefault("ENABLE_TRACING", "false")
os.environ.setdefault("ENABLE_METRICS", "false")
os.environ.setdefault("ENABLE_CONSOLE_EXPORT", "false")


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


# Initialize observability for tests (required after lazy init refactor)
def pytest_configure(config):
    """Initialize observability system for tests."""
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    # Only initialize if not already done
    if not is_initialized():
        # Always initialize observability, even when OTEL SDK is disabled
        # This ensures lazy metrics don't raise RuntimeError
        # The OTEL SDK environment variable will ensure no-op implementations are used
        test_settings = Settings(
            log_format="text",  # Text format for easier test debugging
            enable_file_logging=False,  # No file logging in tests
            langsmith_tracing=False,  # Disable LangSmith in tests
            observability_backend="opentelemetry",  # OpenTelemetry only
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
def mock_settings():
    """Mock settings for testing (session-scoped for performance)"""
    from mcp_server_langgraph.core.config import Settings

    return Settings(
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
def integration_test_env():
    """Check if running in integration test environment (Docker)"""
    return os.getenv("TESTING") == "true"


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
    """Generate a mock JWT token"""
    from datetime import datetime, timedelta

    import jwt

    payload = {
        "sub": "alice",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
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
    with patch("secrets_manager.InfisicalClient") as mock_client:
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
