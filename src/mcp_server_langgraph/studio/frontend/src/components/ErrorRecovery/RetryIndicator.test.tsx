/**
 * RetryIndicator Component Tests
 *
 * TDD - Sprint 3 - Phase 2.2: Automatic Retry System
 *
 * Tests for the visual retry indicator component that shows:
 * - Retry countdown timer
 * - Current retry attempt number
 * - Cancel and force retry buttons
 * - Progress bar for backoff visualization
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";

import { RetryIndicator, type RetryIndicatorProps } from "./RetryIndicator";

// =============================================================================
// Test Helpers
// =============================================================================

const defaultProps: RetryIndicatorProps = {
  retryCount: 1,
  maxRetries: 3,
  delayMs: 5000,
  onCancel: vi.fn(),
  onForceRetry: vi.fn(),
};

function renderRetryIndicator(overrides: Partial<RetryIndicatorProps> = {}) {
  const props = { ...defaultProps, ...overrides };
  return render(<RetryIndicator {...props} />);
}

// =============================================================================
// Tests
// =============================================================================

describe("RetryIndicator", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Rendering", () => {
    it("renders with correct retry count display", () => {
      renderRetryIndicator({ retryCount: 2, maxRetries: 5 });

      expect(screen.getByText(/Retry 2 of 5/i)).toBeInTheDocument();
    });

    it("displays the countdown timer", () => {
      renderRetryIndicator({ delayMs: 5000 });

      // Should show initial countdown
      expect(screen.getByTestId("retry-countdown")).toBeInTheDocument();
    });

    it("shows cancel and force retry buttons", () => {
      renderRetryIndicator();

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /retry now/i }),
      ).toBeInTheDocument();
    });

    it("shows progress bar", () => {
      renderRetryIndicator();

      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      renderRetryIndicator({ className: "custom-class" });

      expect(screen.getByTestId("retry-indicator")).toHaveClass("custom-class");
    });

    it("uses custom testId", () => {
      renderRetryIndicator({ testId: "custom-retry" });

      expect(screen.getByTestId("custom-retry")).toBeInTheDocument();
    });
  });

  describe("Countdown Timer", () => {
    it("updates countdown every second", async () => {
      renderRetryIndicator({ delayMs: 3000 });

      const countdown = screen.getByTestId("retry-countdown");
      expect(countdown).toHaveTextContent("3");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(countdown).toHaveTextContent("2");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(countdown).toHaveTextContent("1");
    });

    it("shows 0 when countdown reaches 0", async () => {
      renderRetryIndicator({ delayMs: 1000 });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(screen.getByTestId("retry-countdown")).toHaveTextContent("0");
    });

    it("calls onComplete when countdown finishes", async () => {
      const onComplete = vi.fn();
      renderRetryIndicator({ delayMs: 2000, onComplete });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(onComplete).toHaveBeenCalledTimes(1);
    });
  });

  describe("Progress Bar", () => {
    it("starts at 100% and decreases", async () => {
      renderRetryIndicator({ delayMs: 4000 });

      const progressbar = screen.getByRole("progressbar");

      // Initial value should be 100%
      expect(progressbar).toHaveAttribute("aria-valuenow", "100");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      // After 2s of 4s, should be ~50%
      expect(progressbar).toHaveAttribute("aria-valuenow", "50");
    });
  });

  describe("User Interactions", () => {
    it("calls onCancel when cancel button clicked", () => {
      const onCancel = vi.fn();
      renderRetryIndicator({ onCancel });

      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it("calls onForceRetry when retry now button clicked", () => {
      const onForceRetry = vi.fn();
      renderRetryIndicator({ onForceRetry });

      fireEvent.click(screen.getByRole("button", { name: /retry now/i }));

      expect(onForceRetry).toHaveBeenCalledTimes(1);
    });

    it("stops countdown when cancel is clicked", async () => {
      const onComplete = vi.fn();
      renderRetryIndicator({ delayMs: 5000, onComplete });

      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // onComplete should not be called after cancel
      expect(onComplete).not.toHaveBeenCalled();
    });

    it("stops countdown when force retry is clicked", async () => {
      const onComplete = vi.fn();
      renderRetryIndicator({ delayMs: 5000, onComplete });

      fireEvent.click(screen.getByRole("button", { name: /retry now/i }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // onComplete should not be called after force retry (user already triggered)
      expect(onComplete).not.toHaveBeenCalled();
    });
  });

  describe("Error Message", () => {
    it("displays error message when provided", () => {
      renderRetryIndicator({ errorMessage: "Connection timed out" });

      expect(screen.getByText("Connection timed out")).toBeInTheDocument();
    });

    it("displays error category icon when provided", () => {
      renderRetryIndicator({ errorCategory: "network" });

      // Network errors show wifi icon
      expect(screen.getByTestId("error-category-icon")).toBeInTheDocument();
    });
  });

  describe("Paused State", () => {
    it("pauses countdown when paused prop is true", async () => {
      const { rerender } = render(
        <RetryIndicator {...defaultProps} delayMs={5000} paused={false} />,
      );

      const countdown = screen.getByTestId("retry-countdown");
      expect(countdown).toHaveTextContent("5");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(countdown).toHaveTextContent("4");

      // Pause the countdown
      rerender(
        <RetryIndicator {...defaultProps} delayMs={5000} paused={true} />,
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      // Should still be 4 after pause
      expect(countdown).toHaveTextContent("4");
    });

    it("shows paused indicator when paused", () => {
      renderRetryIndicator({ paused: true });

      expect(screen.getByText(/paused/i)).toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("renders in compact mode when specified", () => {
      renderRetryIndicator({ compact: true });

      expect(screen.getByTestId("retry-indicator")).toHaveClass(
        "retry-indicator-compact",
      );
    });

    it("hides progress bar in compact mode", () => {
      renderRetryIndicator({ compact: true });

      expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has accessible retry count label", () => {
      renderRetryIndicator({ retryCount: 2, maxRetries: 5 });

      expect(screen.getByText(/Retry 2 of 5/i)).toBeInTheDocument();
    });

    it("progress bar has correct ARIA attributes", () => {
      renderRetryIndicator({ delayMs: 4000 });

      const progressbar = screen.getByRole("progressbar");
      expect(progressbar).toHaveAttribute("aria-valuemin", "0");
      expect(progressbar).toHaveAttribute("aria-valuemax", "100");
      expect(progressbar).toHaveAttribute("aria-label");
    });

    it("buttons have accessible names", () => {
      renderRetryIndicator();

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toHaveAccessibleName();
      expect(
        screen.getByRole("button", { name: /retry now/i }),
      ).toHaveAccessibleName();
    });
  });
});
