"""
MCP Sampling Protocol Handler (2025-11-25 Spec).

Implements sampling/createMessage for servers to request LLM completions
from clients. Enables agentic behaviors with nested LLM calls.

New in 2025-11-25 (SEP-1577):
- tools: list[SamplingTool] - Tool definitions for agentic loops
- toolChoice: ToolChoice - Tool selection preference (auto, none, tool)

Reference: https://modelcontextprotocol.io/specification/2025-11-25/client/sampling
"""

import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# SEP-1577: Sampling with Tools (New in 2025-11-25)
# =============================================================================


class SamplingTool(BaseModel):
    """Tool definition for sampling requests (SEP-1577).

    Allows servers to provide tool definitions when requesting LLM completions,
    enabling agentic loops where the LLM can call tools.
    """

    name: str
    description: str | None = None
    inputSchema: dict[str, Any]


class ToolChoice(BaseModel):
    """Tool selection preference for sampling requests (SEP-1577).

    Controls how the LLM should use the provided tools:
    - auto: LLM decides whether to use tools
    - none: LLM should not use any tools
    - tool: LLM must use the specified tool
    """

    type: Literal["auto", "none", "tool"]
    name: str | None = None  # Required when type="tool"


# =============================================================================
# Message Types
# =============================================================================


class SamplingMessageContent(BaseModel):
    """Content of a sampling message."""

    type: str  # "text", "image", "audio"
    text: str | None = None
    data: str | None = None  # Base64 for image/audio
    mimeType: str | None = None


class SamplingMessage(BaseModel):
    """A message in the sampling conversation."""

    role: str  # "user" or "assistant"
    content: SamplingMessageContent


class ModelHint(BaseModel):
    """Hint for model selection using substring matching."""

    name: str


class ModelPreferences(BaseModel):
    """Preferences for model selection."""

    hints: list[ModelHint] = Field(default_factory=list)
    costPriority: float | None = None  # 0-1 scale
    speedPriority: float | None = None  # 0-1 scale
    intelligencePriority: float | None = None  # 0-1 scale


class SamplingRequest(BaseModel):
    """Request for LLM completion from server to client.

    SEP-1577 (2025-11-25): Added tools and toolChoice parameters for agentic loops.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: int = Field(default=0)
    messages: list[SamplingMessage]
    modelPreferences: ModelPreferences = Field(default_factory=ModelPreferences)
    systemPrompt: str | None = None
    maxTokens: int = 1000
    # SEP-1577: Tool definitions for agentic loops
    tools: list[SamplingTool] | None = None
    toolChoice: ToolChoice | None = None
    status: str = "pending"
    rejection_reason: str | None = None
    response: "SamplingResponse | None" = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=None))

    def to_jsonrpc(self) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 request format."""
        params: dict[str, Any] = {
            "messages": [m.model_dump() for m in self.messages],
            "modelPreferences": self.modelPreferences.model_dump(),
            "systemPrompt": self.systemPrompt,
            "maxTokens": self.maxTokens,
        }

        # SEP-1577: Include tools and toolChoice if provided
        if self.tools is not None:
            params["tools"] = [t.model_dump() for t in self.tools]
        if self.toolChoice is not None:
            params["toolChoice"] = self.toolChoice.model_dump()

        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "sampling/createMessage",
            "params": params,
        }


class SamplingResponse(BaseModel):
    """Response from client with LLM completion."""

    role: str = "assistant"
    content: SamplingMessageContent
    model: str
    stopReason: str  # "endTurn", "stopSequence", "maxTokens"

    def to_jsonrpc(self, request_id: int) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 response format."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "role": self.role,
                "content": self.content.model_dump(),
                "model": self.model,
                "stopReason": self.stopReason,
            },
        }


