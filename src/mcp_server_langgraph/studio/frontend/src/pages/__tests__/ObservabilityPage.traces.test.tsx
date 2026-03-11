/**
 * ObservabilityPage Traces Tests
 *
 * Tests for Traces tab display, pagination, filters, time range, and status display.
 * Split from ObservabilityPage.test.tsx for memory optimization.
 *
 * @see ObservabilityPage.setup.ts for shared mocks and utilities
 * @see ObservabilityPage.traces-intelligence.test.tsx for AI integration tests
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
  mockRefetchTraces,
  mockTraces,
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

vi.mock("../../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: vi.fn(() => false),
  };
});
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

describe("ObservabilityPage - Traces", () => {
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
  // TRACES TAB TESTS
  // ===========================================================================

  describe("Traces Tab", () => {
    it("should display traces when navigating to Distributed Traces tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      expect(screen.getAllByText("success").length).toBeGreaterThan(0);
    });

    it("should show trace duration", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getAllByText(/ms/).length).toBeGreaterThan(0);
      });
    });

    it("should show empty state when no traces", async () => {
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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText(/No traces found/)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // TRACES PAGINATION
  // ===========================================================================

  describe("Traces Pagination", () => {
    it("should show Load More button when next_cursor is present", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: mockTraces,
          total: 100,
          limit: 50,
          nextCursor: "next-page-cursor",
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
        data: {
          items: mockTraces,
          total: 100,
          limit: 50,
          nextCursor: "next",
          hasNext: true,
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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText(/Showing 2 traces/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // TRACES FILTERS
  // ===========================================================================

  describe("Traces Filters", () => {
    it("should have status filter buttons", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^error$/i }));

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ status: "error" }),
          expect.any(Object),
        );
      });
    });
  });

  // ===========================================================================
  // TIME RANGE FILTER EDGE CASES
  // ===========================================================================

  describe("Time Range Filter Edge Cases", () => {
    it("should have default time range option selected", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const timeRangeSelect = screen.getByRole("combobox", {
        name: /time range/i,
      });
      expect(timeRangeSelect).toHaveValue("1h");
    });

    it("should support changing to 15m time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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
          expect.any(Object),
        );
      });
    });

    it("should support changing to 24h time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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
          expect.any(Object),
        );
      });
    });

    it("should support changing to 7d time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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
          expect.any(Object),
        );
      });
    });

    it("should support changing to all time range", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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
          expect.any(Object),
        );
      });
    });
  });

  // ===========================================================================
  // TRACE STATUS DISPLAY EDGE CASES
  // ===========================================================================

  describe("Trace Status Display Edge Cases", () => {
    it("should display error status with red styling", async () => {
      const tracesWithError = [
        {
          traceId: "error-trace",
          spanId: "s1",
          name: "failed/operation",
          startTime: new Date().toISOString(),
          endTime: new Date(Date.now() + 1000).toISOString(),
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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        const errorBadge = screen.getByText("error");
        expect(errorBadge).toBeInTheDocument();
        expect(errorBadge).toHaveClass("bg-error-3");
      });
    });

    it("should display running status with blue styling", async () => {
      const tracesWithRunning = [
        {
          traceId: "running-trace",
          spanId: "s1",
          name: "in-progress/operation",
          startTime: new Date().toISOString(),
          endTime: new Date(Date.now() + 1000).toISOString(),
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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        const runningBadge = screen.getByText("running");
        expect(runningBadge).toBeInTheDocument();
        expect(runningBadge).toHaveClass("bg-primary-3");
      });
    });

    it("should have running status filter button", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^running$/i }));

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ status: "running" }),
          expect.any(Object),
        );
      });
    });
  });

  // ===========================================================================
  // ENTITY ID FILTERS
  // ===========================================================================

  describe("Entity ID Filters", () => {
    it("should have user ID filter input", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const userIdInput = screen.getByPlaceholderText(/user id/i);
      fireEvent.change(userIdInput, { target: { value: "user-123" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ user_id: "user-123" }),
          expect.any(Object),
        );
      });
    });

    it("should call hook with workflow_id filter when entered", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const workflowIdInput = screen.getByPlaceholderText(/workflow id/i);
      fireEvent.change(workflowIdInput, { target: { value: "workflow-456" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ workflow_id: "workflow-456" }),
          expect.any(Object),
        );
      });
    });

    it("should call hook with project_id filter when entered", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      const projectIdInput = screen.getByPlaceholderText(/project id/i);
      fireEvent.change(projectIdInput, { target: { value: "project-789" } });

      await waitFor(() => {
        expect(mockUseListTracesQuery).toHaveBeenCalledWith(
          expect.objectContaining({ project_id: "project-789" }),
          expect.any(Object),
        );
      });
    });
  });

  // ===========================================================================
  // LOAD MORE BUTTON STATES
  // ===========================================================================

  describe("Load More Button States", () => {
    it("should show loading state on Load More button when fetching", async () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: mockTraces,
          total: 100,
          limit: 50,
          nextCursor: "next-page-cursor",
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
          nextCursor: "next-page-cursor",
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

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        const loadMoreButton = screen.getByRole("button", { name: /loading/i });
        expect(loadMoreButton).toBeDisabled();
      });
    });
  });

  // ===========================================================================
  // TRACE SELECTION AND DETAIL VIEW
  // ===========================================================================

  describe("Trace Selection and Detail View", () => {
    it("should select trace when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("chat/completion"));

      await waitFor(() => {
        const traceCard = screen
          .getByText("chat/completion")
          .closest("[class*='cursor-pointer']");
        expect(traceCard).toHaveClass("border-primary-9");
      });
    });

    it("should show TraceViewer when trace is selected with data", async () => {
      mockUseGetTraceQuery.mockReturnValue({
        data: {
          traceId: "1",
          spans: [
            {
              spanId: "span-1",
              name: "Main Span",
              startTime: new Date().toISOString(),
              durationMs: 100,
              status: "ok",
              depth: 0,
              attributes: {},
              events: [],
              errorMessage: null,
              parent_spanId: null,
            },
          ],
          startTime: new Date().toISOString(),
          endTime: new Date(Date.now() + 1000).toISOString(),
          durationMs: 1000,
          serviceName: "test-service",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("chat/completion"));

      await waitFor(() => {
        expect(screen.getByText("Trace Details")).toBeInTheDocument();
      });
    });

    it("should close TraceViewer when close button is clicked", async () => {
      mockUseGetTraceQuery.mockReturnValue({
        data: {
          traceId: "1",
          spans: [],
          startTime: new Date().toISOString(),
          endTime: new Date(Date.now() + 1000).toISOString(),
          durationMs: 1000,
          serviceName: "test-service",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("chat/completion"));

      await waitFor(() => {
        expect(screen.getByText("Trace Details")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Close"));

      await waitFor(() => {
        expect(screen.queryByText("Trace Details")).not.toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // TRACES REFRESH
  // ===========================================================================

  describe("Refresh Button for Traces Tab", () => {
    it("should call refetchTraces when refresh is clicked on traces tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      expect(mockRefetchTraces).toHaveBeenCalled();
    });
  });
});
