# Component Integration Plan: AI Intelligence Hooks

**Purpose**: Guide for integrating AI intelligence hooks into HybridShell UI components
**Status**: Implementation Complete (Sprints 1-6)
**Last Updated**: 2025-12-22

---

## Overview

This document provides a comprehensive guide for integrating the 7 intelligence hook modules into HybridShell UI components. All hooks use the unified `POST /api/v1/studio/analyze` endpoint backed by the `StudioOrchestrator`.

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HybridShell Components                          │
├─────────────────────────────────────────────────────────────────────────┤
│  TopBar │ ActivityBar │ SessionNav │ ConversationPanel │ CanvasWorkspace│
│         │             │            │                   │                │
│  StatusBar │ Diagrams │ Agent Traces │ HITL Dialogs │ Help/Onboarding  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Intelligence Hooks Layer                         │
├─────────────────────────────────────────────────────────────────────────┤
│ useStudioAI        │ useSessionIntelligence    │ useConversationIntel  │
│ useCanvasIntel     │ useTraceIntelligence      │ useHITLIntelligence   │
│ useUXIntelligence  │                           │                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RTK Query (useStudioAnalyzeMutation)                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    POST /api/v1/studio/analyze                          │
│                         StudioOrchestrator                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Intelligence Hook Modules

### 1. useStudioAI (Base Hook)

**File**: `src/hooks/useStudioAI.ts`
**Tests**: 25 tests in `src/hooks/useStudioAI.test.tsx`

The base hook that all specialized hooks compose. Provides direct access to the unified API.

```typescript
import { useStudioAI } from '@/hooks/useStudioAI';

function MyComponent() {
  const { analyze, isLoading, error } = useStudioAI({
    userId: 'user-123',
    sessionId: 'session-456',
  });

  const result = await analyze({
    tasks: [
      { category: 'session', type: 'session_summarize', data: {} },
      { category: 'ux', type: 'nav_prediction', data: { currentPage: 'chat' } },
    ],
  });

  // Result structure:
  // {
  //   analyses: { session_summarize: {...}, nav_prediction: {...} },
  //   cross_insights: ['...'],
  //   failed_analyses: [],
  //   total_cost: '0.002'
  // }
}
```

### 2. useSessionIntelligence

**File**: `src/hooks/useSessionIntelligence.ts`
**Tests**: 11 tests in `src/hooks/useSessionIntelligence.test.tsx`

| Hook | Task Type | Purpose |
|------|-----------|---------|
| `useSessionSummary` | `session_summarize` | One-line summary, key topics, message count |
| `useSessionGroups` | `session_group` | AI-grouped sessions by topic/project |
| `useSessionSimilarity` | `session_similarity` | Find similar sessions |

**Integration Target**: `SessionNav.tsx`

```typescript
// In SessionNav.tsx
import { useSessionSummary, useSessionGroups } from '@/hooks/useSessionIntelligence';

function SessionNav() {
  const { summary, keyTopics, isLoading } = useSessionSummary({
    userId,
    sessionId: currentSessionId,
    enabled: featureFlags.enable_session_intelligence,
  });

  const { groups, totalSessions } = useSessionGroups({
    userId,
    sessions: sessionList,
    enabled: featureFlags.enable_session_intelligence,
  });

  return (
    <nav>
      {/* Show AI summary in session header */}
      {summary && <SessionSummaryBadge summary={summary} topics={keyTopics} />}

      {/* Show AI-grouped sessions */}
      {groups.map(group => (
        <SessionGroup key={group.id} name={group.name} sessions={group.sessions} />
      ))}
    </nav>
  );
}
```

### 3. useConversationIntelligence

**File**: `src/hooks/useConversationIntelligence.ts`
**Tests**: 4 tests in `src/hooks/useConversationIntelligence.test.tsx`

