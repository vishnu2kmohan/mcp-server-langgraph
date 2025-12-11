"""
Test Mock Factories

Provides reusable mock factories for common testing patterns to prevent test fixture issues.

This module addresses the root causes of common test failures:
- Missing dependency mocks in FastAPI test clients
- Incorrect provider configuration for LLM tests
- Circuit breaker state isolation issues
- Brittle unit tests coupled to implementation details (50+ @patch decorators)

## Traditional Mock Factories (Phase 1)

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

## Behavioral Mock Factories (Phase 2 - NEW)

Behavioral mocks test WHAT happens (behavior), not HOW it's implemented.
This makes tests resilient to refactoring.

Usage:
    from tests.utils.mock_factories import (
        create_behavioral_auth_middleware,
        create_behavioral_agent_graph,
        create_behavioral_llm_provider,
        create_behavioral_checkpointer,
    )

    # Test: Authorized user can chat
    auth = create_behavioral_auth_middleware(authorized=True, user_id="alice")
    agent = create_behavioral_agent_graph(response_message="Hi!")

    server = MCPAgentServer(auth_middleware=auth, agent_graph=agent)
    response = await server.handle_chat(message="Hello", token="valid-token")

    assert "Hi!" in response  # Verify behavior, not implementation

Benefits:
    - ✅ Tests survive refactoring (no coupling to import paths)
    - ✅ Self-documenting (behavioral intent is clear)
    - ✅ Composable (mocks can be combined easily)
    - ✅ Fewer lines (no @patch decorator boilerplate)
    - ✅ Reduces 50 @patch decorators to <10 in test_mcp_stdio_server.py

References:
    - Backlog: TESTING_INFRASTRUCTURE_IMPROVEMENTS_BACKLOG.md (Phase 2)
    - Problem: tests/unit/mcp/test_mcp_stdio_server.py has 50 @patch decorators
    - Root cause analysis: Circuit breaker state pollution (pytest-xdist)
    - Root cause analysis: Missing OpenFGA dependency overrides
    - Root cause analysis: Invalid LLM provider configurations
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Literal
from unittest.mock import AsyncMock

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
    mock_client = AsyncMock(return_value=None)  # Container for configured methods
    mock_client.check_permission = AsyncMock(return_value=authorized)
    return mock_client


# ==============================================================================
# LLM Provider Mock Factories
# ==============================================================================


@contextmanager
def create_mock_llm_environment(
    provider: Literal["azure", "bedrock", "openai", "ollama"],
    **custom_env_vars: str,
) -> Generator[dict[str, str], None, None]:
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
        - tests/unit/llm/test_llm_fallback_kwargs.py (fixed: 2 tests)
        - Root cause: Missing environment variable mocking
    """
    from unittest.mock import patch

    env_vars: dict[str, str] = {}

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
        - tests/unit/llm/test_llm_fallback_kwargs.py (fixed: 2 tests)
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
) -> Generator[Any, None, None]:
    """
    Create an isolated circuit breaker context for testing circuit breaker behavior.

    Provides clean circuit breaker state for tests that intentionally manipulate
    circuit breaker state (opening, closing, counting failures).

    Args:
        name: Circuit breaker name (e.g., "openfga", "llm")

    Yields:
        Circuit breaker instance with clean state

    Note:
        The circuit breaker failure threshold is configured via ResilienceConfig,
        not passed as a parameter here. To customize, set up the config before
        calling this function.

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

    # Get circuit breaker instance (configuration comes from ResilienceConfig)
    cb = get_circuit_breaker(name)

    try:
        yield cb
    finally:
        # Reset circuit breaker after test
        reset_circuit_breaker(name)


# ==============================================================================
# Behavioral Mock Factories (Phase 2: Unit Test Refactoring)
# ==============================================================================
#
# Behavioral mocks test WHAT happens (behavior), not HOW it's implemented.
# This approach makes tests resilient to refactoring - internal changes don't
# break tests as long as external behavior remains the same.
#
# Benefits over @patch decorators:
# - Tests survive refactoring (no coupling to import paths)
# - Self-documenting (behavioral intent is clear)
# - Composable (mocks can be combined easily)
# - Fewer lines of code (no patch setup boilerplate)
#
# References:
#   - Backlog: TESTING_INFRASTRUCTURE_IMPROVEMENTS_BACKLOG.md (Phase 2)
#   - Problem: tests/unit/mcp/test_mcp_stdio_server.py has 50 @patch decorators


def create_behavioral_auth_middleware(
    *, authorized: bool = True, user_id: str = "alice", token_valid: bool = True, token_payload: dict | None = None
):
    """
    Create behavioral mock for AuthMiddleware.

    Tests BEHAVIOR: "When token is valid, user is authorized"
    NOT implementation: "verify_token uses JWT library with HS256"

    Args:
        authorized: Whether authorization checks succeed
        user_id: User ID returned in token payload
        token_valid: Whether token validation succeeds
        token_payload: Custom token payload (overrides user_id)

    Returns:
        Mock AuthMiddleware that behaves like real middleware

    Example:
        >>> # Test: Authorized user can access resource
        >>> auth = create_behavioral_auth_middleware(
        ...     authorized=True,
        ...     user_id="alice"
        ... )
        >>> server = MCPAgentServer(auth_middleware=auth)
        >>> response = await server.handle_chat(message="Hello", token="valid-token")
        >>> # Verify behavior: chat succeeded
        >>> assert "Hello" in response

        >>> # Test: Unauthorized user is denied
        >>> auth = create_behavioral_auth_middleware(authorized=False)
        >>> with pytest.raises(PermissionError):
        ...     await server.handle_chat(message="Hello", token="valid-token")

    Replaces:
        @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
        @patch("mcp_server_langgraph.mcp.server_stdio.settings")
        def test_auth(mock_settings, mock_create_auth):
            # 10+ lines of setup...
    """
    from unittest.mock import MagicMock

    mock = MagicMock()

    # verify_token is async in real middleware
    if token_valid:
        verification = MagicMock()
        verification.valid = True
        verification.payload = token_payload or {"sub": user_id, "exp": 9999999999}
        verification.error = None
        mock.verify_token = AsyncMock(return_value=verification)
    else:
        verification = MagicMock()
        verification.valid = False
        verification.error = "Invalid token"
        verification.payload = None
        mock.verify_token = AsyncMock(return_value=verification)

    # authorize can be async or sync depending on usage
    mock.authorize = AsyncMock(return_value=authorized)

    return mock


def create_behavioral_agent_graph(
    *,
    response_message: str = "Hello! How can I help you today?",
    conversation_exists: bool = False,
    user_id: str = "alice",
    messages: list | None = None,
    next_action: str = "",
    invoke_error: Exception | None = None,
):
    """
    Create behavioral mock for LangGraph CompiledGraph.

    Tests BEHAVIOR: "Agent responds to user message"
    NOT implementation: "Graph uses specific checkpointer class"

    Args:
        response_message: Agent's response to user
        conversation_exists: Whether conversation has previous messages
        user_id: User ID for conversation
        messages: Custom message history (overrides conversation_exists)
        next_action: Next action after agent response
        invoke_error: Exception to raise on invoke (for error testing)

    Returns:
        Mock CompiledGraph that behaves like real agent graph

    Example:
        >>> # Test: Agent responds to new conversation
        >>> agent = create_behavioral_agent_graph(
        ...     response_message="Hi! I'm your AI assistant.",
        ...     conversation_exists=False
        ... )
        >>> result = await agent.ainvoke({"messages": [HumanMessage("Hello")]})
        >>> assert "AI assistant" in result["messages"][-1].content

        >>> # Test: Agent handles errors gracefully
        >>> agent = create_behavioral_agent_graph(
        ...     invoke_error=ValueError("LLM API error")
        ... )
        >>> with pytest.raises(ValueError):
        ...     await agent.ainvoke({"messages": [HumanMessage("Hello")]})

    Replaces:
        @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
        @patch("mcp_server_langgraph.mcp.server_stdio.settings")
        def test_agent(mock_settings, mock_get_graph):
            # 15+ lines of setup...
    """
    from langchain_core.messages import AIMessage, HumanMessage
    from unittest.mock import MagicMock

    mock = AsyncMock()

    # Setup state snapshot behavior
    if conversation_exists or messages:
        state_snapshot = MagicMock()
        state_snapshot.values = {"messages": messages or [HumanMessage(content="Previous message")]}
        mock.aget_state.return_value = state_snapshot
    else:
        state_snapshot = MagicMock()
        state_snapshot.values = {"messages": []}
        mock.aget_state.return_value = state_snapshot

    # Setup invoke behavior
    if invoke_error:
        mock.ainvoke.side_effect = invoke_error
    else:
        mock.ainvoke.return_value = {
            "messages": [HumanMessage(content="User input"), AIMessage(content=response_message)],
            "next_action": next_action,
            "user_id": user_id,
        }

    # Setup checkpointer (needed for some tests)
    checkpointer = AsyncMock(return_value=None)  # Container for checkpointer methods
    mock.checkpointer = checkpointer

    return mock


def create_behavioral_llm_provider(
    *,
    response: str = "This is a test response.",
    latency_ms: int = 100,
    error: Exception | None = None,
    provider: str = "openai",
):
    """
    Create behavioral mock for LLM provider.

    Tests BEHAVIOR: "LLM returns response to prompt"
    NOT implementation: "LiteLLM uses specific API endpoint"

    Args:
        response: LLM response text
        latency_ms: Simulated latency in milliseconds
        error: Exception to raise (for error testing)
        provider: Provider name (openai, anthropic, etc.)

    Returns:
        Mock LLM provider that behaves like real provider

    Example:
        >>> # Test: LLM fallback on primary failure
        >>> primary = create_behavioral_llm_provider(
        ...     error=ConnectionError("API unavailable")
        ... )
        >>> fallback = create_behavioral_llm_provider(
        ...     response="Fallback response"
        ... )
        >>> # Test fallback logic works
        >>> result = await try_with_fallback(primary, fallback)
        >>> assert result == "Fallback response"

    Replaces:
        @patch("mcp_server_langgraph.core.llm.litellm_provider.completion")
        def test_llm(mock_completion):
            # 10+ lines of setup...
    """
    import asyncio

    mock = AsyncMock(return_value=None)  # Container for configured methods

    async def invoke_with_latency(*args, **kwargs):
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000)
        if error:
            raise error
        return response

    mock.invoke = invoke_with_latency
    mock.ainvoke = invoke_with_latency
    mock.provider = provider

    return mock


def create_behavioral_checkpointer(*, has_checkpoint: bool = True, checkpoint_data: dict | None = None):
    """
    Create behavioral mock for conversation checkpointer.

    Tests BEHAVIOR: "Checkpointer saves/loads conversation state"
    NOT implementation: "Redis checkpointer uses specific key format"

    Args:
        has_checkpoint: Whether checkpoint exists
        checkpoint_data: Custom checkpoint data

    Returns:
        Mock checkpointer that behaves like real checkpointer

    Example:
        >>> # Test: Conversation resumes from checkpoint
        >>> checkpointer = create_behavioral_checkpointer(
        ...     has_checkpoint=True,
        ...     checkpoint_data={"messages": [HumanMessage("Previous")]}
        ... )
        >>> state = await checkpointer.aget(config)
        >>> assert state["messages"][0].content == "Previous"

        >>> # Test: New conversation has no checkpoint
        >>> checkpointer = create_behavioral_checkpointer(
        ...     has_checkpoint=False
        ... )
        >>> state = await checkpointer.aget(config)
        >>> assert state is None

    Replaces:
        @patch("mcp_server_langgraph.core.graph.RedisCheckpointer")
        def test_checkpoint(mock_checkpointer):
            # 10+ lines of setup...
    """
    from unittest.mock import MagicMock

    mock = AsyncMock(return_value=None)  # Container for checkpointer methods

    if has_checkpoint:
        checkpoint = MagicMock()
        checkpoint.data = checkpoint_data or {"messages": []}
        mock.aget.return_value = checkpoint
    else:
        mock.aget.return_value = None

    mock.aput = AsyncMock(return_value=None)  # Saving always succeeds

    return mock


# ==============================================================================
# FastAPI Test Client Helpers
# ==============================================================================


def verify_dependency_overrides(
    app_dependency_overrides: dict[Any, Any],
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
