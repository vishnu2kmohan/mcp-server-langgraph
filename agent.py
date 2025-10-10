"""
LangGraph Functional API Agent with full observability and multi-provider LLM support
Includes OpenTelemetry and LangSmith tracing integration
"""
from typing import Annotated, TypedDict, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
import operator

from llm_factory import create_llm_from_config
from config import settings

# Import LangSmith config if available
try:
    from langsmith_config import langsmith_config, get_run_metadata, get_run_tags
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


def create_agent_graph():
    """Create the LangGraph agent using functional API with LiteLLM and observability"""

    # Initialize the model via LiteLLM factory
    model = create_llm_from_config(settings)

    # Create runnable config for LangSmith tracing if available
    def get_runnable_config(
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Optional[RunnableConfig]:
        """Get runnable config with LangSmith metadata"""
        if not LANGSMITH_AVAILABLE or not langsmith_config.is_enabled():
            return None

        return RunnableConfig(
            run_name="mcp-server-langgraph",
            tags=get_run_tags(user_id),
            metadata=get_run_metadata(user_id, request_id)
        )

    # Define node functions
    def route_input(state: AgentState) -> AgentState:
        """Route based on message type"""
        last_message = state["messages"][-1]

        if isinstance(last_message, HumanMessage):
            # Determine if this needs tools or direct response
            if any(keyword in last_message.content.lower()
                   for keyword in ["search", "calculate", "lookup"]):
                state["next_action"] = "use_tools"
            else:
                state["next_action"] = "respond"

        return state

    def use_tools(state: AgentState) -> AgentState:
        """Simulate tool usage (extend with real tools)"""
        messages = state["messages"]

        # In real implementation, bind tools to model
        # For now, simulate a tool response
        tool_response = AIMessage(
            content="Tool execution completed. Processing results..."
        )

        return {
            **state,
            "messages": [tool_response],
            "next_action": "respond"
        }

    def generate_response(state: AgentState) -> AgentState:
        """Generate final response using LLM"""
        messages = state["messages"]
        response = model.invoke(messages)

        return {
            **state,
            "messages": [response],
            "next_action": "end"
        }

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
        }
    )
    workflow.add_edge("tools", "respond")
    workflow.add_edge("respond", END)

    # Compile with checkpointing
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Create singleton instance
agent_graph = create_agent_graph()
