# Execution Mode Patterns

**Created**: 2025-01-19
**Last Updated**: 2025-01-19

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| BypassManager | Complete | `src/.../execution/bypass_manager.py` |
| BypassManager tests | Complete | `tests/unit/execution/test_bypass_manager.py` (21 tests) |
| OpenFGA bypass_executor | Complete | `config/openfga/modules/04-access-control.fga` |
| Audit event types | Complete | `src/.../audit/models.py` (BYPASS_ACTIVATED, etc.) |
| Feature flag | Complete | `feature_flags.py` (bypass_risk_aware_enabled) |
| API endpoint | Complete | `api/v1/auth.py` (/bypass-permission) |
| Chat.py integration | Complete | Plan generation SSE + BypassManager + OpenFGA + Audit |
| SegmentedControl UI | Complete | `ChatInput.tsx` |
| ExecutionModeIndicator | Complete | Kept for backward compat |
| Frontend API | Complete | `api/index.ts` (checkBypassPermission) |
| Redux slice | Complete | `executionModeSlice.ts` |
| E2E tests | Complete | `e2e/execution-mode-selection.spec.ts` |
| PreferencesMenu | Complete | `PreferencesMenu.tsx` (23 tests) |
| PreferencesMenu integration | Complete | `ChatInput.tsx` (showPreferencesMenu prop) |

## Overview

This document captures patterns and lessons learned from implementing the execution mode toggle feature (Ctrl/Cmd+Shift+M) with SegmentedControl UI and risk-aware bypass mode.

---

## Architecture

### Mode Selection Strategy

There are two UI patterns for mode selection in ChatInput:

1. **SegmentedControl** (primary): Direct mode selection via radiogroup
   - Used when `onExecutionModeChange` prop is provided
   - All modes visible simultaneously
   - Best for desktop/tablet

2. **ExecutionModeIndicator** (fallback): Click-to-cycle badge
   - Used when only `onCycleExecutionMode` prop is provided
   - Compact single-button interface
   - Good for mobile/narrow layouts

```tsx
// ChatInput decides which to render based on props
{onExecutionModeChange ? (
  <SegmentedControl {...} />
) : onCycleExecutionMode ? (
  <ExecutionModeIndicator {...} />
) : null}
```

### Execution Modes

| Mode | Description | Risk Threshold |
|------|-------------|----------------|
| `default` | Normal chat - approval for medium/high risk | medium+ |
| `plan` | All tasks require explicit approval | all |
| `auto_accept` | Auto-accept suggestions | none |
| `bypass` | Risk-aware auto-approval (requires permission) | high only |

---

## Redux State Management

### executionModeSlice

```typescript
// State shape
interface ExecutionModeState {
  executionMode: ExecutionMode;
  hasBypassPermission: boolean;
}

// Key actions
setExecutionMode(mode)      // Direct mode change
cycleExecutionMode()        // Cycle to next mode
setHasBypassPermission(ok)  // Update from API

// Key selector
selectCanBypass()           // hasBypassPermission && mode === 'bypass'
```

### Permission Wiring

1. **API call**: `useCheckBypassPermissionQuery()` fetches permission on mount
2. **Redux update**: `setHasBypassPermission(result.allowed)`
3. **UI blocking**: Bypass segment disabled if `!hasBypassPermission`

---

## Keyboard Shortcut

**Shortcut**: `Ctrl+Shift+M` (Windows/Linux) or `Cmd+Shift+M` (macOS)

### Implementation Pattern

```typescript
const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
  // Ctrl/Cmd+Shift+M to cycle execution mode
  if (e.key === "m" && e.shiftKey && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    onCycleExecutionMode?.();
    return;
  }
  // ... other handlers
}, [onCycleExecutionMode]);
```

### Accessibility

- Works inside textarea (attached to `onKeyDown`)
- `e.preventDefault()` prevents default browser behavior
- aria-label includes shortcut hint

---

## Testing Patterns

### Motion/React Mock (Critical)

Motion props cause React warnings when passed to DOM elements. Filter them:

