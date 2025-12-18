"""
Settings Fixtures Plugin.

Provides fixtures for application settings in tests.
Extracted from conftest.py for better organization.
"""

import pytest


@pytest.fixture(scope="session")
def mock_settings(test_container):
    """
    Mock settings for testing (session-scoped for performance).

    Uses container.settings pattern for consistency.
    """
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        environment="test",
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        jwt_secret_key="test-secret-key",
        anthropic_api_key="test-anthropic-key",
        model_name="claude-sonnet-4-5-20250929",
        log_level="DEBUG",
        openfga_api_url="http://localhost:8080",
        openfga_store_id="test-store-id",
        openfga_model_id="test-model-id",
    )


@pytest.fixture(scope="session")
def mock_openfga_response():
    """Mock OpenFGA API responses (session-scoped for performance)."""
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
                        "object": "tool:chat",
                    }
                }
            ]
        },
    }


@pytest.fixture
def mock_app_settings(monkeypatch):
    """
    Mock application settings with environment variables set.

    Function-scoped for test isolation.
    """
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    from mcp_server_langgraph.core.config import Settings

    return Settings()
