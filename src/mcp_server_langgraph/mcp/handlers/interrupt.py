"""
Interrupt Handler for MCP Server.

Implements Claude Agent SDK interrupt pattern for graceful cancellation.
Provides session_interrupt tool for controlling long-running operations.
"""

from typing import Any

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.interrupt import get_interrupt_controller
from mcp_server_langgraph.mcp.models import InterruptInput
from mcp_server_langgraph.observability.telemetry import logger, tracer

# Tool name for interrupt operations
INTERRUPT_TOOL_NAME = "session_interrupt"


class InterruptHandler:
    """
    Handler for session_interrupt tool operations.

    Implements Claude Agent SDK interrupt pattern:
    - signal: Interrupt a running session
    - check: Check if session is interrupted
    - clear: Clear interrupt flag for a session
    """

    def __init__(self, auth: AuthMiddleware) -> None:
        """
        Initialize interrupt handler with auth middleware.

        Args:
            auth: Authentication/authorization middleware
        """
        self.auth = auth
        self.tracer = tracer

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle session_interrupt tool invocation.

        Args:
            arguments: Tool arguments including session_id and action
            span: OpenTelemetry span for tracing
            user_id: Authenticated user ID

        Returns:
            List of TextContent responses

        Raises:
            ValueError: If input validation fails
        """
        with tracer.start_as_current_span("interrupt.handle"):
            # Validate input with Pydantic schema
            try:
                interrupt_input = InterruptInput.model_validate(arguments)
            except Exception as e:
                logger.error(f"Invalid interrupt input: {e}", extra={"arguments": arguments})
                msg = f"Invalid interrupt input: {e}"
                raise ValueError(msg) from e

            session_id = interrupt_input.session_id
            action = interrupt_input.action

            span.set_attribute("session.id", session_id)
            span.set_attribute("interrupt.action", action)
            span.set_attribute("user.id", user_id)

            logger.info(
                "Processing interrupt request",
                extra={
                    "session_id": session_id,
                    "action": action,
                    "user_id": user_id,
                },
            )

            # Get the singleton interrupt controller
            controller = get_interrupt_controller()

            if action == "signal":
                await controller.signal_interrupt(session_id)
                logger.info(f"Session {session_id} interrupted by user {user_id}")
                return [
                    TextContent(
                        type="text",
                        text=f"Session '{session_id}' has been interrupted. Running operations will stop at the next checkpoint.",
                    )
                ]

            elif action == "check":
                is_interrupted = await controller.check_interrupted(session_id)
                status = "true" if is_interrupted else "false"
                return [
                    TextContent(
                        type="text",
                        text=f"Session '{session_id}' interrupted: {status}",
                    )
                ]

            elif action == "clear":
                await controller.clear_interrupt(session_id)
                logger.info(f"Interrupt cleared for session {session_id}")
                return [
                    TextContent(
                        type="text",
                        text=f"Interrupt cleared for session '{session_id}'. The session can now proceed normally.",
                    )
                ]

            else:
                # This should never happen due to Pydantic validation
                msg = f"Invalid action: {action}. Must be 'signal', 'check', or 'clear'."
                raise ValueError(msg)
