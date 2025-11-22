"""
Smoke tests for LangGraph Platform deployment package.

These tests ensure the deployment package can be imported and instantiated
without errors, preventing deployment-time failures.
"""

import gc
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def get_repo_root() -> Path:
    """
    Get repository root using marker file search.

    This is the recommended approach (vs hardcoded .parents[N] counts) to
    prevent path calculation errors when files move between directories.
    """
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


@pytest.mark.xdist_group(name="testlanggraphplatformdeployment")
class TestLangGraphPlatformDeployment:
    """Test suite for LangGraph Platform deployment package"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_can_import_agent_module(self):
        """Verify the agent module can be imported without errors"""
        import sys
        from pathlib import Path

        # Add deployments to path
        deployments_dir = get_repo_root() / "deployments"
        sys.path.insert(0, str(deployments_dir))

        try:
            from langgraph_platform import agent  # type: ignore

            assert agent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import agent module: {e}")
        finally:
            if str(deployments_dir) in sys.path:
                sys.path.remove(str(deployments_dir))

    def test_can_import_create_graph_function(self):
        """Verify the create_graph function can be imported"""
        import sys
        from pathlib import Path

        deployments_dir = get_repo_root() / "deployments"
        sys.path.insert(0, str(deployments_dir))

        try:
            from langgraph_platform.agent import create_graph  # type: ignore

            assert callable(create_graph)
        except ImportError as e:
            pytest.fail(f"Failed to import create_graph function: {e}")
        finally:
            if str(deployments_dir) in sys.path:
                sys.path.remove(str(deployments_dir))

    def test_can_import_graph_instance(self):
        """Verify the graph instance can be imported"""
        import sys
        from pathlib import Path

        deployments_dir = get_repo_root() / "deployments"
        sys.path.insert(0, str(deployments_dir))

        try:
            from langgraph_platform.agent import graph  # type: ignore

            assert graph is not None
        except ImportError as e:
            pytest.fail(f"Failed to import graph instance: {e}")
        finally:
            if str(deployments_dir) in sys.path:
                sys.path.remove(str(deployments_dir))

    def test_graph_has_required_attributes(self):
        """Verify the graph instance has expected LangGraph attributes"""
        import sys
        from pathlib import Path

        deployments_dir = get_repo_root() / "deployments"
        sys.path.insert(0, str(deployments_dir))

        try:
            from langgraph_platform.agent import graph  # type: ignore

            # LangGraph compiled graphs should have these attributes
            assert hasattr(graph, "invoke"), "Graph should have invoke method"
            assert hasattr(graph, "stream"), "Graph should have stream method"
        finally:
            if str(deployments_dir) in sys.path:
                sys.path.remove(str(deployments_dir))

    def test_agent_state_type_defined(self):
        """Verify AgentState TypedDict is properly defined"""
        import sys
        from pathlib import Path

        deployments_dir = get_repo_root() / "deployments"
        sys.path.insert(0, str(deployments_dir))

        try:
            from langgraph_platform.agent import AgentState  # type: ignore

            # Verify it has required fields
            assert hasattr(AgentState, "__annotations__")
            annotations = AgentState.__annotations__

            expected_fields = {"messages", "next_action", "user_id", "request_id"}
            actual_fields = set(annotations.keys())

            assert expected_fields == actual_fields, (
                f"AgentState should have fields {expected_fields}, " f"but has {actual_fields}"
            )
        finally:
            if str(deployments_dir) in sys.path:
                sys.path.remove(str(deployments_dir))

    def test_create_graph_returns_compiled_graph(self):
        """Verify create_graph returns a properly compiled LangGraph"""
        import sys
        from pathlib import Path

        deployments_dir = get_repo_root() / "deployments"
        sys.path.insert(0, str(deployments_dir))

        try:
            from langgraph_platform.agent import create_graph  # type: ignore

            graph = create_graph()

            # Should be a compiled graph with invoke/stream methods
            assert hasattr(graph, "invoke")
            assert hasattr(graph, "stream")
            assert callable(graph.invoke)
            assert callable(graph.stream)
        finally:
            if str(deployments_dir) in sys.path:
                sys.path.remove(str(deployments_dir))

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
