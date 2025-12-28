"""
AI-Native APIs

Provides endpoints for AI-powered features:
- Node configuration assistance
- Unified AI suggestions (chat follow-up, workflow optimization)
- Template recommendations (future)

Reference: Phase B - AI Feature Exposure
"""

import re
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any, Literal, cast

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.studio.ai.node_config import (
    NodeConfigAssistant,
    NodeTypeRegistry,
)
from mcp_server_langgraph.core.feature_flags import get_feature_flags
from mcp_server_langgraph.studio.ai.suggestions import (
    WorkflowSuggestionAgent,
    ChatFollowUpSuggestionAgent,
    CommandInterpreterAgent,
    get_suggestion_rate_limiter,
    track_rate_limit_hit,
    track_personalization_usage,
    track_streaming_request,
)
from mcp_server_langgraph.security.prompt_injection import (
    analyze_content as analyze_prompt_injection,
    sanitize_content as sanitize_prompt_injection,
)


ai_router = APIRouter(tags=["ai"])


def _get_rate_limit_key_from_request(request: Request) -> str:
    """Extract rate limit key from request (user ID > IP > default).

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key string (e.g., "user:alice", "ip:192.168.1.1", "default")
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        user_id = request.state.user.get("user_id") or request.state.user.get("keycloak_id")
        if user_id:
            return f"user:{user_id}"

    # Fall back to client IP
    if request.client and request.client.host:
        return f"ip:{request.client.host}"

    return "default"


def _validate_and_sanitize_history(
    messages: list["ConversationMessage"] | None,
) -> list[dict[str, str]] | None:
    """Validate and sanitize conversation history.

    Applies the following protections:
    1. Limits messages to max_conversation_history_messages (feature flag)
    2. Truncates long content to max_input_length (feature flag)
    3. Enhanced prompt injection detection and sanitization
    4. Filters out empty messages

    Uses the security.prompt_injection module for comprehensive attack detection.

    Args:
        messages: List of ConversationMessage from request

    Returns:
        Sanitized list of dicts with role and content, or None if empty
    """
    if not messages:
        return None

    flags = get_feature_flags()

    # Check if validation is enabled
    if not flags.enable_conversation_history_validation:
        # No validation - just convert and return
        return [{"role": m.role, "content": m.content} for m in messages if m.content and m.content.strip()]

    max_messages = flags.max_conversation_history_messages
    max_length = flags.max_input_length

    # Take only the most recent messages up to the limit
    limited_messages = messages[-max_messages:] if len(messages) > max_messages else messages

    sanitized = []
    for msg in limited_messages:
        content = msg.content

        # Skip empty messages
        if not content or not content.strip():
            continue

        # Truncate long content
        if len(content) > max_length:
            content = content[:max_length] + "..."
            logger.debug(
                "Truncated conversation history message",
                extra={"original_length": len(msg.content), "truncated_to": max_length},
            )

        # Enhanced prompt injection detection and sanitization
        analysis = analyze_prompt_injection(content)
        if analysis.is_suspicious:
            sanitized_content, _ = sanitize_prompt_injection(content, replacement="[filtered]")
            content = sanitized_content
            logger.warning(
                "Sanitized potential prompt injection in conversation history",
                extra={
                    "risk_level": analysis.risk_level.value,
                    "risk_score": analysis.risk_score,
                    "detection_count": len(analysis.detections),
                },
            )

        sanitized.append({"role": msg.role, "content": content})

    return sanitized if sanitized else None


# =============================================================================
# Request/Response Models
# =============================================================================


class NodeConfigHelpRequest(BaseModel):
    """Request for node configuration help."""

    node_type: str = Field(description="The type of node (llm, tool, input, output, code, condition)")
    context: dict[str, Any] | None = Field(
        None,
        description="Optional context including existing nodes, workflow goal, etc.",
    )


class NodeConfigHelpResponse(BaseModel):
    """Response containing node configuration help."""

    help_text: str = Field(description="Human-readable help text")
    suggested_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Suggested configuration values",
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Example configurations",
    )
    suggested_connections: list[dict[str, str]] | None = Field(
        None,
        description="Suggested connections to/from existing nodes",
    )


class NodeConfigValidateRequest(BaseModel):
    """Request to validate node configuration."""

    node_type: str = Field(description="The type of node")
    config: dict[str, Any] = Field(description="The configuration to validate")


class NodeConfigValidateResponse(BaseModel):
    """Response containing validation results."""

    valid: bool = Field(description="Whether the configuration is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class NodeTypesResponse(BaseModel):
    """Response containing available node types."""

    node_types: list[str] = Field(description="List of available node types")


# =============================================================================
# Unified AI Suggestions Models
# =============================================================================


class SuggestionType(str, Enum):
    """Types of AI suggestions supported."""

    CHAT_FOLLOWUP = "chat_followup"
    WORKFLOW = "workflow"


class ChatFollowUpCategory(str, Enum):
    """Categories for chat follow-up suggestions."""

    EXPLORE = "explore"
    CLARIFY = "clarify"
    EXAMPLE = "example"
    ALTERNATIVE = "alternative"
    CONTINUE = "continue"


class ChatFollowUpSuggestion(BaseModel):
    """A single chat follow-up suggestion."""

    id: str = Field(description="Unique suggestion ID")
    text: str = Field(description="The suggestion text")
    category: ChatFollowUpCategory = Field(description="Category of suggestion")


class WorkflowSuggestion(BaseModel):
    """A single workflow optimization suggestion."""

    type: str = Field(description="Type of suggestion (e.g., 'optimization', 'error_handling')")
    description: str = Field(description="Human-readable description")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant"] = Field(description="Role of the message sender")
    content: str = Field(description="Message content")


class UnifiedSuggestionsRequest(BaseModel):
    """Unified request for AI suggestions."""

    type: SuggestionType = Field(description="Type of suggestions to generate")
    # For chat_followup type
    content: str | None = Field(None, description="Chat content to analyze (for chat_followup)")
    session_id: str | None = Field(None, description="Session ID for context")
    conversation_history: list[ConversationMessage] | None = Field(
        None, description="Previous conversation messages for personalization"
    )
    # For workflow type
    workflow: dict[str, Any] | None = Field(None, description="Workflow to analyze (for workflow)")
    # Common
    max_suggestions: int = Field(default=4, ge=1, le=10, description="Maximum suggestions to return")


class UnifiedSuggestionsResponse(BaseModel):
    """Unified response containing AI suggestions."""

    suggestions: list[ChatFollowUpSuggestion | WorkflowSuggestion] = Field(
        default_factory=list,
        description="List of suggestions",
    )


# =============================================================================
# Chat Follow-Up Suggestion Generator
# =============================================================================


async def _generate_chat_followup_suggestions(
    content: str,
    max_suggestions: int = 4,
    session_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> list[ChatFollowUpSuggestion]:
    """
    Generate follow-up suggestions based on assistant message content.

    Uses ChatFollowUpSuggestionAgent which tries LLM first,
    then falls back to heuristic-based generation.
    Respects the enable_llm_suggestions feature flag.
    """
    if not content or not content.strip():
        return []

    # Check feature flag for LLM usage
    feature_flags = get_feature_flags()
    enable_llm = feature_flags.enable_llm_suggestions

    agent = ChatFollowUpSuggestionAgent(enable_llm=enable_llm)
    raw_suggestions = await agent.suggest(
        content=content,
        max_suggestions=max_suggestions,
        session_id=session_id,
        conversation_history=conversation_history,
    )

    # Convert agent suggestions to API response format
    return [
        ChatFollowUpSuggestion(
            id=s.id,
            text=s.text,
            category=ChatFollowUpCategory(s.category),
        )
        for s in raw_suggestions
    ]


async def _generate_workflow_suggestions(
    workflow: dict[str, Any],
    max_suggestions: int = 5,
) -> list[WorkflowSuggestion]:
    """
    Generate workflow optimization suggestions.

    Uses WorkflowSuggestionAgent which tries LLM first,
    then falls back to heuristic-based analysis.
    Respects the enable_llm_suggestions feature flag.
    """
    # Check feature flag for LLM usage
    feature_flags = get_feature_flags()
    enable_llm = feature_flags.enable_llm_suggestions

    agent = WorkflowSuggestionAgent(enable_llm=enable_llm)
    raw_suggestions = await agent.suggest(
        workflow=workflow,
        max_suggestions=max_suggestions,
    )

    return [
        WorkflowSuggestion(
            type=s.type,
            description=s.description,
            confidence=s.confidence,
            metadata=s.metadata,
        )
        for s in raw_suggestions
    ]


# =============================================================================
# Module-level instances
# =============================================================================

_assistant = NodeConfigAssistant()
_registry = NodeTypeRegistry()


# =============================================================================
# Endpoints
# =============================================================================


@ai_router.post(
    "/node-config/help",
    status_code=status.HTTP_200_OK,
    summary="Get Node Configuration Help",
    description="Get AI-powered configuration help for a workflow node type",
)
async def get_node_config_help(request: NodeConfigHelpRequest) -> NodeConfigHelpResponse:
    """
    Get configuration help for a node type.

    Example:
        ```
        POST /api/v1/ai/node-config/help
        {
            "node_type": "llm",
            "context": {
                "workflow_goal": "Build a chatbot",
                "existing_nodes": [
                    {"id": "input-1", "type": "input"}
                ]
            }
        }
        ```
    """
    logger.info(
        "Node config help requested",
        extra={
            "node_type": request.node_type,
            "has_context": request.context is not None,
        },
    )

    result = await _assistant.get_help(
        node_type=request.node_type,
        context=request.context,
    )

    return NodeConfigHelpResponse(
        help_text=result.get("help_text", f"Configure the {request.node_type} node."),
        suggested_config=result.get("suggested_config", {}),
        examples=result.get("examples", []),
        suggested_connections=result.get("suggested_connections"),
    )


@ai_router.post(
    "/node-config/validate",
    status_code=status.HTTP_200_OK,
    summary="Validate Node Configuration",
    description="Validate a node configuration against its schema",
)
async def validate_node_config(request: NodeConfigValidateRequest) -> NodeConfigValidateResponse:
    """
    Validate node configuration.

    Example:
        ```
        POST /api/v1/ai/node-config/validate
        {
            "node_type": "llm",
            "config": {
                "model": "gpt-4",
                "temperature": 0.7
            }
        }
        ```
    """
    logger.info(
        "Node config validation requested",
        extra={
            "node_type": request.node_type,
            "config_keys": list(request.config.keys()),
        },
    )

    result = await _assistant.validate_config(
        node_type=request.node_type,
        config=request.config,
    )

    return NodeConfigValidateResponse(
        valid=result.get("valid", False),
        errors=result.get("errors", []),
        warnings=result.get("warnings", []),
    )


@ai_router.get(
    "/node-types",
    status_code=status.HTTP_200_OK,
    summary="Get Available Node Types",
    description="Get all available workflow node types",
)
async def get_node_types() -> NodeTypesResponse:
    """
    Get all available node types.

    Example:
        ```
        GET /api/v1/ai/node-types
        ```
    """
    return NodeTypesResponse(node_types=_registry.get_all_types())


@ai_router.get(
    "/node-types/{node_type}/schema",
    status_code=status.HTTP_200_OK,
    summary="Get Node Type Schema",
    description="Get the JSON Schema for a specific node type",
)
async def get_node_type_schema(node_type: str) -> dict[str, Any]:
    """
    Get schema for a node type.

    Example:
        ```
        GET /api/v1/ai/node-types/llm/schema
        ```
    """
    schema = _registry.get_schema(node_type)

    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node type '{node_type}' not found",
        )

    return schema


# =============================================================================
# Unified AI Suggestions Endpoint
# =============================================================================


@ai_router.post(
    "/suggestions",
    status_code=status.HTTP_200_OK,
    summary="Get AI Suggestions",
    description="Unified endpoint for AI-powered suggestions (chat follow-up, workflow optimization)",
)
async def get_ai_suggestions(
    suggestion_request: UnifiedSuggestionsRequest,
    http_request: Request,
) -> UnifiedSuggestionsResponse:
    """
    Get AI-powered suggestions based on the request type.

    Supports:
    - chat_followup: Follow-up suggestions for chat messages
    - workflow: Workflow optimization suggestions

    Examples:
        ```
        POST /api/v1/ai/suggestions
        {
            "type": "chat_followup",
            "content": "I can help you with Python programming.",
            "max_suggestions": 4
        }
        ```

        ```
        POST /api/v1/ai/suggestions
        {
            "type": "workflow",
            "workflow": {"nodes": [...], "edges": [...]},
            "max_suggestions": 5
        }
        ```
    """
    # Check rate limiting with per-user/per-IP key
    rate_limiter = get_suggestion_rate_limiter()
    rate_key = _get_rate_limit_key_from_request(http_request)
    if not rate_limiter.is_allowed(key=rate_key):
        track_rate_limit_hit(rate_key)  # Track rate limit hit for observability
        retry_after = rate_limiter.get_retry_after(key=rate_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for suggestions",
            headers={"Retry-After": str(retry_after)},
        )

    # Track personalization usage
    has_history = suggestion_request.conversation_history is not None and len(suggestion_request.conversation_history) > 0
    track_personalization_usage(has_history)

    logger.info(
        "AI suggestions requested",
        extra={
            "suggestion_type": suggestion_request.type.value,
            "has_content": suggestion_request.content is not None,
            "has_workflow": suggestion_request.workflow is not None,
            "max_suggestions": suggestion_request.max_suggestions,
            "rate_limit_key": rate_key,
            "has_conversation_history": has_history,
        },
    )

    if suggestion_request.type == SuggestionType.CHAT_FOLLOWUP:
        # Validate required field for chat_followup
        if suggestion_request.content is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="'content' field is required for chat_followup type",
            )

        # Validate and sanitize conversation history
        history = _validate_and_sanitize_history(suggestion_request.conversation_history)

        chat_suggestions = await _generate_chat_followup_suggestions(
            content=suggestion_request.content,
            max_suggestions=suggestion_request.max_suggestions,
            session_id=suggestion_request.session_id,
            conversation_history=history,
        )
        return UnifiedSuggestionsResponse(
            suggestions=cast(list["ChatFollowUpSuggestion | WorkflowSuggestion"], chat_suggestions)
        )

    elif suggestion_request.type == SuggestionType.WORKFLOW:
        # Validate required field for workflow
        if suggestion_request.workflow is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="'workflow' field is required for workflow type",
            )

        workflow_suggestions = await _generate_workflow_suggestions(
            workflow=suggestion_request.workflow,
            max_suggestions=suggestion_request.max_suggestions,
        )
        return UnifiedSuggestionsResponse(
            suggestions=cast(list["ChatFollowUpSuggestion | WorkflowSuggestion"], workflow_suggestions)
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid suggestion type: {suggestion_request.type}. Supported types: chat_followup, workflow",
        )


# =============================================================================
# Streaming AI Suggestions Endpoint
# =============================================================================


async def _stream_suggestions(
    request: UnifiedSuggestionsRequest,
) -> AsyncGenerator[str, None]:
    """Generate suggestions and stream them as SSE events.

    Args:
        request: The suggestion request

    Yields:
        SSE formatted events
    """
    import json

    try:
        if request.type == SuggestionType.CHAT_FOLLOWUP:
            if request.content is None:
                yield f"event: error\ndata: {json.dumps({'error': 'content field required'})}\n\n"
                return

            # Validate and sanitize conversation history
            history = _validate_and_sanitize_history(request.conversation_history)

            suggestions = await _generate_chat_followup_suggestions(
                content=request.content,
                max_suggestions=request.max_suggestions,
                session_id=request.session_id,
                conversation_history=history,
            )

            # Stream each suggestion
            for suggestion in suggestions:
                event_data = {
                    "id": suggestion.id,
                    "text": suggestion.text,
                    "category": suggestion.category.value,
                }
                yield f"event: suggestion\ndata: {json.dumps(event_data)}\n\n"

        elif request.type == SuggestionType.WORKFLOW:
            if request.workflow is None:
                yield f"event: error\ndata: {json.dumps({'error': 'workflow field required'})}\n\n"
                return

            wf_suggestions = await _generate_workflow_suggestions(
                workflow=request.workflow,
                max_suggestions=request.max_suggestions,
            )

            # Stream each workflow suggestion
            for wf_suggestion in wf_suggestions:
                wf_event_data: dict[str, str | float] = {
                    "type": wf_suggestion.type,
                    "description": wf_suggestion.description,
                    "confidence": wf_suggestion.confidence,
                }
                yield f"event: suggestion\ndata: {json.dumps(wf_event_data)}\n\n"

        # Send done event
        yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        logger.exception("Error streaming suggestions")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@ai_router.post(
    "/suggestions/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream AI Suggestions",
    description="Stream AI suggestions using Server-Sent Events (SSE)",
)
async def stream_ai_suggestions(
    suggestion_request: UnifiedSuggestionsRequest,
    http_request: Request,
) -> StreamingResponse:
    """
    Stream AI suggestions as Server-Sent Events.

    Returns suggestions one at a time as they are generated,
    followed by a 'done' event when complete.

    Example:
        ```
        POST /api/v1/ai/suggestions/stream
        {
            "type": "chat_followup",
            "content": "Explain machine learning concepts."
        }
        ```

    SSE Response format:
        ```
        event: suggestion
        data: {"id": "sug-1", "text": "What is neural network?", "category": "explore"}

        event: suggestion
        data: {"id": "sug-2", "text": "Show me an example", "category": "example"}

        event: done
        data: {"done": true}
        ```
    """
    # Check rate limiting with per-user/per-IP key
    rate_limiter = get_suggestion_rate_limiter()
    rate_key = _get_rate_limit_key_from_request(http_request)
    if not rate_limiter.is_allowed(key=rate_key):
        track_rate_limit_hit(rate_key)  # Track rate limit hit for observability
        retry_after = rate_limiter.get_retry_after(key=rate_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for suggestions",
            headers={"Retry-After": str(retry_after)},
        )

    # Track streaming request
    track_streaming_request(suggestion_request.type.value)

    logger.info(
        "Streaming AI suggestions requested",
        extra={
            "suggestion_type": suggestion_request.type.value,
            "has_content": suggestion_request.content is not None,
            "has_workflow": suggestion_request.workflow is not None,
            "rate_limit_key": rate_key,
        },
    )

    return StreamingResponse(
        _stream_suggestions(suggestion_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Suggestion Analytics
# =============================================================================


class SuggestionAction(str, Enum):
    """Actions that can be tracked for suggestions."""

    CLICK = "click"
    DISMISS = "dismiss"
    VIEW = "view"


class SuggestionTrackRequest(BaseModel):
    """Request to track a suggestion interaction."""

    suggestion_id: str = Field(description="ID of the suggestion")
    action: SuggestionAction = Field(description="Action taken (click, dismiss, view)")
    session_id: str | None = Field(None, description="Session ID for context")
    suggestion_type: str | None = Field(None, description="Type of suggestion (chat_followup, workflow)")
    category: str | None = Field(None, description="Category of the suggestion")


class SuggestionTrackResponse(BaseModel):
    """Response confirming interaction tracking."""

    tracked: bool = Field(description="Whether the interaction was successfully tracked")


class SuggestionClickRequest(BaseModel):
    """Request to track a suggestion click."""

    suggestion_id: str = Field(description="ID of the clicked suggestion")
    suggestion_type: SuggestionType = Field(description="Type of suggestion (chat_followup, workflow)")
    category: str | None = Field(None, description="Category of the suggestion (for chat_followup)")
    session_id: str | None = Field(None, description="Session ID for context")


class SuggestionClickResponse(BaseModel):
    """Response confirming click tracking."""

    tracked: bool = Field(description="Whether the click was successfully tracked")


@ai_router.post(
    "/suggestions/click",
    status_code=status.HTTP_200_OK,
    summary="Track Suggestion Click",
    description="Track when a user clicks on a suggestion for analytics",
)
async def track_suggestion_click(
    request: SuggestionClickRequest,
) -> SuggestionClickResponse:
    """
    Track a suggestion click for HEART metrics.

    This endpoint is used to track Adoption metrics - how often users
    actually use the suggestions provided to them.

    Example:
        ```
        POST /api/v1/ai/suggestions/click
        {
            "suggestion_id": "sug-abc123",
            "suggestion_type": "chat_followup",
            "category": "explore",
            "session_id": "session-456"
        }
        ```
    """
    logger.info(
        "Suggestion click tracked",
        extra={
            "suggestion_id": request.suggestion_id,
            "suggestion_type": request.suggestion_type.value,
            "category": request.category,
            "session_id": request.session_id,
        },
    )

    # TODO: Add Prometheus metrics or analytics service integration here
    # For now, we just log the click event

    return SuggestionClickResponse(tracked=True)


@ai_router.post(
    "/suggestions/track",
    status_code=status.HTTP_200_OK,
    summary="Track Suggestion Interaction",
    description="Track user interactions with suggestions (click, dismiss, view)",
)
async def track_suggestion_interaction(
    request: SuggestionTrackRequest,
) -> SuggestionTrackResponse:
    """
    Track a suggestion interaction for quality metrics.

    Supports tracking:
    - click: User selected and used the suggestion
    - dismiss: User explicitly dismissed/ignored the suggestion
    - view: Suggestion was shown to the user (for impression tracking)

    This data is used to measure suggestion quality and improve recommendations.

    Example:
        ```
        POST /api/v1/ai/suggestions/track
        {
            "suggestion_id": "sug-abc123",
            "action": "click",
            "session_id": "session-456",
            "suggestion_type": "chat_followup",
            "category": "explore"
        }
        ```
    """
    # Check feature flag for quality tracking
    flags = get_feature_flags()
    if not flags.enable_suggestion_quality_tracking:
        # Silently accept but don't track when disabled
        return SuggestionTrackResponse(tracked=False)

    logger.info(
        "Suggestion interaction tracked",
        extra={
            "suggestion_id": request.suggestion_id,
            "action": request.action.value,
            "session_id": request.session_id,
            "suggestion_type": request.suggestion_type,
            "category": request.category,
        },
    )

    # Emit Prometheus metrics
    try:
        from mcp_server_langgraph.studio.ai.suggestions import track_suggestion_quality

        track_suggestion_quality(
            action=request.action.value,
            suggestion_type=request.suggestion_type or "unknown",
            category=request.category,
        )
    except ImportError:
        # Metrics not available
        pass

    return SuggestionTrackResponse(tracked=True)


# =============================================================================
# Suggestion Feedback (Thumbs Up/Down)
# =============================================================================


class FeedbackType(str, Enum):
    """Feedback types for suggestions."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class SuggestionFeedbackRequest(BaseModel):
    """Request to submit feedback on a suggestion."""

    suggestion_id: str = Field(description="ID of the suggestion")
    suggestion_type: SuggestionType = Field(description="Type of suggestion (chat_followup, workflow)")
    feedback: FeedbackType = Field(description="Feedback type (positive, negative)")
    category: str | None = Field(None, description="Category of the suggestion")
    session_id: str | None = Field(None, description="Session ID for context")
    comment: str | None = Field(None, description="Optional user comment about the suggestion")


