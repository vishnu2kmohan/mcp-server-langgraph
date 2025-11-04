"""
Test Helper Functions

This module provides convenient helper functions for creating test instances
of agents, servers, settings, and other components.

Usage:
    from mcp_server_langgraph.core.test_helpers import (
        create_test_agent,
        create_test_server,
        create_test_settings,
        create_test_container,
        create_mock_llm_response,
        create_mock_mcp_request,
    )

    # In your tests
    def test_my_feature():
        agent = create_test_agent()
        assert agent.invoke({"message": "test"}) is not None
"""

from __future__ import annotations

from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from mcp_server_langgraph.core.container import ApplicationContainer, create_test_container as _create_container
from mcp_server_langgraph.core.config import Settings


# ==============================================================================
# Container Helpers
# ==============================================================================


def create_test_container(settings: Optional[Settings] = None) -> ApplicationContainer:
    """
    Create a test container with no-op providers.

    This is a convenience wrapper around the container module's create_test_container.

    Args:
        settings: Optional custom settings

    Returns:
        ApplicationContainer configured for testing

    Example:
        container = create_test_container()
        agent = create_agent(container.settings, container.get_telemetry())
    """
    return _create_container(settings=settings)


# ==============================================================================
# Settings Helpers
# ==============================================================================


def create_test_settings(**kwargs) -> Settings:
    """
    Create test settings with safe defaults.

    Args:
        **kwargs: Override any settings attributes

    Returns:
        Settings configured for testing

    Example:
        settings = create_test_settings(model_name="test-model", log_level="ERROR")
    """
    defaults = {
        "environment": "test",
        "log_level": "DEBUG",
        "jwt_secret_key": "test-secret-key-for-testing-only",
        "hipaa_integrity_secret": "test-hipaa-secret-for-testing-only",
        "openfga_store_id": "",
        "openfga_model_id": "",
        "anthropic_api_key": "test-anthropic-key",
        "enable_tracing": False,
        "enable_metrics": False,
    }
    defaults.update(kwargs)
    return Settings(**defaults)


# ==============================================================================
# Agent Helpers
# ==============================================================================


def create_test_agent(settings: Optional[Settings] = None, container: Optional[ApplicationContainer] = None) -> Any:
    """
    Create a test agent instance.

    NOTE: Currently uses the singleton get_agent_graph() function.
    After refactoring agent.py to support dependency injection, this will
    create agents using the container pattern.

    Args:
        settings: Optional custom settings (if container not provided)
        container: Optional container to use for dependencies

    Returns:
        Agent instance (LangGraph CompiledStateGraph)

    Example:
        agent = create_test_agent()
        result = agent.invoke({"messages": [{"role": "user", "content": "test"}]})
    """
    # Get container (for future use)
    if container is None:
        container = create_test_container(settings=settings)

    # Import agent creation function
    # NOTE: get_agent_graph() is currently a singleton, doesn't accept parameters
    # TODO: After Phase 3 refactoring, pass container.settings
    from mcp_server_langgraph.core.agent import get_agent_graph

    # For now, use the global singleton
    # This will be improved in Phase 3 when we refactor agent.py
    agent = get_agent_graph()

    return agent


# ==============================================================================
# Server Helpers
# ==============================================================================


def create_test_server(container: Optional[ApplicationContainer] = None) -> Any:
    """
    Create a test MCP server instance.

    Args:
        container: Optional container to use for dependencies

    Returns:
        MCP server instance

    Example:
        server = create_test_server()
        # Use server in tests
    """
    if container is None:
        container = create_test_container()

    # For now, return a mock server
    # TODO: When we refactor server to use container, this will create a real test server
    mock_server = MagicMock()
    mock_server.server = MagicMock()
    mock_server.auth = container.get_auth()
    mock_server.settings = container.settings

    return mock_server


# ==============================================================================
# Mock Helpers
# ==============================================================================


def create_mock_llm_response(content: str = "Test response", model: str = "test-model", **kwargs) -> Any:
    """
    Create a mock LLM response compatible with LangChain.

    Args:
        content: Response content
        model: Model name
        **kwargs: Additional response attributes

    Returns:
        Mock message object

    Example:
        response = create_mock_llm_response(content="Hello, world!")
    """
    from langchain_core.messages import AIMessage

    return AIMessage(content=content, response_metadata={"model": model, **kwargs})


def create_mock_llm_stream(chunks: List[str]) -> List[Any]:
    """
    Create a mock LLM stream response.

    Args:
        chunks: List of content chunks to stream

    Returns:
        List of mock chunk objects

    Example:
        stream = create_mock_llm_stream(["Hello", " ", "World"])
        for chunk in stream:
            print(chunk.content)
    """
    from langchain_core.messages import AIMessageChunk

    return [AIMessageChunk(content=chunk) for chunk in chunks]


def create_mock_mcp_request(
    method: str = "tools/call", params: Optional[Dict[str, Any]] = None, request_id: int = 1
) -> Dict[str, Any]:
    """
    Create a mock MCP JSON-RPC request.

    Args:
        method: JSON-RPC method name
        params: Method parameters
        request_id: Request ID

    Returns:
        Dict representing MCP request

    Example:
        request = create_mock_mcp_request(
            method="tools/call",
            params={"name": "chat", "arguments": {"message": "test"}}
        )
    """
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def create_mock_jwt_token(user_id: str = "test-user", expiry_hours: int = 1) -> str:
    """
    Create a mock JWT token for testing.

    Args:
        user_id: User ID to include in token
        expiry_hours: Hours until token expires

    Returns:
        JWT token string

    Example:
        token = create_mock_jwt_token(user_id="alice")
        # Use token in auth tests
    """
    import jwt

    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


# ==============================================================================
# Assertion Helpers
# ==============================================================================


def assert_valid_mcp_response(response: Dict[str, Any]) -> None:
    """
    Assert that a response is a valid MCP JSON-RPC response.

    Args:
        response: Response to validate

    Raises:
        AssertionError: If response is invalid

    Example:
        response = server.handle_request(request)
        assert_valid_mcp_response(response)
    """
    assert "jsonrpc" in response
    assert response["jsonrpc"] == "2.0"
    assert "id" in response
    assert ("result" in response) or ("error" in response)


def assert_valid_agent_state(state: Dict[str, Any]) -> None:
    """
    Assert that a state dict is a valid LangGraph agent state.

    Args:
        state: State to validate

    Raises:
        AssertionError: If state is invalid

    Example:
        state = agent.invoke({"messages": [...]})
        assert_valid_agent_state(state)
    """
    assert "messages" in state
    assert isinstance(state["messages"], list)
