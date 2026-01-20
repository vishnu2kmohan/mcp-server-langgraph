# Hook Integration Patterns

**Last Updated**: 2026-01-12
**Status**: Living Document

This document describes patterns for integrating React hooks with components in the DevTools and observability features.

---

## Overview

The frontend uses a layered hook architecture:

1. **Context Hooks** - Provide shared state across component trees
2. **Feature Hooks** - Encapsulate specific feature logic
3. **Persistence Hooks** - Handle data persistence via callbacks
4. **Integration Hooks** - Cross-component communication

---

## Pattern 1: Persistence Callbacks

Components accept optional callback props to sync state changes with parent components or external storage.

### Example: TimelineBar Persistence

```tsx
// TimelineBarProps
interface TimelineBarProps {
  onBookmarkAdd?: (bookmark: { id: string; time: number; label: string }) => void;
  onBookmarkRemove?: (id: string) => void;
  onPlaybackSpeedChange?: (speed: number) => void;
}

// Usage in component
const handleAddBookmark = useCallback(() => {
  const label = `Bookmark ${timeline.bookmarks.length + 1}`;
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  timeline.addBookmark(label);
  onBookmarkAdd?.({ id, time: timeline.currentTime, label });
}, [timeline, onBookmarkAdd]);
```

### Pattern Benefits

- Parent components can persist to localStorage/Redux/API
- Component remains stateless for testing
- Callbacks are optional - component works standalone

### Testing Pattern

```tsx
it("should call onBookmarkAdd when bookmark is added", () => {
  const onBookmarkAdd = vi.fn();
  renderWithProvider(
    <TimelineBar showBookmarkButton onBookmarkAdd={onBookmarkAdd} />,
    { initialEvents },
  );

  fireEvent.click(screen.getByRole("button", { name: /bookmarks/i }));
  fireEvent.click(screen.getByRole("menuitem", { name: /add bookmark/i }));

  expect(onBookmarkAdd).toHaveBeenCalledWith(
    expect.objectContaining({
      id: expect.any(String),
      time: expect.any(Number),
      label: expect.stringMatching(/Bookmark \d+/),
    }),
  );
});
```

---

## Pattern 2: Cross-Panel Navigation (Trace Linking)

The `useTraceLinking` hook enables navigation between panels (e.g., clicking a span in TracesTab highlights it on the canvas).

### Hook Interface

```tsx
const {
  highlightedNodeId,
  highlightNode,
  clearHighlight,
  isNodeHighlighted,
  getNodeHighlightStyle,
  navigateBack,
  navigateForward,
  canNavigateBack,
  canNavigateForward,
} = useTraceLinking({
  initialNodeId: selectedSpanId,
  onHighlight: (nodeId) => {
    // Notify parent component
    onSpanSelect?.(nodeId);
  },
  scrollOnHighlight: true,
  enableHistory: true,
});
```

### UI Integration

```tsx
{/* Navigation buttons appear when history is available */}
{(canNavigateBack || canNavigateForward) && (
  <div className="flex items-center gap-1">
    <Button
      onClick={navigateBack}
      disabled={!canNavigateBack}
      aria-label="Navigate to previous span"
    >
      <ArrowLeft className="h-4 w-4" />
    </Button>
    <Button
      onClick={navigateForward}
      disabled={!canNavigateForward}
      aria-label="Navigate to next span"
    >
      <ArrowRight className="h-4 w-4" />
    </Button>
  </div>
)}
```

### Testing Pattern

```tsx
it("should call onSpanSelect when span is clicked", () => {
  const onSpanSelect = vi.fn();
  renderWithProvider(
    <TracesTab
      traces={mockTraces}
      spans={mockSpans}
      selectedTraceId="trace-1"
      onSpanSelect={onSpanSelect}
    />,
  );

  fireEvent.click(screen.getByText(/auth\.validate/i));
  expect(onSpanSelect).toHaveBeenCalledWith("span-2");
});
```

---

## Pattern 3: Context Provider Integration

Complex components use context providers for shared state management.

### DevToolsTimelineProvider

```tsx
// Wrap components that need timeline state
<DevToolsTimelineProvider initialEvents={events}>
  <TimelineBar showMinimap showBookmarkButton />
  <TracesTab traces={traces} spans={spans} />
</DevToolsTimelineProvider>

// Access context in child components
function TimelineBar() {
  const timeline = useTimelineContext();
  // timeline.currentTime, timeline.events, timeline.bookmarks, etc.
}
```

