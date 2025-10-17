# Agent Architecture and Usage

This document describes the agent architecture used in MCP Server LangGraph and provides guidance for working with LangGraph agents and Pydantic AI integration.

## Table of Contents

- [Overview](#overview)
- [LangGraph Agent](#langgraph-agent)
- [Pydantic AI Integration](#pydantic-ai-integration)
- [Agent Configuration](#agent-configuration)
- [Tool Integration](#tool-integration)
- [State Management](#state-management)
- [Best Practices](#best-practices)

## Overview

MCP Server LangGraph implements a **functional agent architecture** using LangGraph for stateful conversation management and Pydantic AI for structured outputs and tool calling.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Layer                          │
│  ┌──────────────┐              ┌──────────────┐            │
│  │ stdio        │              │ StreamableHTTP│            │
│  │ Transport    │              │  Transport    │            │
│  └──────────────┘              └──────────────┘            │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
             └────────┬───────────────┘
                      │
         ┌────────────▼────────────┐
         │   Auth Middleware       │
         │  (JWT + OpenFGA)        │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │   LangGraph Agent       │
         │                         │
         │  ┌──────────────────┐   │
         │  │  Agent Graph     │   │
         │  │  (StateGraph)    │   │
         │  └────────┬─────────┘   │
         │           │              │
         │  ┌────────▼─────────┐   │
         │  │ Conditional      │   │
         │  │ Routing          │   │
         │  └────────┬─────────┘   │
         │           │              │
         │  ┌────────▼─────────┐   │
         │  │ Tool Execution   │   │
         │  └────────┬─────────┘   │
         └───────────┼─────────────┘
                     │
        ┌────────────▼──────────────┐
        │   Pydantic AI Integration │
        │                           │
        │  ┌────────────────────┐   │
        │  │ Structured Output  │   │
        │  └────────────────────┘   │
        │                           │
        │  ┌────────────────────┐   │
        │  │ Tool Definition    │   │
        │  └────────────────────┘   │
        │                           │
        │  ┌────────────────────┐   │
        │  │ Model Abstraction  │   │
        │  └────────┬───────────┘   │
        └───────────┼───────────────┘
                    │
       ┌────────────▼────────────┐
       │   LLM Factory           │
       │  (LiteLLM + Fallback)   │
       └─────────────────────────┘
```

## LangGraph Agent

### Core Components

Located in: `src/mcp_server_langgraph/core/agent.py`

#### 1. AgentState

```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Add custom state fields as needed
```

#### 2. Agent Graph

```python
from langgraph.graph import StateGraph, END

def create_agent_graph(llm, tools):
    """Create the LangGraph agent graph"""

    # Define nodes
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Define edges
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
```

#### 3. Conditional Routing

```python
def should_continue(state: AgentState) -> str:
    """Determine if agent should continue or end"""
    messages = state["messages"]
    last_message = messages[-1]

    # If LLM made tool calls, continue to tools node
    if last_message.tool_calls:
        return "continue"
    # Otherwise end
    return "end"
```

### Stateful Conversation

LangGraph maintains conversation state through **checkpointing**:

```python
from langgraph.checkpoint.memory import MemorySaver

# In-memory checkpointing (development)
memory = MemorySaver()
agent_graph = create_agent_graph(llm, tools).compile(
    checkpointer=memory
)

# Persistent checkpointing (production)
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/db"
)
agent_graph = create_agent_graph(llm, tools).compile(
    checkpointer=checkpointer
)
```

### Tool Execution

LangGraph handles tool execution automatically:

```python
from langchain_core.tools import tool

@tool
def search_documents(query: str) -> str:
    """Search internal documents"""
    # Implementation
    return results

tools = [search_documents]
agent = create_agent_graph(llm, tools)
```

## Pydantic AI Integration

### Overview

Located in: `src/mcp_server_langgraph/llm/pydantic_agent.py`

Pydantic AI provides:
- **Structured outputs**: Type-safe responses with Pydantic models
- **Model abstraction**: Unified interface across LLM providers
- **Tool integration**: Function calling with validation
- **Streaming support**: Token-by-token streaming

### Agent Creation

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class SearchResult(BaseModel):
    """Structured search result"""
    title: str
    summary: str
    relevance_score: float

# Create agent with structured output
search_agent = Agent(
    model="openai:gpt-4",
    result_type=SearchResult,
    system_prompt="You are a helpful search assistant"
)

# Run agent
result = await search_agent.run("Search for Python tutorials")
# result is a SearchResult instance
```

### Tool Definition

```python
from pydantic_ai import RunContext

@search_agent.tool
async def search_database(
    ctx: RunContext[dict],
    query: str,
    limit: int = 10
) -> list[dict]:
    """Search the document database"""
    # Access context
    user_id = ctx.deps.get("user_id")

    # Implementation
    results = await db.search(query, limit=limit, user_id=user_id)
    return results
```

### Model Switching

Pydantic AI supports dynamic model switching:

```python
from pydantic_ai.models import KnownModelName

# Switch between models
agent = Agent(
    model="openai:gpt-4",  # Default
)

# Runtime override
result = await agent.run(
    "Your query",
    model="anthropic:claude-3-5-sonnet-20241022"  # Override
)
```

### Structured Output Examples

```python
from pydantic import BaseModel, Field
from typing import List

class CodeReview(BaseModel):
    """Structured code review output"""
    issues: List[str] = Field(description="List of issues found")
    suggestions: List[str] = Field(description="Improvement suggestions")
    security_concerns: List[str] = Field(description="Security issues")
    rating: int = Field(ge=1, le=10, description="Code quality rating")

review_agent = Agent(
    model="anthropic:claude-3-5-sonnet-20241022",
    result_type=CodeReview,
    system_prompt="You are an expert code reviewer"
)

# Get structured review
review = await review_agent.run(code_snippet)
# review.issues, review.suggestions are fully typed
```

## Agent Configuration

### LLM Selection

From: `src/mcp_server_langgraph/llm/factory.py`

```python
from mcp_server_langgraph.llm.factory import create_llm_from_config

# Configuration via settings
llm = create_llm_from_config(
    model_name="anthropic/claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=4096,
    fallback_models=["openai/gpt-4", "google/gemini-pro"]
)
```

### Environment Variables

```bash
# Primary model
export MODEL_NAME="anthropic/claude-3-5-sonnet-20241022"
export ANTHROPIC_API_KEY="sk-ant-..."

# Fallback models
export FALLBACK_MODELS="openai/gpt-4,google/gemini-pro"
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# Model parameters
export TEMPERATURE=0.7
export MAX_TOKENS=4096
```

### Multi-Model Fallback

```python
from mcp_server_langgraph.llm.factory import LLMFactory

factory = LLMFactory(
    primary_model="anthropic/claude-3-5-sonnet-20241022",
    fallback_models=[
        "openai/gpt-4",
        "google/gemini-pro",
        "ollama/llama3.1"
    ]
)

# Automatic fallback on failure
llm = factory.create_with_fallback()
```

## Tool Integration

### MCP Tools

MCP (Model Context Protocol) tools are exposed via the MCP server:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("langgraph-agent")

@server.list_tools()
async def list_tools():
    """List available tools"""
    return [
        Tool(
            name="search_documents",
            description="Search internal documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute tool"""
    if name == "search_documents":
        return await search_documents(**arguments)
```

### Custom Tools

Add custom tools to the agent:

```python
from langchain_core.tools import StructuredTool

def calculate_metrics(data: dict) -> dict:
    """Calculate performance metrics"""
    # Implementation
    return metrics

tools = [
    StructuredTool.from_function(
        func=calculate_metrics,
        name="calculate_metrics",
        description="Calculate performance metrics from data"
    )
]

agent = create_agent_graph(llm, tools)
```

### Tool Authorization

Tools respect OpenFGA permissions:

```python
from mcp_server_langgraph.auth.middleware import AuthMiddleware

auth = AuthMiddleware(openfga_client=openfga)

@server.call_tool()
async def call_tool(name: str, arguments: dict, request):
    """Execute tool with authorization"""
    user_id = request.user_id

    # Check permission
    allowed = await auth.check_authorization(
        user_id=user_id,
        relation="execute",
        object=f"tool:{name}"
    )

    if not allowed:
        raise PermissionError(f"User {user_id} cannot execute {name}")

    # Execute tool
    return await tools[name](**arguments)
```

## State Management

### Conversation Memory

LangGraph manages conversation history:

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
agent = create_agent_graph(llm, tools).compile(
    checkpointer=memory
)

# Each conversation has unique thread_id
config = {"configurable": {"thread_id": "user-123-conv-456"}}

# First message
response = await agent.ainvoke(
    {"messages": [("user", "Hello")]},
    config=config
)

# Continues previous conversation
response = await agent.ainvoke(
    {"messages": [("user", "What did I just say?")]},
    config=config
)
# Agent remembers "Hello"
```

### Persistent State

For production, use PostgreSQL checkpointing:

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    os.getenv("POSTGRES_URL")
)

agent = create_agent_graph(llm, tools).compile(
    checkpointer=checkpointer
)
```

### State Schema

Define custom state fields:

```python
class CustomAgentState(TypedDict):
    """Extended agent state"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str  # Track user
    context: dict  # Additional context
    step_count: int  # Track iterations
```

## Best Practices

### 1. Error Handling

```python
from langchain_core.runnables import RunnableConfig

async def agent_node(state: AgentState):
    """Agent node with error handling"""
    try:
        result = await llm.ainvoke(state["messages"])
        return {"messages": [result]}
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        metrics.agent_errors.add(1, {"error_type": type(e).__name__})

        # Return error message to user
        error_msg = AIMessage(
            content=f"I encountered an error: {str(e)}"
        )
        return {"messages": [error_msg]}
```

### 2. Rate Limiting

```python
from langchain_core.rate_limiters import InMemoryRateLimiter

rate_limiter = InMemoryRateLimiter(
    requests_per_second=10,
    check_every_n_seconds=0.1
)

llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    rate_limiter=rate_limiter
)
```

### 3. Streaming Responses

```python
async def stream_agent_response(query: str, thread_id: str):
    """Stream agent responses token by token"""
    config = {"configurable": {"thread_id": thread_id}}

    async for chunk in agent.astream(
        {"messages": [("user", query)]},
        config=config
    ):
        if "messages" in chunk:
            for message in chunk["messages"]:
                if hasattr(message, "content"):
                    yield message.content
```

### 4. Tool Validation

```python
from pydantic import BaseModel, validator

class SearchInput(BaseModel):
    """Validated search input"""
    query: str
    limit: int = 10

    @validator("query")
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v

    @validator("limit")
    def limit_in_range(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v

@tool(args_schema=SearchInput)
def search(query: str, limit: int = 10) -> str:
    """Search with validation"""
    # Input is validated by Pydantic
    return results
```

### 5. Observability

```python
from mcp_server_langgraph.observability.telemetry import tracer, metrics

async def agent_node(state: AgentState):
    """Agent node with observability"""
    with tracer.start_as_current_span("agent.invoke") as span:
        span.set_attribute("message_count", len(state["messages"]))

        start_time = time.time()
        try:
            result = await llm.ainvoke(state["messages"])

            duration_ms = (time.time() - start_time) * 1000
            metrics.agent_duration.record(duration_ms)
            metrics.agent_invocations.add(1, {"status": "success"})

            return {"messages": [result]}
        except Exception as e:
            metrics.agent_invocations.add(1, {"status": "error"})
            raise
```

### 6. Testing Agents

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_agent_tool_calling():
    """Test agent calls tools correctly"""
    # Mock LLM
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_documents",
                "args": {"query": "Python", "limit": 5},
                "id": "call_123"
            }
        ]
    )

    # Mock tool
    mock_tool = AsyncMock(return_value="Search results...")

    # Create agent
    agent = create_agent_graph(mock_llm, [mock_tool])

    # Test
    result = await agent.ainvoke(
        {"messages": [("user", "Search for Python")]}
    )

    # Verify
    assert mock_tool.called
    assert mock_tool.call_args[1]["query"] == "Python"
```

## Performance Considerations

### 1. Token Usage

Monitor token usage to optimize costs:

```python
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = await agent.ainvoke({"messages": messages})

    logger.info(f"Tokens used: {cb.total_tokens}")
    logger.info(f"Cost: ${cb.total_cost:.4f}")
```

### 2. Caching

Use caching for repeated queries:

```python
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

set_llm_cache(InMemoryCache())

# Repeated queries use cache
result1 = await llm.ainvoke("What is Python?")
result2 = await llm.ainvoke("What is Python?")  # Cached
```

### 3. Parallel Tool Execution

Execute independent tools in parallel:

```python
import asyncio

async def tool_node(state: AgentState):
    """Execute tools in parallel when possible"""
    tool_calls = state["messages"][-1].tool_calls

    # Group independent tools
    tasks = [
        execute_tool(call["name"], call["args"])
        for call in tool_calls
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks)
    return {"messages": results}
```

## Resources

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **Pydantic AI Documentation**: https://ai.pydantic.dev/
- **LiteLLM Documentation**: https://docs.litellm.ai/
- **Mintlify Documentation**: [../docs/mint.json](../docs/mint.json) - Comprehensive documentation with 100% coverage
- **Project Guides**:
  - [Pydantic AI Integration](../docs/architecture/adr-0005-pydantic-ai-integration.mdx)
  - [Multi-LLM Setup Guide](../docs/guides/multi-llm-setup.mdx)
  - [Testing Guide](../docs/advanced/testing.mdx)
  - [Development Setup](../docs/advanced/development-setup.mdx)

---

**Last Updated**: 2025-10-14
**LangGraph Version**: 0.6.10 (upgraded from 0.2.28)
**Pydantic AI Version**: 0.0.15
