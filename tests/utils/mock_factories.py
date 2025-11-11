"""
Test Mock Factories

Provides reusable mock factories for common testing patterns to prevent test fixture issues.

This module addresses the root causes of common test failures:
- Missing dependency mocks in FastAPI test clients
- Incorrect provider configuration for LLM tests
- Circuit breaker state isolation issues

Usage:
    from tests.utils.mock_factories import (
        create_mock_openfga_client,
        create_mock_llm_environment,
        create_isolated_circuit_breaker,
    )

    # OpenFGA mock for API tests
    mock_openfga = create_mock_openfga_client(authorized=True)

    # LLM environment mocking
    with create_mock_llm_environment(provider="azure"):
        factory = LLMFactory(provider="azure", ...)

References:
    - Root cause analysis: Circuit breaker state pollution (pytest-xdist)
    - Root cause analysis: Missing OpenFGA dependency overrides
    - Root cause analysis: Invalid LLM provider configurations
"""

import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Literal, Optional
from unittest.mock import AsyncMock, MagicMock

# ==============================================================================
# OpenFGA Mock Factories
# ==============================================================================


def create_mock_openfga_client(authorized: bool = True) -> AsyncMock:
    """
    Create a mock OpenFGA client for FastAPI dependency injection tests.

    This mock prevents test failures caused by missing OpenFGA dependency overrides
    in FastAPI TestClient fixtures.

    Args:
        authorized: If True, all permission checks return True (authorized).
                   If False, all permission checks return False (denied).

    Returns:
        AsyncMock configured as OpenFGA client with check_permission method

    Example:
        >>> @pytest.fixture
        ... def test_client(mock_openfga_client):
        ...     app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client
        ...     return TestClient(app)

    Prevents:
        - 401 Unauthorized errors due to missing OpenFGA mock
        - Test failures in endpoints requiring OpenFGA authorization

    References:
        - tests/api/test_service_principals_endpoints.py (fixed: 4 tests)
        - Root cause: Missing dependency override for get_openfga_client
    """
    mock_client = AsyncMock()
    mock_client.check_permission = AsyncMock(return_value=authorized)
    return mock_client


# ==============================================================================
# LLM Provider Mock Factories
# ==============================================================================


@contextmanager
def create_mock_llm_environment(
    provider: Literal["azure", "bedrock", "openai", "ollama"],
    **custom_env_vars: str,
) -> Generator[Dict[str, str], None, None]:
    """
    Create mock environment variables for LLM provider testing.

    Prevents credential validation errors when testing LLM fallback logic by
    mocking required environment variables for various providers.

    Args:
        provider: LLM provider name (azure, bedrock, openai, ollama)
        **custom_env_vars: Additional environment variables to override

    Yields:
        Dict of environment variables that were set

    Example:
        >>> with create_mock_llm_environment(provider="azure"):
        ...     factory = LLMFactory(provider="azure", model_name="azure/gpt-4")
        ...     result = factory.invoke(messages)

    Prevents:
        - Azure: "Missing credentials" errors requiring AZURE_API_KEY
        - Bedrock: "No module named boto3" errors requiring AWS credentials
        - OpenAI: API key validation errors

    References:
        - tests/unit/test_llm_fallback_kwargs.py (fixed: 2 tests)
        - Root cause: Missing environment variable mocking
    """
    from unittest.mock import patch

    env_vars: Dict[str, str] = {}

    if provider == "azure":
        env_vars = {
            "AZURE_API_KEY": "test-azure-api-key",
            "AZURE_API_BASE": "https://test-endpoint.openai.azure.com",
            "AZURE_API_VERSION": "2024-02-15-preview",
        }
    elif provider == "bedrock":
        env_vars = {
            "AWS_ACCESS_KEY_ID": "test-access-key-id",
            "AWS_SECRET_ACCESS_KEY": "test-secret-access-key",
            "AWS_REGION_NAME": "us-west-2",
        }
    elif provider == "openai":
        env_vars = {
            "OPENAI_API_KEY": "test-openai-api-key",
        }
    elif provider == "ollama":
        env_vars = {
            "OLLAMA_API_BASE": "http://localhost:11434",
        }

    # Merge with custom overrides
    env_vars.update(custom_env_vars)

    with patch.dict(os.environ, env_vars):
        yield env_vars


