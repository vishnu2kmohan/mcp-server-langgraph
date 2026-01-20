# Frontend Testing Patterns

This document describes the testing patterns used in the Studio Frontend codebase for AI-Native Studio Canvas components.

## Table of Contents

- [Test Setup](#test-setup)
- [Provider Wrappers](#provider-wrappers)
- [Mocking Patterns](#mocking-patterns)
  - [Mocking React Router Loaders](#mocking-react-router-loaders)
  - [Mocking Custom Hooks](#mocking-custom-hooks)
  - [Mocking useRevalidator](#mocking-userevalidator-react-router-data-router)
  - [Mocking Redux Actions](#mocking-redux-actions)
  - [Mocking Fetch API](#mocking-fetch-api)
  - [URL-Aware Mock Pattern](#url-aware-mock-pattern-selective-error-injection)
  - [Mocking localStorage](#mocking-localstorage)
- [Common Test Scenarios](#common-test-scenarios)
  - [Testing Concurrent Operation Prevention](#testing-concurrent-operation-prevention)
  - [Testing Cleanup on Unmount](#testing-cleanup-on-unmount)
  - [Testing Status Indicators](#testing-status-indicators)
- [Best Practices](#best-practices)
- [Additional Patterns (2025-01)](#additional-patterns-2025-01)
  - [Mocking useSafeRouteLoaderData](#mocking-usesaferouteloaderdata)
  - [Mocking authenticatedFetch](#mocking-authenticatedfetch)
  - [Redux Provider for AIEmptyState Hook](#redux-provider-for-aiemptystate-hook)
  - [ARIA Role for Toggle Components](#aria-role-for-toggle-components)
  - [RTK Query Hook Mocking](#rtk-query-hook-mocking-with-usegetemptystatesuggestionsmutation)

---

## Test Setup

### Standard Test Imports

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter, Routes, Route } from "react-router";
import React from "react";
```

### Store Factory Pattern

Create test stores with minimal configuration:

```typescript
const createTestStore = (initialState?: Partial<RootState>) => {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
      session: sessionReducer,
      // Add only the slices your component needs
    },
    preloadedState: initialState,
  });
};
```

### Mock Factory Pattern

Create reusable mock factories for test data:

```typescript
const createMockArtifact = (
  overrides: Partial<CanvasArtifact> = {},
): CanvasArtifact => ({
  id: "artifact-1",
  type: "code",
  title: "Test Artifact",
  sessionId: "session-123",
  version: 1,
  content: "console.log('hello');",
  contentType: "code",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  ...overrides,
});

const createMockMessage = (
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id: "msg-1",
  role: "user",
  content: "Hello, how are you?",
  timestamp: Date.now(),
  ...overrides,
});
```

---

## Provider Wrappers

### Basic Wrapper (Redux Only)

```typescript
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
};
```

### Full Wrapper (Redux + Router + Telemetry)

For components that use routing and telemetry:

```typescript
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <TelemetryProvider>
          <MemoryRouter>
            <Routes>
              <Route path="/" element={<>{children}</>} />
            </Routes>
          </MemoryRouter>
        </TelemetryProvider>
      </Provider>
    );
  };
};
```

### Nested Routes Wrapper

For testing components with `<Outlet />`:

```typescript
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>
          <Routes>
            <Route
              path="/"
              element={
                <div data-testid="router-wrapper">
                  {children}
                  <Outlet />
                </div>
              }
            >
              <Route
                path="nested"
                element={<div data-testid="nested-route">Nested</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      </Provider>
    );
  };
};
```

---

## Mocking Patterns

### Mocking React Router Loaders

```typescript
const mockLoaderData: ChatLoaderData = {
  sessionId: "session-123",
  messages: [],
  artifacts: [],
};

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockLoaderData;
      }
      return undefined;
    }),
  };
});
```

### Mocking Custom Hooks

```typescript
const mockRevalidate = vi.fn();
vi.mock("../hooks/useMessageRevalidation", () => ({
  useMessageRevalidation: () => ({
    revalidateMessages: mockRevalidate,
  }),
}));
```

### Mocking useRevalidator (React Router Data Router)

The `useRevalidator` hook from React Router requires a data router context. When testing
components that use this hook (commonly for refreshing loader data after mutations),
you need to mock it in your react-router mock block.

**The Problem:**
Components using `useRevalidator()` will throw an error if rendered outside a data
router context:
```
Error: useRevalidator must be used within a data router
```

**The Solution:**
Add `useRevalidator` to your react-router mock:

```typescript
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockLoaderData;
      }
      return undefined;
    }),
    // Mock useRevalidator to avoid data router requirement
    useRevalidator: vi.fn(() => ({
      revalidate: vi.fn(),
      state: "idle", // "idle" | "loading"
    })),
  };
});
```

**Testing revalidation behavior:**

```typescript
describe("Revalidation", () => {
  it("should call revalidate after successful save", async () => {
    const mockRevalidate = vi.fn();
    const useRevalidatorMock = vi.mocked(useRevalidator);
    useRevalidatorMock.mockReturnValue({
      revalidate: mockRevalidate,
      state: "idle",
    });

    const user = userEvent.setup();
    const store = createTestStore();
    render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });

    // Trigger save action
    await user.click(screen.getByTestId("save-button"));

    await waitFor(() => {
      expect(mockRevalidate).toHaveBeenCalled();
    });
  });

  it("should show loading state during revalidation", () => {
    const useRevalidatorMock = vi.mocked(useRevalidator);
    useRevalidatorMock.mockReturnValue({
      revalidate: vi.fn(),
      state: "loading", // Simulate ongoing revalidation
    });

    const store = createTestStore();
    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
  });
});
```

**Full example (ConnectedCanvasPanel):**

See `src/canvas/ConnectedCanvasPanel.test.tsx` and `src/layout/StudioShellLayout.test.tsx`
for complete working examples of useRevalidator mocking patterns.

### Mocking Redux Actions

When testing thunks or complex actions:

```typescript
vi.mock("../store/slices/sessionSlice", async () => {
  const actual = await vi.importActual("../store/slices/sessionSlice");
  return {
    ...actual,
    sendMessage: vi.fn((content: string) => ({
      type: "session/sendMessage",
      payload: content,
    })),
  };
});
```

### Mocking Fetch API

For components that make direct fetch calls (e.g., save operations):

```typescript
describe("Save Operations", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: () => Promise.resolve({ id: "artifact-1", version: 2 }),
      } as Response)
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should handle successful save", async () => {
    // Test save operation
    await user.click(screen.getByTestId("save-button"));

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/artifacts/"),
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("should handle HTTP errors", async () => {
    vi.spyOn(global, "fetch").mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      } as Response)
    );

    await user.click(screen.getByTestId("save-button"));

    await waitFor(() => {
      expect(screen.getByText(/error.*500/i)).toBeInTheDocument();
    });
  });

  it("should handle network errors", async () => {
    vi.spyOn(global, "fetch").mockImplementationOnce(() =>
      Promise.reject(new Error("Network error"))
    );

    await user.click(screen.getByTestId("save-button"));

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });
});
```

**Testing Authorization Headers:**

```typescript
it("should include authorization header when token exists", async () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
    if (key === "auth_token") return "test-token-123";
    return null;
  });

  await user.click(screen.getByTestId("save-button"));

  expect(global.fetch).toHaveBeenCalledWith(
    expect.any(String),
    expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: "Bearer test-token-123",
      }),
    })
  );
});
```

**URL-Aware Mock Pattern (Selective Error Injection):**

When components make multiple API calls (e.g., fetching suggestions AND saving artifacts), use URL-aware mocks to inject errors only for specific endpoints:

```typescript
it("should show error status when save fails with HTTP error", async () => {
  // Mock failed response ONLY for artifact save calls
  vi.spyOn(global, "fetch").mockImplementation((url) => {
    const urlStr = typeof url === "string" ? url : url.toString();

    // Return error only for artifact save endpoint
    if (urlStr.includes("/api/v1/artifacts/")) {
      return Promise.resolve({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      } as Response);
    }

    // Return success for other calls (suggestions, sessions, etc.)
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ suggestions: [] }),
    } as Response);
  });

  await user.click(screen.getByTestId("save-button"));

  await waitFor(() => {
    expect(screen.getByTestId("save-status-indicator")).toHaveTextContent(/500|error|fail/i);
  });
});

