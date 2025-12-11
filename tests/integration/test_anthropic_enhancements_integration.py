import gc
import os

"\nIntegration tests for Anthropic Best Practices Enhancements\n\nTests all enhancements working together:\n1. Just-in-Time Context Loading (Dynamic Context Loader)\n2. Parallel Tool Execution\n3. Enhanced Structured Note-Taking (LLM Extraction)\n4. Full agentic loop integration\n\nRequires:\n- Qdrant running (for dynamic context)\n- Redis running (for checkpointing)\n- LLM configured (for extraction and agent)\n"
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from mcp_server_langgraph.core.agent import create_agent_graph
from mcp_server_langgraph.core.context_manager import ContextManager
from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader, search_and_load_context
from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation
from tests.helpers.async_mock_helpers import configured_async_mock

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mock_settings():
    """Mock settings with all enhancements enabled"""
    with patch("mcp_server_langgraph.core.config.settings") as mock:
        mock.enable_dynamic_context_loading = True
        mock.enable_parallel_execution = True
        mock.enable_llm_extraction = True
        mock.enable_context_compaction = True
        mock.enable_verification = True
        mock.qdrant_url = "localhost"
        mock.qdrant_port = 6333
        mock.qdrant_collection_name = "test_integration"
        mock.dynamic_context_max_tokens = 2000
        mock.dynamic_context_top_k = 3
        mock.embedding_model = "all-MiniLM-L6-v2"
        mock.context_cache_size = 10
        mock.max_parallel_tools = 5
        mock.max_refinement_attempts = 3
        mock.checkpoint_backend = "memory"
        mock.model_name = "claude-sonnet-4-5-20250929"
        mock.model_provider = "anthropic"
        mock.temperature = 0.7
        yield mock


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_anthropic_enhancements_integration_tests")
@pytest.mark.skipif(
    not (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_API_KEY")),
    reason="Google credentials not set - requires GOOGLE_APPLICATION_CREDENTIALS (Vertex AI) or GOOGLE_API_KEY (Gemini)",
)
class TestDynamicContextIntegration:
    """Test dynamic context loading integration - requires Google embeddings"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_search_load_workflow(self, qdrant_client):
        """Test complete workflow: index → search → load"""
        from os import getenv

        qdrant_url = getenv("QDRANT_URL", "localhost")
        qdrant_port = int(getenv("QDRANT_PORT", "6333"))
        loader = DynamicContextLoader(
            qdrant_url=qdrant_url, qdrant_port=qdrant_port, collection_name="test_integration_contexts"
        )
        try:
            contexts_to_index = [
                {
                    "ref_id": "python_basics",
                    "content": "Python is a high-level programming language with dynamic typing. It supports multiple paradigms including procedural, object-oriented, and functional.",
                    "ref_type": "documentation",
                    "summary": "Python language basics",
                    "metadata": {"topic": "programming", "difficulty": "beginner"},
                },
                {
                    "ref_id": "python_async",
                    "content": "Python's asyncio library provides infrastructure for asynchronous I/O. Use async/await syntax for coroutines. Great for concurrent network operations.",
                    "ref_type": "documentation",
                    "summary": "Python async programming",
                    "metadata": {"topic": "programming", "difficulty": "intermediate"},
                },
                {
                    "ref_id": "docker_intro",
                    "content": "Docker is a containerization platform that packages applications with their dependencies. Uses images and containers for consistent deployment across environments.",
                    "ref_type": "documentation",
                    "summary": "Docker introduction",
                    "metadata": {"topic": "devops", "difficulty": "beginner"},
                },
            ]
            for ctx in contexts_to_index:
                await loader.index_context(**ctx)
            python_results = await loader.semantic_search(
                query="How do I write asynchronous code in Python?", top_k=2, min_score=0.5
            )
            assert len(python_results) >= 1
            assert any(r.ref_id == "python_async" for r in python_results)
            loaded = await loader.load_batch(python_results, max_tokens=1000)
            assert len(loaded) >= 1
            async_ctx = next((c for c in loaded if c.ref_id == "python_async"), None)
            assert async_ctx is not None
            assert "asyncio" in async_ctx.content
        finally:
            try:
                qdrant_client.delete_collection("test_integration_contexts")
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_progressive_discovery(self, qdrant_client):
        """Test progressive discovery pattern"""
        from os import getenv

        qdrant_url = getenv("QDRANT_URL", "localhost")
        qdrant_port = int(getenv("QDRANT_PORT", "6333"))
        loader = DynamicContextLoader(
            qdrant_url=qdrant_url, qdrant_port=qdrant_port, collection_name="test_integration_progressive"
        )
        try:
            await loader.index_context(
                ref_id="ml_overview",
                content="Machine learning is a subset of AI focused on learning from data",
                ref_type="documentation",
                summary="ML overview",
            )
            await loader.index_context(
                ref_id="neural_networks",
                content="Neural networks are ML models inspired by biological neurons",
                ref_type="documentation",
                summary="Neural networks intro",
            )
            await loader.index_context(
                ref_id="transformers",
                content="Transformers are neural network architectures using self-attention mechanisms",
                ref_type="documentation",
                summary="Transformer architecture",
            )
            round1 = await loader.semantic_search("machine learning", top_k=1)
            assert len(round1) >= 1
            round2 = await loader.semantic_search("neural network architectures", top_k=1)
            assert len(round2) >= 1
            round3 = await loader.semantic_search("transformer attention mechanism", top_k=1)
            assert len(round3) >= 1
        finally:
            try:
                qdrant_client.delete_collection("test_integration_progressive")
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_anthropic_enhancements_integration_tests")
class TestParallelExecutionIntegration:
    """Test parallel tool execution integration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_real_tool_parallel_execution(self):
        """Test parallel execution with simulated real tools"""
        executor = ParallelToolExecutor(max_parallelism=3)
        execution_log = []

        async def simulated_tool_executor(tool_name: str, arguments: dict):
            """Simulate various tool execution times - matches ParallelToolExecutor signature"""
            tool_delays = {
                "fetch_user": 0.1,
                "fetch_orders": 0.15,
                "calculate_total": 0.05,
                "apply_discount": 0.05,
                "send_email": 0.2,
            }
            delay = tool_delays.get(tool_name, 0.1)
            execution_log.append(("start", tool_name, asyncio.get_event_loop().time()))
            await asyncio.sleep(delay)
            execution_log.append(("end", tool_name, asyncio.get_event_loop().time()))
            return {"status": "success", "data": f"result_from_{tool_name}"}

        invocations = [
            ToolInvocation(tool_name="fetch_user", arguments={"user_id": "123"}, invocation_id="inv_user", dependencies=[]),
            ToolInvocation(
                tool_name="fetch_orders", arguments={"user_id": "123"}, invocation_id="inv_orders", dependencies=[]
            ),
            ToolInvocation(
                tool_name="calculate_total",
                arguments={"orders": "$inv_orders.result"},
                invocation_id="inv_calc",
                dependencies=["inv_orders"],
            ),
            ToolInvocation(
                tool_name="apply_discount",
                arguments={"total": "$inv_calc.result", "user": "$inv_user.result"},
                invocation_id="inv_discount",
                dependencies=["inv_calc", "inv_user"],
            ),
            ToolInvocation(
                tool_name="send_email",
                arguments={"amount": "$inv_discount.result"},
                invocation_id="inv_email",
                dependencies=["inv_discount"],
            ),
        ]
        results = await executor.execute_parallel(invocations, simulated_tool_executor)
        assert len(results) == 5
        assert all(r.error is None for r in results)
        user_start = next((t for e, n, t in execution_log if e == "start" and n == "fetch_user"))
        orders_start = next((t for e, n, t in execution_log if e == "start" and n == "fetch_orders"))
        assert abs(user_start - orders_start) < 0.05


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_anthropic_enhancements_integration_tests")
class TestContextManagerIntegration:
    """Test context manager LLM extraction integration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_compaction_then_extraction(self):
        """Test compaction followed by extraction"""
        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model") as mock_llm_factory:
            mock_llm = configured_async_mock(return_value=None)

            def mock_ainvoke(messages):
                """Mock ainvoke that handles both list and string inputs"""
                if isinstance(messages, list):
                    prompt_text = str(messages)
                else:
                    prompt_text = str(messages)
                response = MagicMock()
                if "Extract and categorize" in prompt_text or "DECISIONS" in prompt_text:
                    response.content = "DECISIONS:\n- Implement feature X\n\nREQUIREMENTS:\n- Must support async operations\n\nFACTS:\n- Current system handles 1K RPS\n\nACTION_ITEMS:\n- Write implementation plan\n\nISSUES:\n- None\n\nPREFERENCES:\n- Use Python for backend\n"
                else:
                    response.content = "Summary of conversation: User requested feature X, discussed implementation."
                return response

            mock_llm.ainvoke = AsyncMock(side_effect=lambda msg: mock_ainvoke(msg))
            mock_llm_factory.return_value = mock_llm
            manager = ContextManager(compaction_threshold=500, target_after_compaction=300, recent_message_count=2)
            messages = [
                HumanMessage(content="Let's implement feature X"),
                SystemMessage(content="Analyzing requirements"),
                HumanMessage(content="We decided this should be async"),
                SystemMessage(content="Noted"),
                HumanMessage(content="Current system handles 1K RPS"),
                SystemMessage(content="Understood"),
                HumanMessage(content="We need to write an implementation plan"),
                SystemMessage(content="I'll help with that"),
                HumanMessage(content="I prefer using Python for the backend"),
            ]
            compaction_result = await manager.compact_conversation(messages)
            assert compaction_result.compression_ratio <= 1.0
            assert len(compaction_result.compacted_messages) <= len(messages)
            key_info = await manager.extract_key_information_llm(compaction_result.compacted_messages)
            assert len(key_info["decisions"]) >= 1
            assert len(key_info["requirements"]) >= 1
            assert len(key_info["action_items"]) >= 1


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_anthropic_enhancements_integration_tests")
class TestFullAgentIntegration:
    """Test full agent with all enhancements enabled"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not (os.getenv("ANTHROPIC_API_KEY") and os.getenv("RUN_FULL_INTEGRATION_TESTS")),
        reason="Requires full infrastructure (Qdrant, Redis, LLM) - set RUN_FULL_INTEGRATION_TESTS=1",
    )
    @pytest.mark.asyncio
    async def test_agent_with_dynamic_context(self, mock_settings, integration_test_env):
        """
        Test agent graph with dynamic context loading.

        Requires:
        - ANTHROPIC_API_KEY environment variable
        - RUN_FULL_INTEGRATION_TESTS=1
        - Docker infrastructure (Qdrant, Redis) via integration_test_env fixture
        """
        agent = create_agent_graph()
        state = {
            "messages": [HumanMessage(content="How do I implement async code in Python?")],
            "next_action": "respond",
            "user_id": "test_user",
            "request_id": "test_req_123",
            "routing_confidence": None,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": None,
            "user_request": None,
        }
        config = {"configurable": {"thread_id": "test_thread_1"}}
        result = await agent.ainvoke(state, config=config)
        assert "messages" in result
        assert len(result["messages"]) > 1
        system_messages = [m for m in result["messages"] if isinstance(m, SystemMessage)]
        assert len(system_messages) > 0

    @pytest.mark.skipif(
        not (os.getenv("ANTHROPIC_API_KEY") and os.getenv("RUN_FULL_INTEGRATION_TESTS")),
        reason="Requires full infrastructure - set RUN_FULL_INTEGRATION_TESTS=1 and ANTHROPIC_API_KEY",
    )
    @pytest.mark.asyncio
    async def test_agent_with_verification_loop(self, mock_settings, integration_test_env):
        """
        Test agent with verification and refinement.

        Requires full infrastructure and LLM API access.
        """
        agent = create_agent_graph()
        state = {
            "messages": [
                HumanMessage(
                    content="Write a comprehensive guide to implementing a production-ready microservices architecture"
                )
            ],
            "next_action": "respond",
            "user_id": "test_user",
            "request_id": "test_req_456",
            "routing_confidence": None,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": 0,
            "user_request": None,
        }
        config = {"configurable": {"thread_id": "test_thread_2"}}
        result = await agent.ainvoke(state, config=config)
        assert "verification_passed" in result
        assert "verification_score" in result
        if not result["verification_passed"]:
            assert result.get("refinement_attempts", 0) > 0


