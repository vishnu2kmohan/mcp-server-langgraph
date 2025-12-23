# Component Size Reduction Patterns

**Last Updated**: 2025-12-21
**Case Study**: StudioShellLayout.tsx (1,004 → 746 lines, 26% reduction)

This document captures patterns for reducing component size while maintaining functionality and test coverage.

---

## When to Apply

Apply these patterns when a component exceeds **500 lines**, which typically indicates:
- Multiple concerns mixed in one file
- Opportunities for hook extraction
- Types that should be shared across files
- Helper functions that deserve their own home

### Current Large Components

| Component | Lines | Status | Priority |
|-----------|-------|--------|----------|
| ChatMessages.tsx | 1,143 | Pending | High |
| StudioShellLayout.tsx | 746 | ✅ Refactored | Done |

---

## Pattern 1: Extract State Management Hooks

**Before** (inline state + handlers):
```typescript
// StudioShellLayout.tsx - Before
export function StudioShellLayout() {
  // HITL dialog state - 30+ lines
  const [activeApproval, setActiveApproval] = useState<ApprovalPayload | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  // ... 20 more state variables

  // Handlers - 100+ lines
  const handleApprove = useCallback(async () => { /* ... */ }, []);
  const handleReject = useCallback(async () => { /* ... */ }, []);
  // ... 10 more handlers
}
```

**After** (extracted hook):
```typescript
// hooks/useHITLDialogs.ts - 396 lines
export function useHITLDialogs(): UseHITLDialogsReturn {
  // All HITL state encapsulated
  // All handlers encapsulated
  return { showApprovalDialog, handleApprove, handleReject, ... };
}

// StudioShellLayout.tsx - After
import { useHITLDialogs } from "../hooks/useHITLDialogs";

export function StudioShellLayout() {
  const {
    showApprovalDialog,
    activeApproval,
    handleApprove,
    handleReject,
    closApprovalDialog,
  } = useHITLDialogs();
  // ... clean, focused rendering
}
```

**Benefits**:
- Component becomes ~200 lines smaller
- Hook is independently testable (25 tests for useHITLDialogs)
- State logic is reusable in other components
- Easier to reason about component structure

---

## Pattern 2: Consolidate Types to Shared Modules

**Before** (types scattered):
```typescript
// StudioShellLayout.tsx
interface ApprovalRequiredPayload { /* ... */ }
interface ClarificationRequiredPayload { /* ... */ }
function convertUIToAPI(response: UIResponse): APIResponse { /* ... */ }

// hooks/useHITLDialogs.ts
interface ClarificationResponse { /* ... */ }

// components/Admin/ClarificationDialog.tsx
interface ClarificationResponse { /* ... */ }  // Different definition!
```

**After** (consolidated types/hitl.ts):
```typescript
// types/hitl.ts - Single source of truth
export interface ApprovalRequiredPayload { /* ... */ }
export interface ClarificationRequiredPayload { /* ... */ }
export interface ClarificationUIResponse { /* ... */ }
export interface ClarificationAPIResponse { /* ... */ }
export function convertUIResponseToAPIResponse(ui: ClarificationUIResponse): ClarificationAPIResponse { /* ... */ }

// consumers import from one place
import {
  type ApprovalRequiredPayload,
  type ClarificationAPIResponse,
  convertUIResponseToAPIResponse,
} from "../types/hitl";
```

**Benefits**:
- ~40 lines removed per consumer
- Type conflicts eliminated
- Conversion functions have one canonical implementation
- Tests cover types once, not per-consumer

---

## Pattern 3: Re-export for Backwards Compatibility

When consolidating types, add re-exports to avoid breaking existing imports:

```typescript
// hooks/useHITLDialogs.ts
import { type ClarificationAPIResponse } from "../types/hitl";

// Re-export for backwards compatibility
export type ClarificationResponse = ClarificationAPIResponse;
```

This allows existing consumers to continue importing from the hook while new code uses the canonical location.

---

## Pattern 4: Type Aliasing Convention

Use clear naming to distinguish types at different layers:

| Suffix | Purpose | Example |
|--------|---------|---------|
| `*UIResponse` | UI layer (dialog components) | `ClarificationUIResponse` |
| `*APIResponse` | API layer (hook → backend) | `ClarificationAPIResponse` |
| `*Payload` | WebSocket message data | `ApprovalRequiredPayload` |
| `*Request` | Input/request data | `AgentApprovalRequest` |

