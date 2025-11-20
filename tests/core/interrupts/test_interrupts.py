"""
Tests for Interrupt System (Human-in-the-Loop Workflows)

Security-Critical Module: Interrupt bypass could skip validation checkpoints.
Target Coverage: 90%+ (line and branch)

Tests cover:
- Interrupt type enumeration
- Interrupt configuration
- Interrupt handler registration
- Conditional interrupts
- Timeout interrupts
- State management
- Interrupt history
- Edge cases
"""

import gc
from typing import Any

import pytest

# Guard optional freezegun dependency
try:
    from freezegun import freeze_time
except ImportError:
    pytest.skip("freezegun not installed (optional test dependency)", allow_module_level=True)


from mcp_server_langgraph.core.interrupts.interrupts import (
    InterruptConfig,
    InterruptHandler,
    InterruptType,
    create_conditional_interrupt,
    create_interrupt_handler,
    create_timeout_interrupt,
)

# ==============================================================================
# InterruptType Enum Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinterrupttype")
class TestInterruptType:
    """Test interrupt type enumeration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_interrupt_type_values(self):
        """Test all interrupt type values exist."""
        assert InterruptType.APPROVAL == "approval"
        assert InterruptType.VALIDATION == "validation"
        assert InterruptType.TIMEOUT == "timeout"
        assert InterruptType.CONDITIONAL == "conditional"

    def test_interrupt_type_string_conversion(self):
        """Test interrupt type can be created from string."""
        assert InterruptType("approval") == InterruptType.APPROVAL
        assert InterruptType("validation") == InterruptType.VALIDATION
        assert InterruptType("timeout") == InterruptType.TIMEOUT
        assert InterruptType("conditional") == InterruptType.CONDITIONAL

    def test_interrupt_type_invalid_value(self):
        """Test invalid interrupt type raises error."""
        with pytest.raises(ValueError):
            InterruptType("invalid_type")


# ==============================================================================
# InterruptConfig Model Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinterruptconfig")
class TestInterruptConfig:
    """Test InterruptConfig model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_interrupt_config_minimal_fields(self):
        """Test creation with minimal fields."""
        config = InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="test_node",
        )

        assert config.interrupt_type == InterruptType.APPROVAL
        assert config.node_name == "test_node"
        assert config.condition is None
        assert config.timeout_seconds is None
        assert config.notification_channels == []
        assert config.auto_resume is False

    def test_interrupt_config_all_fields(self):
        """Test creation with all fields."""

        def test_condition(state: dict[str, Any]) -> bool:
            return state.get("amount", 0) > 1000

        config = InterruptConfig(
            interrupt_type=InterruptType.CONDITIONAL,
            node_name="payment_node",
            condition=test_condition,
            timeout_seconds=300,
            notification_channels=["email", "slack"],
            auto_resume=True,
        )

        assert config.interrupt_type == InterruptType.CONDITIONAL
        assert config.node_name == "payment_node"
        assert config.condition is not None
        assert config.timeout_seconds == 300
        assert len(config.notification_channels) == 2
        assert "email" in config.notification_channels
        assert "slack" in config.notification_channels
        assert config.auto_resume is True

    def test_interrupt_config_condition_callable(self):
        """Test condition field accepts callable."""

        def my_condition(state: dict[str, Any]) -> bool:
            return state.get("risk_level") == "high"

        config = InterruptConfig(
            interrupt_type=InterruptType.CONDITIONAL,
            node_name="risk_check",
            condition=my_condition,
        )

        # Test calling the condition
        test_state = {"risk_level": "high"}
        assert config.condition(test_state) is True

        test_state_low = {"risk_level": "low"}
        assert config.condition(test_state_low) is False


