"""
Interrupt System for Human-in-the-Loop Workflows

Core interrupt handling for pausing and resuming agent execution.

Supports:
- Manual approval points
- Automatic validation checkpoints
- Time-based interrupts
- Conditional interrupts based on state
"""

from collections.abc import Callable
from datetime import datetime, UTC
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InterruptType(str, Enum):
    """Type of interrupt."""

    APPROVAL = "approval"  # Human approval required
    VALIDATION = "validation"  # Automatic validation checkpoint
    TIMEOUT = "timeout"  # Time-based interrupt
    CONDITIONAL = "conditional"  # Conditional based on state


class InterruptConfig(BaseModel):
    """Configuration for interrupt handling."""

    interrupt_type: InterruptType = Field(description="Type of interrupt")
    node_name: str = Field(description="Node where interrupt occurs")
    condition: Callable[[dict[str, Any]], bool] | None = Field(default=None, description="Optional condition function")
    timeout_seconds: int | None = Field(default=None, description="Timeout in seconds")
    notification_channels: list[str] = Field(default_factory=list, description="Channels to notify")
    auto_resume: bool = Field(default=False, description="Whether to auto-resume after timeout")


class InterruptHandler:
    """
    Handler for managing interrupts in agent workflows.

    Provides mechanisms to pause, resume, and manage interrupted executions.
    """

    def __init__(self) -> None:
        """Initialize interrupt handler."""
        self.pending_interrupts: dict[str, InterruptConfig] = {}
        self.interrupt_history: list[dict[str, Any]] = []

    def register_interrupt(self, config: InterruptConfig) -> str:
        """
        Register an interrupt point.

        Args:
            config: Interrupt configuration

        Returns:
            Interrupt ID
        """
        interrupt_id = f"{config.node_name}_{len(self.pending_interrupts)}"
        self.pending_interrupts[interrupt_id] = config

        return interrupt_id

    def should_interrupt(self, node_name: str, state: dict[str, Any]) -> bool:
        """
        Check if execution should interrupt at this node.

        Args:
            node_name: Current node name
            state: Current state

        Returns:
            True if should interrupt
        """
        for config in self.pending_interrupts.values():
            if config.node_name == node_name:
                # Check condition if provided
                if config.condition:
                    return config.condition(state)
                return True

        return False

    def handle_interrupt(self, node_name: str, state: dict[str, Any]) -> dict[str, Any]:
        """
        Handle interrupt at node.

        Args:
            node_name: Node name
            state: Current state

        Returns:
            Updated state with interrupt metadata
        """
        state["interrupted"] = True
        state["interrupt_node"] = node_name
        state["interrupt_timestamp"] = datetime.now(UTC).isoformat()

        # Add to history
        self.interrupt_history.append({"node": node_name, "state": state.copy(), "timestamp": state["interrupt_timestamp"]})

        return state

    def resume(self, interrupt_id: str, state: dict[str, Any]) -> dict[str, Any]:
        """
        Resume execution after interrupt.

        Args:
            interrupt_id: Interrupt to resume
            state: State to resume with

        Returns:
            Updated state
        """
        state["interrupted"] = False
        state["resumed_at"] = datetime.now(UTC).isoformat()

        return state


def create_interrupt_handler() -> InterruptHandler:
    """
    Create interrupt handler instance.

    Returns:
        InterruptHandler

    Example:
        handler = create_interrupt_handler()
        handler.register_interrupt(InterruptConfig(
            interrupt_type=InterruptType.APPROVAL,
            node_name="risky_action"
        ))
    """
    return InterruptHandler()


# ==============================================================================
# Conditional Interrupts
# ==============================================================================


def create_conditional_interrupt(condition: Callable[[dict[str, Any]], bool], node_name: str) -> InterruptConfig:
    """
    Create conditional interrupt that fires based on state.

    Args:
        condition: Function that returns True if should interrupt
        node_name: Node to interrupt

    Returns:
        InterruptConfig

    Example:
        # Interrupt if amount exceeds threshold
        def high_value_transaction(state):
            return state.get("amount", 0) > 10000

        interrupt = create_conditional_interrupt(
            high_value_transaction,
            "process_payment"
        )
    """
    return InterruptConfig(interrupt_type=InterruptType.CONDITIONAL, node_name=node_name, condition=condition)


def create_timeout_interrupt(node_name: str, timeout_seconds: int) -> InterruptConfig:
    """
    Create time-based interrupt.

    Args:
        node_name: Node to interrupt
        timeout_seconds: Timeout duration

    Returns:
        InterruptConfig

    Example:
        # Interrupt if node takes >30 seconds
        interrupt = create_timeout_interrupt("long_running_task", 30)
    """
    return InterruptConfig(interrupt_type=InterruptType.TIMEOUT, node_name=node_name, timeout_seconds=timeout_seconds)


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Create handler
    handler = create_interrupt_handler()

    # Register approval interrupt
    approval_interrupt = InterruptConfig(
        interrupt_type=InterruptType.APPROVAL, node_name="execute_trade", notification_channels=["email", "slack"]
    )

    interrupt_id = handler.register_interrupt(approval_interrupt)

    print(f"Registered interrupt: {interrupt_id}")

    # Simulate checking interrupt
    test_state = {"action": "execute_trade", "amount": 50000}

    if handler.should_interrupt("execute_trade", test_state):
        print("✋ Interrupt triggered at node: execute_trade")
        state = handler.handle_interrupt("execute_trade", test_state)
        print(f"   State marked as interrupted: {state['interrupted']}")
        print(f"   Timestamp: {state['interrupt_timestamp']}")

        # Simulate approval
        print("\n⏳ Waiting for human approval...")
        print("   (In production: webhook notification sent)")

        # Resume
        state = handler.resume(interrupt_id, state)
        print(f"\n✅ Execution resumed at: {state['resumed_at']}")
