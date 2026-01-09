# ADR-0101: Context Graphs for Decision Trace Capture

| Status   | Accepted                                     |
|----------|----------------------------------------------|
| Date     | 2026-01-08                                   |
| Category | Agent Architecture                           |
| Authors  | Claude Code                                  |

## Context

AI agents make numerous decisions during execution - routing choices, tool selections, model selection, and response generation. Currently, these decisions are opaque:

1. **No Audit Trail**: When an agent makes a decision, there's no record of WHY it chose that path.

2. **No Precedent Learning**: Similar queries can lead to different outcomes without consistent rationale.

3. **No Feedback Loop**: User corrections can't be tied back to improve future decisions.

4. **HITL Gaps**: Human-in-the-loop approval lacks context about the decision being approved.

### Industry Context

[Foundation Capital's article "Context Graphs: AI's Trillion-Dollar Opportunity"](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) describes context graphs as:

> "A knowledge graph that captures not just what decisions were made, but WHY they were made, forming searchable precedent for future decisions."

Key insights:
- Decision traces become first-class data assets
- Semantic search enables precedent lookup
- OTEL correlation links traces to observability
- GDPR compliance requires user data export/deletion

## Decision

Implement a Context Graph system with the following components:

### 1. Database Schema

Two tables capture decision traces and their relationships:

```sql
-- Append-only decision traces
CREATE TABLE decision_traces (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(36) UNIQUE NOT NULL,

    -- Context identifiers
    run_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255),
    project_id VARCHAR(255),
    organization_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- Temporal
    timestamp TIMESTAMPTZ NOT NULL,
    sequence_number INTEGER DEFAULT 0,

    -- Decision classification
    decision_type VARCHAR(50) NOT NULL,  -- routing, tool_selection, etc.
    decision_stage VARCHAR(50) NOT NULL,  -- context_gathering, action, etc.

    -- Input context
    query_text TEXT NOT NULL,
    available_options JSONB,

    -- Decision output
    chosen_action VARCHAR(255) NOT NULL,
    selected_items JSONB,
    confidence NUMERIC(4,3) NOT NULL,

    -- Reasoning (WHY)
    rationale TEXT NOT NULL,
    policy_version VARCHAR(100),

    -- Approval (HITL)
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_status VARCHAR(20),

    -- Outcome
    outcome VARCHAR(20),

    -- OTEL correlation
    otel_trace_id VARCHAR(64),
    otel_span_id VARCHAR(32)
);

-- Graph edges connecting decisions to entities
CREATE TABLE decision_edges (
    id BIGSERIAL PRIMARY KEY,
    edge_id VARCHAR(36) UNIQUE NOT NULL,
    trace_id VARCHAR(36) REFERENCES decision_traces(trace_id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(255) NOT NULL,
    relation VARCHAR(50) NOT NULL,
    weight NUMERIC(4,3) DEFAULT 1.0,
    timestamp TIMESTAMPTZ NOT NULL
);
```

### 2. Feature Flags

Eight feature flags control the system:

| Flag | Default | Purpose |
|------|---------|---------|
| `FF_ENABLE_CONTEXT_GRAPH` | false | Master switch for decision trace capture |
| `FF_ENABLE_PRECEDENT_SEARCH` | false | Enable semantic precedent search |
| `FF_CONTEXT_GRAPH_ASYNC_PERSISTENCE` | true | Persist traces asynchronously |
| `FF_CONTEXT_GRAPH_BATCH_SIZE` | 100 | Batch size for async persistence |
| `FF_CONTEXT_GRAPH_RETENTION_DAYS` | 2555 | Retention period (~7 years) |
| `FF_CONTEXT_GRAPH_SAMPLING_RATE` | 1.0 | Sampling rate (1.0 = 100%) |
| `FF_PRECEDENT_SEARCH_MIN_SCORE` | 0.5 | Minimum similarity threshold |
| `FF_PRECEDENT_SEARCH_MAX_RESULTS` | 10 | Maximum precedent results |

### 3. DecisionEmitter Singleton

A singleton emitter handles non-blocking trace persistence:

```python
class DecisionEmitter:
    """Emits decision traces with async queue for non-blocking persistence."""

    def __init__(self, repository):
        self._repository = repository
        self._queue = asyncio.Queue()
        self._sequence_counters = {}

    async def emit(
        self,
        context: DecisionContext,
        decision_type: str,
        decision_stage: str,
        query_text: str,
        chosen_action: str,
        confidence: float,
        rationale: str,
        **kwargs
    ) -> str | None:
        """Emit a decision trace. Returns trace_id or None if sampled out."""
```

Key features:
- **Sampling**: Configurable rate for high-volume production
- **Truncation**: Query (500 chars) and rationale (1000 chars) limits
- **Async Queue**: Background worker for batched persistence
- **OTEL Correlation**: Captures trace_id and span_id from current span
- **Sequence Numbers**: Per-session ordering for causality

### 4. Bootstrap Integration

The context graph initializes in bootstrap phase 7:

```python
@dataclass
class ContextGraphState:
    emitter: DecisionEmitter | None = None
    repository: DecisionTraceRepositoryBase | None = None
    retention_task: asyncio.Task | None = None

    async def cleanup(self) -> None:
        # Cancel retention scheduler, stop emitter
```

### 5. REST API

Three endpoints expose decision traces:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/context-graph/traces/{trace_id}` | Get specific trace |
| `GET /api/v1/context-graph/sessions/{session_id}/traces` | List session traces |
| `POST /api/v1/context-graph/precedents/search` | Semantic precedent search |

### 6. Retention Scheduler

Daily cleanup of expired traces:

```python
async def _retention_loop(repository):
    while True:
        retention_days = feature_flags.context_graph_retention_days
        deleted = await repository.delete_expired(retention_days)
        await asyncio.sleep(86400)  # 24 hours
```

## Consequences

### Positive

1. **Audit Trail**: Complete record of agent decisions with rationale
2. **Precedent Learning**: Similar queries surface past decisions
3. **HITL Context**: Approvers see full decision context
4. **GDPR Compliance**: User data export and deletion supported
5. **Debugging**: Trace decisions through OTEL correlation
6. **Cost Control**: Sampling rate reduces overhead in production

### Negative

1. **Storage Growth**: Decision traces accumulate (mitigated by retention)
2. **Latency Risk**: Mitigated by async persistence
3. **Complexity**: Additional tables and lifecycle management

### Neutral

1. **Feature Flag Gating**: System disabled by default
2. **No Vector Column**: Embeddings stored in Qdrant, not Postgres

## Implementation

Files created/modified:

| File | Purpose |
|------|---------|
| `database/models.py` | DecisionTrace, DecisionEdge models |
| `storage/models.py` | Pydantic enums and schemas |
| `core/feature_flags.py` | 8 new feature flags |
| `repositories/decision_trace.py` | Repository ABC + Postgres |
| `agents/decision_emitter.py` | Singleton emitter |
| `bootstrap/context_graph.py` | Bootstrap integration |
| `schedulers/decision_retention.py` | Retention scheduler |
| `api/v1/context_graph.py` | REST endpoints |

## References

- [Context Graphs: AI's Trillion-Dollar Opportunity](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/)
- [Arize: Context Graphs as Durable Business Assets](https://arize.com/blog/how-context-graphs-turn-agent-traces-into-durable-business-assets/)
- [Graphlit: The Context Layer AI Agents Need](https://www.graphlit.com/blog/context-layer-ai-agents-need)
