# Pydantic AI Integration Guide

This guide explains how to use Pydantic AI for type-safe agent responses and validation in the MCP server.

## Overview

Pydantic AI provides strongly-typed interactions with LLMs, ensuring outputs match expected schemas for improved reliability and debugging. The integration adds:

- **Type-safe routing** - Structured decision-making with confidence scores
- **Validated responses** - LLM outputs conforming to Pydantic models
- **Structured streaming** - Type-safe streaming chunks with validation
- **Better debugging** - Clear validation errors and metadata

## Architecture

```
User Message → Pydantic AI Router → Type-Safe Decision → Agent Graph
                     ↓
              RouterDecision(
                  action: "use_tools" | "respond" | "clarify",
                  reasoning: str,
                  confidence: float,
                  tool_name: Optional[str]
              )

Agent Graph → Pydantic AI Generator → Validated Response → User
                     ↓
              AgentResponse(
                  content: str,
                  confidence: float,
                  requires_clarification: bool,
                  sources: list[str]
              )
```

## Core Components

### 1. Pydantic AI Agent Wrapper

Located in `pydantic_ai_src/mcp_server_langgraph/core/agent.py`, provides type-safe agent functionality:

```python
from mcp_server_langgraph.llm.pydantic_agent import create_pydantic_agent

# Create agent wrapper
agent = create_pydantic_agent()

# Route message with structured decision
decision = await agent.route_message(
    "Can you search for Python tutorials?",
    context={"user_id": "user:alice"}
)

print(decision.action)       # "use_tools"
print(decision.tool_name)    # "search"
print(decision.confidence)   # 0.92
print(decision.reasoning)    # "User explicitly requested search"

# Generate typed response
response = await agent.generate_response(
    messages=[HumanMessage(content="Hello")],
    context={"user_id": "user:alice"}
)

print(response.content)                    # "Hi there! How can I help?"
print(response.confidence)                  # 0.95
print(response.requires_clarification)      # False
```

### 2. Response Models

#### RouterDecision

```python
from mcp_server_langgraph.llm.pydantic_agent import RouterDecision

decision = RouterDecision(
    action="use_tools",           # Literal["use_tools", "respond", "clarify"]
    reasoning="User needs search results",
    tool_name="search",           # Optional[str]
    confidence=0.9                # float 0.0-1.0
)
```

#### AgentResponse

```python
from mcp_server_langgraph.llm.pydantic_agent import AgentResponse

response = AgentResponse(
    content="Here is your answer...",
    confidence=0.88,
    requires_clarification=False,
    clarification_question=None,  # Optional[str]
    sources=["doc1", "doc2"],     # list[str]
    metadata={"key": "value"}     # dict[str, str]
)
```

### 3. LLM Response Validators

Located in `llm_validators.py`, provides validation utilities:

```python
from mcp_server_langgraph.llm.validators import (
    LLMValidator,
    EntityExtraction,
    IntentClassification,
    SentimentAnalysis
)
from langchain_core.messages import AIMessage

# Validate against custom model
response = AIMessage(content='{"intent": "search", "confidence": 0.9}')
validated = LLMValidator.validate_response(
    response,
    IntentClassification,
    strict=False
)

if validated.is_valid():
    print(validated.data.intent)      # "search"
    print(validated.data.confidence)  # 0.9
else:
    print(validated.get_errors())

# Extract entities
validated = LLMValidator.extract_entities(llm_response)
for entity in validated.data.entities:
    print(f"{entity['type']}: {entity['value']}")

# Classify intent
validated = LLMValidator.classify_intent(llm_response)
print(f"Intent: {validated.data.intent}")
print(f"Confidence: {validated.data.confidence}")

# Analyze sentiment
validated = LLMValidator.analyze_sentiment(llm_response)
print(f"Sentiment: {validated.data.sentiment}")
print(f"Score: {validated.data.score}")
```

### 4. Streaming with Validation

Located in `mcp_streaming.py`:

