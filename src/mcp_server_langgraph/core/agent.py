"""
LangGraph Functional API Agent with full observability and multi-provider LLM support
Includes OpenTelemetry and LangSmith tracing integration
Enhanced with Pydantic AI for type-safe routing and responses
"""

import asyncio
import operator
from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.llm.factory import create_llm_from_config
from mcp_server_langgraph.observability.telemetry import logger

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
    """State for the agent graph"""

    messages: Annotated[list[BaseMessage], operator.add]
    next_action: str
    user_id: str | None
    request_id: str | None
    routing_confidence: float | None  # Confidence from Pydantic AI routing
    reasoning: str | None  # Reasoning from Pydantic AI


def create_agent_graph():
    """Create the LangGraph agent using functional API with LiteLLM and observability"""

    # Initialize the model via LiteLLM factory
    model = create_llm_from_config(settings)

    # Initialize Pydantic AI agent if available
    pydantic_agent = None
    if PYDANTIC_AI_AVAILABLE:
        try:
            pydantic_agent = create_pydantic_agent()
            logger.info("Pydantic AI agent initialized for type-safe routing")
        except Exception as e:
            logger.warning(f"Failed to initialize Pydantic AI agent: {e}", exc_info=True)

    # Create runnable config for LangSmith tracing if available
    def get_runnable_config(user_id: Optional[str] = None, request_id: Optional[str] = None) -> Optional[RunnableConfig]:
        """Get runnable config with LangSmith metadata"""
        if not LANGSMITH_AVAILABLE or not langsmith_config.is_enabled():
            return None

        return RunnableConfig(
            run_name="mcp-server-langgraph", tags=get_run_tags(user_id), metadata=get_run_metadata(user_id, request_id)
        )

    # Define node functions
    def route_input(state: AgentState) -> AgentState:
        """Route based on message type with Pydantic AI for type-safe decisions"""
        last_message = state["messages"][-1]

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

    def use_tools(state: AgentState) -> AgentState:
        """Simulate tool usage (extend with real tools)"""
        # In real implementation, bind tools to model
        # For now, simulate a tool response
        tool_response = AIMessage(content="Tool execution completed. Processing results...")

        return {**state, "messages": [tool_response], "next_action": "respond"}

    def generate_response(state: AgentState) -> AgentState:
        """Generate final response using LLM with Pydantic AI validation"""
        messages = state["messages"]

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
                    },
                )
            except Exception as e:
                logger.error(f"Pydantic AI response generation failed, using fallback: {e}", exc_info=True)
                # Fallback to standard LLM
                response = model.invoke(messages)
        else:
            # Standard LLM response
            response = model.invoke(messages)

        return {**state, "messages": [response], "next_action": "end"}

    def should_continue(state: AgentState) -> Literal["use_tools", "respond", "end"]:
        """Conditional edge function"""
        return state["next_action"]

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", route_input)
    workflow.add_node("tools", use_tools)
    workflow.add_node("respond", generate_response)

    # Add edges
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        should_continue,
        {
            "use_tools": "tools",
            "respond": "respond",
        },
    )
    workflow.add_edge("tools", "respond")
    workflow.add_edge("respond", END)

    # Compile with checkpointing
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Create singleton instance
agent_graph = create_agent_graph()