it("should show error status when save throws exception", async () => {
  // Mock network error ONLY for artifact save calls
  vi.spyOn(global, "fetch").mockImplementation((url) => {
    const urlStr = typeof url === "string" ? url : url.toString();

    if (urlStr.includes("/api/v1/artifacts/")) {
      return Promise.reject(new Error("Network error"));
    }

    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ suggestions: [] }),
    } as Response);
  });

  await user.click(screen.getByTestId("save-button"));

  await waitFor(() => {
    expect(screen.getByTestId("save-status-indicator")).toHaveTextContent(/network error|error|fail/i);
  });
});
```

> **Why URL-Aware Mocks?** Using `mockImplementationOnce` fails when components make multiple fetch calls (e.g., AI suggestions + save operations). The first call consumes the mock, leaving subsequent calls with unexpected behavior. URL-aware mocks ensure errors are injected only where intended.

### Mocking localStorage

```typescript
describe("localStorage Integration", () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
      const storage: Record<string, string> = {
        auth_token: "test-token",
        user_preferences: JSON.stringify({ theme: "dark" }),
      };
      return storage[key] ?? null;
    });

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
});
```

---

## Common Test Scenarios

### Testing Component Rendering

```typescript
describe("Rendering", () => {
  it("should render with data-testid", () => {
    const store = createTestStore();
    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("my-component")).toBeInTheDocument();
  });

  it("should apply custom className", () => {
    const store = createTestStore();
    render(<MyComponent className="custom-class" />, {
      wrapper: createWrapper(store),
    });

    expect(screen.getByTestId("my-component")).toHaveClass("custom-class");
  });
});
```

### Testing Redux Integration

```typescript
describe("Redux Integration", () => {
  it("should dispatch action on user interaction", async () => {
    const user = userEvent.setup();
    const store = createTestStore();

    render(<MyComponent />, { wrapper: createWrapper(store) });

    await user.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => {
      const state = store.getState();
      expect(state.mySlice.someValue).toBe(expectedValue);
    });
  });
});
```

### Testing Loader Data Integration

```typescript
describe("Loader Data Integration", () => {
  beforeEach(() => {
    // Reset mock data before each test
    mockLoaderData.artifacts = [];
  });

  it("should display data from loader", () => {
    mockLoaderData.artifacts = [
      createMockArtifact({ id: "art-1", title: "Test" }),
    ];

    const store = createTestStore();
    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("artifact-tab-art-1")).toBeInTheDocument();
  });

  it("should handle empty data", () => {
    mockLoaderData.artifacts = [];

    const store = createTestStore();
    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByText(/no artifacts/i)).toBeInTheDocument();
  });
});
```

### Testing User Interactions

```typescript
describe("User Interactions", () => {
  it("should send message when form is submitted", async () => {
    const user = userEvent.setup();
    const store = createTestStore();

    render(<MyComponent />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "Test message");

    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockRevalidate).toHaveBeenCalled();
    });
  });

  it("should toggle menu on keyboard shortcut", async () => {
    const user = userEvent.setup();
    const store = createTestStore();

    render(<MyComponent />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "/");

    await waitFor(() => {
      expect(screen.getByTestId("command-menu")).toBeInTheDocument();
    });
  });
});
```

### Testing Async Operations

```typescript
describe("Async Operations", () => {
  it("should show loading state during fetch", async () => {
    const store = createTestStore({
      session: { isLoading: true },
    });

    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
  });

  it("should handle errors gracefully", async () => {
    const store = createTestStore({
      session: { error: "Network error" },
    });

    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByText(/network error/i)).toBeInTheDocument();
  });
});
```

### Testing Concurrent Operation Prevention

Use the **slow promise pattern** to test that concurrent operations are prevented:

```typescript
describe("Concurrent Operation Prevention", () => {
  it("should prevent concurrent saves when already saving", async () => {
    const user = userEvent.setup();

    // Create a controllable promise to simulate slow operation
    let resolveFirstSave: (value: Response) => void;
    const slowFetch = new Promise<Response>((resolve) => {
      resolveFirstSave = resolve;
    });

    const fetchMock = vi.spyOn(global, "fetch")
      .mockImplementationOnce(() => slowFetch)
      .mockImplementation(() =>
        Promise.resolve({ ok: true, status: 200 } as Response)
      );

    render(<MyComponent />, { wrapper: createWrapper(store) });

    // Enter edit mode and make changes
    await user.click(screen.getByTestId("edit-button"));
    await user.type(screen.getByTestId("editor"), "new content");

    // Click save - this starts the first (slow) save
    const saveButton = screen.getByTestId("save-button");
    await user.click(saveButton);

    // Click save again while first save is in progress
    await user.click(saveButton);
    await user.click(saveButton);

    // First save is still pending - should only have 1 fetch call
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Complete the first save
    resolveFirstSave!({ ok: true, status: 200 } as Response);

    // Verify only 1 save was made (concurrent saves were prevented)
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });
});
```

**Key points:**
- Use `let resolveFirstSave: (value: Response) => void` to control when the promise resolves
- The slow promise simulates an in-flight request
- Clicking save multiple times while the first is pending should not trigger additional requests
- Only resolve the promise after verifying the guard is working

### Testing Cleanup on Unmount

Use `vi.useFakeTimers` to test timeout cleanup and prevent "act" warnings:

```typescript
describe("Cleanup on Unmount", () => {
  it("should cleanup save timeout on unmount", async () => {
    // Enable fake timers with time advancement
    vi.useFakeTimers({ shouldAdvanceTime: true });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const store = createTestStore();

    const { unmount } = render(<MyComponent />, {
      wrapper: createWrapper(store),
    });

    // Trigger save to start timeout
    await user.click(screen.getByTestId("edit-button"));
    await user.type(screen.getByTestId("editor"), "content");
    await user.click(screen.getByTestId("save-button"));

    // Unmount before timeout completes
    unmount();

    // Advance timers past the cleanup timeout
    await vi.advanceTimersByTimeAsync(5000);

    // Test passes if no errors are thrown (cleanup worked)
    expect(true).toBe(true);

    // Restore real timers
    vi.useRealTimers();
  });
});
```

**Important considerations:**
- Use `{ shouldAdvanceTime: true }` for components with mixed async/timer behavior
- Configure userEvent with `{ advanceTimers: vi.advanceTimersByTime }`
- Always call `vi.useRealTimers()` in cleanup to avoid affecting other tests
- Use `vi.advanceTimersByTimeAsync()` for async timer advancement

### Testing Status Indicators

Test save status transitions (idle → saving → saved/error):

```typescript
describe("Save Status Indicators", () => {
  it("should show saving status indicator when save is in progress", async () => {
    const user = userEvent.setup();

    // Create slow promise to observe intermediate state
    let resolvePromise: (value: Response) => void;
    vi.spyOn(global, "fetch").mockImplementationOnce(
      () => new Promise((resolve) => { resolvePromise = resolve; })
    );

    render(<MyComponent />, { wrapper: createWrapper(store) });

    await user.click(screen.getByTestId("edit-button"));
    await user.type(screen.getByTestId("editor"), "content");
    await user.click(screen.getByTestId("save-button"));

    // Check saving indicator appears
    await waitFor(() => {
      expect(screen.getByText(/saving/i)).toBeInTheDocument();
    });

    // Complete save
    resolvePromise!({ ok: true, status: 200 } as Response);
  });

  it("should show saved status after successful save", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve({ ok: true, status: 200 } as Response)
    );

    render(<MyComponent />, { wrapper: createWrapper(store) });

    await user.click(screen.getByTestId("edit-button"));
    await user.type(screen.getByTestId("editor"), "content");
    await user.click(screen.getByTestId("save-button"));

    await waitFor(() => {
      expect(screen.getByText(/saved/i)).toBeInTheDocument();
    });
  });

  it("should show error status when save fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve({ ok: false, status: 500 } as Response)
    );

    render(<MyComponent />, { wrapper: createWrapper(store) });

    await user.click(screen.getByTestId("edit-button"));
    await user.type(screen.getByTestId("editor"), "content");
    await user.click(screen.getByTestId("save-button"));

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
```

---

## Best Practices

### 1. Use Specific Queries

Prefer specific queries over generic text matches to avoid multiple element errors:

```typescript
// Bad - may find multiple elements
expect(screen.getByText("Title")).toBeInTheDocument();

