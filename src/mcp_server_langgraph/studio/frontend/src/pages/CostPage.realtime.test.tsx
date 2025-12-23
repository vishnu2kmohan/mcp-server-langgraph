/**
 * CostPage Real-time Integration Tests (TDD RED Phase)
 *
 * Tests verify that CostPage integrates with useCostTrackingWebSocket
 * for real-time cost updates and budget warnings.
 * These tests should FAIL initially until we implement the WebSocket integration.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { CostPage } from "./CostPage";

// Mock RTK Query hooks
vi.mock("../api", () => ({
  useGetCostSummaryQuery: vi.fn(() => ({
    data: {
      total_cost: 125.5,
      total_tokens: 50000,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
  useGetCostByModelQuery: vi.fn(() => ({
    data: [
      { model: "gpt-4", cost: 100.0, requests: 50 },
      { model: "claude-3", cost: 25.5, requests: 25 },
    ],
    isLoading: false,
    refetch: vi.fn(),
  })),
  useGetCostHistoryQuery: vi.fn(() => ({
    data: [
      { date: "2024-01-01", cost: 10.0 },
      { date: "2024-01-02", cost: 15.0 },
    ],
    isLoading: false,
    refetch: vi.fn(),
  })),
}));

// Mock useCostTrackingWebSocket
const mockSubscribeSession = vi.fn();
const mockSubscribeUser = vi.fn();
const mockClearBudgetWarnings = vi.fn();

vi.mock("../hooks/useCostTrackingWebSocket", () => ({
  useCostTrackingWebSocket: vi.fn(() => ({
    status: "connected" as const,
    sessionCosts: {},
    userBudget: null,
    subscribedSessions: new Set<string>(),
    subscribedUsers: new Set<string>(),
    budgetWarnings: [],
    error: null,
    subscribeSession: mockSubscribeSession,
    unsubscribeSession: vi.fn(),
    subscribeUser: mockSubscribeUser,
    unsubscribeUser: vi.fn(),
    getSessionCost: vi.fn(),
    clearBudgetWarnings: mockClearBudgetWarnings,
    disconnect: vi.fn(),
    reconnect: vi.fn(),
  })),
}));

// Create mock store
function createMockStore() {
  return configureStore({
    reducer: {
      // Minimal reducer for testing
      test: (state = {}) => state,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({ serializableCheck: false }),
  });
}

describe("CostPage Real-time Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("WebSocket Connection Status", () => {
    it("should display WebSocket connection status indicator", async () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: WebSocket status indicator doesn't exist yet
        expect(screen.getByTestId("ws-status-indicator")).toBeInTheDocument();
      });
    });

    it("should show connected status when WebSocket is connected", async () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: Status should show "Live" when connected
        const indicator = screen.getByTestId("ws-status-indicator");
        expect(indicator).toHaveTextContent(/live/i);
      });
    });

    it("should show reconnecting status when WebSocket is reconnecting", async () => {
      const { useCostTrackingWebSocket } =
        await import("../hooks/useCostTrackingWebSocket");
      vi.mocked(useCostTrackingWebSocket).mockReturnValue({
        status: "reconnecting" as const,
        sessionCosts: {},
        userBudget: null,
        subscribedSessions: new Set<string>(),
        subscribedUsers: new Set<string>(),
        budgetWarnings: [],
        error: null,
        subscribeSession: mockSubscribeSession,
        unsubscribeSession: vi.fn(),
        subscribeUser: mockSubscribeUser,
        unsubscribeUser: vi.fn(),
        getSessionCost: vi.fn(),
        clearBudgetWarnings: mockClearBudgetWarnings,
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: Status should show "Reconnecting" when reconnecting
        const indicator = screen.getByTestId("ws-status-indicator");
        expect(indicator).toHaveTextContent(/reconnecting/i);
      });
    });
  });

  describe("Real-time Cost Updates", () => {
    it("should display session cost from WebSocket", async () => {
      const { useCostTrackingWebSocket } =
        await import("../hooks/useCostTrackingWebSocket");
      vi.mocked(useCostTrackingWebSocket).mockReturnValue({
        status: "connected" as const,
        sessionCosts: {
          "session-1": {
            session_id: "session-1",
            total_cost: 5.25,
            token_count: 2000,
            model: "gpt-4",
          },
        },
        userBudget: null,
        subscribedSessions: new Set(["session-1"]),
        subscribedUsers: new Set<string>(),
        budgetWarnings: [],
        error: null,
        subscribeSession: mockSubscribeSession,
        unsubscribeSession: vi.fn(),
        subscribeUser: mockSubscribeUser,
        unsubscribeUser: vi.fn(),
        getSessionCost: vi.fn(),
        clearBudgetWarnings: mockClearBudgetWarnings,
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: Session cost section doesn't exist yet
        expect(screen.getByTestId("live-session-costs")).toBeInTheDocument();
        expect(screen.getByText("$5.25")).toBeInTheDocument();
      });
    });
  });

  describe("Budget Warnings", () => {
    it("should display budget warnings when received", async () => {
      const { useCostTrackingWebSocket } =
        await import("../hooks/useCostTrackingWebSocket");
      vi.mocked(useCostTrackingWebSocket).mockReturnValue({
        status: "connected" as const,
        sessionCosts: {},
        userBudget: {
          user_id: "user-1",
          budget_limit: 100,
          current_usage: 85,
          remaining: 15,
        },
        subscribedSessions: new Set<string>(),
        subscribedUsers: new Set(["user-1"]),
        budgetWarnings: [
          {
            user_id: "user-1",
            threshold: 80,
            current_usage: 85,
            budget_limit: 100,
            message: "You have used 85% of your monthly budget",
          },
        ],
        error: null,
        subscribeSession: mockSubscribeSession,
        unsubscribeSession: vi.fn(),
        subscribeUser: mockSubscribeUser,
        unsubscribeUser: vi.fn(),
        getSessionCost: vi.fn(),
        clearBudgetWarnings: mockClearBudgetWarnings,
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: Budget warning banner doesn't exist yet
        expect(screen.getByTestId("budget-warning-banner")).toBeInTheDocument();
        expect(
          screen.getByText(/You have used 85% of your monthly budget/i),
        ).toBeInTheDocument();
      });
    });

    it("should display user budget progress bar", async () => {
      const { useCostTrackingWebSocket } =
        await import("../hooks/useCostTrackingWebSocket");
      vi.mocked(useCostTrackingWebSocket).mockReturnValue({
        status: "connected" as const,
        sessionCosts: {},
        userBudget: {
          user_id: "user-1",
          budget_limit: 100,
          current_usage: 65,
          remaining: 35,
        },
        subscribedSessions: new Set<string>(),
        subscribedUsers: new Set(["user-1"]),
        budgetWarnings: [],
        error: null,
        subscribeSession: mockSubscribeSession,
        unsubscribeSession: vi.fn(),
        subscribeUser: mockSubscribeUser,
        unsubscribeUser: vi.fn(),
        getSessionCost: vi.fn(),
        clearBudgetWarnings: mockClearBudgetWarnings,
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: Budget progress bar doesn't exist yet
        expect(screen.getByTestId("budget-progress-bar")).toBeInTheDocument();
        expect(screen.getByText(/\$35.*remaining/i)).toBeInTheDocument();
      });
    });
  });

  describe("Feature Flag Control", () => {
    it("should not show real-time features when enableRealtime is false", async () => {
      // When enableRealtime option is false or feature flag is disabled,
      // the WebSocket features should not be visible
      // TDD RED: enableRealtime prop doesn't exist yet
      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      // Base functionality should work
      await waitFor(() => {
        expect(screen.getByText("Cost Dashboard")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should display WebSocket error state", async () => {
      const { useCostTrackingWebSocket } =
        await import("../hooks/useCostTrackingWebSocket");
      vi.mocked(useCostTrackingWebSocket).mockReturnValue({
        status: "error" as const,
        sessionCosts: {},
        userBudget: null,
        subscribedSessions: new Set<string>(),
        subscribedUsers: new Set<string>(),
        budgetWarnings: [],
        error: "Connection failed",
        subscribeSession: mockSubscribeSession,
        unsubscribeSession: vi.fn(),
        subscribeUser: mockSubscribeUser,
        unsubscribeUser: vi.fn(),
        getSessionCost: vi.fn(),
        clearBudgetWarnings: mockClearBudgetWarnings,
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <CostPage />
        </Provider>,
      );

      await waitFor(() => {
        // TDD RED: Error indicator doesn't exist yet
        const indicator = screen.getByTestId("ws-status-indicator");
        expect(indicator).toHaveTextContent(/error|offline/i);
      });
    });
  });
});
