# Frontend Test OOM Prevention Guidelines

**Last Updated**: 2025-12-20
**Issue Reference**: WorkflowsPage.test.tsx OOM incident

## Problem Summary

Test files can cause Node.js to run out of memory (OOM) during Vitest execution when heavy dependencies are loaded without proper mocking. The root cause is circular dependency chains that trigger loading entire module trees before mocks can intercept.

### Example OOM Chain

```
WorkflowsPage.test.tsx
  └── WorkflowsPage.tsx
       └── store/slices/workflowSlice.ts
            └── store/index.ts
                 └── api/index.ts (RTK Query)
                      └── All RTK Query endpoints loaded
                           └── 4GB+ heap exhaustion → OOM
```

## High-Risk Dependencies

These modules trigger heavy initialization and should ALWAYS be mocked in tests:

| Module | Risk Level | Why It's Heavy |
|--------|------------|----------------|
| `../api` / `../../api` | **CRITICAL** | RTK Query endpoints, middleware, cache |
| `../store/index` | **CRITICAL** | Full Redux store with all reducers + api |
| `reactflow` / `@xyflow/react` | **HIGH** | React Flow canvas, nodes, edges |
| `react-resizable-panels` | **MEDIUM** | Layout calculations, ResizeObserver |
| Heavy slice imports | **MEDIUM** | May trigger circular imports |

## Safe Patterns

### Pattern 1: Mock API Module Before Imports

```typescript
// ✅ CORRECT: vi.mock is hoisted and runs before imports
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    useGetSomeQuery: () => mockUseGetSomeQuery(),
    useSubmitMutation: () => mockUseSubmitMutation(),
  };
});

// Import AFTER mock
import { SomeComponent } from "./SomeComponent";
import { api } from "../api";
```

### Pattern 2: Minimal Test Store

```typescript
// ✅ CORRECT: Only include reducers needed for the test
function createTestStore() {
  return configureStore({
    reducer: {
      session: sessionReducer,  // Only what's needed
      // ❌ DON'T: [api.reducerPath]: api.reducer (unless mocked)
    },
  });
}
```

### Pattern 3: Mock Heavy Components

```typescript
// ✅ CORRECT: Mock heavy dependencies
vi.mock("react-resizable-panels", () => ({
  Panel: ({ children }) => <div>{children}</div>,
  PanelGroup: ({ children }) => <div>{children}</div>,
  PanelResizeHandle: () => <div />,
}));

vi.mock("reactflow", () => ({
  default: ({ children }) => <div>{children}</div>,
  ReactFlowProvider: ({ children }) => <div>{children}</div>,
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  useNodesState: (nodes) => [nodes, vi.fn()],
  useEdgesState: (edges) => [edges, vi.fn()],
}));
```

### Pattern 4: Use vi.hoisted() for Mock Functions

```typescript
// ✅ CORRECT: Define mock functions before vi.mock references them
const mockUseStreamingChat = vi.hoisted(() => vi.fn());
const mockUseMCPConnection = vi.hoisted(() => vi.fn());

vi.mock("../hooks/useStreamingChat", () => ({
  useStreamingChat: mockUseStreamingChat,
}));
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Import Store Directly

```typescript
// ❌ WRONG: Importing real store loads all reducers including api
import { store } from "../store";

// ✅ CORRECT: Create minimal test store
const store = configureStore({
  reducer: { session: sessionReducer },
});
```

### Anti-Pattern 2: Mock After Import

```typescript
// ❌ WRONG: Module already loaded before mock runs
import { SomeComponent } from "./SomeComponent";

vi.mock("../api", () => ({ ... }));  // Too late!
```

### Anti-Pattern 3: No Mock for API Hooks

```typescript
// ❌ WRONG: RTK Query hooks trigger full api module load
import { useGetHealthQuery } from "../api";

describe("Test", () => {
  it("should work", () => {
    // OOM before this line executes
  });
});
```

### Anti-Pattern 4: Using Full Store with api.reducer

```typescript
// ❌ WRONG (without api mock): Loads entire RTK Query setup
function createTestStore() {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,  // Heavy!
      ...otherReducers,
    },
    middleware: (getDefault) => getDefault().concat(api.middleware),
  });
}

// ✅ CORRECT: Only include api if properly mocked first
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useSomeQuery: () => mockUseSomeQuery() };
});

import { api } from "../api";  // Now safe - mocked

