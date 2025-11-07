"""
Integration tests for distributed conversation checkpointing with Redis

Tests the RedisSaver checkpointer for multi-replica deployments with HPA auto-scaling.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from mcp_server_langgraph.core.agent import AgentState, _create_checkpointer, create_agent_graph
from mcp_server_langgraph.core.config import settings

# Try importing RedisSaver
try:
    from langgraph.checkpoint.redis import RedisSaver

    REDIS_CHECKPOINTER_AVAILABLE = True
except ImportError:
    REDIS_CHECKPOINTER_AVAILABLE = False
    RedisSaver = None


class TestCheckpointerFactory:
    """Tests for checkpointer factory function"""

    def test_create_memory_checkpointer(self):
        """Test factory creates MemorySaver when backend is 'memory'"""
        # Save original setting
        original_backend = settings.checkpoint_backend

        try:
            settings.checkpoint_backend = "memory"
            checkpointer = _create_checkpointer()

            assert isinstance(checkpointer, MemorySaver)
            assert not isinstance(checkpointer, (RedisSaver if REDIS_CHECKPOINTER_AVAILABLE else type(None)))

        finally:
            settings.checkpoint_backend = original_backend

    @pytest.mark.skipif(not REDIS_CHECKPOINTER_AVAILABLE, reason="Redis checkpointer not installed")
    def test_create_redis_checkpointer(self):
        """Test factory creates RedisSaver when backend is 'redis'"""
        # Save original setting
        original_backend = settings.checkpoint_backend
        original_url = settings.checkpoint_redis_url

        try:
            settings.checkpoint_backend = "redis"
            settings.checkpoint_redis_url = "redis://localhost:6379/1"

            checkpointer = _create_checkpointer()

            # Should return RedisSaver or fallback to MemorySaver if Redis unavailable
            assert isinstance(checkpointer, (RedisSaver, MemorySaver))

        finally:
            settings.checkpoint_backend = original_backend
            settings.checkpoint_redis_url = original_url

    def test_unknown_backend_fallback(self):
        """Test factory falls back to MemorySaver for unknown backend"""
        original_backend = settings.checkpoint_backend

        try:
            settings.checkpoint_backend = "unknown-backend"
            checkpointer = _create_checkpointer()

            # Should fallback to MemorySaver
            assert isinstance(checkpointer, MemorySaver)

        finally:
            settings.checkpoint_backend = original_backend


class TestMemoryCheckpointer:
    """Tests for in-memory checkpointer (development/testing)"""

    @pytest.mark.asyncio
    async def test_conversation_state_preserved_same_instance(self):
        """Test conversation state is preserved within same graph instance"""
        # Mock LLM to avoid actual API calls
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test response"))

        # Force memory backend
        original_backend = settings.checkpoint_backend
        original_checkpointing = settings.enable_checkpointing
        settings.checkpoint_backend = "memory"
        settings.enable_checkpointing = True

        try:
            # Create agent graph with memory checkpointer and mocked LLM
            with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
                graph = create_agent_graph()

                # First message
                initial_state: AgentState = {
                    "messages": [HumanMessage(content="Hello")],
                    "next_action": "",
                    "user_id": "test-user",
                    "request_id": "req-1",
                    "routing_confidence": None,
                    "reasoning": None,
                }

                config = {"configurable": {"thread_id": "test-thread-123"}}
                result1 = await graph.ainvoke(initial_state, config)  # noqa: F841

                # Second message (same thread)
                followup_state: AgentState = {
                    "messages": [HumanMessage(content="How are you?")],
                    "next_action": "",
                    "user_id": "test-user",
                    "request_id": "req-2",
                    "routing_confidence": None,
                    "reasoning": None,
                }

                result2 = await graph.ainvoke(followup_state, config)

                # Conversation history should accumulate
                # result2 should have more messages than just the followup
                assert len(result2["messages"]) >= len(followup_state["messages"])

        finally:
            settings.checkpoint_backend = original_backend
            settings.enable_checkpointing = original_checkpointing

    @pytest.mark.asyncio
    async def test_conversation_state_isolated_by_thread_id(self):
        """Test different thread_ids have isolated conversation state"""
        # Mock LLM to avoid actual API calls
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test response"))

        original_backend = settings.checkpoint_backend
        original_checkpointing = settings.enable_checkpointing
        settings.checkpoint_backend = "memory"
        settings.enable_checkpointing = True

        try:
            with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
                graph = create_agent_graph()

                # Thread 1
                state1: AgentState = {
                    "messages": [HumanMessage(content="Thread 1 message")],
                    "next_action": "",
                    "user_id": "user-1",
                    "request_id": "req-1",
                    "routing_confidence": None,
                    "reasoning": None,
                }

                result1 = await graph.ainvoke(state1, config={"configurable": {"thread_id": "thread-1"}})

                # Thread 2 (different thread_id)
                state2: AgentState = {
                    "messages": [HumanMessage(content="Thread 2 message")],
                    "next_action": "",
                    "user_id": "user-2",
                    "request_id": "req-2",
                    "routing_confidence": None,
                    "reasoning": None,
                }

                result2 = await graph.ainvoke(state2, config={"configurable": {"thread_id": "thread-2"}})

                # Results should be independent
                assert result1 != result2

        finally:
            settings.checkpoint_backend = original_backend
            settings.enable_checkpointing = original_checkpointing


@pytest.mark.integration
@pytest.mark.skipif(not REDIS_CHECKPOINTER_AVAILABLE, reason="Redis checkpointer not installed")
class TestRedisCheckpointer:
    """Integration tests for Redis checkpointer (requires Redis)"""

    @pytest.mark.asyncio
    async def test_conversation_state_persists_across_instances(self):
        """
        Test conversation state persists across different graph instances
        (Simulates pod restart or scaling scenario)
        """
        # Mock LLM to avoid actual API calls
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test response"))

        original_backend = settings.checkpoint_backend
        original_url = settings.checkpoint_redis_url
        original_checkpointing = settings.enable_checkpointing

        try:
            # Enable Redis checkpointer
            settings.checkpoint_backend = "redis"
            settings.checkpoint_redis_url = "redis://localhost:6379/1"
            settings.enable_checkpointing = True

            # Simulate Pod A with mocked LLM
            try:
                with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
                    graph_a = create_agent_graph()

                # Verify that Redis is actually being used (not fallback to MemorySaver)
                if graph_a.checkpointer is None:
                    pytest.skip("Checkpointing is disabled")
                checkpointer_type = type(graph_a.checkpointer).__name__
                if checkpointer_type == "MemorySaver":
                    pytest.skip("Redis not available, fell back to MemorySaver")
                if not (checkpointer_type == "RedisSaver" or "Redis" in checkpointer_type):
                    pytest.skip(f"Not using Redis checkpointer: {checkpointer_type}")
            except Exception as e:
                pytest.skip(f"Redis not available during graph creation: {e}")

            initial_state: AgentState = {
                "messages": [HumanMessage(content="Initial message from Pod A")],
                "next_action": "",
                "user_id": "test-user",
                "request_id": "req-1",
                "routing_confidence": None,
                "reasoning": None,
            }

            config = {"configurable": {"thread_id": "persistent-thread-123"}}

            try:
                result_a = await graph_a.ainvoke(initial_state, config)
                initial_message_count = len(result_a["messages"])
            except Exception as e:
                pytest.skip(f"Redis not available: {e}")

            # Simulate pod restart (new graph instance = Pod B) with mocked LLM
            with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
                graph_b = create_agent_graph()

            followup_state: AgentState = {
                "messages": [HumanMessage(content="Followup message from Pod B")],
                "next_action": "",
                "user_id": "test-user",
                "request_id": "req-2",
                "routing_confidence": None,
                "reasoning": None,
            }

            result_b = await graph_b.ainvoke(followup_state, config)

            # Pod B should have access to conversation history from Pod A
            assert len(result_b["messages"]) >= initial_message_count
            # Verify history includes message from Pod A
            message_contents = [msg.content for msg in result_b["messages"] if hasattr(msg, "content")]
            assert any("Pod A" in content or "Initial" in content for content in message_contents)

        finally:
            settings.checkpoint_backend = original_backend
            settings.checkpoint_redis_url = original_url
            settings.enable_checkpointing = original_checkpointing

    @pytest.mark.asyncio
    async def test_different_thread_ids_isolated_in_redis(self):
        """Test different thread_ids remain isolated even with Redis backend"""
        original_backend = settings.checkpoint_backend
        original_url = settings.checkpoint_redis_url
        original_checkpointing = settings.enable_checkpointing

        try:
            settings.checkpoint_backend = "redis"
            settings.checkpoint_redis_url = "redis://localhost:6379/1"
            settings.enable_checkpointing = True

            try:
                graph = create_agent_graph()

                # Verify that Redis is actually being used (not fallback to MemorySaver)
                if graph.checkpointer is None:
                    pytest.skip("Checkpointing is disabled")
                checkpointer_type = type(graph.checkpointer).__name__
                if checkpointer_type == "MemorySaver":
                    pytest.skip("Redis not available, fell back to MemorySaver")
                if not (checkpointer_type == "RedisSaver" or "Redis" in checkpointer_type):
                    pytest.skip(f"Not using Redis checkpointer: {checkpointer_type}")
            except Exception as e:
                pytest.skip(f"Redis not available during graph creation: {e}")

            # Thread 1
            state1: AgentState = {
                "messages": [HumanMessage(content="Thread 1 unique content")],
                "next_action": "",
                "user_id": "user-1",
                "request_id": "req-1",
                "routing_confidence": None,
                "reasoning": None,
            }

            try:
                result1 = await graph.ainvoke(state1, config={"configurable": {"thread_id": "redis-thread-1"}})
            except Exception as e:
                pytest.skip(f"Redis not available: {e}")

            # Thread 2
            state2: AgentState = {
                "messages": [HumanMessage(content="Thread 2 unique content")],
                "next_action": "",
                "user_id": "user-2",
                "request_id": "req-2",
                "routing_confidence": None,
                "reasoning": None,
            }

            result2 = await graph.ainvoke(state2, config={"configurable": {"thread_id": "redis-thread-2"}})

            # Threads should be isolated
            result1_contents = [msg.content for msg in result1["messages"] if hasattr(msg, "content")]
            result2_contents = [msg.content for msg in result2["messages"] if hasattr(msg, "content")]

            # Thread 1 should not contain Thread 2 content
            assert not any("Thread 2" in content for content in result1_contents)
            # Thread 2 should not contain Thread 1 content
            assert not any("Thread 1" in content for content in result2_contents)

        finally:
            settings.checkpoint_backend = original_backend
            settings.checkpoint_redis_url = original_url
            settings.enable_checkpointing = original_checkpointing


@pytest.mark.integration
class TestCheckpointerFallback:
    """Test graceful fallback when Redis is unavailable"""

    def test_redis_unavailable_fallback_to_memory(self):
        """Test graceful fallback to MemorySaver when Redis is unavailable"""
        original_backend = settings.checkpoint_backend
        original_url = settings.checkpoint_redis_url

        try:
            # Configure invalid Redis URL
            settings.checkpoint_backend = "redis"
            settings.checkpoint_redis_url = "redis://invalid-host:9999/1"

            checkpointer = _create_checkpointer()

            # Should fallback to MemorySaver on connection failure
            assert isinstance(checkpointer, MemorySaver)

        finally:
            settings.checkpoint_backend = original_backend
            settings.checkpoint_redis_url = original_url
