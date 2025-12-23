/**
 * AlertBadge Component Tests
 *
 * TDD tests for the header alert badge indicator.
 *
 * Features:
 * - Display alert count
 * - Color coding by severity
 * - Animated pulse for new critical alerts
 * - Click to navigate to admin alerts
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

import { AlertBadge, type AlertBadgeProps } from "./AlertBadge";
import alertReducer from "../store/slices/alertSlice";

// =============================================================================
// Test Helpers
// =============================================================================

const createTestStore = (
  criticalCount = 0,
  warningCount = 0,
  lastCriticalTime: number | null = null,
) =>
  configureStore({
    reducer: {
      alerts: alertReducer,
    },
    preloadedState: {
      alerts: {
        alerts: [
          // Create alerts based on counts
          ...Array(criticalCount)
            .fill(null)
            .map((_, i) => ({
              alert_id: `crit-${i}`,
              name: `Critical${i}`,
              severity: "critical" as const,
              state: "firing" as const,
              message: "Critical alert",
              labels: {},
              annotations: {},
              started_at: new Date().toISOString(),
              ended_at: null,
              fingerprint: `fp-crit-${i}`,
            })),
          ...Array(warningCount)
            .fill(null)
            .map((_, i) => ({
              alert_id: `warn-${i}`,
              name: `Warning${i}`,
              severity: "warning" as const,
              state: "firing" as const,
              message: "Warning alert",
              labels: {},
              annotations: {},
              started_at: new Date().toISOString(),
              ended_at: null,
              fingerprint: `fp-warn-${i}`,
            })),
        ],
        selectedAlertId: null,
        pendingRemediations: [],
        soundEnabled: true,
        lastCriticalAlertTime: lastCriticalTime,
        filters: { severity: ["critical", "warning"], state: ["firing"] },
      },
    },
  });

const defaultProps: AlertBadgeProps = {
  onClick: vi.fn(),
};

const renderWithStore = (ui: ReactNode, store = createTestStore()) =>
  render(<Provider store={store}>{ui}</Provider>);

// =============================================================================
// Tests
// =============================================================================

describe("AlertBadge", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render the badge", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(1, 0));

      expect(screen.getByTestId("alert-badge")).toBeInTheDocument();
    });

    it("should not render when no alerts", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(0, 0));

      expect(screen.queryByTestId("alert-badge")).not.toBeInTheDocument();
    });

    it("should render alert icon", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(1, 0));

      expect(screen.getByTestId("alert-icon")).toBeInTheDocument();
    });
  });

  describe("Alert Count", () => {
    it("should display total alert count", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(2, 3));

      expect(screen.getByTestId("alert-count")).toHaveTextContent("5");
    });

    it("should display critical count only", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(3, 0));

      expect(screen.getByTestId("alert-count")).toHaveTextContent("3");
    });

    it("should display 99+ for large counts", () => {
      renderWithStore(
        <AlertBadge {...defaultProps} />,
        createTestStore(100, 50),
      );

      expect(screen.getByTestId("alert-count")).toHaveTextContent("99+");
    });
  });

  describe("Severity Styling", () => {
    it("should show red styling for critical alerts", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(1, 0));

      expect(screen.getByTestId("alert-badge")).toHaveClass("bg-red-500");
    });

    it("should show yellow styling for warning-only alerts", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(0, 2));

      expect(screen.getByTestId("alert-badge")).toHaveClass("bg-yellow-500");
    });
  });

  describe("Animation", () => {
    it("should pulse when there are new critical alerts", () => {
      // Set last critical alert time to now (within pulse window)
      const recentTime = Date.now() - 5000; // 5 seconds ago
      renderWithStore(
        <AlertBadge {...defaultProps} />,
        createTestStore(1, 0, recentTime),
      );

      expect(screen.getByTestId("alert-badge")).toHaveClass("animate-pulse");
    });

    it("should not pulse when critical alerts are old", () => {
      // Set last critical alert time to 2 minutes ago (outside pulse window)
      const oldTime = Date.now() - 120000; // 2 minutes ago
      renderWithStore(
        <AlertBadge {...defaultProps} />,
        createTestStore(1, 0, oldTime),
      );

      expect(screen.getByTestId("alert-badge")).not.toHaveClass(
        "animate-pulse",
      );
    });

    it("should not pulse for warning-only alerts", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(0, 2));

      expect(screen.getByTestId("alert-badge")).not.toHaveClass(
        "animate-pulse",
      );
    });
  });

  describe("Interaction", () => {
    it("should call onClick when clicked", () => {
      const onClick = vi.fn();
      renderWithStore(
        <AlertBadge {...defaultProps} onClick={onClick} />,
        createTestStore(1, 0),
      );

      fireEvent.click(screen.getByTestId("alert-badge"));

      expect(onClick).toHaveBeenCalled();
    });

    it("should be focusable", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(1, 0));

      const badge = screen.getByTestId("alert-badge");
      expect(badge).toHaveAttribute("tabIndex", "0");
    });

    it("should trigger onClick on Enter key", () => {
      const onClick = vi.fn();
      renderWithStore(
        <AlertBadge {...defaultProps} onClick={onClick} />,
        createTestStore(1, 0),
      );

      fireEvent.keyDown(screen.getByTestId("alert-badge"), { key: "Enter" });

      expect(onClick).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have appropriate aria-label", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(2, 3));

      expect(screen.getByTestId("alert-badge")).toHaveAttribute(
        "aria-label",
        expect.stringContaining("5 alerts"),
      );
    });

    it("should indicate critical alerts in aria-label", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(2, 0));

      expect(screen.getByTestId("alert-badge")).toHaveAttribute(
        "aria-label",
        expect.stringContaining("2 critical"),
      );
    });
  });

  describe("Tooltip", () => {
    it("should have title attribute with details", () => {
      renderWithStore(<AlertBadge {...defaultProps} />, createTestStore(1, 2));

      const badge = screen.getByTestId("alert-badge");
      expect(badge).toHaveAttribute("title");
      expect(badge.getAttribute("title")).toContain("1 critical");
      expect(badge.getAttribute("title")).toContain("2 warning");
    });
  });
});
