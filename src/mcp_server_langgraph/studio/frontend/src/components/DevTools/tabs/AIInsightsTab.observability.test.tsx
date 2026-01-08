/**
 * AIInsightsTab Observability Integration Tests (TDD RED Phase)
 *
 * Tests for Phase 8 AI Observability features:
 * - Integration with useObservabilityAI hook
 * - Natural Language Query interface
 * - Trace anomaly display
 * - Alert correlation display
 * - Cost prediction display
 * - Root cause analysis display
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  within,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AIInsightsTab } from "./AIInsightsTab";
import type { AIInsight } from "../types";

// =============================================================================
// Mock Data
// =============================================================================

const mockInsights: AIInsight[] = [
  {
    id: "insight-1",
    type: "anomaly",
    severity: "high",
    title: "High latency detected",
    description: "Node 3 took 500ms longer than average",
    timestamp: 1703000000000,
    confidence: 0.9,
    entityId: "session-123",
    suggestedAction: "Check network connectivity",
  },
];

const mockObservabilityInsights = {
  traceAnomalies: {
    slowSpans: [
      { spanId: "span-1", durationMs: 1500, name: "db.query", status: "ok" },
      {
        spanId: "span-2",
        durationMs: 2000,
        name: "llm.completion",
        status: "ok",
      },
    ],
    errorPatterns: [
      { name: "api.request", count: 3 },
      { name: "auth.validate", count: 2 },
    ],
    percentiles: { p50: 150, p95: 800, p99: 1500 },
  },
  alertCorrelations: [
    {
      alerts: ["alert-1", "alert-2"],
      services: ["api-gateway", "db-service"],
      timeWindow: { start: 1703000000000, end: 1703000300000 },
    },
  ],
  costPrediction: {
    trend: "increasing" as const,
    projectedDaily: 25.5,
    anomalies: [{ timestamp: 1703000000000, value: 500 }],
  },
  rootCauseAnalysis: {
    hypothesis: "Database connectivity issues causing API failures",
    confidence: 0.85,
    rootCauses: [
      {
        description: "Database connectivity issues causing API failures",
        likelihood: 0.85,
      },
      {
        description: "Resource exhaustion leading to timeouts",
        likelihood: 0.7,
      },
    ],
    suggestedActions: [
      "Check database connection pool settings",
      "Review resource limits and scaling policies",
    ],
  },
};

// =============================================================================
// Mock Hooks
// =============================================================================

const mockUseDevToolsAI = vi.fn().mockReturnValue({
  insights: mockInsights,
  suggestedLayout: null,
  confidence: 0,
  isLoading: false,
  error: null,
  dismissInsight: vi.fn(),
  applyLayout: vi.fn(),
  fetchSuggestions: vi.fn(),
});

const mockUseObservabilityAI = vi.fn().mockReturnValue({
  insights: mockObservabilityInsights,
  suggestedActions: [
    {
      id: "optimize-slow-spans",
      title: "Optimize Slow Operations",
      description: "2 slow operations detected",
      priority: "high",
      category: "performance",
    },
  ],
  isAnalyzing: false,
  refresh: vi.fn(),
});

vi.mock("../hooks/useDevToolsAI", () => ({
  useDevToolsAI: (options: unknown) => mockUseDevToolsAI(options),
}));

vi.mock("../hooks/useObservabilityAI", () => ({
  useObservabilityAI: (options: unknown) => mockUseObservabilityAI(options),
}));

// Mock Redux store hooks
vi.mock("../../../store/hooks", () => ({
  useAppSelector: vi.fn(() => ({ id: "test-user-id", username: "testuser" })),
  useAppDispatch: vi.fn(() => vi.fn()),
}));

vi.mock("../../../store/slices/authSlice", () => ({
  selectUser: vi.fn(),
}));

// =============================================================================
// Tests: Observability Integration
// =============================================================================

describe("AIInsightsTab - Observability Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDevToolsAI.mockReturnValue({
      insights: mockInsights,
      suggestedLayout: null,
      confidence: 0,
      isLoading: false,
      error: null,
      dismissInsight: vi.fn(),
      applyLayout: vi.fn(),
      fetchSuggestions: vi.fn(),
    });
    mockUseObservabilityAI.mockReturnValue({
      insights: mockObservabilityInsights,
      suggestedActions: [],
      isAnalyzing: false,
      refresh: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("observability toggle", () => {
    it("should show observability toggle when enableObservability prop is true", () => {
      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      // TDD RED: Toggle doesn't exist yet
      expect(
        screen.getByTestId("observability-insights-toggle"),
      ).toBeInTheDocument();
    });

    it("should toggle between AI insights and observability insights", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      // TDD RED: Toggle functionality doesn't exist yet
      const toggle = screen.getByTestId("observability-insights-toggle");
      await user.click(toggle);

      expect(
        screen.getByTestId("observability-insights-panel"),
      ).toBeInTheDocument();
    });

    it("should not show observability toggle when enableObservability is false", () => {
      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={false}
        />,
      );

      expect(
        screen.queryByTestId("observability-insights-toggle"),
      ).not.toBeInTheDocument();
    });
  });

  describe("trace anomalies display", () => {
    it("should display slow spans in observability panel", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      // Toggle to observability view
      await user.click(screen.getByTestId("observability-insights-toggle"));

      // Slow spans section should exist with span data
      const slowSpansSection = screen.getByTestId("slow-spans-section");
      expect(slowSpansSection).toBeInTheDocument();
      expect(
        within(slowSpansSection).getByText(/db\.query/),
      ).toBeInTheDocument();
      // Duration is rendered as "1500ms" (text node may be split)
      expect(within(slowSpansSection).getByText("1500ms")).toBeInTheDocument();
    });

    it("should display error patterns", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      // TDD RED: Error patterns section doesn't exist yet
      expect(screen.getByTestId("error-patterns-section")).toBeInTheDocument();
      expect(screen.getByText(/api\.request/)).toBeInTheDocument();
      expect(screen.getByText(/3 occurrences/i)).toBeInTheDocument();
    });

    it("should display latency percentiles", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      // TDD RED: Percentiles display doesn't exist yet
      expect(screen.getByTestId("latency-percentiles")).toBeInTheDocument();
      expect(screen.getByText(/p50: 150ms/i)).toBeInTheDocument();
      expect(screen.getByText(/p95: 800ms/i)).toBeInTheDocument();
      expect(screen.getByText(/p99: 1500ms/i)).toBeInTheDocument();
    });
  });

  describe("alert correlations display", () => {
    it("should display correlated alerts", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      // TDD RED: Alert correlations section doesn't exist yet
      expect(
        screen.getByTestId("alert-correlations-section"),
      ).toBeInTheDocument();
      expect(screen.getByText(/2 alerts correlated/i)).toBeInTheDocument();
    });

    it("should show affected services in correlation", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      expect(screen.getByText(/api-gateway/)).toBeInTheDocument();
      expect(screen.getByText(/db-service/)).toBeInTheDocument();
    });
  });

  describe("cost prediction display", () => {
    it("should display cost trend", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      // TDD RED: Cost prediction section doesn't exist yet
      expect(screen.getByTestId("cost-prediction-section")).toBeInTheDocument();
      expect(screen.getByText(/increasing/i)).toBeInTheDocument();
    });

    it("should display projected daily cost", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      expect(screen.getByText(/\$25\.50/)).toBeInTheDocument();
    });

    it("should highlight cost anomalies", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      expect(screen.getByTestId("cost-anomaly-indicator")).toBeInTheDocument();
    });
  });

  describe("root cause analysis display", () => {
    it("should display hypothesis with confidence", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      // RCA section should exist with hypothesis and confidence
      const rcaSection = screen.getByTestId("root-cause-analysis-section");
      expect(rcaSection).toBeInTheDocument();
      // Check that the hypothesis text appears in the RCA section (may appear multiple times)
      const hypothesisElements = within(rcaSection).getAllByText(
        /Database connectivity issues/,
      );
      expect(hypothesisElements.length).toBeGreaterThan(0);
      // Check confidence percentage appears
      const confidenceElements = within(rcaSection).getAllByText(/85%/);
      expect(confidenceElements.length).toBeGreaterThan(0);
    });

    it("should display suggested actions from RCA", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      expect(
        screen.getByText(/Check database connection pool settings/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Review resource limits and scaling policies/),
      ).toBeInTheDocument();
    });

    it("should display multiple root causes ranked by likelihood", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableObservability={true}
        />,
      );

      await user.click(screen.getByTestId("observability-insights-toggle"));

      const rcaSection = screen.getByTestId("root-cause-analysis-section");
      const rootCauses = within(rcaSection).getAllByTestId(/root-cause-/);
      expect(rootCauses).toHaveLength(2);
    });
  });
});

// =============================================================================
// Tests: Natural Language Query Interface
// =============================================================================

describe("AIInsightsTab - Natural Language Query", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDevToolsAI.mockReturnValue({
      insights: mockInsights,
      suggestedLayout: null,
      confidence: 0,
      isLoading: false,
      error: null,
      dismissInsight: vi.fn(),
      applyLayout: vi.fn(),
      fetchSuggestions: vi.fn(),
    });
    mockUseObservabilityAI.mockReturnValue({
      insights: mockObservabilityInsights,
      suggestedActions: [],
      isAnalyzing: false,
      refresh: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("query input", () => {
    it("should show natural language query input when enableNLQuery is true", () => {
      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={true}
        />,
      );

      // TDD RED: NL query input doesn't exist yet
      expect(screen.getByTestId("nl-query-input")).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText(/ask about your traces/i),
      ).toBeInTheDocument();
    });

    it("should not show NL query input when enableNLQuery is false", () => {
      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={false}
        />,
      );

      expect(screen.queryByTestId("nl-query-input")).not.toBeInTheDocument();
    });

    it("should submit query on Enter", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={true}
        />,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(
        input,
        "What caused the 500 error spike at 10:45?{Enter}",
      );

      // TDD RED: Query submission doesn't exist yet
      expect(screen.getByTestId("nl-query-loading")).toBeInTheDocument();
    });

    it("should show query response after submission", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={true}
        />,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "What caused the 500 error spike?{Enter}");

      // Wait for mock response
      await waitFor(() => {
        expect(screen.getByTestId("nl-query-response")).toBeInTheDocument();
      });
    });
  });

  describe("query suggestions", () => {
    it("should show suggested queries", () => {
      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={true}
        />,
      );

      // TDD RED: Query suggestions don't exist yet
      expect(screen.getByTestId("nl-query-suggestions")).toBeInTheDocument();
    });

    it("should populate input when suggestion is clicked", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={true}
        />,
      );

      const suggestions = screen.getByTestId("nl-query-suggestions");
      const firstSuggestion = within(suggestions).getAllByRole("button")[0];
      await user.click(firstSuggestion);

      const input = screen.getByTestId("nl-query-input");
      // Input should have a value (the suggestion text)
      expect(input).toHaveValue();
    });
  });

  describe("query history", () => {
    it("should show recent queries", async () => {
      const user = userEvent.setup();

      render(
        <AIInsightsTab
          context="session"
          contextEntityId="session-123"
          enableNLQuery={true}
        />,
      );

      // Submit a query first
      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "Show me slow queries{Enter}");

      await waitFor(() => {
        expect(screen.getByTestId("nl-query-response")).toBeInTheDocument();
      });

      // Check query history
      expect(screen.getByTestId("nl-query-history")).toBeInTheDocument();
      expect(screen.getByText(/Show me slow queries/)).toBeInTheDocument();
    });
  });
});

// =============================================================================
// Tests: Predictive Alerts
// =============================================================================

describe("AIInsightsTab - Predictive Alerts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("should display predictive alerts section when available", async () => {
    const user = userEvent.setup();

    mockUseObservabilityAI.mockReturnValue({
      insights: {
        ...mockObservabilityInsights,
        predictiveAlerts: [
          {
            id: "pred-1",
            type: "memory_pressure",
            probability: 0.75,
            estimatedTimeToFire: 15 * 60 * 1000, // 15 minutes
            message: "Memory usage trending toward threshold",
            suggestedAction: "Consider scaling up or reviewing memory usage",
          },
        ],
      },
      suggestedActions: [],
      isAnalyzing: false,
      refresh: vi.fn(),
    });

    render(
      <AIInsightsTab
        context="session"
        contextEntityId="session-123"
        enableObservability={true}
      />,
    );

    await user.click(screen.getByTestId("observability-insights-toggle"));

    // TDD RED: Predictive alerts section doesn't exist yet
    expect(screen.getByTestId("predictive-alerts-section")).toBeInTheDocument();
    expect(
      screen.getByText(/Memory usage trending toward threshold/),
    ).toBeInTheDocument();
    expect(screen.getByText(/75% probability/i)).toBeInTheDocument();
    expect(screen.getByText(/in 15 minutes/i)).toBeInTheDocument();
  });

  it("should show preventive action button for predictive alerts", async () => {
    const user = userEvent.setup();

    mockUseObservabilityAI.mockReturnValue({
      insights: {
        ...mockObservabilityInsights,
        predictiveAlerts: [
          {
            id: "pred-1",
            type: "disk_space",
            probability: 0.9,
            estimatedTimeToFire: 60 * 60 * 1000, // 1 hour
            message: "Disk space running low",
            suggestedAction: "Clean up old logs or expand storage",
          },
        ],
      },
      suggestedActions: [],
      isAnalyzing: false,
      refresh: vi.fn(),
    });

    render(
      <AIInsightsTab
        context="session"
        contextEntityId="session-123"
        enableObservability={true}
      />,
    );

    await user.click(screen.getByTestId("observability-insights-toggle"));

    expect(
      screen.getByTestId("predictive-alert-action-pred-1"),
    ).toBeInTheDocument();
  });

  it("should highlight high probability predictive alerts", async () => {
    const user = userEvent.setup();

    mockUseObservabilityAI.mockReturnValue({
      insights: {
        ...mockObservabilityInsights,
        predictiveAlerts: [
          {
            id: "pred-critical",
            type: "cpu_spike",
            probability: 0.95,
            estimatedTimeToFire: 5 * 60 * 1000, // 5 minutes
            message: "CPU spike imminent",
            suggestedAction: "Scale horizontally",
          },
        ],
      },
      suggestedActions: [],
      isAnalyzing: false,
      refresh: vi.fn(),
    });

    render(
      <AIInsightsTab
        context="session"
        contextEntityId="session-123"
        enableObservability={true}
      />,
    );

    await user.click(screen.getByTestId("observability-insights-toggle"));

    const alert = screen.getByTestId("predictive-alert-pred-critical");
    expect(alert).toHaveClass("bg-error-100");
  });
});

// =============================================================================
// Tests: Combined View
// =============================================================================

describe("AIInsightsTab - Combined Insights View", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDevToolsAI.mockReturnValue({
      insights: mockInsights,
      suggestedLayout: null,
      confidence: 0,
      isLoading: false,
      error: null,
      dismissInsight: vi.fn(),
      applyLayout: vi.fn(),
      fetchSuggestions: vi.fn(),
    });
    mockUseObservabilityAI.mockReturnValue({
      insights: mockObservabilityInsights,
      suggestedActions: [
        {
          id: "action-1",
          title: "Optimize Slow Operations",
          description: "2 slow operations detected",
          priority: "high",
          category: "performance",
        },
      ],
      isAnalyzing: false,
      refresh: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("should merge AI and observability suggested actions", () => {
    render(
      <AIInsightsTab
        context="session"
        contextEntityId="session-123"
        enableObservability={true}
      />,
    );

    // TDD RED: Combined actions view doesn't exist yet
    expect(screen.getByTestId("suggested-actions-panel")).toBeInTheDocument();
    expect(screen.getByText(/Optimize Slow Operations/)).toBeInTheDocument();
  });

  it("should prioritize high-priority actions", () => {
    render(
      <AIInsightsTab
        context="session"
        contextEntityId="session-123"
        enableObservability={true}
      />,
    );

    const actionsPanel = screen.getByTestId("suggested-actions-panel");
    const actions = within(actionsPanel).getAllByTestId(/suggested-action-/);

    // First action should be high priority
    expect(actions[0]).toHaveAttribute("data-priority", "high");
  });

  it("should call both refresh functions when refresh clicked", async () => {
    const user = userEvent.setup();
    const mockAIRefresh = vi.fn();
    const mockObsRefresh = vi.fn();

    mockUseDevToolsAI.mockReturnValue({
      insights: mockInsights,
      suggestedLayout: null,
      confidence: 0,
      isLoading: false,
      error: null,
      dismissInsight: vi.fn(),
      applyLayout: vi.fn(),
      fetchSuggestions: mockAIRefresh,
    });

    mockUseObservabilityAI.mockReturnValue({
      insights: mockObservabilityInsights,
      suggestedActions: [],
      isAnalyzing: false,
      refresh: mockObsRefresh,
    });

    render(
      <AIInsightsTab
        context="session"
        contextEntityId="session-123"
        enableObservability={true}
      />,
    );

    await user.click(screen.getByTestId("refresh-insights-button"));

    expect(mockAIRefresh).toHaveBeenCalled();
    expect(mockObsRefresh).toHaveBeenCalled();
  });
});
