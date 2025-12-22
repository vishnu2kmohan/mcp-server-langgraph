"""
Human-in-the-Loop Workflows

Interrupt mechanisms for agent approval, clarification, and human oversight.

Features:
- Approval nodes that pause execution for human review
- Confidence-based approval for low-confidence decisions
- Clarification requests for text, choice, and confirmation
- Resume/reject workflows
- Notification system
- Audit trail for approvals

Example - Approval:
    from mcp_server_langgraph.core.interrupts import ApprovalNode, ApprovalRequired

    # In your agent graph
    graph.add_node("action", perform_action)
    graph.add_node("approval", ApprovalNode("approve_action"))
    graph.add_edge("approval", "action")

Example - Confidence-based:
    from mcp_server_langgraph.core.interrupts import ConfidenceApprovalNode

    graph.add_node("confidence_check", ConfidenceApprovalNode(threshold=0.7))

Example - Clarification:
    from mcp_server_langgraph.core.interrupts import request_choice

    result = request_choice(state, "Which format?", [
        {"id": "csv", "label": "CSV"},
        {"id": "json", "label": "JSON"},
    ])
"""

from .approval import ApprovalNode, ApprovalRequired, ApprovalResponse, ApprovalStatus
from .clarification import (
    ClarificationOption,
    ClarificationRequest,
    ClarificationResponse,
    ClarificationType,
    create_clarification_request,
    request_choice,
    request_confirmation,
    request_text_input,
)
from .confidence import (
    AUTO_APPROVE_THRESHOLD,
    DEFAULT_CONFIDENCE_THRESHOLD,
    ConfidenceApprovalNode,
    check_confidence,
)
from .interrupts import InterruptType, create_interrupt_handler

__all__ = [
    # Approval
    "ApprovalNode",
    "ApprovalRequired",
    "ApprovalResponse",
    "ApprovalStatus",
    # Confidence-based approval
    "ConfidenceApprovalNode",
    "check_confidence",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "AUTO_APPROVE_THRESHOLD",
    # Clarification
    "ClarificationType",
    "ClarificationOption",
    "ClarificationRequest",
    "ClarificationResponse",
    "create_clarification_request",
    "request_choice",
    "request_confirmation",
    "request_text_input",
    # Core interrupts
    "InterruptType",
    "create_interrupt_handler",
]
