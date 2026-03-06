"""
Tests for Clarification Request Interrupt Functions.

Phase 1 of the Confidence-Based HITL Implementation Plan.

TDD: Write tests FIRST, then implementation.

Clarification requests allow agents to ask users for:
- Text input (free-form responses)
- Choice selection (multiple options)
- Confirmation (yes/no decisions)

Tests:
1. ClarificationType enum exists with proper values
2. ClarificationOption model works correctly
3. ClarificationRequest model validation
4. ClarificationResponse model validation
5. request_clarification function creates proper state
6. request_choice helper function works
7. request_confirmation helper function works
"""

from __future__ import annotations

import gc
from typing import Any

import pytest

pytestmark = pytest.mark.unit


class TestClarificationTypeEnum:
    """Test ClarificationType enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_clarification_type_importable(self) -> None:
        """ClarificationType should be importable."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        assert ClarificationType is not None

    def test_clarification_type_has_text(self) -> None:
        """ClarificationType should have TEXT value."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        assert hasattr(ClarificationType, "TEXT")
        assert ClarificationType.TEXT.value == "text"

    def test_clarification_type_has_choice(self) -> None:
        """ClarificationType should have CHOICE value."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        assert hasattr(ClarificationType, "CHOICE")
        assert ClarificationType.CHOICE.value == "choice"

    def test_clarification_type_has_confirmation(self) -> None:
        """ClarificationType should have CONFIRMATION value."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        assert hasattr(ClarificationType, "CONFIRMATION")
        assert ClarificationType.CONFIRMATION.value == "confirmation"


class TestClarificationOption:
    """Test ClarificationOption model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_clarification_option_importable(self) -> None:
        """ClarificationOption should be importable."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationOption,
        )

        assert ClarificationOption is not None

    def test_option_requires_id_and_label(self) -> None:
        """ClarificationOption should require id and label."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationOption,
        )

        option = ClarificationOption(id="opt1", label="Option 1")
        assert option.id == "opt1"
        assert option.label == "Option 1"

    def test_option_accepts_description(self) -> None:
        """ClarificationOption should accept optional description."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationOption,
        )

        option = ClarificationOption(
            id="opt1",
            label="Option 1",
            description="This is option 1",
        )
        assert option.description == "This is option 1"

    def test_option_accepts_is_recommended(self) -> None:
        """ClarificationOption should accept is_recommended flag."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationOption,
        )

        option = ClarificationOption(
            id="opt1",
            label="Option 1",
            is_recommended=True,
        )
        assert option.is_recommended is True

    def test_option_is_recommended_defaults_false(self) -> None:
        """ClarificationOption is_recommended should default to False."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationOption,
        )

        option = ClarificationOption(id="opt1", label="Option 1")
        assert option.is_recommended is False


class TestClarificationRequest:
    """Test ClarificationRequest model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_clarification_request_importable(self) -> None:
        """ClarificationRequest should be importable."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationRequest,
        )

        assert ClarificationRequest is not None

    def test_request_requires_question(self) -> None:
        """ClarificationRequest should require question field."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationRequest,
            ClarificationType,
        )

        request = ClarificationRequest(
            request_id="req-1",
            clarification_type=ClarificationType.TEXT,
            question="What is your preference?",
        )
        assert request.question == "What is your preference?"

    def test_request_accepts_options_for_choice_type(self) -> None:
        """ClarificationRequest should accept options for choice type."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationOption,
            ClarificationRequest,
            ClarificationType,
        )

        request = ClarificationRequest(
            request_id="req-1",
            clarification_type=ClarificationType.CHOICE,
            question="Which option?",
            options=[
                ClarificationOption(id="a", label="Option A"),
                ClarificationOption(id="b", label="Option B"),
            ],
        )
        assert len(request.options) == 2

    def test_request_accepts_placeholder(self) -> None:
        """ClarificationRequest should accept placeholder for text input."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationRequest,
            ClarificationType,
        )

        request = ClarificationRequest(
            request_id="req-1",
            clarification_type=ClarificationType.TEXT,
            question="Enter value:",
            placeholder="Type here...",
        )
        assert request.placeholder == "Type here..."

    def test_request_has_auto_generated_id(self) -> None:
        """ClarificationRequest can auto-generate request_id."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationRequest,
            ClarificationType,
        )

        request = ClarificationRequest(
            clarification_type=ClarificationType.CONFIRMATION,
            question="Proceed?",
        )
        assert request.request_id is not None
        assert len(request.request_id) > 0

    def test_request_accepts_context(self) -> None:
        """ClarificationRequest should accept context dict."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationRequest,
            ClarificationType,
        )

        request = ClarificationRequest(
            request_id="req-1",
            clarification_type=ClarificationType.TEXT,
            question="What?",
            context={"key": "value", "task_id": "task-1"},
        )
        assert request.context["key"] == "value"