# ==============================================================================
# InterruptHandler Class Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinterrupthandler")
class TestInterruptHandler:
    """Test InterruptHandler class functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_interrupt_handler_init(self):
        """Test InterruptHandler initialization."""
        handler = InterruptHandler()

        assert isinstance(handler.pending_interrupts, dict)
        assert len(handler.pending_interrupts) == 0
        assert isinstance(handler.interrupt_history, list)
        assert len(handler.interrupt_history) == 0

    def test_register_interrupt_returns_id(self):
        """Test register_interrupt returns interrupt ID."""
        handler = InterruptHandler()
        config = InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="test_node",
        )

        interrupt_id = handler.register_interrupt(config)

        assert isinstance(interrupt_id, str)
        assert "test_node" in interrupt_id
        assert interrupt_id in handler.pending_interrupts

    def test_register_interrupt_stores_config(self):
        """Test register_interrupt stores configuration."""
        handler = InterruptHandler()
        config = InterruptConfig(
            interrupt_type=InterruptType.VALIDATION,
            node_name="validation_node",
        )

        interrupt_id = handler.register_interrupt(config)

        stored_config = handler.pending_interrupts[interrupt_id]
        assert stored_config.interrupt_type == InterruptType.VALIDATION
        assert stored_config.node_name == "validation_node"

    def test_register_multiple_interrupts(self):
        """Test registering multiple interrupts."""
        handler = InterruptHandler()

        config1 = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="node1")
        config2 = InterruptConfig(interrupt_type=InterruptType.TIMEOUT, node_name="node2")
        config3 = InterruptConfig(interrupt_type=InterruptType.CONDITIONAL, node_name="node3")

        id1 = handler.register_interrupt(config1)
        id2 = handler.register_interrupt(config2)
        id3 = handler.register_interrupt(config3)

        assert len(handler.pending_interrupts) == 3
        assert id1 != id2 != id3

    def test_register_interrupt_generates_unique_ids(self):
        """Test each registration generates unique ID."""
        handler = InterruptHandler()
        config = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="same_node")

        id1 = handler.register_interrupt(config)
        id2 = handler.register_interrupt(config)
        id3 = handler.register_interrupt(config)

        # Even for same node, IDs should be unique
        assert id1 != id2
        assert id2 != id3
        assert len(handler.pending_interrupts) == 3

    def test_should_interrupt_no_interrupts_registered(self):
        """Test should_interrupt returns False when no interrupts registered."""
        handler = InterruptHandler()
        state: dict[str, Any] = {}

        result = handler.should_interrupt("any_node", state)

        assert result is False

    def test_should_interrupt_matching_node(self):
        """Test should_interrupt returns True for matching node."""
        handler = InterruptHandler()
        config = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="target_node")
        handler.register_interrupt(config)

        state: dict[str, Any] = {}
        result = handler.should_interrupt("target_node", state)

        assert result is True

    def test_should_interrupt_non_matching_node(self):
        """Test should_interrupt returns False for non-matching node."""
        handler = InterruptHandler()
        config = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="target_node")
        handler.register_interrupt(config)

        state: dict[str, Any] = {}
        result = handler.should_interrupt("different_node", state)

        assert result is False

    def test_should_interrupt_with_condition_true(self):
        """Test should_interrupt with condition that returns True."""
        handler = InterruptHandler()

        def high_value_check(state: dict[str, Any]) -> bool:
            return state.get("amount", 0) > 5000

        config = InterruptConfig(
            interrupt_type=InterruptType.CONDITIONAL,
            node_name="payment",
            condition=high_value_check,
        )
        handler.register_interrupt(config)

        state: dict[str, Any] = {"amount": 10000}
        result = handler.should_interrupt("payment", state)

        assert result is True

    def test_should_interrupt_with_condition_false(self):
        """Test should_interrupt with condition that returns False."""
        handler = InterruptHandler()

        def high_value_check(state: dict[str, Any]) -> bool:
            return state.get("amount", 0) > 5000

        config = InterruptConfig(
            interrupt_type=InterruptType.CONDITIONAL,
            node_name="payment",
            condition=high_value_check,
        )
        handler.register_interrupt(config)

        state: dict[str, Any] = {"amount": 100}  # Below threshold
        result = handler.should_interrupt("payment", state)

        assert result is False

    def test_should_interrupt_without_condition(self):
        """Test should_interrupt without condition always returns True for matching node."""
        handler = InterruptHandler()
        config = InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="always_interrupt",
            condition=None,  # No condition
        )
        handler.register_interrupt(config)

        state: dict[str, Any] = {}
        result = handler.should_interrupt("always_interrupt", state)

        assert result is True

    @freeze_time("2024-01-15 18:00:00")
    def test_handle_interrupt_updates_state(self):
        """Test handle_interrupt adds interrupt metadata to state."""
        handler = InterruptHandler()
        state: dict[str, Any] = {"user": "john", "action": "transfer"}

        result_state = handler.handle_interrupt("test_node", state)

        assert result_state["interrupted"] is True
        assert result_state["interrupt_node"] == "test_node"
        assert result_state["interrupt_timestamp"] == "2024-01-15T18:00:00+00:00"

    def test_handle_interrupt_preserves_original_data(self):
        """Test handle_interrupt preserves original state data."""
        handler = InterruptHandler()
        state: dict[str, Any] = {"user_id": "user_123", "data": {"key": "value"}}

        result_state = handler.handle_interrupt("node", state)

        assert result_state["user_id"] == "user_123"
        assert result_state["data"]["key"] == "value"

    @freeze_time("2024-01-15 19:00:00")
    def test_handle_interrupt_adds_to_history(self):
        """Test handle_interrupt adds entry to interrupt history."""
        handler = InterruptHandler()
        state: dict[str, Any] = {"action": "test"}

        handler.handle_interrupt("node1", state)

        assert len(handler.interrupt_history) == 1
        history_entry = handler.interrupt_history[0]
        assert history_entry["node"] == "node1"
        assert history_entry["timestamp"] == "2024-01-15T19:00:00+00:00"
        assert "state" in history_entry

    def test_handle_interrupt_multiple_calls_build_history(self):
        """Test multiple handle_interrupt calls build history."""
        handler = InterruptHandler()

        handler.handle_interrupt("node1", {"step": 1})
        handler.handle_interrupt("node2", {"step": 2})
        handler.handle_interrupt("node3", {"step": 3})

        assert len(handler.interrupt_history) == 3
        assert handler.interrupt_history[0]["node"] == "node1"
        assert handler.interrupt_history[1]["node"] == "node2"
        assert handler.interrupt_history[2]["node"] == "node3"

    @freeze_time("2024-01-15 20:00:00")
    def test_resume_clears_interrupted_flag(self):
        """Test resume clears interrupted flag and adds timestamp."""
        handler = InterruptHandler()
        state: dict[str, Any] = {"interrupted": True, "interrupt_node": "test"}

        result_state = handler.resume("interrupt_123", state)

        assert result_state["interrupted"] is False
        assert result_state["resumed_at"] == "2024-01-15T20:00:00+00:00"

    def test_resume_preserves_state(self):
        """Test resume preserves original state data."""
        handler = InterruptHandler()
        state: dict[str, Any] = {
            "interrupted": True,
            "user": "john",
            "data": {"important": "value"},
        }

        result_state = handler.resume("int_001", state)

        assert result_state["user"] == "john"
        assert result_state["data"]["important"] == "value"


# ==============================================================================
# Helper Function Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcreateinterrupthandler")
class TestCreateInterruptHandler:
    """Test create_interrupt_handler factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_interrupt_handler_returns_instance(self):
        """Test create_interrupt_handler returns InterruptHandler instance."""
        handler = create_interrupt_handler()

        assert isinstance(handler, InterruptHandler)

    def test_create_interrupt_handler_creates_independent_instances(self):
        """Test multiple calls create independent instances."""
        handler1 = create_interrupt_handler()
        handler2 = create_interrupt_handler()

        # Register interrupt in handler1
        config = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="test")
        handler1.register_interrupt(config)

        # handler2 should be unaffected
        assert len(handler1.pending_interrupts) == 1
        assert len(handler2.pending_interrupts) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcreateconditionalinterrupt")
