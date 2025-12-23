/**
 * AIInsightsTab Tests
 *
 * TDD tests for the AI Insights tab in DevTools.
 * Displays AI-generated insights, anomalies, and suggestions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within, fireEvent, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

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
  {
    id: "insight-2",
    type: "performance",
    severity: "medium",
    title: "Token usage spike",
    description: "Last 5 messages used 2x average tokens",
    timestamp: 1703000001000,
    confidence: 0.85,
    entityId: "session-123",
  },
  {
    id: "insight-3",
    type: "suggestion",
    severity: "low",
    title: "Optimization available",
    description: "Consider caching repeated prompts",
    timestamp: 1703000002000,
    confidence: 0.75,
    suggestedAction: "Enable prompt caching",
  },
  {
    id: "insight-4",
    type: "cost",
    severity: "medium",
    title: "Cost projection",
    description: "Estimated daily cost: $12.50 based on current usage",
    timestamp: 1703000003000,
    confidence: 0.8,
  },
];

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

vi.mock("../hooks/useDevToolsAI", () => ({
  useDevToolsAI: (options: unknown) => mockUseDevToolsAI(options),
}));

// =============================================================================
// Tests
// =============================================================================

describe("AIInsightsTab", () => {
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
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("ai-insights-tab")).toBeInTheDocument();
    });

    it("should display insights", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByText("High latency detected")).toBeInTheDocument();
      expect(screen.getByText("Token usage spike")).toBeInTheDocument();
      expect(screen.getByText("Optimization available")).toBeInTheDocument();
    });

    it("should show loading state", () => {
      mockUseDevToolsAI.mockReturnValue({
        insights: [],
        suggestedLayout: null,
        confidence: 0,
        isLoading: true,
        error: null,
        dismissInsight: vi.fn(),
        applyLayout: vi.fn(),
        fetchSuggestions: vi.fn(),
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("ai-insights-loading")).toBeInTheDocument();
    });

    it("should show empty state when no insights", () => {
      mockUseDevToolsAI.mockReturnValue({
        insights: [],
        suggestedLayout: null,
        confidence: 0,
        isLoading: false,
        error: null,
        dismissInsight: vi.fn(),
        applyLayout: vi.fn(),
        fetchSuggestions: vi.fn(),
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("ai-insights-empty")).toBeInTheDocument();
      expect(screen.getByText(/no ai insights/i)).toBeInTheDocument();
    });
  });

  describe("insight display", () => {
    it("should show severity indicators", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("severity-insight-1")).toHaveAttribute(
        "data-severity",
        "high",
      );
      expect(screen.getByTestId("severity-insight-2")).toHaveAttribute(
        "data-severity",
        "medium",
      );
      expect(screen.getByTestId("severity-insight-3")).toHaveAttribute(
        "data-severity",
        "low",
      );
    });

    it("should show insight type badges", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      const insight1 = screen.getByTestId("ai-insight-insight-1");
      expect(within(insight1).getByText("anomaly")).toBeInTheDocument();

      const insight2 = screen.getByTestId("ai-insight-insight-2");
      expect(within(insight2).getByText("performance")).toBeInTheDocument();
    });

    it("should show confidence scores", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("confidence-insight-1")).toHaveTextContent(
        "90%",
      );
      expect(screen.getByTestId("confidence-insight-2")).toHaveTextContent(
        "85%",
      );
    });

    it("should show suggested actions when available", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(
        screen.getByText("Check network connectivity"),
      ).toBeInTheDocument();
      expect(screen.getByText("Enable prompt caching")).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    it("should show filter options", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("filter-all")).toBeInTheDocument();
      expect(screen.getByTestId("filter-anomaly")).toBeInTheDocument();
      expect(screen.getByTestId("filter-suggestion")).toBeInTheDocument();
    });

    it("should filter by type", async () => {
      const user = userEvent.setup();

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      await user.click(screen.getByTestId("filter-anomaly"));

      // Only anomaly should be visible
      expect(screen.getByTestId("ai-insight-insight-1")).toBeInTheDocument();
      expect(
        screen.queryByTestId("ai-insight-insight-2"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("ai-insight-insight-3"),
      ).not.toBeInTheDocument();
    });
  });

  describe("dismiss", () => {
    it("should show dismiss button on hover", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      const insight = screen.getByTestId("ai-insight-insight-1");
      fireEvent.mouseEnter(insight);

      expect(
        within(insight).getByTestId("dismiss-insight-button"),
      ).toBeInTheDocument();
    });

    it("should call dismissInsight when dismiss clicked", () => {
      const mockDismiss = vi.fn();

      mockUseDevToolsAI.mockReturnValue({
        insights: mockInsights,
        suggestedLayout: null,
        confidence: 0,
        isLoading: false,
        error: null,
        dismissInsight: mockDismiss,
        applyLayout: vi.fn(),
        fetchSuggestions: vi.fn(),
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      const insight = screen.getByTestId("ai-insight-insight-1");
      fireEvent.mouseEnter(insight);
      fireEvent.click(within(insight).getByTestId("dismiss-insight-button"));

      expect(mockDismiss).toHaveBeenCalledWith("insight-1");
    });
  });

  describe("refresh", () => {
    it("should have refresh button", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("refresh-insights-button")).toBeInTheDocument();
    });

    it("should call fetchSuggestions when refresh clicked", async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn();

      mockUseDevToolsAI.mockReturnValue({
        insights: mockInsights,
        suggestedLayout: null,
        confidence: 0,
        isLoading: false,
        error: null,
        dismissInsight: vi.fn(),
        applyLayout: vi.fn(),
        fetchSuggestions: mockFetch,
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      await user.click(screen.getByTestId("refresh-insights-button"));

      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe("layout suggestions", () => {
    it("should show layout suggestion banner when available", () => {
      mockUseDevToolsAI.mockReturnValue({
        insights: mockInsights,
        suggestedLayout: ["problems", "console", "network"],
        confidence: 0.85,
        isLoading: false,
        error: null,
        dismissInsight: vi.fn(),
        applyLayout: vi.fn(),
        fetchSuggestions: vi.fn(),
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      const banner = screen.getByTestId("layout-suggestion-banner");
      expect(banner).toBeInTheDocument();
      expect(within(banner).getByText(/85%/)).toBeInTheDocument();
    });

    it("should call applyLayout when apply button clicked", async () => {
      const user = userEvent.setup();
      const mockApply = vi.fn();

      mockUseDevToolsAI.mockReturnValue({
        insights: mockInsights,
        suggestedLayout: ["problems", "console"],
        confidence: 0.9,
        isLoading: false,
        error: null,
        dismissInsight: vi.fn(),
        applyLayout: mockApply,
        fetchSuggestions: vi.fn(),
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      await user.click(screen.getByTestId("apply-layout-button"));

      expect(mockApply).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("should display error message", () => {
      mockUseDevToolsAI.mockReturnValue({
        insights: [],
        suggestedLayout: null,
        confidence: 0,
        isLoading: false,
        error: new Error("Failed to fetch insights"),
        dismissInsight: vi.fn(),
        applyLayout: vi.fn(),
        fetchSuggestions: vi.fn(),
      });

      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(screen.getByTestId("ai-insights-error")).toBeInTheDocument();
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have accessible structure", () => {
      render(<AIInsightsTab context="session" contextEntityId="session-123" />);

      expect(
        screen.getByRole("heading", { name: /insights/i }),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <AIInsightsTab context="session" contextEntityId="session-123" />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
