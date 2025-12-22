"""
Clarification Request System for Human-in-the-Loop Workflows.

Enables agents to request clarification from users when they encounter:
- Ambiguous instructions requiring text input
- Multiple valid approaches requiring choice selection
- Risk acknowledgment requiring confirmation

Architecture:
    Agent Graph → Clarification Node (asks question) → User Response → Resume

Use Cases:
    - "Which report do you mean - Q3 Sales or Q3 Marketing?"
    - "Should I use the fast approach (less accurate) or thorough approach (slower)?"
    - "This action will delete 150 records. Please confirm."

Example:
    from mcp_server_langgraph.core.interrupts.clarification import (
        request_choice,
        request_confirmation,
    )

    def analyze_data(state: dict) -> dict:
        approach = request_choice(
            state=state,
            question="Which analysis approach?",
            options=[
                {"id": "fast", "label": "Fast (~30s)"},
                {"id": "thorough", "label": "Thorough (~5m)"},
            ],
            recommended="thorough",
        )
        return approach
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class ClarificationType(str, Enum):
    """Type of clarification request."""

    TEXT = "text"  # Free-form text response
    CHOICE = "choice"  # Select from options
    CONFIRMATION = "confirmation"  # Yes/No decision
    FILE = "file"  # File upload (future)
    CREDENTIALS = "credentials"  # Sensitive input (future)


class ClarificationOption(BaseModel):
    """Option for choice-type clarifications."""

    id: str = Field(description="Unique identifier for the option")
    label: str = Field(description="Display label for the option")
    description: str | None = Field(
        default=None,
        description="Optional description explaining this option",
    )
    is_recommended: bool = Field(
        default=False,
        description="Whether this option is recommended",
    )


class ClarificationRequest(BaseModel):
    """Request for clarification from user."""

    request_id: str = Field(
        default_factory=lambda: f"clarify_{uuid4().hex[:12]}",
        description="Unique identifier for this request",
    )
    clarification_type: ClarificationType = Field(
        description="Type of clarification (text, choice, confirmation)",
    )
    question: str = Field(description="The question to ask the user")
    options: list[ClarificationOption] = Field(
        default_factory=list,
        description="Options for choice type (empty for other types)",
    )
    placeholder: str | None = Field(
        default=None,
        description="Placeholder text for text input",
    )
    required: bool = Field(
        default=True,
        description="Whether a response is required",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the clarification",
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Optional timeout after which default is used",
    )
    default_value: str | None = Field(
        default=None,
        description="Default value if timeout or skipped",
    )
    requested_at: str | None = Field(
        default=None,
        description="When the clarification was requested",
    )

    @model_validator(mode="after")
    def set_requested_at_timestamp(self) -> Self:
        """Set requested_at timestamp if not provided."""
        if self.requested_at is None:
            self.requested_at = datetime.now(UTC).isoformat()
        return self


class ClarificationResponse(BaseModel):
    """User's response to clarification request."""

    request_id: str = Field(description="ID of the clarification request")
    response_type: ClarificationType = Field(description="Type of response")
    value: str | None = Field(
        default=None,
        description="Text response (for TEXT type)",
    )
    selected_option_id: str | None = Field(
        default=None,
        description="Selected option ID (for CHOICE type)",
    )
    confirmed: bool | None = Field(
        default=None,
        description="Confirmation result (for CONFIRMATION type)",
    )
    responded_by: str = Field(description="Who responded")
    responded_at: str | None = Field(
        default=None,
        description="When the response was provided",
    )

    @model_validator(mode="after")
    def set_responded_at_timestamp(self) -> Self:
        """Set responded_at timestamp if not provided."""
        if self.responded_at is None:
            self.responded_at = datetime.now(UTC).isoformat()
        return self


def create_clarification_request(
    state: dict[str, Any],
    question: str,
    clarification_type: str | ClarificationType = ClarificationType.TEXT,
    options: list[dict[str, Any]] | None = None,
    placeholder: str | None = None,
    context: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a clarification request and add it to state.

    Args:
        state: Current agent state
        question: The question to ask the user
        clarification_type: Type of clarification (text, choice, confirmation)
        options: Options for choice type
        placeholder: Placeholder for text input
        context: Additional context
        request_id: Optional custom request ID

    Returns:
        Updated state with clarification request
    """
    # Convert string type to enum if needed
    if isinstance(clarification_type, str):
        clarification_type = ClarificationType(clarification_type)

    # Convert option dicts to ClarificationOption objects
    option_objects: list[ClarificationOption] = []
    if options:
        for opt in options:
            option_objects.append(ClarificationOption(**opt))

    # Create the request
    request = ClarificationRequest(
        request_id=request_id or f"clarify_{uuid4().hex[:12]}",
        clarification_type=clarification_type,
        question=question,
        options=option_objects,
        placeholder=placeholder,
        context=context or {},
    )

    # Create a copy of state to avoid mutation
    new_state = state.copy()

    # Add clarification request to state
    new_state["clarification_request"] = request.model_dump()
    new_state["pending_clarification"] = True
    new_state["current_clarification_id"] = request.request_id

    return new_state


def request_choice(
    state: dict[str, Any],
    question: str,
    options: list[dict[str, Any]],
    recommended: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Request user to choose from multiple options.

    Args:
        state: Current agent state
        question: The question to ask
        options: List of options, each with id, label, optional description
        recommended: Optional ID of recommended option
        context: Additional context

    Returns:
        Updated state with choice clarification request

    Example:
        result = request_choice(
            state=state,
            question="Which format should I use?",
            options=[
                {"id": "csv", "label": "CSV", "description": "Comma-separated"},
                {"id": "json", "label": "JSON", "description": "JavaScript Object Notation"},
            ],
            recommended="json",
        )
    """
    # Mark recommended option
    if recommended:
        for opt in options:
            if opt.get("id") == recommended:
                opt["is_recommended"] = True

    return create_clarification_request(
        state=state,
        question=question,
        clarification_type=ClarificationType.CHOICE,
        options=options,
        context=context,
    )


def request_confirmation(
    state: dict[str, Any],
    question: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Request user confirmation (yes/no).

    Args:
        state: Current agent state
        question: The confirmation question
        context: Additional context

    Returns:
        Updated state with confirmation clarification request

    Example:
        result = request_confirmation(
            state=state,
            question="This will delete 150 records. Proceed?",
            context={"record_count": 150},
        )
    """
    return create_clarification_request(
        state=state,
        question=question,
        clarification_type=ClarificationType.CONFIRMATION,
        context=context,
    )


def request_text_input(
    state: dict[str, Any],
    question: str,
    placeholder: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Request free-form text input from user.

    Args:
        state: Current agent state
        question: The question to ask
        placeholder: Placeholder text for input field
        context: Additional context

    Returns:
        Updated state with text clarification request

    Example:
        result = request_text_input(
            state=state,
            question="What API key should I use?",
            placeholder="Enter your API key...",
        )
    """
    return create_clarification_request(
        state=state,
        question=question,
        clarification_type=ClarificationType.TEXT,
        placeholder=placeholder,
        context=context,
    )
