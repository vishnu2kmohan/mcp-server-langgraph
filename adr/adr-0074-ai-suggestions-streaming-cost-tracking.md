# ADR-0074: AI Suggestions with Streaming and Cost Tracking

## Status

Accepted

## Date

2025-12-19

## Context

The Studio frontend requires intelligent workflow suggestions to help users discover relevant actions, improve productivity, and provide a more interactive experience. Key requirements include:

1. **Low latency**: Users expect immediate feedback when requesting suggestions
2. **Cost visibility**: Need to track LLM token usage and costs per model
3. **Personalization**: Suggestions should adapt to user context and conversation history
4. **Scalability**: Must handle high concurrent request volume without degrading performance

### Existing State

- No unified suggestions API
- No cost tracking for LLM operations
- No caching strategy for repeated similar requests
- No rate limiting for AI-intensive endpoints

## Decision

Implement a comprehensive AI Suggestions system with the following components:

### 1. Unified Suggestions API

```
POST /api/v1/ai/suggestions
POST /api/v1/ai/suggestions/stream  (SSE streaming)
POST /api/v1/ai/suggestions/chat    (conversation follow-ups)
POST /api/v1/ai/suggestions/track   (interaction tracking)
```

### 2. Streaming Response Pattern

Use Server-Sent Events (SSE) for streaming suggestions to reduce perceived latency:

```python
@ai_router.post("/suggestions/stream")
async def stream_suggestions(request: SuggestionRequest):
    async def generate():
        async for chunk in suggestion_service.stream(request):
            yield f"data: {chunk.model_dump_json()}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 3. Cost Tracking Architecture

```python
# Per-model pricing (USD per 1K tokens)
MODEL_PRICING = {
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
}

# Prometheus metrics
suggestion_cost_total = Counter(
    "suggestion_cost_usd_total",
    "Total cost in USD",
    ["model", "suggestion_type"]
)
suggestion_tokens_total = Counter(
    "suggestion_tokens_total",
    "Total tokens used",
    ["model", "direction"]  # input/output
)
```

### 4. Caching Strategy

- **TTL-based cache**: 5-minute TTL for similar context hashes
- **Cache key**: SHA256 of (user_id, context_summary, suggestion_type)
- **Eviction**: LRU with 10,000 entry limit

### 5. Rate Limiting

Integrate with existing rate limiter middleware:
- 60 requests/minute per user for suggestions
- 10 requests/minute for streaming endpoints
- Graceful degradation with cached responses when rate limited

## Implementation Files

- `src/mcp_server_langgraph/api/v1/ai.py` - API endpoints
- `src/mcp_server_langgraph/studio/ai/suggestions.py` - Core suggestion logic
- `src/mcp_server_langgraph/middleware/rate_limiter.py` - Rate limiting enhancements

## Consequences

### Positive

- **User Experience**: Streaming reduces perceived latency by 60-80%
- **Cost Visibility**: Real-time cost tracking enables budget alerts
- **Performance**: Caching reduces LLM calls by ~40% for repeated queries
- **Observability**: Grafana dashboard provides insights into usage patterns

### Negative

- **Complexity**: Additional infrastructure for caching and streaming
- **Memory**: Cache requires ~100MB for 10K entries
- **Maintenance**: Pricing tables require periodic updates

### Metrics

| Metric | Target |
|--------|--------|
| P95 Latency (streaming first token) | < 500ms |
| Cache hit rate | > 40% |
| Cost per suggestion | < $0.002 avg |
| Rate limit breaches | < 1% of requests |

## References

- ADR-0027: Rate Limiting Strategy
- ADR-0028: Caching Strategy
- ADR-0043: Cost Monitoring Dashboard
- Grafana Dashboard: `ai-suggestions.json`
