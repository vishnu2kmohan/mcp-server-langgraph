# StudioShellLayout Test Suite

This directory contains split test files for the StudioShellLayout component. The tests have been organized into separate files by concern to:

1. **Prevent OOM (Out of Memory)** issues during test runs
2. **Improve test isolation** and parallel execution
3. **Enhance maintainability** by grouping related tests
4. **Reduce context switching** for developers

## File Structure

```
__tests__/
├── README.md                               # This file
├── StudioShellLayout.setup.ts              # Shared mocks, utilities, and helpers
├── StudioShellLayout.core.test.tsx         # Core rendering and structure tests
├── StudioShellLayout.ai.test.tsx           # AI interpretation, nudges, persona
├── StudioShellLayout.panels.test.tsx       # Panel visibility, collapse, responsive
├── StudioShellLayout.rbac.test.tsx         # RBAC, persona-based navigation
└── StudioShellLayout.accessibility.test.tsx # WCAG 2.1 AA compliance, a11y
```

## Test Categories

| File | Tests | Description |
|------|-------|-------------|
| `core.test.tsx` | 13 | Basic rendering, structure, initial state |
| `ai.test.tsx` | 8 | AI interpretation, nudges, persona mismatch |
| `panels.test.tsx` | 18 | Panel visibility, collapse states, responsive |
| `rbac.test.tsx` | 9 | RBAC, persona-based navigation filtering |
| `accessibility.test.tsx` | 10 | WCAG 2.1 AA, axe-core, accessible labels |

**Total: 58 tests** across 5 split files

## Shared Setup (`StudioShellLayout.setup.ts`)

The setup file provides:

### Mock Implementations
```typescript
import { mockImplementations } from "./StudioShellLayout.setup";

vi.mock("../../contexts/TelemetryContext", () => mockImplementations.TelemetryContext);
vi.mock("../../hooks/useNudges", () => mockImplementations.useNudges);
// ... etc
```

### Store Creators
```typescript
import { createTestStore, createStoreWithPersona } from "./StudioShellLayout.setup";

// Default store with admin persona
const store = createTestStore();

// Store with specific persona
const userStore = createStoreWithPersona("user");
const devStore = createStoreWithPersona("developer");
const adminStore = createStoreWithPersona("admin");
```

### Utilities
```typescript
import {
  resetAllMocks,      // Reset all mock state between tests
  flushPromises,       // Wait for pending promises
  dispatchKeyboardEvent, // Simulate keyboard events
  resetPanelCounter,   // Reset panel group counter for predictable IDs
} from "./StudioShellLayout.setup";
```

### Mock State Objects
```typescript
import {
  mockNudgesState,          // Configure nudge test state
  mockPersonaAnalysisState, // Configure persona analysis state
  mockFeatureFlags,         // Configure feature flags
  mockFns,                  // Access mock functions (navigate, revalidate, etc.)
} from "./StudioShellLayout.setup";
```

## Creating a New Split Test File

1. **Create the file** following the naming convention:
   ```
   StudioShellLayout.<category>.test.tsx
   ```

2. **Add the standard imports and mocks**:
   ```typescript
   import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
   import { render, screen, act, waitFor, cleanup } from "@testing-library/react";
   import { Provider } from "react-redux";
   import React from "react";

   // Import shared setup
   import {
     resetAllMocks,
     createTestStore,
     flushPromises,
     mockImplementations,
     mockResizablePanels,
     mockReactRouter,
     resetPanelCounter,
   } from "./StudioShellLayout.setup";

   // Apply mocks (MUST be before component imports)
   vi.mock("../../contexts/TelemetryContext", () => mockImplementations.TelemetryContext);
   vi.mock("../../hooks/useNudges", () => mockImplementations.useNudges);
   // ... add all required mocks

   // Import component AFTER mocks
   import { StudioShellLayout } from "../StudioShellLayout";
   ```

3. **Add the standard test lifecycle**:
   ```typescript
   describe("StudioShellLayout - <Category>", () => {
     beforeEach(() => {
       resetAllMocks();
       resetPanelCounter();
     });

     afterEach(async () => {
       cleanup();
       vi.clearAllMocks();
       vi.restoreAllMocks();
       await act(async () => {
         await flushPromises();
       });
     });

     // Your tests here
   });
   ```

## Running Tests

```bash
# Run all split tests
npm test -- --run src/layout/__tests__/

# Run specific category
npm test -- --run src/layout/__tests__/StudioShellLayout.rbac.test.tsx

# Run with coverage
npm test -- --run src/layout/__tests__/ --coverage
```

## Memory Optimization

The split test pattern prevents OOM issues by:

1. **Smaller per-file memory footprint**: Each file loads independently
2. **Shared mock infrastructure**: Reduces duplicate object creation
3. **Proper cleanup**: `afterEach` ensures no memory leaks
4. **Parallel execution**: Files can run in separate Vitest workers

## Migration Guide

To migrate tests from the main `StudioShellLayout.test.tsx`:

1. Identify the describe block to migrate
2. Copy the tests to a new split file
3. Ensure all required mocks are applied
4. Use `createTestStore()` or `createStoreWithPersona()` for store setup
5. Replace inline mock state with shared `mockNudgesState`, etc.
6. Run and verify tests pass
7. (Optional) Remove migrated tests from main file

## Troubleshooting

### Test IDs Not Found

The mock setup provides limited test IDs. Available IDs include:
- `studio-shell` - Main shell container
- `activity-bar` - Navigation bar
- `status-bar` - Bottom status bar
- `nav-chat`, `nav-workflows`, `nav-admin`, etc. - Navigation buttons
- `panel-group-<direction>` - Panel groups

If a test ID isn't available, either:
- Add it to the mock in `StudioShellLayout.setup.ts`
- Test at a higher level (e.g., check `studio-shell` exists)

### Persona-Specific Tests

Use `createStoreWithPersona()` for persona-specific tests:
```typescript
// Admin sees all navigation
renderWithProviders(createStoreWithPersona("admin"));
expect(screen.getByTestId("nav-admin")).toBeInTheDocument();

// User doesn't see admin nav
renderWithProviders(createStoreWithPersona("user"));
expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();
```

### Feature Flag Tests

Configure feature flags via `mockFns.useFeatureFlag`:
```typescript
mockFns.useFeatureFlag.mockImplementation((flag: string) => {
  if (flag === "nudges") return true;
  return false;
});
```
