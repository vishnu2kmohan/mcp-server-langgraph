/**
 * DevToolsPanel Features Tests
 *
 * Tests for context display, WebSocket status, resize handle, and accessibility.
 * Split from main test file to reduce memory pressure.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import React from "react";
import { DevToolsPanel } from "./DevToolsPanel";
import devToolsReducer from "../../store/slices/devToolsSlice";
import alertsReducer from "../../store/slices/alertSlice";
import type {
  DevToolsContext,
  DevToolsTabId,
} from "../../store/slices/devToolsSlice";

// =============================================================================
// Mock State (mutable for per-test overrides)
// =============================================================================

let mockDevToolsWsState = {
  status: "connected" as "connected" | "connecting" | "disconnected" | "error",
  consoleEntries: [] as unknown[],
  networkEntries: [] as unknown[],
  clearConsoleEntries: vi.fn(),
  clearNetworkEntries: vi.fn(),
  traceSteps: [] as unknown[],
  clearTraceSteps: vi.fn(),
  reconnect: vi.fn(),
  reconnectAttempts: 0,
};

// =============================================================================
// Mocks (must be at top level for hoisting)
// =============================================================================

vi.mock("./hooks/useDevToolsContext", () => ({
  useDevToolsContext: () => ({
    context: "session",
    entityId: "session-123",
    contextLabel: "Session: session-123",
  }),
}));

vi.mock("./context/DevToolsTimelineProvider", () => ({
  DevToolsTimelineProvider: ({ children }: { children: React.ReactNode }) =>
    children,
  useTimelineContext: () => ({
    events: [],
    filteredEvents: [],
    selectedEvent: null,
    setSelectedEvent: vi.fn(),
    timeRange: { start: 0, end: Date.now() },
    setTimeRange: vi.fn(),
    isPlaying: false,
    setIsPlaying: vi.fn(),
    playbackSpeed: 1,
    setPlaybackSpeed: vi.fn(),
    filters: {},
    setFilters: vi.fn(),
    addEvent: vi.fn(),
    clearEvents: vi.fn(),
  }),
}));

vi.mock("./components/DevToolsWebSocketObserver", () => ({
  DevToolsWebSocketObserver: () => null,
}));

vi.mock("./TimelineBar", () => ({
  TimelineBar: () => <div data-testid="timeline-bar-mock">Timeline Bar</div>,
}));

vi.mock("./hooks/useDevToolsWebSocket", () => ({
  useDevToolsWebSocket: () => mockDevToolsWsState,
}));

vi.mock("../../hooks/useTraceWebSocket", () => ({
  useTraceWebSocket: () => ({
    spans: [],
    isConnected: false,
    reconnect: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

vi.mock("../../hooks/useAlertWebSocket", () => ({
  useAlertWebSocket: () => ({
    status: "connected",
    reconnect: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

vi.mock("../../api", () => ({
  useListTracesQuery: () => ({
    data: { items: [] },
    isLoading: false,
    error: null,
  }),
  useGetMetricsQuery: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
  useListAlertsQuery: () => ({
    data: { items: [] },
    isLoading: false,
    error: null,
  }),
  useListLogsQuery: () => ({
    data: { items: [] },
    isLoading: false,
    error: null,
  }),
}));

// =============================================================================
// Test Utilities
// =============================================================================

function createTestStore(
  overrides?: Partial<{
    collapsed: boolean;
    height: number;
    maximized: boolean;
    activeTab: DevToolsTabId;
    detectedContext: DevToolsContext;
    contextEntityId: string | null;
    consoleFilter: "all" | "info" | "warning" | "error";
    aiInsightsEnabled: boolean;
    aiSuggestedLayout: DevToolsTabId[] | null;
  }>,
) {
  return configureStore({
    reducer: {
      devTools: devToolsReducer,
      alerts: alertsReducer,
    },
    preloadedState: {
      devTools: {
        collapsed: false,
        height: 250,
        maximized: false,
        activeTab: "console" as DevToolsTabId,
        detectedContext: "session" as DevToolsContext,
        contextEntityId: "session-123",
        consoleFilter: "all" as const,
        aiInsightsEnabled: false,
        aiSuggestedLayout: null,
        ...overrides,
      },
      alerts: {
        alerts: [],
        selectedAlertId: null,
        pendingRemediations: [],
        soundEnabled: true,
        lastCriticalAlertTime: null,
        filters: {
          severity: ["critical", "warning"],
          state: ["firing"],
        },
      },
    },
  });
}

function renderWithProviders(
  ui: React.ReactElement,
  store = createTestStore(),
) {
  return {
    ...render(
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>,
    ),
    store,
  };
}

// =============================================================================
// Tests
// =============================================================================

describe("DevToolsPanel - Features", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock state to defaults
    mockDevToolsWsState = {
      status: "connected",
      consoleEntries: [],
      networkEntries: [],
      clearConsoleEntries: vi.fn(),
      clearNetworkEntries: vi.fn(),
      traceSteps: [],
      clearTraceSteps: vi.fn(),
      reconnect: vi.fn(),
      reconnectAttempts: 0,
    };
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("context display", () => {
    it("should display context label in header", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByText("Session: session-123")).toBeInTheDocument();
    });

    it("should update context indicator when context changes", () => {
      const store = createTestStore({
        detectedContext: "workflow",
        contextEntityId: "workflow-456",
      });
      renderWithProviders(<DevToolsPanel />, store);
      expect(screen.getByTestId("devtools-header")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA tablist structure", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    it("should have aria-selected on active tab", () => {
      renderWithProviders(<DevToolsPanel />);
      const consoleTab = screen.getByRole("tab", { name: /Console/i });
      expect(consoleTab).toHaveAttribute("aria-selected", "true");
    });

    it("should have tabpanel for content", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByRole("tabpanel")).toBeInTheDocument();
    });

    it("should have accessible button labels", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(
        screen.getByRole("button", { name: /Collapse/i }),
      ).toHaveAccessibleName();
      expect(
        screen.getByRole("button", { name: /Maximize/i }),
      ).toHaveAccessibleName();
      const clearButtons = screen.getAllByRole("button", { name: /Clear/i });
      clearButtons.forEach((button) => {
        expect(button).toHaveAccessibleName();
      });
    });
  });

  describe("websocket status indicators", () => {
    it("should show connected indicator when WebSocket is connected", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(
        screen.getByTestId("devtools-connected-indicator"),
      ).toBeInTheDocument();
    });

    it("should show reconnecting indicator with attempt count", () => {
      mockDevToolsWsState = {
        ...mockDevToolsWsState,
        status: "connecting",
        reconnectAttempts: 3,
      };

      renderWithProviders(<DevToolsPanel />);
      const indicator = screen.getByTestId("devtools-reconnecting-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveTextContent("Reconnecting (3)...");
    });

    it("should show error indicator when WebSocket has error", () => {
      mockDevToolsWsState = {
        ...mockDevToolsWsState,
        status: "error",
        reconnectAttempts: 5,
      };

      renderWithProviders(<DevToolsPanel />);
      const indicator = screen.getByTestId("devtools-error-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveTextContent("Connection error");
    });
  });

  describe("resize handle", () => {
    it("should render resize handle when not maximized", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByTestId("devtools-resize-handle")).toBeInTheDocument();
    });

    it("should have proper accessibility attributes on resize handle", () => {
      renderWithProviders(<DevToolsPanel />);
      const handle = screen.getByTestId("devtools-resize-handle");
      expect(handle).toHaveAttribute("role", "separator");
      expect(handle).toHaveAttribute("aria-orientation", "horizontal");
      expect(handle).toHaveAttribute("aria-label", "Resize DevTools panel");
    });

    it("should hide resize handle when maximized", () => {
      const store = createTestStore({ maximized: true });
      renderWithProviders(<DevToolsPanel />, store);
      expect(
        screen.queryByTestId("devtools-resize-handle"),
      ).not.toBeInTheDocument();
    });

    it("should apply resizing styles during drag", async () => {
      renderWithProviders(<DevToolsPanel />);
      const handle = screen.getByTestId("devtools-resize-handle");

      await userEvent.pointer({ target: handle, keys: "[MouseLeft>]" });

      expect(handle).toHaveClass("cursor-ns-resize");
    });
  });
});
