"""
Agents MCP Tool Handler

Handles agents/orchestrate, agents/decompose, agents/status operations.

Provides MCP interface to the multi-agent orchestration system.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from mcp.types import TextContent

from mcp_server_langgraph.agents import ModelSelector, Orchestrator
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.hook_registry import HookRegistry
from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler
from mcp_server_langgraph.observability.telemetry import logger

# Tool name for hook matching
AGENTS_TOOL_NAME = "agents"


class AgentsToolHandler(AbstractToolHandler):
    """Handler for multi-agent orchestration MCP operations.

    Provides:
    - agents/decompose: Decompose task into subtasks
    - agents/orchestrate: Execute multi-agent orchestration
    - agents/status: Get orchestration status
    - agents/cancel: Cancel running orchestration
    - agents/select_model: Get model recommendation for complexity
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
        orchestrator: Orchestrator | None = None,
        model_selector: ModelSelector | None = None,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        """Initialize agents handler.

        Args:
            auth: Authentication middleware
            agent_graph: LangGraph agent instance
            orchestrator: Optional orchestrator (creates default if None)
            model_selector: Optional model selector (creates default if None)
            hook_registry: Optional hook registry for SDK hook integration
        """
        super().__init__(auth, agent_graph, hook_registry=hook_registry)
        self.orchestrator = orchestrator or Orchestrator()
        self.model_selector = model_selector or ModelSelector()
        self._orchestrations: dict[str, dict[str, Any]] = {}

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Route to appropriate handler based on operation.

        Includes hook dispatch for PreToolUse and PostToolUse.
        """
        operation = arguments.get("operation", "orchestrate")
        tool_name = f"{AGENTS_TOOL_NAME}/{operation}"

        # Create hook context
        request_id = str(span.get_span_context().trace_id) if span.get_span_context() else None
        hook_context = self.get_hook_context(
            session_id=arguments.get("orchestration_id", "default"),
            user_id=user_id,
            request_id=request_id,
        )

        # Dispatch PreToolUse hook
        pre_result = await self.dispatch_pre_handler_hook(
            tool_name=tool_name,
            tool_input=arguments,
            context=hook_context,
        )

        # Check for deny from pre-hook
        if not pre_result.should_proceed:
            deny_message = pre_result.message or "Agent operation blocked by policy"
            logger.warning(
                "Agent operation blocked by pre-hook",
                extra={"user_id": user_id, "operation": operation, "reason": deny_message},
            )
            return [TextContent(type="text", text=f"Request denied: {deny_message}")]

        try:
            if operation == "decompose":
                result = await self.handle_decompose_task(arguments, span, user_id)
            elif operation == "orchestrate":
                result = await self.handle_orchestrate(arguments, span, user_id)
            elif operation == "status":
                result = await self.handle_get_status(arguments, span, user_id)
            elif operation == "cancel":
                result = await self.handle_cancel(arguments, span, user_id)
            elif operation == "select_model":
                result = await self.handle_select_model(arguments, span, user_id)
            else:
                result = [TextContent(type="text", text=f"Unknown operation: {operation}")]

            # Dispatch PostToolUse hook (success case)
            result_text = result[0].text if result else ""
            await self.dispatch_post_handler_hook(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=result_text,
                is_error=False,
                context=hook_context,
            )

            return result

        except Exception as e:
            # Dispatch PostToolUse hook (error case)
            await self.dispatch_post_handler_hook(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=f"Error: {e!s}",
                is_error=True,
                context=hook_context,
            )
            raise

    async def handle_decompose_task(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Decompose a task into subtasks.

        Args:
            arguments: Must contain 'task', optional 'num_subtasks'
            span: Tracing span
            user_id: User ID

        Returns:
            Task decomposition
        """
        task = arguments.get("task", "")
        num_subtasks = arguments.get("num_subtasks", 3)

        decomposition = self.orchestrator.decompose_task(task, num_subtasks)

        return [TextContent(
            type="text",
            text=json.dumps({
                "original_task": decomposition.original_task,
                "subtasks": [
                    {
                        "task_id": st.task_id,
                        "title": st.title,
                        "instructions": st.instructions,
                        "complexity": st.complexity,
                    }
                    for st in decomposition.subtasks
                ],
                "synthesis_instructions": decomposition.synthesis_instructions,
            }, indent=2),
        )]

    async def handle_orchestrate(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Execute multi-agent orchestration.

        Args:
            arguments: Must contain 'task', optional 'strategy'
            span: Tracing span
            user_id: User ID

        Returns:
            Orchestration result or ID for async execution
        """
        # Check feature flag
        if not feature_flags.enable_multi_agent_orchestration:
            return [TextContent(
                type="text",
                text="Multi-agent orchestration is disabled. Enable with FF_ENABLE_MULTI_AGENT_ORCHESTRATION=true",
            )]

        task = arguments.get("task", "")
        strategy = arguments.get("strategy", "parallel")

        # Generate orchestration ID
        orchestration_id = f"orch-{uuid.uuid4().hex[:8]}"

        # Determine number of subagents based on task complexity
        num_agents = self.orchestrator.scale_effort(task)

        # Decompose task
        decomposition = self.orchestrator.decompose_task(task, num_agents)

        # Store orchestration state
        self._orchestrations[orchestration_id] = {
            "id": orchestration_id,
            "task": task,
            "strategy": strategy,
            "status": "running",
            "decomposition": decomposition,
            "user_id": user_id,
        }

        # Execute orchestration
        try:
            results = await self.orchestrator.execute(decomposition)

            # Synthesize results
            synthesis = await self.orchestrator.synthesize(decomposition, results)

            # Update status
            self._orchestrations[orchestration_id]["status"] = "completed"
            self._orchestrations[orchestration_id]["results"] = synthesis

            return [TextContent(
                type="text",
                text=json.dumps({
                    "orchestration_id": orchestration_id,
                    "status": "completed",
                    "subtask_count": len(results),
                    "successful_count": sum(1 for r in results if r.success),
                    "synthesis": synthesis,
                }, indent=2),
            )]

        except Exception as e:
            self._orchestrations[orchestration_id]["status"] = "failed"
            self._orchestrations[orchestration_id]["error"] = str(e)

            return [TextContent(
                type="text",
                text=json.dumps({
                    "orchestration_id": orchestration_id,
                    "status": "failed",
                    "error": str(e),
                }, indent=2),
            )]

    async def handle_get_status(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Get status of an orchestration.

        Args:
            arguments: Must contain 'orchestration_id'
            span: Tracing span
            user_id: User ID

        Returns:
            Orchestration status
        """
        orchestration_id = arguments.get("orchestration_id", "")

        if orchestration_id not in self._orchestrations:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Orchestration not found: {orchestration_id}",
                }, indent=2),
            )]

        orch = self._orchestrations[orchestration_id]
        return [TextContent(
            type="text",
            text=json.dumps({
                "orchestration_id": orch["id"],
                "status": orch["status"],
                "task": orch["task"],
            }, indent=2),
        )]

    async def handle_cancel(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Cancel a running orchestration.

        Args:
            arguments: Must contain 'orchestration_id'
            span: Tracing span
            user_id: User ID

        Returns:
            Cancellation result
        """
        orchestration_id = arguments.get("orchestration_id", "")

        if orchestration_id not in self._orchestrations:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Orchestration not found: {orchestration_id}",
                }, indent=2),
            )]

        orch = self._orchestrations[orchestration_id]
        if orch["status"] == "running":
            # Cancel running subagents
            self.orchestrator.coordinator.cancel_all()
            orch["status"] = "cancelled"

        return [TextContent(
            type="text",
            text=json.dumps({
                "orchestration_id": orchestration_id,
                "status": orch["status"],
                "message": "Orchestration cancelled",
            }, indent=2),
        )]

    async def handle_select_model(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Get model recommendation for task complexity.

        Args:
            arguments: Must contain 'complexity' or 'task_complexity_score'
            span: Tracing span
            user_id: User ID

        Returns:
            Model recommendation
        """
        complexity = arguments.get("complexity")
        score = arguments.get("task_complexity_score")

        if score is not None:
            model = self.model_selector.get_model_for_task(score)
        elif complexity:
            model = self.model_selector.select_model(complexity)
        else:
            model = self.model_selector.select_model("complicated")

        verifier = self.model_selector.select_verifier("auto")

        return [TextContent(
            type="text",
            text=json.dumps({
                "model": model,
                "verifier": verifier,
                "primary_vendor": self.model_selector.primary_vendor,
                "available_vendors": self.model_selector.available_vendors,
            }, indent=2),
        )]