// Good - uses test ID for specificity
expect(screen.getByTestId("artifact-tab-art-1")).toBeInTheDocument();

// Good - when multiple elements are expected
expect(screen.getAllByText("Title").length).toBeGreaterThan(0);
```

### 2. Reset Mocks and State in beforeEach

```typescript
beforeEach(() => {
  vi.clearAllMocks();
  // Reset mutable mock data
  mockLoaderData.sessionId = "session-123";
  mockLoaderData.messages = [];
  mockLoaderData.artifacts = [];
});
```

### 3. Use Proper waitFor for Async Assertions

```typescript
// Bad - may fail due to timing
expect(store.getState().canvas.selectedId).toBe("art-1");

// Good - waits for async updates
await waitFor(() => {
  expect(store.getState().canvas.selectedId).toBe("art-1");
});
```

### 4. Test Accessibility

```typescript
describe("Accessibility", () => {
  it("should have accessible buttons", () => {
    render(<MyComponent />, { wrapper: createWrapper(store) });

    const button = screen.getByRole("button", { name: /submit/i });
    expect(button).toHaveAttribute("type", "button");
    expect(button).toBeVisible();
  });

  it("should have proper aria labels", () => {
    render(<MyComponent />, { wrapper: createWrapper(store) });

    expect(screen.getByRole("textbox")).toHaveAttribute(
      "aria-label",
      "Type your message",
    );
  });
});
```

### 5. Group Related Tests

```typescript
describe("MyComponent", () => {
  describe("Rendering", () => {
    // Tests for initial render state
  });

  describe("Loader Data Integration", () => {
    // Tests for React Router loader data
  });

  describe("User Interactions", () => {
    // Tests for clicks, typing, etc.
  });

  describe("Redux Integration", () => {
    // Tests for store updates
  });

  describe("Accessibility", () => {
    // Tests for a11y requirements
  });
});
```

### 6. Use Type-Safe Mock Factories

```typescript
interface MockOptions<T> extends Partial<T> {}

