"""
LangGraph Agent Client

SDK-agnostic wrapper for agent orchestration that can adapt
to future Claude Agent SDK.

Supports complete hook lifecycle:
- UserPromptSubmit: Before query processing
- PreToolUse: Before tool execution
- PostToolUse: After tool execution
- Stop: After query/task completion

Usage:
    from mcp_server_langgraph.sdk.client import LangGraphAgentClient

    client = LangGraphAgentClient(model_tier="complex")
    response = await client.query("What is 2 + 2?")
    result = await client.run_orchestrated_task("Research quantum computing")

With LLM Factory (for real LLM calls):
    from mcp_server_langgraph.llm.factory import LLMFactory

    llm = LLMFactory(provider="anthropic", model_name="claude-sonnet-4-5")
    client = LangGraphAgentClient(llm_factory=llm)
    response = await client.query("What is 2 + 2?")  # Uses real LLM
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import HumanMessage

from mcp_server_langgraph.agents import ModelSelector, Orchestrator
from mcp_server_langgraph.sdk.hooks import DEFAULT_SECURITY_HOOKS, SecurityHookRegistry
from mcp_server_langgraph.sdk.state import AgentStateManager
from mcp_server_langgraph.sdk.tools import InProcessToolServer, create_default_server

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.factory import LLMFactory


class LangGraphAgentClient:
    """SDK-agnostic agent client.

    Provides a unified interface for agent operations that can adapt
    to future Claude Agent SDK while working with current infrastructure.

    Supports optional LLM factory injection for real LLM calls.
    """

    def __init__(
        self,
        model_tier: str = "complicated",
        model_selector: ModelSelector | None = None,
        orchestrator: Orchestrator | None = None,
        tool_server: InProcessToolServer | None = None,
        hook_registry: SecurityHookRegistry | None = None,
        state_manager: AgentStateManager | None = None,
        llm_factory: LLMFactory | None = None,
    ) -> None:
        """Initialize agent client.

        Args:
            model_tier: Default model tier (simple, complicated, complex)
            model_selector: Optional model selector
            orchestrator: Optional orchestrator
            tool_server: Optional in-process tool server
            hook_registry: Optional security hook registry
            state_manager: Optional state manager
            llm_factory: Optional LLM factory for real LLM calls
        """
        self.model_tier = model_tier
        self.model_selector = model_selector or ModelSelector()
        self.orchestrator = orchestrator or Orchestrator(model_selector=self.model_selector)
        self.tool_server = tool_server or create_default_server()
        self.hook_registry = hook_registry or DEFAULT_SECURITY_HOOKS
        self.state_manager = state_manager or AgentStateManager()
        self.llm_factory = llm_factory

    async def query(
        self,
        prompt: str,
        session_id: str | None = None,
    ) -> str:
        """Send a query to the agent.

        Args:
            prompt: Query prompt
            session_id: Optional session ID for context

        Returns:
            Agent response

        Raises:
            PermissionError: If UserPromptSubmit hook denies the prompt

        Note:
            Uses LLM factory when provided, otherwise returns placeholder.
        """
        query_id = f"query-{uuid.uuid4().hex[:8]}"
        context: dict[str, Any] = {}
        is_error = False
        response = ""

        try:
            # Execute UserPromptSubmit hooks before processing
            prompt = await self._execute_user_prompt_submit_hook(prompt, query_id, context)

            # Get model for this query
            model = self.model_selector.select_model(self.model_tier)

            # Load session context if provided
            if session_id:
                state = await self.state_manager.resume_session(session_id)
                if state:
                    context["session_state"] = state

            # Execute query (internal implementation)
            response = await self._execute_query_internal(prompt, model)

            # Save session state if tracking
            if session_id:
                await self.state_manager.save_state(
                    session_id,
                    {
                        "last_query": prompt,
                        "last_response": response,
                    },
                )

        except PermissionError:
            # Re-raise permission errors (from hook denials)
            raise
        except Exception:
            is_error = True
            raise
        finally:
            # Execute Stop hooks after query completion
            await self._execute_stop_hook(
                reason="error" if is_error else "completed",
                is_error=is_error,
                result=response if not is_error else None,
                query_id=query_id,
                context=context,
            )

        return response

    async def _execute_query_internal(self, prompt: str, model: str) -> str:
        """Execute the query with the LLM.

        Args:
            prompt: The prompt to process
            model: The model to use

        Returns:
            The response from the LLM
        """
        # Use LLM factory if provided, otherwise placeholder
        if self.llm_factory:
            messages = [HumanMessage(content=prompt)]
            ai_response = await self.llm_factory.ainvoke(messages)  # type: ignore[arg-type]
            return str(ai_response.content)
        else:
            # Placeholder response (no LLM factory provided)
            return f"[{model}] Processed: {prompt[:50]}..."

    async def _execute_user_prompt_submit_hook(
        self,
        prompt: str,
        query_id: str,
        context: dict[str, Any],
    ) -> str:
        """Execute UserPromptSubmit hooks before query processing.

        Args:
            prompt: The user's prompt
            query_id: Unique identifier for this query
            context: Execution context

        Returns:
            The (potentially modified) prompt

        Raises:
            PermissionError: If hook denies the prompt
        """
        input_data = {"prompt": prompt}

        hook_result = await self.hook_registry.execute_hooks(
            "UserPromptSubmit",
            "*",  # UserPromptSubmit applies to all prompts
            input_data,
            query_id,
            context,
        )

        if not hook_result.allowed:
            raise PermissionError(f"Prompt denied: {hook_result.reason}")

        # Use modified prompt if hooks transformed it
        if hook_result.modified_input:
            return cast(str, hook_result.modified_input.get("prompt", prompt))

        return prompt

    async def _execute_stop_hook(
        self,
        reason: str,
        is_error: bool,
        result: Any,
        query_id: str,
        context: dict[str, Any],
    ) -> None:
        """Execute Stop hooks after query/task completion.

        Args:
            reason: Reason for stopping (completed, error, interrupted)
            is_error: Whether the operation failed
            result: The result of the operation
            query_id: Unique identifier for this operation
            context: Execution context
        """
        input_data = {
            "reason": reason,
            "is_error": is_error,
            "result": result,
        }

        await self.hook_registry.execute_hooks(
            "Stop",
            "*",  # Stop applies globally
            input_data,
            query_id,
            context,
        )

    async def run_orchestrated_task(
        self,
        task: str,
        subagent_count: int = 3,
        strategy: str = "parallel",
    ) -> dict[str, Any]:
        """Run orchestrator-worker pattern with parallel subagents.

        Args:
            task: Task description
            subagent_count: Number of subagents to spawn
            strategy: Execution strategy (parallel, sequential)

        Returns:
            Orchestration result
        """
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        context: dict[str, Any] = {}
        is_error = False
        result: dict[str, Any] = {}

        try:
            # Decompose task
            decomposition = self.orchestrator.decompose_task(task, subagent_count)

            # Execute with orchestrator
            results = await self.orchestrator.execute(decomposition)

            # Synthesize results
            synthesis = await self.orchestrator.synthesize(decomposition, results)

            result = {
                "task": task,
                "strategy": strategy,
                "subtask_count": len(decomposition.subtasks),
                "successful_count": sum(1 for r in results if r.success),
                "synthesis": synthesis,
            }

        except Exception:
            is_error = True
            raise
        finally:
            # Execute Stop hooks after task completion
            await self._execute_stop_hook(
                reason="error" if is_error else "completed",
                is_error=is_error,
                result=result if not is_error else None,
                query_id=task_id,
                context=context,
            )

        return result

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Call a tool with security hooks.

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            context: Optional execution context

        Returns:
            Tool result

        Raises:
            PermissionError: If hook denies the call
        """
        context = context or {}
        tool_use_id = f"tool-{uuid.uuid4().hex[:8]}"

        # Execute pre-tool-use hooks
        input_data = {
            "tool_name": tool_name,
            "tool_input": arguments,
        }

        hook_result = await self.hook_registry.execute_hooks(
            "PreToolUse",
            tool_name,
            input_data,
            tool_use_id,
            context,
        )

        if not hook_result.allowed:
            raise PermissionError(f"Tool call denied: {hook_result.reason}")

        # Use modified input if hooks transformed it
        if hook_result.modified_input:
            arguments = hook_result.modified_input.get("tool_input", arguments)

        # Call the tool and execute post-tool-use hooks
        is_error = False
        tool_output: Any = None
        try:
            tool_output = await self.tool_server.call_tool(tool_name, arguments)
        except Exception as e:
            is_error = True
            tool_output = str(e)
            # Execute PostToolUse hooks even on error
            await self._execute_post_tool_use_hook(tool_name, arguments, tool_output, is_error, tool_use_id, context)
            raise

        # Execute PostToolUse hooks on success
        await self._execute_post_tool_use_hook(tool_name, arguments, tool_output, is_error, tool_use_id, context)

        return tool_output

    async def _execute_post_tool_use_hook(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        is_error: bool,
        tool_use_id: str,
        context: dict[str, Any],
    ) -> None:
        """Execute PostToolUse hooks after tool execution.

        Args:
            tool_name: Name of the tool
            tool_input: Input provided to the tool
            tool_output: Output from the tool
            is_error: Whether the tool execution failed
            tool_use_id: Unique identifier for this tool use
            context: Execution context
        """
        post_input_data = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "is_error": is_error,
        }

        await self.hook_registry.execute_hooks(
            "PostToolUse",
            tool_name,
            post_input_data,
            tool_use_id,
            context,
        )

    def get_available_tools(self) -> list[str]:
        """Get list of available tools.

        Returns:
            List of tool names
        """
        return self.tool_server.list_tools()

    async def checkpoint_session(
        self,
        session_id: str,
        phase: str,
        summary: str,
    ) -> None:
        """Create a checkpoint for the session.

        Args:
            session_id: Session identifier
            phase: Phase name
            summary: Phase summary
        """
        await self.state_manager.checkpoint(session_id, phase, summary)
