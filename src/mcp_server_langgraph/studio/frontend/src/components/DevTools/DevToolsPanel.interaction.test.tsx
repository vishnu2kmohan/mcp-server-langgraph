/**
 * DevToolsPanel Interaction Tests
 *
 * Tests for tab switching, header actions, and console filter.
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

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListTracesQuery: () => ({
      data: { items: [] },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
    useGetTraceQuery: () => ({
      data: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
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
  };
});
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

describe("DevToolsPanel - Interaction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("tab switching", () => {
    it("should switch active tab when clicked", async () => {
      const user = userEvent.setup();
      const { store } = renderWithProviders(<DevToolsPanel />);

      await user.click(screen.getByRole("tab", { name: /Network/i }));

      expect(store.getState().devTools.activeTab).toBe("network");
    });

    it("should highlight active tab", () => {
      const store = createTestStore({ activeTab: "network" });
      renderWithProviders(<DevToolsPanel />, store);

      const networkTab = screen.getByRole("tab", { name: /Network/i });
      expect(networkTab).toHaveAttribute("aria-selected", "true");
    });

    it("should render correct tab content for Console", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(
        screen.getByTestId("devtools-tab-content-console"),
      ).toBeInTheDocument();
    });

    it("should render correct tab content for Network", () => {
      const store = createTestStore({ activeTab: "network" });
      renderWithProviders(<DevToolsPanel />, store);
      expect(
        screen.getByTestId("devtools-tab-content-network"),
      ).toBeInTheDocument();
    });
  });

  describe("header actions", () => {
    it("should render collapse button", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(
        screen.getByRole("button", { name: /Collapse/i }),
      ).toBeInTheDocument();
    });

    it("should render maximize button", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(
        screen.getByRole("button", { name: /Maximize/i }),
      ).toBeInTheDocument();
    });

    it("should render clear console button", () => {
      renderWithProviders(<DevToolsPanel />);
      const clearButtons = screen.getAllByRole("button", { name: /Clear/i });
      expect(clearButtons.length).toBeGreaterThan(0);
    });

    it("should dispatch toggleDevTools when collapse clicked", async () => {
      const user = userEvent.setup();
      const { store } = renderWithProviders(<DevToolsPanel />);

      await user.click(screen.getByRole("button", { name: /Collapse/i }));

      expect(store.getState().devTools.collapsed).toBe(true);
    });

    it("should dispatch setMaximized when maximize clicked", async () => {
      const user = userEvent.setup();
      const { store } = renderWithProviders(<DevToolsPanel />);

      await user.click(screen.getByRole("button", { name: /Maximize/i }));

      expect(store.getState().devTools.maximized).toBe(true);
    });
  });

  describe("console filter", () => {
    it("should render filter dropdown when Console tab active", () => {
      renderWithProviders(<DevToolsPanel />);
      expect(screen.getByTestId("console-filter")).toBeInTheDocument();
    });

    it("should show current filter value", () => {
      const store = createTestStore({ consoleFilter: "error" });
      renderWithProviders(<DevToolsPanel />, store);
      expect(screen.getByTestId("console-filter")).toHaveTextContent(/error/i);
    });
  });
});
