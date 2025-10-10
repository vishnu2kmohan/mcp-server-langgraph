"""Pytest configuration and shared fixtures"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Set test environment variables before importing modules
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("OPENFGA_API_URL", "http://localhost:8080")
os.environ.setdefault("OPENFGA_STORE_ID", "test-store-id")
os.environ.setdefault("OPENFGA_MODEL_ID", "test-model-id")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("OTLP_ENDPOINT", "http://localhost:4317")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    from config import Settings

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


@pytest.fixture
def mock_openfga_response():
    """Mock OpenFGA API responses"""
    return {
        "check": {"allowed": True},
        "list_objects": {"objects": ["tool:chat", "tool:search"]},
        "write": {"writes": []},
        "read": {
            "tuples": [
                {
                    "key": {
                        "user": "user:alice",
                        "relation": "executor",
                        "object": "tool:chat"
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_infisical_response():
    """Mock Infisical API responses"""
    return {
        "secrets": [
            {
                "secretKey": "JWT_SECRET_KEY",
                "secretValue": "test-jwt-secret",
                "version": 1
            },
            {
                "secretKey": "ANTHROPIC_API_KEY",
                "secretValue": "sk-ant-test-key",
                "version": 1
            }
        ]
    }


@pytest.fixture
def mock_jwt_token():
    """Generate a mock JWT token"""
    import jwt
    from datetime import datetime, timedelta

    payload = {
        "sub": "alice",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture
def mock_user_alice():
    """Mock user alice"""
    return {
        "username": "alice",
        "tier": "premium",
        "organization": "acme",
        "roles": ["admin", "user"]
    }


@pytest.fixture
def mock_user_bob():
    """Mock user bob"""
    return {
        "username": "bob",
        "tier": "standard",
        "organization": "acme",
        "roles": ["user"]
    }


@pytest.fixture
def mock_agent_state():
    """Mock LangGraph agent state"""
    return {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "next_action": "respond",
        "user_id": "alice",
        "request_id": "test-request-123"
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


@pytest.fixture
def mock_mcp_request():
    """Mock MCP JSON-RPC request"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "chat",
            "arguments": {
                "message": "What is 2+2?",
                "username": "alice"
            }
        }
    }


@pytest.fixture
def mock_mcp_initialize_request():
    """Mock MCP initialize request"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
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


@pytest.fixture
def sample_openfga_tuples():
    """Sample OpenFGA relationship tuples"""
    return [
        {
            "user": "user:alice",
            "relation": "executor",
            "object": "tool:chat"
        },
        {
            "user": "user:alice",
            "relation": "admin",
            "object": "organization:acme"
        },
        {
            "user": "user:bob",
            "relation": "member",
            "object": "organization:acme"
        },
        {
            "user": "organization:acme#member",
            "relation": "executor",
            "object": "tool:search"
        }
    ]


@pytest.fixture
def temp_checkpoint_dir(tmp_path):
    """Create temporary directory for checkpoints"""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return str(checkpoint_dir)


# Async context manager helpers
@pytest.fixture
def async_context_manager():
    """Helper to create async context managers for mocking"""
    def _create(return_value):
        class AsyncContextManager:
            async def __aenter__(self):
                return return_value

            async def __aexit__(self, *args):
                pass

        return AsyncContextManager()

    return _create
