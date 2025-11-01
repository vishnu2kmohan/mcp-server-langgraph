"""
Human-in-the-Loop Workflows

Interrupt mechanisms for agent approval and human oversight.

Features:
- Approval nodes that pause execution
- Resume/reject workflows
- Notification system
- Audit trail for approvals

Example:
    from mcp_server_langgraph.core.interrupts import ApprovalNode, ApprovalRequired

    # In your agent graph
    graph.add_node("action", perform_action)
    graph.add_node("approval", ApprovalNode("approve_action"))
    graph.add_edge("approval", "action")

    # Execution pauses at approval node
    # Resume with: agent.update_state(config, {"approved": True})
"""

from .approval import ApprovalNode, ApprovalRequired, ApprovalResponse, ApprovalStatus
from .interrupts import InterruptType, create_interrupt_handler

__all__ = [
    "ApprovalNode",
    "ApprovalRequired",
    "ApprovalResponse",
    "ApprovalStatus",
    "InterruptType",
    "create_interrupt_handler",
]
