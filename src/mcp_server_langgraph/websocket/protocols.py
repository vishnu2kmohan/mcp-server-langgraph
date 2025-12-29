"""
WebSocket Protocol Models.

Pydantic models mirroring the TypeScript websocket-protocols.ts types.
These models provide:
    - Type-safe message validation
    - JSON Schema generation for documentation
    - Automatic serialization/deserialization

Protocol Version: 1.0.0

This file should be kept in sync with:
    frontend/src/types/websocket-protocols.ts
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Protocol Version
# =============================================================================

PROTOCOL_VERSION = "1.0.0"


def extract_protocol_version(version_string: str | None) -> tuple[int, int, int] | None:
    """
    Extract semantic version components from a version string.

    Args:
        version_string: Version string like "1.0.0" or "2.1.3"

    Returns:
        Tuple of (major, minor, patch) or None if invalid
    """
    if not version_string:
        return None

    try:
        parts = version_string.split(".")
        if len(parts) != 3:
            return None
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def is_version_compatible(client_version: str | None, server_version: str = PROTOCOL_VERSION) -> bool:
    """
    Check if client version is compatible with server version.

    Compatibility rules:
    - Major version must match exactly (breaking changes)
    - Minor version: server >= client (backwards compatible features)
    - Patch version: any (bug fixes only)

    Args:
        client_version: Client's protocol version string
        server_version: Server's protocol version (defaults to PROTOCOL_VERSION)

    Returns:
        True if versions are compatible, False otherwise
    """
    client = extract_protocol_version(client_version)
    server = extract_protocol_version(server_version)

    if not client or not server:
        return False

    # Major version must match exactly
    if client[0] != server[0]:
        return False

    # Server can support higher minor versions (backwards compatible)
    # Client can't require features from a newer server
    return client[1] <= server[1]


def validate_protocol_version(client_version: str | None) -> tuple[bool, str]:
    """
    Validate client protocol version against server.

    Args:
        client_version: The protocol version from client (from ?v= query param)

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, reason) if invalid
    """
    if not client_version:
        return (False, "Missing protocol version. Add ?v=1.0.0 to WebSocket URL.")

    client = extract_protocol_version(client_version)
    if not client:
        return (False, f"Invalid protocol version format: {client_version}. Expected semver like '1.0.0'.")

    server = extract_protocol_version(PROTOCOL_VERSION)
    if not server:
        # Should never happen with a valid PROTOCOL_VERSION constant
        return (False, "Server protocol version misconfigured.")

    if not is_version_compatible(client_version, PROTOCOL_VERSION):
        # Extract major version for clearer error message
        server = extract_protocol_version(PROTOCOL_VERSION)
        major_version = server[0] if server else 1
        return (
            False,
            f"Protocol version mismatch. Client: {client_version}, Server: {PROTOCOL_VERSION}. "
            f"Server supports versions {major_version}.x.x. Please refresh the page or update your client.",
        )

    return (True, "")


# =============================================================================
# Base Message Types
# =============================================================================


class MessageEnvelopeBase(BaseModel):
    """Base class for all WebSocket message envelopes."""

    type: str = Field(..., description="Message type discriminator")
    id: str | None = Field(None, description="Correlation ID for request-response")
    payload: dict[str, Any] | None = Field(None, description="Message payload")

    model_config = {"extra": "allow"}


# =============================================================================
# DevTools Protocol (/api/v1/ws/devtools)
# =============================================================================


class ConsoleLevel(str, Enum):
    """Console log level."""

    LOG = "log"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    DEBUG = "debug"


class ConsoleLogPayload(BaseModel):
    """Console log entry payload."""

    level: ConsoleLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    timestamp: str = Field(..., description="ISO timestamp")
    source: str = Field("system", description="Log source")
    id: str | None = Field(None, description="Entry ID")
    data: dict[str, Any] | None = Field(None, description="Additional data")


class ConsoleLogEntry(BaseModel):
    """Console log entry message (Server -> Client)."""

    type: Literal["console"] = "console"
    payload: ConsoleLogPayload


class NetworkStatus(str, Enum):
    """Network request status."""

    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"


class NetworkRequestPayload(BaseModel):
    """Network request entry payload."""

    id: str = Field(..., description="Request ID")
    url: str = Field(..., description="Request URL")
    method: str = Field(..., description="HTTP method")
    status: NetworkStatus = Field(NetworkStatus.PENDING, description="Request status")
    status_code: int | None = Field(None, description="HTTP status code")
    duration_ms: int | None = Field(None, description="Duration in milliseconds")
    timestamp: str = Field(..., description="ISO timestamp")
    request_headers: dict[str, str] | None = Field(None, description="Request headers")
    response_headers: dict[str, str] | None = Field(None, description="Response headers")
    error: str | None = Field(None, description="Error message if failed")


class NetworkRequestEntry(BaseModel):
    """Network request entry message (Server -> Client)."""

    type: Literal["network"] = "network"
    payload: NetworkRequestPayload


class NetworkUpdatePayload(BaseModel):
    """Network update payload for existing requests."""

    id: str = Field(..., description="Request ID to update")
    status: NetworkStatus | None = Field(None, description="Updated status")
    status_code: int | None = Field(None, description="HTTP status code")
    duration_ms: int | None = Field(None, description="Duration in milliseconds")
    response_headers: dict[str, str] | None = Field(None, description="Response headers")
    error: str | None = Field(None, description="Error message if failed")


class NetworkUpdateEntry(BaseModel):
    """Network update message for existing requests (Server -> Client)."""

    type: Literal["network_update"] = "network_update"
    payload: NetworkUpdatePayload


DevToolsMessage = ConsoleLogEntry | NetworkRequestEntry | NetworkUpdateEntry


# =============================================================================
# Traces Protocol (/api/v1/ws/traces)
# =============================================================================


class TraceSpanStatus(str, Enum):
    """Trace span status."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