### Testing with Providers

```tsx
function renderWithProvider(
  ui: React.ReactElement,
  providerProps?: Partial<React.ComponentProps<typeof DevToolsTimelineProvider>>,
) {
  return render(
    <DevToolsTimelineProvider {...providerProps}>
      {ui}
    </DevToolsTimelineProvider>,
  );
}

it("should render with context", () => {
  const initialEvents = [
    { id: "1", type: "console", timestamp: Date.now(), ... },
  ];
  renderWithProvider(<TimelineBar />, { initialEvents });
  expect(screen.getByTestId("timeline-bar")).toBeInTheDocument();
});
```

---

## Pattern 4: Keyboard Shortcuts

The `useTimelineKeyboard` hook provides keyboard navigation for timeline controls.

### Hook Usage

```tsx
const { shortcuts } = useTimelineKeyboard({
  enabled: hasEvents,
  onPlayPause: () => {
    if (timeline.isPlaying) {
      timeline.stopPlayback();
    } else {
      timeline.startPlayback();
    }
  },
  onStepForward: () => timeline.stepForward(),
  onStepBackward: () => timeline.stepBackward(),
  onJumpToStart: () => timeline.jumpToStart(),
  onJumpToEnd: () => timeline.jumpToEnd(),
  onAddBookmark: () => handleAddBookmark(),
  onNextBookmark: () => {
    const next = sortedBookmarks.find((b) => b.timestamp > timeline.currentTime);
    if (next) timeline.jumpToBookmark(next.id);
  },
  onPrevBookmark: () => {
    const prev = reverseSortedBookmarks.find((b) => b.timestamp < timeline.currentTime);
    if (prev) timeline.jumpToBookmark(prev.id);
  },
  onSetSpeed: (speed: number) => {
    timeline.setPlaybackSpeed(speed);
    onPlaybackSpeedChange?.(speed);
  },
});
```

### Default Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause |
| Left Arrow | Step backward |
| Right Arrow | Step forward |
| Home | Jump to start |
| End | Jump to end |
| B | Add bookmark |
| [ | Previous bookmark |
| ] | Next bookmark |
| 1-4 | Set speed (0.5x, 1x, 2x, 4x) |

---

## Pattern 5: WebSocket Integration

The `useDevToolsWebSocket` hook provides real-time updates for console/network entries.

### Hook Interface

```tsx
const {
  status,           // "connected" | "connecting" | "disconnected" | "error"
  consoleEntries,
  networkEntries,
  traceSteps,
  clearConsoleEntries,
  clearNetworkEntries,
  clearTraceSteps,
  reconnect,
  reconnectAttempts,
} = useDevToolsWebSocket();
```

### Status Indicator Pattern

```tsx
{status === "connected" && (
  <span data-testid="devtools-connected-indicator">Connected</span>
)}
{status === "connecting" && (
  <span data-testid="devtools-reconnecting-indicator">
    Reconnecting ({reconnectAttempts})...
  </span>
)}
{status === "error" && (
  <span data-testid="devtools-error-indicator">Connection error</span>
)}
```

---

## Testing Guidance

### DevToolsPanel Test Stability

The DevToolsPanel tests are complex due to:
- 8 vi.mock() calls for dependencies
- Redux store creation per test
- userEvent.setup() instances
- 34 total tests

**Known Issue**: Running the full suite can trigger OOM killer (exit code 137) on systems with limited memory. This is due to cumulative memory pressure from:
- Multiple forked worker processes
- Redux store instances not fully garbage collected between tests
- Heavy DOM rendering with jsdom

**Recommendations**:
1. Use `--testNamePattern` to run specific tests during development
2. Individual tests run in ~20-200ms; full suite takes 30+ seconds
3. Run with `--no-threads` or reduce `maxWorkers` if OOM occurs
4. The vitest config uses `pool: "forks"` with `isolate: true` for proper isolation
5. Consider splitting into multiple test files if OOM persists

### Mocking Pattern

```tsx
// Mock at module level
vi.mock("./hooks/useDevToolsWebSocket", () => ({
  useDevToolsWebSocket: () => mockDevToolsWsState,
}));

// Reset in beforeEach
beforeEach(() => {
  vi.clearAllMocks();
  mockDevToolsWsState = {
    status: "connected",
    consoleEntries: [],
    // ...defaults
  };
});
```

