"""
Chat Tool Handler

Handles agent_chat tool invocations for the MCP server.
Implements Anthropic best practices for token-efficient responses.
"""

from typing import Any

from langchain_core.messages import HumanMessage
from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.agent import AgentState
from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler
from mcp_server_langgraph.mcp.models import ChatInput
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import format_response


class ChatToolHandler(AbstractToolHandler):
    """
    Handler for agent_chat tool operations.

    Implements Anthropic best practices:
    - Response format control (concise vs detailed)
    - Token-efficient responses with truncation
    - Clear error messages
    - Performance tracking
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
    ) -> None:
        """Initialize chat handler with dependencies."""
        super().__init__(auth, agent_graph)

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle agent_chat tool invocation.

        Args:
            arguments: Tool arguments including message, token, user_id, thread_id
            span: OpenTelemetry span for tracing
            user_id: Authenticated user ID

        Returns:
            List of TextContent responses
        """
        with tracer.start_as_current_span("agent.chat"):
            # Validate input with Pydantic schema
            try:
                chat_input = ChatInput.model_validate(arguments)
            except Exception as e:
                logger.error(f"Invalid chat input: {e}", extra={"arguments": arguments})
                msg = f"Invalid chat input: {e}"
                raise ValueError(msg) from e

            message = chat_input.message
            thread_id = chat_input.thread_id or "default"
            response_format_type = chat_input.response_format

            span.set_attribute("message.length", len(message))
            span.set_attribute("thread.id", thread_id)
            span.set_attribute("user.id", user_id)
            span.set_attribute("response.format", response_format_type)

            # Check if conversation exists
            conversation_exists = await self._check_conversation_exists(thread_id)

            # Authorize access for existing conversations
            if conversation_exists:
                await self._authorize_conversation_access(user_id, thread_id)
            else:
                logger.info(
                    "Creating new conversation, user granted implicit ownership",
                    extra={"user_id": user_id, "thread_id": thread_id},
                )

            logger.info(
                "Processing chat message",
                extra={
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "message_preview": message[:100],
                    "response_format": response_format_type,
                },
            )

            # Create initial state
            initial_state = self._create_initial_state(message, user_id, span)

            # Run the agent graph
            config = {"configurable": {"thread_id": thread_id}}

            try:
                result = await self.agent_graph.ainvoke(initial_state, config)
                return await self._process_result(result, message, thread_id, user_id, response_format_type, span)
            except Exception as e:
                logger.error(
                    f"Error processing chat: {e}",
                    extra={"error": str(e), "thread_id": thread_id},
                    exc_info=True,
                )
                metrics.failed_calls.add(1, {"tool": "agent_chat", "error": type(e).__name__})
                span.record_exception(e)
                raise

    async def _check_conversation_exists(self, thread_id: str) -> bool:
        """Check if a conversation exists in the checkpointer."""
        graph = self.agent_graph
        if hasattr(graph, "checkpointer") and graph.checkpointer is not None:
            try:
                config = {"configurable": {"thread_id": thread_id}}
                state_snapshot = await graph.aget_state(config)
                return state_snapshot is not None and state_snapshot.values is not None
            except Exception:
                return False
        return False

    async def _authorize_conversation_access(self, user_id: str, thread_id: str) -> None:
        """Authorize user access to an existing conversation."""
        conversation_resource = f"conversation:{thread_id}"
        can_edit = await self.auth.authorize(user_id=user_id, relation="editor", resource=conversation_resource)
        if not can_edit:
            logger.warning(
                "User cannot edit conversation",
                extra={"user_id": user_id, "thread_id": thread_id},
            )
            msg = (
                f"Not authorized to edit conversation '{thread_id}'. "
                f"Request access from conversation owner or use a different thread_id."
            )
            raise PermissionError(msg)

    def _create_initial_state(self, message: str, user_id: str, span: Any) -> AgentState:
        """Create initial agent state for the conversation."""
        return {
            "messages": [HumanMessage(content=message)],
            "next_action": "",
            "user_id": user_id,
            "request_id": str(span.get_span_context().trace_id) if span.get_span_context() else None,
            "routing_confidence": None,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": None,
            "user_request": message,
        }

    async def _process_result(
        self,
        result: dict[str, Any],
        message: str,
        thread_id: str,
        user_id: str,
        response_format_type: str,
        span: Any,
    ) -> list[TextContent]:
        """Process agent result and return formatted response."""
        response_message = result["messages"][-1]
        response_text = response_message.content

        # Apply response formatting
        formatted_response = format_response(response_text, format_type=response_format_type)

        span.set_attribute("response.length.original", len(response_text))
        span.set_attribute("response.length.formatted", len(formatted_response))
        metrics.successful_calls.add(1, {"tool": "agent_chat", "format": response_format_type})

        logger.info(
            "Chat response generated",
            extra={
                "thread_id": thread_id,
                "original_length": len(response_text),
                "formatted_length": len(formatted_response),
                "format": response_format_type,
            },
        )

        # Record conversation metadata
        await self._record_conversation_metadata(thread_id, user_id, message, result)

        return [TextContent(type="text", text=formatted_response)]

    async def _record_conversation_metadata(
        self,
        thread_id: str,
        user_id: str,
        message: str,
        result: dict[str, Any],
    ) -> None:
        """Record conversation metadata for search functionality."""
        try:
            from mcp_server_langgraph.core.storage.conversation_store import get_conversation_store

            store = get_conversation_store()
            message_count = len(result.get("messages", []))
            title = message[:50] + "..." if len(message) > 50 else message

            await store.record_conversation(
                thread_id=thread_id,
                user_id=user_id,
                message_count=message_count,
                title=title,
            )
            logger.debug(f"Recorded conversation metadata for {thread_id}")
        except Exception as e:
            logger.debug(f"Failed to record conversation metadata: {e}")
