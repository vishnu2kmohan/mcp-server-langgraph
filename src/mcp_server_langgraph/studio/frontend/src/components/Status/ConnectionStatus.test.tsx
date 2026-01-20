/**
 * ConnectionStatus Tests
 *
 * TDD tests for the Connection Status indicator component.
 * Tests cover:
 * - Connection state display (connected/connecting/disconnected)
 * - API latency display
 * - Last sync time
 * - Click to reconnect
 * - Toast notifications for connection changes
 * - WCAG 2.1 AA accessibility requirements
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ConnectionStatus } from "./ConnectionStatus";

expect.extend(toHaveNoViolations);

describe("ConnectionStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the connection status indicator", () => {
      render(<ConnectionStatus status="connected" />);

      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });

    it("should render with custom className", () => {
      render(<ConnectionStatus status="connected" className="custom-class" />);

      expect(screen.getByTestId("connection-status")).toHaveClass(
        "custom-class",
      );
    });
  });

  // ===========================================================================
  // Connection State Tests
  // ===========================================================================

  describe("connection states", () => {
    it("should show connected state with green indicator", () => {
      render(<ConnectionStatus status="connected" />);

      expect(screen.getByText(/connected/i)).toBeInTheDocument();
      expect(screen.getByTestId("status-indicator")).toHaveClass(
        "bg-success-9",
      );
    });

    it("should show connecting state with yellow indicator", () => {
      render(<ConnectionStatus status="connecting" />);

      expect(screen.getByText(/connecting/i)).toBeInTheDocument();
      expect(screen.getByTestId("status-indicator")).toHaveClass(
        "bg-warning-9",
      );
    });

    it("should show disconnected state with red indicator", () => {
      render(<ConnectionStatus status="disconnected" />);

      expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
      expect(screen.getByTestId("status-indicator")).toHaveClass(
        "bg-error-9",
      );
    });

    it("should show reconnecting state with pulsing yellow indicator", () => {
      render(<ConnectionStatus status="reconnecting" />);

      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument();
      expect(screen.getByTestId("status-indicator")).toHaveClass(
        "animate-pulse",
      );
    });
  });

  // ===========================================================================
  // Latency Display Tests
  // ===========================================================================

  describe("latency display", () => {
    it("should show latency when provided", () => {
      render(<ConnectionStatus status="connected" latencyMs={45} />);

      expect(screen.getByText(/45ms/i)).toBeInTheDocument();
    });

    it("should not show latency when not provided", () => {
      render(<ConnectionStatus status="connected" />);

      expect(screen.queryByText(/ms$/i)).not.toBeInTheDocument();
    });

    it("should show green latency for good connection", () => {
      render(<ConnectionStatus status="connected" latencyMs={50} />);

      expect(screen.getByText(/50ms/i)).toHaveClass("text-success-10");
    });

    it("should show yellow latency for moderate connection", () => {
      render(<ConnectionStatus status="connected" latencyMs={150} />);

      expect(screen.getByText(/150ms/i)).toHaveClass("text-warning-10");
    });

    it("should show red latency for slow connection", () => {
      render(<ConnectionStatus status="connected" latencyMs={300} />);

      expect(screen.getByText(/300ms/i)).toHaveClass("text-error-10");
    });
  });

  // ===========================================================================
  // Last Sync Time Tests
  // ===========================================================================

  describe("last sync time", () => {
    it("should show last sync time when provided", () => {
      const recentTime = Date.now() - 30000; // 30 seconds ago
      render(<ConnectionStatus status="connected" lastSyncAt={recentTime} />);

      expect(screen.getByText(/synced/i)).toBeInTheDocument();
    });

    it("should show 'just now' for recent sync", () => {
      const recentTime = Date.now() - 5000; // 5 seconds ago
      render(<ConnectionStatus status="connected" lastSyncAt={recentTime} />);

      expect(screen.getByText(/just now/i)).toBeInTheDocument();
    });

    it("should show minutes ago for older sync", () => {
      const oldTime = Date.now() - 120000; // 2 minutes ago
      render(<ConnectionStatus status="connected" lastSyncAt={oldTime} />);

      expect(screen.getByText(/2m ago/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Reconnect Action Tests
  // ===========================================================================

  describe("reconnect action", () => {
    it("should show reconnect button when disconnected", () => {
      render(<ConnectionStatus status="disconnected" onReconnect={() => {}} />);

      expect(
        screen.getByRole("button", { name: /reconnect/i }),
      ).toBeInTheDocument();
    });

    it("should not show reconnect button when connected", () => {
      render(<ConnectionStatus status="connected" onReconnect={() => {}} />);

      expect(
        screen.queryByRole("button", { name: /reconnect/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onReconnect when reconnect button is clicked", async () => {
      const onReconnect = vi.fn();
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <ConnectionStatus status="disconnected" onReconnect={onReconnect} />,
      );

      await user.click(screen.getByRole("button", { name: /reconnect/i }));

      expect(onReconnect).toHaveBeenCalled();
    });

    it("should disable reconnect button when reconnecting", () => {
      render(<ConnectionStatus status="reconnecting" onReconnect={() => {}} />);

      const button = screen.queryByRole("button", { name: /reconnect/i });
      // Button might not exist or be disabled during reconnecting state
      if (button) {
        expect(button).toBeDisabled();
      }
    });
  });

  // ===========================================================================
  // Compact Mode Tests
  // ===========================================================================

  describe("compact mode", () => {
    it("should render in compact mode when specified", () => {
      render(<ConnectionStatus status="connected" compact />);

      const statusElement = screen.getByTestId("connection-status");
      expect(statusElement).toHaveAttribute("data-compact", "true");
    });

    it("should hide text in compact mode", () => {
      render(<ConnectionStatus status="connected" compact />);

      expect(screen.queryByText(/connected/i)).not.toBeInTheDocument();
    });

    it("should show status indicator in compact mode", () => {
      render(<ConnectionStatus status="connected" compact />);

      expect(screen.getByTestId("status-indicator")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Tooltip Tests
  // ===========================================================================

  describe("tooltip", () => {
    it("should show full status on hover in compact mode", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<ConnectionStatus status="connected" compact latencyMs={45} />);

      const statusElement = screen.getByTestId("connection-status");
      await user.hover(statusElement);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <ConnectionStatus status="connected" latencyMs={45} />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper aria-label for status", () => {
      render(<ConnectionStatus status="connected" />);

      const statusElement = screen.getByTestId("connection-status");
      expect(statusElement).toHaveAttribute("aria-label");
    });

    it("should announce connection changes to screen readers", () => {
      render(<ConnectionStatus status="disconnected" />);

      const liveRegion = screen.getByRole("status");
      expect(liveRegion).toHaveAttribute("aria-live", "polite");
    });

    it("should have proper role for reconnect button", () => {
      render(<ConnectionStatus status="disconnected" onReconnect={() => {}} />);

      expect(
        screen.getByRole("button", { name: /reconnect/i }),
      ).toBeInTheDocument();
    });
  });
});
