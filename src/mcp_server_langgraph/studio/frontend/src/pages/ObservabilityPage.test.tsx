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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ObservabilityPage } from "./ObservabilityPage";
import { TestProvider } from "../test-utils";
import observabilityReducer from "../store/slices/observabilitySlice";

// Mock the RTK Query hooks
const mockRefetchTraces = vi.fn();
const mockRefetchLogs = vi.fn();
const mockRefetchMetrics = vi.fn();
const mockRefetchAlerts = vi.fn();
const mockRefetchSessions = vi.fn();
const mockRefetchWorkflows = vi.fn();

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    useListTracesQuery: vi.fn(),
    useListLogsQuery: vi.fn(),
    useGetMetricsQuery: vi.fn(),
    useGetTraceQuery: vi.fn(),
    useListAlertsQuery: vi.fn(),
    useListSessionsQuery: vi.fn(),
    useListWorkflowsQuery: vi.fn(),
  };
});

import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useGetTraceQuery,
  useListAlertsQuery,
  useListSessionsQuery,
  useListWorkflowsQuery,
} from "../api";

// Cast to vi.Mock for type safety
const mockUseListTracesQuery = useListTracesQuery as ReturnType<typeof vi.fn>;
const mockUseListLogsQuery = useListLogsQuery as ReturnType<typeof vi.fn>;
const mockUseGetMetricsQuery = useGetMetricsQuery as ReturnType<typeof vi.fn>;
const mockUseGetTraceQuery = useGetTraceQuery as ReturnType<typeof vi.fn>;
const mockUseListAlertsQuery = useListAlertsQuery as ReturnType<typeof vi.fn>;
const mockUseListSessionsQuery = useListSessionsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseListWorkflowsQuery = useListWorkflowsQuery as ReturnType<
  typeof vi.fn
>;

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

const mockSessions = [
  {
    id: "session-1",
    name: "Agent Chat Session",
    workflow_id: null,
    user_id: "user-123",
    status: "active",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    config: null,
  },
  {
    id: "session-2",
    name: "Data Analysis Session",
    workflow_id: "workflow-1",
    user_id: "user-456",
    status: "archived",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    config: null,
  },
];

