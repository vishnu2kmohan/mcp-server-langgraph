/**
 * LogsTab Tests - react-table layout, auto-tail, service discovery
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";

import { LogsTab } from "./LogsTab";
import { DevToolsTimelineProvider } from "../context/DevToolsTimelineProvider";

// =============================================================================
// Helpers & Mocks
// =============================================================================

const mockServicesHook = vi
  .fn()
  .mockReturnValue({ data: ["api-gateway", "worker"] });

vi.mock("../../api", () => ({
  useListDevtoolsServicesQuery: () => mockServicesHook(),
}));

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
    traceId: "abc123",
    spanId: "def456",
    attributes: { method: "POST", path: "/api/v1/chat" },
  },
  {
    id: "log-2",
    timestamp: new Date(Date.now() - 55000).toISOString(),
    level: "debug" as const,
    service: "llm-service",
    message: "Token prediction started",
    traceId: "abc123",
    spanId: "ghi789",
    attributes: { model: "gpt-4", estimatedTokens: 1500 },
  },
  {
    id: "log-3",
    timestamp: new Date(Date.now() - 50000).toISOString(),
    level: "error" as const,
    service: "db-service",
    message: "Connection timeout",
    traceId: "abc123",
    spanId: "jkl012",
    attributes: { error: "ETIMEDOUT", host: "db-primary" },
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("LogsTab (react-table + service discovery)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders logs with human-friendly timestamps", () => {
    renderWithProvider(<LogsTab logs={mockLogs} />);
    expect(screen.getByTestId("logs-tab")).toBeInTheDocument();
    expect(screen.getAllByTestId("human-timestamp").length).toBeGreaterThan(0);
    expect(screen.getByText(/request received/i)).toBeInTheDocument();
  });

  it("shows empty state when no logs available", () => {
    renderWithProvider(<LogsTab />);
    expect(screen.getByText(/no logs/i)).toBeInTheDocument();
  });

  it("filters by search term and level", () => {
    renderWithProvider(<LogsTab logs={mockLogs} />);

    fireEvent.change(screen.getByPlaceholderText(/search logs/i), {
      target: { value: "connection" },
    });
    expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
    expect(screen.queryByText(/request received/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /level/i }));
    fireEvent.click(screen.getByRole("button", { name: /error/i }));
    expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
  });

  it("merges discovered services into the filter dropdown", () => {
    renderWithProvider(<LogsTab logs={mockLogs.slice(0, 1)} />);

    fireEvent.click(screen.getByRole("button", { name: /service/i }));
    expect(screen.getByRole("button", { name: /worker/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /api-gateway/i }),
    ).toBeInTheDocument();
  });

  it("toggles auto-tail via the down arrow control", () => {
    renderWithProvider(<LogsTab logs={mockLogs} />);
    const toggle = screen.getByTestId("logs-auto-tail");
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "false");
  });

  it("invokes onJumpToTrace when Jump to Trace is clicked", () => {
    const onJumpToTrace = vi.fn();
    renderWithProvider(
      <LogsTab logs={mockLogs} onJumpToTrace={onJumpToTrace} />,
    );

    fireEvent.click(
      screen.getAllByRole("button", { name: /jump to trace/i })[0],
    );
    expect(onJumpToTrace).toHaveBeenCalledWith("abc123");
  });

  it("shows loading and error states", () => {
    renderWithProvider(<LogsTab isLoading />);
    expect(screen.getByTestId("logs-loading")).toBeInTheDocument();

    cleanup();
    renderWithProvider(<LogsTab error="Failed to fetch logs" />);
    expect(screen.getByText(/failed to fetch logs/i)).toBeInTheDocument();
  });
});
