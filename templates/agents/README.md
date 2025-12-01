# Pre-Built Agent Templates

Production-ready agent implementations showcasing MCP Server with LangGraph capabilities.

## Available Templates

### 1. Customer Support Agent
**File:** `customer_support_agent.py`

**Features:**
- Intent classification (FAQ, technical, billing, complaints)
- FAQ knowledge base search
- Sentiment analysis
- Priority escalation
- Human agent handoff
- Response templates

**Use Cases:**
- Customer service automation
- First-line support
- Ticket triage
- FAQ automation

**Example:**
```python
from templates.agents.customer_support_agent import create_support_agent

agent = create_support_agent()
result = agent.invoke({"query": "How do I reset my password?"})
print(result.response)
```

### 2. Research Agent
**File:** `research_agent.py`

**Features:**
- Multi-query generation
- Web search integration
- Source credibility validation
- Information synthesis
- Citation management
- Confidence scoring

**Use Cases:**
- Market research
- Competitive analysis
- Literature reviews
- Fact-checking

**Example:**
```python
from templates.agents.research_agent import create_research_agent

agent = create_research_agent(max_sources=10)
result = agent.invoke({"topic": "LangGraph architecture"})
print(result.summary)
```

### 3. Code Review Agent *(Coming Soon)*
**Features:**
- Code analysis
- Security vulnerability detection
- Best practices validation
- Performance optimization suggestions
- Documentation quality checks

### 4. Data Analyst Agent *(Coming Soon)*
**Features:**
- Data query generation (SQL, pandas)
- Statistical analysis
- Visualization recommendations
- Insight extraction
- Report generation

## Template Structure

Each agent template follows this structure:

```python
# State Definition
class AgentState(BaseModel):
    """Defines the agent's state schema"""
    input: str
    output: str
    metadata: Dict

# Node Functions
def process_step(state: AgentState) -> AgentState:
    """Individual processing steps"""
    return state

# Routing Logic
def route_decision(state: AgentState) -> str:
    """Conditional routing based on state"""
    return "next_node"

# Agent Creation
def create_agent(**config):
    """Factory function to create configured agent"""
    graph = StateGraph(AgentState)
    # ... add nodes and edges
    return graph.compile()
```

## Customization Guide

### 1. Modify State Schema
```python
class CustomState(BaseModel):
    # Add your fields
    custom_field: str = Field(description="My custom field")
```

### 2. Add New Nodes
```python
def custom_processing(state: CustomState) -> CustomState:
    # Your logic here
    state.custom_field = "processed"
    return state

graph.add_node("custom", custom_processing)
```

### 3. Integrate External APIs
```python
import httpx

async def call_external_api(state: AgentState) -> AgentState:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com",
            json={"query": state.query}
        )
        state.api_result = response.json()
    return state
```

### 4. Add LLM Integration
```python
from litellm import acompletion

async def llm_process(state: AgentState) -> AgentState:
    response = await acompletion(
        model="gemini/gemini-2.5-flash",
        messages=[{"role": "user", "content": state.query}]
    )
    state.llm_response = response.choices[0].message.content
    return state
```

## Production Deployment

### 1. Replace Simulated Data

**Before (Template):**
```python
def search_kb(state):
    # Simulated data
    results = [{"answer": "..."}]
    return results
```

**After (Production):**
```python
def search_kb(state):
    # Real database
    results = db.query(
        "SELECT * FROM faq WHERE question LIKE %s",
        (f"%{state.query}%",)
    )
    return results
```

### 2. Add Error Handling
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def robust_api_call(state: AgentState) -> AgentState:
    try:
        # API call
        result = external_api.call(state.query)
        state.result = result
    except Exception as e:
        state.error = str(e)
        # Log error, alert, etc.
    return state
```

### 3. Add Observability
```python
from mcp_server_langgraph.observability import trace_span

def process_with_tracing(state: AgentState) -> AgentState:
    with trace_span("process_step", attributes={"query": state.query}):
        # Your processing logic
        result = process(state.query)
        state.result = result
    return state
```

### 4. Add Caching
```python
from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour TTL

def cached_search(state: AgentState) -> AgentState:
    cache_key = f"search:{state.query}"

    if cache_key in cache:
        state.results = cache[cache_key]
    else:
        state.results = expensive_search(state.query)
        cache[cache_key] = state.results

    return state
```

## Testing

Each template includes example usage at the bottom:

```bash
# Run template tests
python templates/agents/customer_support_agent.py
python templates/agents/research_agent.py
```

### Unit Tests

Create tests in `tests/templates/agents/`:

```python
# tests/templates/agents/test_customer_support.py
from templates.agents.customer_support_agent import create_support_agent

def test_faq_intent():
    agent = create_support_agent()
    result = agent.invoke({"query": "How do I reset password?"})

    assert result.intent == "faq"
    assert "password" in result.response.lower()
```

## Integration with MCP Server

```python
# server_with_template.py
from fastapi import FastAPI
from templates.agents.customer_support_agent import create_support_agent

app = FastAPI()
support_agent = create_support_agent()

@app.post("/support")
async def handle_support(query: str):
    result = support_agent.invoke({"query": query})
    return {
        "response": result.response,
        "intent": result.intent,
        "escalated": result.escalated
    }
```

## Best Practices

1. **State Management**
   - Keep state immutable where possible
   - Use Pydantic for validation
   - Include metadata for debugging

2. **Error Handling**
   - Wrap external calls in try/except
   - Use retry logic for transient failures
   - Provide fallback responses

3. **Observability**
   - Add spans for each processing step
   - Log state transitions
   - Track performance metrics

4. **Security**
   - Sanitize user inputs
   - Validate outputs
   - Rate limit API calls
   - Implement authentication

5. **Performance**
   - Cache expensive operations
   - Use async for I/O operations
   - Parallelize independent tasks
   - Optimize database queries

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [Production Deployment Guide](../../docs/deployment/overview.mdx)
- [Testing Guide](../../docs/advanced/testing.mdx)

## Contributing

Want to add a new template?

1. Follow the template structure above
2. Include comprehensive docstrings
3. Add example usage
4. Create unit tests
5. Update this README

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for details.