```typescript
const MOTION_PROPS = new Set([
  "whileHover", "whileTap", "whileFocus", "whileDrag", "whileInView",
  "initial", "animate", "exit", "variants", "transition",
  "layout", "layoutId", "drag", "dragConstraints", "dragElastic",
  "dragMomentum", "onAnimationStart", "onAnimationComplete",
  "onDragStart", "onDragEnd", "onDrag",
]);

function filterMotionProps<T>(props: T): T {
  const filtered = { ...props };
  for (const key of Object.keys(filtered)) {
    if (MOTION_PROPS.has(key)) delete filtered[key];
  }
  return filtered;
}

vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...props }) => <div {...filterMotionProps(props)}>{children}</div>,
    button: ({ children, ...props }) => <button {...filterMotionProps(props)}>{children}</button>,
  },
  useReducedMotion: () => false,
  AnimatePresence: ({ children }) => <>{children}</>,
}));
```

### Test Selector Strategy

Use specific aria-labels to avoid regex collisions:

```typescript
// BAD: /auto/i matches both "Auto" and "auto-approval"
screen.getByRole("radio", { name: /auto/i })

// GOOD: specific aria-label
screen.getByRole("radio", { name: /auto mode/i })
screen.getByRole("radio", { name: /bypass mode/i })
```

### RTK Query Mock Pattern

```typescript
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useCheckBypassPermissionQuery: () => ({
      data: { allowed: false },
      isLoading: false,
      isError: false,
    }),
  };
});
```

### Redux Slice Mock Pattern

```typescript
vi.mock("../store/slices/executionModeSlice", () => ({
  selectExecutionMode: () => "default",
  selectCanBypass: () => false,
  cycleExecutionMode: vi.fn(() => ({ type: "executionMode/cycleExecutionMode" })),
  setExecutionMode: vi.fn((mode) => ({
    type: "executionMode/setExecutionMode",
    payload: mode,
  })),
  setHasBypassPermission: vi.fn((allowed) => ({
    type: "executionMode/setHasBypassPermission",
    payload: allowed,
  })),
}));
```

---

## OpenFGA Permission Model

### Bypass Permission

```fga
type system
  relations
    define bypass_executor: [user] or admin
```

### Checking Permission

```python
# Backend: check_permission (NOT check)
allowed = await openfga.check_permission(
    user=current_user["user_id"],  # Already "user:alice"
    relation="bypass_executor",
    object="system:global",
    critical=True,  # Fail-closed
)
```

### Frontend API

```typescript
// RTK Query endpoint
checkBypassPermission: builder.query<{ allowed: boolean }, void>({
  query: () => "/auth/bypass-permission",
  providesTags: ["BypassPermission"],
}),
```

---

## File Reference

| File | Purpose |
|------|---------|
| `ChatInput.tsx` | Mode selection UI (SegmentedControl or ExecutionModeIndicator) |
| `ChatInput.modes.test.tsx` | Unit tests for mode toggle |
| `ExecutionModeIndicator.tsx` | Compact click-to-cycle badge (fallback) |
| `executionModeSlice.ts` | Redux state for execution mode |
| `ConnectedChatInputForm.tsx` | Wires mode state to ChatInput |
| `execution-mode-selection.spec.ts` | E2E tests for mode selection |
| `bypass_manager.py` | Backend risk-aware auto-approval |

---

## Gotchas

### 1. User ID Format (CRITICAL)

`current_user["user_id"]` is **already prefixed** as `user:alice` from `jwt_utils.py:170`. **DO NOT prefix again!**

```python
# CORRECT - use as-is
user_id = current_user.get("user_id")  # Returns "user:alice"
await openfga.check_permission(user=user_id, ...)  # Works!

# WRONG - double-prefixed
user_id = f"user:{current_user.get('user_id')}"  # "user:user:alice" - FAILS!
```

**Where this applies:**
- OpenFGA `check_permission()` calls
- Audit event `actor_id` field
- Any permission checks

### 2. Shortcut not customizable

Hardcoded Ctrl/Cmd+Shift+M for this iteration. Preferences wiring deferred.

### 3. SegmentedControl vs ExecutionModeIndicator

Keep both for different use cases. ChatInput conditionally renders based on props.

### 4. Test isolation

Mock both `executionModeSlice` and `useCheckBypassPermissionQuery` when testing ConnectedChatInputForm.

### 5. Bypass mode cycling

Skip bypass in cycle if `!hasBypassPermission`.

### 6. Audit event helpers deferred

Currently only BYPASS_ACTIVATED is used. When BYPASS_AUTO_APPROVED/USER_APPROVED/REJECTED are implemented, consider extracting a `create_bypass_audit_event()` helper to reduce duplication.

### 7. Model selection separate from PreferencesMenu

Model selector remains in ChatInput controls row for visibility. PreferencesMenu consolidates thinking level, tool mode, and KB focus only. This is intentional - users need to see current model at a glance.

