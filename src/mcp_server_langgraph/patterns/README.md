
# Multi-Agent Patterns

Production-ready patterns for coordinating multiple AI agents in complex workflows.

## Available Patterns

### 1. Supervisor Pattern
**File:** `supervisor.py`

One coordinating agent delegates tasks to specialized workers.

**Architecture:**
```
User Query → Supervisor (routes) → Worker Agent → Result → Supervisor → Response
```

**When to Use:**
- Task requires different types of expertise
- Clear delegation model needed
- Want centralized coordination
- Sequential or conditional routing

**Example:**
```python
from mcp_server_langgraph.patterns import Supervisor

# Define specialized agents
def research_agent(task):
    return "Research findings..."

def writer_agent(task):
    return "Written content..."

# Create supervisor
supervisor = Supervisor(
    agents={
        "research": research_agent,
        "writer": writer_agent,
        "reviewer": reviewer_agent
    },
    routing_strategy="sequential"  # or "conditional"
)

# Execute
result = supervisor.invoke("Write a research report")
print(result["final_result"])
```

**Routing Strategies:**
- `sequential`: Execute all agents in order (research → write → review)
- `conditional`: Supervisor decides next agent based on state
- `parallel`: Future - execute agents concurrently

**Production Features:**
- State persistence with checkpointer
- Error handling per agent
- Routing decision tracking
- Agent execution history

---

### 2. Swarm Pattern
**File:** `swarm.py`

Multiple agents execute the same task in parallel, results are aggregated.

**Architecture:**
```
Query → [Agent 1, Agent 2, Agent 3] (parallel) → Aggregator → Final Result
```

**When to Use:**
- Want multiple perspectives on same problem
- Need consensus or voting
- Redundancy for critical decisions
- Cross-validation of results

**Example:**
```python
from mcp_server_langgraph.patterns import Swarm

# Define diverse agents
swarm = Swarm(
    agents={
        "optimistic": optimistic_analyzer,
        "pessimistic": risk_analyzer,
        "neutral": balanced_analyzer
    },
    aggregation_strategy="consensus",  # or "voting", "synthesis", "concatenate"
    min_agreement=0.7
)

# Execute in parallel
result = swarm.invoke("Should we invest in this technology?")
print(result["aggregated_result"])
print(f"Consensus: {result['consensus_score']:.0%}")
```

**Aggregation Strategies:**
- `consensus`: Find common ground (shows agreement level)
- `voting`: Majority vote for discrete choices
- `synthesis`: LLM synthesizes all perspectives
- `concatenate`: Present all viewpoints separately