@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_anthropic_enhancements_integration_tests")
class TestEndToEndWorkflow:
    """Test complete end-to-end workflow with all enhancements"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("RUN_FULL_INTEGRATION_TESTS"),
        reason="Requires langchain-google-genai - set RUN_FULL_INTEGRATION_TESTS=1",
    )
    @pytest.mark.asyncio
    async def test_mock_full_workflow(self):
        """
        Test complete workflow with mocked external dependencies.

        Requires langchain-google-genai package to be installed.
        Runs when RUN_FULL_INTEGRATION_TESTS environment variable is set.
        """
        with patch("mcp_server_langgraph.core.dynamic_context_loader.QdrantClient") as mock_qdrant_cls:
            mock_qdrant = MagicMock()
            mock_qdrant.get_collections.return_value.collections = []
            mock_qdrant.search.return_value = [
                MagicMock(
                    id="ctx_1",
                    score=0.92,
                    payload={
                        "ref_id": "python_async_doc",
                        "ref_type": "documentation",
                        "summary": "Python async/await guide",
                        "metadata": {},
                    },
                )
            ]
            mock_qdrant_cls.return_value = mock_qdrant
            with patch("sentence_transformers.SentenceTransformer") as mock_st:
                mock_embedder = MagicMock()
                mock_embedder.encode.return_value = [0.1] * 384
                mock_st.return_value = mock_embedder
                loader = DynamicContextLoader(qdrant_url="localhost", qdrant_port=6333, collection_name="test")
                results = await search_and_load_context(
                    query="How to use async in Python?", loader=loader, top_k=3, max_tokens=1000
                )
                assert mock_qdrant.search.called
                assert mock_embedder.encode.called
        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model") as mock_llm_factory:
            mock_llm = configured_async_mock(return_value=None)

            async def mock_ainvoke(prompt):
                response = MagicMock()
                if "Extract and categorize" in prompt:
                    response.content = "DECISIONS:\n- Use asyncio for async operations\n\nREQUIREMENTS:\n- Support Python 3.10+\n\nFACTS:\n- asyncio is in stdlib\n\nACTION_ITEMS:\n- Write example code\n\nISSUES:\n- None\n\nPREFERENCES:\n- None\n"
                else:
                    response.content = "Summary of discussion"
                return response

            mock_llm.ainvoke = mock_ainvoke
            mock_llm_factory.return_value = mock_llm
            manager = ContextManager()
            messages = [
                HumanMessage(content="We decided to use asyncio for async operations"),
                HumanMessage(content="Must support Python 3.10+"),
            ]
            extraction = await manager.extract_key_information_llm(messages)
            assert len(extraction["decisions"]) >= 1
            assert len(extraction["requirements"]) >= 1
        executor = ParallelToolExecutor(max_parallelism=5)

        async def mock_tool(invocation):
            from mcp_server_langgraph.core.parallel_executor import ToolResult

            await asyncio.sleep(0.01)
            return ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                success=True,
                result="done",
                error=None,
                execution_time_ms=10.0,
            )

        invocations = [
            ToolInvocation(tool_name="tool1", arguments={}, invocation_id="inv1", dependencies=[]),
            ToolInvocation(tool_name="tool2", arguments={}, invocation_id="inv2", dependencies=[]),
            ToolInvocation(tool_name="tool3", arguments={}, invocation_id="inv3", dependencies=["inv1", "inv2"]),
        ]
        results = await executor.execute_parallel(invocations, mock_tool)
        assert len(results) == 3
        assert all(r.success for r in results)
        print("\n✅ End-to-end workflow test passed:")
        print("  - Dynamic context loading: ✓")
        print("  - LLM extraction: ✓")
        print("  - Parallel execution: ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