class TestCreateConditionalInterrupt:
    """Test create_conditional_interrupt helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_conditional_interrupt_returns_config(self):
        """Test create_conditional_interrupt returns InterruptConfig."""

        def my_condition(state: dict[str, Any]) -> bool:
            return True

        config = create_conditional_interrupt(my_condition, "test_node")

        assert isinstance(config, InterruptConfig)

    def test_create_conditional_interrupt_sets_type(self):
        """Test interrupt type is set to CONDITIONAL."""

        def condition(state: dict[str, Any]) -> bool:
            return False

        config = create_conditional_interrupt(condition, "node")

        assert config.interrupt_type == InterruptType.CONDITIONAL

    def test_create_conditional_interrupt_sets_condition(self):
        """Test condition function is stored correctly."""

        def risk_check(state: dict[str, Any]) -> bool:
            return state.get("risk") == "high"

        config = create_conditional_interrupt(risk_check, "risk_node")

        # Test the condition works
        assert config.condition({"risk": "high"}) is True
        assert config.condition({"risk": "low"}) is False

    def test_create_conditional_interrupt_sets_node_name(self):
        """Test node_name is set correctly."""

        def cond(state: dict[str, Any]) -> bool:
            return True

        config = create_conditional_interrupt(cond, "my_special_node")

        assert config.node_name == "my_special_node"

    def test_create_conditional_interrupt_with_complex_condition(self):
        """Test conditional interrupt with complex business logic."""

        def complex_condition(state: dict[str, Any]) -> bool:
            """Interrupt if high-value transaction in restricted country."""
            amount = state.get("amount", 0)
            country = state.get("country", "")
            restricted_countries = ["XX", "YY", "ZZ"]

            return amount > 10000 and country in restricted_countries

        config = create_conditional_interrupt(complex_condition, "compliance_check")

        # Should interrupt
        assert config.condition({"amount": 15000, "country": "XX"}) is True

        # Should not interrupt (low amount)
        assert config.condition({"amount": 5000, "country": "XX"}) is False

        # Should not interrupt (allowed country)
        assert config.condition({"amount": 15000, "country": "US"}) is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcreatetimeoutinterrupt")
class TestCreateTimeoutInterrupt:
    """Test create_timeout_interrupt helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_timeout_interrupt_returns_config(self):
        """Test create_timeout_interrupt returns InterruptConfig."""
        config = create_timeout_interrupt("test_node", 30)

        assert isinstance(config, InterruptConfig)

    def test_create_timeout_interrupt_sets_type(self):
        """Test interrupt type is set to TIMEOUT."""
        config = create_timeout_interrupt("node", 60)

        assert config.interrupt_type == InterruptType.TIMEOUT

    def test_create_timeout_interrupt_sets_timeout(self):
        """Test timeout_seconds is set correctly."""
        config = create_timeout_interrupt("long_task", 300)

        assert config.timeout_seconds == 300

    def test_create_timeout_interrupt_sets_node_name(self):
        """Test node_name is set correctly."""
        config = create_timeout_interrupt("slow_operation", 120)

        assert config.node_name == "slow_operation"

    def test_create_timeout_interrupt_various_durations(self):
        """Test timeout interrupt with various durations."""
        config_short = create_timeout_interrupt("quick_task", 5)
        config_medium = create_timeout_interrupt("medium_task", 60)
        config_long = create_timeout_interrupt("long_task", 3600)

        assert config_short.timeout_seconds == 5
        assert config_medium.timeout_seconds == 60
        assert config_long.timeout_seconds == 3600


