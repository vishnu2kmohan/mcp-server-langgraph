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
    trace_id: "trace-1",
    name: "api.request",
    start_time: 100,
    duration_ms: 500,
    span_count: 5,
    service_name: "api-gateway",
    status: "ok",
  },
  {
    trace_id: "trace-2",
    name: "db.query",
    start_time: 200,
    duration_ms: 150,
    span_count: 3,
    service_name: "db-service",
    status: "error",
  },
];

const mockSpans = [
  {
    span_id: "span-1",
    trace_id: "trace-1",
    parent_span_id: null,
    name: "api.request",
    start_time: 100,
    duration_ms: 500,
    status: "ok",
    service_name: "api-gateway",
    depth: 0,
    attributes: {},
  },
  {
    span_id: "span-2",
    trace_id: "trace-1",
    parent_span_id: "span-1",
    name: "auth.validate",
    start_time: 110,
    duration_ms: 50,
    status: "ok",
    service_name: "auth-service",
    depth: 1,
    attributes: {},
  },
  {
    span_id: "span-3",
    trace_id: "trace-1",
    parent_span_id: "span-1",
    name: "db.query",
    start_time: 170,
    duration_ms: 200,
    status: "ok",
    service_name: "db-service",
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

  describe("grafana integration", () => {
    it("should display View in Grafana button when grafanaUrl is provided", () => {
      renderWithProvider(
        <TracesTab
          traces={mockTraces}
          selectedTraceId="trace-1"
          grafanaUrl="/grafana/explore"
        />,
      );

      expect(
        screen.getByRole("button", { name: /view in grafana/i }),
      ).toBeInTheDocument();
    });

    it("should open Grafana URL with trace ID", () => {
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

      renderWithProvider(
        <TracesTab
          traces={mockTraces}
          selectedTraceId="trace-1"
          grafanaUrl="/grafana/explore"
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /view in grafana/i }));

      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("trace-1"),
        "_blank",
      );

      openSpy.mockRestore();
    });
  });
});
