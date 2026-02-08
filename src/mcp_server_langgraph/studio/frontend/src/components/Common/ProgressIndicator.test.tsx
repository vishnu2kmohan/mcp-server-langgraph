/**
 * ProgressIndicator Tests
 *
 * TDD tests for the Progress Indicator component.
 * Tests cover:
 * - Determinate progress bar (known percentage)
 * - Indeterminate spinner (unknown duration)
 * - Status text display
 * - Cancel button
 * - ETA display
 * - WCAG 2.1 AA accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ProgressIndicator } from "./ProgressIndicator";

import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

describe("ProgressIndicator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Determinate Progress Tests
  // ===========================================================================

  describe("determinate progress", () => {
    it("should render progress bar with percentage", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} max={100} />
        </TestProvider>,
      );

      expect(screen.getByRole("progressbar")).toBeInTheDocument();
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-valuenow",
        "50",
      );
    });

    it("should show percentage text", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={75} max={100} showPercentage />
        </TestProvider>,
      );

      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    it("should update progress bar width via CSS custom property", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={60} max={100} />
        </TestProvider>,
      );

      const progressFill = screen.getByTestId("progress-fill");
      // Uses CSS custom property for width (applied via progress-bar-fill class)
      expect(progressFill).toHaveClass("progress-bar-fill");
      expect(progressFill.style.getPropertyValue("--progress")).toBe("60%");
    });

    it("should handle custom max value", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={5} max={10} showPercentage />
        </TestProvider>,
      );

      expect(screen.getByText("50%")).toBeInTheDocument();
    });

    it("should clamp value to 0-100%", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={150} max={100} showPercentage />
        </TestProvider>,
      );

      expect(screen.getByText("100%")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Indeterminate Progress Tests
  // ===========================================================================

  describe("indeterminate progress", () => {
    it("should render spinner when indeterminate", () => {
      render(
        <TestProvider>
          <ProgressIndicator indeterminate />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-spinner")).toBeInTheDocument();
    });

    it("should not show percentage when indeterminate", () => {
      render(
        <TestProvider>
          <ProgressIndicator indeterminate showPercentage />
        </TestProvider>,
      );

      expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    });

    it("should have aria-busy when indeterminate", () => {
      render(
        <TestProvider>
          <ProgressIndicator indeterminate />
        </TestProvider>,
      );

      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-busy",
        "true",
      );
    });
  });

  // ===========================================================================
  // Status Text Tests
  // ===========================================================================

  describe("status text", () => {
    it("should display status message", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} status="Processing files..." />
        </TestProvider>,
      );

      expect(screen.getByText("Processing files...")).toBeInTheDocument();
    });

    it("should update status dynamically", () => {
      const { rerender } = render(
        <TestProvider>
          <ProgressIndicator value={25} status="Step 1 of 4" />
        </TestProvider>,
      );

      expect(screen.getByText("Step 1 of 4")).toBeInTheDocument();

      rerender(<ProgressIndicator value={50} status="Step 2 of 4" />);

      expect(screen.getByText("Step 2 of 4")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Cancel Button Tests
  // ===========================================================================

  describe("cancel button", () => {
    it("should show cancel button when onCancel is provided", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} onCancel={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should call onCancel when cancel button clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ProgressIndicator value={50} onCancel={onCancel} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalled();
    });

    it("should hide cancel button when not provided", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} />
        </TestProvider>,
      );

      expect(
        screen.queryByRole("button", { name: /cancel/i }),
      ).not.toBeInTheDocument();
    });

    it("should disable cancel button when cancelling prop is true", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} onCancel={() => {}} cancelling={true} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });
  });

  // ===========================================================================
  // ETA Display Tests
  // ===========================================================================

  describe("ETA display", () => {
    it("should show ETA when provided", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} eta="2 minutes remaining" />
        </TestProvider>,
      );

      expect(screen.getByText("2 minutes remaining")).toBeInTheDocument();
    });

    it("should hide ETA when not provided", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} />
        </TestProvider>,
      );

      expect(screen.queryByText(/remaining/i)).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Size Variants Tests
  // ===========================================================================

  describe("size variants", () => {
    it("should render small size", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} size="sm" />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveAttribute(
        "data-size",
        "sm",
      );
    });

    it("should render medium size by default", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveAttribute(
        "data-size",
        "md",
      );
    });

    it("should render large size", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} size="lg" />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveAttribute(
        "data-size",
        "lg",
      );
    });
  });

  // ===========================================================================
  // Color Variants Tests
  // ===========================================================================

  describe("color variants", () => {
    it("should render default color", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveAttribute(
        "data-color",
        "primary",
      );
    });

    it("should render success color", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={100} color="success" />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveAttribute(
        "data-color",
        "success",
      );
    });

    it("should render warning color", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} color="warning" />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveAttribute(
        "data-color",
        "warning",
      );
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <ProgressIndicator value={50} status="Loading..." />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper aria-valuemin and aria-valuemax", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} max={100} />
        </TestProvider>,
      );

      const progressbar = screen.getByRole("progressbar");
      expect(progressbar).toHaveAttribute("aria-valuemin", "0");
      expect(progressbar).toHaveAttribute("aria-valuemax", "100");
    });

    it("should have aria-label", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} label="Upload progress" />
        </TestProvider>,
      );

      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-label",
        "Upload progress",
      );
    });

    it("should announce progress changes to screen readers", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} status="Uploading..." />
        </TestProvider>,
      );

      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <ProgressIndicator value={50} className="custom-class" />
        </TestProvider>,
      );

      expect(screen.getByTestId("progress-indicator")).toHaveClass(
        "custom-class",
      );
    });
  });
});
