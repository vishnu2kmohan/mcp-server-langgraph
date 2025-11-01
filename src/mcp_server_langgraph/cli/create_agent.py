"""
Agent creation command for MCP Server CLI.

Generates agent files from templates.
"""

from pathlib import Path
from typing import List, Literal

AgentTemplate = Literal["basic", "research", "customer-support", "code-review", "data-analyst"]


AGENT_TEMPLATES = {
    "basic": """\"\"\"
Basic Agent

A simple agent with customizable tools.
\"\"\"

from langgraph.graph import StateGraph
from typing import TypedDict, List


class {class_name}State(TypedDict):
    \"\"\"State for {agent_name} agent.\"\"\"
    query: str
    response: str
    context: List[str]


def process_query(state: {class_name}State) -> {class_name}State:
    \"\"\"Process the user query.\"\"\"
    # TODO: Implement your agent logic here
    state["response"] = f"Processed: {{state['query']}}"
    return state


# Create agent graph
graph = StateGraph({class_name}State)
graph.add_node("process", process_query)
graph.set_entry_point("process")
graph.set_finish_point("process")

{agent_name}_agent = graph.compile()
""",
    "research": """\"\"\"
Research Agent

Searches and summarizes information from multiple sources.
\"\"\"

from langgraph.graph import StateGraph
from typing import TypedDict, List, Annotated


class ResearchState(TypedDict):
    \"\"\"State for research agent.\"\"\"
    query: str
    search_results: List[str]
    summary: str
    sources: List[str]


def search(state: ResearchState) -> ResearchState:
    \"\"\"Search for information.\"\"\"
    # TODO: Implement search using Tavily, Google, or other search tools
    state["search_results"] = ["Result 1", "Result 2", "Result 3"]
    state["sources"] = ["https://example.com/1", "https://example.com/2"]
    return state


def summarize(state: ResearchState) -> ResearchState:
    \"\"\"Summarize search results.\"\"\"
    # TODO: Use LLM to summarize results
    results = " ".join(state["search_results"])
    state["summary"] = f"Summary of: {{results}}"
    return state


# Create research agent graph
graph = StateGraph(ResearchState)
graph.add_node("search", search)
graph.add_node("summarize", summarize)
graph.add_edge("search", "summarize")
graph.set_entry_point("search")
graph.set_finish_point("summarize")

research_agent = graph.compile()
""",
    "customer-support": """\"\"\"
Customer Support Agent

Handles customer inquiries with FAQ lookup and escalation.
\"\"\"

from langgraph.graph import StateGraph
from typing import TypedDict, Literal


class SupportState(TypedDict):
    \"\"\"State for customer support agent.\"\"\"
    query: str
    intent: Literal["faq", "technical", "billing", "escalate"]
    response: str
    escalated: bool


def classify_intent(state: SupportState) -> SupportState:
    \"\"\"Classify the customer query.\"\"\"
    # TODO: Use LLM to classify intent
    query_lower = state["query"].lower()
    if "price" in query_lower or "cost" in query_lower:
        state["intent"] = "billing"
    elif "error" in query_lower or "bug" in query_lower:
        state["intent"] = "technical"
    else:
        state["intent"] = "faq"
    return state


def handle_faq(state: SupportState) -> SupportState:
    \"\"\"Handle FAQ queries.\"\"\"
    # TODO: Lookup in knowledge base
    state["response"] = "Here's the answer from our FAQ..."
    return state


def handle_technical(state: SupportState) -> SupportState:
    \"\"\"Handle technical support queries.\"\"\"
    # TODO: Check technical documentation or escalate
    state["response"] = "Let me help you troubleshoot..."
    return state


def escalate(state: SupportState) -> SupportState:
    \"\"\"Escalate to human agent.\"\"\"
    state["escalated"] = True
    state["response"] = "I'm connecting you with a specialist..."
    return state


def route(state: SupportState) -> str:
    \"\"\"Route to appropriate handler.\"\"\"
    intent_map = {
        "faq": "handle_faq",
        "technical": "handle_technical",
        "billing": "escalate",
    }
    return intent_map.get(state["intent"], "handle_faq")


# Create support agent graph
graph = StateGraph(SupportState)
graph.add_node("classify", classify_intent)
graph.add_node("handle_faq", handle_faq)
graph.add_node("handle_technical", handle_technical)
graph.add_node("escalate", escalate)

graph.set_entry_point("classify")
graph.add_conditional_edges("classify", route)

support_agent = graph.compile()
""",
}


def generate_agent(name: str, template: AgentTemplate = "basic", tools: List[str] = None) -> None:
    """
    Generate an agent file from a template.

    Args:
        name: Name of the agent (e.g., "my_agent")
        template: Agent template to use
        tools: List of tools to include

    Raises:
        ValueError: If template is invalid
        FileExistsError: If agent file already exists
    """
    if template not in AGENT_TEMPLATES:
        raise ValueError(f"Invalid template: {template}")

    # Create agents directory if it doesn't exist
    agents_dir = Path("src/agents")
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Generate file name
    agent_file = agents_dir / f"{name}_agent.py"

    if agent_file.exists():
        raise FileExistsError(f"Agent file already exists: {agent_file}")

    # Get template content
    template_content = AGENT_TEMPLATES[template]

    # Replace placeholders
    class_name = "".join(word.capitalize() for word in name.split("_"))
    content = template_content.format(
        agent_name=name,
        class_name=class_name,
    )

    # Write file
    agent_file.write_text(content)

    # Create test file
    tests_dir = Path("tests/agents")
    tests_dir.mkdir(parents=True, exist_ok=True)

    test_file = tests_dir / f"test_{name}_agent.py"
    test_content = f'''"""
Tests for {name} agent.
"""

import pytest
from src.agents.{name}_agent import {name}_agent


def test_{name}_agent_basic():
    """Test basic agent functionality."""
    # TODO: Implement tests
    assert {name}_agent is not None


@pytest.mark.asyncio
async def test_{name}_agent_async():
    """Test async agent invocation."""
    # TODO: Implement async tests
    pass
'''

    test_file.write_text(test_content)
