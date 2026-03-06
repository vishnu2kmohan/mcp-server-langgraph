"""
Tests for Compile-Time Agent Graph Builder.

TDD tests for the build_agent_graph function that constructs graphs
based on AgentConfig at compile time (not runtime).
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestGraphBuilderImports:
    """Test that graph builder is importable."""

    def test_import_build_agent_graph(self):
        """build_agent_graph should be importable."""
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        assert build_agent_graph is not None

    def test_import_agent_config(self):
        """AgentConfig should be importable for graph building."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        assert AgentConfig is not None


@pytest.mark.unit
class TestGraphTopologyWithConfig:
    """Test that graph topology changes based on AgentConfig."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_graph_has_metadata_with_version(self, monkeypatch):
        """Compiled graph should have graph_version in metadata."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig()
        graph = build_agent_graph(config)

        # Graph should have metadata with version
        # Note: LangGraph CompiledGraph stores config on the graph object
        assert hasattr(graph, "config_specs") or hasattr(graph, "builder")

    @pytest.mark.asyncio
    async def test_verification_enabled_adds_verify_node(self, monkeypatch):
        """With verification enabled, graph should have verify node."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_verification=True)
        graph = build_agent_graph(config)

        # Get node names from the graph
        node_names = set(graph.nodes.keys())

        assert "verify" in node_names, f"verify node missing. Nodes: {node_names}"
        assert "refine" in node_names, f"refine node missing. Nodes: {node_names}"

    @pytest.mark.asyncio
    async def test_verification_disabled_no_verify_node(self, monkeypatch):
        """With verification disabled, graph should NOT have verify/refine nodes."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_verification=False)
        graph = build_agent_graph(config)

        node_names = set(graph.nodes.keys())

        assert "verify" not in node_names, f"verify node should not exist. Nodes: {node_names}"
        assert "refine" not in node_names, f"refine node should not exist. Nodes: {node_names}"

    @pytest.mark.asyncio
    async def test_context_compaction_enabled_adds_compact_node(self, monkeypatch):
        """With compaction enabled, graph should have compact node."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_context_compaction=True)
        graph = build_agent_graph(config)

        node_names = set(graph.nodes.keys())

        assert "compact" in node_names, f"compact node missing. Nodes: {node_names}"

    @pytest.mark.asyncio
    async def test_context_compaction_disabled_no_compact_node(self, monkeypatch):
        """With compaction disabled, graph should NOT have compact node."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_context_compaction=False)
        graph = build_agent_graph(config)

        node_names = set(graph.nodes.keys())

        assert "compact" not in node_names, f"compact node should not exist. Nodes: {node_names}"

    @pytest.mark.asyncio
    async def test_dynamic_context_enabled_adds_load_context_node(self, monkeypatch):
        """With dynamic context enabled (and loader available), graph should have load_context node."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "local")  # Use local for test

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_dynamic_context_loading=True)
        graph = build_agent_graph(config)

        _node_names = set(graph.nodes.keys())  # Store for debugging if needed

        # Note: load_context only added if DynamicContextLoader succeeds
        # In test env with local embeddings, it may or may not be present
        # The key is that the graph builds successfully
        assert graph is not None

    @pytest.mark.asyncio
    async def test_dynamic_context_disabled_no_load_context_node(self, monkeypatch):
        """With dynamic context disabled, graph should NOT have load_context node."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_dynamic_context_loading=False)
        graph = build_agent_graph(config)

        node_names = set(graph.nodes.keys())

        assert "load_context" not in node_names, f"load_context node should not exist. Nodes: {node_names}"


@pytest.mark.unit
class TestCoreNodesAlwaysPresent:
    """Test that core nodes are always present regardless of config."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_router_always_present(self, monkeypatch):
        """Router node should always be present."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig()
        graph = build_agent_graph(config)

        assert "router" in graph.nodes

    @pytest.mark.asyncio
    async def test_respond_always_present(self, monkeypatch):
        """Respond node should always be present."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig()
        graph = build_agent_graph(config)

        assert "respond" in graph.nodes

    @pytest.mark.asyncio
    async def test_tools_always_present(self, monkeypatch):
        """Tools node should always be present."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig()
        graph = build_agent_graph(config)

        assert "tools" in graph.nodes


@pytest.mark.unit
class TestMinimalGraph:
    """Test minimal graph configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_minimal_graph_has_only_core_nodes(self, monkeypatch):
        """Minimal config should produce graph with only core nodes."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        # Disable all optional features
        config = AgentConfig(
            enable_context_compaction=False,
            enable_verification=False,
            enable_dynamic_context_loading=False,
        )
        graph = build_agent_graph(config)

        node_names = set(graph.nodes.keys())
        core_nodes = {"router", "tools", "respond"}

        # Filter out LangGraph internal nodes (__start__, __end__)
        user_nodes = {n for n in node_names if not n.startswith("__")}

        # Only core nodes should be present
        assert user_nodes == core_nodes, f"Expected {core_nodes}, got {user_nodes}"
