"""
LangGraph Functional API Agent with full observability and multi-provider LLM support
Includes OpenTelemetry and LangSmith tracing integration
Enhanced with Pydantic AI for type-safe routing and responses

Implements Anthropic's gather-action-verify-repeat agentic loop:
1. Gather Context: Compaction and just-in-time loading
2. Take Action: Routing and tool execution
3. Verify Work: LLM-as-judge pattern
4. Repeat: Iterative refinement based on feedback
"""

import asyncio
import operator
from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.context_manager import ContextManager
from mcp_server_langgraph.llm.factory import create_llm_from_config
from mcp_server_langgraph.llm.verifier import OutputVerifier
from mcp_server_langgraph.observability.telemetry import logger

# Import Dynamic Context Loader if enabled
try:
    from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader, search_and_load_context

    DYNAMIC_CONTEXT_AVAILABLE = True
except ImportError:
    DYNAMIC_CONTEXT_AVAILABLE = False
    logger.warning("Dynamic context loader not available")

# Import Redis checkpointer if available
try:
    from langgraph.checkpoint.redis import RedisSaver

    REDIS_CHECKPOINTER_AVAILABLE = True
except ImportError:
    REDIS_CHECKPOINTER_AVAILABLE = False
    logger.warning("Redis checkpointer not available, using fallback to MemorySaver")

# Import Pydantic AI for type-safe responses
try:
    from mcp_server_langgraph.llm.pydantic_agent import create_pydantic_agent

    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    logger.warning("Pydantic AI not available, using fallback routing")

# Import LangSmith config if available
try:
    from mcp_server_langgraph.observability.langsmith import get_run_metadata, get_run_tags, langsmith_config

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    langsmith_config = None


class AgentState(TypedDict):
    """
    State for the agent graph.

    Implements full agentic loop state management:
    - Context: messages, compaction status
    - Routing: next_action, confidence, reasoning
    - Verification: verification results, refinement attempts
    - Metadata: user_id, request_id
    """

    messages: Annotated[list[BaseMessage], operator.add]
    next_action: str
    user_id: str | None
    request_id: str | None
    routing_confidence: float | None  # Confidence from Pydantic AI routing
    reasoning: str | None  # Reasoning from Pydantic AI

    # Context management
    compaction_applied: bool | None  # Whether compaction was applied
    original_message_count: int | None  # Message count before compaction

    # Verification and refinement
    verification_passed: bool | None  # Whether verification passed
    verification_score: float | None  # Overall quality score (0-1)
    verification_feedback: str | None  # Feedback for refinement
    refinement_attempts: int | None  # Number of refinement iterations
    user_request: str | None  # Original user request for verification


def _initialize_pydantic_agent():
    """Initialize Pydantic AI agent if available"""
    if not PYDANTIC_AI_AVAILABLE:
        return None

    try:
        pydantic_agent = create_pydantic_agent()
        logger.info("Pydantic AI agent initialized for type-safe routing")
        return pydantic_agent
    except Exception as e:
        logger.warning(f"Failed to initialize Pydantic AI agent: {e}", exc_info=True)
        return None


def _create_checkpointer() -> BaseCheckpointSaver:
    """
    Create checkpointer backend based on configuration

    Returns:
        BaseCheckpointSaver: Configured checkpointer (MemorySaver or RedisSaver)
    """
    backend = settings.checkpoint_backend.lower()

    if backend == "redis":
        if not REDIS_CHECKPOINTER_AVAILABLE:
            logger.warning(
                "Redis checkpointer not available (langgraph-checkpoint-redis not installed), "
                "falling back to MemorySaver. Install with: pip install langgraph-checkpoint-redis"
            )
            return MemorySaver()

        try:
            logger.info(
                "Initializing Redis checkpointer for distributed conversation state",
                extra={
                    "redis_url": settings.checkpoint_redis_url,
                    "ttl_seconds": settings.checkpoint_redis_ttl,
                },
            )

            # Create Redis checkpointer with TTL
            checkpointer = RedisSaver.from_conn_string(
                conn_string=settings.checkpoint_redis_url,
                ttl=settings.checkpoint_redis_ttl,
            )

            logger.info("Redis checkpointer initialized successfully")
            return checkpointer

        except Exception as e:
            logger.error(
                f"Failed to initialize Redis checkpointer: {e}. Falling back to MemorySaver",
                exc_info=True,
            )
            return MemorySaver()

    elif backend == "memory":
        logger.info("Using in-memory checkpointer (not suitable for multi-replica deployments)")
        return MemorySaver()

    else:
        logger.warning(
            f"Unknown checkpoint backend '{backend}', falling back to MemorySaver. " f"Supported: 'memory', 'redis'"
        )
        return MemorySaver()