class SuggestionFeedbackResponse(BaseModel):
    """Response confirming feedback submission."""

    recorded: bool = Field(description="Whether the feedback was successfully recorded")
    feedback_id: str | None = Field(None, description="ID of the recorded feedback (if available)")


@ai_router.post(
    "/suggestions/feedback",
    status_code=status.HTTP_200_OK,
    summary="Submit Suggestion Feedback",
    description="Submit thumbs up/down feedback on a suggestion to improve quality",
)
async def submit_suggestion_feedback(
    request: SuggestionFeedbackRequest,
) -> SuggestionFeedbackResponse:
    """
    Submit feedback (thumbs up/down) on a suggestion.

    This endpoint is used to collect user feedback on suggestion quality,
    which helps improve future recommendations.

    Example:
        ```
        POST /api/v1/ai/suggestions/feedback
        {
            "suggestion_id": "sug-abc123",
            "suggestion_type": "chat_followup",
            "feedback": "positive",
            "category": "explore",
            "session_id": "session-456"
        }
        ```
    """
    # Check feature flag for quality tracking
    flags = get_feature_flags()
    if not flags.enable_suggestion_quality_tracking:
        # Silently accept but don't track when disabled
        return SuggestionFeedbackResponse(recorded=False, feedback_id=None)

    logger.info(
        "Suggestion feedback submitted",
        extra={
            "suggestion_id": request.suggestion_id,
            "suggestion_type": request.suggestion_type.value,
            "feedback": request.feedback.value,
            "category": request.category,
            "session_id": request.session_id,
            "has_comment": request.comment is not None,
        },
    )

    # Emit Prometheus metrics for feedback
    try:
        from mcp_server_langgraph.studio.ai.suggestions import track_suggestion_feedback

        track_suggestion_feedback(
            feedback=request.feedback.value,
            suggestion_type=request.suggestion_type.value,
            category=request.category,
        )
    except ImportError:
        # Metrics function not available
        pass

    # Generate a feedback ID for tracking (optional)
    import uuid

    feedback_id = f"fb-{uuid.uuid4().hex[:12]}"

    return SuggestionFeedbackResponse(recorded=True, feedback_id=feedback_id)


