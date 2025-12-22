# Contributing to Studio Frontend

This guide covers the development workflow, testing patterns, and documentation structure for the Studio Frontend.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Type check
npm run typecheck

# Lint
npm run lint
```

## Project Structure

```
src/
├── ai/                 # AI features (suggestions, command palette)
├── canvas/             # Canvas workspace components
├── compliance/         # Compliance dashboard panels
├── components/         # Shared UI components
├── contexts/           # React contexts
├── conversation/       # Chat/conversation components
├── help/               # Help and accessibility
├── hooks/              # Custom React hooks
├── layout/             # Layout components (HybridShell, TopBar, etc.)
├── pages/              # Page components
├── router/             # React Router configuration
├── store/              # Redux store and slices
├── types/              # TypeScript types
└── utils/              # Utility functions

e2e/                    # Playwright E2E tests
.metrics/               # Performance metrics (Lighthouse, etc.)
```

## Testing

### Testing Documentation

**IMPORTANT**: Before writing tests, read these guides:

| Guide | Location | Purpose |
|-------|----------|---------|
| **Testing Patterns** | `docs-internal/frontend/testing/TESTING_PATTERNS.md` | Provider wrappers, mock factories, common scenarios |
| **OOM Prevention** | `docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md` | Critical patterns to avoid memory issues |

### Test Types

#### Unit Tests (Vitest)

Fast, isolated tests for components and utilities.

```bash
npm test              # Watch mode
npm run test:run      # Single run
npm run test:coverage # With coverage
```

**Location**: Colocated with source files (e.g., `Component.test.tsx`)

#### E2E Tests (Playwright)

Full user journey tests with mocked or real backend.

```bash
npm run test:e2e         # Run all
npm run test:e2e:ui      # Interactive mode
npm run test:e2e:headed  # Show browser
```

**Location**: `e2e/*.spec.ts`

### OOM Prevention (Critical)

Some components have circular dependencies that cause Vitest to run out of memory. **Always follow these patterns**:

#### Safe Pattern: Mock API Before Imports

```typescript
// ✅ CORRECT: vi.mock is hoisted and runs before imports
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    useGetSomeQuery: () => mockUseGetSomeQuery(),
  };
});

// Import AFTER mock
import { SomeComponent } from "./SomeComponent";
```

#### Safe Pattern: Minimal Test Store

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

#### High-Risk Dependencies

These modules trigger heavy initialization and should ALWAYS be mocked:

| Module | Risk Level | Why It's Heavy |
|--------|------------|----------------|
| `../api` / `../../api` | **CRITICAL** | RTK Query endpoints, middleware, cache |
| `../store/index` | **CRITICAL** | Full Redux store with all reducers + api |
| `reactflow` / `@xyflow/react` | **HIGH** | React Flow canvas, nodes, edges |
| `react-resizable-panels` | **MEDIUM** | Layout calculations, ResizeObserver |

See `docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md` for complete patterns.

### Test Checklist

Before committing a new test file:

- [ ] All `../api` imports have corresponding `vi.mock("../api")` calls
- [ ] `vi.mock()` calls appear BEFORE import statements
- [ ] Test store only includes reducers actually needed
- [ ] Heavy libraries (reactflow, react-resizable-panels) are mocked
- [ ] No direct `import { store } from "../store"` usage
- [ ] `beforeEach(() => vi.clearAllMocks())` is present
- [ ] Test file runs in under 60 seconds with no memory warnings

### Verify OOM Safety

```bash
# Run single test file with timeout
timeout 60 npm run test -- --run path/to/your.test.tsx

# Check memory usage (should complete with 512MB heap)
NODE_OPTIONS="--max-old-space-size=512" npm run test -- --run path/to/your.test.tsx
```

## Documentation Structure

### Where Documentation Belongs

| Type | Location | Format |
|------|----------|--------|
| User-facing docs | `docs/` (root) | `.mdx` (Mintlify) |
| Internal dev docs | `docs-internal/frontend/` | `.md` |
| Testing guides | `docs-internal/frontend/testing/` | `.md` |
| Metrics data | `.metrics/` | `.json` |

**DO NOT** put documentation in:
- ❌ `src/.../docs/` - This folder should not exist
- ❌ `docs/internal/` - Use `docs-internal/` instead

### Internal Documentation

Frontend-specific internal docs are in `docs-internal/frontend/`:

- `FRONTEND_API_AUDIT.md` - API endpoint usage
- `STATE_MANAGEMENT_PATTERNS.md` - Redux patterns
- `MCP_CONNECTIONS_FEATURE.md` - MCP connections spec
- `STORAGE_MIGRATION.md` - LocalStorage migration
- `testing/TESTING_PATTERNS.md` - Testing patterns
- `testing/TESTING_OOM_PREVENTION.md` - OOM prevention

## Code Style

### Component Structure

```typescript
// 1. Imports (external, then internal)
import { useState } from "react";
import { useAppDispatch } from "../store/hooks";

// 2. Types/Interfaces
interface MyComponentProps {
  title: string;
  onClose?: () => void;
}

// 3. Component
export function MyComponent({ title, onClose }: MyComponentProps) {
  // Hooks first
  const dispatch = useAppDispatch();
  const [isOpen, setIsOpen] = useState(false);

  // Handlers
  const handleClick = useCallback(() => {
    setIsOpen(true);
  }, []);

  // Render
  return (
    <div data-testid="my-component">
      {title}
    </div>
  );
}
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `MyComponent.tsx` |
| Hooks | camelCase with `use` prefix | `useMyHook.ts` |
| Utils | camelCase | `myUtil.ts` |
| Tests | Same name + `.test` | `MyComponent.test.tsx` |
| E2E Tests | kebab-case + `.spec` | `my-feature.spec.ts` |

### Test IDs

Always add `data-testid` for elements that need testing:

```typescript
<button data-testid="save-button">Save</button>
<div data-testid="artifact-tab-artifact-1">...</div>
```

## Feature Flag Gating

### Overview

AI components and experimental features are gated behind feature flags to enable gradual rollouts. Always check feature flags before rendering AI components.

### Available Feature Flags

| Flag | Purpose | Components Gated |
|------|---------|------------------|
| `canvas_ai_palette` | AI command palette and edit overlay | `AICommandPalette`, `AIEditOverlay` |
| `ai_suggestions` | AI-powered suggestions | `InlineSuggestions`, `BackgroundAgentPanel`, `AgentTaskQueue` |

### Usage in Components

```typescript
import { useFeatureFlag } from "../contexts/FeatureFlagContext";

export function MyComponent() {
  // Get feature flag value
  const aiSuggestionsEnabled = useFeatureFlag("ai_suggestions");

  return (
    <div>
      {/* Only render AI features when flag is enabled */}
      {aiSuggestionsEnabled && (
        <InlineSuggestions suggestions={suggestions} />
      )}
    </div>
  );
}
```

### Mocking in Tests

When testing components that use feature flags, mock the `useFeatureFlag` hook:

```typescript
// Mock useFeatureFlag to enable AI components in tests
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => {
    // Enable AI feature flags for testing
    if (flag === "canvas_ai_palette" || flag === "ai_suggestions") {
      return true;
    }
    return false;
  },
}));
```

### Test Infrastructure

Feature flags are configured in:

| File | Purpose |
|------|---------|
| `.env.test` | Default test environment values |
| `docker-compose.test.yml` | Integration/E2E test containers |

Example from `.env.test`:
```bash
FF_CANVAS_AI_PALETTE=true        # Phase 4: AI command palette
FF_ENABLE_AI_SUGGESTIONS=true    # Phase 4: AI suggestions
```

### Best Practices

1. **Always check the flag before rendering**: Don't render AI components unconditionally
2. **Gate keyboard shortcuts too**: If a shortcut triggers an AI feature, check the flag first
3. **Mock flags in tests**: Use `vi.mock()` to control flag values in unit tests
4. **Update infrastructure**: When adding new flags, update `.env.test` and `docker-compose.test.yml`

## Type Organization

### Consolidated Type Modules

Complex features with types shared across multiple files should have dedicated type modules in `src/types/`:

| Module | Purpose |
|--------|---------|
| `types/api.ts` | API request/response types |
| `types/hitl.ts` | Human-in-the-Loop (HITL) types for agent approval/clarification |
| `types/session.ts` | Session and message types |
| `types/workflow.ts` | Workflow execution types |

### Type Aliasing Convention

When the same conceptual type has different shapes for different layers (UI vs API), use clear naming:

```typescript
// In types/hitl.ts

