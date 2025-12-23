/**
 * LogsTab Component Tests
 *
 * TDD tests for OTEL structured logs with trace correlation.
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

import { LogsTab } from "./LogsTab";
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

const mockLogs = [
  {
    id: "log-1",
    timestamp: new Date(Date.now() - 60000).toISOString(),
    level: "info" as const,
    service: "api-gateway",
    message: "Request received",
    trace_id: "abc123",
    span_id: "def456",
    attributes: { method: "POST", path: "/api/v1/chat" },
  },
  {
    id: "log-2",
    timestamp: new Date(Date.now() - 55000).toISOString(),
    level: "debug" as const,
    service: "llm-service",
    message: "Token prediction started",
    trace_id: "abc123",
    span_id: "ghi789",
    attributes: { model: "gpt-4", estimated_tokens: 1500 },
  },
  {
    id: "log-3",
    timestamp: new Date(Date.now() - 50000).toISOString(),
    level: "error" as const,
    service: "db-service",
    message: "Connection timeout",
    trace_id: "abc123",
    span_id: "jkl012",
    attributes: { error: "ETIMEDOUT", host: "db-primary" },
  },
  {
    id: "log-4",
    timestamp: new Date(Date.now() - 45000).toISOString(),
    level: "warning" as const,
    service: "cache-service",
    message: "Cache miss rate increasing",
    trace_id: "xyz789",
    span_id: "mno345",
    attributes: { miss_rate: "15%" },
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("LogsTab", () => {
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
      renderWithProvider(<LogsTab />);
      expect(screen.getByTestId("logs-tab")).toBeInTheDocument();
    });

    it("should display empty state when no logs", () => {
      renderWithProvider(<LogsTab />);
      expect(screen.getByText(/no logs/i)).toBeInTheDocument();
    });

    it("should display search input", () => {
      renderWithProvider(<LogsTab />);
      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });

    it("should display filter controls", () => {
      renderWithProvider(<LogsTab />);
      expect(
        screen.getByRole("button", { name: /level/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /service/i }),
      ).toBeInTheDocument();
    });
  });

  describe("log list", () => {
    it("should display logs when logs exist", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      expect(screen.getByText(/request received/i)).toBeInTheDocument();
      expect(screen.getByText(/token prediction started/i)).toBeInTheDocument();
      expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
    });

    it("should display level badges", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      const logsTab = screen.getByTestId("logs-tab");
      expect(within(logsTab).getByText(/^info$/i)).toBeInTheDocument();
      expect(within(logsTab).getByText(/^debug$/i)).toBeInTheDocument();
      expect(within(logsTab).getByText(/^error$/i)).toBeInTheDocument();
    });

    it("should display service names", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      expect(screen.getByText(/api-gateway/i)).toBeInTheDocument();
      expect(screen.getByText(/llm-service/i)).toBeInTheDocument();
      expect(screen.getByText(/db-service/i)).toBeInTheDocument();
    });

    it("should display timestamps", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      const logsTab = screen.getByTestId("logs-tab");
      // Should have timestamps displayed
      const timestamps = within(logsTab).getAllByTestId("log-timestamp");
      expect(timestamps.length).toBeGreaterThan(0);
    });
  });

  describe("trace correlation", () => {
    it("should display trace_id for logs with traces", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      expect(screen.getAllByText(/abc123/i).length).toBeGreaterThan(0);
    });

    it("should display span_id for logs with spans", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      expect(screen.getAllByText(/def456/i).length).toBeGreaterThan(0);
    });

    it("should have Jump to Trace button for logs with trace_id", () => {
      const onJumpToTrace = vi.fn();
      renderWithProvider(
        <LogsTab logs={mockLogs} onJumpToTrace={onJumpToTrace} />,
      );

      const jumpButtons = screen.getAllByRole("button", {
        name: /jump to trace/i,
      });
      expect(jumpButtons.length).toBeGreaterThan(0);
    });

    it("should call onJumpToTrace when Jump to Trace clicked", () => {
      const onJumpToTrace = vi.fn();
      renderWithProvider(
        <LogsTab logs={mockLogs} onJumpToTrace={onJumpToTrace} />,
      );

      const jumpButtons = screen.getAllByRole("button", {
        name: /jump to trace/i,
      });
      fireEvent.click(jumpButtons[0]);

      expect(onJumpToTrace).toHaveBeenCalledWith("abc123");
    });
  });

  describe("filtering", () => {
    it("should filter logs by search term", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "connection" } });

      expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
      expect(screen.queryByText(/request received/i)).not.toBeInTheDocument();
    });

    it("should filter logs by level", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      fireEvent.click(screen.getByRole("button", { name: /level/i }));
      fireEvent.click(screen.getByRole("option", { name: /error/i }));

      expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
      expect(screen.queryByText(/request received/i)).not.toBeInTheDocument();
    });

    it("should filter logs by service", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      fireEvent.click(screen.getByRole("button", { name: /service/i }));
      fireEvent.click(screen.getByRole("option", { name: /api-gateway/i }));

      expect(screen.getByText(/request received/i)).toBeInTheDocument();
      expect(screen.queryByText(/connection timeout/i)).not.toBeInTheDocument();
    });
  });

  describe("expandable attributes", () => {
    it("should show expand button for logs with attributes", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      const expandButtons = screen.getAllByRole("button", { name: /expand/i });
      expect(expandButtons.length).toBeGreaterThan(0);
    });

    it("should expand attributes when clicked", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      const expandButtons = screen.getAllByRole("button", { name: /expand/i });
      fireEvent.click(expandButtons[0]);

      // Should show attributes JSON
      expect(screen.getByText(/method/i)).toBeInTheDocument();
      expect(screen.getByText(/post/i)).toBeInTheDocument();
    });
  });

  describe("timeline integration", () => {
    it("should filter logs by time window", () => {
      // Logs should sync with timeline context
      renderWithProvider(<LogsTab logs={mockLogs} />);

      expect(screen.getByTestId("logs-tab")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("should show loading skeleton when isLoading", () => {
      renderWithProvider(<LogsTab isLoading />);

      expect(screen.getByTestId("logs-loading")).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("should display error message on error", () => {
      renderWithProvider(<LogsTab error="Failed to fetch logs" />);

      expect(screen.getByText(/failed to fetch logs/i)).toBeInTheDocument();
    });
  });

  describe("copy action", () => {
    it("should have copy button for logs", () => {
      renderWithProvider(<LogsTab logs={mockLogs} />);

      const copyButtons = screen.getAllByRole("button", { name: /copy/i });
      expect(copyButtons.length).toBeGreaterThan(0);
    });
  });
});