class TestClarificationResponse:
    """Test ClarificationResponse model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_clarification_response_importable(self) -> None:
        """ClarificationResponse should be importable."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationResponse,
        )

        assert ClarificationResponse is not None

    def test_response_for_text_input(self) -> None:
        """ClarificationResponse should handle text input."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationResponse,
            ClarificationType,
        )

        response = ClarificationResponse(
            request_id="req-1",
            response_type=ClarificationType.TEXT,
            value="User typed this",
            responded_by="user@example.com",
        )
        assert response.value == "User typed this"

    def test_response_for_choice(self) -> None:
        """ClarificationResponse should handle choice selection."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationResponse,
            ClarificationType,
        )

        response = ClarificationResponse(
            request_id="req-1",
            response_type=ClarificationType.CHOICE,
            selected_option_id="opt2",
            responded_by="user@example.com",
        )
        assert response.selected_option_id == "opt2"

    def test_response_for_confirmation(self) -> None:
        """ClarificationResponse should handle confirmation."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationResponse,
            ClarificationType,
        )

        response = ClarificationResponse(
            request_id="req-1",
            response_type=ClarificationType.CONFIRMATION,
            confirmed=True,
            responded_by="user@example.com",
        )
        assert response.confirmed is True

    def test_response_has_responded_at_timestamp(self) -> None:
        """ClarificationResponse should auto-set responded_at."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationResponse,
            ClarificationType,
        )

        response = ClarificationResponse(
            request_id="req-1",
            response_type=ClarificationType.CONFIRMATION,
            confirmed=True,
            responded_by="user@example.com",
        )
        assert response.responded_at is not None


class TestClarificationHelperFunctions:
    """Test clarification helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_clarification_request_importable(self) -> None:
        """create_clarification_request function should be importable."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            create_clarification_request,
        )

        assert callable(create_clarification_request)

    def test_create_clarification_request_returns_state_update(self) -> None:
        """create_clarification_request should return state update dict."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            create_clarification_request,
        )

        state: dict[str, Any] = {"messages": ["hello"]}
        result = create_clarification_request(
            state=state,
            question="What do you want?",
            clarification_type="text",
        )

        assert "clarification_request" in result
        assert result.get("pending_clarification") is True

    def test_request_choice_helper(self) -> None:
        """request_choice should create choice clarification."""
        from mcp_server_langgraph.core.interrupts.clarification import request_choice

        state: dict[str, Any] = {}
        result = request_choice(
            state=state,
            question="Which format?",
            options=[
                {"id": "csv", "label": "CSV"},
                {"id": "json", "label": "JSON"},
            ],
        )

        assert result.get("pending_clarification") is True
        assert result["clarification_request"]["clarification_type"] == "choice"
        assert len(result["clarification_request"]["options"]) == 2

    def test_request_confirmation_helper(self) -> None:
        """request_confirmation should create confirmation clarification."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            request_confirmation,
        )

        state: dict[str, Any] = {}
        result = request_confirmation(
            state=state,
            question="Delete 100 records?",
        )

        assert result.get("pending_clarification") is True
        assert result["clarification_request"]["clarification_type"] == "confirmation"

    def test_request_choice_with_recommended(self) -> None:
        """request_choice should mark recommended option."""
        from mcp_server_langgraph.core.interrupts.clarification import request_choice

        state: dict[str, Any] = {}
        result = request_choice(
            state=state,
            question="Which approach?",
            options=[
                {"id": "fast", "label": "Fast"},
                {"id": "thorough", "label": "Thorough"},
            ],
            recommended="thorough",
        )

        options = result["clarification_request"]["options"]
        thorough_opt = next(o for o in options if o["id"] == "thorough")
        assert thorough_opt["is_recommended"] is True


class TestClarificationStateManagement:
    """Test clarification state updates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_clarification_request_preserved_in_state(self) -> None:
        """Clarification request should be preserved in state."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            create_clarification_request,
        )

        state: dict[str, Any] = {"existing_key": "value"}
        result = create_clarification_request(
            state=state,
            question="What?",
            clarification_type="text",
        )

        assert result["existing_key"] == "value"
        assert "clarification_request" in result

    def test_current_clarification_id_set(self) -> None:
        """current_clarification_id should be set in state."""
        from mcp_server_langgraph.core.interrupts.clarification import (
            create_clarification_request,
        )

        state: dict[str, Any] = {}
        result = create_clarification_request(
            state=state,
            question="What?",
            clarification_type="text",
        )

        assert "current_clarification_id" in result
        assert result["current_clarification_id"] is not None
