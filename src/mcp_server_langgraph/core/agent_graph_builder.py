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
    - Context: messages, compaction status, kb_focus
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
    # KB Focus Mode: "all", "kb_only", "web_only", "none" (ADR-0094)
    kb_focus: str | None

    # Verification and refinement
    verification_passed: bool | None
    verification_score: float | None
    verification_feedback: str | None
    refinement_attempts: int | None
    user_request: str | None

    # Semantic tool/skill selection (Anthropic Tool Search Tool pattern)
    selected_tools: list[str] | None
    selected_skills: list[str] | None

    # Semantic memory retrieval for context enrichment
    retrieved_memories: list[str] | None


# Comparison keywords that indicate multi-faceted queries
_COMPARISON_KEYWORDS = frozenset(
    {
        "compare",
        "vs",
        "versus",
        "differ",
        "difference",
        "differences",
        "contrast",
        "between",
        "relationship",
        "compare to",
        "compared to",
    }
)


def is_complex_query(query: str) -> bool:
    """Detect if a query is complex (multi-entity, comparison, or long).

    Complex queries benefit from progressive discovery, which performs
    iterative refinement of search results.

    Args:
        query: The user's query text

    Returns:
        True if the query is complex, False otherwise

    Complexity indicators:
    - Contains comparison keywords (vs, differ, contrast)
    - Long queries (>30 words, likely multi-faceted)
    - Multiple explicit entities (detected by simple heuristics)
    """
    query_lower = query.lower()
    words = query.split()

    # Long queries are typically complex
    if len(words) > 30:
        return True

    # Check for comparison keywords
    for keyword in _COMPARISON_KEYWORDS:
        if keyword in query_lower:
            return True

    # Multiple "and" or "or" connectors suggest multiple topics
    connector_count = query_lower.count(" and ") + query_lower.count(" or ")
    return connector_count >= 2


async def _load_dynamic_context_impl(
    state: dict[str, Any],
    context_loader: Any,
    top_k: int = 3,
    max_tokens: int = 2000,
    enable_progressive: bool = False,
) -> dict[str, Any]:
    """
    Load dynamic context based on user request.

    This function is extracted for testability. It handles:
    - KB focus mode filtering
    - Context search and loading
    - Progressive discovery for complex queries (when enabled)
    - Event dispatch for observability

    Args:
        state: Current agent state with messages and kb_focus
        context_loader: DynamicContextLoader instance
        top_k: Maximum number of context items to retrieve
        max_tokens: Maximum tokens for context
        enable_progressive: Enable progressive discovery for complex queries

    Returns:
        Updated state with context messages inserted
    """
    from langchain_core.callbacks.manager import adispatch_custom_event

    from mcp_server_langgraph.core.dynamic_context_loader import (
        KBFocusMode,
        search_and_load_context,
    )
    from mcp_server_langgraph.observability.telemetry import logger

    last_message = state["messages"][-1]

    if not isinstance(last_message, HumanMessage):
        return {k: v for k, v in state.items() if k != "messages"}

    # Extract kb_focus from state (ADR-0094: KB Focus Mode)
    # Default to "all" if not specified for backward compatibility
    kb_focus_raw = state.get("kb_focus", "all") or "all"
    # Validate and cast to KBFocusMode (mypy type safety)
    valid_modes: set[KBFocusMode] = {"all", "kb_only", "web_only", "none"}
    kb_focus: KBFocusMode = kb_focus_raw if kb_focus_raw in valid_modes else "all"  # type: ignore[assignment]

    # Skip context loading if kb_focus is "none"
    if kb_focus == "none":
        logger.info("Skipping dynamic context loading (kb_focus=none)")
        return {k: v for k, v in state.items() if k != "messages"}

    try:
        logger.info("Loading dynamic context", extra={"kb_focus": kb_focus})
        query = last_message.content if isinstance(last_message.content, str) else str(last_message.content)

        # Use progressive discovery for complex queries when enabled
        if enable_progressive and is_complex_query(query):
            logger.info("Using progressive discovery for complex query")
            # Use progressive_discover directly for iterative refinement
            references = await context_loader.progressive_discover(
                initial_query=query,
                max_iterations=3,
            )
            # Load the discovered references
            loaded_contexts = await context_loader.load_batch(references, max_tokens=max_tokens)
        else:
            # Default path: use search_and_load_context (semantic_search)
            loaded_contexts = await search_and_load_context(
                query=query,
                loader=context_loader,
                top_k=top_k,
                max_tokens=max_tokens,
                focus_mode=kb_focus,
            )

        if loaded_contexts:
            # Calculate total tokens for event
            total_tokens = sum(getattr(ctx, "token_count", 0) for ctx in loaded_contexts)

            # Dispatch event for observability (chat.py:892 handles this)
            await adispatch_custom_event(
                "dynamic_context_loaded",
                {"refs_count": len(loaded_contexts), "tokens_loaded": total_tokens},
            )

            context_messages = context_loader.to_messages(loaded_contexts)
            current_messages = list(state["messages"])
            messages_before = current_messages[:-1]
            user_message = current_messages[-1]
            state["messages"] = messages_before + context_messages + [user_message]
            logger.info(f"Dynamic context loaded: {len(loaded_contexts)} contexts, {total_tokens} tokens")

    except Exception as e:
        logger.error(f"Dynamic context loading failed: {e}", exc_info=True)

    return {k: v for k, v in state.items() if k != "messages"}