---

## Hook Inventory

### DevTools Hooks (integrated)

| Hook | Component | Status |
|------|-----------|--------|
| useTimelineContext | TimelineBar, TracesTab | Integrated |
| useTimelineKeyboard | TimelineBar | Integrated |
| useTraceLinking | TracesTab | Integrated |
| useDevToolsWebSocket | DevToolsPanel | Integrated |
| useDevToolsContext | DevToolsPanel | Integrated |

### Pending Integration

| Hook | Target Component | Priority |
|------|------------------|----------|
| useDevToolsResize | DevToolsPanel | P2 |
| useConsoleEntries | ConsoleTab | P2 |
| useNetworkEntries | NetworkTab | P2 |
| useStateHistory | StateTab | P2 |
| useAgentTrace | AgentTraceTab | P2 |
| useProblems | ProblemsTab | P2 |
| useAutoTail | ConsoleTab, LogsTab | P3 |
| useDevToolsAI | AIInsightsTab | P3 |
| useObservabilityAI | AlertsTab, TracesTab | P3 |

---

## Pattern 7: MSW Handler Integration for E2E Tests

When writing E2E or integration tests that need stateful mock handlers (e.g., simulating a database), use the global MSW server with `server.use()` to prepend handlers. This ensures your handlers take priority over the default global handlers.

### Problem

Tests that create their own MSW server conflict with the global server from `test/setup.ts`. MSW only allows one server to be active at a time.

### Solution: Use `server.use()` to Prepend Handlers

```tsx
// Import the global server
import { server } from "../mocks/server";

// Define stateful handlers locally
const sessionGoalStore = new Map<string, StoredGoal[]>();

const e2eHandlers = [
  http.post("/api/v1/sessions/:session_id/goal", async ({ params, request }) => {
    const { session_id } = params as { session_id: string };
    const body = await request.json();

    // Store in local state for E2E verification
    const goals = sessionGoalStore.get(session_id) ?? [];
    goals.push({ id: generateId(), ...body });
    sessionGoalStore.set(session_id, goals);

    return HttpResponse.json({ session_id, ...body }, { status: 201 });
  }),

  http.get("/api/v1/sessions/:session_id/goals", ({ params }) => {
    const { session_id } = params as { session_id: string };
    const goals = sessionGoalStore.get(session_id) ?? [];
    return HttpResponse.json({ session_id, goals, total: goals.length });
  }),
];

describe("E2E Flow", () => {
  // Prepend handlers before EACH test (gives them priority)
  beforeEach(() => {
    server.use(...e2eHandlers);
  });

  afterEach(() => {
    server.resetHandlers(); // Removes prepended handlers
    sessionGoalStore.clear(); // Reset local state
  });

  it("completes full flow", async () => {
    // Test code here - uses e2eHandlers
  });
});
```

### Key Points

1. **Import global server**: Use `import { server } from "../mocks/server"`
2. **Prepend with `server.use()`**: Handlers added with `server.use()` take priority
3. **Reset in `afterEach`**: `server.resetHandlers()` removes prepended handlers
4. **Clear local state**: Reset any local storage (Maps, arrays) in `afterEach`

### When to Use This Pattern

| Scenario | Use This Pattern |
|----------|------------------|
| E2E tests with in-memory state | ✅ Yes |
| Tests that override error responses | ✅ Yes |
| Tests with delayed responses | ✅ Yes |
| Simple unit tests | ❌ No - use vi.mock() |
| Component tests with mocked hooks | ❌ No - use vi.mock() |

### Example Files

- `src/api/sessionGoal.e2e.test.tsx` - Full E2E example with stateful handlers
- `src/api/endpoints.test.tsx` - API endpoint tests with handler overrides
- `src/mocks/handlers/sessionGoalHandlers.ts` - Reusable handler definitions

---

## Related Documentation

- [STATE_MANAGEMENT_PATTERNS.md](./STATE_MANAGEMENT_PATTERNS.md) - Redux patterns
- [ACCESSIBILITY_IMPLEMENTATION.md](./ACCESSIBILITY_IMPLEMENTATION.md) - ARIA patterns
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Component styling