### 8. PreferencesMenu feature flag

Controlled by `preferences_menu` flag. When enabled, hides separate ToolSelector and KB Focus controls (consolidated into menu).

### 9. Vitest Mock Hoisting (CRITICAL)

Due to Vitest's `vi.mock()` hoisting, **you cannot import helper functions** and use them in mock factories.

```typescript
// ❌ WRONG - will fail with "Cannot access before initialization"
import { createMotionMock } from "../test-utils";
vi.mock("motion/react", () => createMotionMock());  // ERROR!

// ❌ WRONG - external variable reference
const mockFn = vi.fn();
vi.mock("../store/slices/executionModeSlice", () => ({
  selectExecutionMode: mockFn,  // ERROR! mockFn hoisted before definition
}));

// ✅ CORRECT - inline mock factory
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
}));

// ✅ CORRECT - use inline vi.fn() in mock
vi.mock("../store/slices/executionModeSlice", () => ({
  selectExecutionMode: () => "default",  // Inline function
  cycleExecutionMode: vi.fn(() => ({ type: "test" })),  // vi.fn() inline is OK
}));
```

**Key points:**
- `vi.mock()` is hoisted to the top of the file before any imports or variable declarations
- Mock factory functions run before any code in the file executes
- Copy MOTION_PROPS and filterMotionProps inline from `test-utils.tsx`

### 10. Feature Flag End-to-End Wiring (CRITICAL)

Adding a new feature flag requires changes in **THREE places** - miss any and the flag won't work!

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Backend Flag Definition                                │
│  File: src/mcp_server_langgraph/core/feature_flags.py          │
│                                                                  │
│  bypass_risk_aware_enabled: bool = Field(                       │
│      default=False,                                              │
│      description="Enable risk-aware bypass mode",                │
│  )                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Add to get_ui_features_for_role() mapping             │
│  File: src/mcp_server_langgraph/core/feature_flags.py:2013     │
│                                                                  │
│  def get_ui_features_for_role(self) -> dict[str, bool]:         │
│      return {                                                    │
│          ...                                                     │
│          "bypass_risk_aware_enabled": self.bypass_risk_aware,   │  ← ADD HERE!
│      }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Frontend TypeScript Interface                          │
│  File: src/.../studio/frontend/src/types/api.ts:254+           │
│                                                                  │
│  export interface FeatureFlags {                                 │
│      ...                                                         │
│      bypass_risk_aware_enabled?: boolean;  ← ADD HERE!          │
│  }                                                               │
│                                                                  │
│  NOTE: This is in types/api.ts, NOT types/index.ts!             │
└─────────────────────────────────────────────────────────────────┘
```

**Common failure modes:**
- Flag defined but not in `get_ui_features_for_role()` → Frontend never receives it
- Flag not in `types/api.ts` → TypeScript errors or flag ignored
- Added to wrong TypeScript file → Runtime undefined

### 11. Bypass mode telemetry

Use `sessionTelemetry.trackExecutionModeChange()` for mode switches and `sessionTelemetry.trackBypassApproval()` for plan approvals. Metrics available in `getMetrics().executionMode`. Track: mode changes by trigger, bypass approvals by approval type (auto/user), risk level, and complexity.

### 12. TelemetryContext Mock Required

When testing ConnectedChatInputForm, you MUST mock `TelemetryContext`:

```typescript
vi.mock("../contexts/TelemetryContext", () => ({
  useSessionTelemetry: () => ({
    trackExecutionModeChange: vi.fn(),
    trackBypassApproval: vi.fn(),
    trackSessionCreation: vi.fn(),
    // ... other methods
  }),
}));
```

Without this mock, tests fail with hook errors after telemetry wiring was added.

### 13. Test Selector Collisions

Use specific aria-labels to avoid regex collisions in tests:

```typescript
// ❌ BAD - /auto/i matches both "Auto" and "auto-approval"
screen.getByRole("radio", { name: /auto/i });

// ✅ GOOD - specific aria-label
screen.getByRole("radio", { name: /auto mode/i });
screen.getByRole("radio", { name: /bypass mode/i });
```

### 14. Bypass Audit Event Helper

Use `log_bypass_audit_event()` from `execution/bypass_audit.py` to reduce duplication when logging bypass-related audit events:

```python
from mcp_server_langgraph.audit.context import create_context_from_request
from mcp_server_langgraph.audit.models import AuditEventType
from mcp_server_langgraph.execution.bypass_audit import log_bypass_audit_event