async def _retrieve_tools_impl(
    state: dict[str, Any],
    semantic_index_manager: Any | None,
    max_selected_tools: int = 10,
) -> dict[str, Any]:
    """
    Select tools based on user query via semantic search.

    This function is extracted for testability. It implements:
    - Anthropic Tool Search Tool pattern
    - LangGraph Many Tools pattern
    - Graceful fallback to all tools on error

    Args:
        state: Current agent state with messages
        semantic_index_manager: SemanticIndexManager instance or None
        max_selected_tools: Maximum tools to select (from config)

    Returns:
        Updated state with selected_tools populated
    """
    from mcp_server_langgraph.observability.telemetry import logger

    # Get the last user message for semantic search
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if not last_message:
        # No message to search with - use all tools
        state["selected_tools"] = None
        logger.debug("No message for semantic tool selection, using all tools")
        return {k: v for k, v in state.items() if k != "messages"}

    # Extract query text from message
    if hasattr(last_message, "content"):
        query = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
    else:
        query = str(last_message)

    # Short queries may not benefit from semantic search
    if len(query.strip()) < 10:
        state["selected_tools"] = None
        logger.debug("Query too short for semantic tool selection, using all tools")
        return {k: v for k, v in state.items() if k != "messages"}

    try:
        # Use semantic index manager if available (ADR-0099)
        if semantic_index_manager is not None:
            logger.info(f"Semantic tool selection query: '{query[:50]}...'")

            # Get user_id from state for authorization (ADR-0068)
            user_id = state.get("user_id") or "user:anonymous"

            # Search for relevant tools using semantic similarity
            tool_entries = await semantic_index_manager.search_tools(
                query=query,
                user_id=user_id,
                limit=max_selected_tools,
            )

            if tool_entries:
                # Extract tool names from search results
                state["selected_tools"] = [entry.name for entry in tool_entries]
                logger.info(
                    f"Semantic tool selection: selected {len(state['selected_tools'])} tools: "
                    f"{state['selected_tools']}"
                )
            else:
                # No tools found - fall back to all tools
                state["selected_tools"] = None
                logger.info("Semantic tool selection: no matching tools, using all tools")
        else:
            # No semantic index manager provided - use all tools
            state["selected_tools"] = None
            logger.debug("Semantic tool selection: manager not configured, using all tools")

    except Exception as e:
        # Graceful fallback - use all tools if semantic search fails
        logger.warning(f"Semantic tool selection failed, falling back to all tools: {e}")
        state["selected_tools"] = None

    return {k: v for k, v in state.items() if k != "messages"}