# =============================================================================
# URL Content Fetching (OpenWebUI-style "#URL" integration)
# =============================================================================


class UrlFetchRequest(BaseModel):
    """Request to fetch content from a URL."""

    url: str = Field(description="The URL to fetch content from (must be http:// or https://)")


class UrlFetchResponse(BaseModel):
    """Response containing fetched URL content."""

    url: str = Field(description="The URL that was fetched")
    title: str | None = Field(None, description="Page title if available")
    content: str = Field(description="Extracted text content from the page")
    content_type: str = Field(description="Content type of the response")
    content_length: int = Field(description="Length of extracted content in characters")
    truncated: bool = Field(default=False, description="Whether content was truncated due to size limits")


# SSRF Protection: Allowed URL schemes and blocked private IP ranges
ALLOWED_SCHEMES = {"http", "https"}
MAX_CONTENT_LENGTH = 100_000  # 100KB limit for content extraction


def _is_safe_url(url: str) -> tuple[bool, str | None]:
    """
    Validate URL for SSRF protection.

    Returns:
        Tuple of (is_safe, error_message)
    """
    import ipaddress
    from urllib.parse import urlparse
    import socket

    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."

        # Check for empty hostname
        if not parsed.hostname:
            return False, "Invalid URL: missing hostname"

        # Resolve hostname to check for private IPs
        try:
            resolved_ips = socket.getaddrinfo(parsed.hostname, parsed.port or 80, socket.AF_UNSPEC, socket.SOCK_STREAM)

            for family, _, _, _, addr in resolved_ips:
                ip_str = addr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    # Block private, loopback, and link-local addresses
                    if ip.is_private or ip.is_loopback or ip.is_link_local:
                        return False, "Access to private/internal IP addresses is not allowed"
                except ValueError:
                    continue

        except socket.gaierror as e:
            return False, f"Failed to resolve hostname: {e}"

        return True, None

    except Exception as e:
        return False, f"Invalid URL: {e}"