function createTestStore() {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,  // OK - api is mocked
    },
  });
}
```

## Checklist for New Test Files

Before committing a new test file:

- [ ] All `../api` imports have corresponding `vi.mock("../api")` calls
- [ ] `vi.mock()` calls appear BEFORE import statements (Vitest hoists them)
- [ ] Test store only includes reducers actually needed
- [ ] Heavy libraries (reactflow, react-resizable-panels) are mocked
- [ ] No direct `import { store } from "../store"` usage
- [ ] `beforeEach(() => vi.clearAllMocks())` is present
- [ ] Test file runs in under 60 seconds with no memory warnings

## Testing Your Test File

Run these commands to verify your test file is OOM-safe:

```bash
# Run single test file with timeout
timeout 60 npm run test -- --run path/to/your.test.tsx

# Check memory usage
NODE_OPTIONS="--max-old-space-size=512" npm run test -- --run path/to/your.test.tsx

# If OOM occurs, the test needs better mocking
```

## Known OOM-Prone Files

These test files have been documented as OOM risks and have special handling:

| File | Status | Solution |
|------|--------|----------|
| `WorkflowsPage.test.tsx` | ✅ FIXED | Full OOM fix implemented via store/types.ts isolation + thin wrapper pattern |

## Implemented Fixes

### Store Types Isolation (2025-12-20) - COMPLETE FIX

The root cause of the OOM issue was a circular dependency chain:
```
WorkflowsPage.tsx
  └── store/hooks.ts
       └── store/index.ts (imported types)
            └── api/index.ts (RTK Query)
                 └── 2150 lines, 150+ endpoints
                      └── 4GB+ heap exhaustion → OOM
```

**Solution: Isolated Type Definitions**

**File: `src/store/types.ts`** (NEW)
```typescript
/**
 * Store Types - Isolated Type Definitions
 *
 * Exports RootState and AppDispatch types WITHOUT importing
 * the full store or api modules.
 */
import type { ThunkDispatch, UnknownAction } from "@reduxjs/toolkit";

// Type-only imports from slices (do NOT trigger module evaluation)
import type uiReducer from "./slices/uiSlice";
import type personaReducer from "./slices/personaSlice";
// ... other slice type imports

type UIState = ReturnType<typeof uiReducer>;
type PersonaState = ReturnType<typeof personaReducer>;
// ... other state types

export interface SliceStates {
  ui: UIState;
  persona: PersonaState;
  // ... all slice states
}

// Placeholder for RTK Query api state (avoids importing api module)
type ApiState = any;

export interface RootState extends SliceStates {
  api: ApiState;
}

export type AppDispatch = ThunkDispatch<RootState, undefined, UnknownAction>;
```

**File: `src/store/hooks.ts`** (MODIFIED)
```typescript
// BEFORE (caused OOM):
import type { RootState, AppDispatch } from "./index";

// AFTER (OOM-safe):
import type { RootState, AppDispatch } from "./types";
```

**Results:**
- WorkflowsPage.test.tsx: 32 tests pass in 1.05s
- No OOM, no memory warnings
- Full unit test coverage restored

### Thin Wrapper Pattern (2025-12-20)

For API hooks, a thin wrapper pattern reduces coupling:

**File: `src/hooks/useWorkflowAPI.ts`**
```typescript
/**
 * Thin wrapper for workflow API hooks.
 * Allows tests to mock this small module instead of the full RTK Query API.
 */
export {
  useGetWorkflowSuggestionsMutation,
  useListWorkflowExecutionsQuery,
} from "../api";
```

**Benefits:**
- WorkflowsPage imports from `../hooks/useWorkflowAPI` instead of `../api`
- Tests can mock `../hooks/useWorkflowAPI` without loading full RTK Query
- The wrapper itself can be unit tested (see `useWorkflowAPI.test.ts`)

## Reference Files (Good Examples)

Study these files for proper mocking patterns:

- `src/pages/SharedWorkflowsPage.test.tsx` - Proper api mock with spread
- `src/components/Layout/AppShell.test.tsx` - Complex component with full mocking
- `src/components/Workflow/WorkflowCanvas.test.tsx` - reactflow mocking
- `src/pages/ChatPage.test.tsx` - Multiple hook mocks

## Audit Results (2025-12-20)

Comprehensive audit of 89 frontend test files:

| Category | Files | Status |
|----------|-------|--------|
| Proper API mocking | 89/89 | ✅ All safe |
| Minimal test stores | 45/45 | ✅ All safe |
| React Flow mocking | 9/9 | ✅ All safe |
| Type safety | 89/89 | ✅ All safe |

**No HIGH-RISK files detected** in the current test suite.
