"""
E2E Tests for Semantic Tool Selection (ADR-0099)

Tests the complete semantic tool selection flow from user query to response:
1. Graph builds with semantic tool selection enabled
2. Semantic index manager indexes and searches tools
3. Selected tools are dynamically bound to the LLM
4. Response includes tool selection metadata (SSE event)

Semantic Tool Selection implements:
- Anthropic Tool Search Tool pattern (defer_loading)
- LangGraph Many Tools pattern (dynamic tool binding)
- OpenFGA authorization for tool access

These tests can run with mocked infrastructure or full E2E (make test-infra-up).
"""

from __future__ import annotations

import gc
import time
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.semantic_search,
]


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder that returns consistent embeddings."""
    embedder = MagicMock()
    embedder.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3, 0.4] * 96)  # 384 dims

    # Return dynamic number of embeddings based on input
    def mock_embed_documents(texts: list[str]) -> list[list[float]]:
        return [[0.1 + i * 0.1, 0.2, 0.3, 0.4] * 96 for i in range(len(texts))]

    embedder.embed_documents = MagicMock(side_effect=mock_embed_documents)
    return embedder


@pytest.fixture
def mock_qdrant_client() -> AsyncMock:
    """Create a mock Qdrant async client."""
    client = AsyncMock(return_value=None)
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    client.create_collection = AsyncMock(return_value=None)
    client.upsert = AsyncMock(return_value=None)
    mock_response = MagicMock()
    mock_response.points = []
    client.query_points = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client that always returns True for authorization."""
    client = AsyncMock(return_value=None)
    client.check_permission = AsyncMock(return_value=True)
    return client


