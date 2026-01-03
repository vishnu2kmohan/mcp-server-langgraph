# ADR-0088: Frontend Hook Selection Guidance

**Status**: Accepted
**Date**: 2026-01-02
**Context**: Agent Studio Frontend Hook Audit (Phase 5)
**Supersedes**: None
**Related**: ADR-0084 (Studio Orchestrator Unified AI), ADR-0085 (Feature Flag Consolidation)

## Context

The Agent Studio frontend has 127+ custom hooks across 10 categories. A comprehensive audit identified:

1. **Duplicate hooks** serving similar purposes with different implementations
2. **Dead exports** - hooks exported but never imported at runtime
3. **Unclear selection criteria** - developers unsure which hook to use for a given task

### Problems Identified

1. **Nudge System Duplication**
   - `useNudges` - Simple, localStorage + authenticatedFetch
   - `useAINudges` - Complex, Redux + RTK Query (never adopted)
   - Both hit same backend: `/api/v1/ai/nudges/recommend`

2. **AI Intelligence Hooks Overlap**
   - `useConversationIntelligence` - Conversation-specific analysis
   - `useSessionIntelligence` - Session-level analysis
   - `useCanvasIntelligence` - Canvas code/diagram analysis
   - `useTraceIntelligence` - Trace summarization
   - `useHITLIntelligence` - HITL risk/decision analysis
   - All use `useStudioAnalyzeMutation` with different categories

3. **Dead Exports**
   - `useAINudges` - Deprecated, use `useNudges` with `enableAI=true`
   - `useAIDisclosure` - Deprecated, use `useProgressiveDisclosure`
   - `useTierLimits` - Deprecated, use feature flags
   - `useBatchApprovals` - Deprecated, use RTK Query mutations

4. **WebSocket Hook Proliferation**
   - 16+ WebSocket hooks with similar patterns
   - Some never connected at runtime

## Decision

### 1. Hook Selection Matrix

| Use Case | Recommended Hook | Avoid |
|----------|------------------|-------|
| **Nudges/Hints** | `useNudges` with `enableAI=true` | `useAINudges` (deprecated) |
| **Progressive Disclosure** | `useProgressiveDisclosure` | `useAIDisclosure` (deprecated) |
| **AI Analysis (Conversation)** | `useConversationIntelligence` | - |
| **AI Analysis (Canvas)** | `useCanvasIntelligence` | - |
| **AI Analysis (Session)** | `useSessionIntelligence` | - |
| **AI Analysis (Trace)** | `useTraceIntelligence` | - |
| **AI Analysis (HITL)** | `useRiskAssessment`, `useDecisionHistory` | - |
| **Tier Limits** | `useFeatureFlag` | `useTierLimits` (deprecated) |
| **Batch HITL** | RTK Query mutations | `useBatchApprovals` (deprecated) |

### 2. State Management Selection

| Complexity | Approach | Example Hooks |
|------------|----------|---------------|
| **Simple/Local** | useState + localStorage | `useNudges`, `useProgressiveDisclosure` |
| **Shared/Global** | Redux slice | `useAppSelector`, `useHITLDialogs` |
| **Server State** | RTK Query | `useListSessionsQuery`, `useStudioAnalyzeMutation` |
| **Real-time** | WebSocket hooks | `useNotificationWebSocket`, `useAlertWebSocket` |

### 3. AI Integration Pattern

All AI-powered features should use the **StudioOrchestrator** via RTK Query:

```typescript
// Preferred: Use domain-specific intelligence hooks
import { useCanvasIntelligence } from '../hooks';

const { summary, isLoading } = useCanvasIntelligence({
  userId,
  content: canvasContent,
  category: 'code',
});

// These hooks internally use:
const [analyzeMutation] = useStudioAnalyzeMutation();
await analyzeMutation({
  user_id: userId,
  session_id: sessionId,
  tasks: [{ category: 'code', type: 'summarize', data: { ... } }],
}).unwrap();
```

### 4. Deprecation Policy

Deprecated hooks:
1. Have `@deprecated` JSDoc annotation with migration guidance
2. Remain exported for backwards compatibility
3. Will be removed in next major version
4. Are marked in this ADR for reference

### 5. New Hook Guidelines

When creating new hooks:

1. **Check for existing alternatives** - Search `src/hooks/` first
2. **Prefer composition** - Compose from existing hooks rather than duplicating
3. **State management** - Use simplest approach that meets requirements
4. **AI integration** - Use `useStudioAnalyzeMutation` with appropriate category
5. **Testing** - Write tests before implementation (TDD)
6. **Documentation** - Include JSDoc with examples

## Consequences

### Positive

- Clear selection criteria for hook usage
- Reduced confusion for new developers
- Deprecated hooks identified and documented
- Consistent AI integration pattern via StudioOrchestrator

### Negative

- Deprecated hooks still in codebase (backwards compatibility)
- Migration needed for any future users of deprecated hooks

### Neutral

- Hook count remains high (127+), but now well-organized
- Dead exports remain for type safety until removal

## Compliance

- [ ] All deprecated hooks have `@deprecated` JSDoc annotation
- [ ] Hook selection matrix documented in this ADR
- [ ] New hook creation follows guidelines
- [ ] Dead exports tracked for removal in next major version

## References

- Sprint Block 5 Hooks Audit Report
- `src/hooks/index.ts` - Central export file
- `src/test/commonMocks.ts` - Shared mock implementations
