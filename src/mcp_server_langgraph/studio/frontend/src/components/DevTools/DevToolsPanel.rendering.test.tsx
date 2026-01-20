/**
 * DevToolsPanel Rendering Tests
 *
 * Tests for basic rendering, collapsed state, and styling.
 * Split from main test file to reduce memory pressure.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
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
  useDevToolsWebSocket: () => ({
    status: "connected",
    consoleEntries: [],
    networkEntries: [],
    clearConsoleEntries: vi.fn(),
    clearNetworkEntries: vi.fn(),
    traceSteps: [],
    clearTraceSteps: vi.fn(),
    reconnect: vi.fn(),
    reconnectAttempts: 0,
  }),
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

describe("DevToolsPanel - Rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render DevToolsPanel with data-testid", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByTestId("devtools-panel")).toBeInTheDocument();
    });

    it("should render header with context indicator", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByTestId("devtools-header")).toBeInTheDocument();
      expect(screen.getByText(/Session:/)).toBeInTheDocument();
    });

    it("should render tab bar", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByTestId("devtools-tabs")).toBeInTheDocument();
    });

    it("should render Console tab by default", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByRole("tab", { name: /Console/i })).toBeInTheDocument();
    });

    it("should render available tabs for session context", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByRole("tab", { name: /Console/i })).toBeInTheDocument();
      expect(
        screen.getByRole("tab", { name: /Agent Trace/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Network/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /State/i })).toBeInTheDocument();
      expect(
        screen.getByRole("tab", { name: /Problems/i }),
      ).toBeInTheDocument();
    });

    it("should not render AI Insights tab when disabled", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(
        screen.queryByRole("tab", { name: /AI Insights/i }),
      ).not.toBeInTheDocument();
    });

    it("should render AI Insights tab when enabled", () => {
      const store = createTestStore({ aiInsightsEnabled: true });
      renderWithProviders(<DevToolsPanel />, store);
      expect(
        screen.getByRole("tab", { name: /AI Insights/i }),
      ).toBeInTheDocument();
    });
  });

  describe("collapsed state", () => {
    it("should not render content when collapsed", () => {
      const store = createTestStore({ collapsed: true });
      renderWithProviders(<DevToolsPanel />, store);
      expect(screen.queryByTestId("devtools-panel")).not.toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("should accept className prop", () => {
      renderWithProviders(<DevToolsPanel className="custom-class" />);
      expect(screen.getByTestId("devtools-panel")).toHaveClass("custom-class");
    });

    it("should apply dark mode styles via design system tokens", () => {
      renderWithProviders(<DevToolsPanel />);
      const panel = screen.getByTestId("devtools-panel");
      // Uses bg-neutral-1 (Radix color scale token) which handles dark mode automatically
      // via CSS custom properties, not explicit dark: prefixed classes
      expect(panel).toHaveClass("bg-neutral-1");
    });
  });
});