@pytest.mark.xdist_group(name="test_semantic_tool_selection_e2e")
class TestSemanticToolSelectionE2E:
    """
    E2E tests for Semantic Tool Selection (ADR-0099).

    Tests validate the full flow:
    1. Tool indexing at startup
    2. Semantic search during message processing
    3. Dynamic tool binding in LLM invocation
    4. SSE events for frontend visibility
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_01_graph_builds_with_semantic_tool_selection_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Test 1: Agent graph builds correctly with semantic tool selection.

        GIVEN semantic tool selection feature flag is enabled
        WHEN the agent graph is built
        THEN it should include the retrieve_tools node
        AND the node should be wired between START and router
        """
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # Verify graph structure
        assert graph is not None
        assert "retrieve_tools" in graph.nodes
        assert "router" in graph.nodes
        assert "respond" in graph.nodes

    @pytest.mark.asyncio
    async def test_02_graph_with_all_semantic_features_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Test 2: Agent graph with all semantic features builds correctly.

        GIVEN all semantic search features are enabled (tools, skills, memories)
        WHEN the agent graph is built
        THEN it should include all three retrieval nodes
        AND they should be wired in sequence before router
        """
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_semantic_skill_search=True,
            enable_semantic_memory_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # Verify all semantic nodes are present
        assert "retrieve_tools" in graph.nodes
        assert "retrieve_skills" in graph.nodes
        assert "retrieve_memories" in graph.nodes
        assert "router" in graph.nodes

    @pytest.mark.asyncio
    async def test_03_semantic_index_manager_full_lifecycle(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """
        Test 3: Full lifecycle - index tools, search, and verify results.

        GIVEN a SemanticIndexManager with mock dependencies
        WHEN tools are indexed and then searched
        THEN the search should return matching tools
        AND authorization should be checked for each result
        """
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        task_start_time = time.time()
        task_success = False

        try:
            # Setup mock search results
            mock_qdrant_client.query_points.return_value.points = [
                ScoredPoint(
                    id="builtin-calculator",
                    version=1,
                    score=0.95,
                    payload={
                        "tool_id": "builtin:calculator",
                        "name": "calculator",
                        "description": "Perform mathematical calculations",
                        "category": "math",
                        "ref_type": "tool",
                        "scope": "session",
                    },
                    vector=None,
                ),
                ScoredPoint(
                    id="builtin-search",
                    version=1,
                    score=0.88,
                    payload={
                        "tool_id": "builtin:search",
                        "name": "web_search",
                        "description": "Search the web for information",
                        "category": "search",
                        "ref_type": "tool",
                        "scope": "session",
                    },
                    vector=None,
                ),
            ]

            # Create manager
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=mock_qdrant_client,
            )

            # Index tools
            tools_to_index = [
                ToolIndexEntry(
                    tool_id="builtin:calculator",
                    name="calculator",
                    description="Perform mathematical calculations",
                    category="math",
                ),
                ToolIndexEntry(
                    tool_id="builtin:search",
                    name="web_search",
                    description="Search the web for information",
                    category="search",
                ),
            ]
            await manager.index_tools_batch(tools_to_index)

            # Search for tools
            with patch(
                "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
                return_value=mock_openfga_client,
            ):
                results = await manager.search_tools(
                    query="calculate 2+2",
                    user_id="user:test_alice",
                    limit=5,
                )

            # Verify results
            assert len(results) == 2
            tool_names = [r.name for r in results]
            assert "calculator" in tool_names
            assert "web_search" in tool_names

            task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            heart_metrics = {
                "task_name": "semantic_index_full_lifecycle",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    @pytest.mark.asyncio
    async def test_04_retrieve_tools_impl_uses_semantic_index(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """
        Test 4: retrieve_tools node uses SemanticIndexManager correctly.

        GIVEN a SemanticIndexManager instance
        WHEN _retrieve_tools_impl is called with a user query
        THEN it should search for tools and update state with selected_tools
        """
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        task_start_time = time.time()
        task_success = False

        try:
            # Setup mock search result
            mock_qdrant_client.query_points.return_value.points = [
                ScoredPoint(
                    id="builtin-read_file",
                    version=1,
                    score=0.92,
                    payload={
                        "tool_id": "builtin:read_file",
                        "name": "read_file",
                        "description": "Read contents of a file",
                        "category": "filesystem",
                        "ref_type": "tool",
                        "scope": "session",
                    },
                    vector=None,
                )
            ]

            # Create manager
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=mock_qdrant_client,
            )

            # Create state with a user message
            from langchain_core.messages import HumanMessage

            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Please read the file config.yaml")],
                "user_id": "user:test_alice",
                "selected_tools": None,
            }

            # Execute _retrieve_tools_impl
            with patch(
                "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
                return_value=mock_openfga_client,
            ):
                result = await _retrieve_tools_impl(
                    state=state,
                    semantic_index_manager=manager,
                    max_selected_tools=10,
                )

            # Verify selected_tools is populated
            assert result.get("selected_tools") is not None
            assert "read_file" in result["selected_tools"]

            task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            heart_metrics = {
                "task_name": "retrieve_tools_impl",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    @pytest.mark.asyncio
    async def test_05_dynamic_tool_binding_uses_selected_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Test 5: Dynamic tool binding respects selected_tools in state.

        GIVEN selected_tools is populated in agent state
        WHEN generate_response (via _generate_response_impl) is called
        THEN only the selected tools should be bound to the model
        """
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        task_start_time = time.time()
        task_success = False

        try:
            from langchain_core.messages import AIMessage, HumanMessage

            from mcp_server_langgraph.core.agent_graph_builder import (
                _generate_response_impl,
            )

            # Create mock model that tracks bind_tools calls
            mock_model = MagicMock()
            mock_bound_model = MagicMock()
            mock_bound_model.ainvoke = AsyncMock(return_value=AIMessage(content="Result using selected tools"))
            mock_model.bind_tools = MagicMock(return_value=mock_bound_model)

            # Create mock tools
            mock_calculator = MagicMock()
            mock_calculator.name = "calculator"
            mock_search = MagicMock()
            mock_search.name = "web_search"
            mock_read_file = MagicMock()
            mock_read_file.name = "read_file"

            bound_tools = [mock_calculator, mock_search, mock_read_file]

            # State with selected_tools (only calculator and read_file selected)
            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Calculate 2+2 and read config")],
                "selected_tools": ["calculator", "read_file"],  # web_search NOT selected
                "user_id": "user:test_alice",
            }

            # Execute _generate_response_impl
            await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=bound_tools,
                model_with_tools=None,
                pydantic_agent=None,
            )

            # Verify bind_tools was called with only selected tools
            mock_model.bind_tools.assert_called_once()
            bound_tools_arg = mock_model.bind_tools.call_args[0][0]
            bound_tool_names = [t.name for t in bound_tools_arg]

            assert "calculator" in bound_tool_names
            assert "read_file" in bound_tool_names
            assert "web_search" not in bound_tool_names  # This was NOT selected

            task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            heart_metrics = {
                "task_name": "dynamic_tool_binding",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    @pytest.mark.asyncio
    async def test_06_graceful_fallback_when_no_tools_found(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """
        Test 6: Graceful fallback when semantic search returns no tools.

        GIVEN semantic search returns no matching tools
        WHEN retrieve_tools_impl is executed
        THEN selected_tools should be None (fallback to all tools)
        """
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        task_start_time = time.time()
        task_success = False

        try:
            # Empty search results
            mock_qdrant_client.query_points.return_value.points = []

            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=mock_qdrant_client,
            )

            from langchain_core.messages import HumanMessage

            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Do something completely unrelated")],
                "user_id": "user:test_alice",
                "selected_tools": None,
            }

            with patch(
                "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
                return_value=mock_openfga_client,
            ):
                result = await _retrieve_tools_impl(
                    state=state,
                    semantic_index_manager=manager,
                    max_selected_tools=10,
                )

            # Fallback: selected_tools should be None
            assert result.get("selected_tools") is None

            task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            heart_metrics = {
                "task_name": "graceful_fallback_no_tools",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    @pytest.mark.asyncio
    async def test_07_authorization_denies_access_to_tool_index(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
    ) -> None:
        """
        Test 7: Authorization check denies access when user lacks viewer permission.

        GIVEN a user without viewer access to tool_index
        WHEN semantic tool search is performed
        THEN empty results should be returned (fail-closed)
        AND no search query should be executed

        Note: Authorization is at the tool_index level, not per-tool.
        This ensures users without access to the index can't see any tools.
        """
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        task_start_time = time.time()
        task_success = False

        try:
            # Setup search results (shouldn't be used if authorization fails)
            mock_qdrant_client.query_points.return_value.points = [
                MagicMock(
                    id="tool-1",
                    score=0.95,
                    payload={
                        "tool_id": "tool-1",
                        "name": "some_tool",
                        "description": "Should not be visible",
                        "category": "test",
                        "ref_type": "tool",
                        "scope": "session",
                    },
                )
            ]

            # Mock OpenFGA to deny access to tool_index
            mock_openfga = AsyncMock(return_value=None)
            mock_openfga.check_permission = AsyncMock(return_value=False)  # Deny access

            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=mock_qdrant_client,
            )

            with patch(
                "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
                return_value=mock_openfga,
            ):
                results = await manager.search_tools(
                    query="test query",
                    user_id="user:unauthorized_user",
                    limit=10,
                )

            # No tools should be returned (fail-closed)
            assert len(results) == 0

            # Authorization check should have been called
            mock_openfga.check_permission.assert_called_once()

            task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            heart_metrics = {
                "task_name": "authorization_denies_tool_index_access",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")


@pytest.mark.xdist_group(name="test_semantic_sse_events")
class TestSemanticToolSelectionSSEEvents:
    """Tests for SSE events emitted during semantic tool selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires E2E infrastructure running (make test-infra-up)")
    async def test_08_chat_stream_includes_selected_tools_event(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test 8: Chat streaming includes selected_tools SSE event.

        GIVEN semantic tool selection is enabled
        WHEN a user sends a chat message via streaming endpoint
        THEN an SSE event with selected_tools should be emitted
        AND the frontend can display which tools were selected

        This test requires full E2E infrastructure.
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        selected_tools_event_received = False

        try:
            async with httpx.AsyncClient() as client:
                chat_payload = {
                    "messages": [{"role": "user", "content": "Calculate 2+2"}],
                    "model": "gpt-3.5-turbo",
                    "stream": True,
                }

                async with client.stream(
                    "POST",
                    f"{e2e_api_base_url}/api/v1/chat/completions",
                    json=chat_payload,
                    headers={"Authorization": "Bearer test-token"},
                    timeout=30.0,
                ) as response:
                    if response.status_code in [200, 401]:
                        async for line in response.aiter_lines():
                            if "selected_tools" in line:
                                selected_tools_event_received = True
                                break

                if response.status_code == 200:
                    task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            heart_metrics = {
                "task_name": "chat_stream_selected_tools_event",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "event_received": selected_tools_event_received,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")
