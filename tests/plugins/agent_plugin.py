"""
Agent Fixtures Plugin.

Provides fixtures for LangGraph agent testing.
Extracted from conftest.py for better organization.
"""

import pytest
from langchain_core.messages import HumanMessage


@pytest.fixture
def mock_agent_state():
    """Mock LangGraph agent state."""
    return {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "next_action": "respond",
        "user_id": "alice",
        "request_id": "test-request-123",
    }


@pytest.fixture
def mock_agent_config():
    """Mock agent configuration for testing."""
    from mcp_server_langgraph.core.agent_config import AgentConfig

    return AgentConfig(
        enable_context_compaction=False,
        enable_verification=False,
        enable_dynamic_context_loading=False,
        enable_checkpointing=False,
    )


@pytest.fixture
def mock_minimal_agent_graph(mock_agent_config):
    """Create a minimal agent graph for fast testing."""
    from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

    return build_agent_graph(mock_agent_config)