const createMock = <T extends object>(
  defaults: T,
  overrides: MockOptions<T> = {},
): T => ({
  ...defaults,
  ...overrides,
});
```

---

## Test File Structure

```
src/
├── canvas/
│   ├── CanvasWorkspace.tsx
│   ├── CanvasWorkspace.test.tsx      # Co-located tests
│   ├── ConnectedCanvasPanel.tsx
│   └── ConnectedCanvasPanel.test.tsx
├── conversation/
│   ├── ConversationPanel.tsx
│   ├── ConversationPanel.test.tsx
│   └── ConnectedConversationPanel.test.tsx
└── test-utils.tsx                     # Shared test utilities
```

## Coverage Targets

| Category | Minimum | Target |
|----------|---------|--------|
| Redux Slices | 95% | 100% |
| Connected Components | 80% | 90% |
| UI Components | 80% | 85% |
| Hooks | 90% | 95% |
| Utilities | 95% | 100% |

---

## Related Documentation

- [TDD Guidelines](./TDD.md)
- [Component Architecture](./ARCHITECTURE.md)
- [React Router Integration](./ROUTER.md)

## Example Test Files

These test files demonstrate the patterns documented above:

| File | Patterns Demonstrated |
|------|----------------------|
| `src/canvas/ConnectedCanvasPanel.test.tsx` | Fetch mocking, save status indicators, concurrent operation prevention, cleanup on unmount, localStorage mocking |
| `src/canvas/CanvasWorkspace.test.tsx` | Redux integration, artifact selection, AI edit overlay |
| `src/layout/StudioShellLayout.test.tsx` | useRevalidator mocking, feature flag integration |
| `src/pages/MCPPage.test.tsx` | Tab navigation, search filtering, Redux state |
| `src/components/Layout/ActivityLog.test.tsx` | Notification types, compact mode, maxItems limiting |
| `src/components/Artifacts/MDXArtifact.test.tsx` | Accordion expansion, tab switching, interactive components |
| `src/pages/ArtifactsPage.test.tsx` | useSafeRouteLoaderData mocking, Redux Provider with AIEmptyState |
| `src/pages/__tests__/WorkflowsPage.features.test.tsx` | authenticatedFetch mocking, hoisted mock pattern |

---

## Additional Patterns (2025-01)

### Mocking useSafeRouteLoaderData

When components use `useSafeRouteLoaderData` instead of `useRouteLoaderData`, mock the hook directly:

```typescript
// WRONG: Mocking useRouteLoaderData won't work
vi.mock("react-router", async (importOriginal) => {
  const actual = (await importOriginal()) as object;
  return {
    ...actual,
    useRouteLoaderData: vi.fn(),  // Component doesn't use this
  };
});

