# 3. Dual Observability: OpenTelemetry + LangSmith

Date: 2025-10-11

## Status

Accepted

## Context

Production systems require comprehensive observability to:
- Debug issues quickly
- Monitor performance
- Track user behavior
- Optimize LLM usage
- Meet SLA requirements

For an LLM-powered MCP server, we have two distinct observability needs:

1. **Infrastructure Observability**: Traditional application metrics
   - Request latency, error rates, throughput
   - System resources (CPU, memory, disk)
   - Distributed tracing across services
   - Database query performance

2. **LLM-Specific Observability**: AI/ML-specific insights
   - Prompt quality and effectiveness
   - LLM response quality
   - Token usage and costs
   - Model performance comparison
   - Chain/agent execution flow

No single tool excels at both. Using only one would sacrifice critical visibility in the other domain.

## Decision

We will implement a **dual observability strategy**:

1. **OpenTelemetry** for infrastructure observability
   - Distributed tracing with Jaeger
   - Metrics with Prometheus
   - Structured logging with trace correlation
   - Standard OTLP exporters

2. **LangSmith** for LLM-specific observability
   - Prompt engineering and debugging
   - LLM call tracing and analysis
   - Token usage tracking
   - Model comparison and evaluation
   - Dataset management

Users can enable one or both based on their needs:
- `OBSERVABILITY_BACKEND=opentelemetry` (default)
- `OBSERVABILITY_BACKEND=langsmith`
- `OBSERVABILITY_BACKEND=both` (production recommended)

## Consequences

### Positive Consequences

- **Best of Both Worlds**: Infrastructure + AI observability
- **Complete Visibility**: No blind spots in production
- **Tool Specialization**: Each tool does what it does best
- **Flexibility**: Can use one or both based on needs
- **Industry Standard**: OpenTelemetry is CNCF standard
- **LLM Optimization**: LangSmith enables prompt engineering
- **Cost Tracking**: Detailed token usage visibility

### Negative Consequences

- **Increased Complexity**: Two systems to configure and maintain
- **Higher Infrastructure Cost**: Running both Jaeger and LangSmith
- **Learning Curve**: Team must learn both systems
- **Data Duplication**: Some overlap in traced data
- **Configuration Overhead**: Separate config for each system

### Neutral Consequences

- **Performance**: Minimal overhead (~1-2% with both enabled)
- **Storage**: Increased log/trace storage requirements
- **Vendor Risk**: LangSmith is commercial (OpenTelemetry is free)

## Alternatives Considered

### 1. OpenTelemetry Only

**Description**: Use only OpenTelemetry for all observability

**Pros**:
- Single system to maintain
- Open-source, no vendor lock-in
- Industry standard
- Great for infrastructure

**Cons**:
- Poor LLM-specific insights
- No prompt debugging tools
- Manual token tracking
- No model comparison features

**Why Rejected**: Insufficient for LLM observability needs

### 2. LangSmith Only

**Description**: Use only LangSmith for all observability

**Pros**:
- Excellent LLM tracing
- Great prompt debugging
- Built-in evaluations
- Cost tracking

**Cons**:
- Vendor lock-in (LangChain product)
- Poor infrastructure metrics
- No distributed tracing
- Less flexible than OpenTelemetry

**Why Rejected**: Insufficient for infrastructure observability

### 3. Datadog or New Relic

**Description**: Use commercial APM solution

**Pros**:
- All-in-one solution
- Good infrastructure observability
- Some LLM features

**Cons**:
- Expensive at scale
- Vendor lock-in
- LLM features not as mature
- Less flexible than open standards

**Why Rejected**: High cost, less specialized for LLMs

### 4. Prometheus + Grafana Only

**Description**: Use metrics-focused stack

**Pros**:
- Excellent metrics
- Great visualization
- Open-source

**Cons**:
- No distributed tracing
- No LLM-specific features
- Manual instrumentation

**Why Rejected**: Missing tracing and LLM insights

### 5. Custom Logging Solution

**Description**: Build custom observability

**Pros**:
- Full control
- Exactly what we need

**Cons**:
- Massive development effort
- Reinventing the wheel
- Hard to maintain
- No standard tools

**Why Rejected**: Not feasible to replicate existing tools

## Implementation Details

### OpenTelemetry Stack

```python
# observability.py
- Tracer: Distributed tracing
- Meter: Metrics collection
- Logger: Structured logging with trace context

# Exporters:
- OTLP → Jaeger (traces)
- OTLP → Prometheus (metrics)
- Console (development)
```

### LangSmith Integration

```python
# langsmith_config.py
- Conditional initialization
- Automatic trace context
- Token usage tracking
- Run metadata tagging
```

### Configuration

```python
# config.py
observability_backend: str = "both"  # opentelemetry, langsmith, both
langsmith_api_key: Optional[str] = None
langsmith_tracing: bool = False
```

### Docker Compose Stack

```yaml
services:
  otel-collector:  # Receives traces/metrics
  jaeger:          # Trace visualization
  prometheus:      # Metrics storage
  grafana:         # Unified dashboard
```

### Usage

```python
# Both systems instrumented automatically
with tracer.start_as_current_span("agent.chat") as span:
    response = await llm.ainvoke(messages)
    # → Traced in both Jaeger and LangSmith
```

## Metrics Tracked

### OpenTelemetry Metrics
- `agent.tool.calls` - Tool invocation count
- `agent.calls.successful` - Success rate
- `agent.calls.failed` - Error rate
- `agent.response.duration` - Latency histogram
- `auth.failures` - Auth errors
- `authz.failures` - Authorization denials

### LangSmith Metrics
- Token usage per model
- Cost per request
- Prompt templates used
- Model performance comparison
- Chain execution paths

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LANGSMITH_INTEGRATION.md](../LANGSMITH_INTEGRATION.md)
- Related Files: `observability.py`, `langsmith_config.py`
- Related ADRs: [0001](0001-llm-multi-provider.md) (LLM abstraction)