# ==============================================================================
# Integration Tests (Complete Interrupt Workflows)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinterruptworkflowintegration")
class TestInterruptWorkflowIntegration:
    """Integration tests for complete interrupt workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @freeze_time("2024-01-15 21:00:00")
    def test_full_interrupt_workflow(self):
        """Test complete interrupt workflow: register -> check -> interrupt -> resume."""
        # Step 1: Create handler and register interrupt
        handler = create_interrupt_handler()
        config = InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="sensitive_operation",
        )
        interrupt_id = handler.register_interrupt(config)

        # Step 2: Check if should interrupt
        state: dict[str, Any] = {"user": "john", "action": "delete_data"}
        should_stop = handler.should_interrupt("sensitive_operation", state)
        assert should_stop is True

        # Step 3: Handle interrupt
        state = handler.handle_interrupt("sensitive_operation", state)
        assert state["interrupted"] is True
        assert state["interrupt_timestamp"] == "2024-01-15T21:00:00+00:00"

        # Step 4: Resume execution
        with freeze_time("2024-01-15 21:05:00"):
            state = handler.resume(interrupt_id, state)

        assert state["interrupted"] is False
        assert state["resumed_at"] == "2024-01-15T21:05:00+00:00"

    def test_conditional_interrupt_workflow(self):
        """Test conditional interrupt only fires when condition met."""
        handler = create_interrupt_handler()

        def amount_threshold(state: dict[str, Any]) -> bool:
            return state.get("amount", 0) > 1000

        config = create_conditional_interrupt(amount_threshold, "payment")
        handler.register_interrupt(config)

        # Low amount - should not interrupt
        low_state: dict[str, Any] = {"amount": 500}
        assert handler.should_interrupt("payment", low_state) is False

        # High amount - should interrupt
        high_state: dict[str, Any] = {"amount": 5000}
        assert handler.should_interrupt("payment", high_state) is True

    def test_multiple_nodes_with_different_interrupts(self):
        """Test multiple nodes with different interrupt configurations."""
        handler = create_interrupt_handler()

        # Node 1: Always interrupt
        config1 = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="node1")

        # Node 2: Conditional interrupt
        config2 = create_conditional_interrupt(
            lambda state: state.get("flag") is True,
            "node2",
        )

        # Node 3: Timeout interrupt
        config3 = create_timeout_interrupt("node3", 30)

        handler.register_interrupt(config1)
        handler.register_interrupt(config2)
        handler.register_interrupt(config3)

        state: dict[str, Any] = {"flag": False}

        # Node 1: Should always interrupt
        assert handler.should_interrupt("node1", state) is True

        # Node 2: Should not interrupt (flag is False)
        assert handler.should_interrupt("node2", state) is False

        # Node 3: Should interrupt (no condition)
        assert handler.should_interrupt("node3", state) is True

        # Change state
        state["flag"] = True

        # Now node2 should interrupt
        assert handler.should_interrupt("node2", state) is True


# ==============================================================================
# Edge Cases and Error Scenarios
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinterruptedgecases")
class TestInterruptEdgeCases:
    """Test edge cases and error scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_should_interrupt_empty_state(self):
        """Test should_interrupt with empty state."""
        handler = create_interrupt_handler()
        config = InterruptConfig(interrupt_type=InterruptType.APPROVAL, node_name="test")
        handler.register_interrupt(config)

        result = handler.should_interrupt("test", {})

        assert result is True  # Should still work with empty state

    def test_should_interrupt_with_condition_empty_state(self):
        """Test conditional interrupt with empty state."""
        handler = create_interrupt_handler()

        def safe_condition(state: dict[str, Any]) -> bool:
            return state.get("value", 0) > 100

        config = create_conditional_interrupt(safe_condition, "test")
        handler.register_interrupt(config)

        result = handler.should_interrupt("test", {})

        assert result is False  # Condition should handle missing keys gracefully

    def test_handle_interrupt_empty_state(self):
        """Test handle_interrupt with empty state."""
        handler = create_interrupt_handler()

        result_state = handler.handle_interrupt("test_node", {})

        assert result_state["interrupted"] is True
        assert result_state["interrupt_node"] == "test_node"
        assert "interrupt_timestamp" in result_state

    def test_resume_empty_state(self):
        """Test resume with empty state."""
        handler = create_interrupt_handler()

        result_state = handler.resume("int_id", {})

        assert result_state["interrupted"] is False
        assert "resumed_at" in result_state

    def test_interrupt_history_state_isolation(self):
        """Test interrupt history stores state copy, not reference."""
        handler = create_interrupt_handler()
        original_state: dict[str, Any] = {"value": "original"}

        handler.handle_interrupt("node", original_state)

        # Modify original state
        original_state["value"] = "modified"

        # History should have original value (copy, not reference)
        history_state = handler.interrupt_history[0]["state"]
        assert history_state["value"] == "original"

    def test_multiple_interrupts_same_node_different_conditions(self):
        """Test registering multiple interrupts for same node with different conditions."""
        handler = create_interrupt_handler()

        def condition1(state: dict[str, Any]) -> bool:
            return state.get("flag1") is True

        def condition2(state: dict[str, Any]) -> bool:
            return state.get("flag2") is True

        config1 = InterruptConfig(
            interrupt_type=InterruptType.CONDITIONAL,
            node_name="same_node",
            condition=condition1,
        )
        config2 = InterruptConfig(
            interrupt_type=InterruptType.CONDITIONAL,
            node_name="same_node",
            condition=condition2,
        )

        handler.register_interrupt(config1)
        handler.register_interrupt(config2)

        # If either condition is true, should interrupt (first match wins)
        state_both_false: dict[str, Any] = {"flag1": False, "flag2": False}
        assert handler.should_interrupt("same_node", state_both_false) is False

        state_first_true: dict[str, Any] = {"flag1": True, "flag2": False}
        assert handler.should_interrupt("same_node", state_first_true) is True

    def test_notification_channels_stored(self):
        """Test notification_channels are stored in config."""
        config = InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="notify_test",
            notification_channels=["email", "slack", "sms"],
        )

        assert len(config.notification_channels) == 3
        assert "email" in config.notification_channels
        assert "slack" in config.notification_channels
        assert "sms" in config.notification_channels

    def test_auto_resume_flag(self):
        """Test auto_resume flag is stored correctly."""
        config_manual = InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="manual",
            auto_resume=False,
        )
        config_auto = InterruptConfig(
            interrupt_type=InterruptType.TIMEOUT,
            node_name="auto",
            auto_resume=True,
        )

        assert config_manual.auto_resume is False
        assert config_auto.auto_resume is True
