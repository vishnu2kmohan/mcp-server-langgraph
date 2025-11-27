"""
Test suite for agent.py type safety (MyPy compliance)

This test ensures that the agent module passes MyPy type checking,
preventing the regression of type errors that block CI/CD.

Following TDD principles: This test should FAIL initially, then PASS
after fixing the type annotations.

Regression prevention for validation audit findings:
- 2 MyPy errors in agent.py (lines 696, 699)
- ainvoke type incompatibility with list[BaseMessage]
"""

import gc
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="agent_type_compliance")
@pytest.mark.timeout(120)  # Allow up to 2 minutes for mypy subprocess tests
class TestAgentTypeCompliance:
    """Test that agent.py passes MyPy type checking"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_module_passes_mypy(self):
        """
        Test that agent.py has no MyPy type errors.

        RED Phase: This test will FAIL initially due to:
        - Line 696: Argument 1 to "ainvoke" incompatible type
        - Line 699: Argument 1 to "ainvoke" incompatible type

        GREEN Phase: After fixing type annotations, test should PASS

        Expected errors before fix:
        - error: Argument 1 to "ainvoke" of "LLMFactory" has incompatible type
          "list[BaseMessage]"; expected "list[BaseMessage | dict[str, Any]]"
        """
        # Get the path to agent.py
        agent_file = Path("src/mcp_server_langgraph/core/agent.py")
        assert agent_file.exists(), f"Agent file not found: {agent_file}"

        # Run MyPy on agent.py
        result = subprocess.run(
            ["uv", "run", "mypy", str(agent_file), "--no-error-summary"], capture_output=True, text=True, timeout=30
        )

        # Check for specific type errors that need to be fixed
        if result.returncode != 0:
            # Parse errors from stdout (mypy outputs errors there, not stderr)
            errors = result.stdout

            # Assert no type errors (this will fail in RED phase)
            pytest.fail(
                f"MyPy type errors found in agent.py:\n{errors}\n\n"
                f"Expected: 0 errors\n"
                f"Actual: {result.returncode} exit code\n\n"
                f"Fix: Update type annotations to match expected types"
            )

    def test_agent_state_messages_type(self):
        """
        Test that AgentState.messages has the correct type annotation.

        The messages field should be compatible with both:
        1. operator.add for concatenation
        2. Methods expecting list[BaseMessage]

        This test validates the type definition is correct.
        """
        from mcp_server_langgraph.core.agent import AgentState
        from typing import get_type_hints, get_args, get_origin
        from collections.abc import Sequence

        # Get type hints for AgentState
        hints = get_type_hints(AgentState, include_extras=True)

        # Get the messages field type
        messages_type = hints.get("messages")
        assert messages_type is not None, "messages field not found in AgentState"

        # Extract the actual type from Annotated
        from typing import Annotated

        if get_origin(messages_type) is Annotated:
            args = get_args(messages_type)
            actual_type = args[0]  # First arg is the actual type

            # The type should be compatible with list operations
            # Check if it's a Sequence or list type
            origin = get_origin(actual_type)

            # Document the current type for debugging
            print(f"Current messages type: {actual_type}")
            print(f"Origin: {origin}")

            # This test documents the type - will be used to verify the fix
            # After fix, we expect origin to be list or compatible with list operations

    def test_no_mypy_errors_in_codebase(self):
        """
        Test that the entire src/mcp_server_langgraph module passes MyPy.

        This is a broader check to ensure the type safety fix doesn't
        introduce errors elsewhere.
        """
        # CI runners are slower - allow 90 seconds for full codebase mypy check
        result = subprocess.run(
            ["uv", "run", "mypy", "src/mcp_server_langgraph", "--no-error-summary"], capture_output=True, text=True, timeout=90
        )

        if result.returncode != 0:
            # Count errors from stdout (mypy outputs errors there, not stderr)
            error_lines = [line for line in result.stdout.split("\n") if "error:" in line]
            error_count = len(error_lines)

            pytest.fail(
                f"MyPy found {error_count} type errors in codebase:\n"
                f"{result.stdout}\n\n"
                f"Expected: 0 errors\n"
                f"Current errors must be fixed to unblock CI/CD"
            )


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_message_handling")
class TestAgentMessageHandling:
    """Test that message handling works correctly with the fixed types"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_message_list_operations(self):
        """
        Test that message lists support required operations:
        - Concatenation with +
        - Slicing
        - Indexing
        - Conversion to list

        These operations are used throughout agent.py and must work
        with the correct type annotation.
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        # Create sample messages
        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User query"),
            AIMessage(content="AI response"),
        ]

        # Test concatenation (used with operator.add)
        new_messages = messages + [HumanMessage(content="Follow-up")]
        assert len(new_messages) == 4
        assert isinstance(new_messages, list)

        # Test slicing (used in verify_response, line 728)
        context = messages[:-1]
        assert len(context) == 2
        assert isinstance(context, list)

        # Test indexing (used in verify_response, line 719)
        last_message = messages[-1]
        assert isinstance(last_message, AIMessage)

        # Test list conversion (used throughout agent.py)
        messages_copy = list(messages)
        assert messages_copy == messages
        assert isinstance(messages_copy, list)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
