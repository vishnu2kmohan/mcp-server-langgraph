"""HumanExpertTool for human-in-the-loop workflows.

Provides a tool that allows treating humans as experts in the
tool-calling loop. This enables agents to ask questions to human
experts when they need clarification or domain expertise.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


class RequestStatus(StrEnum):
    """Status of a human expert request.

    Lifecycle: PENDING -> ANSWERED
                      -> TIMEOUT
                      -> CANCELLED
    """

    PENDING = "pending"
    ANSWERED = "answered"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class HumanExpertRequest:
    """A request to a human expert.

    Attributes:
        question: The question to ask the human expert
        context: Contextual information for the question
        options: Optional list of pre-defined options to choose from
        timeout_seconds: Optional timeout for the request
    """

    question: str
    context: str
    options: list[str] | None = None
    timeout_seconds: int | None = None


@dataclass
class HumanExpertResponse:
    """A response from a human expert.

    Attributes:
        answer: The free-text answer from the human
        answered_by: Identifier of the human who answered
        selected_option: Index of the selected option (if options were provided)
        confidence: Optional confidence level (0-1) in the answer
    """

    answer: str
    answered_by: str
    selected_option: int | None = None
    confidence: float | None = None


@dataclass
class _PendingRequest:
    """Internal tracking for a pending request."""

    request_id: str
    request: HumanExpertRequest
    session_id: str
    status: RequestStatus = RequestStatus.PENDING
    response: HumanExpertResponse | None = None


class HumanExpertTool:
    """Tool for asking questions to human experts.

    This tool enables agents to pause execution and ask humans
    for clarification, domain expertise, or approval.

    Attributes:
        name: Tool name for registration
        description: Human-readable description of the tool
    """

    name: str = "human_expert"
    description: str = (
        "Ask a human expert for clarification, domain knowledge, or approval. "
        "Use when the task requires human judgment or domain expertise that "
        "cannot be reliably determined by the AI alone."
    )

    def __init__(self) -> None:
        """Initialize the HumanExpertTool."""
        self._requests: dict[str, _PendingRequest] = {}
        self._session_requests: dict[str, list[str]] = {}

    async def ask(
        self,
        request: HumanExpertRequest,
        *,
        session_id: str,
    ) -> str:
        """Create a request for human expert input.

        Args:
            request: The HumanExpertRequest with question and context
            session_id: Session identifier for tracking

        Returns:
            request_id: Unique identifier for the request
        """
        request_id = str(uuid.uuid4())

        pending = _PendingRequest(
            request_id=request_id,
            request=request,
            session_id=session_id,
            status=RequestStatus.PENDING,
        )
        self._requests[request_id] = pending

        if session_id not in self._session_requests:
            self._session_requests[session_id] = []
        self._session_requests[session_id].append(request_id)

        return request_id

    async def respond(
        self,
        request_id: str,
        response: HumanExpertResponse,
    ) -> None:
        """Submit a response for a pending request.

        Args:
            request_id: The request identifier
            response: The HumanExpertResponse from the human

        Raises:
            KeyError: If request_id is not found
        """
        if request_id not in self._requests:
            raise KeyError(f"Request not found: {request_id}")

        pending = self._requests[request_id]
        pending.status = RequestStatus.ANSWERED
        pending.response = response

    def get_status(self, request_id: str) -> RequestStatus:
        """Get the status of a request.

        Args:
            request_id: The request identifier

        Returns:
            RequestStatus of the request

        Raises:
            KeyError: If request_id is not found
        """
        if request_id not in self._requests:
            raise KeyError(f"Request not found: {request_id}")
        return self._requests[request_id].status

    def get_request(self, request_id: str) -> HumanExpertRequest | None:
        """Get the original request.

        Args:
            request_id: The request identifier

        Returns:
            HumanExpertRequest if found, None otherwise
        """
        pending = self._requests.get(request_id)
        if pending is None:
            return None
        return pending.request

    def get_response(self, request_id: str) -> HumanExpertResponse | None:
        """Get the response for a request.

        Args:
            request_id: The request identifier

        Returns:
            HumanExpertResponse if answered, None otherwise
        """
        pending = self._requests.get(request_id)
        if pending is None:
            return None
        return pending.response

    def list_pending(self, session_id: str) -> list[HumanExpertRequest]:
        """List all pending requests for a session.

        Args:
            session_id: Session identifier to filter by

        Returns:
            List of pending HumanExpertRequests
        """
        request_ids = self._session_requests.get(session_id, [])
        pending_requests: list[HumanExpertRequest] = []

        for request_id in request_ids:
            pending = self._requests.get(request_id)
            if pending and pending.status == RequestStatus.PENDING:
                pending_requests.append(pending.request)

        return pending_requests
