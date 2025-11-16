"""
Regression test for LangGraph 1.0.3+ return type changes.

OpenAI Codex Finding (2025-11-16):
==================================
tests/patterns/test_supervisor.py:241 fails with AttributeError: 'dict' object has no attribute 'task'

Root Cause:
-----------
LangGraph underwent a breaking API change between versions:
- **0.6.10 and earlier**: compiled.invoke() returned Pydantic model instances (e.g., SupervisorState)
- **1.0.3+**: compiled.invoke() returns plain Python dictionaries

Impact:
-------
Tests that access result.task (attribute access) fail because result is now a dict,
requiring result["task"] (key access) instead.

This regression test validates the current LangGraph 1.0.3+ behavior and ensures
our code correctly handles dict return types.

Related Files:
--------------
- src/mcp_server_langgraph/patterns/supervisor.py - Already handles dicts correctly (lines 248+)
- src/mcp_server_langgraph/patterns/swarm.py - Also handles dicts correctly
- tests/patterns/test_supervisor.py:241 - Needs update to use dict access
- tests/patterns/test_swarm.py - May need similar update

References:
-----------
- pyproject.toml: langgraph>=1.0.3 (line 29)
- Migration from 0.2.28 → 0.6.10 → 1.0.3 (breaking changes)
"""

import gc
from typing import Any, Dict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from mcp_server_langgraph.patterns.supervisor import Supervisor, SupervisorState
from mcp_server_langgraph.patterns.swarm import Swarm, SwarmState


