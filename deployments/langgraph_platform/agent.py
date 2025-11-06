"""
LangGraph Platform-compatible agent definition
This module defines the graph for deployment to LangGraph Platform
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.llm.factory import create_llm_from_config


class AgentState(TypedDict):
    """State for the agent graph"""

    messages: Annotated[list[BaseMessage], operator.add]
    next_action: str
    user_id: str | None
    request_id: str | None


def create_graph():
    """Create the LangGraph agent for platform deployment"""

    # Initialize the model
    model = create_llm_from_config(settings)

    # Define node functions
    def route_input(state: AgentState) -> AgentState:
        """Route based on message type"""
        last_message = state["messages"][-1]

        if isinstance(last_message, HumanMessage):
            # Determine if this needs tools or direct response
            if any(keyword in last_message.content.lower() for keyword in ["search", "calculate", "lookup"]):
                state["next_action"] = "use_tools"
            else:
                state["next_action"] = "respond"

        return state

    def use_tools(state: AgentState) -> AgentState:
        """Simulate tool usage (extend with real tools)"""
        # In real implementation, bind tools to model
        # For now, simulate a tool response
        tool_response = AIMessage(content="Tool execution completed. Processing results...")

        return {**state, "messages": [tool_response], "next_action": "respond"}

    def generate_response(state: AgentState) -> AgentState:
        """Generate final response using LLM"""
        messages = state["messages"]
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


# Create the graph instance for LangGraph Platform
# The platform will look for a variable named 'graph'
graph = create_graph()