class SamplingHandler:
    """Handler for managing sampling requests and responses."""

    def __init__(self) -> None:
        """Initialize the sampling handler."""
        self._pending: dict[str, SamplingRequest] = {}
        self._completed: dict[str, SamplingRequest] = {}
        self._next_request_id: int = 1

    def create_request(
        self,
        messages: list[SamplingMessage],
        model_preferences: ModelPreferences | None = None,
        system_prompt: str | None = None,
        max_tokens: int = 1000,
        tools: list[SamplingTool] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> SamplingRequest:
        """Create a new sampling request.

        Args:
            messages: Conversation messages
            model_preferences: Model selection preferences
            system_prompt: System prompt for the LLM
            max_tokens: Maximum tokens in response
            tools: Tool definitions for agentic loops (SEP-1577)
            tool_choice: Tool selection preference (SEP-1577)

        Returns:
            SamplingRequest object with pending status
        """
        request = SamplingRequest(
            id=str(uuid.uuid4()),
            request_id=self._next_request_id,
            messages=messages,
            modelPreferences=model_preferences or ModelPreferences(),
            systemPrompt=system_prompt,
            maxTokens=max_tokens,
            tools=tools,
            toolChoice=tool_choice,
        )
        self._next_request_id += 1
        self._pending[request.id] = request
        return request

    def get_pending_request(self, request_id: str) -> SamplingRequest | None:
        """Get a pending sampling request by ID.

        Args:
            request_id: Unique request identifier

        Returns:
            SamplingRequest if found and pending, None otherwise
        """
        return self._pending.get(request_id)

    def approve_request(self, request_id: str) -> SamplingRequest:
        """Approve a sampling request for execution.

        Args:
            request_id: ID of the request to approve

        Returns:
            Updated SamplingRequest with approved status

        Raises:
            ValueError: If request not found
        """
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Sampling request {request_id} not found")

        request.status = "approved"
        return request

    def reject_request(
        self,
        request_id: str,
        reason: str | None = None,
    ) -> SamplingRequest:
        """Reject a sampling request.

        Args:
            request_id: ID of the request to reject
            reason: Optional rejection reason

        Returns:
            Updated SamplingRequest with rejected status

        Raises:
            ValueError: If request not found
        """
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Sampling request {request_id} not found")

        request.status = "rejected"
        request.rejection_reason = reason

        # Move from pending to completed
        del self._pending[request_id]
        self._completed[request_id] = request

        return request

    def complete_request(
        self,
        request_id: str,
        response: SamplingResponse,
    ) -> SamplingRequest:
        """Complete a sampling request with LLM response.

        Args:
            request_id: ID of the request to complete
            response: LLM completion response

        Returns:
            Updated SamplingRequest with completed status

        Raises:
            ValueError: If request not found
        """
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Sampling request {request_id} not found")

        request.status = "completed"
        request.response = response

        # Move from pending to completed
        del self._pending[request_id]
        self._completed[request_id] = request

        return request

    def edit_request(
        self,
        request_id: str,
        messages: list[SamplingMessage] | None = None,
        system_prompt: str | None = None,
    ) -> SamplingRequest:
        """Edit a pending sampling request.

        Args:
            request_id: ID of the request to edit
            messages: New messages (optional)
            system_prompt: New system prompt (optional)

        Returns:
            Updated SamplingRequest

        Raises:
            ValueError: If request not found or not pending
        """
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Sampling request {request_id} not found")

        if request.status != "pending":
            raise ValueError(f"Cannot edit request with status {request.status}")

        if messages is not None:
            request.messages = messages
        if system_prompt is not None:
            request.systemPrompt = system_prompt

        return request

    def list_pending(self) -> list[SamplingRequest]:
        """List all pending sampling requests.

        Returns:
            List of pending request objects
        """
        return list(self._pending.values())


# =============================================================================
# LLM Execution
# =============================================================================


async def execute_sampling_request(
    request: SamplingRequest,
    llm: Any,
) -> SamplingResponse:
    """Execute a sampling request using the provided LLM.

    Args:
        request: Approved sampling request
        llm: LLM provider instance

    Returns:
        SamplingResponse with completion
    """
    # Build prompt from messages
    prompt = ""
    if request.systemPrompt:
        prompt = f"System: {request.systemPrompt}\n\n"

    for msg in request.messages:
        role = msg.role.capitalize()
        content = msg.content.text or ""
        prompt += f"{role}: {content}\n"

    # Call LLM
    result = await llm.agenerate([prompt])
    response_text = result.generations[0][0].text

    return SamplingResponse(
        role="assistant",
        content=SamplingMessageContent(type="text", text=response_text),
        model=getattr(llm, "model_name", "unknown"),
        stopReason="endTurn",
    )


def select_model_from_preferences(
    preferences: ModelPreferences,
    available_models: list[str],
) -> str:
    """Select best model based on preferences and availability.

    Args:
        preferences: Model preferences with hints and priorities
        available_models: List of available model IDs

    Returns:
        Selected model ID
    """
    # Try hints first (substring matching)
    for hint in preferences.hints:
        for model in available_models:
            if hint.name.lower() in model.lower():
                return model

    # Fall back to first available
    return available_models[0] if available_models else "default"


# =============================================================================
# Rate Limiting
# =============================================================================


class SamplingRateLimiter:
    """Rate limiter for sampling requests per server."""

    def __init__(
        self,
        max_requests_per_minute: int = 10,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute per server
        """
        self._max_requests = max_requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    def allow_request(self, server_id: str) -> bool:
        """Check if a request is allowed for the given server.

        Args:
            server_id: ID of the requesting server

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Clean old requests
        self._requests[server_id] = [t for t in self._requests[server_id] if t > window_start]

        # Check limit
        if len(self._requests[server_id]) >= self._max_requests:
            return False

        # Record request
        self._requests[server_id].append(now)
        return True

    def get_remaining(self, server_id: str) -> int:
        """Get remaining allowed requests for a server.

        Args:
            server_id: ID of the server

        Returns:
            Number of remaining requests in current window
        """
        now = time.time()
        window_start = now - 60

        current = len([t for t in self._requests[server_id] if t > window_start])

        return max(0, self._max_requests - current)