async def _retrieve_skills_impl(
    state: dict[str, Any],
    semantic_index_manager: Any | None,
    max_selected_skills: int = 5,
) -> dict[str, Any]:
    """
    Retrieve skills based on user query via semantic search.

    This function is extracted for testability. It implements:
    - Anthropic Tool Search Tool pattern for skills
    - LangGraph Many Tools pattern for skill discovery
    - Graceful fallback to all skills on error

    Args:
        state: Current agent state with messages
        semantic_index_manager: SemanticIndexManager instance or None
        max_selected_skills: Maximum skills to select (from config)

    Returns:
        Updated state with selected_skills populated
    """
    from mcp_server_langgraph.observability.telemetry import logger

    # Get the last user message for semantic search
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if not last_message:
        # No message to search with - use all skills
        state["selected_skills"] = None
        logger.debug("No message for semantic skill selection, using all skills")
        return {k: v for k, v in state.items() if k != "messages"}

    # Extract query text from message
    if hasattr(last_message, "content"):
        query = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
    else:
        query = str(last_message)

    # Short queries may not benefit from semantic search
    if len(query.strip()) < 10:
        state["selected_skills"] = None
        logger.debug("Query too short for semantic skill selection, using all skills")
        return {k: v for k, v in state.items() if k != "messages"}

    try:
        # Use semantic index manager if available (ADR-0099)
        if semantic_index_manager is not None:
            logger.info(f"Semantic skill selection query: '{query[:50]}...'")

            # Get user_id from state for authorization (ADR-0068)
            user_id = state.get("user_id") or "user:anonymous"

            # Search for relevant skills using semantic similarity
            skill_entries = await semantic_index_manager.search_skills(
                query=query,
                user_id=user_id,
                limit=max_selected_skills,
            )

            if skill_entries:
                # Extract skill names from search results
                state["selected_skills"] = [entry.name for entry in skill_entries]
                logger.info(
                    f"Semantic skill selection: selected {len(state['selected_skills'])} skills: "
                    f"{state['selected_skills']}"
                )
            else:
                # No skills found - fall back to all skills
                state["selected_skills"] = None
                logger.info("Semantic skill selection: no matching skills, using all skills")
        else:
            # No semantic index manager provided - use all skills
            state["selected_skills"] = None
            logger.debug("Semantic skill selection: manager not configured, using all skills")

    except Exception as e:
        # Graceful fallback - use all skills if semantic search fails
        logger.warning(f"Semantic skill selection failed, falling back to all skills: {e}")
        state["selected_skills"] = None

    return {k: v for k, v in state.items() if k != "messages"}


async def _retrieve_memories_impl(
    state: dict[str, Any],
    semantic_index_manager: Any | None,
    max_retrieved_memories: int = 10,
) -> dict[str, Any]:
    """
    Retrieve memories based on user query via semantic search.

    This function is extracted for testability. It implements:
    - Semantic memory retrieval for context enrichment
    - Graceful fallback when no memories found or search fails

    Args:
        state: Current agent state with messages
        semantic_index_manager: SemanticIndexManager instance or None
        max_retrieved_memories: Maximum memories to retrieve (from config)

    Returns:
        Updated state with retrieved_memories populated
    """
    from mcp_server_langgraph.observability.telemetry import logger

    # Get the last user message for semantic search
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if not last_message:
        # No message to search with - no context enrichment
        state["retrieved_memories"] = None
        logger.debug("No message for memory retrieval, skipping")
        return {k: v for k, v in state.items() if k != "messages"}

    # Extract query text from message
    if hasattr(last_message, "content"):
        query = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
    else:
        query = str(last_message)

    # Short queries may not benefit from memory search
    if len(query.strip()) < 10:
        state["retrieved_memories"] = None
        logger.debug("Query too short for memory retrieval, skipping")
        return {k: v for k, v in state.items() if k != "messages"}

    try:
        # Use semantic index manager if available (ADR-0099)
        if semantic_index_manager is not None:
            logger.info(f"Semantic memory retrieval query: '{query[:50]}...'")

            # Get user_id from state for user-scoped memory search (ADR-0068)
            user_id = state.get("user_id") or "user:anonymous"

            # Search for relevant memories using semantic similarity
            # User searches their own memories (current_user_id == search_user_id)
            memory_entries = await semantic_index_manager.search_memories(
                query=query,
                current_user_id=user_id,
                search_user_id=user_id,
                limit=max_retrieved_memories,
            )

            if memory_entries:
                # Extract memory contents from search results
                state["retrieved_memories"] = [entry.content for entry in memory_entries]
                logger.info(
                    f"Semantic memory retrieval: retrieved {len(state['retrieved_memories'])} memories"
                )
            else:
                # No memories found - no context enrichment
                state["retrieved_memories"] = None
                logger.info("Semantic memory retrieval: no matching memories found")
        else:
            # No semantic index manager provided - no memory retrieval
            state["retrieved_memories"] = None
            logger.debug("Semantic memory retrieval: manager not configured, skipping")

    except Exception as e:
        # Graceful fallback - skip memory retrieval if search fails
        logger.warning(f"Semantic memory retrieval failed, skipping: {e}")
        state["retrieved_memories"] = None

    return {k: v for k, v in state.items() if k != "messages"}


