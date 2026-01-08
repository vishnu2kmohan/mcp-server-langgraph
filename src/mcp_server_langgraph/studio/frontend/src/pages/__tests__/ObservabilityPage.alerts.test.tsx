/**
 * ObservabilityPage Alerts Tests
 *
 * Tests for Alerts tab display, severity/state badges, filters, and edge cases.
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
  mockRefetchAlerts,
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

describe("ObservabilityPage - Alerts", () => {
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
  // ALERTS TAB TESTS
  // ===========================================================================

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

  // ===========================================================================
  // ALERT SEVERITY EDGE CASES
  // ===========================================================================

  describe("Alert Severity Edge Cases", () => {
    it("should display error severity alert with orange styling", async () => {
      const alertsWithErrorSeverity = [
        {
          alertId: "alert-error",
          name: "Error Severity Alert",
          severity: "error",
          state: "firing",
          message: "Error level alert",
          labels: { service: "test" },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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
        const severityBadges = screen.getAllByText("error");
        const severityBadge = severityBadges.find((el) =>
          el.classList.contains("bg-grafana-100"),
        );
        expect(severityBadge).toBeInTheDocument();
      });
    });

    it("should display info severity alert with blue styling", async () => {
      const alertsWithInfoSeverity = [
        {
          alertId: "alert-info",
          name: "Info Severity Alert",
          severity: "info",
          state: "pending",
          message: "Info level alert",
          labels: { service: "test" },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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
        expect(infoBadge).toHaveClass("bg-primary-100");
      });
    });
  });

  // ===========================================================================
  // ALERT STATE EDGE CASES
  // ===========================================================================

  describe("Alert State Edge Cases", () => {
    it("should display pending state alert with yellow styling", async () => {
      const alertsWithPendingState = [
        {
          alertId: "alert-pending",
          name: "Pending State Alert",
          severity: "warning",
          state: "pending",
          message: "Pending alert",
          labels: { service: "test" },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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
        const stateBadges = screen.getAllByText("pending");
        const stateBadge = stateBadges.find((el) =>
          el.classList.contains("rounded-full"),
        );
        expect(stateBadge).toBeInTheDocument();
        expect(stateBadge).toHaveClass("bg-warning-100");
      });
    });

    it("should display resolved state alert with green styling", async () => {
      const alertsWithResolvedState = [
        {
          alertId: "alert-resolved",
          name: "Resolved State Alert",
          severity: "info",
          state: "resolved",
          message: "Resolved alert",
          labels: { service: "test" },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: new Date().toISOString(),
          generatorUrl: null,
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
        const stateBadges = screen.getAllByText("resolved");
        const stateBadge = stateBadges.find((el) =>
          el.classList.contains("rounded-full"),
        );
        expect(stateBadge).toBeInTheDocument();
        expect(stateBadge).toHaveClass("bg-success-100");
      });
    });

    it("should display silenced state alert with gray styling", async () => {
      const alertsWithSilencedState = [
        {
          alertId: "alert-silenced",
          name: "Silenced State Alert",
          severity: "warning",
          state: "silenced",
          message: "Silenced alert",
          labels: { service: "test" },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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

  // ===========================================================================
  // ALERT MESSAGE FALLBACK EDGE CASES
  // ===========================================================================

  describe("Alert Message Fallback Edge Cases", () => {
    it("should display annotation summary when message is empty", async () => {
      const alertsWithSummary = [
        {
          alertId: "alert-summary",
          name: "Alert With Summary",
          severity: "warning",
          state: "firing",
          message: "",
          labels: { service: "test" },
          annotations: { summary: "This is the summary annotation" },
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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
          alertId: "alert-no-desc",
          name: "Alert With No Description",
          severity: "warning",
          state: "firing",
          message: "",
          labels: { service: "test" },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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
          alertId: "alert-no-start",
          name: "Alert Without Start Time",
          severity: "warning",
          state: "pending",
          message: "Alert message",
          labels: { service: "test" },
          annotations: {},
          startedAt: null,
          endedAt: null,
          generatorUrl: null,
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
          alertId: "alert-no-url",
          name: "Alert Without Generator URL",
          severity: "warning",
          state: "firing",
          message: "Alert message",
          labels: {},
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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

  // ===========================================================================
  // ALERT FILTERS EDGE CASES
  // ===========================================================================

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

  // ===========================================================================
  // ALERT LABELS DISPLAY
  // ===========================================================================

  describe("Alert Labels Display", () => {
    it("should not display alertname and severity in labels", async () => {
      const alertsWithFilteredLabels = [
        {
          alertId: "alert-labels",
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
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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

      expect(screen.getByText("service=test-service")).toBeInTheDocument();
      expect(screen.getByText("environment=production")).toBeInTheDocument();
      expect(screen.queryByText("alertname=TestAlert")).not.toBeInTheDocument();
      expect(screen.queryByText("severity=warning")).not.toBeInTheDocument();
    });

    it("should limit labels to 5 displayed", async () => {
      const alertsWithManyLabels = [
        {
          alertId: "alert-many-labels",
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
          startedAt: new Date().toISOString(),
          endedAt: null,
          generatorUrl: null,
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

      expect(screen.getByText("label1=value1")).toBeInTheDocument();
      expect(screen.getByText("label5=value5")).toBeInTheDocument();
      expect(screen.queryByText("label6=value6")).not.toBeInTheDocument();
      expect(screen.queryByText("label7=value7")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // ALERTS LOADING/ERROR/REFRESH STATES
  // ===========================================================================

  describe("Loading States for Alerts Tab", () => {
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

  describe("Error States for Alerts Tab", () => {
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

  describe("Refresh Button for Alerts Tab", () => {
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
});
