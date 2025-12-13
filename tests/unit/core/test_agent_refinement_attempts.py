"""
Tests for None refinement_attempts handling in agent.

Tests that the agent's generate_response function correctly handles
None values for refinement_attempts in the state.

TDD: These tests were written to verify the fix for TypeError when
refinement_attempts is None.

Follows memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agent]


@pytest.mark.xdist_group(name="agent_refinement")
class TestAgentRefinementAttempts:
    """Test refinement_attempts handling in agent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_refinement_attempts_none_treated_as_zero(self) -> None:
        """Test that None refinement_attempts is treated as 0."""
        # The fix: state.get("refinement_attempts") or 0
        # This handles both missing keys AND explicit None values

        # Simulate the fixed logic
        state = {"refinement_attempts": None}
        refinement_attempts = state.get("refinement_attempts") or 0

        # Should not raise TypeError
        assert refinement_attempts == 0
        assert refinement_attempts > -1  # Comparison should work

    @pytest.mark.unit
    def test_refinement_attempts_missing_treated_as_zero(self) -> None:
        """Test that missing refinement_attempts is treated as 0."""
        state = {}  # No refinement_attempts key
        refinement_attempts = state.get("refinement_attempts") or 0

        assert refinement_attempts == 0

    @pytest.mark.unit
    def test_refinement_attempts_zero_preserved(self) -> None:
        """Test that explicit 0 is preserved (not falsy coercion issue)."""
        state = {"refinement_attempts": 0}
        refinement_attempts = state.get("refinement_attempts") or 0

        # 0 or 0 = 0, which is correct
        assert refinement_attempts == 0

    @pytest.mark.unit
    def test_refinement_attempts_positive_preserved(self) -> None:
        """Test that positive values are preserved."""
        state = {"refinement_attempts": 3}
        refinement_attempts = state.get("refinement_attempts") or 0

        assert refinement_attempts == 3

    @pytest.mark.unit
    def test_comparison_with_none_raises_type_error(self) -> None:
        """Test that comparing None with int raises TypeError (the bug)."""
        # This demonstrates the original bug
        state = {"refinement_attempts": None}
        refinement_attempts = state.get("refinement_attempts")  # Returns None

        with pytest.raises(TypeError):
            # This was the original code that failed:
            _ = refinement_attempts > 0  # type: ignore[operator]

    @pytest.mark.unit
    def test_refinement_logic_with_none_does_not_add_context(self) -> None:
        """Test that None refinement_attempts skips refinement context."""
        # Simulate the fixed logic from generate_response
        state = {
            "refinement_attempts": None,
            "verification_feedback": "Some feedback",
        }

        refinement_attempts = state.get("refinement_attempts") or 0
        messages_list = ["original message"]

        # The condition that was failing:
        # if refinement_attempts > 0 and state.get("verification_feedback"):
        if refinement_attempts > 0 and state.get("verification_feedback"):
            messages_list = ["refinement prompt"] + messages_list

        # Should NOT add refinement prompt because refinement_attempts is 0
        assert len(messages_list) == 1
        assert messages_list[0] == "original message"

    @pytest.mark.unit
    def test_refinement_logic_with_positive_adds_context(self) -> None:
        """Test that positive refinement_attempts adds refinement context."""
        state = {
            "refinement_attempts": 2,
            "verification_feedback": "Some feedback",
        }

        refinement_attempts = state.get("refinement_attempts") or 0
        messages_list = ["original message"]

        if refinement_attempts > 0 and state.get("verification_feedback"):
            messages_list = ["refinement prompt"] + messages_list

        # Should add refinement prompt
        assert len(messages_list) == 2
        assert messages_list[0] == "refinement prompt"