**Production Features:**
- Parallel execution (all agents run simultaneously)
- Consensus scoring
- Error handling (one agent failure doesn't block others)
- Configurable agreement thresholds

---

### 3. Hierarchical Pattern
**File:** `hierarchical.py`

Multi-level delegation with CEO → Managers → Workers structure.

**Architecture:**
```
Project → CEO → [Manager A, Manager B]
               ↓              ↓
        [W1, W2, W3]   [W4, W5, W6]
               ↓              ↓
          Reports → Consolidation → Final Report
```

**When to Use:**
- Complex multi-stage projects
- Organizational-style delegation
- Need manager-level summaries
- Clear hierarchy required

**Example:**
```python
from mcp_server_langgraph.patterns import HierarchicalCoordinator

hierarchy = HierarchicalCoordinator(
    ceo_agent=executive_planner,
    managers={
        "research_mgr": research_manager,
        "dev_mgr": development_manager
    },
    workers={
        "research_mgr": [researcher1, researcher2],
        "dev_mgr": [dev1, dev2, dev3]
    }
)

# Execute hierarchical workflow
result = hierarchy.invoke("Build AI-powered search feature")
print(result["final_report"])
```

**Levels:**
1. **CEO:** Strategic planning and manager assignment
2. **Managers:** Team coordination and task breakdown
3. **Workers:** Actual task execution
4. **Consolidation:** Aggregate all reports

**Production Features:**
- Multi-level state management
- Manager summaries before consolidation
- Execution path tracking
- Scalable to any hierarchy depth

---

## Pattern Comparison

| Pattern | Structure | Execution | Best For |
|---------|-----------|-----------|----------|
| **Supervisor** | Star (1 → many) | Sequential/Conditional | Task routing |
| **Swarm** | Parallel (all same) | Simultaneous | Consensus building |
| **Hierarchical** | Tree (multi-level) | Cascading delegation | Complex projects |

## Integration with MCP Server

### Using with LangGraph Checkpointers

```python
from langgraph.checkpoint.redis import RedisSaver
from mcp_server_langgraph.patterns import Supervisor

# With Redis checkpointer for persistence
checkpointer = RedisSaver(redis_client)

supervisor = Supervisor(
    agents={"research": agent1, "writer": agent2}
)

compiled = supervisor.compile(checkpointer=checkpointer)

# Invoke with thread ID for conversation continuity
result = compiled.invoke(
    SupervisorState(task="Write report"),
    config={"configurable": {"thread_id": "user-123"}}
)
```

### Using with Observability

```python
from mcp_server_langgraph.observability import get_tracer

tracer = get_tracer(__name__)

def traced_agent(task: str) -> str:
    with tracer.start_as_current_span("research_agent"):
        # Your agent logic
        result = perform_research(task)
        return result

supervisor = Supervisor(agents={"research": traced_agent})
```

### Using in FastAPI Endpoints

```python
from fastapi import FastAPI
from mcp_server_langgraph.patterns import Supervisor

app = FastAPI()
supervisor = Supervisor(agents={...})

@app.post("/multi-agent")
async def run_supervisor(task: str):
    result = supervisor.invoke(task)
    return {
        "final_result": result["final_result"],
        "agent_history": result["agent_history"],
        "routing_decision": result["routing_decision"]
    }
```

## Advanced Patterns

### Combining Patterns

You can combine patterns for complex workflows:

```python
# Hierarchical + Swarm: Managers use swarms
def manager_with_swarm(task):
    swarm = Swarm(agents={"agent1": a1, "agent2": a2})
    return swarm.invoke(task)

hierarchy = HierarchicalCoordinator(
    ceo_agent=ceo,
    managers={"research_mgr": manager_with_swarm},
    workers={}  # Workers handled by swarm
)
```

### Custom Patterns

Extend base classes for custom patterns:

```python
from langgraph.graph import StateGraph
from pydantic import BaseModel

class CustomState(BaseModel):
    # Your state fields
    pass

class CustomPattern:
    def __init__(self, **config):
        self.config = config
        self._graph = None

    def build(self) -> StateGraph:
        graph = StateGraph(CustomState)
        # Build your graph
        return graph

    def compile(self, checkpointer=None):
        if self._graph is None:
            self._graph = self.build()
        return self._graph.compile(checkpointer=checkpointer)
```

## Production Best Practices

### 1. Error Handling

```python
def robust_agent(task: str) -> str:
    try:
        result = external_api_call(task)
        return result
    except Exception as e:
        # Fallback or error response
        return f"Agent error: {str(e)}"

supervisor = Supervisor(agents={"agent1": robust_agent})
```

### 2. Timeout Management

```python
from tenacity import retry, stop_after_delay

@retry(stop=stop_after_delay(30))  # 30 second timeout
def agent_with_timeout(task: str) -> str:
    return slow_operation(task)
```

### 3. Result Validation

```python
def validated_agent(task: str) -> str:
    result = agent_logic(task)

    # Validate result
    if not result or len(result) < 10:
        return "Error: Invalid result from agent"

    return result
```

### 4. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_agent(task: str) -> str:
    # Expensive operation
    return expensive_research(task)
```

## Testing

### Unit Tests

```python
# tests/patterns/test_supervisor.py
from mcp_server_langgraph.patterns import Supervisor

def test_supervisor_routing():
    def agent1(task):
        return "result1"

    supervisor = Supervisor(agents={"agent1": agent1})
    result = supervisor.invoke("test task")

    assert result["final_result"] != ""
    assert "agent1" in result["agent_history"]
```

### Integration Tests

```python
# tests/patterns/test_supervisor_integration.py
import pytest
from mcp_server_langgraph.patterns import Supervisor

@pytest.mark.integration
async def test_supervisor_with_llm():
    # Test with actual LLM integration
    supervisor = Supervisor(
        agents={"research": real_research_agent}
    )

    result = supervisor.invoke("Research AI trends")

    assert result["final_result"] != ""
    assert len(result["agent_results"]) > 0
```

## Performance Considerations

### Parallel Execution

For Swarm pattern, agents run in parallel automatically:

```python
# All 3 agents execute simultaneously
swarm = Swarm(agents={
    "agent1": slow_agent,  # Takes 5s
    "agent2": slow_agent,  # Takes 5s
    "agent3": slow_agent,  # Takes 5s
})

# Total time: ~5s (not 15s!) due to parallel execution
```

### Resource Management

```python
# Limit concurrent workers in Hierarchical
hierarchy = HierarchicalCoordinator(
    ceo_agent=ceo,
    managers={"mgr1": mgr},
    workers={"mgr1": [w1, w2, w3]},  # 3 workers max
)
```

## Migration from Other Frameworks

### From CrewAI

**CrewAI:**
```python
from crewai import Agent, Crew

agent1 = Agent(role="Researcher", ...)
agent2 = Agent(role="Writer", ...)

crew = Crew(agents=[agent1, agent2], process="sequential")
result = crew.kickoff()
```

**MCP Server with LangGraph:**
```python
from mcp_server_langgraph.patterns import Supervisor

supervisor = Supervisor(
    agents={"researcher": agent1_func, "writer": agent2_func},
    routing_strategy="sequential"
)

result = supervisor.invoke("task")
```

### From LangGraph

**Raw LangGraph:**
```python
graph = StateGraph(State)
graph.add_node("agent1", func1)
graph.add_node("agent2", func2)
graph.add_edge("agent1", "agent2")
```

**With Patterns:**
```python
# Same result, cleaner API
supervisor = Supervisor(
    agents={"agent1": func1, "agent2": func2},
    routing_strategy="sequential"
)
```

## Examples

See `examples/multi_agent_demo.py` for complete examples (coming soon).

## Resources

- [LangGraph Multi-Agent Docs](https://langchain-ai.github.io/langgraph/how-tos/multi-agent/)
- [CrewAI Comparison](../../../docs/comparisons/vs-crewai.mdx)
- [Production Deployment](../../../docs/deployment/overview.mdx)

## Contributing

To add a new pattern:
1. Create `src/mcp_server_langgraph/patterns/your_pattern.py`
2. Define state with Pydantic model
3. Implement build() method
4. Add tests in `tests/patterns/`
5. Update `__init__.py` to export
6. Add to this README

See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for details.