const mockWorkflows = [
  {
    id: "workflow-1",
    name: "Data Pipeline",
    description: "ETL workflow for data processing",
    node_count: 5,
    edge_count: 4,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "workflow-2",
    name: "Report Generator",
    description: "Automated report generation workflow",
    node_count: 3,
    edge_count: 2,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 172800000).toISOString(),
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

    // Default mock: sessions (Agent Sessions tab)
    mockUseListSessionsQuery.mockReturnValue({
      data: { items: mockSessions, total: 2, next_cursor: null },
      isLoading: false,
      error: null,
      refetch: mockRefetchSessions,
    });

    // Default mock: workflows (Workflow Runs tab)
    mockUseListWorkflowsQuery.mockReturnValue({
      data: { items: mockWorkflows, total: 2, next_cursor: null },
      isLoading: false,
      error: null,
      refetch: mockRefetchWorkflows,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
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
    it("should have Agent Sessions tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Agent Sessions")).toBeInTheDocument();
    });

    it("should have Workflow Runs tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Workflow Runs")).toBeInTheDocument();
    });

    it("should have Distributed Traces tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Distributed Traces")).toBeInTheDocument();
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

    it("should default to Agent Sessions tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Agent Sessions should be visible by default
      await waitFor(() => {
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });
    });

    it("should switch to Distributed Traces tab when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Click on Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      // Should display traces
      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });
    });

    it("should switch to Logs tab when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Click on Logs tab
      fireEvent.click(screen.getByText("Logs"));

      // Should display logs
      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });
    });
  });

  describe("Agent Sessions Tab", () => {
    it("should display agent sessions by default", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
        expect(screen.getByText("Data Analysis Session")).toBeInTheDocument();
      });
    });

    it("should show session status badges", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Active")).toBeInTheDocument();
        expect(screen.getByText("Archived")).toBeInTheDocument();
      });
    });

    it("should show empty state when no sessions", async () => {
      mockUseListSessionsQuery.mockReturnValue({
        data: { items: [], total: 0, next_cursor: null },
        isLoading: false,
        error: null,
        refetch: mockRefetchSessions,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("No agent sessions found")).toBeInTheDocument();
      });
    });

    it("should call refetchSessions when refresh is clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchSessions).toHaveBeenCalled();
    });
  });

  describe("Workflow Runs Tab", () => {
    it("should display workflows when switching to Workflow Runs tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Workflow Runs"));

      await waitFor(() => {
        expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
        expect(screen.getByText("Report Generator")).toBeInTheDocument();
      });
    });

    it("should show workflow node and edge counts", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Workflow Runs"));

      await waitFor(() => {
        expect(screen.getByText("5 nodes")).toBeInTheDocument();
        expect(screen.getByText("4 edges")).toBeInTheDocument();
      });
    });

    it("should show workflow descriptions", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Workflow Runs"));

      await waitFor(() => {
        expect(
          screen.getByText("ETL workflow for data processing"),
        ).toBeInTheDocument();
      });
    });

    it("should show empty state when no workflows", async () => {
      mockUseListWorkflowsQuery.mockReturnValue({
        data: { items: [], total: 0, next_cursor: null },
        isLoading: false,
        error: null,
        refetch: mockRefetchWorkflows,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Workflow Runs"));

      await waitFor(() => {
        expect(screen.getByText("No workflow runs found")).toBeInTheDocument();
      });
    });

    it("should call refetchWorkflows when refresh is clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Workflow Runs"));

      await waitFor(() => {
        expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchWorkflows).toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeletons initially for sessions", () => {
      // Set sessions to loading state
      mockUseListSessionsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchSessions,
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
      mockUseListSessionsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchSessions,
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
    it("should display traces when navigating to Distributed Traces tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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
      mockUseListSessionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500, message: "Internal Server Error" },
        refetch: mockRefetchSessions,
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
      mockUseListSessionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500 },
        refetch: mockRefetchSessions,
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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

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

  describe("URL Tab Sync", () => {
    // Helper to render with specific initial route
    const renderWithRoute = (initialPath: string) => {
      const store = configureStore({
        reducer: {
          observability: observabilityReducer,
        },
      });

      return render(
        <Provider store={store}>
          <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
              <Route path="/observability" element={<ObservabilityPage />} />
              <Route
                path="/observability/agent-sessions"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/workflow-runs"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/traces"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/logs"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/metrics"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/alerts"
                element={<ObservabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </Provider>,
      );
    };

    it("should show agent sessions tab when URL path is /observability/agent-sessions", async () => {
      renderWithRoute("/observability/agent-sessions");

      await waitFor(() => {
        // Agent Sessions tab should be active - sessions content should be visible
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });
    });

    it("should show workflow runs tab when URL path is /observability/workflow-runs", async () => {
      renderWithRoute("/observability/workflow-runs");

      await waitFor(() => {
        // Workflow Runs tab should be active - workflows content should be visible
        expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
      });
    });

    it("should show traces tab when URL path is /observability/traces", async () => {
      renderWithRoute("/observability/traces");

      await waitFor(() => {
        // Traces tab should be active - traces content should be visible
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });
    });

    it("should show logs tab when URL path is /observability/logs", async () => {
      renderWithRoute("/observability/logs");

      await waitFor(() => {
        // Logs tab should be active - logs content should be visible
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });
    });

    it("should show metrics tab when URL path is /observability/metrics", async () => {
      renderWithRoute("/observability/metrics");

      await waitFor(() => {
        // Metrics tab should be active - metrics content should be visible
        expect(screen.getByText("Total Requests")).toBeInTheDocument();
      });
    });

    it("should show alerts tab when URL path is /observability/alerts", async () => {
      renderWithRoute("/observability/alerts");

      await waitFor(() => {
        // Alerts tab should be active - alerts content should be visible
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });
    });

    it("should default to agent sessions tab when URL path is /observability", async () => {
      renderWithRoute("/observability");

      await waitFor(() => {
        // Default to agent sessions tab
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });
    });
  });

  describe("Time Range Filter Edge Cases", () => {
    it("should have default time range option selected", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      // Default is "1h" from Redux observabilitySlice initial state
      expect(timeRangeSelect).toHaveValue("1h");
    });

    it("should support changing to 15m time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      fireEvent.change(timeRangeSelect, { target: { value: "15m" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ start_time: expect.any(String) }),
        );
      });
    });

    it("should support changing to 1h time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      fireEvent.change(timeRangeSelect, { target: { value: "1h" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ start_time: expect.any(String) }),
        );
      });
    });

    it("should support changing to 24h time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      fireEvent.change(timeRangeSelect, { target: { value: "24h" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ start_time: expect.any(String) }),
        );
      });
    });

    it("should support changing to 7d time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      fireEvent.change(timeRangeSelect, { target: { value: "7d" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ start_time: expect.any(String) }),
        );
      });
    });

    it("should support changing to all time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      fireEvent.change(timeRangeSelect, { target: { value: "all" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ start_time: undefined }),
        );
      });
    });
  });

  describe("Log Level Display Edge Cases", () => {
    it("should display warn level with yellow styling", async () => {
      const logsWithWarn = [
        {
          id: "log-warn",
          level: "warn",
          message: "Warning message",
          timestamp: new Date().toISOString(),
          service: "test",
        },
      ];

      mockUseListLogsQuery.mockReturnValue({
        data: { items: logsWithWarn, total: 1, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchLogs,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        const warnBadge = screen.getByText("warn");
        expect(warnBadge).toBeInTheDocument();
        expect(warnBadge).toHaveClass("bg-yellow-100");
      });
    });

    it("should display debug level with gray styling", async () => {
      const logsWithDebug = [
        {
          id: "log-debug",
          level: "debug",
          message: "Debug message",
          timestamp: new Date().toISOString(),
          service: "test",
        },
      ];

      mockUseListLogsQuery.mockReturnValue({
        data: { items: logsWithDebug, total: 1, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchLogs,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        const debugBadge = screen.getByText("debug");
        expect(debugBadge).toBeInTheDocument();
        expect(debugBadge).toHaveClass("bg-gray-100");
      });
    });

    it("should display log without service field", async () => {
      const logsWithoutService = [
        {
          id: "log-no-service",
          level: "info",
          message: "Message without service",
          timestamp: new Date().toISOString(),
          service: undefined,
        },
      ];

      mockUseListLogsQuery.mockReturnValue({
        data: { items: logsWithoutService, total: 1, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchLogs,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText("Message without service")).toBeInTheDocument();
      });
    });
  });

  describe("Trace Status Display Edge Cases", () => {
    it("should display error status with red styling", async () => {
      const tracesWithError = [
        {
          trace_id: "error-trace",
          span_id: "s1",
          name: "failed/operation",
          start_time: new Date().toISOString(),
          end_time: new Date(Date.now() + 1000).toISOString(),
          status: "error",
          attributes: {},
        },
      ];

      mockUseListTracesQuery.mockReturnValue({
        data: { items: tracesWithError, total: 1, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        const errorBadge = screen.getByText("error");
        expect(errorBadge).toBeInTheDocument();
        expect(errorBadge).toHaveClass("bg-red-100");
      });
    });

    it("should display running status with blue styling", async () => {
      const tracesWithRunning = [
        {
          trace_id: "running-trace",
          span_id: "s1",
          name: "in-progress/operation",
          start_time: new Date().toISOString(),
          end_time: new Date(Date.now() + 1000).toISOString(),
          status: "running",
          attributes: {},
        },
      ];

      mockUseListTracesQuery.mockReturnValue({
        data: { items: tracesWithRunning, total: 1, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        const runningBadge = screen.getByText("running");
        expect(runningBadge).toBeInTheDocument();
        expect(runningBadge).toHaveClass("bg-blue-100");
      });
    });

    it("should have running status filter button", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(
        screen.getByRole("button", { name: /^running$/i }),
      ).toBeInTheDocument();
    });

    it("should call hook with running status when selected", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^running$/i }));

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ status: "running" }),
        );
      });
    });
  });

  describe("Alert Severity Edge Cases", () => {
    it("should display error severity alert with orange styling", async () => {
      const alertsWithErrorSeverity = [
        {
          alert_id: "alert-error",
          name: "Error Severity Alert",
          severity: "error",
          state: "firing",
          message: "Error level alert",
          labels: { service: "test" },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithErrorSeverity, total: 1 },
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
        // The error severity badge (not the state)
        const severityBadges = screen.getAllByText("error");
        const severityBadge = severityBadges.find((el) =>
          el.classList.contains("bg-orange-100"),
        );
        expect(severityBadge).toBeInTheDocument();
      });
    });

    it("should display info severity alert with blue styling", async () => {
      const alertsWithInfoSeverity = [
        {
          alert_id: "alert-info",
          name: "Info Severity Alert",
          severity: "info",
          state: "pending",
          message: "Info level alert",
          labels: { service: "test" },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithInfoSeverity, total: 1 },
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
        const infoBadge = screen.getByText("info");
        expect(infoBadge).toBeInTheDocument();
        expect(infoBadge).toHaveClass("bg-blue-100");
      });
    });
  });

  describe("Alert State Edge Cases", () => {
    it("should display pending state alert with yellow styling", async () => {
      const alertsWithPendingState = [
        {
          alert_id: "alert-pending",
          name: "Pending State Alert",
          severity: "warning",
          state: "pending",
          message: "Pending alert",
          labels: { service: "test" },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithPendingState, total: 1 },
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
        // State badge (not the filter button)
        const stateBadges = screen.getAllByText("pending");
        const stateBadge = stateBadges.find((el) =>
          el.classList.contains("rounded-full"),
        );
        expect(stateBadge).toBeInTheDocument();
        expect(stateBadge).toHaveClass("bg-yellow-100");
      });
    });

    it("should display resolved state alert with green styling", async () => {
      const alertsWithResolvedState = [
        {
          alert_id: "alert-resolved",
          name: "Resolved State Alert",
          severity: "info",
          state: "resolved",
          message: "Resolved alert",
          labels: { service: "test" },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: new Date().toISOString(),
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithResolvedState, total: 1 },
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
        // State badge (not the filter button)
        const stateBadges = screen.getAllByText("resolved");
        const stateBadge = stateBadges.find((el) =>
          el.classList.contains("rounded-full"),
        );
        expect(stateBadge).toBeInTheDocument();
        expect(stateBadge).toHaveClass("bg-green-100");
      });
    });

    it("should display silenced state alert with gray styling", async () => {
      const alertsWithSilencedState = [
        {
          alert_id: "alert-silenced",
          name: "Silenced State Alert",
          severity: "warning",
          state: "silenced",
          message: "Silenced alert",
          labels: { service: "test" },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithSilencedState, total: 1 },
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
        const silencedBadge = screen.getByText("silenced");
        expect(silencedBadge).toBeInTheDocument();
        expect(silencedBadge).toHaveClass("bg-gray-100");
      });
    });
  });

  describe("Alert Message Fallback Edge Cases", () => {
    it("should display annotation summary when message is empty", async () => {
      const alertsWithSummary = [
        {
          alert_id: "alert-summary",
          name: "Alert With Summary",
          severity: "warning",
          state: "firing",
          message: "",
          labels: { service: "test" },
          annotations: { summary: "This is the summary annotation" },
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithSummary, total: 1 },
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
        expect(
          screen.getByText("This is the summary annotation"),
        ).toBeInTheDocument();
      });
    });

    it("should display 'No description' when message and annotations are empty", async () => {
      const alertsWithNoDescription = [
        {
          alert_id: "alert-no-desc",
          name: "Alert With No Description",
          severity: "warning",
          state: "firing",
          message: "",
          labels: { service: "test" },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithNoDescription, total: 1 },
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
        expect(screen.getByText("No description")).toBeInTheDocument();
      });
    });

    it("should display alert without started_at date", async () => {
      const alertsWithoutStartedAt = [
        {
          alert_id: "alert-no-start",
          name: "Alert Without Start Time",
          severity: "warning",
          state: "pending",
          message: "Alert message",
          labels: { service: "test" },
          annotations: {},
          started_at: null,
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithoutStartedAt, total: 1 },
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
        expect(
          screen.getByText("Alert Without Start Time"),
        ).toBeInTheDocument();
        // Should NOT show "Started" text when started_at is null
        expect(screen.queryByText(/Started/)).not.toBeInTheDocument();
      });
    });

    it("should display external link when generator_url is present", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // First alert has generator_url
      const externalLinks = screen.getAllByTitle("View in Grafana");
      expect(externalLinks.length).toBeGreaterThan(0);
      expect(externalLinks[0]).toHaveAttribute(
        "href",
        "http://grafana/alerting/1",
      );
    });

    it("should not display external link when generator_url is null", async () => {
      const alertsWithoutGeneratorUrl = [
        {
          alert_id: "alert-no-url",
          name: "Alert Without Generator URL",
          severity: "warning",
          state: "firing",
          message: "Alert message",
          labels: {},
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithoutGeneratorUrl, total: 1 },
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
        expect(
          screen.getByText("Alert Without Generator URL"),
        ).toBeInTheDocument();
      });

      expect(screen.queryByTitle("View in Grafana")).not.toBeInTheDocument();
    });
  });

  describe("Loading States for Different Tabs", () => {
    it("should show loading skeleton for logs tab", async () => {
      mockUseListLogsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchLogs,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
      });
    });

    it("should show loading skeleton for metrics tab", async () => {
      mockUseGetMetricsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchMetrics,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
      });
    });

    it("should show loading skeleton for alerts tab", async () => {
      mockUseListAlertsQuery.mockReturnValue({
        data: null,
        isLoading: true,
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
        expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
      });
    });
  });

  describe("Error States for Different Tabs", () => {
    it("should show error for logs tab", async () => {
      mockUseListLogsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500 },
        refetch: mockRefetchLogs,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
      });
    });

    it("should show error for metrics tab", async () => {
      mockUseGetMetricsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500 },
        refetch: mockRefetchMetrics,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
      });
    });

    it("should show error for alerts tab", async () => {
      mockUseListAlertsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500 },
        refetch: mockRefetchAlerts,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
      });
    });
  });

  describe("Refresh Button for Different Tabs", () => {
    it("should call refetchTraces when refresh is clicked on traces tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchTraces).toHaveBeenCalled();
    });

    it("should call refetchLogs when refresh is clicked on logs tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchLogs).toHaveBeenCalled();
    });

    it("should call refetchMetrics when refresh is clicked on metrics tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(screen.getByText("Total Requests")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchMetrics).toHaveBeenCalled();
    });

    it("should call refetchAlerts when refresh is clicked on alerts tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchAlerts).toHaveBeenCalled();
    });
  });

  describe("Entity ID Filters", () => {
    it("should have user ID filter input", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText(/user id/i)).toBeInTheDocument();
    });

    it("should have workflow ID filter input", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText(/workflow id/i)).toBeInTheDocument();
    });

    it("should have project ID filter input", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText(/project id/i)).toBeInTheDocument();
    });

    it("should call hook with user_id filter when entered", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const userIdInput = screen.getByPlaceholderText(/user id/i);
      fireEvent.change(userIdInput, { target: { value: "user-123" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ user_id: "user-123" }),
        );
      });
    });

    it("should call hook with workflow_id filter when entered", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const workflowIdInput = screen.getByPlaceholderText(/workflow id/i);
      fireEvent.change(workflowIdInput, { target: { value: "workflow-456" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ workflow_id: "workflow-456" }),
        );
      });
    });

    it("should call hook with project_id filter when entered", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const projectIdInput = screen.getByPlaceholderText(/project id/i);
      fireEvent.change(projectIdInput, { target: { value: "project-789" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ project_id: "project-789" }),
        );
      });
    });
  });

  describe("Trace Selection and Detail View", () => {
    it("should select trace when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Click on the trace card
      fireEvent.click(screen.getByText("chat/completion"));

      // The trace should be selected (highlighted)
      await waitFor(() => {
        const traceCard = screen
          .getByText("chat/completion")
          .closest("[class*='cursor-pointer']");
        expect(traceCard).toHaveClass("border-blue-500");
      });
    });

    it("should show TraceViewer when trace is selected with data", async () => {
      // Mock the trace detail query to return data
      mockUseGetTraceQuery.mockReturnValue({
        data: {
          trace_id: "1",
          spans: [
            {
              span_id: "span-1",
              name: "Main Span",
              start_time: new Date().toISOString(),
              duration_ms: 100,
              status: "ok",
              depth: 0,
              attributes: {},
              events: [],
              error_message: null,
              parent_span_id: null,
            },
          ],
          start_time: new Date().toISOString(),
          end_time: new Date(Date.now() + 1000).toISOString(),
          duration_ms: 1000,
          service_name: "test-service",
        },
        isLoading: false,
        error: null,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Click on the trace card
      fireEvent.click(screen.getByText("chat/completion"));

      // Should show trace details panel
      await waitFor(() => {
        expect(screen.getByText("Trace Details")).toBeInTheDocument();
      });
    });

    it("should close TraceViewer when close button is clicked", async () => {
      mockUseGetTraceQuery.mockReturnValue({
        data: {
          trace_id: "1",
          spans: [],
          start_time: new Date().toISOString(),
          end_time: new Date(Date.now() + 1000).toISOString(),
          duration_ms: 1000,
          service_name: "test-service",
        },
        isLoading: false,
        error: null,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Click on the trace card
      fireEvent.click(screen.getByText("chat/completion"));

      await waitFor(() => {
        expect(screen.getByText("Trace Details")).toBeInTheDocument();
      });

      // Click close button
      fireEvent.click(screen.getByText("Close"));

      await waitFor(() => {
        expect(screen.queryByText("Trace Details")).not.toBeInTheDocument();
      });
    });
  });

  describe("Alert Filters Edge Cases", () => {
    it("should have severity filter dropdown", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should call alerts hook with state filter when selected", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // Click the Firing filter button
      fireEvent.click(screen.getByRole("button", { name: /^Firing$/i }));

      await waitFor(() => {
        expect(mockUseListAlertsQuery).toHaveBeenCalledWith(
          expect.objectContaining({ state: "firing" }),
          expect.anything(),
        );
      });
    });

    it("should call alerts hook with severity filter when selected", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });

      // Change the severity dropdown
      const severitySelect = screen.getByRole("combobox");
      fireEvent.change(severitySelect, { target: { value: "critical" } });

      await waitFor(() => {
        expect(mockUseListAlertsQuery).toHaveBeenCalledWith(
          expect.objectContaining({ severity: "critical" }),
          expect.anything(),
        );
      });
    });

    it("should show alert count", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /alerts/i }));

      await waitFor(() => {
        expect(screen.getByText("2 alerts")).toBeInTheDocument();
      });
    });
  });

  describe("Empty Metrics State", () => {
    it("should show empty state when no metrics data available", async () => {
      mockUseGetMetricsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        refetch: mockRefetchMetrics,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Metrics"));

      await waitFor(() => {
        expect(
          screen.getByText("No metrics data available"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Load More Button States", () => {
    it("should show loading state on Load More button when fetching", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: mockTraces,
          total: 100,
          limit: 50,
          next_cursor: "next-page-cursor",
        },
        isLoading: false,
        isFetching: true,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("Loading...")).toBeInTheDocument();
      });
    });

    it("should disable Load More button when fetching", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: mockTraces,
          total: 100,
          limit: 50,
          next_cursor: "next-page-cursor",
        },
        isLoading: false,
        isFetching: true,
        error: null,
        refetch: mockRefetchTraces,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      // Navigate to Distributed Traces tab
      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        const loadMoreButton = screen.getByRole("button", { name: /loading/i });
        expect(loadMoreButton).toBeDisabled();
      });
    });
  });

  describe("Alert Labels Display", () => {
    it("should not display alertname and severity in labels", async () => {
      const alertsWithFilteredLabels = [
        {
          alert_id: "alert-labels",
          name: "Alert With Labels",
          severity: "warning",
          state: "firing",
          message: "Alert message",
          labels: {
            alertname: "TestAlert",
            severity: "warning",
            service: "test-service",
            environment: "production",
          },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithFilteredLabels, total: 1 },
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
        expect(screen.getByText("Alert With Labels")).toBeInTheDocument();
      });

      // Should display service and environment
      expect(screen.getByText("service=test-service")).toBeInTheDocument();
      expect(screen.getByText("environment=production")).toBeInTheDocument();
      // Should NOT display alertname and severity in labels
      expect(screen.queryByText("alertname=TestAlert")).not.toBeInTheDocument();
      expect(screen.queryByText("severity=warning")).not.toBeInTheDocument();
    });

    it("should limit labels to 5 displayed", async () => {
      const alertsWithManyLabels = [
        {
          alert_id: "alert-many-labels",
          name: "Alert With Many Labels",
          severity: "warning",
          state: "firing",
          message: "Alert message",
          labels: {
            label1: "value1",
            label2: "value2",
            label3: "value3",
            label4: "value4",
            label5: "value5",
            label6: "value6",
            label7: "value7",
          },
          annotations: {},
          started_at: new Date().toISOString(),
          ended_at: null,
          generator_url: null,
        },
      ];

      mockUseListAlertsQuery.mockReturnValue({
        data: { items: alertsWithManyLabels, total: 1 },
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
        expect(screen.getByText("Alert With Many Labels")).toBeInTheDocument();
      });

      // Should only display 5 labels
      expect(screen.getByText("label1=value1")).toBeInTheDocument();
      expect(screen.getByText("label5=value5")).toBeInTheDocument();
      expect(screen.queryByText("label6=value6")).not.toBeInTheDocument();
      expect(screen.queryByText("label7=value7")).not.toBeInTheDocument();
    });
  });
});