class TraceSpanPayload(BaseModel):
    """Trace span entry payload."""

    span_id: str = Field(..., description="Span ID")
    trace_id: str = Field(..., description="Trace ID")
    parent_span_id: str | None = Field(None, description="Parent span ID")
    name: str = Field(..., description="Span name")
    start_time: int = Field(..., description="Start time in milliseconds")
    end_time: int = Field(..., description="End time in milliseconds")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    status: TraceSpanStatus = Field(TraceSpanStatus.UNSET, description="Span status")
    service_name: str = Field(..., description="Service name")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Span attributes")


class TraceSpanEntry(BaseModel):
    """Trace span entry message (Server -> Client)."""

    type: Literal["trace_span"] = "trace_span"
    payload: TraceSpanPayload


class TraceEventPayload(BaseModel):
    """Trace event entry payload."""

    span_id: str = Field(..., description="Parent span ID")
    name: str = Field(..., description="Event name")
    timestamp: str = Field(..., description="ISO timestamp")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Event attributes")


class TraceEventEntry(BaseModel):
    """Trace event entry message (Server -> Client)."""

    type: Literal["trace_event"] = "trace_event"
    payload: TraceEventPayload


class TraceSubscribePayload(BaseModel):
    """Trace subscribe payload (Client -> Server)."""

    service_filter: str | None = Field(None, description="Service name filter")
    trace_id: str | None = Field(None, description="Specific trace ID to follow")


class TraceSubscribeMessage(BaseModel):
    """Trace subscribe message (Client -> Server)."""

    type: Literal["subscribe"] = "subscribe"
    id: str | None = Field(None, description="Message correlation ID")
    payload: TraceSubscribePayload | None = None


TracesMessage = TraceSpanEntry | TraceEventEntry | TraceSubscribeMessage


# =============================================================================
# Budget Alerts Protocol (/api/v1/ws/budget/alerts)
# =============================================================================


class BudgetEntityType(str, Enum):
    """Budget entity types."""

    ORGANIZATION = "organization"
    PROJECT = "project"
    TEAM = "team"
    USER = "user"


