/**
 * ObservabilityPage Tests
 *
 * TDD tests for the observability page using RTK Query.
 * Tests cover:
 * - Tab navigation
 * - Traces display
 * - Logs display
 * - Metrics display
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ObservabilityPage } from "./ObservabilityPage";
import { TestProvider } from "../test-utils";

// Mock the RTK Query hooks
const mockRefetchTraces = vi.fn();
const mockRefetchLogs = vi.fn();
const mockRefetchMetrics = vi.fn();
const mockRefetchAlerts = vi.fn();

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    useListTracesQuery: vi.fn(),
    useListLogsQuery: vi.fn(),
    useGetMetricsQuery: vi.fn(),
    useGetTraceQuery: vi.fn(),
    useListAlertsQuery: vi.fn(),
  };
});

import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useGetTraceQuery,
  useListAlertsQuery,
} from "../api";

// Cast to vi.Mock for type safety
const mockUseListTracesQuery = useListTracesQuery as ReturnType<typeof vi.fn>;
const mockUseListLogsQuery = useListLogsQuery as ReturnType<typeof vi.fn>;
const mockUseGetMetricsQuery = useGetMetricsQuery as ReturnType<typeof vi.fn>;
const mockUseGetTraceQuery = useGetTraceQuery as ReturnType<typeof vi.fn>;
const mockUseListAlertsQuery = useListAlertsQuery as ReturnType<typeof vi.fn>;

// Default mock data
const mockTraces = [
  {
    trace_id: "1",
    span_id: "s1",
    name: "chat/completion",
    start_time: new Date().toISOString(),
    end_time: new Date(Date.now() + 1234).toISOString(),
    status: "success",
    attributes: {},
  },
  {
    trace_id: "2",
    span_id: "s2",
    name: "tools/execute",
    start_time: new Date(Date.now() - 60000).toISOString(),
    end_time: new Date(Date.now() - 60000 + 567).toISOString(),
    status: "success",
    attributes: {},
  },
];

const mockLogs = [
  {
    id: "log-1",
    level: "info",
    message: "Processing request",
    timestamp: new Date().toISOString(),
    service: "agent",
  },
  {
    id: "log-2",
    level: "error",
    message: "Connection failed",
    timestamp: new Date().toISOString(),
    service: "mcp",
  },
];

const mockMetrics = {
  requests_total: 1523,
  errors_total: 12,
  avg_latency_ms: 234,
  p99_latency_ms: 890,
  tokens_used: 45678,
  active_sessions: 8,
};

const mockAlerts = [
  {
    alert_id: "alert-1",
    name: "High Memory Usage",
    severity: "warning",
    state: "firing",
    message: "Memory usage is above 80%",
    labels: { service: "mcp-server", severity: "warning" },
    annotations: { summary: "High memory alert" },
    started_at: new Date().toISOString(),
    ended_at: null,
    generator_url: "http://grafana/alerting/1",
  },
  {
    alert_id: "alert-2",
    name: "API Latency High",
    severity: "critical",
    state: "firing",
    message: "API latency exceeds threshold",
    labels: { service: "api-gateway", severity: "critical" },
    annotations: { summary: "High latency detected" },
    started_at: new Date(Date.now() - 300000).toISOString(),
    ended_at: null,
    generator_url: null,
  },
];

describe("ObservabilityPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock: successful traces response
    mockUseListTracesQuery.mockReturnValue({
      data: { items: mockTraces, total: 2, limit: 50 },
      isLoading: false,
      error: null,
      refetch: mockRefetchTraces,
    });

    mockUseListLogsQuery.mockReturnValue({
      data: { items: mockLogs, total: 2, limit: 50 },
      isLoading: false,
      error: null,
      refetch: mockRefetchLogs,
    });

    mockUseGetMetricsQuery.mockReturnValue({
      data: mockMetrics,
      isLoading: false,
      error: null,
      refetch: mockRefetchMetrics,
    });

    mockUseListAlertsQuery.mockReturnValue({
      data: { items: mockAlerts, total: 2 },
      isLoading: false,
      error: null,
      refetch: mockRefetchAlerts,
    });

    // Default mock: trace detail query (used by TraceViewer)
    mockUseGetTraceQuery.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });
  });

  describe("Header", () => {
    it("should display page title", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Observability")).toBeInTheDocument();
    });

    it("should display page description", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(
        screen.getByText(/Monitor traces, logs, and metrics/),
      ).toBeInTheDocument();
    });

    it("should have refresh button", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Refresh")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("should have Traces tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Traces")).toBeInTheDocument();
    });

    it("should have Logs tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Logs")).toBeInTheDocument();
    });

    it("should have Metrics tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Metrics")).toBeInTheDocument();
    });

    it("should switch to Logs tab when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Traces should be visible by default
      expect(screen.getByText("chat/completion")).toBeInTheDocument();

      // Click on Logs tab
      fireEvent.click(screen.getByText("Logs"));

      // Should display logs
      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });
    });
  });

  describe("Loading State", () => {
    it("should show loading skeletons initially", () => {
      // Set traces to loading state
      mockUseListTracesQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Should show skeleton placeholders instead of spinner
      expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should show multiple skeleton items while loading", () => {
      mockUseListTracesQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Should have multiple skeleton items (3 by default)
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe("Traces Tab", () => {
    it("should display traces after loading", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });
    });

    it("should show trace status badges", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Check for status badge
      expect(screen.getAllByText("success").length).toBeGreaterThan(0);
    });

    it("should show trace duration", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        // Duration is calculated from start_time and end_time
        // Multiple traces have duration, so use getAllByText
        expect(screen.getAllByText(/ms/).length).toBeGreaterThan(0);
      });
    });

    it("should show empty state when no traces", async () => {
      // Override mock to return empty traces
      mockUseListTracesQuery.mockReturnValue({
        data: { items: [], total: 0, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText(/No traces found/)).toBeInTheDocument();
      });
    });
  });

  describe("Logs Tab", () => {
    it("should fetch and display logs when switching to Logs tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });
    });

    it("should display log entries with level badges", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
        expect(screen.getByText("info")).toBeInTheDocument();
      });
    });

    it("should show service name for each log entry", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText("agent")).toBeInTheDocument();
      });
    });

    it("should show empty state when no logs", async () => {
      // Override mock to return empty logs
      mockUseListLogsQuery.mockReturnValue({
        data: { items: [], total: 0, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchLogs,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText(/No logs found/)).toBeInTheDocument();
      });
    });
  });

  describe("Metrics Tab", () => {
    it("should fetch and display metrics when switching to Metrics tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText("Total Requests")).toBeInTheDocument();
      });
    });

    it("should display request count metric", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText("Total Requests")).toBeInTheDocument();
        expect(screen.getByText("1,523")).toBeInTheDocument();
      });
    });

    it("should display error count metric", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText("Total Errors")).toBeInTheDocument();
        expect(screen.getByText("12")).toBeInTheDocument();
      });
    });

    it("should display latency metrics", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText("Avg Latency")).toBeInTheDocument();
        expect(screen.getByText("234ms")).toBeInTheDocument();
      });
    });

    it("should display token usage metric", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.queryByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText("Tokens Used")).toBeInTheDocument();
        expect(screen.getByText("45,678")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error message when fetch fails", async () => {
      // Mock RTK Query hooks to return error state
      mockUseListTracesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500, message: "Internal Server Error" },
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
      });
    });

    it("should show retry button on error", async () => {
      // Mock RTK Query hooks to return error state
      mockUseListTracesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500 },
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Retry")).toBeInTheDocument();
      });
    });
  });

  describe("Traces Pagination", () => {
    it("should show Load More button when next_cursor is present", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: mockTraces,
          total: 100,
          limit: 50,
          next_cursor: "next-page-cursor",
        },
        isLoading: false,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /load more/i }),
        ).toBeInTheDocument();
      });
    });

    it("should not show Load More button when no next_cursor", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: { items: mockTraces, total: 2, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(
        screen.queryByRole("button", { name: /load more/i }),
      ).not.toBeInTheDocument();
    });

    it("should show trace count", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: { items: mockTraces, total: 100, limit: 50, next_cursor: "next" },
        isLoading: false,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText(/2 of 100/i)).toBeInTheDocument();
      });
    });
  });

  describe("Traces Filters", () => {
    it("should have status filter buttons", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Status filter buttons
      expect(
        screen.getByRole("button", { name: /^all$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^success$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^error$/i }),
      ).toBeInTheDocument();
    });

    it("should have session ID filter input", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText(/session id/i)).toBeInTheDocument();
    });

    it("should have time range filter", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Time range filter options
      expect(
        screen.getByRole("combobox", { name: /time range/i }),
      ).toBeInTheDocument();
    });

    it("should call hook with status filter when status is selected", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^error$/i }));

      // The hook should be called with the new status
      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ status: "error" }),
        );
      });
    });
  });

  describe("Alerts Tab", () => {
    it("should show Alerts tab in navigation", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /alerts/i }),
      ).toBeInTheDocument();
    });

    it("should switch to alerts tab when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });
    });

    it("should display alert severity badges", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // Check for severity badges
      expect(screen.getByText("warning")).toBeInTheDocument();
      expect(screen.getByText("critical")).toBeInTheDocument();
    });

    it("should display alert state badges", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // Check for state badges (both alerts are firing)
      const firingBadges = screen.getAllByText("firing");
      expect(firingBadges.length).toBe(2);
    });

    it("should have state filter buttons", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // State filter buttons
      expect(
        screen.getByRole("button", { name: /^All$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^Firing$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^Pending$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^Resolved$/i }),
      ).toBeInTheDocument();
    });

    it("should display alert labels", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // Check for service labels
      expect(screen.getByText("service=mcp-server")).toBeInTheDocument();
      expect(screen.getByText("service=api-gateway")).toBeInTheDocument();
    });

    it("should show empty state when no alerts", async () => {
      mockUseListAlertsQuery.mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
        error: null,
        refetch: mockRefetchAlerts,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("No alerts found")).toBeInTheDocument();
      });
    });
  });
});