def _get_runnable_config(user_id: Optional[str] = None, request_id: Optional[str] = None) -> Optional[RunnableConfig]:
    """Get runnable config with LangSmith metadata"""
    if not LANGSMITH_AVAILABLE or not langsmith_config.is_enabled():
        return None

    return RunnableConfig(
        run_name="mcp-server-langgraph", tags=get_run_tags(user_id), metadata=get_run_metadata(user_id, request_id)
    )


def _fallback_routing(state: AgentState, last_message: HumanMessage) -> AgentState:
    """Fallback routing logic without Pydantic AI"""
    # Determine if this needs tools or direct response
    if any(keyword in last_message.content.lower() for keyword in ["search", "calculate", "lookup"]):
        state["next_action"] = "use_tools"
    else:
        state["next_action"] = "respond"

    state["routing_confidence"] = 0.5  # Low confidence for fallback
    state["reasoning"] = "Fallback keyword-based routing"

    return state


def create_agent_graph():
    """
    Create the LangGraph agent using functional API with LiteLLM and observability.

    Implements Anthropic's agentic loop:
    1. Gather Context: compact_context node
    2. Take Action: route_input → use_tools → generate_response
    3. Verify Work: verify_response node
    4. Repeat: refine_response loop (max 3 iterations)
    """

    # Initialize the model via LiteLLM factory
    model = create_llm_from_config(settings)

    # Initialize Pydantic AI agent if available
    pydantic_agent = _initialize_pydantic_agent()

    # Initialize context manager for compaction
    context_manager = ContextManager(compaction_threshold=8000, target_after_compaction=4000, recent_message_count=5)

    # Initialize output verifier for quality checks
    output_verifier = OutputVerifier(quality_threshold=0.7)

    # Initialize dynamic context loader if enabled
    enable_dynamic_loading = getattr(settings, "enable_dynamic_context_loading", False)
    context_loader = None
    if enable_dynamic_loading and DYNAMIC_CONTEXT_AVAILABLE:
        try:
            context_loader = DynamicContextLoader()
            logger.info("Dynamic context loader initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize dynamic context loader: {e}", exc_info=True)
            enable_dynamic_loading = False

    # Feature flags for new capabilities
    enable_context_compaction = getattr(settings, "enable_context_compaction", True)
    enable_verification = getattr(settings, "enable_verification", True)
    max_refinement_attempts = getattr(settings, "max_refinement_attempts", 3)

    # Define node functions

    async def load_dynamic_context(state: AgentState) -> AgentState:
        """
        Load relevant context dynamically based on user request.

        Implements Anthropic's Just-in-Time loading strategy.
        """
        if not enable_dynamic_loading or not context_loader:
            return state

        last_message = state["messages"][-1]

        if isinstance(last_message, HumanMessage):
            try:
                logger.info("Loading dynamic context")

                # Search for relevant context
                loaded_contexts = await search_and_load_context(
                    query=last_message.content,
                    loader=context_loader,
                    top_k=getattr(settings, "dynamic_context_top_k", 3),
                    max_tokens=getattr(settings, "dynamic_context_max_tokens", 2000),
                )

                if loaded_contexts:
                    # Convert to messages and prepend
                    context_messages = context_loader.to_messages(loaded_contexts)

                    # Insert context before user message
                    messages_before = state["messages"][:-1]
                    user_message = state["messages"][-1]
                    state["messages"] = messages_before + context_messages + [user_message]

                    logger.info(
                        "Dynamic context loaded",
                        extra={
                            "contexts_loaded": len(loaded_contexts),
                            "total_tokens": sum(c.token_count for c in loaded_contexts),
                        },
                    )

            except Exception as e:
                logger.error(f"Dynamic context loading failed: {e}", exc_info=True)
                # Continue without dynamic context

        return state

    def compact_context(state: AgentState) -> AgentState:
        """
        Compact conversation context when approaching token limits.

        Implements Anthropic's "Compaction" technique for long-horizon tasks.
        """
        if not enable_context_compaction:
            return state

        messages = state["messages"]

        if context_manager.needs_compaction(messages):
            try:
                logger.info("Applying context compaction")
                result = asyncio.run(context_manager.compact_conversation(messages))

                state["messages"] = result.compacted_messages
                state["compaction_applied"] = True
                state["original_message_count"] = len(messages)

                logger.info(
                    "Context compacted",
                    extra={
                        "original_messages": len(messages),
                        "compacted_messages": len(result.compacted_messages),
                        "compression_ratio": result.compression_ratio,
                    },
                )
            except Exception as e:
                logger.error(f"Context compaction failed: {e}", exc_info=True)
                # Continue without compaction on error
                state["compaction_applied"] = False
        else:
            state["compaction_applied"] = False

        return state

    def route_input(state: AgentState) -> AgentState:
        """
        Route based on message type with Pydantic AI for type-safe decisions.

        Also captures original user request for verification later.
        """
        last_message = state["messages"][-1]

        # Capture original user request for verification
        if isinstance(last_message, HumanMessage):
            state["user_request"] = last_message.content

        if isinstance(last_message, HumanMessage):
            # Use Pydantic AI for intelligent routing if available
            if pydantic_agent:
                try:
                    # Run async routing in sync context
                    decision = asyncio.run(
                        pydantic_agent.route_message(
                            last_message.content,
                            context={"user_id": state.get("user_id", "unknown"), "message_count": str(len(state["messages"]))},
                        )
                    )

                    # Update state with type-safe decision
                    state["next_action"] = decision.action
                    state["routing_confidence"] = decision.confidence
                    state["reasoning"] = decision.reasoning

                    logger.info(
                        "Pydantic AI routing decision",
                        extra={"action": decision.action, "confidence": decision.confidence, "reasoning": decision.reasoning},
                    )
                except Exception as e:
                    logger.error(f"Pydantic AI routing failed, using fallback: {e}", exc_info=True)
                    # Fallback to simple routing
                    state = _fallback_routing(state, last_message)
            else:
                # Fallback routing if Pydantic AI not available
                state = _fallback_routing(state, last_message)

        return state

    def use_tools(state: AgentState) -> AgentState:
        """Simulate tool usage (extend with real tools)"""
        # In real implementation, bind tools to model
        # For now, simulate a tool response
        tool_response = AIMessage(content="Tool execution completed. Processing results...")

        return {**state, "messages": [tool_response], "next_action": "respond"}

    def generate_response(state: AgentState) -> AgentState:
        """Generate final response using LLM with Pydantic AI validation"""
        messages = state["messages"]

        # Add refinement context if this is a refinement attempt
        refinement_attempts = state.get("refinement_attempts", 0)
        if refinement_attempts > 0 and state.get("verification_feedback"):
            refinement_prompt = SystemMessage(
                content=f"<refinement_guidance>\n"
                f"Previous response had issues. Please refine based on this feedback:\n"
                f"{state['verification_feedback']}\n"
                f"</refinement_guidance>"
            )
            messages = [refinement_prompt] + messages

        # Use Pydantic AI for structured response if available
        if pydantic_agent:
            try:
                # Generate type-safe response
                typed_response = asyncio.run(
                    pydantic_agent.generate_response(
                        messages,
                        context={
                            "user_id": state.get("user_id", "unknown"),
                            "routing_confidence": str(state.get("routing_confidence", 0.0)),
                            "refinement_attempt": str(refinement_attempts),
                        },
                    )
                )

                # Convert to AIMessage
                response = AIMessage(content=typed_response.content)

                logger.info(
                    "Pydantic AI response generated",
                    extra={
                        "confidence": typed_response.confidence,
                        "requires_clarification": typed_response.requires_clarification,
                        "sources": typed_response.sources,
                        "refinement_attempt": refinement_attempts,
                    },
                )
            except Exception as e:
                logger.error(f"Pydantic AI response generation failed, using fallback: {e}", exc_info=True)
                # Fallback to standard LLM
                response = model.invoke(messages)
        else:
            # Standard LLM response
            response = model.invoke(messages)

        return {**state, "messages": [response], "next_action": "verify" if enable_verification else "end"}

    def verify_response(state: AgentState) -> AgentState:
        """
        Verify response quality using LLM-as-judge pattern.

        Implements Anthropic's "Verify Work" step in the agent loop.
        """
        if not enable_verification:
            state["next_action"] = "end"
            return state

        # Get the response to verify (last message)
        response_message = state["messages"][-1]
        response_text = response_message.content if hasattr(response_message, "content") else str(response_message)

        # Get user request
        user_request = state.get("user_request", "")

        # Get conversation context (excluding the response we're verifying)
        conversation_context = state["messages"][:-1]

        try:
            logger.info("Verifying response quality")
            verification_result = asyncio.run(
                output_verifier.verify_response(
                    response=response_text, user_request=user_request, conversation_context=conversation_context
                )
            )

            state["verification_passed"] = verification_result.passed
            state["verification_score"] = verification_result.overall_score
            state["verification_feedback"] = verification_result.feedback

            # Determine next action
            refinement_attempts = state.get("refinement_attempts", 0)

            if verification_result.passed:
                state["next_action"] = "end"
                logger.info(
                    "Verification passed", extra={"score": verification_result.overall_score, "attempts": refinement_attempts}
                )
            elif refinement_attempts < max_refinement_attempts:
                state["next_action"] = "refine"
                logger.info(
                    "Verification failed, refining response",
                    extra={
                        "score": verification_result.overall_score,
                        "attempt": refinement_attempts + 1,
                        "max_attempts": max_refinement_attempts,
                    },
                )
            else:
                # Max attempts reached, accept response
                state["next_action"] = "end"
                logger.warning(
                    "Max refinement attempts reached, accepting response",
                    extra={"score": verification_result.overall_score, "attempts": refinement_attempts},
                )

        except Exception as e:
            logger.error(f"Verification failed: {e}", exc_info=True)
            # On verification error, accept response (fail-open)
            state["verification_passed"] = True
            state["next_action"] = "end"

        return state

    def refine_response(state: AgentState) -> AgentState:
        """
        Refine response based on verification feedback.

        Implements iterative refinement loop (part of "Repeat" in agentic loop).
        """
        # Increment refinement attempts
        refinement_attempts = state.get("refinement_attempts", 0)
        state["refinement_attempts"] = refinement_attempts + 1

        # Remove the failed response from messages
        # It will be regenerated with refinement guidance
        state["messages"] = state["messages"][:-1]

        # Set next action to respond (will regenerate with feedback)
        state["next_action"] = "respond"

        logger.info(
            "Refining response",
            extra={"attempt": state["refinement_attempts"], "feedback": state.get("verification_feedback", "")[:100]},
        )

        return state

    def should_continue(state: AgentState) -> Literal["use_tools", "respond", "end"]:
        """Conditional edge function for routing"""
        return state["next_action"]

    def should_verify(state: AgentState) -> Literal["verify", "refine", "end"]:
        """Conditional edge function for verification loop"""
        return state["next_action"]

    # Build the graph with full agentic loop
    workflow = StateGraph(AgentState)

    # Add nodes (Load → Gather → Route → Act → Verify → Repeat)
    workflow.add_node("load_context", load_dynamic_context)  # Just-in-Time Context Loading
    workflow.add_node("compact", compact_context)  # Gather Context (Compaction)
    workflow.add_node("router", route_input)  # Route Decision
    workflow.add_node("tools", use_tools)  # Take Action (tools)
    workflow.add_node("respond", generate_response)  # Take Action (response)
    workflow.add_node("verify", verify_response)  # Verify Work
    workflow.add_node("refine", refine_response)  # Repeat (refinement)

    # Add edges for full agentic loop with dynamic context loading
    workflow.add_edge(START, "load_context")  # Start with JIT context loading
    workflow.add_edge("load_context", "compact")  # Then compaction
    workflow.add_edge("compact", "router")  # Then route
    workflow.add_conditional_edges(
        "router",
        should_continue,
        {
            "use_tools": "tools",
            "respond": "respond",
        },
    )
    workflow.add_edge("tools", "respond")
    workflow.add_conditional_edges(
        "verify",
        should_verify,
        {
            "verify": "verify",  # Not used (defensive)
            "refine": "refine",  # Refinement needed
            "end": END,  # Verification passed
        },
    )
    workflow.add_edge("respond", "verify")  # Always verify responses
    workflow.add_edge("refine", "respond")  # Refine loops back to respond

    # Compile with checkpointing (uses factory to get Redis or Memory)
    checkpointer = _create_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


# Create singleton instance
agent_graph = create_agent_graph()