| Hook | Task Type | Purpose |
|------|-----------|---------|
| `useIntentDetection` | `intent_detect` | Detect user intent (question, code request, task) |
| `useContextOptimization` | `context_optimize` | Suggest context trimming |
| `useGoalTracking` | `goal_track` | Track session goals across messages |

**Integration Target**: `ConnectedConversationPanel.tsx`, `ChatInputForm.tsx`

```typescript
// In ChatInputForm.tsx
import { useIntentDetection } from '@/hooks/useConversationIntelligence';

function ChatInputForm({ onSubmit }) {
  const [input, setInput] = useState('');

  const { intent, confidence, suggestedAction } = useIntentDetection({
    userId,
    query: input,
    enabled: featureFlags.enable_conversation_intelligence && input.length > 10,
    debounceMs: 500, // Debounce to avoid excessive API calls
  });

  return (
    <form onSubmit={onSubmit}>
      <textarea value={input} onChange={e => setInput(e.target.value)} />

      {/* Show intent indicator */}
      {intent && (
        <IntentBadge
          intent={intent}  // 'question' | 'code_request' | 'task' | 'clarification'
          confidence={confidence}
        />
      )}
    </form>
  );
}
```

### 4. useCanvasIntelligence

**File**: `src/hooks/useCanvasIntelligence.ts`
**Tests**: 10 tests in `src/hooks/useCanvasIntelligence.test.tsx`

| Hook | Task Type | Purpose |
|------|-----------|---------|
| `useArtifactTypeSuggestion` | `artifact_suggest_type` | Suggest optimal artifact type |
| `useCodeAnalysis` | `code_analyze` | Real-time code quality analysis |
| `useDiffExplanation` | `diff_explain` | Explain changes between versions |
| `useDiagramAnalysis` | `diagram_analyze` | Analyze and validate diagrams |
| `useDiagramToCode` | `diagram_to_code` | Generate code from diagrams |

**Integration Target**: `CanvasWorkspace.tsx`, `CanvasArtifact.tsx`

```typescript
// In CanvasArtifact.tsx
import { useCodeAnalysis, useDiffExplanation } from '@/hooks/useCanvasIntelligence';

function CanvasArtifact({ artifact, previousVersion }) {
  const { issues, suggestions, qualityScore } = useCodeAnalysis({
    userId,
    sessionId,
    code: artifact.content,
    language: artifact.language,
    enabled: artifact.type === 'code' && featureFlags.enable_canvas_intelligence,
  });

  const { explanation, changes } = useDiffExplanation({
    userId,
    sessionId,
    oldContent: previousVersion?.content,
    newContent: artifact.content,
    enabled: previousVersion && featureFlags.enable_canvas_intelligence,
  });

  return (
    <div className="artifact">
      <CodeEditor content={artifact.content} />

      {/* Quality indicator */}
      {qualityScore && <QualityBadge score={qualityScore} issues={issues} />}

      {/* Version diff explanation */}
      {explanation && <DiffExplanation text={explanation} changes={changes} />}
    </div>
  );
}
```

### 5. useTraceIntelligence

**File**: `src/hooks/useTraceIntelligence.ts`
**Tests**: 10 tests in `src/hooks/useTraceIntelligence.test.tsx`

| Hook | Task Type | Purpose |
|------|-----------|---------|
| `useTraceSummary` | `trace_summarize` | One-sentence trace summary |
| `useTraceAnomaly` | `trace_anomaly` | Detect bottlenecks and issues |
| `useCostProjection` | `cost_project` | Real-time session cost estimate |
| `useTokenPrediction` | `token_predict` | Token usage forecast |

**Integration Target**: `AgentExecutionTracePanel.tsx`, `StatusBar.tsx`

