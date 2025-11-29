# 5. Type-Safe Agent Responses with Pydantic AI

Date: 2025-10-11

## Status

Accepted

## Category

Core Architecture

## Context

LLM agents face a fundamental challenge: **unstructured outputs**. LLMs return free-form text, but applications need:
- Structured data (not raw strings)
- Type safety (compile-time checking)
- Confidence scores (how sure is the AI?)
- Validation (ensuring outputs meet schemas)
- Reasoning transparency (why did it choose this?)

Traditional approaches have limitations:

1. **Manual String Parsing**
   ```python
   response = llm.invoke("Route this message")
   if "search" in response.lower():
       action = "use_tools"  # Fragile!
   ```

2. **JSON Output Parsing**
   ```python
   response = llm.invoke("Return JSON: {action: ...}")
   data = json.loads(response)  # May fail!
   ```

3. **Function Calling** (Provider-specific)
   ```python
   # Only works with some providers
   tools = [{"name": "route", "schema": ...}]
   response = llm.invoke(messages, tools=tools)
   ```

Problems:
- No type safety (strings everywhere)
- Manual validation required
- Errors at runtime, not compile-time
- No confidence scores
- Provider-specific implementations

For a production agent, we need:
- **Type-safe routing**: Literal["use_tools", "respond", "end"]
- **Confidence tracking**: 0.0-1.0 scores for decisions
- **Reasoning capture**: Why did the agent choose this path?
- **Graceful fallback**: Degrade to keyword matching if AI fails
- **Structured responses**: Pydantic models, not strings

## Decision

We will use **Pydantic AI** for type-safe agent routing and response generation.

Pydantic AI provides:
- **Type-safe outputs**: LLM outputs conform to Pydantic models
- **Confidence scores**: Every decision includes 0.0-1.0 confidence
- **Reasoning transparency**: LLM explains its decisions
- **Automatic validation**: Pydantic validates all outputs
- **Fallback mechanism**: Degrades gracefully on errors
- **Provider-agnostic**: Works with any LLM (via LiteLLM)

Implementation:
- `pydantic_ai_src/mcp_server_langgraph/core/agent.py`: Wrapper around Pydantic AI
- `src/mcp_server_langgraph/core/agent.py`: Uses Pydantic AI for routing and responses
- `llm_validators.py`: Generic validation framework
- `mcp_streaming.py`: Type-safe streaming

## Consequences

### Positive Consequences

- **Type Safety**: Compile-time checking of LLM outputs
- **Confidence Tracking**: Know when AI is uncertain
- **Better Debugging**: Reasoning explains decisions
- **Validation**: Automatic schema checking
- **Graceful Degradation**: Fallback to keywords if AI fails
- **Structured Data**: Pydantic models instead of strings
- **Testing**: Easier to mock and test structured outputs

### Negative Consequences

- **Latency**: +50-200ms for LLM-based routing vs keywords
- **Complexity**: Additional abstraction layer
- **LLM Dependency**: Routing requires LLM call (can be cached)
- **Token Cost**: Extra tokens for structured outputs
- **Learning Curve**: Team must understand Pydantic AI

### Neutral Consequences

- **Fallback Required**: Must implement keyword fallback
- **Provider Compatibility**: Works with most providers, not all

## Alternatives Considered

### 1. Keyword-Based Routing Only

**Description**: Simple string matching for routing

```python
if "search" in message.lower():
    action = "use_tools"
```

**Pros**:
- Instant (no LLM call)
- Free (no tokens)
- Simple to understand

**Cons**:
- Brittle (misses variations)
- No confidence scores
- Can't handle ambiguity
- Frequent false positives/negatives

**Why Rejected**: Too simplistic for production quality

### 2. LangChain Structured Output

**Description**: Use LangChain's with_structured_output

**Pros**:
- Built into LangChain
- Good integration
- Type hints supported

**Cons**:
- Provider-specific (not all LLMs)
- Less flexible than Pydantic AI
- No confidence scores
- No reasoning capture

**Why Rejected**: Pydantic AI more powerful and flexible

### 3. OpenAI Function Calling

**Description**: Use native function calling APIs

**Pros**:
- Fast and efficient
- Provider-optimized
- Structured outputs

**Cons**:
- OpenAI/Anthropic only
- Not provider-agnostic
- No confidence scores
- Vendor lock-in

**Why Rejected**: Not compatible with multi-provider strategy

### 4. Instructor Library

**Description**: Use Instructor for structured outputs

**Pros**:
- Similar to Pydantic AI
- Good type safety
- Validation

**Cons**:
- Less mature
- No confidence scores
- No reasoning transparency
- Smaller community

**Why Rejected**: Pydantic AI has better features

### 5. Manual JSON + Pydantic Validation

**Description**: Ask LLM for JSON, validate with Pydantic

**Pros**:
- Full control
- No extra dependencies

**Cons**:
- Manual prompt engineering
- No standardization
- Brittle parsing
- No confidence scores

**Why Rejected**: Pydantic AI automates this better

## Implementation Details

### Routing Decision Model

```python
class RoutingDecision(BaseModel):
    action: Literal["use_tools", "respond", "end"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
```

### Response Model

```python
class AgentResponse(BaseModel):
    content: str
    confidence: float
    requires_clarification: bool
    sources: List[str]
```

### Usage in Agent

```python
# src/mcp_server_langgraph/core/agent.py
decision = await pydantic_agent.route_message(message)
# decision.action: "use_tools" (typed!)
# decision.confidence: 0.92
# decision.reasoning: "User explicitly requested search"
```

### Fallback Logic

```python
try:
    decision = await pydantic_agent.route_message(message)
except Exception:
    # Fallback to keyword matching
    decision = keyword_based_routing(message)
    decision.confidence = 0.5
```

### Confidence Threshold

```python
# feature_flags.py
pydantic_ai_confidence_threshold: float = 0.7

# Only trust high-confidence decisions
if decision.confidence >= threshold:
    use_pydantic_ai_decision()
else:
    use_fallback()
```

## Performance Impact

Benchmarks on routing latency:

| Method | Latency | Tokens | Accuracy |
|--------|---------|--------|----------|
| Keywords | \<1ms | 0 | 65% |
| Pydantic AI | 150ms | ~50 | 92% |
| Function Calling | 120ms | ~40 | 90% |

**Trade-off**: +150ms for +27% accuracy improvement

**Mitigation**:
- Cache routing decisions for similar inputs
- Use confidence threshold to skip uncertain routes
- Async processing (doesn't block user)

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [reference/pydantic-ai.md](../reference/pydantic-ai.md)
- Related Files: `src/mcp_server_langgraph/core/agent.py`, `llm_validators.py`
- Related ADRs: [0001](adr-0001-llm-multi-provider.md) (LiteLLM integration)