// UI-layer type (used by dialog components)
export interface ClarificationUIResponse {
  request_id: string;
  value?: string;              // Text input value
  selected_option_id?: string; // Selected option ID
  confirmed?: boolean;
  responded_by: string;        // For attribution in UI
}

// API-layer type (used by hooks for API calls)
export interface ClarificationAPIResponse {
  request_id: string;
  response_type: "choice" | "text" | "confirm"; // Explicit discriminator
  selected_option?: string;
  text_response?: string;
  confirmed?: boolean;
}

// Conversion function
export function convertUIResponseToAPIResponse(
  uiResponse: ClarificationUIResponse
): ClarificationAPIResponse { ... }
```

### Naming Conventions for Types

| Suffix | Purpose | Example |
|--------|---------|---------|
| `*UIResponse` | Response type for UI layer | `ClarificationUIResponse` |
| `*APIResponse` | Response type for API layer | `ClarificationAPIResponse` |
| `*Payload` | WebSocket message data | `ApprovalRequiredPayload` |
| `*Request` | Request/input data | `AgentApprovalRequest` |

### Avoiding Type Conflicts

When two modules export types with the same name:

**Option 1: Import with alias (temporary fix)**
```typescript
import { type ClarificationResponse as DialogResponse } from "../components/Admin/ClarificationDialog";
import type { ClarificationResponse as HookResponse } from "../hooks/useHITLDialogs";
```

**Option 2: Consolidate into shared module (preferred)**
```typescript
// Move types to types/hitl.ts
import {
  type ClarificationUIResponse,
  type ClarificationAPIResponse,
  convertUIResponseToAPIResponse,
} from "../types/hitl";
```

### Re-exporting for Backwards Compatibility

When consolidating types, re-export from the original location to avoid breaking imports:

```typescript
// In hooks/useHITLDialogs.ts
import { type ClarificationAPIResponse } from "../types/hitl";

// Re-export for backwards compatibility
export type ClarificationResponse = ClarificationAPIResponse;
```

## Pull Request Checklist

- [ ] Tests pass: `npm run test:run`
- [ ] Type check passes: `npm run typecheck`
- [ ] Lint passes: `npm run lint`
- [ ] No OOM issues in new tests
- [ ] Documentation updated if needed
- [ ] E2E tests added for user-facing features

## Getting Help

- **Testing issues**: Check `docs-internal/frontend/testing/`
- **Architecture questions**: Check `docs-internal/frontend/STATE_MANAGEMENT_PATTERNS.md`
- **API contracts**: Check `docs-internal/frontend/FRONTEND_API_AUDIT.md`