class BudgetAlertStatus(str, Enum):
    """Budget alert status levels."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


class BudgetAlertPayload(BaseModel):
    """Budget alert entry payload."""

    entity_type: BudgetEntityType = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")
    status: BudgetAlertStatus = Field(..., description="Alert status")
    percent_used: float = Field(..., description="Percentage of budget used")
    current_spend: str = Field(..., description="Current spend amount")
    remaining: str = Field(..., description="Remaining budget")
    monthly_limit_usd: str = Field(..., description="Monthly limit in USD")
    message: str = Field("", description="Alert message")


class BudgetAlertEntry(BaseModel):
    """Budget alert entry message (Server -> Client)."""

    type: Literal["budget_alert"] = "budget_alert"
    payload: BudgetAlertPayload


class BudgetSubscribedPayload(BaseModel):
    """Subscription confirmation payload."""

    entity_ids: list[str] = Field(default_factory=list, description="Subscribed entity IDs")
    subscribe_all: bool = Field(False, description="Whether subscribed to all")


class BudgetSubscribedResponse(BaseModel):
    """Subscription confirmation (Server -> Client)."""

    type: Literal["subscribed"] = "subscribed"
    payload: BudgetSubscribedPayload


class BudgetSubscribeEntitiesPayload(BaseModel):
    """Subscribe entities payload."""

    entity_ids: list[str] = Field(..., description="Entity IDs to subscribe to")


class BudgetSubscribeEntitiesMessage(BaseModel):
    """Subscribe to specific entities (Client -> Server)."""

    type: Literal["subscribe_entities"] = "subscribe_entities"
    id: str | None = Field(None, description="Message correlation ID")
    payload: BudgetSubscribeEntitiesPayload


class BudgetSubscribeAllMessage(BaseModel):
    """Subscribe to all alerts (Client -> Server)."""

    type: Literal["subscribe_all"] = "subscribe_all"
    id: str | None = Field(None, description="Message correlation ID")
    payload: dict[str, Any] = Field(default_factory=dict)


BudgetAlertsMessage = BudgetAlertEntry | BudgetSubscribedResponse | BudgetSubscribeEntitiesMessage | BudgetSubscribeAllMessage


# =============================================================================
# AI Suggestions Protocol (/api/v1/ws/ai/suggestions)
# =============================================================================


class SuggestionResponsePayload(BaseModel):
    """AI suggestion response payload."""

    suggestion_id: str = Field(..., description="Suggestion ID")
    text: str = Field(..., description="Suggestion text")
    confidence: float = Field(..., description="Confidence score 0-1")
    reasoning: str | None = Field(None, description="Reasoning explanation")


class SuggestionResponseEntry(BaseModel):
    """AI suggestion response (Server -> Client)."""

    type: Literal["suggestion_response"] = "suggestion_response"
    payload: SuggestionResponsePayload


class SuggestionRequestPayload(BaseModel):
    """AI suggestion request payload."""

    session_id: str = Field(..., description="Session ID for context")
    input_text: str = Field(..., description="Current input text")
    cursor_position: int = Field(..., description="Cursor position in text")
    context_window: int = Field(500, description="Context window size")


class SuggestionRequestMessage(BaseModel):
    """Request AI suggestion (Client -> Server)."""

    type: Literal["suggestion_request"] = "suggestion_request"
    id: str | None = Field(None, description="Message correlation ID")
    payload: SuggestionRequestPayload


class SuggestionAcceptPayload(BaseModel):
    """Suggestion accept payload."""

    suggestion_id: str = Field(..., description="Accepted suggestion ID")


class SuggestionAcceptMessage(BaseModel):
    """Accept a suggestion (Client -> Server)."""

    type: Literal["suggestion_accept"] = "suggestion_accept"
    id: str | None = Field(None, description="Message correlation ID")
    payload: SuggestionAcceptPayload


class SuggestionRejectPayload(BaseModel):
    """Suggestion reject payload."""

    suggestion_id: str = Field(..., description="Rejected suggestion ID")
    reason: str | None = Field(None, description="Rejection reason")


class SuggestionRejectMessage(BaseModel):
    """Reject a suggestion (Client -> Server)."""

    type: Literal["suggestion_reject"] = "suggestion_reject"
    id: str | None = Field(None, description="Message correlation ID")
    payload: SuggestionRejectPayload


class ContextUpdatePayload(BaseModel):
    """Context update payload."""

    session_id: str = Field(..., description="Session ID")
    context: str = Field(..., description="Context string")


class ContextUpdateMessage(BaseModel):
    """Update session context (Client -> Server)."""

    type: Literal["context_update"] = "context_update"
    id: str | None = Field(None, description="Message correlation ID")
    payload: ContextUpdatePayload


AISuggestionsMessage = (
    SuggestionResponseEntry
    | SuggestionRequestMessage
    | SuggestionAcceptMessage
    | SuggestionRejectMessage
    | ContextUpdateMessage
)


# =============================================================================
# MCP Aggregated Protocol (/api/v1/ws/mcp/aggregated)
# =============================================================================


class MCPServerState(str, Enum):
    """MCP server connection states."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"


class MCPServerStatusPayload(BaseModel):
    """MCP server status payload."""

    server_id: str = Field(..., description="MCP server ID")
    name: str = Field(..., description="Server name")
    status: MCPServerState = Field(..., description="Connection status")
    tools_count: int = Field(0, description="Number of available tools")
    last_seen: str | None = Field(None, description="Last seen timestamp")


class MCPServerStatusEntry(BaseModel):
    """MCP server status update (Server -> Client)."""

    type: Literal["server_status"] = "server_status"
    payload: MCPServerStatusPayload


