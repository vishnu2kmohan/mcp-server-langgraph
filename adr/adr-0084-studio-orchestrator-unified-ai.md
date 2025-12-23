# 84. StudioOrchestrator - Unified AI Intelligence Pattern

Date: 2025-12-22

## Status

Accepted

## Category

Architecture & AI Intelligence Systems

## Context

The HybridShell frontend requires AI-powered intelligence capabilities across 8 categories:

1. **UX Intelligence**: Navigation prediction, contextual help, learning paths
2. **Session Intelligence**: Session summarization, grouping, similarity search
3. **Conversation Intelligence**: Intent detection, context optimization, goal tracking
4. **Canvas Intelligence**: Artifact type suggestion, code analysis, diff explanation
5. **Diagram Intelligence**: Diagram validation, diagram-to-code generation
6. **Trace Intelligence**: Trace summarization, anomaly detection, cost projection
7. **HITL Intelligence**: Risk assessment, decision history analysis
8. **Command Intelligence**: Command interpretation, inline suggestions, AI edit generation

**Problems with Prior Approach**:

1. **Fragmented Endpoints**: Multiple separate API endpoints for different AI features
2. **Inconsistent Patterns**: UXOrchestrator, AlertOrchestrator, and direct API calls used different patterns
3. **No Cross-Insights**: Unable to synthesize insights across different analysis types
4. **Cost Fragmentation**: Difficult to track and control AI costs across features
5. **Duplicate Code**: Each feature reimplemented parallel execution, error handling, and caching

**Goals**:

- Single unified API endpoint for all AI intelligence features
- Parallel execution of multiple analysis tasks in one request
- Cross-category insight synthesis
- Unified cost tracking and budget enforcement
- Consistent feature flag control
- Persona-based access control

## Decision

Implement a **StudioOrchestrator** that consolidates all AI intelligence capabilities into a single orchestration layer:

### 1. Unified StudioOrchestrator

**Location**: `src/mcp_server_langgraph/agents/studio_orchestrator.py`

**Design**:
```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Literal

class TaskCategory(str, Enum):
    UX = "ux"
    SESSION = "session"
    CONVERSATION = "conversation"
    CANVAS = "canvas"
    DIAGRAM = "diagram"
    TRACE = "trace"
    HITL = "hitl"
    COMMAND = "command"

@dataclass
class StudioTask(BaseTask):
    category: TaskCategory
    task_type: Literal[
        # UX Intelligence
        "persona_analysis", "disclosure_analysis", "error_analysis",
        "nudge_recommendation", "nav_prediction", "contextual_help", "learning_path",
        # Session Intelligence
        "session_summarize", "session_group", "session_similarity",
        # Conversation Intelligence
        "intent_detect", "context_optimize", "goal_track",
        # Canvas Intelligence
        "artifact_suggest_type", "code_analyze", "diff_explain",
        # Diagram Intelligence
        "diagram_analyze", "diagram_to_code",
        # Trace Intelligence
        "trace_summarize", "trace_anomaly", "cost_project", "token_predict",
        # HITL Intelligence
        "risk_assess", "decision_history",
        # Command Intelligence
        "command_interpret", "inline_suggest", "ai_edit_generate",
    ]
    user_id: str
    session_id: str | None = None
    persona: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

class StudioOrchestrator(BaseOrchestrator[StudioTask, StudioResult]):
    """Unified orchestrator for ALL HybridShell AI intelligence features."""

    @property
    def feature_flag_name(self) -> str:
        return "enable_studio_ai"

    async def _execute_task(self, task: StudioTask) -> StudioResult:
        """Route task to appropriate handler based on category."""
        handler = self._handlers.get(task.category)
        return await handler(task)

    def synthesize(self, results: list[StudioResult]) -> dict[str, Any]:
        """Generate cross-category insights."""
        return {
            "analyses": {r.task_type: r.data for r in results if r.success},
            "cross_insights": self._generate_cross_insights(results),
            "failed_analyses": [r.task_type for r in results if not r.success],
            "total_cost": sum(r.cost for r in results),
        }
```

### 2. Single API Endpoint

**Location**: `src/mcp_server_langgraph/api/v1/studio_ai.py`

**Endpoint**: `POST /api/v1/studio/analyze`

```python
@studio_ai_router.post("/analyze")
async def analyze(
    request: StudioAnalyzeRequest,
    orchestrator: StudioOrchestrator = Depends(get_studio_orchestrator),
) -> StudioAnalyzeResponse:
    """Unified analysis endpoint for ALL Studio AI capabilities."""
    tasks = [
        StudioTask(
            category=TaskCategory(t.category),
            task_type=t.type,
            user_id=request.user_id,
            session_id=request.session_id,
            persona=request.persona,
            data=t.data,
        )
        for t in request.tasks
    ]
    result = await orchestrator.analyze(...)
    return StudioAnalyzeResponse(**result)
```

**Request Format**:
```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "persona": "alice-builder",
  "tasks": [
    {"category": "session", "type": "session_summarize", "data": {}},
    {"category": "conversation", "type": "intent_detect", "data": {"query": "..."}},
    {"category": "ux", "type": "nav_prediction", "data": {"currentPage": "chat"}}
  ]
}
```