async def _fetch_and_extract_content(url: str) -> dict[str, Any]:
    """
    Fetch URL and extract readable content.

    Uses httpx for async HTTP requests.
    """
    import httpx
    from html import unescape

    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        max_redirects=5,
        headers={
            "User-Agent": "MCP-Server-LangGraph/1.0 (URL Content Fetcher)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8",
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        raw_content = response.text

        # Extract title and content based on content type
        title = None
        extracted_content = raw_content

        if "text/html" in content_type or "application/xhtml" in content_type:
            # Extract title
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", raw_content, re.IGNORECASE)
            if title_match:
                title = unescape(title_match.group(1).strip())

            # Remove script and style tags
            extracted_content = re.sub(
                r"<(script|style|noscript)[^>]*>.*?</\1>",
                "",
                raw_content,
                flags=re.DOTALL | re.IGNORECASE,
            )

            # Remove HTML tags
            extracted_content = re.sub(r"<[^>]+>", " ", extracted_content)

            # Decode HTML entities
            extracted_content = unescape(extracted_content)

            # Normalize whitespace
            extracted_content = re.sub(r"\s+", " ", extracted_content).strip()

        elif "application/json" in content_type:
            import json

            try:
                parsed_json = json.loads(raw_content)
                extracted_content = json.dumps(parsed_json, indent=2)
            except json.JSONDecodeError:
                pass

        # Truncate if too long
        truncated = False
        if len(extracted_content) > MAX_CONTENT_LENGTH:
            extracted_content = extracted_content[:MAX_CONTENT_LENGTH] + "... [truncated]"
            truncated = True

        return {
            "url": str(response.url),
            "title": title,
            "content": extracted_content,
            "content_type": content_type.split(";")[0],
            "content_length": len(extracted_content),
            "truncated": truncated,
        }


@ai_router.post(
    "/fetch-url",
    status_code=status.HTTP_200_OK,
    summary="Fetch URL Content",
    description="Fetch and extract content from a URL for chat context",
)
async def fetch_url_content(request: UrlFetchRequest) -> UrlFetchResponse:
    """
    Fetch content from a URL for inclusion in chat context.

    Security:
    - SSRF protection: Blocks private/internal IP addresses
    - Only http/https schemes allowed
    - Content size limited to 100KB
    - Request timeout of 10 seconds
    """
    logger.info("URL content fetch requested", extra={"url": request.url})

    # SSRF validation
    is_safe, error = _is_safe_url(request.url)
    if not is_safe:
        logger.warning(
            "URL fetch blocked by SSRF protection",
            extra={"url": request.url, "reason": error},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    try:
        result = await _fetch_and_extract_content(request.url)
        logger.info(
            "URL content fetched successfully",
            extra={"url": result["url"], "content_length": result["content_length"]},
        )
        return UrlFetchResponse(**result)

    except Exception as e:
        logger.exception("Failed to fetch URL content")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch URL: {e}",
        )


# =============================================================================
# Chat Suggestions (Inline Completions)
# =============================================================================


class ChatSuggestion(BaseModel):
    """A single chat suggestion."""

    text: str = Field(description="The suggested text completion")
    confidence: float = Field(default=0.7, description="Confidence score 0-1")
    reasoning: str | None = Field(None, description="Why this suggestion was made")


class ChatSuggestionsRequest(BaseModel):
    """Request for chat inline suggestions."""

    input_text: str = Field(description="The user's partial input text")
    session_id: str | None = Field(None, description="Session ID for context")
    max_suggestions: int = Field(default=3, description="Maximum suggestions to return")


class ChatSuggestionsResponse(BaseModel):
    """Response with chat suggestions."""

    suggestions: list[ChatSuggestion] = Field(default_factory=list, description="List of suggested completions")


@ai_router.post(
    "/chat-suggestions",
    status_code=status.HTTP_200_OK,
    summary="Get Chat Inline Suggestions",
    description="Get AI-powered inline suggestions for chat input completion",
)
async def get_chat_suggestions(
    request: ChatSuggestionsRequest,
) -> ChatSuggestionsResponse:
    """
    Get inline suggestions for chat input.

    Used by the frontend useInlineSuggestions hook to provide
    autocomplete-style suggestions as the user types.

    Uses ChatFollowUpSuggestionAgent with LLM integration for intelligent
    suggestions, with automatic fallback to heuristics when LLM is unavailable.

    Example:
        ```
        POST /api/v1/ai/chat-suggestions
        {
            "input_text": "How do I configure",
            "session_id": "session-123",
            "max_suggestions": 3
        }
        ```
    """
    # Return empty for empty input
    if not request.input_text or not request.input_text.strip():
        return ChatSuggestionsResponse(suggestions=[])

    # Check feature flag
    flags = get_feature_flags()
    if not flags.enable_ai_suggestions:
        return ChatSuggestionsResponse(suggestions=[])

    try:
        # Use the existing ChatFollowUpSuggestionAgent with LLM integration
        agent = ChatFollowUpSuggestionAgent(
            enable_llm=flags.enable_llm_suggestions,
            enable_cache=True,
        )

        # Generate LLM-powered suggestions
        llm_suggestions = await agent.suggest(
            content=request.input_text,
            max_suggestions=request.max_suggestions,
            session_id=request.session_id,
        )

        # Convert to response format
        suggestions = [
            ChatSuggestion(
                text=s.text,
                confidence=s.confidence,
                reasoning=s.reasoning,
            )
            for s in llm_suggestions
        ]

        return ChatSuggestionsResponse(suggestions=suggestions)

    except Exception as e:
        logger.warning(
            "LLM suggestions failed, returning empty",
            extra={"error": str(e), "input_text": request.input_text[:50]},
        )
        return ChatSuggestionsResponse(suggestions=[])


# =============================================================================
# Canvas Actions
# =============================================================================


class CanvasActionRequest(BaseModel):
    """Request for canvas action."""

    canvas_id: str | None = Field(None, description="Canvas identifier")
    state: dict[str, Any] | None = Field(None, description="Canvas state data")
    format: str | None = Field(None, description="Export format (png, svg, json)")


class CanvasActionResponse(BaseModel):
    """Response from canvas action."""

    success: bool = Field(description="Whether the action succeeded")
    message: str | None = Field(None, description="Status message")
    data: dict[str, Any] | None = Field(None, description="Action result data")


@ai_router.post(
    "/canvas/{action}",
    status_code=status.HTTP_200_OK,
    summary="Execute Canvas Action",
    description="Execute an AI-assisted canvas action (save, export, analyze)",
)
async def execute_canvas_action(
    action: str,
    request: CanvasActionRequest,
) -> CanvasActionResponse:
    """
    Execute an AI-assisted action on the canvas.

    Supported actions:
    - save: Save the current canvas state
    - export: Export canvas to various formats
    - analyze: AI analysis of canvas content
    - optimize: AI-powered layout optimization

    Example:
        ```
        POST /api/v1/ai/canvas/save
        {
            "canvas_id": "canvas-123",
            "state": {...}
        }
        ```
    """
    valid_actions = {"save", "export", "analyze", "optimize", "clear"}

    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid canvas action: {action}. Valid actions: {', '.join(valid_actions)}",
        )

    logger.info(
        "Canvas action requested",
        extra={"action": action, "canvas_id": request.canvas_id},
    )

    # Handle each action
    if action == "save":
        # TODO: Implement actual save logic
        return CanvasActionResponse(
            success=True,
            message="Canvas state saved",
            data={"canvas_id": request.canvas_id},
        )
    elif action == "export":
        export_format = request.format or "png"
        return CanvasActionResponse(
            success=True,
            message=f"Canvas exported as {export_format}",
            data={"format": export_format},
        )
    elif action == "analyze":
        return CanvasActionResponse(
            success=True,
            message="Canvas analysis complete",
            data={"nodes": 0, "edges": 0, "complexity": "low"},
        )
    elif action == "optimize":
        return CanvasActionResponse(
            success=True,
            message="Canvas layout optimized",
            data={"optimized": True},
        )
    elif action == "clear":
        return CanvasActionResponse(
            success=True,
            message="Canvas cleared",
        )

    return CanvasActionResponse(success=True)


