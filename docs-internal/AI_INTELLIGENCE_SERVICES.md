# AI Intelligence Services

**Status**: Active
**Last Updated**: 2025-12-27
**Owner**: Platform Team

## Purpose

This document describes the AI Intelligence Services in the Agent Studio, which provide real-time AI-powered capabilities across eight intelligence categories. The services are unified through the `StudioOrchestrator` architecture and delivered via REST API and WebSocket endpoints.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [AI Intelligence Categories](#ai-intelligence-categories)
4. [Available AI Services](#available-ai-services)
5. [Feature Flags](#feature-flags)
6. [API Integration](#api-integration)
7. [WebSocket Integration](#websocket-integration)
8. [Frontend Integration](#frontend-integration)
9. [Configuration](#configuration)
10. [Cost Tracking](#cost-tracking)
11. [Security & Authorization](#security--authorization)
12. [Observability](#observability)

---

## Overview

The AI Intelligence Services provide **8 categories** of AI-powered capabilities for the Agent Studio:

| Category | Purpose | Task Types |
|----------|---------|------------|
| **UX** | Navigation prediction, contextual help, learning paths | 10 task types |
| **Session** | Session summarization, grouping, similarity | 3 task types |
| **Conversation** | Intent detection, context optimization, goal tracking | 3 task types |
| **Canvas** | Artifact type suggestion, code analysis, diff explanation | 3 task types |
| **Diagram** | Diagram validation, diagram-to-code generation | 2 task types |
| **Trace** | Trace summarization, anomaly detection, cost projection | 4 task types |
| **HITL** | Risk assessment, decision history analysis | 6 task types |
| **Command** | Command interpretation, inline suggestions, AI edit generation | 3 task types |

**Total**: **34 task types** across **8 categories**

---

## Architecture

### StudioOrchestrator - Unified AI Service

The `StudioOrchestrator` is the central orchestration layer for all AI intelligence services.

**Location**: `src/mcp_server_langgraph/agents/studio_orchestrator.py` (1,199 lines)

**Key Features**:

1. **Unified Cost Tracking**: Single cost tracking pool across all AI features
2. **Parallel Execution**: Multiple tasks execute concurrently in a single request
3. **Cross-Category Insights**: Synthesizes patterns across different analysis types
4. **Resilience Patterns**: Circuit breakers, retries, and graceful degradation per category
5. **Feature Flag Control**: Granular rollout with category-level flags
6. **Persona-Based Access**: RBAC integration for permission checks

**Design Pattern**: Inherits from `BaseOrchestrator` to leverage common parallel execution patterns.

```python
class StudioOrchestrator(BaseOrchestrator[StudioTask, StudioResult]):
    """Unified orchestrator for ALL Studio AI capabilities."""

    @property
    def feature_flag_name(self) -> str:
        return "enable_studio_ai"

    async def _execute_task(self, task: StudioTask) -> StudioResult:
        """Route task to appropriate handler based on category."""
        # Routes to: UX, SESSION, CONVERSATION, CANVAS, DIAGRAM,
        #            TRACE, HITL, COMMAND handlers

    def synthesize(self, results: list[StudioResult]) -> dict[str, Any]:
        """Generate cross-category insights."""
```

### Task Model

```python
from enum import Enum
from dataclasses import dataclass

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
    task_type: str  # Specific task within category
    user_id: str
    session_id: str | None = None
    persona: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
```

---

## AI Intelligence Categories

### 1. UX Intelligence

**Purpose**: Adaptive user experience optimization

**Task Types**:
- `persona_analysis` - Detect user persona and behavior patterns
- `disclosure_analysis` - Analyze optimal UI complexity level
- `error_analysis` - Classify errors and suggest recovery actions
- `nudge_recommendation` - Smart nudges based on user behavior
- `onboarding_personalization` - Personalized onboarding flows
- `empty_state_suggestions` - Contextual CTAs for empty states
- `metrics_insights` - HEART metrics insights and predictions
- `nav_prediction` - Predict and reorder navigation items
- `contextual_help` - Context-aware help content
- `learning_path` - Personalized learning recommendations

**Feature Flags**:
- `FF_ENABLE_AI_PERSONA_ANALYSIS`
- `FF_ENABLE_AI_DISCLOSURE`
- `FF_ENABLE_AI_ERROR_RECOVERY`
- `FF_ENABLE_AI_NUDGES`
- `FF_ENABLE_AI_ONBOARDING`
- `FF_ENABLE_AI_EMPTY_STATES`
- `FF_ENABLE_AI_METRICS_INSIGHTS`

### 2. Session Intelligence

**Purpose**: Session management and organization

**Task Types**:
- `session_summarize` - Generate AI summary of a session
- `session_group` - Group sessions by topic/project
- `session_similarity` - Find sessions similar to a given session

**Feature Flag**: `FF_ENABLE_SESSION_INTELLIGENCE`

### 3. Conversation Intelligence

**Purpose**: Real-time conversation understanding

**Task Types**:
- `intent_detect` - Classify user intent from input text
- `context_optimize` - Suggest context trimming when approaching token limit
- `goal_track` - Track session goals across multiple messages

**Feature Flag**: `FF_ENABLE_CONVERSATION_INTELLIGENCE`

### 4. Canvas Intelligence

**Purpose**: Code and artifact analysis

**Task Types**:
- `artifact_suggest_type` - Suggest optimal artifact type for content
- `code_analyze` - Analyze code quality and complexity
- `diff_explain` - Explain changes between versions in natural language

**Feature Flag**: `FF_ENABLE_CANVAS_INTELLIGENCE`

### 5. Diagram Intelligence

**Purpose**: Diagram validation and code generation

**Task Types**:
- `diagram_analyze` - Validate and analyze Mermaid diagrams
- `diagram_to_code` - Generate code from flowchart/sequence diagrams

**Feature Flag**: `FF_ENABLE_DIAGRAM_INTELLIGENCE`

### 6. Trace Intelligence

**Purpose**: Observability and cost insights

**Task Types**:
- `trace_summarize` - Generate one-sentence summary of agent execution
- `trace_anomaly` - Detect bottlenecks and anomalies in execution
- `cost_project` - Estimate real-time session costs
- `token_predict` - Forecast token usage and optimization opportunities

**Feature Flag**: `FF_ENABLE_TRACE_INTELLIGENCE`

### 7. HITL Intelligence

**Purpose**: Human-in-the-loop decision support

**Task Types**:
- `risk_assess` - AI-generated risk score for pending actions
- `decision_history` - Show how user decided similar requests before
- `uncertainty_analysis` - Analyze WHY the agent is uncertain
- `risk_analysis` - Analyze what could go wrong
- `alternatives_analysis` - Generate safer alternatives
- `evidence_extraction` - Extract confidence factors from reasoning trace

**Feature Flags**:
- `FF_ENABLE_AGENT_HITL`
- `FF_ENABLE_AI_EXPLANATIONS`

### 8. Command Intelligence

**Purpose**: Natural language command interpretation and code suggestions

**Task Types**:
- `command_interpret` - AI interprets natural language commands
- `inline_suggest` - Generate inline code suggestions
- `ai_edit_generate` - Generate AI-powered edits

**Feature Flag**: `FF_ENABLE_AI_SUGGESTIONS`

---

## Available AI Services

### AI Suggestions (Inline Completions)

**Purpose**: Real-time AI-powered text completions as users type

**Delivery**: WebSocket (`/api/v1/ws/ai/suggestions`)

**Features**:
- Session context awareness
- Debounced input handling
- Confidence scoring
- User acceptance/rejection tracking

**Message Flow**:

```typescript
// Client → Server
{
  "type": "suggestion_request",
  "payload": {
    "session_id": "uuid",
    "input_text": "Hello, I need help with",
    "cursor_position": 25,
    "context_window": 500
  }
}

// Server → Client
{
  "type": "suggestion_response",
  "payload": {
    "suggestion_id": "uuid",
    "text": "I'd be happy to help! What would you like assistance with?",
    "confidence": 0.85,
    "reasoning": "Based on user's greeting pattern"
  }
}
```

**Frontend Hook**: `useInlineSuggestions()`

**Implementation**:
- **Handler**: `src/mcp_server_langgraph/websocket/handlers/ai_suggestions.py`
- **LLM Integration**: Uses `create_llm_from_config()` for text completion
- **Rate Limiting**: 300 requests/minute per user
- **Authentication**: Required

### AI Title Generation

**Purpose**: Automatically generate descriptive titles for chat sessions

**Delivery**: REST API (planned) or batch processing

**Task Type**: `session_summarize` (Session Intelligence category)

**Features**:
- Analyzes first 3-5 messages of a session
- Generates concise, descriptive title (5-10 words)
- Falls back to timestamp-based titles on failure

**Frontend Hooks**:
- `useAutoSessionTitle()` - Auto-generate title on session start
- `useSessionAutoName()` - Alternative implementation

**Status**: Partially implemented (backend ready, frontend integration in progress)

### AI Workflow Recommendations

**Purpose**: Suggest workflow templates based on user intent and session context

**Delivery**: REST API via StudioOrchestrator

**Related Services**:
- **Workflow Suggestions**: `src/mcp_server_langgraph/studio/ai/suggestions.py`
- **Template Matching**: `src/mcp_server_langgraph/studio/ai/templates.py`

**Features**:
- Analyzes conversation to detect workflow patterns
- Matches against template library
- Suggests "Save as Workflow" at appropriate moments
- Provides template recommendations for new workflows

**Frontend Components**:
- `SaveAsWorkflowButton.tsx` - In-chat workflow capture
- `SuggestionChips.tsx` - Template recommendations

**Task Types**:
- `intent_detect` (Conversation Intelligence) - Detects workflow intent
- `command_interpret` (Command Intelligence) - Interprets workflow commands

### AI Intent Classification

**Purpose**: Classify user intent from input text to route requests appropriately

**Delivery**: REST API via StudioOrchestrator

**Task Type**: `intent_detect` (Conversation Intelligence category)

**Intent Categories**:
- **Question** - User asking a question
- **Task** - User requesting an action
- **Clarification** - User seeking clarification
- **Feedback** - User providing feedback
- **Navigation** - User wants to navigate somewhere
- **Workflow** - User wants to create/run a workflow

**Features**:
- Confidence scoring (0.0-1.0)
- Multi-label classification support
- Session history awareness
- Fallback to rule-based classification

**Frontend Hook**: `useConversationIntelligence()`

**Example**:

```typescript
const { detectIntent } = useConversationIntelligence();

const result = await detectIntent({
  query: "Can you help me build a chatbot?",
  sessionId: currentSessionId,
});

// Result:
{
  intent: "task",
  confidence: 0.92,
  subIntents: ["workflow", "agent_creation"],
  suggestedAction: "show_agent_templates"
}
```

---

## Feature Flags

### Master Flags

| Flag | Default | Environment Variable | Description |
|------|---------|---------------------|-------------|
| `enable_studio_ai` | `false` | `FF_ENABLE_STUDIO_AI` | Master toggle for all StudioOrchestrator features |
| `enable_ai_ux` | `true` | `FF_ENABLE_AI_UX` | Master toggle for all AI UX features |
| `enable_agent_hitl` | `true` | `FF_ENABLE_AGENT_HITL` | Master toggle for HITL intelligence |

### Category Flags (require `enable_studio_ai=true`)

| Flag | Default | Environment Variable | Description |
|------|---------|---------------------|-------------|
| `enable_session_intelligence` | `false` | `FF_ENABLE_SESSION_INTELLIGENCE` | Session category (session_*) |
| `enable_conversation_intelligence` | `false` | `FF_ENABLE_CONVERSATION_INTELLIGENCE` | Conversation category (intent_*, context_*, goal_*) |
| `enable_canvas_intelligence` | `false` | `FF_ENABLE_CANVAS_INTELLIGENCE` | Canvas category (artifact_*, code_*, diff_*) |
| `enable_diagram_intelligence` | `false` | `FF_ENABLE_DIAGRAM_INTELLIGENCE` | Diagram category (diagram_*) |
| `enable_trace_intelligence` | `false` | `FF_ENABLE_TRACE_INTELLIGENCE` | Trace category (trace_*, cost_*, token_*) |

### Service-Specific Flags

| Flag | Default | Environment Variable | Description |
|------|---------|---------------------|-------------|
| `enable_ai_suggestions` | `true` | `FF_ENABLE_AI_SUGGESTIONS` | Inline AI suggestions (UX category) |
| `enable_ai_suggestions_websocket` | `true` | `FF_ENABLE_AI_SUGGESTIONS_WEBSOCKET` | WebSocket endpoint for AI suggestions |
| `enable_ai_explanations` | `false` | `FF_ENABLE_AI_EXPLANATIONS` | AI explanations for HITL dialogs |

### UX Intelligence Flags

| Flag | Default | Environment Variable | Description |
|------|---------|---------------------|-------------|
| `enable_ai_persona_analysis` | `true` | `FF_ENABLE_AI_PERSONA_ANALYSIS` | Persona behavior analysis |
| `enable_ai_disclosure` | `true` | `FF_ENABLE_AI_DISCLOSURE` | Progressive disclosure analysis |
| `enable_ai_error_recovery` | `true` | `FF_ENABLE_AI_ERROR_RECOVERY` | Error classification and recovery |
| `enable_ai_nudges` | `true` | `FF_ENABLE_AI_NUDGES` | Smart nudge recommendations |
| `enable_ai_onboarding` | `true` | `FF_ENABLE_AI_ONBOARDING` | Onboarding personalization |
| `enable_ai_empty_states` | `true` | `FF_ENABLE_AI_EMPTY_STATES` | Empty state suggestions |
| `enable_ai_metrics_insights` | `true` | `FF_ENABLE_AI_METRICS_INSIGHTS` | HEART metrics insights |

### Performance Flags

| Flag | Default | Environment Variable | Description |
|------|---------|---------------------|-------------|
| `enable_ai_ux_redis_cache` | `false` | `FF_ENABLE_AI_UX_REDIS_CACHE` | Redis caching for LLM responses |
| `enable_ai_ux_streaming` | `true` | `FF_ENABLE_AI_UX_STREAMING` | Streaming responses via SSE |
| `enable_ai_ux_parallel_graph` | `true` | `FF_ENABLE_AI_UX_PARALLEL_GRAPH` | Parallel graph execution (LangGraph Send API) |
| `enable_batch_composite_analysis` | `true` | `FF_ENABLE_BATCH_COMPOSITE_ANALYSIS` | Batch composite analysis |

---

## API Integration

### REST API

**Endpoint**: `POST /api/v1/studio/analyze`

**Location**: `src/mcp_server_langgraph/api/v1/studio_ai.py`

**Request Model**:

```typescript
interface StudioAnalyzeRequest {
  user_id: string;
  session_id: string;
  persona?: string;  // For RBAC filtering
  tasks: Array<{
    category: TaskCategory;
    type: string;
    data?: Record<string, any>;
  }>;
  context?: Record<string, any>;
}
```

**Response Model**:

```typescript
interface StudioAnalyzeResponse {
  user_id: string;
  session_id: string;
  analyses: Record<string, any>;  // Results by task type
  cross_insights: string[];       // Cross-category insights
  failed_analyses: string[];      // Failed task types
  total_cost: string;             // Total cost as Decimal string
}
```

**Example Request**:

```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "persona": "alice-builder",
  "tasks": [
    {
      "category": "ux",
      "type": "persona_analysis",
      "data": {}
    },
    {
      "category": "session",
      "type": "session_summarize",
      "data": {}
    },
    {
      "category": "conversation",
      "type": "intent_detect",
      "data": {
        "query": "Can you help me build a chatbot?"
      }
    }
  ]
}
```

**Example Response**:

```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "analyses": {
    "persona_analysis": {
      "detected_persona": "alice-builder",
      "confidence": 0.92,
      "behavior_patterns": ["workflow_creation", "advanced_features"]
    },
    "session_summarize": {
      "summary": "User building a customer support chatbot",
      "key_topics": ["chatbot", "customer_support", "automation"]
    },
    "intent_detect": {
      "intent": "task",
      "confidence": 0.88,
      "subIntents": ["workflow", "agent_creation"]
    }
  },
  "cross_insights": [
    "User persona 'alice-builder' combined with session context for personalized experience",
    "Session history combined with detected intent for context-aware suggestions"
  ],
  "failed_analyses": [],
  "total_cost": "0.0042"
}
```

### WebSocket API

**Endpoint**: `ws://localhost:8000/api/v1/ws/ai/suggestions`

**Handler**: `AISuggestionsHandler` (extends `WebSocketBase`)

**Location**: `src/mcp_server_langgraph/websocket/handlers/ai_suggestions.py`

**Message Types**:

```typescript
// Client → Server
type ClientMessage =
  | { type: "suggestion_request"; payload: SuggestionRequest }
  | { type: "suggestion_accept"; payload: { suggestion_id: string } }
  | { type: "suggestion_reject"; payload: { suggestion_id: string; reason?: string } }
  | { type: "context_update"; payload: { session_id: string; context: string } };

// Server → Client
type ServerMessage =
  | { type: "suggestion_response"; payload: SuggestionResponse }
  | { type: "error"; payload: ErrorResponse };
```

**Features**:
- Authentication required (JWT token)
- Rate limiting: 300 requests/minute
- Session context caching
- Authorization checks via OpenFGA

---

## Frontend Integration

### React Hooks

The frontend provides specialized hooks that compose the base `useStudioAI` hook:

**Base Hook**: `useStudioAI()` (310 lines, 25 tests)

```typescript
const {
  results,
  analyses,
  crossInsights,
  failedAnalyses,
  totalCost,
  isLoading,
  error,
  refetch,
  getResult,
} = useStudioAI({
  userId: 'user-123',
  sessionId: 'session-456',
  persona: 'alice-builder',
  tasks: [
    { category: 'ux', type: 'persona_analysis', data: {} },
    { category: 'session', type: 'session_summarize', data: {} },
  ],
});
```

**Specialized Hooks** (location: `src/studio/frontend/src/hooks/`):

| Hook | Purpose | Tests | File |
|------|---------|-------|------|
| `useSessionIntelligence()` | Session summarize, group, similarity | 11 | `useSessionIntelligence.ts` |
| `useConversationIntelligence()` | Intent detect, context optimize, goal track | 4 | `useConversationIntelligence.ts` |
| `useCanvasIntelligence()` | Artifact suggest, code analyze, diff explain | 10 | `useCanvasIntelligence.ts` |
| `useTraceIntelligence()` | Trace summarize, anomaly, cost project | 10 | `useTraceIntelligence.ts` |
| `useHITLIntelligence()` | Risk assess, decision history | 12 | `useHITLIntelligence.ts` |
| `useUXIntelligence()` | Nav prediction, contextual help, learning path | 9 | `useUXIntelligence.ts` |
| `useInlineSuggestions()` | WebSocket-based inline suggestions | - | `useInlineSuggestions.ts` |

### Redux Toolkit Integration

**RTK Query Endpoint** (`src/studio/frontend/src/api/index.ts`):

```typescript
import { studioApi } from './index';

export const studioAiApi = studioApi.injectEndpoints({
  endpoints: (builder) => ({
    studioAnalyze: builder.mutation<
      StudioAnalyzeResponse,
      StudioAnalyzeRequest
    >({
      query: (request) => ({
        url: '/studio/analyze',
        method: 'POST',
        body: request,
      }),
      // Automatic cache invalidation
      invalidatesTags: (result) => [
        { type: 'Session', id: result?.session_id },
      ],
    }),
  }),
});

export const { useStudioAnalyzeMutation } = studioAiApi;
```

### E2E Test Coverage

**Test Files** (location: `src/studio/frontend/e2e/`):

| File | Purpose | Lines |
|------|---------|-------|
| `conversation-intelligence.spec.ts` | Intent detection, context optimization | 487 |
| `session-intelligence.spec.ts` | Session summarization, grouping | 412 |
| `canvas-intelligence.spec.ts` | Artifact suggestions, code analysis | 531 |
| `trace-intelligence.spec.ts` | Trace analysis, cost projection | 389 |
| `diagram-intelligence.spec.ts` | Diagram validation, code generation | 298 |
| `command-intelligence.spec.ts` | Command interpretation, inline suggestions | 624 |
| `ai-suggestions.spec.ts` | WebSocket-based inline suggestions | 1,008 |

**Total E2E Coverage**: 3,749 lines across 7 files

---

## Configuration

### Environment Variables

**AI Service Configuration**:

```bash
# Master flags
FF_ENABLE_STUDIO_AI=false                     # Master toggle (gradual rollout)
FF_ENABLE_AI_UX=true                          # UX intelligence
FF_ENABLE_AGENT_HITL=true                     # HITL intelligence

# Category flags (require enable_studio_ai=true)
FF_ENABLE_SESSION_INTELLIGENCE=false          # Session intelligence
FF_ENABLE_CONVERSATION_INTELLIGENCE=false     # Conversation intelligence
FF_ENABLE_CANVAS_INTELLIGENCE=false           # Canvas intelligence
FF_ENABLE_DIAGRAM_INTELLIGENCE=false          # Diagram intelligence
FF_ENABLE_TRACE_INTELLIGENCE=false            # Trace intelligence

# Service-specific flags
FF_ENABLE_AI_SUGGESTIONS=true                 # Inline suggestions
FF_ENABLE_AI_SUGGESTIONS_WEBSOCKET=true       # WebSocket endpoint
FF_ENABLE_AI_EXPLANATIONS=false               # HITL explanations

# Performance flags
FF_ENABLE_AI_UX_REDIS_CACHE=false            # Redis caching
FF_ENABLE_AI_UX_STREAMING=true               # SSE streaming
FF_ENABLE_AI_UX_PARALLEL_GRAPH=true          # Parallel execution
```

**LLM Configuration**:

```bash
# LLM provider settings (inherited from core config)
LLM_PROVIDER=anthropic                        # anthropic, openai, google, azure
LLM_MODEL=claude-3-5-sonnet-20241022         # Model identifier
LLM_TEMPERATURE=0.7                           # Temperature for suggestions
LLM_MAX_TOKENS=150                            # Max tokens for suggestions
LLM_TIMEOUT_SECONDS=60                        # Request timeout
```

**WebSocket Configuration**:

```bash
# WebSocket settings
WS_RATE_LIMIT_PER_MINUTE=300                 # Rate limit for AI suggestions
WS_MESSAGE_TIMEOUT=30                         # Message processing timeout
WS_REQUIRE_AUTH=true                          # Require authentication
```

### Feature Flag Access (Python)

```python
from mcp_server_langgraph.core.feature_flags import feature_flags

# Check master flag
if feature_flags.enable_studio_ai:
    # Check category flags
    if feature_flags.enable_session_intelligence:
        # Execute session intelligence task
        pass

# Check service-specific flags
if feature_flags.enable_ai_suggestions:
    if feature_flags.enable_ai_suggestions_websocket:
        # Enable WebSocket endpoint
        pass
```

### Feature Flag Access (TypeScript)

```typescript
import { useFeatureFlags } from '@/contexts/FeatureFlagContext';

function MyComponent() {
  const { flags, isEnabled } = useFeatureFlags();

  // Check master flag
  if (isEnabled('studio_ai')) {
    // Check category flags
    if (isEnabled('session_intelligence')) {
      // Render session intelligence UI
    }
  }

  // Check service-specific flags
  if (isEnabled('ai_suggestions')) {
    if (isEnabled('ai_suggestions_websocket')) {
      // Connect to WebSocket
    }
  }
}
```

---

## Cost Tracking

### Unified Cost Tracking

The `StudioOrchestrator` maintains a single cost tracking pool for all AI features.

**Implementation**: Uses `CostTracker` from `mcp_server_langgraph/agents/cost_tracker.py`

**Features**:
- Per-session cost tracking
- Per-category cost allocation
- Budget enforcement
- Cost projection

**Example**:

```python
orchestrator = StudioOrchestrator(
    cost_tracker=CostTracker(
        session_id="session-456",
        budget_limit=Decimal("1.00"),  # $1.00 budget
    )
)

result = await orchestrator.analyze(...)

# Check total cost
total_cost = result.get("total_cost")  # Decimal as string
```

### Cost Projection

**Task Type**: `cost_project` (Trace Intelligence)

**Purpose**: Estimate real-time session costs based on usage patterns

**Example**:

```typescript
const { projectCost } = useTraceIntelligence();

const projection = await projectCost({
  sessionId: currentSessionId,
});

// Result:
{
  current_cost: "0.42",
  projected_cost: "1.20",
  remaining_budget: "0.58",
  estimated_messages_remaining: 45,
  cost_per_message_avg: "0.0093"
}
```

---

## Security & Authorization

### Authentication

All AI services require authentication:

- **REST API**: JWT token in `Authorization` header
- **WebSocket**: JWT token in query parameter or header

### Authorization (OpenFGA)

Persona-based access control using OpenFGA:

| Feature | admin | alice-builder | alice-analyst | bob | auditor |
|---------|-------|---------------|---------------|-----|---------|
| Session Intelligence | Yes | Yes | Yes | Yes | No |
| Conversation Intelligence | Yes | Yes | Yes | Yes | No |
| Canvas Intelligence | Yes | Yes | No | No | No |
| Diagram Intelligence | Yes | Yes | No | No | No |
| Trace Intelligence | Yes | No | Yes | No | No |
| HITL Intelligence | Yes | No | No | No | Yes |
| UX Intelligence | Yes | Yes | Yes | Yes | Yes |
| Command Intelligence | Yes | Yes | No | No | No |

**Implementation**:

```python
# Backend (automatic via StudioOrchestrator)
task = StudioTask(
    category=TaskCategory.CANVAS,
    task_type="code_analyze",
    user_id="user-123",
    persona="bob",  # Will fail authorization
)

# OpenFGA check: user:bob has relation "user" on ai:canvas?
# Result: False → Returns 403 Forbidden
```

```typescript
// Frontend (automatic via hooks)
const { analyzeCode, isAuthorized } = useCanvasIntelligence();

if (!isAuthorized) {
  // Show permission denied message
  return <PermissionDenied />;
}
```

### Rate Limiting

**REST API**: 60 requests/minute per user (configurable via `FF_RATE_LIMIT_REQUESTS_PER_MINUTE`)

**WebSocket**: 300 messages/minute per connection (configurable via WebSocket config)

---

## Observability

### Metrics

**Prometheus Metrics** (exported by StudioOrchestrator):

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

### Grafana Dashboard

**Dashboard**: `monitoring/grafana/dashboards/AI/studio-ai-intelligence.json`

**Panels**:
- Request rate by category
- Error rate by task type
- Cost by category
- P95 latency by task type
- Cross-insights generation rate
- Circuit breaker states

### Alerting

**Alert Rules**: `deployments/monitoring/alerting-rules/studio-ai-cost-alerts.yaml`

**Alerts**:
- `StudioAICostBudgetExceeded` - Session cost exceeds budget
- `StudioAIHighErrorRate` - Error rate > 5% for 5 minutes
- `StudioAICircuitBreakerOpen` - Circuit breaker open for category
- `StudioAIHighLatency` - P95 latency > 5s for task type

### OpenTelemetry Tracing

All AI service calls are traced using OpenTelemetry:

**Trace Structure**:
```
studio.ai.analyze [SPAN]
  ├─ ux.persona_analysis [SPAN]
  ├─ session.session_summarize [SPAN]
  ├─ conversation.intent_detect [SPAN]
  └─ synthesize.cross_insights [SPAN]
```

**Attributes**:
- `user.id`
- `session.id`
- `persona`
- `task.category`
- `task.type`
- `cost.dollars`
- `confidence.score`

---

## Related Documentation

### Architecture Decision Records (ADRs)

- **ADR-0084**: [StudioOrchestrator Unified AI Pattern](../adr/adr-0084-studio-orchestrator-unified-ai.md)
- **ADR-0078**: [Multi-Agent Orchestrator Patterns](../adr/adr-0078-multi-agent-orchestrator-patterns.md)
- **ADR-0083**: [Confidence-Based HITL System](../adr/adr-0083-confidence-based-hitl.md)
- **ADR-0074**: [AI Suggestions Streaming & Cost Tracking](../adr/adr-0074-ai-suggestions-streaming-cost-tracking.md)

### Implementation Files

**Backend**:
- `src/mcp_server_langgraph/agents/studio_orchestrator.py` (1,199 lines)
- `src/mcp_server_langgraph/api/v1/studio_ai.py` (222 lines)
- `src/mcp_server_langgraph/websocket/handlers/ai_suggestions.py` (400 lines)
- `tests/unit/agents/test_studio_orchestrator.py`
- `tests/unit/api/v1/test_studio_ai.py`
- `tests/integration/test_studio_orchestrator_api.py`

**Frontend**:
- `src/hooks/useStudioAI.ts` (310 lines, 25 tests)
- `src/hooks/useSessionIntelligence.ts` (11 tests)
- `src/hooks/useConversationIntelligence.ts` (4 tests)
- `src/hooks/useCanvasIntelligence.ts` (10 tests)
- `src/hooks/useTraceIntelligence.ts` (10 tests)
- `src/hooks/useHITLIntelligence.ts` (12 tests)
- `src/hooks/useUXIntelligence.ts` (9 tests)
- `src/hooks/useInlineSuggestions.ts`
- `src/mocks/handlers/studioHandlers.ts` (492 lines)

### User Documentation

- [Studio Feature Flags Guide](../docs/guides/studio-feature-flags.mdx)
- [Studio Architecture Overview](./STUDIO_ARCHITECTURE.md)
- [Feature Flag Catalog](./FEATURE_FLAG_CATALOG.md)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-27 | 1.0.0 | Initial documentation |

---

**Questions or Issues?** Contact the Platform Team or file an issue in the repository.
