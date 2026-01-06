/**
 * ObservabilityPage Metrics Tests
 *
 * Tests for Metrics tab display and empty state.
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
  mockRefetchMetrics,
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

describe("ObservabilityPage - Metrics", () => {
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
  // METRICS TAB TESTS
  // ===========================================================================

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

  // ===========================================================================
  // EMPTY METRICS STATE
  // ===========================================================================

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

  // ===========================================================================
  // METRICS LOADING/ERROR STATES
  // ===========================================================================

  describe("Loading States for Metrics Tab", () => {
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
  });

  describe("Error States for Metrics Tab", () => {
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
  });

  describe("Refresh Button for Metrics Tab", () => {
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
  });
});