async def _generate_response_impl(
    state: dict[str, Any],
    model: Any,
    bound_tools: list[Any],
    model_with_tools: Any | None,
    pydantic_agent: Any | None,
) -> dict[str, Any]:
    """
    Generate response implementation with dynamic tool binding support.

    This is a testable helper function for the generate_response node.
    It implements ADR-0099 dynamic tool binding:
    - If state["selected_tools"] contains tool names, bind only those tools
    - If state["selected_tools"] is None or empty, use all bound tools

    Args:
        state: Current agent state with messages and optional selected_tools
        model: Base LLM model (without tools bound)
        bound_tools: List of all available tool objects
        model_with_tools: Model pre-bound with all tools (fallback)
        pydantic_agent: Optional Pydantic AI agent for typed responses

    Returns:
        Updated state with response message
    """
    from langchain_core.messages import SystemMessage

    from mcp_server_langgraph.observability.telemetry import logger

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

    # Determine which model to use based on selected_tools (ADR-0099)
    selected_tool_names = state.get("selected_tools")

    if selected_tool_names and len(selected_tool_names) > 0 and bound_tools:
        # Filter tools to only those selected by semantic search
        filtered_tools = [t for t in bound_tools if t.name in selected_tool_names]

        if filtered_tools and hasattr(model, "bind_tools"):
            # Dynamically bind only the selected tools
            model_for_response = model.bind_tools(filtered_tools)
            logger.info(
                f"Dynamic tool binding: using {len(filtered_tools)} of {len(bound_tools)} tools "
                f"(selected: {selected_tool_names})"
            )
        elif model_with_tools is not None:
            # Fall back to pre-bound model if binding fails
            model_for_response = model_with_tools
            logger.warning("Dynamic tool binding failed, using all tools")
        else:
            # No tools available
            model_for_response = model
    elif model_with_tools is not None:
        # No selection or empty selection - use all tools
        model_for_response = model_with_tools
    else:
        # No tools bound at all
        model_for_response = model

    # Generate response
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
            from langchain_core.messages import AIMessage

            response = AIMessage(content=typed_response.content)
            logger.info(f"Pydantic AI response generated, confidence: {typed_response.confidence}")
        except Exception as e:
            logger.error(f"Pydantic AI response failed: {e}")
            response = await model_for_response.ainvoke(messages_list)  # type: ignore[arg-type]
    else:
        response = await model_for_response.ainvoke(messages_list)  # type: ignore[arg-type]

    # Check if the LLM generated tool calls (when tool calling is enabled)
    # If tool_calls are present, route to use_tools to execute them
    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls and len(tool_calls) > 0:
        state["next_action"] = "use_tools"
        logger.info(f"LLM generated {len(tool_calls)} tool call(s), routing to use_tools")
    else:
        # No tool calls - proceed with verification or end
        state["next_action"] = "end"

    return {**state, "messages": [response]}


