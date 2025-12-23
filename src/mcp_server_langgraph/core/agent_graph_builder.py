"""
Agent Graph Builder - Compile-Time Graph Composition.

This module builds LangGraph agent graphs based on AgentConfig at compile time.
Feature flags are evaluated during graph construction, not at runtime.

Key principle: Open/Closed Principle (OCP)
- Open for extension (new features via AgentConfig)
- Closed for modification (node functions don't check feature flags)

Usage:
    from mcp_server_langgraph.core.agent_config import AgentConfig
    from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

    # Full-featured graph
    config = AgentConfig()
    graph = build_agent_graph(config)

    # Minimal graph (no verification, no compaction)
    config = AgentConfig(
        enable_verification=False,
        enable_context_compaction=False,
    )
    graph = build_agent_graph(config)
"""

from __future__ import annotations

import operator
from typing import TYPE_CHECKING, Annotated, Any, Literal, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

if TYPE_CHECKING:
    from mcp_server_langgraph.core.agent_config import AgentConfig


class AgentState(TypedDict):
    """
    State for the agent graph.

    Implements full agentic loop state management:
    - Context: messages, compaction status
    - Routing: next_action, confidence, reasoning
    - Verification: verification results, refinement attempts
    - Metadata: user_id, request_id
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    user_id: str | None
    request_id: str | None
    session_id: str | None  # For interrupt checking (Claude Agent SDK pattern)
    routing_confidence: float | None
    reasoning: str | None

    # Context management
    compaction_applied: bool | None
    original_message_count: int | None

    # Verification and refinement
    verification_passed: bool | None
    verification_score: float | None
    verification_feedback: str | None
    refinement_attempts: int | None
    user_request: str | None


def build_agent_graph(
    config: AgentConfig,
    checkpointer: Any | None = None,
    settings: Any | None = None,
) -> Any:
    """
    Build a LangGraph agent graph based on AgentConfig.

    This function implements compile-time graph composition:
    - Nodes are conditionally added based on config
    - No runtime feature flag checks in node functions
    - Graph topology is determined at construction time

    Args:
        config: AgentConfig specifying which features to enable
        checkpointer: Optional checkpointer for state persistence.
                      If None and enable_checkpointing=True, uses MemorySaver.
        settings: Optional Settings object for LLM configuration.
                  If None, uses global settings.

    Returns:
        Compiled LangGraph StateGraph
    """
    from mcp_server_langgraph.core.context_manager import ContextManager
    from mcp_server_langgraph.llm.factory import create_llm_from_config
    from mcp_server_langgraph.llm.verifier import OutputVerifier
    from mcp_server_langgraph.observability.telemetry import logger

    # Use provided settings or fall back to global settings
    if settings is None:
        from mcp_server_langgraph.core.config import settings as global_settings

        effective_settings = global_settings
    else:
        effective_settings = settings

    # Initialize the model via LiteLLM factory
    model = create_llm_from_config(effective_settings)

    # Initialize context manager (only used if compaction enabled)
    context_manager = None
    if config.enable_context_compaction:
        context_manager = ContextManager(
            compaction_threshold=config.compaction_threshold,
            target_after_compaction=config.target_after_compaction,
            recent_message_count=config.recent_message_count,
        )

    # Initialize output verifier (only used if verification enabled)
    output_verifier = None
    if config.enable_verification:
        output_verifier = OutputVerifier(
            quality_threshold=config.verification_quality_threshold,
        )

    # Initialize dynamic context loader (only if enabled)
    context_loader = None
    if config.enable_dynamic_context_loading:
        try:
            from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader

            context_loader = DynamicContextLoader()
            logger.info("Dynamic context loader initialized")
        except ImportError:
            logger.warning("Dynamic context loader not available (import failed)")
            # Don't add the node if loader isn't available
        except Exception as e:
            logger.warning(f"Dynamic context loader initialization failed: {e}")
            # Don't add the node if initialization fails (e.g., embedding provider not configured)

    # Initialize Pydantic AI agent if available
    pydantic_agent = None
    try:
        from mcp_server_langgraph.llm.pydantic_agent import create_pydantic_agent

        pydantic_agent = create_pydantic_agent()
        logger.info("Pydantic AI agent initialized for type-safe routing")
    except Exception as e:
        logger.warning(f"Failed to initialize Pydantic AI agent: {e}")

    # =========================================================================
    # Node Functions (no feature flag checks - topology determined at build)
    # =========================================================================

    async def load_dynamic_context(state: AgentState) -> AgentState:
        """Load relevant context dynamically based on user request."""
        # Note: This node is only added if enable_dynamic_context_loading=True
        # and context_loader was successfully initialized
        last_message = state["messages"][-1]

        if isinstance(last_message, HumanMessage) and context_loader:
            try:
                from mcp_server_langgraph.core.dynamic_context_loader import search_and_load_context

                logger.info("Loading dynamic context")
                query = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
                loaded_contexts = await search_and_load_context(
                    query=query,
                    loader=context_loader,
                    top_k=3,
                    max_tokens=2000,
                )

                if loaded_contexts:
                    context_messages = context_loader.to_messages(loaded_contexts)
                    current_messages = list(state["messages"])
                    messages_before = current_messages[:-1]
                    user_message = current_messages[-1]
                    state["messages"] = messages_before + context_messages + [user_message]
                    logger.info(f"Dynamic context loaded: {len(loaded_contexts)} contexts")

            except Exception as e:
                logger.error(f"Dynamic context loading failed: {e}", exc_info=True)

        return {k: v for k, v in state.items() if k != "messages"}  # type: ignore[return-value]

    async def compact_context(state: AgentState) -> AgentState:
        """Compact conversation context when approaching token limits."""
        # Note: This node is only added if enable_context_compaction=True
        messages_list = list(state["messages"])

        if context_manager and context_manager.needs_compaction(messages_list):
            try:
                logger.info("Applying context compaction")
                result = await context_manager.compact_conversation(messages_list)
                state["messages"] = result.compacted_messages
                state["compaction_applied"] = True
                state["original_message_count"] = len(messages_list)
                logger.info(f"Context compacted: {len(messages_list)} -> {len(result.compacted_messages)}")
            except Exception as e:
                logger.error(f"Context compaction failed: {e}", exc_info=True)
                state["compaction_applied"] = False
        else:
            state["compaction_applied"] = False

        return {k: v for k, v in state.items() if k != "messages"}  # type: ignore[return-value]

    async def route_input(state: AgentState) -> AgentState:
        """Route based on message type with Pydantic AI for type-safe decisions."""
        last_message = state["messages"][-1]

        if isinstance(last_message, HumanMessage):
            user_request = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
            state["user_request"] = user_request

            if pydantic_agent:
                try:
                    # Ensure content is a string for route_message
                    message_content = user_request  # Already converted to str above
                    decision = await pydantic_agent.route_message(
                        message_content,
                        context={"user_id": state.get("user_id", "unknown"), "message_count": str(len(state["messages"]))},
                    )
                    state["next_action"] = decision.action
                    state["routing_confidence"] = decision.confidence
                    state["reasoning"] = decision.reasoning
                    logger.info(f"Pydantic AI routing: {decision.action}")
                except Exception as e:
                    logger.error(f"Pydantic AI routing failed: {e}")
                    state["next_action"] = "respond"
                    state["routing_confidence"] = 0.5
                    state["reasoning"] = "Fallback routing"
            else:
                # Simple keyword-based fallback
                content = user_request.lower()
                if any(keyword in content for keyword in ["search", "calculate", "lookup"]):
                    state["next_action"] = "use_tools"
                else:
                    state["next_action"] = "respond"
                state["routing_confidence"] = 0.5
                state["reasoning"] = "Keyword-based fallback"

        return {k: v for k, v in state.items() if k != "messages"}  # type: ignore[return-value]

    async def use_tools(state: AgentState) -> AgentState:
        """Execute tools based on LangChain tool calls."""

        messages = state["messages"]
        last_message = messages[-1]

        tool_calls = getattr(last_message, "tool_calls", None) if hasattr(last_message, "tool_calls") else None

        if not tool_calls or len(tool_calls) == 0:
            logger.warning("use_tools node reached but no tool calls found")
            tool_response = AIMessage(content="No tool calls found. Proceeding with direct response.")
            return {**state, "messages": [tool_response], "next_action": "respond"}

        logger.info(f"Executing {len(tool_calls)} tools")

        # Execute tools (parallel execution controlled by config.enable_parallel_execution)
        if config.enable_parallel_execution and len(tool_calls) > 1:
            tool_messages = await _execute_tools_parallel(tool_calls, config.max_parallel_tools)
        else:
            tool_messages = await _execute_tools_serial(tool_calls)

        return {**state, "messages": tool_messages, "next_action": "respond"}

    async def _execute_tools_serial(tool_calls: list[dict]) -> list:  # type: ignore[type-arg]
        """Execute tools serially."""
        from langchain_core.messages import ToolMessage

        from mcp_server_langgraph.tools import get_tool_by_name

        tool_messages: list[ToolMessage] = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_call_id = tool_call.get("id", str(len(tool_messages)))
            tool_args = tool_call.get("args", {})

            try:
                tool = get_tool_by_name(tool_name)
                if tool is None:
                    result_content = f"Error: Tool '{tool_name}' not found"
                    logger.error(f"Tool '{tool_name}' not found")
                else:
                    logger.info(f"Invoking tool '{tool_name}'")
                    if hasattr(tool, "ainvoke"):
                        result_content = await tool.ainvoke(tool_args)
                    else:
                        result_content = tool.invoke(tool_args)
                    logger.info(f"Tool '{tool_name}' executed successfully")
            except Exception as e:
                result_content = f"Error executing tool '{tool_name}': {e!s}"
                logger.error(f"Tool execution failed: {tool_name}", exc_info=True)

            tool_message = ToolMessage(
                content=str(result_content),
                tool_call_id=tool_call_id,
                name=tool_name,
            )
            tool_messages.append(tool_message)

        return tool_messages

    async def _execute_tools_parallel(tool_calls: list[dict], max_parallel: int) -> list:  # type: ignore[type-arg]
        """Execute tools in parallel."""
        from langchain_core.messages import ToolMessage

        from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation
        from mcp_server_langgraph.tools import get_tool_by_name

        executor = ParallelToolExecutor(max_parallelism=max_parallel)

        invocations = [
            ToolInvocation(
                tool_name=tc.get("name", "unknown"),
                arguments=tc.get("args", {}),
                invocation_id=tc.get("id", f"call_{i}"),
                dependencies=[],
            )
            for i, tc in enumerate(tool_calls)
        ]

        async def execute_single_tool(tool_name: str, arguments: dict) -> Any:  # type: ignore[type-arg]
            tool = get_tool_by_name(tool_name)
            if tool is None:
                raise ValueError(f"Tool '{tool_name}' not found")
            if hasattr(tool, "ainvoke"):
                return await tool.ainvoke(arguments)
            return tool.invoke(arguments)

        try:
            results = await executor.execute_parallel(invocations, execute_single_tool)
            tool_messages = []
            for result in results:
                content = f"Error: {result.error!s}" if result.error else str(result.result)
                tool_message = ToolMessage(
                    content=content,
                    tool_call_id=result.invocation_id,
                    name=result.tool_name,
                )
                tool_messages.append(tool_message)
            return tool_messages
        except Exception as e:
            logger.error(f"Parallel tool execution failed: {e}", exc_info=True)
            return await _execute_tools_serial(tool_calls)

    async def generate_response(state: AgentState) -> AgentState:
        """Generate final response using LLM."""
        messages_list = list(state["messages"])

        refinement_attempts = state.get("refinement_attempts") or 0
        if refinement_attempts > 0 and state.get("verification_feedback"):
            refinement_prompt = SystemMessage(
                content=f"<refinement_guidance>\n"
                f"Previous response had issues. Please refine based on this feedback:\n"
                f"{state['verification_feedback']}\n"
                f"</refinement_guidance>"
            )
            messages_list = [refinement_prompt] + messages_list

        if pydantic_agent:
            try:
                typed_response = await pydantic_agent.generate_response(
                    messages_list,
                    context={
                        "user_id": state.get("user_id", "unknown"),
                        "routing_confidence": str(state.get("routing_confidence", 0.0)),
                        "refinement_attempt": str(refinement_attempts),
                    },
                )
                response = AIMessage(content=typed_response.content)
                logger.info(f"Pydantic AI response generated, confidence: {typed_response.confidence}")
            except Exception as e:
                logger.error(f"Pydantic AI response failed: {e}")
                response = await model.ainvoke(messages_list)  # type: ignore[arg-type]
        else:
            response = await model.ainvoke(messages_list)  # type: ignore[arg-type]

        # Next action is determined by graph structure:
        # - If verification enabled: respond -> verify (unconditional edge)
        # - If verification disabled: respond -> END (unconditional edge)
        # The verify node will set next_action after verification.
        # We just preserve the current next_action or set to empty.
        return {**state, "messages": [response]}

    async def verify_response(state: AgentState) -> AgentState:
        """Verify response quality using LLM-as-judge pattern.

        When visual verification is enabled and the response contains URLs,
        this function also performs visual verification and combines the results.
        """
        # Note: This node is only added if enable_verification=True
        response_message = state["messages"][-1]
        response_content = response_message.content if hasattr(response_message, "content") else str(response_message)
        response_text = response_content if isinstance(response_content, str) else str(response_content)

        user_request = state.get("user_request") or ""
        conversation_context = list(state["messages"])[:-1]

        try:
            logger.info("Verifying response quality")

            # Text verification (always performed)
            text_result = await output_verifier.verify_response(  # type: ignore[union-attr]
                response=response_text,
                user_request=user_request,
                conversation_context=conversation_context,
            )

            # Visual verification (conditional on config and URL presence)
            # Uses extracted helper functions for cleaner code
            from mcp_server_langgraph.core.visual_verification_helper import (
                combine_verification_results,
                extract_urls_from_text,
                perform_visual_verification,
                prioritize_urls,
            )

            visual_results: list[Any] = []
            if config.enable_visual_verification:
                # Extract and prioritize URLs
                all_urls = extract_urls_from_text(response_text)

                if all_urls:
                    urls_to_verify = prioritize_urls(
                        urls=all_urls,
                        priority=config.visual_verification_url_priority,
                        max_urls=config.visual_verification_max_urls,
                    )

                    logger.info(
                        f"Visual verification enabled, found {len(all_urls)} URL(s), "
                        f"verifying {len(urls_to_verify)} (priority: {config.visual_verification_url_priority})"
                    )

                    # Perform visual verification on prioritized URLs
                    visual_results = await perform_visual_verification(
                        urls=urls_to_verify,
                        expected_state=user_request,
                        output_verifier=output_verifier,
                    )

            # Combine text and visual results using configurable weights
            combined = combine_verification_results(
                text_result=text_result,
                visual_results=visual_results,
                text_weight=config.visual_verification_text_weight,
                visual_weight=config.visual_verification_visual_weight,
            )

            state["verification_passed"] = combined["passed"]
            state["verification_score"] = combined["score"]
            state["verification_feedback"] = combined["feedback"]

            refinement_attempts = state.get("refinement_attempts", 0)

            if state["verification_passed"]:
                state["next_action"] = "end"
                logger.info(f"Verification passed, score: {state['verification_score']}")
            elif (refinement_attempts or 0) < config.max_refinement_attempts:
                state["next_action"] = "refine"
                logger.info(f"Verification failed, refining (attempt {(refinement_attempts or 0) + 1})")
            else:
                state["next_action"] = "end"
                logger.warning("Max refinement attempts reached, accepting response")

        except Exception as e:
            logger.error(f"Verification failed: {e}", exc_info=True)
            state["verification_passed"] = True
            state["next_action"] = "end"

        return {k: v for k, v in state.items() if k != "messages"}  # type: ignore[return-value]

    async def refine_response(state: AgentState) -> AgentState:
        """Refine response based on verification feedback."""
        # Note: This node is only added if enable_verification=True
        refinement_attempts = state.get("refinement_attempts", 0) or 0
        state["refinement_attempts"] = refinement_attempts + 1
        state["messages"] = state["messages"][:-1]  # Remove failed response
        state["next_action"] = "respond"

        logger.info(f"Refining response, attempt {state['refinement_attempts']}")
        return {k: v for k, v in state.items() if k != "messages"}  # type: ignore[return-value]

    def should_continue(state: AgentState) -> Literal["use_tools", "respond", "end"]:
        """Conditional edge function for routing."""
        next_action = state.get("next_action", "respond") or "respond"
        if not next_action or next_action not in ["use_tools", "respond", "end"]:
            return "respond"
        return next_action  # type: ignore[return-value]

    def should_verify(state: AgentState) -> Literal["verify", "refine", "end"]:
        """Conditional edge function for verification loop."""
        next_action = state.get("next_action", "end") or "end"
        if not next_action or next_action not in ["verify", "refine", "end"]:
            return "end"
        return next_action  # type: ignore[return-value]

    # =========================================================================
    # Build Graph (compile-time composition based on config)
    # =========================================================================

    workflow = StateGraph(AgentState)

    # Core nodes (always present)
    workflow.add_node("router", route_input)
    workflow.add_node("tools", use_tools)
    workflow.add_node("respond", generate_response)

    # Determine entry point based on enabled features
    entry_node: str | None = "router"  # Default entry

    # Add optional nodes and wire edges based on config
    if config.enable_dynamic_context_loading and context_loader:
        workflow.add_node("load_context", load_dynamic_context)
        workflow.add_edge(START, "load_context")
        entry_node = None  # START already wired

        if config.enable_context_compaction:
            workflow.add_node("compact", compact_context)
            workflow.add_edge("load_context", "compact")
            workflow.add_edge("compact", "router")
        else:
            workflow.add_edge("load_context", "router")

    elif config.enable_context_compaction:
        workflow.add_node("compact", compact_context)
        workflow.add_edge(START, "compact")
        workflow.add_edge("compact", "router")
        entry_node = None  # START already wired

    # Wire START to entry if not already wired
    if entry_node:
        workflow.add_edge(START, entry_node)

    # Router conditional edges
    workflow.add_conditional_edges(
        "router",
        should_continue,
        {
            "use_tools": "tools",
            "respond": "respond",
        },
    )
    workflow.add_edge("tools", "respond")

    # Add verification nodes if enabled
    if config.enable_verification:
        workflow.add_node("verify", verify_response)
        workflow.add_node("refine", refine_response)

        workflow.add_edge("respond", "verify")
        workflow.add_conditional_edges(
            "verify",
            should_verify,
            {
                "verify": "verify",  # Defensive
                "refine": "refine",
                "end": END,
            },
        )
        workflow.add_edge("refine", "respond")
    else:
        # No verification - respond goes directly to END
        workflow.add_edge("respond", END)

    # Compile with optional checkpointing
    if config.enable_checkpointing:
        if checkpointer is None:
            # Use MemorySaver as default if no checkpointer provided
            from langgraph.checkpoint.memory import MemorySaver

            checkpointer = MemorySaver()
        compiled = workflow.compile(checkpointer=checkpointer)
    else:
        compiled = workflow.compile()

    # Store graph version in metadata for checkpoint compatibility
    compiled._graph_version = config.graph_version  # type: ignore[attr-defined]

    logger.info(
        f"Agent graph built with version {config.graph_version}",
        extra={
            "enable_compaction": config.enable_context_compaction,
            "enable_verification": config.enable_verification,
            "enable_dynamic_context": config.enable_dynamic_context_loading,
            "nodes": list(compiled.nodes.keys()),
        },
    )

    return compiled


__all__ = ["build_agent_graph", "AgentState"]