// CORRECT: Mock the actual hook used by the component
const mockUseSafeRouteLoaderData = vi.fn();

vi.mock("../hooks/useSafeRouteLoaderData", () => ({
  useSafeRouteLoaderData: () => mockUseSafeRouteLoaderData(),
  useIsDataRouter: () => true,
}));

// In beforeEach:
mockUseSafeRouteLoaderData.mockReturnValue({
  artifacts: testArtifacts,
  total: 3,
});
```

**Example file:** `src/pages/ArtifactsPage.test.tsx`

### Mocking authenticatedFetch

Components using `authenticatedFetch` require direct module mocking, NOT `global.fetch` assignment:

```typescript
// WRONG: Won't intercept calls through authenticatedFetch wrapper
global.fetch = vi.fn();

// CORRECT: Mock the authenticatedFetch module
const mockAuthenticatedFetch = vi.hoisted(() => vi.fn());

vi.mock("../../utils/authenticatedFetch", () => ({
  authenticatedFetch: mockAuthenticatedFetch,
}));

// In tests:
mockAuthenticatedFetch.mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ code: "test" }),
});
```

**Example file:** `src/pages/__tests__/WorkflowsPage.features.test.tsx`

### Redux Provider for AIEmptyState Hook

Components using `useAIEmptyState` require Redux Provider with `persona` and `session` slices:

```typescript
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import personaReducer from "../../store/slices/personaSlice";
import sessionReducer from "../../store/slices/sessionSlice";