def build_agent_graph(
    config: AgentConfig,
    checkpointer: Any | None = None,
    settings: Any | None = None,
    semantic_index_manager: Any | None = None,
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
        semantic_index_manager: Optional SemanticIndexManager for semantic tool
                                selection (ADR-0099). If provided, enables dynamic
                                tool selection based on query similarity.

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

    # Bind tools to model if tool calling is enabled
    # This allows the LLM to autonomously decide when to call tools
    model_with_tools = model
    bound_tools: list[Any] = []
    if config.enable_tool_calling:
        try:
            from mcp_server_langgraph.tools import get_all_tools

            bound_tools = get_all_tools(effective_settings)
            if bound_tools and hasattr(model, "bind_tools"):
                model_with_tools = model.bind_tools(bound_tools)
                logger.info(f"Tool calling enabled: bound {len(bound_tools)} tools to model")
            elif bound_tools:
                logger.warning("Model does not support bind_tools - tool calling will use keyword routing")
            else:
                logger.info("No tools available to bind")
        except Exception as e:
            logger.warning(f"Failed to bind tools to model: {e}")
            # Fall back to model without tools

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
        if context_loader:
            top_k = getattr(effective_settings, "dynamic_context_top_k", 3)
            max_tokens = getattr(effective_settings, "dynamic_context_max_tokens", 2000)
            return await _load_dynamic_context_impl(
                state=dict(state),
                context_loader=context_loader,
                top_k=top_k,
                max_tokens=max_tokens,
            )  # type: ignore[return-value]
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

    async def retrieve_tools(state: AgentState) -> AgentState:
        """Dynamically retrieve tools based on user query via semantic search.

        Implements the Anthropic Tool Search Tool pattern and LangGraph's
        Many Tools pattern. Uses semantic embeddings to find relevant tools
        before binding them to the LLM, reducing token usage with 50+ tools.

        When semantic search fails or returns no results, falls back to
        using all available tools (graceful degradation).
        """
        # Delegate to testable helper function
        return await _retrieve_tools_impl(
            state=dict(state),
            semantic_index_manager=semantic_index_manager,
            max_selected_tools=config.max_selected_tools,
        )  # type: ignore[return-value]

    async def retrieve_skills(state: AgentState) -> AgentState:
        """Dynamically retrieve skills based on user query via semantic search.

        Implements the Anthropic Tool Search Tool pattern for skill discovery.
        Uses semantic embeddings to find relevant skills before binding them
        to the LLM, enabling progressive skill loading.

        When semantic search fails or returns no results, falls back to
        using all available skills (graceful degradation).
        """
        # Delegate to testable helper function
        return await _retrieve_skills_impl(
            state=dict(state),
            semantic_index_manager=semantic_index_manager,
            max_selected_skills=config.max_selected_skills,
        )  # type: ignore[return-value]

    async def retrieve_memories(state: AgentState) -> AgentState:
        """Retrieve relevant memories for context enrichment via semantic search.

        Implements semantic memory retrieval for the agent. Uses embeddings
        to find relevant memories (preferences, facts, history) to enrich
        the context before LLM invocation.

        When semantic search fails or returns no results, continues without
        memory context (graceful degradation).
        """
        # Delegate to testable helper function
        return await _retrieve_memories_impl(
            state=dict(state),
            semantic_index_manager=semantic_index_manager,
            max_retrieved_memories=config.max_retrieved_memories,
        )  # type: ignore[return-value]

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
        """Generate final response using LLM with dynamic tool binding (ADR-0099).

        When semantic tool selection is enabled, this node uses only the tools
        selected by the retrieve_tools node, reducing token usage significantly.
        """
        return await _generate_response_impl(
            state=dict(state),
            model=model,
            bound_tools=bound_tools,
            model_with_tools=model_with_tools,
            pydantic_agent=pydantic_agent,
        )  # type: ignore[return-value]

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

    def should_use_tools_or_continue(state: AgentState) -> Literal["use_tools", "verify", "end"]:
        """Conditional edge function to route based on tool_calls in response.

        When the LLM generates tool_calls (with tool-bound model), route to
        use_tools to execute them. Otherwise, continue to verification or end.
        """
        next_action = state.get("next_action", "end") or "end"
        if next_action == "use_tools":
            return "use_tools"
        # If verification is enabled, "verify" will be mapped to the verify node
        # Otherwise, "end" will be mapped to END
        return "end" if next_action == "end" else "verify"

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

    # Determine the node that comes before router (for semantic tool selection)
    pre_router_node: str = "router"  # What to connect TO router

    # Add semantic tool retrieval node if enabled (Anthropic Tool Search Tool pattern)
    if config.enable_semantic_tool_search:
        workflow.add_node("retrieve_tools", retrieve_tools)
        pre_router_node = "retrieve_tools"  # retrieve_tools comes before router
        workflow.add_edge("retrieve_tools", "router")

    # Add semantic skill retrieval node if enabled (ADR-0099)
    if config.enable_semantic_skill_search:
        workflow.add_node("retrieve_skills", retrieve_skills)
        # retrieve_skills comes before router (or before retrieve_tools if that's before router)
        if config.enable_semantic_tool_search:
            # Chain: retrieve_skills -> retrieve_tools -> router
            workflow.add_edge("retrieve_skills", "retrieve_tools")
            pre_router_node = "retrieve_skills"
        else:
            # Chain: retrieve_skills -> router
            workflow.add_edge("retrieve_skills", "router")
            pre_router_node = "retrieve_skills"

    # Add semantic memory retrieval node if enabled (ADR-0099)
    if config.enable_semantic_memory_search:
        workflow.add_node("retrieve_memories", retrieve_memories)
        # retrieve_memories comes first in the semantic search chain
        if config.enable_semantic_skill_search:
            # Chain: retrieve_memories -> retrieve_skills -> ...
            workflow.add_edge("retrieve_memories", "retrieve_skills")
            pre_router_node = "retrieve_memories"
        elif config.enable_semantic_tool_search:
            # Chain: retrieve_memories -> retrieve_tools -> router
            workflow.add_edge("retrieve_memories", "retrieve_tools")
            pre_router_node = "retrieve_memories"
        else:
            # Chain: retrieve_memories -> router
            workflow.add_edge("retrieve_memories", "router")
            pre_router_node = "retrieve_memories"

    # Add optional nodes and wire edges based on config
    if config.enable_dynamic_context_loading and context_loader:
        workflow.add_node("load_context", load_dynamic_context)
        workflow.add_edge(START, "load_context")
        entry_node = None  # START already wired

        if config.enable_context_compaction:
            workflow.add_node("compact", compact_context)
            workflow.add_edge("load_context", "compact")
            workflow.add_edge("compact", pre_router_node)
        else:
            workflow.add_edge("load_context", pre_router_node)

    elif config.enable_context_compaction:
        workflow.add_node("compact", compact_context)
        workflow.add_edge(START, "compact")
        workflow.add_edge("compact", pre_router_node)
        entry_node = None  # START already wired

    # Wire START to entry if not already wired
    if entry_node:
        if config.enable_semantic_memory_search:
            # retrieve_memories is the first node when memory search is enabled
            workflow.add_edge(START, "retrieve_memories")
        elif config.enable_semantic_skill_search:
            # retrieve_skills is the first node when skill search is enabled
            workflow.add_edge(START, "retrieve_skills")
        elif config.enable_semantic_tool_search:
            workflow.add_edge(START, "retrieve_tools")
        else:
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

        # Respond can route to: tools (if tool_calls), verify, or end
        workflow.add_conditional_edges(
            "respond",
            should_use_tools_or_continue,
            {
                "use_tools": "tools",
                "verify": "verify",
                "end": END,
            },
        )
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
        # No verification - respond can route to tools or END
        workflow.add_conditional_edges(
            "respond",
            should_use_tools_or_continue,
            {
                "use_tools": "tools",
                "verify": END,  # Map verify to END when verification disabled
                "end": END,
            },
        )

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
            "enable_tool_calling": config.enable_tool_calling,
            "enable_semantic_tool_search": config.enable_semantic_tool_search,
            "bound_tools_count": len(bound_tools),
            "nodes": list(compiled.nodes.keys()),
        },
    )

    return compiled


__all__ = ["build_agent_graph", "AgentState"]
