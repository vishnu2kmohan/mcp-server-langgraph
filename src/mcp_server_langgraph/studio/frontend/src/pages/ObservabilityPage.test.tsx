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
import { TestRouter } from "../test-utils";

// Mock the RTK Query hooks
const mockRefetchTraces = vi.fn();
const mockRefetchLogs = vi.fn();
const mockRefetchMetrics = vi.fn();

vi.mock("../api", () => ({
  useListTracesQuery: vi.fn(),
  useListLogsQuery: vi.fn(),
  useGetMetricsQuery: vi.fn(),
  useGetTraceQuery: vi.fn(),
}));

import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useGetTraceQuery,
} from "../api";

// Cast to vi.Mock for type safety
const mockUseListTracesQuery = useListTracesQuery as ReturnType<typeof vi.fn>;
const mockUseListLogsQuery = useListLogsQuery as ReturnType<typeof vi.fn>;
const mockUseGetMetricsQuery = useGetMetricsQuery as ReturnType<typeof vi.fn>;
const mockUseGetTraceQuery = useGetTraceQuery as ReturnType<typeof vi.fn>;

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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      expect(screen.getByText("Observability")).toBeInTheDocument();
    });

    it("should display page description", () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      expect(
        screen.getByText(/Monitor traces, logs, and metrics/),
      ).toBeInTheDocument();
    });

    it("should have refresh button", () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      expect(screen.getByText("Refresh")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("should have Traces tab", () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      expect(screen.getByText("Traces")).toBeInTheDocument();
    });

    it("should have Logs tab", () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      expect(screen.getByText("Logs")).toBeInTheDocument();
    });

    it("should have Metrics tab", () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      expect(screen.getByText("Metrics")).toBeInTheDocument();
    });

    it("should switch to Logs tab when clicked", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      // Should have multiple skeleton items (3 by default)
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe("Traces Tab", () => {
    it("should display traces after loading", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });
    });

    it("should show trace status badges", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      // Check for status badge
      expect(screen.getAllByText("success").length).toBeGreaterThan(0);
    });

    it("should show trace duration", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/No traces found/)).toBeInTheDocument();
      });
    });
  });

  describe("Logs Tab", () => {
    it("should fetch and display logs when switching to Logs tab", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/2 of 100/i)).toBeInTheDocument();
      });
    });
  });

  describe("Traces Filters", () => {
    it("should have status filter buttons", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText(/session id/i)).toBeInTheDocument();
    });

    it("should have time range filter", async () => {
      render(
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
        <TestRouter>
          <ObservabilityPage />
        </TestRouter>,
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
});