```typescript
// In AgentExecutionTracePanel.tsx
import { useTraceSummary, useTraceAnomaly } from '@/hooks/useTraceIntelligence';

function AgentExecutionTracePanel({ traceId }) {
  const { summary, keyActions, totalDurationMs } = useTraceSummary({
    userId,
    sessionId,
    traceId,
    enabled: featureFlags.enable_trace_intelligence,
  });

  const { anomalies, bottlenecks, healthScore } = useTraceAnomaly({
    userId,
    sessionId,
    traceId,
    enabled: featureFlags.enable_trace_intelligence,
  });

  return (
    <div className="trace-panel">
      {/* AI-generated summary */}
      <div className="summary">
        <p>{summary}</p>
        <span className="duration">{totalDurationMs}ms</span>
      </div>

      {/* Health score */}
      <HealthIndicator score={healthScore} />

      {/* Bottleneck warnings */}
      {bottlenecks.map(b => (
        <BottleneckWarning
          key={b.step_name}
          step={b.step_name}
          percentage={b.percentage_of_total}
        />
      ))}
    </div>
  );
}
```

### 6. useHITLIntelligence

**File**: `src/hooks/useHITLIntelligence.ts`
**Tests**: 12 tests in `src/hooks/useHITLIntelligence.test.tsx`

| Hook | Task Type | Purpose |
|------|-----------|---------|
| `useRiskAssessment` | `risk_assess` | AI risk score for pending actions |
| `useDecisionHistory` | `decision_history` | Similar past decisions |

**Integration Target**: `AgentApprovalDialog.tsx`, `BatchApprovalPanel.tsx`

```typescript
// In AgentApprovalDialog.tsx
import { useRiskAssessment, useDecisionHistory } from '@/hooks/useHITLIntelligence';

function AgentApprovalDialog({ request, onApprove, onReject }) {
  const { riskScore, riskLevel, riskFactors, mitigations } = useRiskAssessment({
    userId,
    sessionId,
    agentRequestId: request.id,
    actionType: request.action_type,
    parameters: request.parameters,
    enabled: featureFlags.enable_hitl_ai,
  });

  const { similarDecisions, approvalRate, suggestedAction } = useDecisionHistory({
    userId,
    agentRequestId: request.id,
    enabled: featureFlags.enable_hitl_ai,
  });

  return (
    <Dialog>
      <h2>Agent Action Request</h2>

      {/* Risk indicator */}
      <RiskIndicator
        score={riskScore}
        level={riskLevel}  // 'low' | 'medium' | 'high' | 'critical'
        factors={riskFactors}
      />

      {/* Similar past decisions */}
      {similarDecisions.length > 0 && (
        <div className="similar-decisions">
          <p>{similarDecisions.length} similar decisions found</p>
          <p>Approval rate: {approvalRate}%</p>
          <p>Suggested action: {suggestedAction}</p>
        </div>
      )}

      {/* Mitigations for high-risk actions */}
      {riskLevel !== 'low' && (
        <MitigationsList mitigations={mitigations} />
      )}

      <DialogActions>
        <Button onClick={onReject}>Reject</Button>
        <Button onClick={onApprove} variant={riskLevel === 'high' ? 'warning' : 'primary'}>
          Approve
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

### 7. useUXIntelligence

**File**: `src/hooks/useUXIntelligence.ts`
**Tests**: 9 tests in `src/hooks/useUXIntelligence.test.tsx`

| Hook | Task Type | Purpose |
|------|-----------|---------|
| `useNavPrediction` | `nav_prediction` | Predict and reorder nav items |
| `useContextualHelp` | `contextual_help` | Context-aware help content |
| `useLearningPath` | `learning_path` | Personalized learning recommendations |

**Integration Target**: `ActivityBar.tsx`, `HelpPane.tsx`, `OnboardingWizard.tsx`

```typescript
// In ActivityBar.tsx
import { useNavPrediction } from '@/hooks/useUXIntelligence';