### 3. Frontend Hook Layer

**Base Hook**: `src/hooks/useStudioAI.ts`

**Specialized Hooks** (composing the base hook):
- `useSessionIntelligence.ts` - Session summarize, group, similarity
- `useConversationIntelligence.ts` - Intent detect, context optimize, goal track
- `useCanvasIntelligence.ts` - Artifact suggest, code analyze, diff explain
- `useTraceIntelligence.ts` - Trace summarize, anomaly, cost project
- `useHITLIntelligence.ts` - Risk assess, decision history
- `useUXIntelligence.ts` - Nav prediction, contextual help, learning path

### 4. Feature Flag Hierarchy

| Flag | Purpose | Controls |
|------|---------|----------|
| `enable_studio_ai` | Master toggle | All StudioOrchestrator features |
| `enable_session_intelligence` | Session category | session_* task types |
| `enable_conversation_intelligence` | Conversation category | intent_*, context_*, goal_* |
| `enable_canvas_intelligence` | Canvas category | artifact_*, code_*, diff_* |
| `enable_diagram_intelligence` | Diagram category | diagram_* |
| `enable_trace_intelligence` | Trace category | trace_*, cost_*, token_* |
| `enable_hitl_ai` | HITL category | risk_*, decision_* |
| `enable_ai_suggestions` | UX category | nav_*, contextual_*, learning_* |

### 5. Persona-Based Access Control

| Feature | admin | alice-builder | alice-analyst | bob | auditor |
|---------|-------|---------------|---------------|-----|---------|
| Session Intelligence | Yes | Yes | Yes | Yes | No |
| Canvas Intelligence | Yes | Yes | No | No | No |
| Trace Intelligence | Yes | No | Yes | No | No |
| HITL Intelligence | Yes | No | No | No | Yes |
| UX Intelligence | Yes | Yes | Yes | Yes | Yes |

## Consequences

### Positive

1. **Single API Surface**: One endpoint replaces 20+ individual endpoints
2. **Parallel Execution**: Multiple tasks execute concurrently in single request
3. **Cross-Insights**: Synthesize patterns across different analysis types
4. **Unified Cost Tracking**: Single CostTracker pool for all AI features
5. **Consistent Patterns**: All hooks follow same composition pattern
6. **Feature Flag Control**: Granular rollout with category-level flags
7. **Type Safety**: Comprehensive TypeScript types for all hooks

### Negative

1. **Migration Effort**: Existing direct API calls need updating
2. **Larger Request Payloads**: Composite requests are more complex
3. **All-or-Nothing Features**: Some category flags control multiple task types

### Risks

1. **Single Point of Failure**: StudioOrchestrator failure affects all AI features
   - Mitigation: Circuit breaker per category, graceful degradation

2. **Cost Explosion**: Easy to request many tasks at once
   - Mitigation: Per-request task limits, session cost caps

## Related ADRs

- ADR-0078: Multi-Agent Orchestrator Patterns (BaseOrchestrator design)
- ADR-0083: Confidence-Based HITL System (risk_assess integration)
- ADR-0074: AI Suggestions Streaming & Cost Tracking (cost projection)
- ADR-0009: Feature Flag System (flag hierarchy)

## Implementation Files

### Backend
- `src/mcp_server_langgraph/agents/studio_orchestrator.py` (1,099 lines)
- `src/mcp_server_langgraph/api/v1/studio_ai.py` (224 lines)
- `tests/unit/agents/test_studio_orchestrator.py`
- `tests/unit/api/v1/test_studio_ai.py`
- `tests/integration/test_studio_orchestrator_api.py`

### Frontend
- `src/hooks/useStudioAI.ts` (310 lines, 25 tests)
- `src/hooks/useSessionIntelligence.ts` (11 tests)
- `src/hooks/useConversationIntelligence.ts` (4 tests)
- `src/hooks/useCanvasIntelligence.ts` (10 tests)
- `src/hooks/useTraceIntelligence.ts` (10 tests)
- `src/hooks/useHITLIntelligence.ts` (12 tests)
- `src/hooks/useUXIntelligence.ts` (9 tests)
- `src/mocks/handlers/studioHandlers.ts` (492 lines)
- `e2e/*-intelligence.spec.ts` (7 files, 3,749 lines)

### Documentation
- `docs-internal/frontend/COMPONENT_INTEGRATION_PLAN.md`
- Plan file: `/home/vishnu/.claude/plans/noble-sparking-boot.md`

## Metrics

```prometheus
# Request metrics
studio_ai_requests_total{category, task_type, persona, success}
studio_ai_request_duration_seconds{category, task_type}

# Cost metrics
studio_ai_cost_dollars{category, task_type, model}

# Synthesis metrics
studio_ai_cross_insights_generated_total
studio_ai_tasks_per_request{count_bucket}

# Error metrics
studio_ai_fallback_total{category, task_type, reason}
studio_ai_circuit_breaker_state{category}
```
