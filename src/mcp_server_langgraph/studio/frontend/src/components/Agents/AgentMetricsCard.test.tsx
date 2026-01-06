/**
 * AgentMetricsCard Tests
 *
 * TDD tests for the AgentMetricsCard component.
 * Tests cover:
 * - Display of orchestrator metrics (executions, duration, success rate)
 * - Display of HITL metrics (requests, approvals, rejections)
 * - Display of cost metrics (total cost, tokens, per-request cost)
 * - Persona-based visibility (only admin, developer)
 * - Loading and error states
 * - Time range selector
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AgentMetricsCard } from "./AgentMetricsCard";
import personaReducer from "../../store/slices/personaSlice";
import type { AgentMetricsResponseCamelCase } from "../../types/api";

// Mock the API hook
const mockRefetch = vi.fn();
vi.mock("../../api", () => ({
  useGetAgentMetricsQuery: vi.fn(),
}));

import { useGetAgentMetricsQuery } from "../../api";
const mockUseGetAgentMetricsQuery = useGetAgentMetricsQuery as ReturnType<
  typeof vi.fn
>;

// Helper to create a test store with specific persona
function createTestStoreWithPersona(persona: "admin" | "developer" | "user") {
  return configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona,
        subPersona: null,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
        visibleModules: [],
        featureFlags: {},
        apiVersion: null,
      },
    },
  });
}

// Mock metrics data (camelCase per ADR-0091)
const mockMetrics: AgentMetricsResponseCamelCase = {
  timestamp: "2025-12-27T12:00:00Z",
  timeRangeHours: 24,
  orchestrator: {
    totalExecutions: 1000,
    successfulExecutions: 950,
    failedExecutions: 50,
    avgDurationMs: 1500.5,
    p50DurationMs: 1200.0,
    p95DurationMs: 2500.0,
    p99DurationMs: 3000.0,
  },
  hitl: {
    totalRequests: 100,
    approvedCount: 85,
    rejectedCount: 10,
    pendingCount: 5,
    avgResponseLatencyMs: 5000.0,
  },
  cost: {
    totalCostUsd: 125.5,
    totalTokens: 2500000,
    avgCostPerRequestUsd: 0.1255,
  },
};

describe("AgentMetricsCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Persona Visibility", () => {
    it("should render for admin persona", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByTestId("agent-metrics-card")).toBeInTheDocument();
    });

    it("should render for developer persona", () => {
      const store = createTestStoreWithPersona("developer");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByTestId("agent-metrics-card")).toBeInTheDocument();
    });

    it("should NOT render for user persona", () => {
      const store = createTestStoreWithPersona("user");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(
        screen.queryByTestId("agent-metrics-card"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner while fetching", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByTestId("metrics-loading")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when metrics unavailable", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 503 },
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByTestId("metrics-error")).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 503 },
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Orchestrator Metrics", () => {
    it("should display total executions", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByText("1,000")).toBeInTheDocument();
    });

    it("should display success rate", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      // 950 successful out of 1000 = 95%
      expect(screen.getByText("95.0%")).toBeInTheDocument();
    });

    it("should display average duration", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByText(/1500.5/)).toBeInTheDocument();
    });
  });

  describe("HITL Metrics", () => {
    it("should display total HITL requests", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      // HITL section should show 100 total requests
      const hitlSection = screen.getByTestId("hitl-metrics");
      expect(within(hitlSection).getByText("100")).toBeInTheDocument();
    });

    it("should display approval count", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByText("85")).toBeInTheDocument();
    });

    it("should display pending count", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByText("5")).toBeInTheDocument();
    });
  });

  describe("Cost Metrics", () => {
    it("should display total cost", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByText("$125.50")).toBeInTheDocument();
    });

    it("should display total tokens", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      // 2,500,000 tokens
      expect(screen.getByText("2,500,000")).toBeInTheDocument();
    });
  });

  describe("Time Range Selector", () => {
    it("should display time range", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(screen.getByText(/24h/)).toBeInTheDocument();
    });
  });

  describe("Refresh Functionality", () => {
    it("should have refresh button", () => {
      const store = createTestStoreWithPersona("admin");
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });

    it("should call refetch when refresh is clicked", async () => {
      const store = createTestStoreWithPersona("admin");
      const user = userEvent.setup();
      mockUseGetAgentMetricsQuery.mockReturnValue({
        data: mockMetrics,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <Provider store={store}>
          <AgentMetricsCard />
        </Provider>,
      );

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      await user.click(refreshButton);

      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });
});
