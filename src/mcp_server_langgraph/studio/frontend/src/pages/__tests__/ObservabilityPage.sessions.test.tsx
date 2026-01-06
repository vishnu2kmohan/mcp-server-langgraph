/**
 * ObservabilityPage Sessions Tests
 *
 * Tests for Agent Sessions tab and Workflow Runs tab.
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
  mockRefetchSessions,
  mockRefetchWorkflows,
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

describe("ObservabilityPage - Sessions", () => {
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
  // AGENT SESSIONS TAB TESTS
  // ===========================================================================

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
        data: { items: [], total: 0, nextCursor: null },
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

  // ===========================================================================
  // WORKFLOW RUNS TAB TESTS
  // ===========================================================================

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
        data: { items: [], total: 0, nextCursor: null },
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
});
