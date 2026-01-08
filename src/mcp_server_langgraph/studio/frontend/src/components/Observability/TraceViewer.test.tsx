/**
 * TraceViewer Component Tests
 *
 * TDD tests for the trace visualization component.
 * Tests cover:
 * - Trace timeline rendering
 * - Span selection and details
 * - Span hierarchy visualization
 * - Search and filtering
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { TraceViewer } from "./TraceViewer";
import type { Trace, Span } from "./types";

const mockSpans: Span[] = [
  {
    spanId: "span-1",
    name: "HTTP POST /api/chat",
    startTime: 1704067200000,
    durationMs: 150,
    status: "ok",
    depth: 0,
    attributes: { "http.method": "POST", "http.url": "/api/chat" },
    events: [],
  },
  {
    spanId: "span-2",
    name: "LLM Inference",
    startTime: 1704067200020,
    durationMs: 100,
    status: "ok",
    depth: 1,
    attributes: { "llm.model": "gpt-4", "llm.tokens": 1250 },
    events: [{ name: "token_generated", timestamp: 1704067200050 }],
  },
  {
    spanId: "span-3",
    name: "Database Query",
    startTime: 1704067200130,
    durationMs: 15,
    status: "error",
    depth: 1,
    attributes: { "db.statement": "SELECT * FROM sessions" },
    events: [],
    errorMessage: "Connection timeout",
  },
];

const mockTrace: Trace = {
  traceId: "trace-123",
  spans: mockSpans,
  startTime: 1704067200000,
  endTime: 1704067200150,
  durationMs: 150,
};

describe("TraceViewer", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render trace ID", () => {
      render(<TraceViewer trace={mockTrace} />);

      expect(screen.getByText(/trace-123/i)).toBeInTheDocument();
    });

    it("should render all spans", () => {
      render(<TraceViewer trace={mockTrace} />);

      expect(screen.getByText("HTTP POST /api/chat")).toBeInTheDocument();
      expect(screen.getByText("LLM Inference")).toBeInTheDocument();
      expect(screen.getByText("Database Query")).toBeInTheDocument();
    });

    it("should render total duration", () => {
      render(<TraceViewer trace={mockTrace} />);

      expect(screen.getByText(/Total Duration: 150ms/)).toBeInTheDocument();
    });
  });

  describe("Span Timeline", () => {
    it("should render spans in a timeline", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spans = screen.getAllByTestId(/^span-row-/);
      expect(spans).toHaveLength(3);
    });

    it("should indent child spans based on depth", () => {
      render(<TraceViewer trace={mockTrace} />);

      const span1 = screen.getByTestId("span-row-span-1");
      const span2 = screen.getByTestId("span-row-span-2");

      // Child span should have indentation
      expect(span2).toHaveClass("ml-4");
      expect(span1).not.toHaveClass("ml-4");
    });

    it("should show span duration visually", () => {
      render(<TraceViewer trace={mockTrace} />);

      const span2Bar = screen.getByTestId("span-bar-span-2");
      expect(span2Bar).toBeInTheDocument();
    });
  });

  describe("Span Status", () => {
    it("should show success status with green indicator", () => {
      render(<TraceViewer trace={mockTrace} />);

      const successSpan = screen.getByTestId("span-status-span-1");
      expect(successSpan).toHaveClass("bg-success-500");
    });

    it("should show error status with red indicator", () => {
      render(<TraceViewer trace={mockTrace} />);

      const errorSpan = screen.getByTestId("span-status-span-3");
      expect(errorSpan).toHaveClass("bg-error-500");
    });
  });

  describe("Span Selection", () => {
    it("should select span when clicked", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spanRow = screen.getByTestId("span-row-span-2");
      fireEvent.click(spanRow);

      expect(spanRow).toHaveClass("bg-primary-50");
    });

    it("should show span details panel when span is selected", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spanRow = screen.getByTestId("span-row-span-2");
      fireEvent.click(spanRow);

      expect(screen.getByTestId("span-details")).toBeInTheDocument();
      // Both timeline and details show the span name
      expect(screen.getAllByText("LLM Inference")).toHaveLength(2);
    });

    it("should display span attributes in details panel", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spanRow = screen.getByTestId("span-row-span-2");
      fireEvent.click(spanRow);

      expect(screen.getByText("llm.model")).toBeInTheDocument();
      expect(screen.getByText("gpt-4")).toBeInTheDocument();
    });

    it("should display span events in details panel", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spanRow = screen.getByTestId("span-row-span-2");
      fireEvent.click(spanRow);

      expect(screen.getByText("token_generated")).toBeInTheDocument();
    });
  });

  describe("Error Display", () => {
    it("should show error message for failed spans", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spanRow = screen.getByTestId("span-row-span-3");
      fireEvent.click(spanRow);

      expect(screen.getByText("Connection timeout")).toBeInTheDocument();
    });

    it("should highlight error spans in timeline", () => {
      render(<TraceViewer trace={mockTrace} />);

      const errorBar = screen.getByTestId("span-bar-span-3");
      expect(errorBar).toHaveClass("bg-error-400");
    });
  });

  describe("Search and Filter", () => {
    it("should filter spans by name", () => {
      render(<TraceViewer trace={mockTrace} />);

      const searchInput = screen.getByPlaceholderText(/search spans/i);
      fireEvent.change(searchInput, { target: { value: "LLM" } });

      expect(screen.getByText("LLM Inference")).toBeInTheDocument();
      expect(screen.queryByText("Database Query")).not.toBeInTheDocument();
    });

    it("should show no results message when no spans match", () => {
      render(<TraceViewer trace={mockTrace} />);

      const searchInput = screen.getByPlaceholderText(/search spans/i);
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      expect(screen.getByText(/no spans found/i)).toBeInTheDocument();
    });
  });

  describe("External Links", () => {
    it("should render link to Grafana when grafanaUrl is provided", () => {
      render(
        <TraceViewer
          trace={mockTrace}
          grafanaUrl="https://grafana.example.com/explore?traceId=trace-123"
        />,
      );

      expect(
        screen.getByRole("link", { name: /view in grafana/i }),
      ).toHaveAttribute(
        "href",
        "https://grafana.example.com/explore?traceId=trace-123",
      );
    });
  });

  describe("Loading and Empty States", () => {
    it("should show loading state", () => {
      render(<TraceViewer trace={null} isLoading={true} />);

      expect(screen.getByTestId("trace-loading")).toBeInTheDocument();
    });

    it("should show empty state when no trace", () => {
      render(<TraceViewer trace={null} isLoading={false} />);

      expect(screen.getByText(/no trace data/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible role for timeline", () => {
      render(<TraceViewer trace={mockTrace} />);

      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("should have accessible labels for span rows", () => {
      render(<TraceViewer trace={mockTrace} />);

      const spans = screen.getAllByRole("listitem");
      expect(spans.length).toBeGreaterThan(0);
    });
  });
});