const createTestStore = () =>
  configureStore({
    reducer: {
      persona: personaReducer,
      session: sessionReducer,
    },
    preloadedState: {
      persona: {
        persona: "developer" as const,
        subPersona: null,
        username: "test-user",
        visibleModules: [],
        error: null,
      },
      session: {
        currentSessionId: null,
        sessions: {},
        recentSessions: [],
        isLoading: false,
        error: null,
      },
    },
  });

export const renderWithRouter = (component: React.ReactNode) => {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <MemoryRouter>{component}</MemoryRouter>
    </Provider>,
  );
};
```

**Example file:** `src/pages/__tests__/ProjectsPage.fixtures.tsx`

### ARIA Role for Toggle Components

The `Toggle` component uses `role="switch"` (not `role="checkbox"`):

```typescript
// WRONG: Toggle doesn't render a checkbox
expect(screen.getByRole("checkbox", { name: /enable verification/i })).toBeInTheDocument();

// CORRECT: Toggle uses switch role with aria-checked
const toggle = screen.getByRole("switch", { name: /enable verification/i });
expect(toggle).toHaveAttribute("aria-checked", "true");

// To simulate toggle:
fireEvent.click(toggle);
expect(toggle).toHaveAttribute("aria-checked", "false");
```

**Example file:** `src/pages/AgentsPage.test.tsx`

### RTK Query Hook Mocking with useGetEmptyStateSuggestionsMutation

Many page components use `useGetEmptyStateSuggestionsMutation` via `AIEmptyState`. Always mock it:

```typescript
vi.mock("../../api", () => ({
  useGetEmptyStateSuggestionsMutation: () => [vi.fn(), { isLoading: false }],
  // ... other hooks
}));
```

See `scripts/add-missing-api-mocks.sh` for bulk-adding this mock to test files.