function ActivityBar({ modules }) {
  const { predictedItems, currentContext, confidence } = useNavPrediction({
    userId,
    currentPage: location.pathname,
    recentPages: navigationHistory,
    enabled: featureFlags.enable_ai_suggestions,
  });

  // Reorder modules based on prediction
  const orderedModules = useMemo(() => {
    if (!predictedItems.length) return modules;

    return [...modules].sort((a, b) => {
      const aScore = predictedItems.find(p => p.id === a.id)?.score ?? 0;
      const bScore = predictedItems.find(p => p.id === b.id)?.score ?? 0;
      return bScore - aScore;
    });
  }, [modules, predictedItems]);

  return (
    <nav className="activity-bar">
      {orderedModules.map(module => (
        <NavItem
          key={module.id}
          module={module}
          isPredicted={predictedItems.some(p => p.id === module.id)}
        />
      ))}
    </nav>
  );
}
```

---

## Component-to-Hook Mapping

| Component | Intelligence Hooks | Feature Flags |
|-----------|-------------------|---------------|
| **TopBar** | `useNavPrediction` | `enable_ai_suggestions` |
| **ActivityBar** | `useNavPrediction` | `enable_ai_suggestions` |
| **SessionNav** | `useSessionSummary`, `useSessionGroups`, `useSessionSimilarity` | `enable_session_intelligence` |
| **ConversationPanel** | `useIntentDetection`, `useContextOptimization`, `useGoalTracking` | `enable_conversation_intelligence` |
| **CanvasWorkspace** | `useArtifactTypeSuggestion`, `useCodeAnalysis`, `useDiffExplanation` | `enable_canvas_intelligence` |
| **CanvasArtifact** | `useDiagramAnalysis`, `useDiagramToCode` | `enable_diagram_intelligence` |
| **StatusBar** | `useCostProjection`, `useTokenPrediction` | `enable_trace_intelligence` |
| **AgentTracePanel** | `useTraceSummary`, `useTraceAnomaly` | `enable_trace_intelligence` |
| **AgentApprovalDialog** | `useRiskAssessment`, `useDecisionHistory` | `enable_hitl_ai` |
| **HelpPane** | `useContextualHelp`, `useLearningPath` | `enable_ai_suggestions` |

---

## Feature Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `enable_studio_ai` | Master toggle for all StudioOrchestrator features | `false` |
| `enable_session_intelligence` | Session summarize/group/similarity | `false` |
| `enable_conversation_intelligence` | Intent/context/goal features | `false` |
| `enable_canvas_intelligence` | Artifact/code/diff features | `false` |
| `enable_diagram_intelligence` | Diagram analysis/generation | `false` |
| `enable_trace_intelligence` | Trace summarize/anomaly | `false` |
| `enable_hitl_ai` | HITL risk assessment | `false` |
| `enable_ai_suggestions` | UX intelligence (nav, help, learning) | `false` |

### Feature Flag Usage Pattern

```typescript
import { useFeatureFlags } from '@/contexts/FeatureFlagContext';

function MyComponent() {
  const { flags } = useFeatureFlags();

  const { summary } = useSessionSummary({
    userId,
    sessionId,
    // Only call API if feature is enabled
    enabled: flags.enable_session_intelligence && flags.enable_studio_ai,
  });

  // Also guard UI elements
  return (
    <div>
      {flags.enable_session_intelligence && summary && (
        <SessionSummaryBadge summary={summary} />
      )}
    </div>
  );
}
```

---

## Persona-Based Access Control

Not all personas have access to all intelligence features:

| Feature | admin | alice-builder | alice-analyst | alice-devops | bob | auditor | compliance-officer |
|---------|-------|---------------|---------------|--------------|-----|---------|-------------------|
| Session Intelligence | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Conversation Intelligence | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Canvas Intelligence | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Diagram Intelligence | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Trace Intelligence | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| HITL Intelligence | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| UX Intelligence | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Persona Check Pattern

```typescript
import { usePersona } from '@/persona/PersonaContext';

