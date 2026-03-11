/**
 * ObservabilityPage Trace Intelligence Tests
 *
 * Tests for AI-powered trace analysis, summaries, anomalies, and optimization suggestions.
 * Split from ObservabilityPage.test.tsx for memory optimization.
 *
 * @see ObservabilityPage.setup.ts for shared mocks and utilities
 * @see ObservabilityPage.traces.test.tsx for core traces tests
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
  mockTraceSummary,
  mockTraceAnomaly,
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
  useTraceSummary: vi.fn(() => mockTraceSummary),
  useTraceAnomaly: vi.fn(() => mockTraceAnomaly),
}));

vi.mock("../../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: vi.fn(() => false),
  };
});
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";
import {
  useTraceSummary,
  useTraceAnomaly,
} from "../../hooks/useTraceIntelligence";

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
const mockUseFeatureFlag = useFeatureFlag as ReturnType<typeof vi.fn>;
const mockUseTraceSummary = useTraceSummary as ReturnType<typeof vi.fn>;
const mockUseTraceAnomaly = useTraceAnomaly as ReturnType<typeof vi.fn>;

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("ObservabilityPage - Trace Intelligence", () => {
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

    // Enable AI feature flag for trace intelligence tests
    mockUseFeatureFlag.mockReturnValue(true);

    // Mock trace detail query to return data
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
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    // Reset to default disabled state
    mockUseFeatureFlag.mockReturnValue(false);
    mockUseTraceSummary.mockReturnValue(mockTraceSummary);
    mockUseTraceAnomaly.mockReturnValue(mockTraceAnomaly);
  });

  // ===========================================================================
  // AI INSIGHTS PANEL
  // ===========================================================================

  describe("AI Insights Panel", () => {
    it("should show AI Insights panel when trace is selected and AI is enabled", async () => {
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
        expect(
          screen.getByTestId("trace-intelligence-panel"),
        ).toBeInTheDocument();
        expect(screen.getByText("AI Insights")).toBeInTheDocument();
      });
    });

    it("should not show AI Insights panel when AI feature flag is disabled", async () => {
      mockUseFeatureFlag.mockReturnValue(false);

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

      expect(
        screen.queryByTestId("trace-intelligence-panel"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // TRACE SUMMARY
  // ===========================================================================

  describe("Trace Summary", () => {
    it("should display trace summary when available", async () => {
      mockUseTraceSummary.mockReturnValue({
        ...mockTraceSummary,
        summary: "Agent successfully processed 3 user requests",
        totalDurationMs: 2500,
        stepCount: 5,
        toolCallCount: 2,
        success: true,
        keyActions: ["search", "analyze", "respond"],
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
        expect(
          screen.getByText("Agent successfully processed 3 user requests"),
        ).toBeInTheDocument();
      });

      expect(screen.getByText("5 steps")).toBeInTheDocument();
      expect(screen.getByText("2 tool calls")).toBeInTheDocument();
      expect(screen.getByText("2500ms total")).toBeInTheDocument();

      expect(screen.getByText("search")).toBeInTheDocument();
      expect(screen.getByText("analyze")).toBeInTheDocument();
      expect(screen.getByText("respond")).toBeInTheDocument();
    });

    it("should show loading state for trace summary", async () => {
      mockUseTraceSummary.mockReturnValue({
        ...mockTraceSummary,
        isLoading: true,
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
        expect(screen.getByText("Analyzing trace...")).toBeInTheDocument();
      });
    });

    it("should show 'No summary available' when summary is empty", async () => {
      mockUseTraceSummary.mockReturnValue({
        ...mockTraceSummary,
        summary: null,
        isLoading: false,
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
        expect(screen.getByText("No summary available")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // HEALTH SCORE
  // ===========================================================================

  describe("Health Score", () => {
    it("should display health score when available", async () => {
      mockUseTraceAnomaly.mockReturnValue({
        ...mockTraceAnomaly,
        healthScore: 85,
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
        expect(screen.getByText("85/100")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // BOTTLENECKS
  // ===========================================================================

  describe("Bottlenecks", () => {
    it("should display bottlenecks when detected", async () => {
      mockUseTraceAnomaly.mockReturnValue({
        ...mockTraceAnomaly,
        healthScore: 70,
        bottlenecks: [
          {
            stepName: "llm_call",
            durationMs: 1500,
            percentageOfTotal: 60,
          },
          {
            stepName: "db_query",
            durationMs: 500,
            percentageOfTotal: 20,
          },
        ],
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
        expect(screen.getByText("llm_call")).toBeInTheDocument();
        expect(screen.getByText("db_query")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // ANOMALIES
  // ===========================================================================

  describe("Anomalies", () => {
    it("should display anomalies when detected", async () => {
      mockUseTraceAnomaly.mockReturnValue({
        ...mockTraceAnomaly,
        healthScore: 50,
        anomalies: [
          {
            type: "slow_step",
            stepName: "external_api",
            severity: "warning",
            message: "Step took 3x longer than average",
            suggestedFix: "Consider caching API responses",
          },
          {
            type: "error",
            stepName: "parser",
            severity: "error",
            message: "Parsing failed for input",
          },
        ],
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
        expect(
          screen.getByText("external_api: Step took 3x longer than average"),
        ).toBeInTheDocument();
        expect(
          screen.getByText("parser: Parsing failed for input"),
        ).toBeInTheDocument();
      });
    });

    it("should show 'No issues detected' when trace is healthy", async () => {
      mockUseTraceAnomaly.mockReturnValue({
        ...mockTraceAnomaly,
        healthScore: 95,
        anomalies: [],
        bottlenecks: [],
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
        expect(screen.getByText("No issues detected")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // OPTIMIZATION SUGGESTIONS
  // ===========================================================================

  describe("Optimization Suggestions", () => {
    it("should display optimization suggestions when available", async () => {
      mockUseTraceAnomaly.mockReturnValue({
        ...mockTraceAnomaly,
        healthScore: 75,
        optimizationSuggestions: [
          "Consider parallelizing independent steps",
          "Use streaming for large payloads",
          "Cache frequently accessed data",
        ],
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
        expect(
          screen.getByText("Consider parallelizing independent steps"),
        ).toBeInTheDocument();
        expect(
          screen.getByText("Use streaming for large payloads"),
        ).toBeInTheDocument();
        expect(
          screen.getByText("Cache frequently accessed data"),
        ).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // ANOMALY LOADING STATE
  // ===========================================================================

  describe("Anomaly Loading State", () => {
    it("should show loading state for anomaly detection", async () => {
      mockUseTraceAnomaly.mockReturnValue({
        ...mockTraceAnomaly,
        isLoading: true,
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
        expect(screen.getByText("Detecting anomalies...")).toBeInTheDocument();
      });
    });
  });
});