```python
from mcp_server_langgraph.mcp.streaming import (
    stream_validated_response,
    MCPStreamingValidator,
    StreamChunk
)

# Stream response with validation
async for chunk_json in stream_validated_response(
    content="Long response content...",
    chunk_size=100,
    stream_id="request-123"
):
    # Each chunk is a validated JSON object
    chunk = json.loads(chunk_json)
    print(f"Chunk {chunk['chunk_index']}: {chunk['content']}")

    if chunk['is_final']:
        print("Stream complete!")

# Validate streaming chunks
validator = MCPStreamingValidator()

chunk = await validator.validate_chunk(
    {"content": "Hello", "chunk_index": 0, "is_final": False},
    stream_id="stream-1"
)

# Finalize and validate complete stream
response = await validator.finalize_stream("stream-1")
print(f"Total content: {response.get_full_content()}")
print(f"Chunk count: {response.chunk_count}")
print(f"Complete: {response.is_complete}")
```

## Integration with Agent

The agent in `src/mcp_server_langgraph/core/agent.py` automatically uses Pydantic AI if available:

### Routing

```python
# Pydantic AI routing (automatic)
def route_input(state: AgentState) -> AgentState:
    """Route with Pydantic AI for type-safe decisions"""

    decision = await pydantic_agent.route_message(
        message.content,
        context={"user_id": state["user_id"]}
    )

    # Type-safe state updates
    state["next_action"] = decision.action        # Literal type
    state["routing_confidence"] = decision.confidence
    state["reasoning"] = decision.reasoning

    return state
```

### Response Generation

```python
# Pydantic AI response generation (automatic)
def generate_response(state: AgentState) -> AgentState:
    """Generate with Pydantic AI validation"""

    typed_response = await pydantic_agent.generate_response(
        messages,
        context={"user_id": state["user_id"]}
    )

    # Convert to AIMessage
    response = AIMessage(content=typed_response.content)

    # Log metadata
    logger.info(
        "Response generated",
        extra={
            "confidence": typed_response.confidence,
            "sources": typed_response.sources
        }
    )

    return state
```

## Custom Response Models

Create custom Pydantic models for specific use cases:

```python
from pydantic import BaseModel, Field

class CodeReview(BaseModel):
    """Code review response."""

    summary: str = Field(description="Overall review summary")
    issues: list[dict[str, str]] = Field(description="Found issues")
    suggestions: list[str] = Field(description="Improvement suggestions")
    severity: str = Field(description="Overall severity (low/medium/high)")
    confidence: float = Field(ge=0.0, le=1.0)

# Use with validator
from mcp_server_langgraph.llm.validators import LLMValidator

validated = LLMValidator.validate_response(
    llm_response,
    CodeReview,
    strict=True  # Raise exception on validation failure
)

review = validated.data
print(f"Summary: {review.summary}")
for issue in review.issues:
    print(f"- {issue['type']}: {issue['description']}")
```

## Provider Configuration

Pydantic AI supports multiple LLM providers:

```python
from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

# Google (Gemini)
agent = PydanticAIAgentWrapper(
    model_name="gemini-2.5-flash-002",
    provider="google"
)
# → Uses: "gemini-2.5-flash-002"

# Anthropic
agent = PydanticAIAgentWrapper(
    model_name="claude-3-5-sonnet-20241022",
    provider="anthropic"
)
# → Uses: "anthropic:claude-3-5-sonnet-20241022"

# OpenAI
agent = PydanticAIAgentWrapper(
    model_name="gpt-4o",
    provider="openai"
)
# → Uses: "openai:gpt-4o"
```

## Fallback Behavior

If Pydantic AI is unavailable or fails, the agent uses fallback logic:

```python
# Fallback routing (keyword-based)
if "search" in message.lower():
    action = "use_tools"
else:
    action = "respond"

state["next_action"] = action
state["routing_confidence"] = 0.5  # Low confidence
state["reasoning"] = "Fallback keyword-based routing"
```

## Testing

Run Pydantic AI tests:

```bash
# Unit tests
pytest tests/test_pydantic_ai.py -m unit -v

# Integration tests (requires API keys)
pytest tests/test_pydantic_ai.py -m integration -v

# All Pydantic AI tests
pytest tests/test_pydantic_ai.py -v
```

Example test:

```python
import pytest
from mcp_server_langgraph.llm.pydantic_agent import RouterDecision

@pytest.mark.unit
def test_router_decision_validation():
    """Test RouterDecision validates confidence range."""

    # Valid
    decision = RouterDecision(
        action="respond",
        reasoning="Direct answer",
        confidence=0.9
    )
    assert decision.confidence == 0.9

    # Invalid (confidence > 1.0)
    with pytest.raises(ValidationError):
        RouterDecision(
            action="respond",
            reasoning="Invalid",
            confidence=1.5
        )
```

## Observability

Pydantic AI integration includes full observability:

### Tracing

```python
# Automatic spans
- pydantic_ai.route         # Routing decision
- pydantic_ai.generate_response  # Response generation
- llm.validate_response     # Response validation
- mcp.validate_chunk        # Streaming chunk validation
- mcp.finalize_stream       # Stream finalization
```

### Metrics

```python
# Automatic metrics
metrics.successful_calls.add(1, {"operation": "route_message"})
metrics.failed_calls.add(1, {"operation": "validate_response"})
```

### Logging

```python
# Structured logs
logger.info(
    "Pydantic AI routing decision",
    extra={
        "action": decision.action,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning
    }
)

logger.info(
    "Response validated successfully",
    extra={
        "model": "RouterDecision",
        "content_length": 123
    }
)
```

## Performance Considerations

### Latency

- **Routing**: +50-200ms for LLM-based routing vs keyword matching
- **Validation**: <5ms for Pydantic validation
- **Streaming**: Minimal overhead (<1% per chunk)

### Optimization

```python
# Cache routing decisions for similar messages
# Use simple fallback for low-stakes decisions
# Stream large responses to reduce perceived latency

# Example: Fast path for simple queries
if is_simple_query(message):
    # Use fallback routing
    return _fallback_routing(state, message)
else:
    # Use Pydantic AI for complex routing
    return await pydantic_agent.route_message(message)
```

## Best Practices

### 1. Use Type Hints

```python
from mcp_server_langgraph.llm.pydantic_agent import RouterDecision, AgentResponse

async def process_message(message: str) -> AgentResponse:
    """Always use type hints for Pydantic models."""
    decision: RouterDecision = await agent.route_message(message)
    response: AgentResponse = await agent.generate_response(messages)
    return response
```

### 2. Handle Validation Errors

```python
validated = LLMValidator.validate_response(response, MyModel, strict=False)

if not validated.is_valid():
    logger.warning(
        "Validation failed",
        extra={"errors": validated.get_errors()}
    )
    # Handle gracefully
    return fallback_response()
```

### 3. Add Confidence Thresholds

```python
decision = await agent.route_message(message)

if decision.confidence < 0.7:
    # Low confidence - ask for clarification
    return AgentResponse(
        content="Could you please rephrase?",
        confidence=0.5,
        requires_clarification=True,
        clarification_question="I'm not sure what you mean. Could you provide more details?"
    )
```

### 4. Log Metadata

```python
response = await agent.generate_response(messages)

logger.info(
    "Agent response",
    extra={
        "confidence": response.confidence,
        "sources": response.sources,
        "requires_clarification": response.requires_clarification,
        "content_length": len(response.content)
    }
)
```

## Troubleshooting

### Pydantic AI Not Available

```
WARNING:root:Pydantic AI not available, using fallback routing
```

**Solution**: Install Pydantic AI:
```bash
pip install pydantic-ai>=1.0.0
```

### Validation Failures

```
WARNING:root:Response validation failed
```

**Solution**: Check LLM output format:
```python
# Ensure LLM returns JSON for structured models
# Or handle validation errors gracefully with strict=False
```

### Import Errors

```
ImportError: cannot import name 'create_pydantic_agent'
```

**Solution**: Check Python path and module location:
```bash
python -c "import pydantic_ai_agent; print(pydantic_ai_agent.__file__)"
```

## Examples

See full examples in:
- `src/mcp_server_langgraph/core/agent.py` - Agent integration
- `tests/test_pydantic_ai.py` - Comprehensive tests
- `pydantic_ai_src/mcp_server_langgraph/core/agent.py` - Agent wrapper implementation
- `llm_validators.py` - Validation utilities
- `mcp_streaming.py` - Streaming with validation