def validate_ollama_model_name(model_name: str) -> None:
    """
    Validate Ollama model name has correct format.

    Ollama models must use the format "ollama/model:tag" or "ollama/model".
    This function helps prevent common test failures from incorrect model naming.

    Args:
        model_name: Model name to validate

    Raises:
        ValueError: If model name doesn't start with "ollama/"

    Example:
        >>> validate_ollama_model_name("ollama/llama3.1:8b")  # OK
        >>> validate_ollama_model_name("llama3.1:8b")  # Raises ValueError

    Prevents:
        - "LLM Provider NOT provided" errors for unprefixed Ollama models
        - Test failures due to incorrect model routing

    References:
        - tests/unit/test_llm_fallback_kwargs.py (fixed: 2 tests)
        - Root cause: Invalid model names missing "ollama/" prefix
    """
    if not model_name.startswith("ollama/"):
        raise ValueError(
            f"Invalid Ollama model name: '{model_name}'. "
            f"Ollama models must use format 'ollama/model:tag' or 'ollama/model'. "
            f"Did you mean 'ollama/{model_name}'?"
        )


# ==============================================================================
# Circuit Breaker Test Utilities
# ==============================================================================


@contextmanager
def create_isolated_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
) -> Generator[Any, None, None]:
    """
    Create an isolated circuit breaker context for testing circuit breaker behavior.

    Provides clean circuit breaker state for tests that intentionally manipulate
    circuit breaker state (opening, closing, counting failures).

    Args:
        name: Circuit breaker name (e.g., "openfga", "llm")
        failure_threshold: Number of failures before circuit opens

    Yields:
        Circuit breaker instance with clean state

    Example:
        >>> with create_isolated_circuit_breaker("openfga") as cb:
        ...     # Trigger failures
        ...     for _ in range(15):
        ...         try:
        ...             await client.check_permission(...)
        ...         except:
        ...             pass
        ...     # Verify circuit is open
        ...     assert cb.state.name == "open"

    Prevents:
        - Circuit breaker state pollution from autouse fixture
        - Test failures due to unexpected circuit breaker state
        - Parallel test execution issues with shared global state

    References:
        - tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality (fixed: 4 tests)
        - Root cause: Global autouse fixture resetting circuit breaker during tests
    """
    from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker, reset_circuit_breaker

    # Reset circuit breaker before test
    reset_circuit_breaker(name)

    # Get circuit breaker instance
    cb = get_circuit_breaker(name, failure_threshold=failure_threshold)

    try:
        yield cb
    finally:
        # Reset circuit breaker after test
        reset_circuit_breaker(name)


# ==============================================================================
# FastAPI Test Client Helpers
# ==============================================================================


def verify_dependency_overrides(
    app_dependency_overrides: Dict[Any, Any],
    required_dependencies: list[Any],
) -> None:
    """
    Verify that all required dependencies are overridden in a FastAPI test client.

    Helps prevent test failures caused by incomplete dependency mocking, especially
    for endpoints that require multiple dependencies (auth, OpenFGA, managers, etc.).

    Args:
        app_dependency_overrides: FastAPI app.dependency_overrides dict
        required_dependencies: List of dependency functions that must be overridden

    Raises:
        AssertionError: If any required dependency is not overridden

    Example:
        >>> from mcp_server_langgraph.core.dependencies import (
        ...     get_current_user,
        ...     get_openfga_client,
        ...     get_service_principal_manager,
        ... )
        >>> verify_dependency_overrides(
        ...     app.dependency_overrides,
        ...     [get_current_user, get_openfga_client, get_service_principal_manager],
        ... )

    Prevents:
        - 401 Unauthorized errors from missing auth mocks
        - Test failures due to uninitialized dependencies

    References:
        - tests/api/test_service_principals_endpoints.py (fixed: 4 tests)
        - Root cause: Missing get_openfga_client dependency override
    """
    missing_overrides = [dep for dep in required_dependencies if dep not in app_dependency_overrides]

    if missing_overrides:
        missing_names = [dep.__name__ for dep in missing_overrides]
        raise AssertionError(
            f"Missing required dependency overrides in FastAPI test client: {missing_names}. "
            f"Add these overrides to prevent test failures: "
            f"app.dependency_overrides[dep] = mock_dep"
        )