@pytest.mark.xdist_group(name="langgraph_return_types")
class TestLangGraphReturnTypes:
    """
    Test suite validating LangGraph 1.0.3+ return type behavior.

    These tests document the breaking API change and ensure our patterns
    handle both dict and Pydantic model types correctly.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_langgraph_1_0_3_returns_dict_not_pydantic_model(self):
        """
        Validate that LangGraph 1.0.3+ compiled.invoke() returns dict, not Pydantic model.

        This is the DOCUMENTED behavior we expect in LangGraph 1.0.3+.
        If this test fails, LangGraph may have reverted the API change.
        """
        # GIVEN: A simple StateGraph with Pydantic state
        from pydantic import BaseModel, Field

        class SimpleState(BaseModel):
            value: str = Field(default="initial")

        graph = StateGraph(SimpleState)

        def update_value(state: SimpleState) -> Dict[str, Any]:
            return {"value": "updated"}

        graph.add_node("update", update_value)
        graph.set_entry_point("update")
        graph.set_finish_point("update")

        compiled = graph.compile()

        # WHEN: Invoking the compiled graph
        result = compiled.invoke(SimpleState(value="initial"))

        # THEN: Result should be a dict (LangGraph 1.0.3+ behavior)
        assert isinstance(result, dict), (
            f"LangGraph 1.0.3+ should return dict, got {type(result).__name__}. "
            f"If you're seeing a Pydantic model, LangGraph may have changed the API again."
        )

        # THEN: Result should contain the state data as dict keys
        assert "value" in result, "Result dict should contain 'value' key"
        assert result["value"] == "updated", "Value should be updated"

        # THEN: Result should NOT have Pydantic model attributes
        assert not hasattr(result, "value"), "Result should not have '.value' attribute access (dict, not Pydantic model)"

    def test_supervisor_pattern_handles_dict_return(self):
        """
        Validate that Supervisor pattern correctly handles dict returns from compiled.invoke().

        The Supervisor.invoke() method (lines 248+) already treats results as dicts.
        This test ensures that implementation is correct.
        """

        # GIVEN: A Supervisor with a simple agent
        def simple_agent(task: str) -> str:
            return f"processed: {task}"

        supervisor = Supervisor(agents={"agent1": simple_agent})

        # WHEN: Compiling the supervisor and invoking with checkpointer
        checkpointer = MemorySaver()
        compiled = supervisor.compile(checkpointer=checkpointer)

        initial_state = SupervisorState(task="test-task")
        config = {"configurable": {"thread_id": "test-thread-123"}}

        result = compiled.invoke(initial_state, config=config)

        # THEN: Result should be a dict (LangGraph 1.0.3+ behavior)
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"

        # THEN: Result should contain expected state keys
        assert "task" in result, "Result should contain 'task' key"
        assert "final_result" in result, "Result should contain 'final_result' key"
        assert "completed" in result, "Result should contain 'completed' key"

        # THEN: Should access via dict keys, not attributes
        assert result["task"] == "test-task"
        assert isinstance(result["final_result"], str)

    def test_swarm_pattern_handles_dict_return(self):
        """
        Validate that Swarm pattern correctly handles dict returns from compiled.invoke().

        Similar to Supervisor, Swarm should handle dict returns correctly.
        """

        # GIVEN: A Swarm with simple agents
        def agent1(query: str) -> str:
            return f"agent1: {query}"

        def agent2(query: str) -> str:
            return f"agent2: {query}"

        swarm = Swarm(agents={"agent1": agent1, "agent2": agent2}, aggregation_strategy="synthesis")

        # WHEN: Compiling and invoking the swarm
        checkpointer = MemorySaver()
        compiled = swarm.compile(checkpointer=checkpointer)

        initial_state = SwarmState(query="test-query")
        config = {"configurable": {"thread_id": "test-thread-456"}}

        result = compiled.invoke(initial_state, config=config)

        # THEN: Result should be a dict (LangGraph 1.0.3+ behavior)
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"

        # THEN: Result should contain expected state keys
        assert "query" in result, "Result should contain 'query' key"
        assert "agent_results" in result, "Result should contain 'agent_results' key"
        assert "aggregated_result" in result, "Result should contain 'aggregated_result' key"

        # THEN: Should access via dict keys, not attributes
        assert result["query"] == "test-query"
        assert isinstance(result["agent_results"], dict)

    def test_dict_to_pydantic_conversion(self):
        """
        Demonstrate how to convert dict results back to Pydantic models if needed.

        This pattern can be used in tests that need type safety from Pydantic models.
        """

        # GIVEN: A compiled graph that returns dict
        def simple_agent(task: str) -> str:
            return "result"

        supervisor = Supervisor(agents={"agent1": simple_agent})
        compiled = supervisor.compile()

        result_dict = compiled.invoke(SupervisorState(task="test"))

        # WHEN: Converting dict to Pydantic model
        assert isinstance(result_dict, dict), "Should start with dict"

        # Parse dict into SupervisorState using Pydantic v2 model_validate
        result_model = SupervisorState.model_validate(result_dict)

        # THEN: Can now use attribute access
        assert isinstance(result_model, SupervisorState)
        assert result_model.task == "test"  # Attribute access works on Pydantic model
        assert result_model.completed is not None  # Type safety from Pydantic

    @pytest.mark.parametrize("use_checkpointer", [True, False])
    def test_return_type_consistent_with_and_without_checkpointer(self, use_checkpointer):
        """
        Validate that return type is consistent regardless of checkpointer usage.

        Both checkpointed and non-checkpointed invocations should return dicts in 1.0.3+.
        """

        # GIVEN: A simple supervisor
        def simple_agent(task: str) -> str:
            return "done"

        supervisor = Supervisor(agents={"agent1": simple_agent})

        # WHEN: Compiling with or without checkpointer
        if use_checkpointer:
            compiled = supervisor.compile(checkpointer=MemorySaver())
            config = {"configurable": {"thread_id": "test-123"}}
        else:
            compiled = supervisor.compile()
            config = {}

        result = compiled.invoke(SupervisorState(task="test"), config=config)

        # THEN: Should always return dict
        assert isinstance(result, dict), (
            f"Return type should be dict (with checkpointer={use_checkpointer}), " f"got {type(result).__name__}"
        )


@pytest.mark.xdist_group(name="langgraph_compatibility")
class TestBackwardCompatibilityPatterns:
    """
    Test patterns for writing code that works with both dict and Pydantic returns.

    These patterns help maintain backward compatibility if LangGraph changes behavior again.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_safe_dict_access_pattern(self):
        """
        Demonstrate safe access pattern that works for both dict and Pydantic models.
        """

        def simple_agent(task: str) -> str:
            return "result"

        supervisor = Supervisor(agents={"agent1": simple_agent})
        compiled = supervisor.compile()

        result = compiled.invoke(SupervisorState(task="test"))

        # PATTERN 1: Use dict access (works for dict, fails for Pydantic)
        if isinstance(result, dict):
            task_value = result["task"]
        else:
            task_value = result.task

        assert task_value == "test"

        # PATTERN 2: Use getattr with fallback (works for both)
        task_value_safe = result.get("task") if isinstance(result, dict) else getattr(result, "task", None)
        assert task_value_safe == "test"

    def test_helper_function_for_safe_access(self):
        """
        Demonstrate helper function for safe attribute/key access.
        """

        def get_state_field(state: Any, field: str) -> Any:
            """
            Get field from state, whether it's a dict or Pydantic model.

            Args:
                state: State object (dict or Pydantic model)
                field: Field name to retrieve

            Returns:
                Field value

            Raises:
                KeyError/AttributeError: If field doesn't exist
            """
            if isinstance(state, dict):
                return state[field]
            else:
                return getattr(state, field)

        # Test with dict (LangGraph 1.0.3+)
        def simple_agent(task: str) -> str:
            return "result"

        supervisor = Supervisor(agents={"agent1": simple_agent})
        compiled = supervisor.compile()

        result = compiled.invoke(SupervisorState(task="test"))

        # Should work regardless of return type
        task_value = get_state_field(result, "task")
        assert task_value == "test"

        completed_value = get_state_field(result, "completed")
        assert completed_value is not None
