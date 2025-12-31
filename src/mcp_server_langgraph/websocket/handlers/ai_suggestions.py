"""
AI Suggestions WebSocket Handler.

Provides real-time AI suggestion streaming for the Studio frontend.

Features:
    - Real-time typing suggestions powered by LLM
    - Session context awareness
    - Rate limiting to prevent abuse
    - Authentication required
    - Feature flag controlled

Message Types (Client -> Server):
    - suggestion_request: Request an AI suggestion
    - suggestion_accept: User accepted the suggestion
    - suggestion_reject: User rejected the suggestion
    - context_update: Update session context

Message Types (Server -> Client):
    - suggestion_response: AI suggestion response
    - error: Error response

Example Message (suggestion_request):
    {
        "type": "suggestion_request",
        "payload": {
            "session_id": "uuid",
            "input_text": "Hello, I need help with",
            "cursor_position": 25,
            "context_window": 500
        }
    }

Example Response (suggestion_response):
    {
        "type": "suggestion_response",
        "payload": {
            "suggestion_id": "uuid",
            "text": "I'd be happy to help! What would you like assistance with?",
            "confidence": 0.85,
            "reasoning": "Based on user's greeting pattern"
        }
    }
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import (
    AISuggestionError,
    AISuggestionMessageType,
    AISuggestionRequest,
    AISuggestionResponse,
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


class AISuggestionsHandler(WebSocketBase):
    """
    WebSocket handler for real-time AI suggestion streaming.

    Extends WebSocketBase to provide AI-powered suggestion generation
    with the standardized infrastructure (auth, rate limiting, metrics, etc.).

    The handler receives user input and context, generates AI suggestions,
    and streams them back to the client in real-time.

    Usage:
        handler = AISuggestionsHandler(
            config=WebSocketConfig(
                endpoint_name="ai-suggestions",
                require_auth=True,
                authz_resource_type="ai",
                authz_resource_id="suggestions",
                authz_required_relation="user",
                rate_limit_per_minute=300,
                message_timeout=30,
            ),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the AI suggestions handler.

        Args:
            config: WebSocket configuration.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._user_id: str | None = None
        self._session_context: dict[str, str] = {}

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        self._user_id = user.id
        logger.info(
            f"AI suggestions stream connected: user={self._user_id}",
            extra={"user_id": self._user_id},
        )

    async def on_disconnect(self) -> None:
        """Handle connection teardown."""
        # Fall back to base class user if on_connect was never called
        # This handles the race condition where client disconnects during auth
        user_id = self._user_id or (self._user.id if self._user else None)
        logger.info(
            f"AI suggestions stream disconnected: user={user_id}",
            extra={"user_id": user_id},
        )
        self._session_context.clear()

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming AI suggestion messages.

        Dispatches messages to appropriate handlers based on type.

        Args:
            message: The incoming message envelope.

        Returns:
            Response message envelope, or None if no response needed.
        """
        message_type = message.type

        try:
            if message_type == AISuggestionMessageType.SUGGESTION_REQUEST:
                return await self._handle_suggestion_request(message)
            elif message_type == AISuggestionMessageType.SUGGESTION_ACCEPT:
                return await self._handle_suggestion_accept(message)
            elif message_type == AISuggestionMessageType.SUGGESTION_REJECT:
                return await self._handle_suggestion_reject(message)
            elif message_type == AISuggestionMessageType.CONTEXT_UPDATE:
                return await self._handle_context_update(message)
            else:
                logger.debug(
                    f"Unhandled message type: {message_type}",
                    extra={"message_type": message_type, "user_id": self._user_id},
                )
                return None
        except Exception as e:
            logger.exception(
                f"Error handling AI suggestion message: {e}",
                extra={"message_type": message_type, "user_id": self._user_id},
            )
            return self._create_error_response(
                code="internal_error",
                message="An internal error occurred while processing your request",
                retryable=True,
            )

    async def _handle_suggestion_request(self, message: MessageEnvelope) -> MessageEnvelope:
        """
        Handle a suggestion request from the client.

        Args:
            message: The incoming suggestion request.

        Returns:
            Suggestion response or error.
        """
        payload = message.payload or {}
        try:
            request = AISuggestionRequest.from_dict(payload)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                f"Invalid suggestion request: {e}",
                extra={"user_id": self._user_id},
            )
            return self._create_error_response(
                code="invalid_request",
                message="Invalid suggestion request format",
                retryable=False,
            )

        # Validate session ownership (placeholder - would check against session store)
        if not request.session_id:
            return self._create_error_response(
                code="missing_session",
                message="Session ID is required",
                retryable=False,
            )

        # Generate suggestion (placeholder - would call LLM service)
        suggestion = await self._generate_suggestion(request)

        return MessageEnvelope(
            type=AISuggestionMessageType.SUGGESTION_RESPONSE,
            payload=suggestion.to_dict(),
            id=message.id,
        )

    async def _handle_suggestion_accept(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle suggestion acceptance - used for learning/analytics.

        Args:
            message: The suggestion accept message.

        Returns:
            None - no response needed.
        """
        payload = message.payload or {}
        suggestion_id = payload.get("suggestion_id")
        logger.info(
            f"Suggestion accepted: {suggestion_id}",
            extra={
                "suggestion_id": suggestion_id,
                "user_id": self._user_id,
            },
        )
        # Record metrics for suggestion acceptance
        if self._metrics:
            self._metrics.record_message_sent("suggestion_accepted")
        return None

    async def _handle_suggestion_reject(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle suggestion rejection - used for learning/analytics.

        Args:
            message: The suggestion reject message.

        Returns:
            None - no response needed.
        """
        payload = message.payload or {}
        suggestion_id = payload.get("suggestion_id")
        reason = payload.get("reason")
        logger.info(
            f"Suggestion rejected: {suggestion_id}",
            extra={
                "suggestion_id": suggestion_id,
                "reason": reason,
                "user_id": self._user_id,
            },
        )
        # Record metrics for suggestion rejection
        if self._metrics:
            self._metrics.record_message_sent("suggestion_rejected")
        return None

    async def _handle_context_update(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle context updates from the client.

        Args:
            message: The context update message.

        Returns:
            None - no response needed.
        """
        payload = message.payload or {}
        session_id = payload.get("session_id")
        context = payload.get("context", "")

        if session_id:
            self._session_context[session_id] = context
            logger.debug(
                f"Context updated for session: {session_id}",
                extra={
                    "session_id": session_id,
                    "context_length": len(context),
                    "user_id": self._user_id,
                },
            )
        return None

    async def _generate_suggestion(self, request: AISuggestionRequest) -> AISuggestionResponse:
        """
        Generate an AI suggestion based on the request using LLM.

        Uses the Multi-Agent Orchestrator's LLM infrastructure to generate
        real-time text completions based on user input and session context.

        Args:
            request: The suggestion request.

        Returns:
            Generated suggestion response.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.llm.factory import create_llm_from_config

        suggestion_id = str(uuid.uuid4())

        # Get cached context if available
        context = self._session_context.get(request.session_id, "")

        logger.debug(
            f"Generating AI suggestion: {suggestion_id}",
            extra={
                "suggestion_id": suggestion_id,
                "session_id": request.session_id,
                "input_length": len(request.input_text),
                "context_length": len(context),
                "user_id": self._user_id,
            },
        )

        try:
            # Get LLM factory from config
            llm = create_llm_from_config(settings)

            # Build prompt for suggestion generation
            system_prompt = """You are an AI assistant helping with text completion.
Given the user's partial input and conversation context, suggest a natural continuation.
Keep suggestions concise (1-2 sentences max) and contextually appropriate.
Return ONLY the suggested completion text, nothing else."""

            # Include context if available
            user_prompt = f"Context: {context[: request.context_window]}\n\n" if context else ""
            user_prompt += f"Complete this text: {request.input_text}"

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            # Call LLM for suggestion
            response = await llm.ainvoke(messages, max_tokens=150, temperature=0.7)
            suggestion_text = response.content.strip()

            # Estimate confidence based on response length and context availability
            confidence = 0.85 if context else 0.75

            logger.info(
                f"Generated AI suggestion successfully: {suggestion_id}",
                extra={
                    "suggestion_id": suggestion_id,
                    "suggestion_length": len(suggestion_text),
                    "confidence": confidence,
                    "user_id": self._user_id,
                },
            )

            return AISuggestionResponse(
                suggestion_id=suggestion_id,
                text=suggestion_text,
                confidence=confidence,
                reasoning="Generated from session context" if context else "Generated from input",
            )

        except Exception as e:
            logger.warning(
                f"LLM suggestion generation failed: {e}",
                extra={
                    "suggestion_id": suggestion_id,
                    "error": str(e),
                    "user_id": self._user_id,
                },
            )
            # Return a fallback response
            return AISuggestionResponse(
                suggestion_id=suggestion_id,
                text="",
                confidence=0.0,
                reasoning=f"Suggestion generation unavailable: {str(e)[:100]}",
            )

    def _create_error_response(self, code: str, message: str, retryable: bool = False) -> MessageEnvelope:
        """
        Create an error response envelope.

        Args:
            code: Error code.
            message: Human-readable error message.
            retryable: Whether the client should retry.

        Returns:
            Error message envelope.
        """
        error = AISuggestionError(code=code, message=message, retryable=retryable)
        return MessageEnvelope(
            type=AISuggestionMessageType.ERROR,
            payload=error.to_dict(),
        )
