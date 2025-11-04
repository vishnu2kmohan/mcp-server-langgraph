"""
Smoke tests for LangGraph Platform deployment package.

These tests ensure the deployment package can be imported and instantiated
without errors, preventing deployment-time failures.
"""

import pytest


class TestLangGraphPlatformDeployment:
    """Test suite for LangGraph Platform deployment package"""

    def test_can_import_agent_module(self):
        """Verify the agent module can be imported without errors"""
        try:
            from deployments.langgraph_platform import agent
            assert agent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import agent module: {e}")

    def test_can_import_create_graph_function(self):
        """Verify the create_graph function can be imported"""
        try:
            from deployments.langgraph_platform.agent import create_graph
            assert callable(create_graph)
        except ImportError as e:
            pytest.fail(f"Failed to import create_graph function: {e}")

    def test_can_import_graph_instance(self):
        """Verify the graph instance can be imported"""
        try:
            from deployments.langgraph_platform.agent import graph
            assert graph is not None
        except ImportError as e:
            pytest.fail(f"Failed to import graph instance: {e}")

    def test_graph_has_required_attributes(self):
        """Verify the graph instance has expected LangGraph attributes"""
        from deployments.langgraph_platform.agent import graph

        # LangGraph compiled graphs should have these attributes
        assert hasattr(graph, "invoke"), "Graph should have invoke method"
        assert hasattr(graph, "stream"), "Graph should have stream method"

    def test_agent_state_type_defined(self):
        """Verify AgentState TypedDict is properly defined"""
        from deployments.langgraph_platform.agent import AgentState

        # Verify it has required fields
        assert hasattr(AgentState, "__annotations__")
        annotations = AgentState.__annotations__

        expected_fields = {"messages", "next_action", "user_id", "request_id"}
        actual_fields = set(annotations.keys())

        assert expected_fields == actual_fields, (
            f"AgentState should have fields {expected_fields}, "
            f"but has {actual_fields}"
        )

    def test_create_graph_returns_compiled_graph(self):
        """Verify create_graph returns a properly compiled LangGraph"""
        from deployments.langgraph_platform.agent import create_graph

        graph = create_graph()

        # Should be a compiled graph with invoke/stream methods
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")
        assert callable(graph.invoke)
        assert callable(graph.stream)

    @pytest.mark.integration
    def test_graph_can_process_simple_message(self):
        """
        Integration test: Verify graph can process a simple message.

        Note: This requires valid LLM configuration in settings.
        Skip if LLM_PROVIDER is not set.
        """
        import os

        if not os.getenv("LLM_PROVIDER"):
            pytest.skip("LLM_PROVIDER not configured, skipping integration test")

        from langchain_core.messages import HumanMessage
        from deployments.langgraph_platform.agent import graph

        initial_state = {
            "messages": [HumanMessage(content="Hello, how are you?")],
            "next_action": "",
            "user_id": "test-user",
            "request_id": "test-request-123",
        }

        try:
            result = graph.invoke(initial_state)

            # Verify we got a response
            assert "messages" in result
            assert len(result["messages"]) > 0

        except Exception as e:
            pytest.fail(f"Graph failed to process message: {e}")