See `CONTRIBUTING.md > Type Organization` for full documentation.

---

## Pattern 5: Extract Loading Fallbacks

Loading fallbacks can become sub-components:

**Before**:
```typescript
// ChatMessages.tsx - 50+ lines of loading states
function DiagramLoadingFallback() { /* 10 lines */ }
function CodeLoadingFallback() { /* 10 lines */ }
function SandpackLoadingFallback() { /* 20 lines */ }
```

**After**:
```typescript
// components/LoadingFallbacks/index.ts
export { DiagramLoadingFallback } from "./DiagramLoadingFallback";
export { CodeLoadingFallback } from "./CodeLoadingFallback";
export { SandpackLoadingFallback } from "./SandpackLoadingFallback";

// ChatMessages.tsx
import { DiagramLoadingFallback, CodeLoadingFallback } from "../LoadingFallbacks";
```

---

## Refactoring Checklist

### Before Starting

- [ ] Count current lines (`wc -l Component.tsx`)
- [ ] Run tests to establish baseline (`npm test -- Component.test.tsx`)
- [ ] Identify state clusters that belong together
- [ ] Identify types used by multiple files

### During Refactoring

- [ ] **TDD**: Write tests for new hooks BEFORE implementation
- [ ] Extract one concern at a time
- [ ] Keep component tests passing at each step
- [ ] Add `export type { X }` for backwards compatibility
- [ ] Update types/index.ts if adding new type modules

### After Refactoring

- [ ] Run full test suite
- [ ] Verify line count reduction
- [ ] Update CONTRIBUTING.md if new patterns established
- [ ] Add entry to plan metrics

---

## Case Study: StudioShellLayout Refactoring

### Timeline

| Step | Lines | Tests | Notes |
|------|-------|-------|-------|
| Initial | 1,004 | 129 pass | Starting point |
| Extract useHITLDialogs | 877 | 154 pass | +25 hook tests |
| Consolidate types/hitl.ts | 812 | 164 pass | +10 type tests |
| Move helper functions | 746 | 164 pass | Final state |

### Metrics

- **Lines Reduced**: 258 (26%)
- **Test Increase**: +35 tests (better coverage)
- **Time**: ~2 hours (including TDD)
- **Breaks**: 0 (all tests pass at each step)

### Key Decisions

1. **Hook boundary**: useHITLDialogs encapsulates all Human-in-the-Loop state
2. **Type location**: types/hitl.ts for cross-cutting HITL types
3. **Backwards compat**: Re-exports in useHITLDialogs.ts
4. **Conversion functions**: Live with types, not with consumers

---

## Applying to ChatMessages.tsx (1,143 lines)

### Proposed Extraction Plan

1. **types/chat-messages.ts** (~150 lines)
   - `Message`, `Source` interfaces
   - `LangGraphNode`, `LangGraphEdge` types
   - `AgentExecutionTrace` interface

2. **hooks/useChatAutoScroll.ts** (~50 lines)
   - Auto-scroll to bottom logic
   - Ref management

3. **components/Chat/LangGraphVisualization.tsx** (~100 lines)
   - LangGraphNodeVisualization component
   - getNodeTypeIcon, getNodeStatusIndicator, getNodeColor

4. **components/Chat/MarkdownContent.tsx** (~250 lines)
   - MarkdownContent component with all custom renderers
   - ChartCodeBlock sub-component

5. **components/LoadingFallbacks/** (~50 lines)
   - DiagramLoadingFallback
   - CodeLoadingFallback
   - SandpackLoadingFallback

### Expected Result

- ChatMessages.tsx: ~550 lines (51% reduction)
- Total lines: Same (just organized better)
- Tests: +50 (for extracted modules)
- Reusability: LangGraphVisualization, MarkdownContent reusable

---

## Related Documentation

- [CONTRIBUTING.md > Type Organization](../../studio/frontend/CONTRIBUTING.md)
- [TESTING_PATTERNS.md](./testing/TESTING_PATTERNS.md)
- [STATE_MANAGEMENT_PATTERNS.md](./STATE_MANAGEMENT_PATTERNS.md)
