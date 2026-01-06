/**
 * ProjectDetailPage Observability Tests
 *
 * Tests for Observability Tab display, real data, logs, alerts, and error handling.
 * Split from ProjectDetailPage.test.tsx for memory optimization.
 *
 * @see ProjectDetailPage.setup.ts for shared mocks and utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, waitFor, cleanup } from "@testing-library/react";

// Import shared setup
import {
  resetAllMocks,
  setupDefaultMocks,
  mockRefetch as _mockRefetch,
  mockObservabilityData as _mockObservabilityData,
  renderWithRouter,
} from "./ProjectDetailPage.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetFeatureFlagsQuery: vi.fn(),
    useGetProjectQuery: vi.fn(),
    useGetProjectObservabilityQuery: vi.fn(),
    useGetProjectLogsQuery: vi.fn(),
    useGetProjectAlertsQuery: vi.fn(),
    useGetProjectCostSummaryQuery: vi.fn(),
    useGetProjectCostByModelQuery: vi.fn(),
    useAddProjectMemberMutation: vi.fn(),
    useRemoveProjectMemberMutation: vi.fn(),
    useAddProjectConnectionMutation: vi.fn(),
  };
});

// Import mocked hooks
import {
  useGetFeatureFlagsQuery,
  useGetProjectQuery,
  useGetProjectObservabilityQuery,
  useGetProjectLogsQuery,
  useGetProjectAlertsQuery,
  useGetProjectCostSummaryQuery,
  useGetProjectCostByModelQuery,
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
  useAddProjectConnectionMutation,
} from "../../api";

// Cast for type safety
const mockUseGetFeatureFlagsQuery = useGetFeatureFlagsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectQuery = useGetProjectQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectObservabilityQuery =
  useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectLogsQuery = useGetProjectLogsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectAlertsQuery = useGetProjectAlertsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectCostSummaryQuery =
  useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectCostByModelQuery =
  useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>;
const mockUseAddProjectMemberMutation =
  useAddProjectMemberMutation as ReturnType<typeof vi.fn>;
const mockUseRemoveProjectMemberMutation =
  useRemoveProjectMemberMutation as ReturnType<typeof vi.fn>;
const mockUseAddProjectConnectionMutation =
  useAddProjectConnectionMutation as ReturnType<typeof vi.fn>;

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("ProjectDetailPage - Observability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
    setupDefaultMocks({
      useGetFeatureFlagsQuery: mockUseGetFeatureFlagsQuery,
      useGetProjectQuery: mockUseGetProjectQuery,
      useGetProjectObservabilityQuery: mockUseGetProjectObservabilityQuery,
      useGetProjectLogsQuery: mockUseGetProjectLogsQuery,
      useGetProjectAlertsQuery: mockUseGetProjectAlertsQuery,
      useGetProjectCostSummaryQuery: mockUseGetProjectCostSummaryQuery,
      useGetProjectCostByModelQuery: mockUseGetProjectCostByModelQuery,
      useAddProjectMemberMutation: mockUseAddProjectMemberMutation,
      useRemoveProjectMemberMutation: mockUseRemoveProjectMemberMutation,
      useAddProjectConnectionMutation: mockUseAddProjectConnectionMutation,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // OBSERVABILITY TAB LINKS
  // ===========================================================================

  describe("Observability Tab Links", () => {
    it("should have link to full observability page", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        // Component shows links like "View traces →" - use exact text to avoid matching description text
        const viewTracesLink = screen.getByText("View traces →");
        expect(viewTracesLink).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // OBSERVABILITY TAB REAL DATA
  // ===========================================================================

  describe("ObservabilityTab Real Data", () => {
    it("should display trace count from RTK Query", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("100")).toBeInTheDocument(); // traceCount
      });
    });

    it("should display request metrics from RTK Query", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("500")).toBeInTheDocument(); // requestsTotal
        expect(screen.getByText("10")).toBeInTheDocument(); // errorsTotal
        expect(screen.getByText(/150/)).toBeInTheDocument(); // avgLatencyMs
      });
    });
  });

  // ===========================================================================
  // OBSERVABILITY TAB LOGS
  // ===========================================================================

  describe("ObservabilityTab Logs", () => {
    it("should display logs section", async () => {
      mockUseGetProjectLogsQuery.mockReturnValue({
        data: {
          logs: [
            {
              id: "log-1",
              level: "info",
              message: "Test log message",
              timestamp: "2025-01-01T00:00:00Z",
            },
            {
              id: "log-2",
              level: "error",
              message: "Error log message",
              timestamp: "2025-01-01T00:01:00Z",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Test log message")).toBeInTheDocument();
        expect(screen.getByText("Error log message")).toBeInTheDocument();
      });
    });

    it("should display log level badges", async () => {
      mockUseGetProjectLogsQuery.mockReturnValue({
        data: {
          logs: [
            {
              id: "log-1",
              level: "info",
              message: "Info log",
              timestamp: "2025-01-01T00:00:00Z",
            },
            {
              id: "log-2",
              level: "error",
              message: "Error log",
              timestamp: "2025-01-01T00:01:00Z",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("info")).toBeInTheDocument();
        expect(screen.getByText("error")).toBeInTheDocument();
      });
    });

    it("should show empty logs message when no logs", async () => {
      mockUseGetProjectLogsQuery.mockReturnValue({
        data: { logs: [], total: 0 },
        isLoading: false,
        error: null,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText(/No logs/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // OBSERVABILITY TAB ALERTS
  // ===========================================================================

  describe("ObservabilityTab Alerts", () => {
    it("should display alerts section", async () => {
      mockUseGetProjectAlertsQuery.mockReturnValue({
        data: {
          alerts: [
            {
              id: "alert-1",
              severity: "critical",
              message: "High CPU usage detected",
              created_at: "2025-01-01T00:00:00Z",
            },
            {
              id: "alert-2",
              severity: "warning",
              message: "Memory running low",
              created_at: "2025-01-01T00:01:00Z",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        // Component shows alert.message
        expect(screen.getByText("High CPU usage detected")).toBeInTheDocument();
        expect(screen.getByText("Memory running low")).toBeInTheDocument();
      });
    });

    it("should display alert severity badges", async () => {
      mockUseGetProjectAlertsQuery.mockReturnValue({
        data: {
          alerts: [
            {
              id: "alert-1",
              severity: "critical",
              message: "High CPU",
              created_at: "2025-01-01T00:00:00Z",
            },
            {
              id: "alert-2",
              severity: "warning",
              message: "Memory Low",
              created_at: "2025-01-01T00:01:00Z",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("critical")).toBeInTheDocument();
        expect(screen.getByText("warning")).toBeInTheDocument();
      });
    });

    it("should show empty alerts message when no alerts", async () => {
      mockUseGetProjectAlertsQuery.mockReturnValue({
        data: { alerts: [], total: 0 },
        isLoading: false,
        error: null,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        // Component shows "No active alerts"
        expect(screen.getByText(/No active alerts/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // OBSERVABILITY ERROR HANDLING
  // ===========================================================================

  describe("ObservabilityTab Error Handling", () => {
    it("should show error message when RTK Query returns error", async () => {
      mockUseGetProjectObservabilityQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it("should show retry button when RTK Query returns error", async () => {
      mockUseGetProjectObservabilityQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });
    });

    it("should refetch when retry button is clicked", async () => {
      const mockObsRefetch = vi.fn();

      mockUseGetProjectObservabilityQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: mockObsRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Retry/i }));

      expect(mockObsRefetch).toHaveBeenCalled();
    });
  });
});