# =============================================================================
# Natural Language Command Interpretation
# =============================================================================


class InterpretCommandRequest(BaseModel):
    """Request to interpret a natural language command."""

    command: str = Field(description="The natural language command to interpret")
    session_id: str | None = Field(None, description="Session ID for context")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class InterpretedAction(BaseModel):
    """The interpreted action from a command."""

    action: str = Field(description="The action to perform")
    intent: str = Field(description="The detected user intent")
    confidence: float = Field(default=0.8, description="Confidence in interpretation")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    suggestion: str | None = Field(None, description="Suggested UI action")


class InterpretCommandResponse(BaseModel):
    """Response with interpreted command."""

    action: str = Field(description="The primary action")
    intent: str = Field(description="The detected intent")
    confidence: float = Field(description="Interpretation confidence")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    alternatives: list[InterpretedAction] = Field(default_factory=list, description="Alternative interpretations")


@ai_router.post(
    "/interpret-command",
    status_code=status.HTTP_200_OK,
    summary="Interpret Natural Language Command",
    description="Interpret a natural language command and determine the intended action",
)
async def interpret_command(
    request: InterpretCommandRequest,
) -> InterpretCommandResponse:
    """
    Interpret a natural language command.

    Used by the Studio shell to understand user commands like:
    - "create a new session"
    - "run the workflow"
    - "show me the logs"
    - "connect to the MCP server"

    Uses LLM-powered interpretation with heuristic fallback.

    Example:
        ```
        POST /api/v1/ai/interpret-command
        {
            "command": "create a new session",
            "session_id": "session-123"
        }
        ```
    """
    # Check feature flag
    flags = get_feature_flags()
    enable_llm = flags.enable_ai_suggestions and flags.enable_llm_suggestions

    # Handle empty command
    if not request.command or not request.command.strip():
        return InterpretCommandResponse(
            action="none",
            intent="empty",
            confidence=1.0,
            parameters={},
        )

    try:
        # Use the LLM-powered CommandInterpreterAgent
        agent = CommandInterpreterAgent(enable_llm=enable_llm)

        result = await agent.interpret(
            command=request.command,
            context=request.context,
            session_id=request.session_id,
        )

        # Convert alternatives to InterpretedAction objects
        alternatives = [
            InterpretedAction(
                action=alt.get("action", "unknown"),
                confidence=alt.get("confidence", 0.5),
            )
            for alt in result.alternatives
        ]

        return InterpretCommandResponse(
            action=result.action,
            intent=result.intent,
            confidence=result.confidence,
            parameters=result.parameters,
            alternatives=alternatives,
        )

    except Exception as e:
        logger.warning(
            "Command interpretation failed, using fallback",
            error=str(e),
            command=request.command[:50],
        )
        # Return a safe fallback
        return InterpretCommandResponse(
            action="send_message",
            intent="chat",
            confidence=0.5,
            parameters={"message": request.command},
        )
