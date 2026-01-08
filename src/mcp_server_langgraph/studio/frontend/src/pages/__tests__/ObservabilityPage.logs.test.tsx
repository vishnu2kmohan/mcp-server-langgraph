/**
 * ObservabilityPage Logs Tests
 *
 * Tests for Logs tab display, level badges, and edge cases.
 * Split from ObservabilityPage.test.tsx for memory optimization.
 *
 * @see ObservabilityPage.setup.ts for shared mocks and utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { ObservabilityPage } from "../ObservabilityPage";
import { TestProvider } from "../../test-utils";

// Import shared setup
import {
  resetAllMocks,
  setupDefaultMocks,
  mockRefetchLogs,
} from "./ObservabilityPage.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
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

vi.mock("../../hooks/useTraceIntelligence", () => ({
  useTraceSummary: vi.fn(() => ({
    summary: null,
    totalDurationMs: null,
    stepCount: null,
    toolCallCount: null,
    success: null,
    keyActions: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useTraceAnomaly: vi.fn(() => ({
    anomalies: [],
    bottlenecks: [],
    healthScore: null,
    optimizationSuggestions: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: vi.fn(() => false),
}));

// Import mocked hooks
import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useGetTraceQuery,
  useListAlertsQuery,
  useListSessionsQuery,
  useListWorkflowsQuery,
} from "../../api";

// Cast for type safety
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

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("ObservabilityPage - Logs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
    setupDefaultMocks({
      useListTracesQuery: mockUseListTracesQuery,
      useListLogsQuery: mockUseListLogsQuery,
      useGetMetricsQuery: mockUseGetMetricsQuery,
      useGetTraceQuery: mockUseGetTraceQuery,
      useListAlertsQuery: mockUseListAlertsQuery,
      useListSessionsQuery: mockUseListSessionsQuery,
      useListWorkflowsQuery: mockUseListWorkflowsQuery,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // LOGS TAB TESTS
  // ===========================================================================

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

  // ===========================================================================
  // LOG LEVEL DISPLAY EDGE CASES
  // ===========================================================================

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
        expect(warnBadge).toHaveClass("bg-warning-100");
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

  // ===========================================================================
  // LOGS LOADING/ERROR STATES
  // ===========================================================================

  describe("Loading States for Logs Tab", () => {
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
  });

  describe("Error States for Logs Tab", () => {
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
  });

  describe("Refresh Button for Logs Tab", () => {
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
  });
});
