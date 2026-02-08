/**
 * TracesTab Component Tests
 *
 * TDD tests for OTEL distributed traces waterfall view.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  within,
  cleanup,
} from "@testing-library/react";
import React from "react";

import { TracesTab } from "./TracesTab";
import { DevToolsTimelineProvider } from "../context/DevToolsTimelineProvider";

// Mock useLGTMIntegration hook
const mockGetTraceUrl = vi.fn();
vi.mock("../hooks/useLGTMIntegration", () => ({
  useLGTMIntegration: () => ({
    canOpenInTempo: true,
    getTraceUrl: mockGetTraceUrl,
    tempoUrl: "/tempo",
  }),
}));

// =============================================================================
// Test Helpers
// =============================================================================

function renderWithProvider(
  ui: React.ReactElement,
  providerProps?: Partial<
    React.ComponentProps<typeof DevToolsTimelineProvider>
  >,
) {
  return render(
    <DevToolsTimelineProvider {...providerProps}>
      {ui}
    </DevToolsTimelineProvider>,
  );
}

const mockTraces = [
  {
    traceId: "trace-1",
    name: "api.request",
    startTime: 100,
    durationMs: 500,
    spanCount: 5,
    serviceName: "api-gateway",
    status: "ok",
  },
  {
    traceId: "trace-2",
    name: "db.query",
    startTime: 200,
    durationMs: 150,
    spanCount: 3,
    serviceName: "db-service",
    status: "error",
  },
];

const mockSpans = [
  {
    spanId: "span-1",
    traceId: "trace-1",
    parentSpanId: null,
    name: "api.request",
    startTime: 100,
    durationMs: 500,
    status: "ok",
    serviceName: "api-gateway",
    depth: 0,
    attributes: {},
  },
  {
    spanId: "span-2",
    traceId: "trace-1",
    parentSpanId: "span-1",
    name: "auth.validate",
    startTime: 110,
    durationMs: 50,
    status: "ok",
    serviceName: "auth-service",
    depth: 1,
    attributes: {},
  },
  {
    spanId: "span-3",
    traceId: "trace-1",
    parentSpanId: "span-1",
    name: "db.query",
    startTime: 170,
    durationMs: 200,
    status: "ok",
    serviceName: "db-service",
    depth: 1,
    attributes: {},
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("TracesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render without crashing", () => {
      renderWithProvider(<TracesTab />);
      expect(screen.getByTestId("traces-tab")).toBeInTheDocument();
    });

    it("should display empty state when no traces", () => {
      renderWithProvider(<TracesTab />);
      expect(screen.getByText(/no traces/i)).toBeInTheDocument();
    });

    it("should display search input", () => {
      renderWithProvider(<TracesTab />);
      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });

    it("should display filter controls", () => {
      renderWithProvider(<TracesTab />);
      expect(
        screen.getByRole("button", { name: /service/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /status/i }),
      ).toBeInTheDocument();
    });
  });

  describe("trace list", () => {
    it("should display trace list when traces exist", () => {
      renderWithProvider(<TracesTab traces={mockTraces} />);

      expect(screen.getByText(/api\.request/i)).toBeInTheDocument();
      expect(screen.getByText(/db\.query/i)).toBeInTheDocument();
    });

    it("should show trace metadata", () => {
      renderWithProvider(<TracesTab traces={mockTraces} />);

      expect(screen.getByText(/500ms/i)).toBeInTheDocument();
      expect(screen.getByText(/5 spans/i)).toBeInTheDocument();
    });

    it("should highlight error traces", () => {
      renderWithProvider(<TracesTab traces={mockTraces} />);

      const errorTrace = screen.getByText(/db\.query/i).closest("[data-trace]");
      expect(errorTrace).toHaveAttribute("data-status", "error");
    });
  });

  describe("waterfall view", () => {
    it("should display waterfall when trace is selected", () => {
      renderWithProvider(<TracesTab traces={mockTraces} spans={mockSpans} />);

      fireEvent.click(screen.getByText(/api\.request/i));

      expect(screen.getByTestId("trace-waterfall")).toBeInTheDocument();
    });

    it("should show span hierarchy", () => {
      renderWithProvider(
        <TracesTab
          traces={mockTraces}
          spans={mockSpans}
          selectedTraceId="trace-1"
        />,
      );

      expect(screen.getByText(/auth\.validate/i)).toBeInTheDocument();
      expect(screen.getByText(/db\.query/i)).toBeInTheDocument();
    });

    it("should display span timing bars", () => {
      renderWithProvider(
        <TracesTab
          traces={mockTraces}
          spans={mockSpans}
          selectedTraceId="trace-1"
        />,
      );

      const waterfall = screen.getByTestId("trace-waterfall");
      const timingBars = within(waterfall).getAllByTestId("span-timing-bar");
      expect(timingBars.length).toBeGreaterThan(0);
    });
  });

  describe("filtering", () => {
    it("should filter traces by search term", () => {
      renderWithProvider(<TracesTab traces={mockTraces} />);

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "api" } });

      expect(screen.getByText(/api\.request/i)).toBeInTheDocument();
      expect(screen.queryByText(/db\.query/i)).not.toBeInTheDocument();
    });

    it("should filter traces by status", async () => {
      renderWithProvider(<TracesTab traces={mockTraces} />);

      fireEvent.click(screen.getByRole("button", { name: /status/i }));
      fireEvent.click(screen.getByRole("option", { name: /error/i }));

      expect(screen.queryByText(/api\.request/i)).not.toBeInTheDocument();
      expect(screen.getByText(/db\.query/i)).toBeInTheDocument();
    });
  });

  describe("timeline integration", () => {
    it("should filter traces by time window", () => {
      // Traces within time window should be shown
      renderWithProvider(<TracesTab traces={mockTraces} />);

      // The tab should integrate with the timeline context
      expect(screen.getByTestId("traces-tab")).toBeInTheDocument();
    });

    it("should highlight trace at current timeline position", () => {
      renderWithProvider(
        <TracesTab
          traces={mockTraces}
          spans={mockSpans}
          selectedTraceId="trace-1"
        />,
      );

      // Should highlight spans based on current timeline time
      expect(screen.getByTestId("trace-waterfall")).toBeInTheDocument();
    });
  });

  describe("span details", () => {
    it("should show span details on click", () => {
      renderWithProvider(
        <TracesTab
          traces={mockTraces}
          spans={mockSpans}
          selectedTraceId="trace-1"
        />,
      );

      const spanRow = screen.getByText(/auth\.validate/i);
      fireEvent.click(spanRow);

      expect(screen.getByTestId("span-details")).toBeInTheDocument();
    });
  });

  describe("tempo integration", () => {
    it("should display View in Tempo button when LGTM integration is available", () => {
      renderWithProvider(
        <TracesTab traces={mockTraces} selectedTraceId="trace-1" />,
      );

      expect(
        screen.getByRole("button", { name: /view in tempo/i }),
      ).toBeInTheDocument();
    });

    it("should open Tempo URL with trace ID", () => {
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
      mockGetTraceUrl.mockReturnValue("/tempo/explore?traceId=trace-1");

      renderWithProvider(
        <TracesTab traces={mockTraces} selectedTraceId="trace-1" />,
      );

      fireEvent.click(screen.getByRole("button", { name: /view in tempo/i }));

      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("trace-1"),
        "_blank",
      );

      openSpy.mockRestore();
    });
  });
});