class MCPToolCallPayload(BaseModel):
    """MCP tool call payload."""

    call_id: str = Field(..., description="Tool call ID")
    server_id: str = Field(..., description="MCP server ID")
    tool_name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    status: str = Field("pending", description="Call status")
    result: Any | None = Field(None, description="Call result")
    error: str | None = Field(None, description="Error message if failed")
    started_at: str | None = Field(None, description="Start timestamp")
    completed_at: str | None = Field(None, description="Completion timestamp")


class MCPToolCallEntry(BaseModel):
    """MCP tool call update (Server -> Client)."""

    type: Literal["tool_call"] = "tool_call"
    payload: MCPToolCallPayload


MCPAggregatedMessage = MCPServerStatusEntry | MCPToolCallEntry


# =============================================================================
# Error Protocol (Shared)
# =============================================================================


class WebSocketErrorPayload(BaseModel):
    """WebSocket error payload."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    retryable: bool = Field(False, description="Whether client should retry")


class WebSocketError(BaseModel):
    """Error message (Server -> Client)."""

    type: Literal["error"] = "error"
    payload: WebSocketErrorPayload


# =============================================================================
# Type Guards (Python equivalents)
# =============================================================================


def is_console_log_entry(data: dict[str, Any]) -> bool:
    """Check if data is a ConsoleLogEntry."""
    return isinstance(data, dict) and data.get("type") == "console" and "payload" in data


def is_network_request_entry(data: dict[str, Any]) -> bool:
    """Check if data is a NetworkRequestEntry."""
    return isinstance(data, dict) and data.get("type") == "network" and "payload" in data


def is_network_update_entry(data: dict[str, Any]) -> bool:
    """Check if data is a NetworkUpdateEntry."""
    return isinstance(data, dict) and data.get("type") == "network_update" and "payload" in data


def is_trace_span_entry(data: dict[str, Any]) -> bool:
    """Check if data is a TraceSpanEntry."""
    return isinstance(data, dict) and data.get("type") == "trace_span" and "payload" in data


def is_trace_event_entry(data: dict[str, Any]) -> bool:
    """Check if data is a TraceEventEntry."""
    return isinstance(data, dict) and data.get("type") == "trace_event" and "payload" in data


def is_budget_alert_entry(data: dict[str, Any]) -> bool:
    """Check if data is a BudgetAlertEntry."""
    return isinstance(data, dict) and data.get("type") == "budget_alert" and "payload" in data


def is_suggestion_response_entry(data: dict[str, Any]) -> bool:
    """Check if data is a SuggestionResponseEntry."""
    return isinstance(data, dict) and data.get("type") == "suggestion_response" and "payload" in data


def is_websocket_error(data: dict[str, Any]) -> bool:
    """Check if data is a WebSocketError."""
    return isinstance(data, dict) and data.get("type") == "error" and "payload" in data


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_message(data: dict[str, Any], model_type: type[BaseModel]) -> BaseModel:
    """
    Validate and parse a message dict into a Pydantic model.

    Args:
        data: The raw message dictionary
        model_type: The Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance

    Raises:
        pydantic.ValidationError: If validation fails
    """
    return model_type.model_validate(data)


def parse_message_envelope(data: dict[str, Any]) -> MessageEnvelopeBase:
    """
    Parse a raw message into the appropriate typed model.

    Returns the most specific model type based on the message type.
    Falls back to MessageEnvelopeBase if type is unknown.
    """
    msg_type = data.get("type", "")

    # DevTools
    if msg_type == "console":
        return ConsoleLogEntry.model_validate(data)
    if msg_type == "network":
        return NetworkRequestEntry.model_validate(data)
    if msg_type == "network_update":
        return NetworkUpdateEntry.model_validate(data)

    # Traces
    if msg_type == "trace_span":
        return TraceSpanEntry.model_validate(data)
    if msg_type == "trace_event":
        return TraceEventEntry.model_validate(data)

    # Budget Alerts
    if msg_type == "budget_alert":
        return BudgetAlertEntry.model_validate(data)
    if msg_type == "subscribed":
        return BudgetSubscribedResponse.model_validate(data)

    # AI Suggestions
    if msg_type == "suggestion_response":
        return SuggestionResponseEntry.model_validate(data)
    if msg_type == "suggestion_request":
        return SuggestionRequestMessage.model_validate(data)

    # MCP Aggregated
    if msg_type == "server_status":
        return MCPServerStatusEntry.model_validate(data)
    if msg_type == "tool_call":
        return MCPToolCallEntry.model_validate(data)

    # Error
    if msg_type == "error":
        return WebSocketError.model_validate(data)

    # Unknown - return base envelope
    return MessageEnvelopeBase.model_validate(data)