await log_bypass_audit_event(
    audit_service=audit_service,
    event_type=AuditEventType.BYPASS_ACTIVATED,
    current_user=current_user,
    resource_type="session",
    resource_id=session_id,
    action="Activated risk-aware bypass execution mode",
    details={"execution_mode": "bypass"},
    context=create_context_from_request(request),
)
```

The helper:
- Handles `audit_service=None` gracefully (no-op)
- Swallows exceptions to not fail the request
- Creates consistent actor/category/regulation_tags
- Creates minimal context if not provided

### 15. Execution Plan Cost Estimation

Use `estimate_execution_cost()` from `execution/cost_estimator.py` for plan cost estimation:

```python
from mcp_server_langgraph.execution.cost_estimator import estimate_execution_cost

cost = estimate_execution_cost(
    model="claude-sonnet-4-20250514",
    task_type=routing_decision.task_type,
    complexity=routing_decision.complexity,
    thinking_budget=routing_decision.thinking_budget,
)
```

The estimator:
- Uses LiteLLM pricing data for accurate model costs
- Estimates tokens based on task_type, complexity, thinking_budget
- Returns Decimal("0") for unknown models (fail-safe)

### 16. Cost Estimation with Confidence Intervals

Use `estimate_execution_cost_with_confidence()` for cost estimates with min/max bounds and critique rounds:

```python
from mcp_server_langgraph.execution.cost_estimator import (
    estimate_execution_cost_with_confidence,
)

result = estimate_execution_cost_with_confidence(
    model="claude-sonnet-4-20250514",
    task_type="code",
    complexity="complicated",
    thinking_budget="medium",
    critique_rounds=2,  # Optional, defaults to 0
)

print(f"${result['min_cost']} - ${result['max_cost']}")  # e.g., $0.08 - $0.18
```

Features:
- **Confidence intervals**: Based on complexity (simple ±20%, complicated -30%/+40%, complex -50%/+100%)
- **Critique rounds**: Each round multiplies cost by 1.3 (30% overhead)
- Returns `CostEstimateWithConfidence` TypedDict with `min_cost`, `estimated_cost`, `max_cost`

### 17. Bypass Audit Events Implementation

All four bypass audit events are now implemented:

| Event | Location | When Logged |
|-------|----------|-------------|
| `BYPASS_ACTIVATED` | `chat.py:1721` | User enables bypass mode |
| `BYPASS_AUTO_APPROVED` | `chat.py:1409` | Low-risk plan auto-approved |
| `BYPASS_USER_APPROVED` | `execution_plans.py:253` | User manually approves plan |
| `BYPASS_REJECTED` | `execution_plans.py:307` | User rejects plan |

All use `log_bypass_audit_event()` helper for consistent structure:
- Category: SYSTEM
- Regulation tags: SOC2, FedRAMP
- Actor from current_user (already prefixed as "user:alice")

---

## Future Work

### Customizable Keyboard Shortcuts (Deferred)

**Status**: Deferred to future iteration

The execution mode toggle keyboard shortcut (`Ctrl/Cmd+Shift+M`) is currently hardcoded. Customizable shortcuts were intentionally deferred due to complexity.

**Planned implementation**:

1. **Preferences Model**: Add to `types/preferences.ts`:
   ```typescript
   interface KeyboardPreferences {
     cycleExecutionMode: ShortcutDef;
     // ... other shortcuts
   }
   ```

2. **Settings UI**: Add shortcut customization to SettingsPanel

3. **Persistence**: Store in user preferences (localStorage + backend sync)

4. **Hook Integration**: Update `ChatInput.handleKeyDown` to read from preferences

5. **Help Updates**: Dynamic shortcut display in:
   - `helpData.ts`
   - Tooltips (ExecutionModeIndicator, SegmentedControl)
   - Keyboard shortcuts overlay

**Why deferred**:
- Requires preferences infrastructure changes
- Cross-platform shortcut detection complexity (Mac vs Windows/Linux)
- Need to handle shortcut conflicts with browser/OS defaults
- Accessibility testing for custom shortcuts

**Files to modify when implementing**:
- `src/.../types/preferences.ts`
- `src/.../components/Settings/KeyboardSettings.tsx` (new)
- `src/.../components/Chat/ChatInput.tsx`
- `src/.../help/helpData.ts`
- `src/.../hooks/useKeyboardPreferences.ts` (new)
