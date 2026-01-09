/**
 * DecisionTimeline Tests
 *
 * TDD tests for the decision timeline component (ADR-0101 Context Graphs).
 * Tests cover:
 * - Rendering decision traces in chronological order
 * - Displaying decision type, action, confidence
 * - Loading and empty states
 * - Filtering by decision type
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { DecisionTimeline } from "./DecisionTimeline";
import type { DecisionTraceSummary } from "../../types/contextGraph";

describe("DecisionTimeline", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  const mockTraces: DecisionTraceSummary[] = [
    {
      traceId: "trace-001",
      timestamp: "2026-01-08T10:00:00Z",
      decisionType: "routing",
      chosenAction: "search_tool",
      confidence: 0.95,
      outcome: "success",
    },
    {
      traceId: "trace-002",
      timestamp: "2026-01-08T10:01:00Z",
      decisionType: "tool_selection",
      chosenAction: "web_search,file_read",
      confidence: 0.87,
      outcome: "success",
    },
    {
      traceId: "trace-003",
      timestamp: "2026-01-08T10:02:00Z",
      decisionType: "approval",
      chosenAction: "requires_approval",
      confidence: 0.72,
      outcome: null,
    },
  ];

  describe("rendering", () => {
    it("should render a timeline container", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      expect(screen.getByTestId("decision-timeline")).toBeInTheDocument();
    });

    it("should render each trace as a timeline item", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      const items = screen.getAllByTestId("timeline-item");
      expect(items).toHaveLength(3);
    });

    it("should display decision type for each trace", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      expect(screen.getByText("routing")).toBeInTheDocument();
      expect(screen.getByText("tool_selection")).toBeInTheDocument();
      expect(screen.getByText("approval")).toBeInTheDocument();
    });

    it("should display chosen action for each trace", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      expect(screen.getByText("search_tool")).toBeInTheDocument();
      expect(screen.getByText("web_search,file_read")).toBeInTheDocument();
      expect(screen.getByText("requires_approval")).toBeInTheDocument();
    });

    it("should display confidence as percentage", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      expect(screen.getByText("95%")).toBeInTheDocument();
      expect(screen.getByText("87%")).toBeInTheDocument();
      expect(screen.getByText("72%")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<DecisionTimeline traces={[]} isLoading />);
      expect(screen.getByTestId("timeline-loading")).toBeInTheDocument();
    });

    it("should show skeleton items when loading", () => {
      render(<DecisionTimeline traces={[]} isLoading />);
      const skeletons = screen.getAllByTestId("timeline-skeleton");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("empty state", () => {
    it("should show empty message when no traces", () => {
      render(<DecisionTimeline traces={[]} />);
      expect(screen.getByTestId("timeline-empty")).toBeInTheDocument();
    });

    it("should display appropriate empty message", () => {
      render(<DecisionTimeline traces={[]} />);
      expect(screen.getByText(/no decision traces/i)).toBeInTheDocument();
    });
  });

  describe("outcome indicator", () => {
    it("should show success indicator for successful outcomes", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      const successIndicators = screen.getAllByTestId("outcome-success");
      expect(successIndicators.length).toBe(2);
    });

    it("should show pending indicator for null outcomes", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      expect(screen.getByTestId("outcome-pending")).toBeInTheDocument();
    });
  });

  describe("timestamp display", () => {
    it("should display formatted timestamp", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      // Should show time in readable format (timezone-agnostic check)
      // Just verify there's a time element with AM/PM format
      const timeElements = screen.getAllByText(
        /\d{1,2}:\d{2}:\d{2}\s*(AM|PM)?/i,
      );
      expect(timeElements.length).toBeGreaterThan(0);
    });
  });

  describe("filtering", () => {
    it("should support filtering by decision type", () => {
      render(<DecisionTimeline traces={mockTraces} filterType="routing" />);
      const items = screen.getAllByTestId("timeline-item");
      expect(items).toHaveLength(1);
    });
  });

  describe("accessibility", () => {
    it("should have appropriate ARIA labels", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      expect(
        screen.getByRole("list", { name: /decision timeline/i }),
      ).toBeInTheDocument();
    });

    it("should mark each item as a listitem", () => {
      render(<DecisionTimeline traces={mockTraces} />);
      const listitems = screen.getAllByRole("listitem");
      expect(listitems).toHaveLength(3);
    });
  });
});