function CanvasArtifact({ artifact }) {
  const { currentPersona } = usePersona();

  // Only alice-builder and admin have canvas intelligence
  const canUseCanvasAI = ['admin', 'alice-builder'].includes(currentPersona?.variant ?? '');

  const { qualityScore } = useCodeAnalysis({
    userId,
    code: artifact.content,
    enabled: canUseCanvasAI && featureFlags.enable_canvas_intelligence,
  });

  return (
    <div>
      {canUseCanvasAI && qualityScore && <QualityBadge score={qualityScore} />}
    </div>
  );
}
```

---

## Error Handling

All hooks provide consistent error handling:

```typescript
const {
  summary,
  isLoading,
  error,      // Error object if request failed
  refetch,    // Function to retry the request
} = useSessionSummary({
  userId,
  sessionId,
  enabled: true,
});

// Display error state
if (error) {
  return (
    <ErrorState
      message="Failed to load session summary"
      onRetry={refetch}
    />
  );
}

// Loading state
if (isLoading) {
  return <Skeleton />;
}
```

---

## Performance Considerations

### 1. Debouncing

For hooks triggered by user input, use debouncing:

```typescript
const { intent } = useIntentDetection({
  query: input,
  enabled: input.length > 10,
  debounceMs: 500, // Wait 500ms after user stops typing
});
```

### 2. Conditional Enabling

Only enable hooks when their data is actually needed:

```typescript
const { summary } = useSessionSummary({
  sessionId,
  // Only fetch when session panel is visible
  enabled: isPanelVisible && featureFlags.enable_session_intelligence,
});
```

### 3. Caching

RTK Query handles caching automatically. Repeated calls with same parameters reuse cached data.

### 4. Parallel Requests

Use `useStudioAI` directly for batch operations:

```typescript
const { analyze } = useStudioAI({ userId, sessionId });

// Single API call for multiple task types
const result = await analyze({
  tasks: [
    { category: 'session', type: 'session_summarize', data: {} },
    { category: 'trace', type: 'trace_summarize', data: { traceId } },
    { category: 'ux', type: 'nav_prediction', data: {} },
  ],
});
```

---

## Testing Guidelines

### Unit Testing Pattern

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

// Mock the API
vi.mock('../api', () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () => Promise.resolve({
        analyses: { /* mock response */ },
      }),
    })),
    { isLoading: false },
  ]),
}));

const Wrapper = ({ children }) => (
  <Provider store={configureStore({ reducer: {} })}>
    {children}
  </Provider>
);

describe('useSessionSummary', () => {
  it('returns summary when enabled', async () => {
    const { result } = renderHook(
      () => useSessionSummary({ userId: 'test', sessionId: 'session-1', enabled: true }),
      { wrapper: Wrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.summary).toBeDefined();
  });
});
```

---

## Rollout Strategy

### Phase 1: Internal Testing
1. Enable `enable_studio_ai` in development/staging
2. Test each intelligence category individually
3. Verify persona-based access control

### Phase 2: Limited Rollout
1. Enable for `admin` persona only in production
2. Monitor error rates and latency
3. Gather user feedback

### Phase 3: Gradual Expansion
1. Enable for `alice-*` personas
2. Add UX intelligence for all users
3. Monitor cost tracking metrics

### Phase 4: Full Rollout
1. Enable all features for all appropriate personas
2. Set conservative cost limits initially
3. Adjust limits based on usage patterns

---

## Related Documentation

- **Plan File**: `/home/vishnu/.claude/plans/noble-sparking-boot.md`
- **Backend API**: `src/mcp_server_langgraph/api/v1/studio_ai.py`
- **Orchestrator**: `src/mcp_server_langgraph/agents/studio_orchestrator.py`
- **Feature Flags**: `src/mcp_server_langgraph/core/feature_flags.py`
- **E2E Tests**: `e2e/*-intelligence.spec.ts`
- **MSW Handlers**: `src/mocks/handlers/studioHandlers.ts`
